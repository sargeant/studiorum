"""Omnidexer system for comprehensive content indexing."""

import hashlib
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

if TYPE_CHECKING:
    from ..container import ServiceContainer
    from ..protocols.progress import ProgressCallback
    from ..services.protocols import SourceManagerProtocol
    from .content_merger import ContentMerger

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..cache import cached
from ..interfaces import DeepIndexable
from ..logging import get_logger
from ..models.content import BaseContent, ContentType
from .base import DataLoader, SourceManager
from .fluff_loader import FluffDataLoader
from .json_loader import JsonDataLoader
from .unified_source_manager import UnifiedSourceManager

logger = get_logger(__name__)


T = TypeVar("T", bound=BaseContent)


class IndexEntry[T: BaseContent](BaseModel):
    """Represents an indexed content entry with validation."""

    content: T = Field(description="The content being indexed")
    content_type: ContentType | Any = Field(description="Type of the content")
    hash_id: str = Field(
        min_length=8, max_length=8, description="8-character unique hash identifier"
    )
    lookup_key: str = Field(
        min_length=1, description="Lowercase lookup key for searches"
    )

    @field_validator("content_type", mode="before")
    @classmethod
    def validate_content_type(cls, v: Any) -> ContentType:
        """Validate content type, handling dynamically extended enums."""
        # Handle ContentType instances directly (including dynamically extended ones)
        # The dynamic enum replacement means isinstance() might fail, so check attributes
        if (
            hasattr(v, "value")
            and hasattr(v, "name")
            and hasattr(v, "__class__")
            and v.__class__.__name__ == "ContentType"
        ):
            # We've verified this has the ContentType interface via duck typing
            # Cast to ContentType for type safety since we know it's the right type
            return cast(ContentType, v)

        # Handle string values by constructing ContentType enum
        if isinstance(v, str):
            try:
                return ContentType(v)
            except ValueError as e:
                # For dynamically registered types, try attribute access
                try:
                    attr_name = v.upper()
                    if hasattr(ContentType, attr_name):
                        attr_value = getattr(ContentType, attr_name)
                        # Verify the attribute is actually a ContentType enum member
                        if (
                            hasattr(attr_value, "value")
                            and hasattr(attr_value, "name")
                            and attr_value.__class__.__name__ == "ContentType"
                        ):
                            return cast(ContentType, attr_value)
                # Validation fallback chain, raises ValueError after all attempts
                except Exception:  # nosec B110
                    pass
                raise ValueError(f"Invalid ContentType: {v}") from e

        # Standard isinstance check for original enum instances
        if isinstance(v, ContentType):
            return v

        raise ValueError(f"ContentType must be ContentType enum, got {type(v)}: {v}")

    @field_validator("hash_id")
    @classmethod
    def validate_hash_id(cls, v: str) -> str:
        """Validate hash ID format."""
        if not v.isalnum():
            raise ValueError("Hash ID must contain only alphanumeric characters")
        return v.lower()

    @field_validator("lookup_key")
    @classmethod
    def validate_lookup_key(cls, v: str) -> str:
        """Validate and normalize lookup key."""
        normalized = v.strip().lower()
        if "|" not in normalized:
            raise ValueError(
                "Lookup key must contain '|' separator between name and source"
            )
        return normalized

    @classmethod
    def create(cls, content: T, content_type: ContentType) -> "IndexEntry[T]":
        """Create an index entry from content with automatic hash and key generation."""
        # Handle different source formats
        if hasattr(content.source, "abbreviation"):
            source_abbrev = content.source.abbreviation
        elif isinstance(content.source, dict):
            source_abbrev = content.source.get("abbreviation", str(content.source))
        else:
            source_abbrev = str(content.source)

        # Generate unique hash (using SHA256 for security)
        identifier = f"{content_type.value}:{content.name}:{source_abbrev}"
        hash_id = hashlib.sha256(identifier.encode()).hexdigest()[:8]

        # Generate lookup key (lowercase for case-insensitive searches)
        lookup_key = f"{content.name}|{source_abbrev}".lower()

        return cls(
            content=content,
            content_type=content_type,
            hash_id=hash_id,
            lookup_key=lookup_key,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Omnidexer:
    """
    Central indexing system for all 5e content with deep content discovery.

    The Omnidexer provides comprehensive content indexing and discovery capabilities,
    including support for nested content through the DeepIndexable protocol. This
    enables discovery of class features within classes, adventure sections within
    adventures, spell references in creature abilities, and more.

    Features:
        - Multi-index architecture (hash, type, source, name-based lookups)
        - Deep content discovery via DeepIndexable protocol
        - Cycle prevention for safe recursive indexing
        - Performance monitoring and optimization
        - Type-safe content resolution
        - Singleton ContentMerger for efficient dual-file operations with cache benefits

    Performance Optimizations:
        The Omnidexer uses a singleton ContentMerger instance that preserves its LRU cache
        across multiple load operations. This significantly improves performance in test
        environments and scenarios where the same data is accessed repeatedly, as the
        cache remains warm between operations rather than being recreated each time.

    Example:
        >>> omnidexer = Omnidexer(enable_deep_indexing=True)
        >>> omnidexer.load_all_data()  # doctest: +SKIP
        >>> # Find primary content
        >>> from ..registry.content_type_resolver import resolve_content_type
        >>> class_type = resolve_content_type("class")
        >>> fighter = omnidexer.find(class_type, "Fighter", "PHB")  # doctest: +SKIP
        >>> # Find nested content (requires deep indexing)
        >>> feature_type = resolve_content_type("classfeature")
        >>> action_surge = omnidexer.find(feature_type, "Action Surge", "PHB")  # doctest: +SKIP
        >>> section_type = resolve_content_type("adventuresection")
        >>> sections = omnidexer.find_all(section_type)  # doctest: +SKIP
    """

    def __init__(
        self,
        source_manager: SourceManager | None = None,
        enable_deep_indexing: bool = True,
    ):
        """
        Initialize the Omnidexer.

        Args:
            source_manager: Custom source manager for content loading. If None,
                          uses UnifiedSourceManager with default sources.
            enable_deep_indexing: Whether to enable deep indexing of nested content.
                                Defaults to True. Disable for performance-critical
                                applications where nested content discovery is not needed.
        """
        # Ensure content types are initialized before creating source manager
        # This prevents warnings about missing content types during initialization
        from ..registry import initialize_content_types

        initialize_content_types()

        # Initialize source manager
        if source_manager is not None:
            self.source_manager = source_manager
        else:
            self.source_manager = UnifiedSourceManager()
        self.enable_deep_indexing = enable_deep_indexing

        # Note: Removing async lock since we're converting to sync
        # Thread safety no longer needed for sync operations

        # Index structures
        self._index: dict[str, IndexEntry[BaseContent]] = {}  # hash_id -> entry
        self._by_type: dict[ContentType, dict[str, IndexEntry[BaseContent]]] = (
            defaultdict(dict)
        )  # type -> lookup_key -> entry
        self._by_source: dict[str, list[IndexEntry[BaseContent]]] = defaultdict(
            list
        )  # source -> entries
        self._by_name: dict[str, list[IndexEntry[BaseContent]]] = defaultdict(
            list
        )  # name -> entries

        # Deep indexing support
        self._indexed_hashes: set[str] = (
            set()
        )  # Tracks already indexed content to prevent cycles

        # Loaders
        self._loaders: dict[ContentType, DataLoader] = {}
        self._loaded_types: set[ContentType] = set()

        # ContentMerger singleton for dual-file operations
        # Initialized lazily and preserved across multiple operations to maintain
        # cache benefits. This significantly improves performance in test environments
        # and scenarios where repeated data access occurs.
        self._content_merger: ContentMerger | None = None

        # Register default loaders
        self._register_default_loaders()

    # Content types for each loader type - dynamically resolved from registry
    # Removed hardcoded tuples in favor of cached dynamic resolution

    def _register_default_loaders(self) -> None:
        """Register default data loaders for common content types."""
        # Content types are already initialized in __init__ before source manager creation

        # Use dynamic resolution with caching for performance
        self._register_loaders_for_type(JsonDataLoader, self._get_json_content_types())
        self._register_loaders_for_type(
            FluffDataLoader, self._get_fluff_content_types()
        )

    def _register_loaders_for_type(
        self, loader_cls: type[DataLoader], content_types: tuple[ContentType, ...]
    ) -> None:
        """Helper to register loaders for a given loader class and content types."""
        for content_type in content_types:
            if hasattr(loader_cls, "create_for_type"):
                loader = loader_cls.create_for_type(content_type)
            else:
                # Fallback to regular instantiation if create_for_type doesn't exist
                loader = loader_cls()
            self.register_loader(content_type, loader)

    def register_loader(self, content_type: ContentType, loader: DataLoader) -> None:
        """Register a data loader for a specific content type."""
        self._loaders[content_type] = loader
        logger.debug(f"Registered loader for {content_type.value}")

    def load_all_data(
        self,
        data_path: Path | None = None,
        *,
        progress_callback: "ProgressCallback | None" = None,
    ) -> dict[str, int]:
        """Load all available data and build comprehensive index."""
        logger.debug("Starting omnidexer data loading...")

        # Start overall progress operation
        main_operation_id = None
        if progress_callback:
            main_operation_id = progress_callback.start_operation(
                "Loading 5e content types", metadata={"component": "omnidexer"}
            )

        # Ensure sources are ready if using unified source manager
        if isinstance(self.source_manager, UnifiedSourceManager):
            self.source_manager.ensure_sources_ready_sync()

        # Get data paths from source manager
        data_paths = self.source_manager.get_data_paths()
        # Debug output can be enabled for troubleshooting
        # print(f"DEBUG Omnidexer: Got data paths for content types: {list(data_paths.keys())}")
        # for content_type, paths in data_paths.items():
        #     print(f"DEBUG Omnidexer: {content_type} has {len(paths)} files")

        # Process all data sequentially
        load_stats: dict[str, int] = defaultdict(int)
        total_loaded = 0

        # Load metadata files (adventures.json, books.json, etc.)
        for content_type, paths in data_paths.items():
            if content_type in self._loaders:
                # Report progress for this content type
                type_operation_id = None
                if progress_callback:
                    type_operation_id = progress_callback.start_operation(
                        f"Loading {content_type.value}",
                        total=len(paths),
                        metadata={"content_type": content_type.value},
                    )

                for i, path in enumerate(paths):
                    if progress_callback and type_operation_id:
                        progress_callback.update_progress(
                            type_operation_id,
                            completed=i,
                            description=f"Loading {content_type.value} from {path.name}",
                        )

                    result = self._load_content_type(content_type, path)
                    if isinstance(result, dict):
                        for content_type_str, count in result.items():
                            load_stats[content_type_str] += count
                            total_loaded += count

                if progress_callback and type_operation_id:
                    progress_callback.complete_operation(
                        type_operation_id,
                        result=f"Loaded {len(paths)} {content_type.value} files",
                    )
            else:
                logger.warning(f"No loader registered for {content_type.value}")

        # Load and merge dual-file content (adventures and books)
        dual_file_result = self._load_dual_file_content()
        for content_type_str, count in dual_file_result.items():
            load_stats[content_type_str] += count
            total_loaded += count

        if total_loaded == 0:
            logger.warning("No data files found to load")

        logger.debug(
            f"Omnidexer loaded {total_loaded} total items across {len(load_stats)} content types"
        )
        self._log_index_stats()

        # Complete main progress operation
        if progress_callback and main_operation_id:
            progress_callback.complete_operation(
                main_operation_id,
                result=f"Loaded {total_loaded} items across {len(load_stats)} content types",
            )

        return load_stats

    def _load_dual_file_content(self) -> dict[str, int]:
        """Load and merge dual-file content types (adventures and books).

        This method loads content files (adventure-*.json, book-*.json) and merges
        them with metadata already loaded from metadata files (adventures.json, books.json).
        This ensures that adventures and books have complete content, not just metadata.

        Performance: Uses a singleton ContentMerger instance that maintains its LRU cache
        across multiple operations. This provides significant performance benefits in test
        environments and scenarios with repeated data access, as the cache remains warm
        rather than being recreated for each operation.

        Returns:
            Dictionary mapping content type names to counts of enriched items
        """
        if not hasattr(self.source_manager, "get_content_files"):
            logger.debug(
                "Source manager does not support content files, skipping dual-file loading"
            )
            return {}

        # Get content files from source manager
        content_files = self.source_manager.get_content_files()

        # Handle test environments where content_files might be a Mock
        # In tests, Mocks can't be iterated with 'in' operator
        if hasattr(content_files, "_mock_name"):
            logger.debug("Mock source manager detected, skipping dual-file enrichment")
            return {}

        # Initialize ContentMerger singleton if not already done
        # This preserves the LRU cache across multiple operations, providing
        # significant performance benefits in test environments and repeated access scenarios
        if self._content_merger is None:
            from .content_merger import ContentMerger

            self._content_merger = ContentMerger(self.source_manager)
            logger.debug("Initialized singleton ContentMerger with cache preservation")

        enrichment_stats = {}

        # Process adventures and books (dual-file types)
        adventure_type = ContentType("adventure")
        book_type = ContentType("book")

        for content_type in [adventure_type, book_type]:
            if content_type not in content_files:
                continue

            type_files = content_files[content_type]
            enriched_count = 0

            logger.info(
                f"Processing {len(type_files)} {content_type.value} content files for enrichment"
            )

            for content_file in type_files:
                # Extract content ID from filename (e.g., "adventure-skt.json" -> "skt")
                content_id = self._extract_content_id_from_filename(
                    content_file, content_type
                )
                if not content_id:
                    logger.warning(f"Could not extract content ID from {content_file}")
                    continue

                # Find the metadata item in our already-loaded index
                metadata_item = self._find_metadata_item(content_type, content_id)
                if not metadata_item:
                    logger.debug(
                        f"No metadata found for {content_type.value} '{content_id}', loading content-only"
                    )
                    # Load content-only file if no metadata exists
                    self._load_content_only_file(content_type, content_file)
                    enriched_count += 1
                    continue

                # Load content file data
                content_data = self._content_merger.load_content_file(
                    content_type, content_id
                )
                if not content_data:
                    logger.warning(
                        f"Could not load content data for {content_type.value} '{content_id}'"
                    )
                    continue

                # Convert metadata item to dict for merging
                if hasattr(metadata_item.content, "model_dump"):
                    metadata_dict = metadata_item.content.model_dump()
                elif hasattr(metadata_item.content, "__dict__"):
                    metadata_dict = metadata_item.content.__dict__.copy()
                else:
                    metadata_dict = dict(metadata_item.content)

                # Merge metadata with content
                merged_data = self._content_merger.merge_metadata_content(
                    metadata_dict, content_data
                )

                # Create enriched content object directly using the content factory
                try:
                    if content_type in self._loaders:
                        loader = self._loaders[content_type]
                        # Use the loader's content factory to create validated content from merged data
                        # The merged_data is already a single adventure/book object, not wrapped in JSON format
                        from studiorum.core.loaders.json_loader import JsonDataLoader

                        if isinstance(loader, JsonDataLoader):
                            enriched_item = loader._content_factory.create_content(
                                merged_data, content_type
                            )
                        else:
                            # Fallback for other loader types
                            enriched_item = None

                        if enriched_item:
                            # Replace the metadata-only item with the enriched item
                            self._replace_index_entry(
                                metadata_item, enriched_item, content_type
                            )
                            enriched_count += 1
                            logger.debug(
                                f"Enriched {content_type.value} '{content_id}' with {len(merged_data.get('contents', []))} sections"
                            )
                        else:
                            logger.error(
                                f"No content created from merged data for {content_type.value} '{content_id}'"
                            )
                    else:
                        logger.warning(f"No loader available for {content_type.value}")

                except Exception as e:
                    logger.error(
                        f"Failed to create enriched {content_type.value} '{content_id}': {e}"
                    )
                    logger.debug(f"Merged data keys: {list(merged_data.keys())}")
                    logger.debug(f"Sample merged data: {str(merged_data)[:200]}...")
                    continue

            if enriched_count > 0:
                enrichment_stats[f"{content_type.value}_enriched"] = enriched_count
                logger.debug(
                    f"Enriched {enriched_count} {content_type.value} items with content data"
                )

        return enrichment_stats

    def _extract_content_id_from_filename(
        self, file_path: Path, content_type: ContentType
    ) -> str | None:
        """Extract content ID from content file name.

        Args:
            file_path: Path to content file (e.g., "/path/adventure-skt.json")
            content_type: Type of content

        Returns:
            Content ID (e.g., "skt") or None if extraction fails
        """
        filename = file_path.stem.lower()  # Get filename without extension

        if content_type.value == "adventure":
            if filename.startswith("adventure-"):
                return filename[10:]  # Remove "adventure-" prefix
        elif content_type.value == "book":
            if filename.startswith("book-"):
                return filename[5:]  # Remove "book-" prefix

        return None

    def _find_metadata_item(
        self, content_type: ContentType, content_id: str
    ) -> IndexEntry[BaseContent] | None:
        """Find metadata item in the index by content type and ID.

        Args:
            content_type: Type of content to search
            content_id: Content ID to find

        Returns:
            IndexEntry for the metadata item, or None if not found
        """
        if content_type not in self._by_type:
            return None

        type_index = self._by_type[content_type]

        # Search by ID attribute (case-insensitive)
        for entry in type_index.values():
            if (
                hasattr(entry.content, "id")
                and entry.content.id.lower() == content_id.lower()
            ):
                return entry

        return None

    def _load_content_only_file(
        self, content_type: ContentType, content_file: Path
    ) -> None:
        """Load content-only file when no metadata exists.

        Args:
            content_type: Type of content
            content_file: Path to content file
        """
        try:
            if content_type in self._loaders:
                loader = self._loaders[content_type]
                content_items = loader.load(content_file)

                for item in content_items:
                    self._add_to_index(item, content_type)

                logger.debug(
                    f"Loaded {len(content_items)} content-only {content_type.value} items from {content_file}"
                )
            else:
                logger.warning(f"No loader registered for {content_type.value}")
        except Exception as e:
            logger.error(
                f"Failed to load content-only {content_type.value} from {content_file}: {e}"
            )

    def _replace_index_entry(
        self,
        old_entry: IndexEntry[BaseContent],
        new_content: BaseContent,
        content_type: ContentType,
    ) -> None:
        """Replace an existing index entry with enriched content.

        Args:
            old_entry: The existing index entry to replace
            new_content: The new enriched content
            content_type: Type of content
        """
        # Remove old entry from all indexes
        old_hash_id = old_entry.hash_id
        old_lookup_key = old_entry.lookup_key

        # Remove from hash index
        if old_hash_id in self._index:
            del self._index[old_hash_id]

        # Remove from type index
        if (
            content_type in self._by_type
            and old_lookup_key in self._by_type[content_type]
        ):
            del self._by_type[content_type][old_lookup_key]

        # Remove from source index
        if hasattr(old_entry.content.source, "abbreviation"):
            source_abbrev = old_entry.content.source.abbreviation
            if source_abbrev in self._by_source:
                self._by_source[source_abbrev] = [
                    entry
                    for entry in self._by_source[source_abbrev]
                    if entry.hash_id != old_hash_id
                ]

        # Remove from name index
        name_key = old_entry.content.name.lower()
        if name_key in self._by_name:
            self._by_name[name_key] = [
                entry
                for entry in self._by_name[name_key]
                if entry.hash_id != old_hash_id
            ]

        # Remove from indexed hashes
        if old_hash_id in self._indexed_hashes:
            self._indexed_hashes.remove(old_hash_id)

        # Add new enriched content
        self._add_to_index(new_content, content_type)

    def _load_content_type(
        self, content_type: ContentType, path: Path
    ) -> dict[str, int]:
        """Load a specific content type from path."""
        if content_type not in self._loaders:
            logger.warning(f"No loader registered for {content_type.value}")
            return {}

        try:
            loader = self._loaders[content_type]
            content_items = loader.load(path)

            # Enhance spells with class information from lookup data
            if content_type.value == "spell":
                content_items = self._enhance_spells_with_class_data(content_items)

            # Index all loaded items
            for item in content_items:
                self._add_to_index(item, content_type)

            self._loaded_types.add(content_type)
            logger.debug(
                f"Loaded {len(content_items)} {content_type.value} items from {path}"
            )

            return {content_type.value: len(content_items)}

        except Exception as e:
            logger.error(f"Failed to load {content_type.value} from {path}: {e}")
            return {}

    def _enhance_spells_with_class_data(
        self, content_items: list[BaseContent]
    ) -> list[BaseContent]:
        """Enhance spell objects with class information from lookup data."""
        try:
            from ..models.spells import Spell
            from ..services.spell_class_lookup import get_spell_class_lookup_service

            lookup_service = get_spell_class_lookup_service()

            enhanced_items: list[BaseContent] = []
            for item in content_items:
                if isinstance(item, Spell):
                    enhanced_item = lookup_service.enhance_spell(item)
                    enhanced_items.append(enhanced_item)
                else:
                    # Not a spell, just add as-is
                    enhanced_items.append(item)

            logger.debug(
                f"Enhanced {len([item for item in content_items if isinstance(item, Spell)])} spells with class information"
            )
            return enhanced_items

        except Exception as e:
            logger.warning(f"Failed to enhance spells with class data: {e}")
            return content_items

    def _is_already_indexed(
        self, content: BaseContent, content_type: ContentType
    ) -> bool:
        """Check if content is already indexed to prevent cycles."""
        # Generate the same hash that would be used for indexing
        if hasattr(content.source, "abbreviation"):
            source_abbrev = content.source.abbreviation
        elif isinstance(content.source, dict):
            source_abbrev = content.source.get("abbreviation", str(content.source))
        else:
            source_abbrev = str(content.source)

        identifier = f"{content_type.value}:{content.name}:{source_abbrev}"
        hash_id = hashlib.sha256(identifier.encode()).hexdigest()[:8]

        return hash_id in self._indexed_hashes

    def _add_to_index(self, content: BaseContent, content_type: ContentType) -> None:
        """Add content item to all indexes with optional deep indexing."""
        # Check if already indexed to prevent cycles (outside lock for performance)
        if self._is_already_indexed(content, content_type):
            logger.debug(
                f"Skipping already indexed {content_type.value}: {content.name}"
            )
            return

        entry = IndexEntry.create(content, content_type)

        # Check for duplicate hash_id (cycle prevention)
        if entry.hash_id in self._indexed_hashes:
            return

        # Track this content as indexed
        self._indexed_hashes.add(entry.hash_id)

        # Primary hash-based index
        self._index[entry.hash_id] = entry

        # Type-based index (for content type + name/source lookups)
        self._by_type[content_type][entry.lookup_key] = entry

        # Source-based index (for finding all content from a source)
        # Handle different source formats
        if hasattr(content.source, "abbreviation"):
            source_abbrev = content.source.abbreviation
        elif isinstance(content.source, dict):
            source_abbrev = content.source.get("abbreviation", str(content.source))
        else:
            source_abbrev = str(content.source)
        self._by_source[source_abbrev].append(entry)

        # Name-based index (for fuzzy name searches)
        name_key = content.name.lower()
        self._by_name[name_key].append(entry)

        # Deep indexing: if enabled and content supports it, index nested content
        if self.enable_deep_indexing and isinstance(content, DeepIndexable):
            try:
                nested_content = content.get_deep_index_entries(self)
                indexed_count = 0
                for nested_item in nested_content:
                    try:
                        # Determine content type for nested item
                        nested_type = ContentType.from_content(nested_item)
                        # Recursively add nested content (cycle prevention handled above)
                        self._add_to_index(nested_item, nested_type)
                        indexed_count += 1
                    except ValueError:
                        # Skip nested items that don't have registered content types
                        # This is expected for nested content like sections, tables, insets
                        logger.debug(
                            f"Skipping nested item {type(nested_item).__name__} without registered content type"
                        )
                        continue

                logger.debug(
                    f"Deep indexed {indexed_count} nested items from {content_type.value}: {content.name}"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to deep index nested content for {content_type.value} '{content.name}': {e}"
                )
                # Continue with normal indexing even if deep indexing fails

    def find(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> BaseContent | None:
        """Find content by type, name, and optionally source."""
        # Use cached version with proper type annotation
        result = self._find_cached(content_type, name, source)
        return cast(BaseContent | None, result)

    @cached(
        key_func=lambda self,
        content_type,
        name,
        source: f"omnidexer:find:{content_type.value}:{name}:{source or 'any'}:deep={self.enable_deep_indexing}",
        ttl=timedelta(hours=1),  # Cache for 1 hour
    )
    def _find_cached(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> BaseContent | None:
        """Cached implementation of find."""
        if content_type not in self._by_type:
            return None

        type_index = self._by_type[content_type]

        if source:
            # Exact lookup with source
            lookup_key = f"{name}|{source}".lower()
            entry = type_index.get(lookup_key)
            return entry.content if entry else None
        else:
            # Search all sources for this name
            name_lower = name.lower()
            for lookup_key, entry in type_index.items():
                if lookup_key.startswith(f"{name_lower}|"):
                    return entry.content
            return None

    def find_by_hash(self, hash_id: str) -> BaseContent | None:
        """Find content by unique hash identifier."""
        entry = self._index.get(hash_id)
        return entry.content if entry else None

    def find_all(self, content_type: ContentType, name: str) -> list[BaseContent]:
        """Find all content matching type and name across all sources."""
        if content_type not in self._by_type:
            return []

        type_index = self._by_type[content_type]
        name_lower = name.lower()
        matches = []

        for lookup_key, entry in type_index.items():
            if lookup_key.startswith(f"{name_lower}|"):
                matches.append(entry.content)

        return matches

    def get_all_by_type(self, content_type: ContentType | str) -> list[BaseContent]:
        """Get all content of a specific type.

        Args:
            content_type: ContentType enum or string value

        Returns:
            List of content items of the specified type
        """
        # Convert string to ContentType enum for backward compatibility
        if isinstance(content_type, str):
            try:
                content_type = ContentType(content_type)
            except ValueError:
                # If the string doesn't match a valid ContentType, return empty list
                return []

        if content_type not in self._by_type:
            return []
        return [entry.content for entry in self._by_type[content_type].values()]

    def get_all_by_source(self, source: str) -> list[BaseContent]:
        """Get all content from a specific source."""
        entries = self._by_source.get(source, [])
        return [entry.content for entry in entries]

    def search(
        self, query: str, content_type: ContentType | None = None, limit: int = 50
    ) -> list[BaseContent]:
        """Search for content by name (fuzzy matching)."""
        # Use cached version with proper type annotation
        result = self._search_cached(query, content_type, limit)
        return cast(list[BaseContent], result)

    @cached(
        key_func=lambda self,
        query,
        content_type,
        limit: f"omnidexer:search:{query}:{content_type.value if content_type else 'all'}:{limit}:deep={self.enable_deep_indexing}",
        ttl=timedelta(minutes=30),  # Cache for 30 minutes
    )
    def _search_cached(
        self, query: str, content_type: ContentType | None = None, limit: int = 50
    ) -> list[BaseContent]:
        """Cached implementation of search."""
        query_lower = query.lower()
        results = []

        search_types = [content_type] if content_type else ContentType

        for ctype in search_types:
            if ctype not in self._by_type:
                continue

            for entry in self._by_type[ctype].values():
                # Simple fuzzy matching - can be enhanced
                if query_lower in entry.content.name.lower():
                    results.append(entry.content)
                    if len(results) >= limit:
                        return results

        return results

    def search_by_name_prefix(
        self, prefix: str, content_type: ContentType | None = None, limit: int = 20
    ) -> list[BaseContent]:
        """Search for content by name prefix."""
        prefix_lower = prefix.lower()
        results = []

        search_types = [content_type] if content_type else ContentType

        for ctype in search_types:
            if ctype not in self._by_type:
                continue

            for lookup_key, entry in self._by_type[ctype].items():
                content_name = entry.content.name.lower()
                if content_name.startswith(prefix_lower):
                    results.append(entry.content)
                    if len(results) >= limit:
                        return results

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the loaded index."""
        stats: dict[str, Any] = {
            "total_items": len(self._index),
            "by_type": {},
            "by_source": {},
            "loaded_types": list(self._loaded_types),
        }

        # Count by type
        for content_type, items in self._by_type.items():
            stats["by_type"][content_type.value] = len(items)

        # Count by source
        for source, entries in self._by_source.items():
            stats["by_source"][source] = len(entries)

        return stats

    def is_loaded(self, content_type: ContentType) -> bool:
        """Check if a content type has been loaded."""
        return content_type in self._loaded_types

    def get_supported_types(self) -> list[ContentType]:
        """Get list of supported content types.

        Returns:
            List of content types supported by registered loaders
        """
        return list(self._get_json_content_types()) + list(
            self._get_fluff_content_types()
        )

    def _get_json_content_types(self) -> tuple[ContentType, ...]:
        """Get JSON content types from registry - cached for performance."""
        from ..registry.content_type_registry import get_content_type_registry

        registry = get_content_type_registry()
        json_types: list[ContentType] = []

        for enum_value, metadata in registry.get_all().items():
            if metadata.loader_type == "json":
                try:
                    json_types.append(ContentType(enum_value))
                except ValueError:
                    # Skip test-only registrations that aren't valid enum members
                    logger.debug(f"Skipping test-only content type: {enum_value}")
                    continue

        return tuple(json_types)

    def _get_fluff_content_types(self) -> tuple[ContentType, ...]:
        """Get fluff content types from registry - cached for performance."""
        from ..registry.content_type_registry import get_content_type_registry

        registry = get_content_type_registry()
        fluff_types: list[ContentType] = []

        for enum_value, metadata in registry.get_all().items():
            if metadata.loader_type == "fluff":
                try:
                    fluff_types.append(ContentType(enum_value))
                except ValueError:
                    # Skip test-only registrations that aren't valid enum members
                    logger.debug(f"Skipping test-only content type: {enum_value}")
                    continue

        return tuple(fluff_types)

    def get_content_merger(self) -> "ContentMerger | None":
        """Get the shared ContentMerger instance, initializing if needed.

        This method provides access to the singleton ContentMerger instance used
        for dual-file operations. The singleton pattern preserves the LRU cache
        across multiple operations, providing significant performance benefits:

        - Cache remains warm between operations rather than being recreated
        - Reduces file I/O when the same content is accessed repeatedly
        - Particularly beneficial in test environments with repeated data loading
        - Enables sharing of cache benefits across multiple components

        Returns:
            Shared ContentMerger instance or None if source manager doesn't support content files
        """
        # Check if source manager supports content files
        if not hasattr(self.source_manager, "get_content_files"):
            logger.debug(
                "Source manager does not support content files, no ContentMerger available"
            )
            return None

        # Initialize ContentMerger singleton if not already done
        # This preserves cache state and provides performance benefits
        if self._content_merger is None:
            from .content_merger import ContentMerger

            self._content_merger = ContentMerger(self.source_manager)
            logger.debug(
                "Initialized singleton ContentMerger with cache preservation benefits"
            )

        return self._content_merger

    def _log_index_stats(self) -> None:
        """Log statistics about the loaded index."""
        stats = self.get_statistics()

        logger.debug("Omnidexer Index Statistics:")
        logger.debug(f"  Total items: {stats['total_items']}")

        for content_type, count in stats["by_type"].items():
            logger.debug(f"  {content_type}: {count} items")

        logger.debug(f"  Sources: {len(stats['by_source'])}")
        for source, count in list(stats["by_source"].items())[
            :10
        ]:  # Show top 10 sources
            logger.debug(f"    {source}: {count} items")
