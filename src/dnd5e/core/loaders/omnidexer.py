"""Omnidexer system for comprehensive content indexing."""

import asyncio
import hashlib
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..cache import cached
from ..interfaces import DeepIndexable
from ..logging import get_logger
from ..models.content import BaseContent, ContentType
from .base import DataLoader, SourceManager
from .configurable_source_manager import ConfigurableSourceManager
from .fluff_loader import FluffDataLoader
from .json_loader import JsonDataLoader

logger = get_logger(__name__)


class IndexEntry(BaseModel):
    """Represents an indexed content entry with validation."""

    content: BaseContent = Field(description="The content being indexed")
    content_type: ContentType = Field(description="Type of the content")
    hash_id: str = Field(
        min_length=8, max_length=8, description="8-character unique hash identifier"
    )
    lookup_key: str = Field(
        min_length=1, description="Lowercase lookup key for searches"
    )

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
    def create(cls, content: BaseContent, content_type: ContentType) -> "IndexEntry":
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
    Central indexing system for all D&D content with deep content discovery.

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

    Example:
        >>> omnidexer = Omnidexer(enable_deep_indexing=True)
        >>> await omnidexer.load_all_data()  # doctest: +SKIP
        >>> # Find primary content
        >>> fighter = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")  # doctest: +SKIP
        >>> # Find nested content (requires deep indexing)
        >>> action_surge = omnidexer.find(ContentType.CLASS_FEATURE, "Action Surge", "PHB")  # doctest: +SKIP
        >>> sections = omnidexer.find_all(ContentType.ADVENTURE_SECTION)  # doctest: +SKIP
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
                          uses ConfigurableSourceManager with default sources.
            enable_deep_indexing: Whether to enable deep indexing of nested content.
                                Defaults to True. Disable for performance-critical
                                applications where nested content discovery is not needed.
        """
        self.source_manager = source_manager or ConfigurableSourceManager()
        self.enable_deep_indexing = enable_deep_indexing

        # Index structures
        self._index: dict[str, IndexEntry] = {}  # hash_id -> entry
        self._by_type: dict[ContentType, dict[str, IndexEntry]] = defaultdict(
            dict
        )  # type -> lookup_key -> entry
        self._by_source: dict[str, list[IndexEntry]] = defaultdict(
            list
        )  # source -> entries
        self._by_name: dict[str, list[IndexEntry]] = defaultdict(
            list
        )  # name -> entries

        # Deep indexing support
        self._indexed_hashes: set[str] = (
            set()
        )  # Tracks already indexed content to prevent cycles

        # Loaders
        self._loaders: dict[ContentType, DataLoader] = {}
        self._loaded_types: set[ContentType] = set()

        # Register default loaders
        self._register_default_loaders()

    # New: Define content types for each loader type
    _JSON_CONTENT_TYPES = (
        ContentType.SPELL,
        ContentType.CREATURE,
        ContentType.ITEM,
        ContentType.ADVENTURE,
        ContentType.BOOK,
        ContentType.FEAT,
        ContentType.RACE,
        ContentType.BACKGROUND,
        ContentType.CLASS,
        ContentType.VEHICLE,
    )

    _FLUFF_CONTENT_TYPES = (
        ContentType.SPELL_FLUFF,
        ContentType.CREATURE_FLUFF,
        ContentType.ITEM_FLUFF,
    )

    def _register_default_loaders(self) -> None:
        """Register default data loaders for common content types."""
        self._register_loaders_for_type(JsonDataLoader, self._JSON_CONTENT_TYPES)
        self._register_loaders_for_type(FluffDataLoader, self._FLUFF_CONTENT_TYPES)

    def _register_loaders_for_type(
        self, loader_cls: type[DataLoader], content_types: tuple[ContentType, ...]
    ) -> None:
        """Helper to register loaders for a given loader class and content types."""
        for content_type in content_types:
            loader = loader_cls.create_for_type(content_type)  # type: ignore[attr-defined]
            self.register_loader(content_type, loader)

    def register_loader(self, content_type: ContentType, loader: DataLoader) -> None:
        """Register a data loader for a specific content type."""
        self._loaders[content_type] = loader
        logger.info(f"Registered loader for {content_type.value}")

    async def load_all_data(self, data_path: Path | None = None) -> dict[str, int]:
        """Load all available data and build comprehensive index."""
        logger.info("Starting omnidexer data loading...")

        # Ensure sources are ready if using configurable source manager
        if isinstance(self.source_manager, ConfigurableSourceManager):
            await self.source_manager.ensure_sources_ready()

        # Get data paths from source manager
        data_paths = self.source_manager.get_data_paths()
        # Debug output can be enabled for troubleshooting
        # print(f"DEBUG Omnidexer: Got data paths for content types: {list(data_paths.keys())}")
        # for content_type, paths in data_paths.items():
        #     print(f"DEBUG Omnidexer: {content_type} has {len(paths)} files")

        # Create loading tasks
        load_tasks = []
        for content_type, paths in data_paths.items():
            if content_type in self._loaders:
                for path in paths:
                    task = self._load_content_type(content_type, path)
                    load_tasks.append(task)
            else:
                logger.warning(f"No loader registered for {content_type.value}")

        if not load_tasks:
            logger.warning("No data files found to load")
            return {}

        # Execute all loading tasks concurrently
        logger.info(f"Starting {len(load_tasks)} loading tasks")
        results = await asyncio.gather(*load_tasks, return_exceptions=True)

        # Process results
        load_stats: dict[str, int] = defaultdict(int)
        total_loaded = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Loading task failed: {result}")
            elif isinstance(result, dict):
                for content_type_str, count in result.items():
                    load_stats[content_type_str] += count
                    total_loaded += count

        logger.info(
            f"Omnidexer loaded {total_loaded} total items across {len(load_stats)} content types"
        )
        self._log_index_stats()

        return load_stats

    async def _load_content_type(
        self, content_type: ContentType, path: Path
    ) -> dict[str, int]:
        """Load a specific content type from path."""
        if content_type not in self._loaders:
            logger.warning(f"No loader registered for {content_type.value}")
            return {}

        try:
            loader = self._loaders[content_type]
            content_items = await loader.load(path)

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
        # Check if already indexed to prevent cycles
        if self._is_already_indexed(content, content_type):
            logger.debug(
                f"Skipping already indexed {content_type.value}: {content.name}"
            )
            return

        entry = IndexEntry.create(content, content_type)

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
                for nested_item in nested_content:
                    # Determine content type for nested item
                    nested_type = ContentType.from_content(nested_item)
                    # Recursively add nested content (cycle prevention handled above)
                    self._add_to_index(nested_item, nested_type)

                logger.debug(
                    f"Deep indexed {len(nested_content)} nested items from {content_type.value}: {content.name}"
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
        # Use cached version
        return self._find_cached(content_type, name, source)  # type: ignore[no-any-return]

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
            # Type cast needed due to Any type in IndexEntry.content
            return entry.content if entry else None  # type: ignore[no-any-return]
        else:
            # Search all sources for this name
            name_lower = name.lower()
            for lookup_key, entry in type_index.items():
                if lookup_key.startswith(f"{name_lower}|"):
                    # Type cast needed due to Any type in IndexEntry.content
                    return entry.content  # type: ignore[no-any-return]
            return None

    def find_by_hash(self, hash_id: str) -> BaseContent | None:
        """Find content by unique hash identifier."""
        entry = self._index.get(hash_id)
        # Type cast needed due to Any type in IndexEntry.content
        return entry.content if entry else None  # type: ignore[no-any-return]

    def find_all(self, content_type: ContentType, name: str) -> list[BaseContent]:
        """Find all content matching type and name across all sources."""
        if content_type not in self._by_type:
            return []

        type_index = self._by_type[content_type]
        name_lower = name.lower()
        matches = []

        for lookup_key, entry in type_index.items():
            if lookup_key.startswith(f"{name_lower}|"):
                # Type cast needed due to Any type in IndexEntry.content
                matches.append(entry.content)  # type: ignore[arg-type]

        return matches

    def get_all_by_type(self, content_type: ContentType) -> list[BaseContent]:
        """Get all content of a specific type."""
        if content_type not in self._by_type:
            return []
        # Type cast needed due to Any type in IndexEntry.content
        return [entry.content for entry in self._by_type[content_type].values()]  # type: ignore[misc]

    def get_all_by_source(self, source: str) -> list[BaseContent]:
        """Get all content from a specific source."""
        entries = self._by_source.get(source, [])
        # Type cast needed due to Any type in IndexEntry.content
        return [entry.content for entry in entries]  # type: ignore[misc]

    def search(
        self, query: str, content_type: ContentType | None = None, limit: int = 50
    ) -> list[BaseContent]:
        """Search for content by name (fuzzy matching)."""
        # Use cached version
        return self._search_cached(query, content_type, limit)  # type: ignore[no-any-return]

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
                    # Type cast needed due to Any type in IndexEntry.content
                    results.append(entry.content)  # type: ignore[arg-type]
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
                    # Type cast needed due to Any type in IndexEntry.content
                    results.append(entry.content)  # type: ignore[arg-type]
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

    def _log_index_stats(self) -> None:
        """Log statistics about the loaded index."""
        stats = self.get_statistics()

        logger.info("Omnidexer Index Statistics:")
        logger.info(f"  Total items: {stats['total_items']}")

        for content_type, count in stats["by_type"].items():
            logger.info(f"  {content_type}: {count} items")

        logger.info(f"  Sources: {len(stats['by_source'])}")
        for source, count in list(stats["by_source"].items())[
            :10
        ]:  # Show top 10 sources
            logger.info(f"    {source}: {count} items")
