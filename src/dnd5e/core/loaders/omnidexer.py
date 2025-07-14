"""Omnidexer system for comprehensive content indexing."""

import asyncio
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..config.settings import get_logger
from ..models.content import BaseContent, ContentType
from .base import DataLoader, SourceManager
from .configurable_source_manager import ConfigurableSourceManager
from .fluff_loader import FluffDataLoader
from .json_loader import JsonDataLoader

logger = get_logger(__name__)


@dataclass
class IndexEntry:
    """Represents an indexed content entry."""

    content: BaseContent
    content_type: ContentType
    hash_id: str
    lookup_key: str

    @classmethod
    def create(cls, content: BaseContent, content_type: ContentType) -> "IndexEntry":
        """Create an index entry from content."""
        # Handle different source formats
        if hasattr(content.source, "abbreviation"):
            source_abbrev = content.source.abbreviation
        elif isinstance(content.source, dict):
            source_abbrev = content.source.get("abbreviation", str(content.source))
        else:
            source_abbrev = str(content.source)

        # Generate unique hash
        identifier = f"{content_type.value}:{content.name}:{source_abbrev}"
        hash_id = hashlib.md5(identifier.encode()).hexdigest()[:8]

        # Generate lookup key (lowercase for case-insensitive searches)
        lookup_key = f"{content.name}|{source_abbrev}".lower()

        return cls(
            content=content,
            content_type=content_type,
            hash_id=hash_id,
            lookup_key=lookup_key,
        )


class Omnidexer:
    """Central indexing system for all D&D content, inspired by 5etools."""

    def __init__(self, source_manager: Optional[SourceManager] = None):
        self.source_manager = source_manager or ConfigurableSourceManager()

        # Index structures
        self._index: Dict[str, IndexEntry] = {}  # hash_id -> entry
        self._by_type: Dict[ContentType, Dict[str, IndexEntry]] = defaultdict(
            dict
        )  # type -> lookup_key -> entry
        self._by_source: Dict[str, List[IndexEntry]] = defaultdict(
            list
        )  # source -> entries
        self._by_name: Dict[str, List[IndexEntry]] = defaultdict(
            list
        )  # name -> entries

        # Loaders
        self._loaders: Dict[ContentType, DataLoader] = {}
        self._loaded_types: Set[ContentType] = set()

        # Register default loaders
        self._register_default_loaders()

    def _register_default_loaders(self):
        """Register default data loaders for common content types."""
        loaders = {
            ContentType.SPELL: JsonDataLoader.create_for_type(ContentType.SPELL),
            ContentType.CREATURE: JsonDataLoader.create_for_type(ContentType.CREATURE),
            ContentType.ITEM: JsonDataLoader.create_for_type(ContentType.ITEM),
            ContentType.ADVENTURE: JsonDataLoader.create_for_type(
                ContentType.ADVENTURE
            ),
            ContentType.BOOK: JsonDataLoader.create_for_type(ContentType.BOOK),
            ContentType.FEAT: JsonDataLoader.create_for_type(ContentType.FEAT),
            ContentType.RACE: JsonDataLoader.create_for_type(ContentType.RACE),
            ContentType.BACKGROUND: JsonDataLoader.create_for_type(
                ContentType.BACKGROUND
            ),
            ContentType.CLASS: JsonDataLoader.create_for_type(ContentType.CLASS),
            # Fluff loaders
            ContentType.SPELL_FLUFF: FluffDataLoader.create_for_type(
                ContentType.SPELL_FLUFF
            ),
            ContentType.CREATURE_FLUFF: FluffDataLoader.create_for_type(
                ContentType.CREATURE_FLUFF
            ),
            ContentType.ITEM_FLUFF: FluffDataLoader.create_for_type(
                ContentType.ITEM_FLUFF
            ),
        }

        for content_type, loader in loaders.items():
            self.register_loader(content_type, loader)

    def register_loader(self, content_type: ContentType, loader: DataLoader):
        """Register a data loader for a specific content type."""
        self._loaders[content_type] = loader
        logger.info(f"Registered loader for {content_type.value}")

    async def load_all_data(self, data_path: Optional[Path] = None) -> Dict[str, int]:
        """Load all available data and build comprehensive index."""
        logger.info("Starting omnidexer data loading...")

        # Ensure sources are ready if using configurable source manager
        if isinstance(self.source_manager, ConfigurableSourceManager):
            await self.source_manager.ensure_sources_ready()

        # Get data paths from source manager
        data_paths = self.source_manager.get_data_paths()

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
        load_stats = defaultdict(int)
        total_loaded = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Loading task failed: {result}")
            elif isinstance(result, dict):
                for content_type, count in result.items():
                    load_stats[content_type] += count
                    total_loaded += count

        logger.info(
            f"Omnidexer loaded {total_loaded} total items across {len(load_stats)} content types"
        )
        self._log_index_stats()

        return dict(load_stats)

    async def _load_content_type(
        self, content_type: ContentType, path: Path
    ) -> Dict[str, int]:
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

    def _add_to_index(self, content: BaseContent, content_type: ContentType):
        """Add content item to all indexes."""
        entry = IndexEntry.create(content, content_type)

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

    def find(
        self, content_type: ContentType, name: str, source: Optional[str] = None
    ) -> Optional[BaseContent]:
        """Find content by type, name, and optionally source."""
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

    def find_by_hash(self, hash_id: str) -> Optional[BaseContent]:
        """Find content by unique hash identifier."""
        entry = self._index.get(hash_id)
        return entry.content if entry else None

    def find_all(self, content_type: ContentType, name: str) -> List[BaseContent]:
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

    def get_all_by_type(self, content_type: ContentType) -> List[BaseContent]:
        """Get all content of a specific type."""
        if content_type not in self._by_type:
            return []
        return [entry.content for entry in self._by_type[content_type].values()]

    def get_all_by_source(self, source: str) -> List[BaseContent]:
        """Get all content from a specific source."""
        entries = self._by_source.get(source, [])
        return [entry.content for entry in entries]

    def search(
        self, query: str, content_type: Optional[ContentType] = None, limit: int = 50
    ) -> List[BaseContent]:
        """Search for content by name (fuzzy matching)."""
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
        self, prefix: str, content_type: Optional[ContentType] = None, limit: int = 20
    ) -> List[BaseContent]:
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

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loaded index."""
        stats = {
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

    def _log_index_stats(self):
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
