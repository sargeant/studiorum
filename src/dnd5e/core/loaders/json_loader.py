"""JSON data loader with Pydantic validation."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..cache import get_cache
from ..config.settings import get_settings
from ..logging import get_logger
from ..models.content import BaseContent, ContentType
from ..validation.error_tracker import ValidationErrorTracker
from .base import DataLoader
from .content_factory import ContentFactory, get_content_factory

logger = get_logger(__name__)


# Content factory for creating content instances
# This removes the need for direct model imports


class JsonDataLoader(DataLoader[BaseContent]):
    """Loads and validates JSON data using Pydantic models with dependency injection."""

    def __init__(
        self,
        content_type: ContentType,
        content_factory: ContentFactory | None = None,
    ):
        self._content_type = content_type
        self._content_factory = content_factory or get_content_factory()
        self._error_tracker = ValidationErrorTracker()
        self._settings = get_settings()

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

    async def load(
        self, path: Path
    ) -> list[BaseContent]:  # Changed from T to BaseContent
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
        result = await self._load_from_file(path)

        # Cache the result (24 hour TTL)
        cache.set(cache_key, result, expire=timedelta(hours=24).total_seconds())

        return result

    async def _load_from_file(self, path: Path) -> list[BaseContent]:
        """Load JSON file from disk."""
        try:
            logger.info(f"Loading {self._content_type.value} data from {path}")

            # Read JSON file
            with open(path, encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    # Check if this might be an index file with malformed JSON
                    f.seek(0)
                    content = f.read()
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

            # Validate each item
            validated_content = []
            for item in content_list:
                try:
                    # Skip copy-template items that reference other content
                    if self._is_copy_template(item):
                        logger.debug(
                            f"Skipping copy-template item {item.get('name', 'unknown')} in {path}"
                        )
                        continue

                    # Skip sections when parsing inappropriate content types
                    if item.get("type") == "section" and self._content_type not in [
                        ContentType.BOOK,
                        ContentType.ADVENTURE,
                    ]:
                        logger.debug(
                            f"Skipping section item when parsing {self._content_type.value}"
                        )
                        continue

                    # Ensure source information is present
                    item = self._ensure_source_info(item, path)

                    # Add missing required fields with reasonable defaults
                    item = self._add_missing_required_fields(item)

                    validated_item = self._content_factory.create_content(
                        item, self._content_type
                    )
                    validated_content.append(validated_item)
                except ValidationError as e:
                    # Handle validation error with enhanced error tracking
                    self._handle_validation_error(e, item, path)
                except Exception as e:
                    logger.error(f"Unexpected error validating item in {path}: {e}")

            logger.info(
                f"Successfully loaded {len(validated_content)} {self._content_type.value} items from {path}"
            )
            return validated_content

        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return []

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

        # Direct content arrays
        if self._content_type == ContentType.SPELL and "spell" in data:
            spell_data = data["spell"]
            if isinstance(spell_data, list):
                return spell_data
            return []
        elif self._content_type == ContentType.CREATURE and "monster" in data:
            monster_data = data["monster"]
            if isinstance(monster_data, list):
                return monster_data
            return []
        elif self._content_type == ContentType.ITEM and "item" in data:
            item_data = data["item"]
            if isinstance(item_data, list):
                return item_data
            return []
        elif self._content_type == ContentType.ADVENTURE:
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
            elif "data" in data:
                # Handle 5etools adventure data format with data array
                # Return the entire file as a single adventure, not individual sections
                adventure_data = data["data"]
                if isinstance(adventure_data, list) and adventure_data:
                    return [data]  # Wrap entire file structure as single adventure
            return []
        elif self._content_type == ContentType.BOOK:
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
            elif "data" in data:
                # Handle 5etools book data format with data array
                # Return the entire file as a single book, not individual sections
                book_data = data["data"]
                if isinstance(book_data, list) and book_data:
                    return [data]  # Wrap entire file structure as single book
            return []
        elif self._content_type == ContentType.FEAT and "feat" in data:
            feat_data = data["feat"]
            if isinstance(feat_data, list):
                return feat_data
            return []
        elif self._content_type == ContentType.RACE and "race" in data:
            race_data = data["race"]
            if isinstance(race_data, list):
                return race_data
            return []
        elif self._content_type == ContentType.BACKGROUND and "background" in data:
            background_data = data["background"]
            if isinstance(background_data, list):
                return background_data
            return []
        elif self._content_type == ContentType.CLASS and "class" in data:
            class_data = data["class"]
            if isinstance(class_data, list):
                return class_data
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
        # Map content types to their allowed JSON keys
        content_type_keys = {
            ContentType.SPELL: {"spell", "spells"},
            ContentType.CREATURE: {
                "creature",
                "creatures",
                "monster",
                "monsters",
                "bestiary",
            },
            ContentType.ITEM: {
                "item",
                "items",
                "baseitem",
                "baseItems",
                "magicvariant",
                "magicVariant",
            },
            ContentType.CLASS: {"class", "classes"},
            ContentType.RACE: {"race", "races"},
            ContentType.BACKGROUND: {"background", "backgrounds"},
            ContentType.FEAT: {"feat", "feats"},
            ContentType.ADVENTURE: {"adventure", "adventures"},
            ContentType.BOOK: {
                "book",
                "books",
                "bookData",
                "data",
            },  # Books have multiple formats
            ContentType.SPELL_FLUFF: {"spellFluff", "spell_fluff"},
            ContentType.CREATURE_FLUFF: {
                "creatureFluff",
                "creature_fluff",
                "monsterFluff",
                "monster_fluff",
            },
            ContentType.ITEM_FLUFF: {"itemFluff", "item_fluff"},
        }

        return content_type_keys.get(self._content_type, set())

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

    def _add_missing_required_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        """Add missing required fields with reasonable defaults."""
        # Handle missing fields for different content types
        if self._content_type == ContentType.CREATURE:
            # Add missing alignment field for creatures
            if "alignment" not in item:
                item["alignment"] = ["N"]  # Default to Neutral
                logger.debug(
                    f"Added default alignment for creature {item.get('name', 'unknown')}"
                )

        elif self._content_type == ContentType.ITEM:
            # Add missing type field for items
            if "type" not in item:
                item_type = self._infer_item_type(item)
                item["type"] = item_type
                logger.debug(
                    f"Added inferred type '{item_type}' for item {item.get('name', 'unknown')}"
                )

        elif self._content_type == ContentType.ADVENTURE:
            # Add missing name field for 5etools adventure format
            if "name" not in item and "data" in item:
                # For 5etools format, derive adventure name from source or use generic name
                source = item.get("source")
                if source:
                    abbrev = None
                    # Handle both dict and object source formats
                    if isinstance(source, dict):
                        abbrev = source.get("abbreviation")
                    elif hasattr(source, "abbreviation"):
                        abbrev = source.abbreviation

                    if abbrev:
                        # Use abbreviation as name for adventures since actual names are in adventures.json
                        item["name"] = f"Adventure {abbrev}"
                    else:
                        item["name"] = "Unknown Adventure"
                else:
                    item["name"] = "Unknown Adventure"
                logger.debug(f"Added name '{item['name']}' for adventure")

        elif self._content_type == ContentType.BOOK:
            # Add missing name field for 5etools book format
            if "name" not in item and "data" in item:
                # For 5etools format, derive book name from source or use generic name
                source = item.get("source")
                if source:
                    abbrev = None
                    # Handle both dict and object source formats
                    if isinstance(source, dict):
                        abbrev = source.get("abbreviation")
                    elif hasattr(source, "abbreviation"):
                        abbrev = source.abbreviation

                    if abbrev:
                        # Convert abbreviation to readable name
                        name_map = {
                            "PHB": "Player's Handbook",
                            "MM": "Monster Manual",
                            "DMG": "Dungeon Master's Guide",
                            "XPHB": "Player's Handbook (2024)",
                        }
                        item["name"] = name_map.get(abbrev, abbrev)
                    else:
                        item["name"] = "Unknown Book"
                else:
                    item["name"] = "Unknown Book"
                logger.debug(f"Added name '{item['name']}' for book")

        elif self._content_type == ContentType.SPELL:
            # Add missing required fields for spells
            defaults_added = []

            if "components" not in item:
                item["components"] = {}  # Empty dict for SpellComponent defaults
                defaults_added.append("components")

            if "level" not in item:
                item["level"] = 0  # Cantrip
                defaults_added.append("level")

            if "school" not in item:
                item["school"] = "T"  # Transmutation
                defaults_added.append("school")

            if "time" not in item:
                item["time"] = [{"number": 1, "unit": "action"}]
                defaults_added.append("time")

            if "range" not in item:
                item["range"] = {"type": "point", "distance": {"type": "self"}}
                defaults_added.append("range")

            if "duration" not in item:
                item["duration"] = [{"type": "instant"}]
                defaults_added.append("duration")

            if "entries" not in item:
                item["entries"] = ["Incomplete spell data."]
                defaults_added.append("entries")

            if defaults_added:
                logger.debug(
                    f"Added default fields {defaults_added} for spell {item.get('name', 'unknown')}"
                )

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

    def _is_copy_template(self, item: dict[str, Any]) -> bool:
        """Check if this item is a copy-template that references other content."""
        # Check for 5etools copy mechanism
        if "_copy" in item:
            return True

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

    def _is_index_file(self, path: Path, data: dict[str, Any]) -> bool:
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

    def _make_fluff_compatible(
        self, fluff_item: dict[str, Any], path: Path
    ) -> dict[str, Any] | None:
        """Convert fluff item to be compatible with main content model - deprecated."""
        logger.debug(
            f"Fluff compatibility conversion called for {self._content_type.value} in {path}"
        )
        return None

    def _infer_item_type(self, item: dict[str, Any]) -> str:
        """Infer item type from common fields."""
        if "weaponCategory" in item:
            return "weapon"
        if "armorCategory" in item:
            return "armor"
        if "wondrous" in item:
            return "wondrous item"
        if "consumable" in item:
            return "consumable"
        return "item"  # Default generic item

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
        ):
            return False

        # If it has 'book' key, it's definitely not a content file
        if "book" in data:
            return False

        # Check if it has metadata fields - if so, it's a mixed file and should be loaded
        metadata_fields = {"name", "id", "source", "published", "author", "level"}
        has_metadata = any(field in data for field in metadata_fields)

        # Only consider it a pure content file if it has ONLY 'data' and no metadata fields
        return not has_metadata

    def _extract_text_from_entries(self, entries: Any) -> list[str]:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                text_parts.extend(self._extract_text_from_entries(entry))
        elif isinstance(entries, dict):
            # Handle different entry types
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
                # Skip copy-template items that reference other content
                if self._is_copy_template(item):
                    logger.debug(
                        f"Skipping copy-template item {item.get('name', 'unknown')} in {path}"
                    )
                    continue

                # Skip sections when parsing inappropriate content types
                if item.get("type") == "section" and self._content_type not in [
                    ContentType.BOOK,
                    ContentType.ADVENTURE,
                ]:
                    logger.debug(
                        f"Skipping section item when parsing {self._content_type.value}"
                    )
                    continue

                # Ensure source information is present
                item = self._ensure_source_info(item, path)

                # Add missing required fields with reasonable defaults
                item = self._add_missing_required_fields(item)

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
        context = {
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
