"""JSON data loader with Pydantic validation."""

import json
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from pydantic import ValidationError

from ..cache import get_cache
from ..config.settings import get_settings
from ..logging import get_logger
from ..models.content import BaseContent, ContentType
from ..validation.error_tracker import ValidationErrorTracker
from .base import DataLoader
from .content_factory import ContentFactory

logger = get_logger(__name__)


# Content factory for creating content instances
# This removes the need for direct model imports


class JsonDataLoader(DataLoader[BaseContent]):
    """Loads and validated JSON data using Pydantic models with dependency injection."""

    # Class-level shared registry for base items metadata
    _shared_base_items_registry: dict[str, dict[str, Any]] | None = None

    def __init__(
        self,
        content_type: ContentType,
        content_factory: ContentFactory | None = None,
    ):
        self._content_type = content_type
        if content_factory is None:
            from ..container import get_global_container

            factory_result = get_global_container().get_content_factory()
            if factory_result.is_error():
                raise RuntimeError(
                    f"Failed to get content factory: {factory_result.error.message}"  # type: ignore[attr-defined]
                )
            content_factory = factory_result.unwrap()
        self._content_factory = content_factory
        self._error_tracker = ValidationErrorTracker()
        self._settings = get_settings()
        self._base_items_registry: dict[str, dict[str, Any]] | None = None

        # Class-level registry is already declared above

    def _get_cache_key(self, path: Path) -> str:
        """Generate cache key for a file path."""
        # Use file path, content type, file modification time, and file size
        # Including both mtime and size helps detect changes even when mtime precision is low
        try:
            stat = path.stat()
            return f"json_loader:{self._content_type.value}:{path}:{stat.st_mtime}:{stat.st_size}"
        except OSError:
            # If we can't stat the file, just use the path
            return f"json_loader:{self._content_type.value}:{path}:0:0"

    def load(self, path: Path) -> list[BaseContent]:  # Changed from T to BaseContent
        """Load JSON file and validate against Pydantic model."""
        # Try to get from cache first
        cache = get_cache()
        cache_key = self._get_cache_key(path)

        # Check cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {path}")
            return cached_result  # type: ignore[no-any-return]

        # Load from file if not in cache
        result = self._load_from_file(path)

        # Cache the result (24 hour TTL)
        cache.set(cache_key, result, expire=timedelta(hours=24).total_seconds())

        return result

    def _load_from_file(self, path: Path) -> list[BaseContent]:
        """Load JSON file from disk."""
        try:
            logger.info(f"Loading {self._content_type.value} data from {path}")

            # Read JSON file synchronously
            with open(path, encoding="utf-8") as f:
                content = ""  # Initialize content
                try:
                    content = f.read()
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    # Check if this might be an index file with malformed JSON
                    if "{@" in content and any(
                        pattern in path.name.lower()
                        for pattern in ["-list.", "index.", "_list.", "_index."]
                    ):
                        logger.debug(f"Skipping malformed index file: {path}")
                        return []
                    else:
                        # Re-raise the original error for other files
                        raise e

            # Extract content based on file structure
            content_list = self._extract_content(data, path)

            # Validate each item sequentially
            validated_content = self._validate_items_sequentially(content_list, path)

            logger.info(
                f"Successfully loaded {len(validated_content)} {self._content_type.value} items from {path}"
            )
            return validated_content

        except Exception as e:
            logger.warning(
                f"Failed to load {self._content_type.value} from {path}: {e}"
            )
            return []

    def _validate_items_sequentially(
        self, content_list: list[dict], path: Path
    ) -> list[BaseContent]:
        """Validate content items sequentially (for smaller files)."""
        validated_content = []
        for item in content_list:
            try:
                # Resolve _copy references for items
                if "_copy" in item:
                    item = self._process_copy_inheritance(item)

                # Also check if item type references a base item that needs inheritance
                item = self._resolve_base_type_inheritance(item)

                # Skip other copy-template items (NPCs with missing stats)
                # But don't skip items marked for copy resolution
                if self._is_copy_template(item) and not item.get(
                    "_needsCopyResolution"
                ):
                    logger.debug(
                        f"Skipping copy-template item {item.get('name', 'unknown')} in {path}"
                    )
                    continue

                # Skip sections when parsing inappropriate content types
                if item.get("type") == "section" and self._content_type.value not in [
                    "book",
                    "adventure",
                ]:
                    logger.debug(
                        f"Skipping section item when parsing {self._content_type.value}"
                    )
                    continue

                # Ensure source information is present
                item = self._ensure_source_info(item, path)

                # For items needing copy resolution, create a minimal placeholder object
                if item.get("_needsCopyResolution"):
                    validated_item = self._create_copy_placeholder(
                        item, self._content_type
                    )
                else:
                    validated_item = self._content_factory.create_content(
                        item, self._content_type
                    )

                validated_content.append(validated_item)
            except ValidationError as e:
                # Handle validation error with enhanced error tracking
                self._handle_validation_error(e, item, path)
            except Exception as e:
                logger.error(f"Unexpected error validating item in {path}: {e}")

        return validated_content

    def get_content_type(self) -> ContentType:
        return self._content_type

    def get_supported_types(self) -> list[ContentType]:
        """Get list of supported content types."""
        return self._content_factory.get_supported_types()

    def get_model_class(self) -> type[BaseContent]:
        """Return the base content class for backward compatibility."""
        return BaseContent

    def _extract_content(
        self, data: dict[str, Any], path: Path
    ) -> list[dict[str, Any]]:
        """Extract content list from various JSON structures."""
        # Handle different JSON structures from 5etools

        # Check if this is an index/list file and skip it
        if self._is_index_file(path, data):
            logger.debug(f"Skipping index/list file: {path}")
            return []

        # Check if this is a Foundry VTT format file and skip it
        if self._is_foundry_file(path, data):
            logger.debug(f"Skipping Foundry VTT format file: {path}")
            return []

        # Check if this is a template file and skip it
        if self._is_template_file(path, data):
            logger.debug(f"Skipping template file: {path}")
            return []

        # Check if this is a fluff file - these should be handled by FluffDataLoader
        if self._is_fluff_file(path, data):
            logger.debug(
                f"Fluff file {path} should be handled by FluffDataLoader, skipping"
            )
            return []

        # Check if this is a metadata/sources file and skip it
        if self._is_metadata_file(path, data):
            logger.debug(f"Skipping metadata/sources file: {path}")
            return []

        # Direct content arrays using string-based comparisons
        if self._content_type.value == "spell" and "spell" in data:
            spell_data = data["spell"]
            if isinstance(spell_data, list):
                return spell_data
            return []
        elif self._content_type.value == "creature" and "monster" in data:
            monster_data = data["monster"]
            if isinstance(monster_data, list):
                return monster_data
            return []
        elif self._content_type.value == "item" and "item" in data:
            item_data = data["item"]
            if isinstance(item_data, list):
                return item_data
            return []
        elif self._content_type.value == "adventure":
            # Handle both metadata files (adventures.json) and content files (adventure-*.json)

            # Check if this is a metadata file (adventures.json) and process it
            if self._is_adventure_metadata_file(data):
                logger.debug("Processing adventure metadata file")
                adventure_data = data["adventure"]
                if isinstance(adventure_data, list):
                    return adventure_data
                return []

            # Check if this is a content file (adventure-*.json) and process it
            if self._is_adventure_content_file(data):
                logger.debug("Processing adventure content file")
                # Transform content file format to expected Adventure format
                return self._process_adventure_content_file(data)

            # Handle mixed format (metadata + data in same file)
            if "data" in data and isinstance(data["data"], list):
                # This is a mixed format file with both metadata and content
                # Return the entire file structure as a single adventure
                logger.debug("Processing mixed format adventure (metadata + data)")
                return [data]

            # Legacy handling for other adventure formats
            if "adventure" in data:
                adventure_data = data["adventure"]
                if isinstance(adventure_data, list):
                    return adventure_data
                return []
            elif "adventureData" in data:
                # Handle adventure data format
                adventure_data = data["adventureData"]
                if isinstance(adventure_data, list) and adventure_data:
                    return adventure_data

            return []
        elif self._content_type.value == "book":
            # Handle both metadata files (books.json) and content files (book-*.json)

            # Check if this is a metadata file (books.json) and process it
            if self._is_book_metadata_file(data):
                logger.debug("Processing book metadata file")
                book_data = data["book"]
                if isinstance(book_data, list):
                    return book_data
                return []

            # Check if this is a content file (book-*.json) and process it
            if self._is_book_content_file(data):
                logger.debug("Processing book content file")
                # Return the entire file structure as a single book (preserve original format)
                return [data]

            # Legacy handling for other book formats (priority order: book > bookData > data)
            if "book" in data:
                book_data = data["book"]
                if isinstance(book_data, list):
                    return book_data
                return []
            elif "bookData" in data:
                # Handle book data format
                book_data = data["bookData"]
                if isinstance(book_data, list) and book_data:
                    return book_data

            # Handle mixed format (metadata + data in same file) - lowest priority
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                # This is a mixed format file with both metadata and content
                # Return the entire file structure as a single book
                logger.debug("Processing mixed format book (metadata + data)")
                return [data]

            return []
        elif self._content_type.value == "feat" and "feat" in data:
            feat_data = data["feat"]
            if isinstance(feat_data, list):
                return feat_data
            return []
        elif self._content_type.value == "race" and "race" in data:
            race_data = data["race"]
            if isinstance(race_data, list):
                return race_data
            return []
        elif self._content_type.value == "background" and "background" in data:
            background_data = data["background"]
            if isinstance(background_data, list):
                return background_data
            return []
        elif self._content_type.value == "class" and "class" in data:
            class_data = data["class"]
            if isinstance(class_data, list):
                return class_data
            return []
        elif self._content_type.value == "variantrule" and "variantrule" in data:
            variant_rule_data = data["variantrule"]
            if isinstance(variant_rule_data, list):
                return variant_rule_data
            return []
        elif self._content_type.value == "action" and "action" in data:
            action_data = data["action"]
            if isinstance(action_data, list):
                return action_data
            return []
        elif self._content_type.value == "condition" and "condition" in data:
            condition_data = data["condition"]
            if isinstance(condition_data, list):
                return condition_data
            return []
        elif self._content_type.value == "sense" and "sense" in data:
            sense_data = data["sense"]
            if isinstance(sense_data, list):
                return sense_data
            return []
        elif self._content_type.value == "hazard" and "hazard" in data:
            hazard_data = data["hazard"]
            if isinstance(hazard_data, list):
                return hazard_data
            return []
        elif self._content_type.value == "status" and "status" in data:
            status_data = data["status"]
            if isinstance(status_data, list):
                return status_data
            return []

        # Generic fallbacks
        content_type_name = self._content_type.value
        if content_type_name in data:
            generic_data = data[content_type_name]
            if isinstance(generic_data, list):
                return generic_data
            return []

        # Try plural forms
        plural_name = content_type_name + "s"
        if plural_name in data:
            plural_data = data[plural_name]
            if isinstance(plural_data, list):
                return plural_data
            return []

        # If the data itself is a list, use it directly
        if isinstance(data, list):
            return data

        # Strict content type validation - only allow specific keys for each content type
        # This prevents cross-contamination between content types (fixes issue #54)
        allowed_fallback_keys = self._get_allowed_fallback_keys()

        for key, value in data.items():
            if key in allowed_fallback_keys and isinstance(value, list) and value:
                logger.debug(
                    f"Using '{key}' array as content for {self._content_type.value}"
                )
                return value

        # No valid content found for this content type
        logger.debug(
            f"No valid content keys found for {self._content_type.value}. "
            f"Expected keys: {list(allowed_fallback_keys)} but found: {list(data.keys())}"
        )

        logger.warning(f"No content found for {self._content_type.value} in {path}")
        return []

    def _get_allowed_fallback_keys(self) -> set[str]:
        """Get the set of JSON keys that are allowed for fallback extraction for this content type.

        This prevents cross-contamination where a spell loader could extract class data
        through generic fallback logic, which would then have spell defaults injected.

        Returns:
            Set of allowed JSON keys for this content type
        """
        # Map content types to their allowed JSON keys using string-based mapping
        content_type_keys = {
            "spell": {"spell", "spells"},
            "creature": {
                "creature",
                "creatures",
                "monster",
                "monsters",
                "bestiary",
            },
            "item": {
                "item",
                "items",
                "baseitem",
                "baseItems",
                "magicvariant",
                "magicVariant",
            },
            "class": {"class", "classes"},
            "race": {"race", "races"},
            "background": {"background", "backgrounds"},
            "feat": {"feat", "feats"},
            "adventure": {"adventure", "adventures"},
            "book": {
                "book",
                "books",
                "bookData",
                "data",
            },  # Books have multiple formats
            "spellFluff": {"spellFluff", "spell_fluff"},
            "creatureFluff": {
                "creatureFluff",
                "creature_fluff",
                "monsterFluff",
                "monster_fluff",
            },
            "itemFluff": {"itemFluff", "item_fluff"},
            "variantrule": {"variantrule", "variantrules"},
            "action": {"action", "actions"},
            "condition": {"condition", "conditions"},
            "sense": {"sense", "senses"},
            "hazard": {"hazard", "hazards"},
            "status": {"status", "statuses"},
        }

        return content_type_keys.get(self._content_type.value, set())

    def _ensure_source_info(self, item: dict[str, Any], path: Path) -> dict[str, Any]:
        """Ensure item has source information."""
        if "source" not in item:
            # Try to infer source from filename
            source_abbrev = self._infer_source_from_path(path)
            item["source"] = {
                "abbreviation": source_abbrev,
                "name": source_abbrev,  # Will be resolved later by source manager
            }
        elif isinstance(item["source"], str):
            # Convert string source to proper format
            source_abbrev = item["source"]
            item["source"] = {"abbreviation": source_abbrev, "name": source_abbrev}

        return item

    def _infer_source_from_path(self, path: Path) -> str:
        """Infer source abbreviation from file path."""
        filename = path.stem.lower()

        # Common source patterns in filenames
        source_patterns = {
            "phb": "PHB",
            "mm": "MM",
            "dmg": "DMG",
            "scag": "SCAG",
            "vgm": "VGM",
            "xge": "XGE",
            "mtf": "MTF",
            "tce": "TCE",
            "cos": "CoS",
            "player": "PHB",
            "monster": "MM",
            "dungeon": "DMG",
        }

        for pattern, source in source_patterns.items():
            if pattern in filename:
                return source

        # Fallback: use filename as source
        return path.stem.upper()

    def _is_foundry_file(self, path: Path, data: dict[str, Any]) -> bool:
        """Check if this is a Foundry VTT format file."""
        filename = path.name.lower()

        # Check filename patterns
        if "foundry" in filename:
            return True

        # Check for Foundry-specific data structure
        # Foundry files often have content with 'system', 'activities', or '_id' fields
        for content_array in data.values():
            if isinstance(content_array, list) and content_array:
                first_item = content_array[0]
                if isinstance(first_item, dict):
                    foundry_indicators = [
                        "system",
                        "activities",
                        "_id",
                        "migrationVersion",
                        "folder",
                    ]
                    if any(indicator in first_item for indicator in foundry_indicators):
                        return True

        return False

    def _is_template_file(self, path: Path, data: dict[str, Any]) -> bool:
        """Check if this is a template file containing incomplete creature data."""
        filename = path.name.lower()

        # Only check filename patterns for explicit template markers
        if "template" in filename and "creature" in filename:
            return True

        # For creature files only, check if content looks like templates
        if self._content_type != ContentType.CREATURE:
            return False

        # Check if this file contains template-like data structures
        # Templates often have incomplete creature data or special markers
        for content_array in data.values():
            if isinstance(content_array, list) and content_array:
                # Check if ALL items in the array look like templates
                template_items = 0
                total_items = 0

                for item in content_array[:5]:  # Check first 5 items
                    if not isinstance(item, dict):
                        continue

                    total_items += 1

                    # Check for explicit template indicators
                    template_indicators = [
                        "template",
                        "inherit",
                        "_template",
                        "isTemplate",
                    ]
                    if any(indicator in item for indicator in template_indicators):
                        template_items += 1
                        continue

                    # Check if most required creature fields are missing (indicates template)
                    required_fields = ["size", "type", "alignment", "ac", "hp", "speed"]
                    missing_count = sum(
                        1 for field in required_fields if field not in item
                    )
                    if (
                        missing_count >= 5
                    ):  # If missing almost all required fields, likely a template
                        template_items += 1

                # Only mark as template if most items look like templates
                if total_items > 0 and template_items / total_items >= 0.8:
                    return True

        return False

    def _get_base_items_registry(self) -> dict[str, dict[str, Any]]:
        """Get or create the base items registry for _copy resolution."""
        # Use shared registry to ensure all loader instances use the same data
        if JsonDataLoader._shared_base_items_registry is None:
            JsonDataLoader._shared_base_items_registry = self._load_base_items()
        return JsonDataLoader._shared_base_items_registry

    def _load_base_items(self) -> dict[str, dict[str, Any]]:
        """Load all base item definitions for _copy resolution from items-base.json."""
        registry = {}

        # Find items-base.json in data paths
        from ..config.paths import get_path_config

        path_config = get_path_config()

        # Check multiple possible locations for items-base.json
        possible_paths = []

        # Check configured data paths
        if path_config.data_path and path_config.data_path.exists():
            possible_paths.append(path_config.data_path / "items-base.json")

        # Check 5etools-src directory
        fivetools_src = (
            Path.home() / "Code" / "5etools-src" / "data" / "items-base.json"
        )
        if fivetools_src.exists():
            possible_paths.append(fivetools_src)

        # Check srd-data directory
        srd_data = path_config.root_path / "srd-data" / "items-base.json"
        if srd_data.exists():
            possible_paths.append(srd_data)

        # Try to load from the first available path
        for base_path in possible_paths:
            if base_path.exists():
                try:
                    with open(base_path, encoding="utf-8") as f:
                        base_data = json.loads(f.read())

                    # Extract both baseitem and itemType arrays
                    items_loaded = 0

                    if "baseitem" in base_data and isinstance(
                        base_data["baseitem"], list
                    ):
                        for item in base_data["baseitem"]:
                            if "abbreviation" in item and "source" in item:
                                key = f"{item['abbreviation']}|{item['source']}"
                                registry[key] = item
                                items_loaded += 1

                    if "itemType" in base_data and isinstance(
                        base_data["itemType"], list
                    ):
                        for item in base_data["itemType"]:
                            if "abbreviation" in item and "source" in item:
                                key = f"{item['abbreviation']}|{item['source']}"
                                registry[key] = item
                                items_loaded += 1

                    if items_loaded > 0:
                        logger.debug(
                            f"Loaded {items_loaded} base items from {base_path}"
                        )
                        break
                    else:
                        logger.warning(
                            f"No baseitem or itemType arrays found in {base_path}"
                        )

                except Exception as e:
                    logger.warning(f"Failed to load base items from {base_path}: {e}")
                    continue

        if not registry:
            logger.warning(
                "No base items registry loaded - _copy resolution will be unavailable"
            )

        return registry

    def get_type_metadata(self, type_id: str) -> dict[str, Any] | None:
        """Get type metadata for a type ID like '$G|DMG'."""
        base_items = self._get_base_items_registry()
        return base_items.get(type_id)

    @classmethod
    def get_shared_type_metadata(cls, type_id: str) -> dict[str, Any] | None:
        """Get type metadata using shared registry (static access)."""
        if cls._shared_base_items_registry is None:
            # Initialize with empty loader if needed
            temp_loader = cls(ContentType("item"))
            temp_loader._get_base_items_registry()  # This will populate the shared registry

        return (
            cls._shared_base_items_registry.get(type_id)
            if cls._shared_base_items_registry
            else None
        )

    def _process_copy_inheritance(self, item: dict[str, Any]) -> dict[str, Any]:
        """Handle _copy references during JSON loading.

        For now, we only resolve simple base item references (abbreviation/source).
        Complex copy references (name/source with _mod) are marked for post-loading resolution.
        """
        if "_copy" not in item:
            return item

        copy_ref = item["_copy"]
        if not isinstance(copy_ref, dict):
            logger.warning(
                f"Invalid _copy reference format in item {item.get('name', 'unknown')}: expected dict, got {type(copy_ref)}"
            )
            return item

        # Handle simple base item references (existing logic)
        if (
            "abbreviation" in copy_ref
            and "source" in copy_ref
            and not copy_ref.get("_mod")
            and not copy_ref.get("_templates")
        ):
            copy_source_key = f"{copy_ref['abbreviation']}|{copy_ref['source']}"
            base_items = self._get_base_items_registry()
            source_item = base_items.get(copy_source_key)

            if source_item:
                # Merge properties (source properties as base, item properties override)
                resolved_item = {**source_item, **item}
                # Cleanup and mark as copy
                if "_copy" in resolved_item:
                    del resolved_item["_copy"]
                resolved_item["_isCopy"] = True
                logger.debug(
                    f"Resolved simple _copy inheritance for {item.get('name', 'unknown')} from {copy_source_key}"
                )
                return resolved_item
            else:
                logger.warning(
                    f"Could not resolve base item _copy reference: {copy_source_key} for item {item.get('name', 'unknown')}"
                )

        # For complex copy references (creature-to-creature, _mod, _templates),
        # mark for post-loading resolution
        if "name" in copy_ref or "_mod" in copy_ref or "_templates" in copy_ref:
            item["_needsCopyResolution"] = True
            logger.debug(
                f"Marked {item.get('name', 'unknown')} for post-loading copy resolution"
            )

        return item

    def _create_copy_placeholder(
        self, item: dict[str, Any], content_type: ContentType
    ) -> BaseContent:
        """Create a placeholder object for items needing copy resolution."""
        # Create a minimal valid object with required fields filled with defaults
        placeholder_data = item.copy()

        if content_type == ContentType.CREATURE:
            # Add minimal required creature fields with placeholder values
            placeholder_data.setdefault("size", ["M"])  # Medium as default
            placeholder_data.setdefault(
                "type", {"type": "humanoid"}
            )  # Generic humanoid
            placeholder_data.setdefault("ac", [10])  # Default AC
            placeholder_data.setdefault(
                "hp", {"average": 1, "formula": "1d1"}
            )  # Minimal HP
            placeholder_data.setdefault("speed", {"walk": 30})  # Default speed
            # Default ability scores (all 10s)
            placeholder_data.setdefault("str", 10)
            placeholder_data.setdefault("dex", 10)
            placeholder_data.setdefault("con", 10)
            placeholder_data.setdefault("int", 10)
            placeholder_data.setdefault("wis", 10)
            placeholder_data.setdefault("cha", 10)

        # Create the content object with the placeholder data
        content_obj = self._content_factory.create_content(
            placeholder_data, content_type
        )

        # Preserve the copy resolution flag and original copy data as extra fields
        if item.get("_needsCopyResolution"):
            if (
                not hasattr(content_obj, "__pydantic_extra__")
                or content_obj.__pydantic_extra__ is None
            ):
                content_obj.__pydantic_extra__ = {}
            content_obj.__pydantic_extra__["_needsCopyResolution"] = True
        if "_copy" in item:
            if (
                not hasattr(content_obj, "__pydantic_extra__")
                or content_obj.__pydantic_extra__ is None
            ):
                content_obj.__pydantic_extra__ = {}
            content_obj.__pydantic_extra__["_copy"] = item["_copy"]

        return content_obj

    def _resolve_base_type_inheritance(self, item: dict[str, Any]) -> dict[str, Any]:
        """Resolve inheritance from base types for items that reference base items by type."""
        # Only handle items without entries that might need base type inheritance
        if "entries" in item and item["entries"]:
            return item

        # Check if item has a type that references a base item
        item_type = item.get("type")
        if not item_type or not isinstance(item_type, str):
            return item

        # Parse type format: "ABBREVIATION|SOURCE" (e.g., "AIR|DMG")
        if "|" not in item_type:
            return item

        base_items = self._get_base_items_registry()
        base_item = base_items.get(item_type)

        if not base_item:
            logger.debug(
                f"No base item found for type {item_type} in item {item.get('name', 'unknown')}"
            )
            return item

        # Resolve the base item's _copy chain if it has one
        resolved_base = base_item
        if "_copy" in base_item:
            resolved_base = self._process_copy_inheritance(base_item.copy())

        # Inherit entries from resolved base item if the item lacks them
        if (
            "entries" in resolved_base
            and resolved_base["entries"]
            and not item.get("entries")
        ):
            item["entries"] = resolved_base["entries"]
            logger.debug(
                f"Inherited entries for {item.get('name', 'unknown')} from base type {item_type}"
            )

        return item

    def _is_copy_template(self, item: dict[str, Any]) -> bool:
        """Check if this item is a copy-template that references other content."""
        # Items with _copy references or marked for copy resolution should not be considered templates
        if "_copy" in item or item.get("_needsCopyResolution"):
            return False

        # Check for NPC/template markers that indicate incomplete data
        if item.get("isNpc"):
            # For NPCs, check if they have basic stat requirements
            # If they're missing AC, HP, and ability scores, they're likely stub entries
            required_creature_fields = [
                "ac",
                "hp",
                "str",
                "dex",
                "con",
                "int",
                "wis",
                "cha",
            ]
            missing_count = sum(
                1 for field in required_creature_fields if field not in item
            )

            # If missing most required creature fields, it's likely a stub/template
            if missing_count >= 6:  # Missing most creature stats
                return True

            # Also check for NPCs that only have basic identity info
            if not any(field in item for field in ["ac", "hp"]):
                return True

        return False

    def _is_index_file(self, path: Path, data: dict[str, Any] | list[Any]) -> bool:
        """Check if this is an index/list file containing tag references."""
        filename = path.name.lower()

        # Check filename patterns for index/list files
        if any(
            pattern in filename for pattern in ["-list.", "index.", "_list.", "_index."]
        ):
            return True

        # Check if the data structure indicates an index file
        # Index files often contain arrays of strings (tag references)
        # rather than arrays of objects (content items)
        if isinstance(data, list):
            # If it's a list and most items are strings containing tags, it's likely an index
            if len(data) > 0:
                string_items = sum(1 for item in data[:10] if isinstance(item, str))
                if string_items / min(len(data), 10) > 0.5:  # More than 50% are strings
                    # Check if strings contain tag patterns
                    tag_strings = sum(
                        1
                        for item in data[:10]
                        if isinstance(item, str) and "{@" in item
                    )
                    if tag_strings > 0:
                        return True

        # Check top-level arrays for similar pattern
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Check first few items
                    sample_size = min(10, len(value))
                    string_items = sum(
                        1 for item in value[:sample_size] if isinstance(item, str)
                    )

                    if string_items / sample_size > 0.5:  # More than 50% are strings
                        # Check if strings contain tag patterns
                        tag_strings = sum(
                            1
                            for item in value[:sample_size]
                            if isinstance(item, str) and "{@" in item
                        )
                        if tag_strings > 0:
                            return True

        return False

    def _is_metadata_file(self, path: Path, data: dict[str, Any]) -> bool:
        """Check if this is a metadata/sources file rather than content."""
        filename = path.name.lower()

        # Check filename patterns for metadata files
        if any(
            pattern in filename
            for pattern in ["sources.", "metadata.", "_sources.", "_metadata."]
        ):
            return True

        # Check if the data structure indicates a metadata file
        # Metadata files typically have source abbreviations as top-level keys
        # and nested structures with metadata rather than content arrays
        if isinstance(data, dict) and not any(
            isinstance(value, list) for value in data.values()
        ):
            # Check if top-level keys look like source abbreviations (typically 2-6 uppercase letters)
            top_keys = list(data.keys())[:5]  # Check first 5 keys
            abbrev_pattern_count = 0

            for key in top_keys:
                if (
                    isinstance(key, str)
                    and len(key) >= 2
                    and len(key) <= 6
                    and key.isupper()
                ):
                    # Check if the value contains metadata structure
                    value = data[key]
                    if isinstance(value, dict):
                        # Look for nested spell/class mapping structures
                        nested_values = list(value.values())[
                            :3
                        ]  # Check first 3 nested items
                        for nested_val in nested_values:
                            if isinstance(nested_val, dict) and "class" in nested_val:
                                abbrev_pattern_count += 1
                                break

            # If most top-level keys look like source abbreviations with metadata, it's likely a metadata file
            if len(top_keys) > 0 and abbrev_pattern_count / len(top_keys) >= 0.6:
                return True

        return False

    def _is_fluff_file(self, path: Path, data: dict[str, Any]) -> bool:
        """Check if this is a fluff data file."""
        filename = path.name.lower()

        # Check filename patterns
        if "fluff" in filename:
            return True

        # Check for fluff data keys
        fluff_keys = [
            "spellFluff",
            "monsterFluff",
            "itemFluff",
            "adventureFluff",
            "bookFluff",
            "fluff",
        ]

        for key in fluff_keys:
            if key in data:
                return True

        return False

    def _extract_fluff_content(
        self, data: dict[str, Any], path: Path
    ) -> list[dict[str, Any]]:
        """Extract fluff content with liberal parsing."""
        # Fluff content should be handled by FluffDataLoader
        logger.debug(
            f"Fluff content extraction called for {self._content_type.value} in {path}"
        )
        return []

    def _process_fluff_items(
        self, fluff_items: list[dict[str, Any]], path: Path
    ) -> list[dict[str, Any]]:
        """Process fluff items - now handled by FluffDataLoader."""
        logger.debug(
            f"Fluff item processing called for {self._content_type.value} in {path}"
        )
        return []

    def _extract_fluff_text(self, fluff_item: dict[str, Any]) -> str:
        """Extract descriptive text from fluff item."""
        text_parts = []

        # Try to extract from entries
        entries = fluff_item.get("entries", [])
        if entries:
            text_parts.extend(self._extract_text_from_entries(entries))

        # Try other text fields
        for field in ["text", "description", "flavor"]:
            if field in fluff_item and isinstance(fluff_item[field], str):
                text_parts.append(fluff_item[field])

        return " ".join(text_parts) if text_parts else ""

    def _is_adventure_metadata_file(self, data: dict[str, Any]) -> bool:
        """Check if this is an adventure metadata file (adventures.json).

        Adventure metadata files have:
        - 'adventure' key with array of adventure metadata objects
        - No 'data' key (which would indicate content files)

        Args:
            data: The parsed JSON data

        Returns:
            True if this is an adventure metadata file
        """
        return (
            isinstance(data, dict)
            and "adventure" in data
            and "data" not in data
            and isinstance(data["adventure"], list)
        )

    def _is_adventure_content_file(self, data: dict[str, Any]) -> bool:
        """Check if this is an adventure content file (adventure-*.json).

        Adventure content files have:
        - ONLY 'data' key with array of section objects
        - No 'adventure' key (which would indicate metadata files)
        - No metadata fields like 'name', 'id', 'source' at root level

        Args:
            data: The parsed JSON data

        Returns:
            True if this is a pure adventure content file (should be skipped during metadata loading)
        """
        if (
            not isinstance(data, dict)
            or "data" not in data
            or not isinstance(data["data"], list)
        ):
            return False

        # If it has 'adventure' key, it's definitely not a content file
        if "adventure" in data:
            return False

        # Check if it has metadata fields - if so, it's a mixed file and should be loaded
        metadata_fields = {"name", "id", "source", "published", "author", "level"}
        has_metadata = any(field in data for field in metadata_fields)

        # Only consider it a pure content file if it has ONLY 'data' and no metadata fields
        return not has_metadata

    def _process_adventure_content_file(
        self, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Process adventure content file into format expected by Adventure model.

        Content files have structure:
        {
            "data": [
                {"type": "section", "name": "...", "entries": [...]}
            ]
        }

        We need to create a single adventure object with the content data.
        """
        if "data" not in data or not isinstance(data["data"], list):
            return []

        # Create a synthetic adventure object with the content
        adventure: dict[str, Any] = {
            "name": "Adventure",  # Default name for content-only files
            "id": "temp",
            "source": "TEMP",
            "contents": [],
            # Transform the data sections into contents
        }

        # Process the data array into contents
        for item in data["data"]:
            if isinstance(item, dict) and item.get("type") == "section":
                chapter = {
                    "name": item.get("name", "Unnamed Chapter"),
                    "entries": item.get("entries", []),
                }
                adventure["contents"].append(chapter)

        return [adventure]

    def _process_book_content_file(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Process book content file into format expected by Book model.

        Content files have structure:
        {
            "data": [
                {"type": "section", "name": "...", "entries": [...]}
            ]
        }

        We need to create a single book object with the content data.
        """
        if "data" not in data or not isinstance(data["data"], list):
            return []

        # Create a synthetic book object with the content
        book: dict[str, Any] = {
            "name": "Book",  # Default name for content-only files
            "id": "temp",
            "source": "TEMP",
            "contents": [],
        }

        # Process the data array into contents
        for item in data["data"]:
            if isinstance(item, dict) and item.get("type") == "section":
                chapter = {
                    "name": item.get("name", "Unnamed Chapter"),
                    "entries": item.get("entries", []),
                }
                book["contents"].append(chapter)

        return [book]

    def _is_book_metadata_file(self, data: dict[str, Any]) -> bool:
        """Check if this is a book metadata file (books.json).

        Book metadata files have:
        - 'book' key with array of book metadata objects
        - No 'data' key (which would indicate content files)

        Args:
            data: The parsed JSON data

        Returns:
            True if this is a book metadata file
        """
        return (
            isinstance(data, dict)
            and "book" in data
            and "data" not in data
            and isinstance(data["book"], list)
        )

    def _is_book_content_file(self, data: dict[str, Any]) -> bool:
        """Check if this is a book content file (book-*.json).

        Book content files have:
        - ONLY 'data' key with array of section objects
        - No 'book' key (which would indicate metadata files)
        - No metadata fields like 'name', 'id', 'source' at root level

        Args:
            data: The parsed JSON data

        Returns:
            True if this is a pure book content file (should be skipped during metadata loading)
        """
        if (
            not isinstance(data, dict)
            or "data" not in data
            or not isinstance(data["data"], list)
            or not data[
                "data"
            ]  # Empty data arrays should not be treated as content files
        ):
            return False

        # If it has 'book' key, it's definitely not a content file
        if "book" in data:
            return False

        # Check if it has metadata fields or other format keys - if so, it's a mixed file and should be loaded
        metadata_fields = {"name", "id", "source", "published", "author", "level"}
        legacy_format_keys = {
            "bookData"
        }  # Other legacy format keys that indicate mixed format
        has_metadata = any(field in data for field in metadata_fields)
        has_legacy_format = any(key in data for key in legacy_format_keys)

        # Only consider it a pure content file if it has ONLY 'data' and no metadata/legacy format fields
        return not (has_metadata or has_legacy_format)

    def _extract_text_from_entries(self, entries: Any) -> list[str]:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                text_parts.extend(self._extract_text_from_entries(entry))
        elif isinstance(entries, dict):
            # Handle structured dict entries (current 5etools format)
            if "entries" in entries:
                text_parts.extend(self._extract_text_from_entries(entries["entries"]))
            elif "text" in entries:
                text_parts.append(entries["text"])
            # Add name if present
            if "name" in entries:
                text_parts.append(f"**{entries['name']}**")
        elif isinstance(entries, str):
            text_parts.append(entries)

        return text_parts

    @classmethod
    def create_for_type(cls, content_type: ContentType) -> "JsonDataLoader":
        """Create a JsonDataLoader instance for a given content type."""
        return JsonDataLoader(content_type)

    def load_from_data(self, data: dict[str, Any], path: Path) -> list[BaseContent]:
        """Load content from already-parsed JSON data.

        Args:
            data: Parsed JSON data dictionary
            path: Path to the source file (for error reporting)

        Returns:
            List of validated content objects
        """
        # Extract content based on file structure
        content_list = self._extract_content(data, path)

        # Validate each item
        validated_content = []
        for item in content_list:
            try:
                # Resolve _copy references for items
                if "_copy" in item:
                    item = self._process_copy_inheritance(item)

                # Also check if item type references a base item that needs inheritance
                item = self._resolve_base_type_inheritance(item)

                # Skip other copy-template items (NPCs with missing stats)
                # But don't skip items marked for copy resolution
                if self._is_copy_template(item) and not item.get(
                    "_needsCopyResolution"
                ):
                    logger.debug(
                        f"Skipping copy-template item {item.get('name', 'unknown')} in {path}"
                    )
                    continue

                # Skip sections when parsing inappropriate content types
                if item.get("type") == "section" and self._content_type.value not in [
                    "book",
                    "adventure",
                ]:
                    logger.debug(
                        f"Skipping section item when parsing {self._content_type.value}"
                    )
                    continue

                # Ensure source information is present
                item = self._ensure_source_info(item, path)

                validated_item = self._content_factory.create_content(
                    item, self._content_type
                )
                validated_content.append(validated_item)
            except ValidationError as e:
                # Handle validation error with enhanced error tracking
                self._handle_validation_error(e, item, path)
            except Exception as e:
                logger.error(f"Unexpected error validating item in {path}: {e}")

        # Log validation summary if enabled
        if self._settings.validation_summary:
            self._log_validation_summary()

        return validated_content

    def _handle_validation_error(
        self, error: ValidationError, item: dict[str, Any], path: Path
    ) -> None:
        """Handle validation errors with deduplication and strictness control.

        Args:
            error: The ValidationError that occurred
            item: The item data that failed validation
            path: Path to the source file
        """
        # Create context for error tracking
        from dnd5e.core.validation.error_tracker import ErrorContext

        context: ErrorContext = {
            "file": str(path),
            "item_name": item.get("name", "unknown"),
            "content_type": self._content_type.value,
        }

        # Check strictness setting
        if self._settings.validation_strictness == "strict":
            # In strict mode, re-raise the validation error
            raise error
        elif self._settings.validation_strictness == "lenient":
            # In lenient mode, only record error but don't log
            self._error_tracker.record_error(error, context)
            return

        # Normal mode: use error tracker for deduplication
        if self._error_tracker.should_log_error(error, context):
            # Format error message with context and suggestions
            formatted_message = self._error_tracker.format_error_message(error, context)
            logger.warning(formatted_message)

        # Always record the error for statistics
        self._error_tracker.record_error(error, context)

    def _log_validation_summary(self) -> None:
        """Log a summary of validation errors encountered during processing."""
        summary = self._error_tracker.get_summary()

        if not summary:
            logger.info("Validation Summary: No validation errors encountered")
            return

        total_errors = sum(data["count"] for data in summary.values())
        total_types = len(summary)

        logger.info(f"Validation Summary: {total_errors} errors of {total_types} types")

        # Log details for each error type
        for error_sig, data in summary.items():
            files_count = len(data["files"])
            logger.info(
                f"  {data['error_type']}: {data['count']} occurrences "
                f"across {files_count} files"
            )
            logger.debug(f"    Message: {data['message']}")
            logger.debug(f"    Field: {data['field_path']}")

            # Show a few example files if there are many
            if files_count <= 3:
                logger.debug(f"    Files: {', '.join(data['files'])}")
            else:
                example_files = data["files"][:3]
                logger.debug(
                    f"    Files: {', '.join(example_files)} "
                    f"(and {files_count - 3} others)"
                )
