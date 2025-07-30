"""Configurable source manager that integrates with the new content source system."""

from pathlib import Path
from typing import Any

from ..config.sources import get_content_config
from ..logging import get_logger
from ..models.content import ContentType
from ..sources import ContentSourceManager
from .base import SourceManager

logger = get_logger(__name__)


class ConfigurableSourceManager(SourceManager):
    """Source manager that uses configurable content sources.

    This class implements 5etools dual-file architecture for adventures and books:

    **Metadata Files:**
    - `adventures.json`: Contains lightweight adventure metadata (names, IDs, TOC structure)
    - `books.json`: Contains lightweight book metadata (names, IDs, TOC structure)
    - Loaded by omnidexer during startup for catalog/index population
    - Provide structure and metadata but no actual content entries

    **Content Files:**
    - `adventure-{id}.json`: Contains full adventure content data
    - `book-{id}.json`: Contains full book content data
    - Loaded on-demand when specific content is requested
    - Provide actual entry data but minimal metadata
    - ID is lowercase version of metadata ID (e.g., "CoS" → "adventure-cos.json")

    **Loading Strategy:**
    1. Omnidexer loads only metadata files to build content catalog
    2. ContentResolver loads content files on-demand when adventures/books are accessed
    3. ContentMerger combines metadata structure with content data at runtime

    **File Pattern Examples:**
    ```
    /data/adventures.json          # Metadata for all adventures
    /data/adventure/adventure-cos.json    # Content for Curse of Strahd
    /data/books.json               # Metadata for all books
    /data/book/book-phb.json      # Content for Player's Handbook
    ```

    This prevents the duplicate loading issue where both metadata and content
    files were being loaded as separate adventures, resulting in empty metadata
    entries and unreachable content entries.
    """

    def __init__(self) -> None:
        """Initialize with content configuration."""
        self.config = get_content_config()
        self.content_manager = ContentSourceManager(self.config)
        self._data_paths_cache: dict[ContentType, list[Path]] | None = None
        self._source_info_cache: dict[str, dict[str, Any]] | None = None

    async def ensure_sources_ready(self) -> None:
        """Ensure all content sources are available and indexed."""
        await self.content_manager.ensure_all_sources()
        await self.content_manager.build_content_index()

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to data files organized by content type.

        For adventures and books, this returns only metadata files to prevent
        duplicate loading. Content files are loaded on-demand by ContentResolver.
        Other content types use the original pattern-based discovery.
        """
        if self._data_paths_cache is not None:
            return self._data_paths_cache

        # Check if content index is built
        if not self.content_manager._index_built:
            logger.warning(
                "Content index not built. Run async ensure_sources_ready() first."
            )
            return {}

        # Start with metadata files for adventures and books
        data_paths = self.get_metadata_files()

        # Map content types to file patterns for other content types
        content_patterns = {
            ContentType.SPELL: ["spell", "spells"],
            ContentType.CREATURE: ["bestiary", "monster", "creatures"],
            ContentType.ITEM: ["item", "items"],
            ContentType.CLASS: ["class", "classes"],
            ContentType.BACKGROUND: ["background", "backgrounds"],
            ContentType.FEAT: ["feat", "feats"],
            ContentType.RACE: ["race", "races"],
            # Fluff content patterns - these should be checked first
            ContentType.SPELL_FLUFF: ["fluff-spell", "spell-fluff"],
            ContentType.CREATURE_FLUFF: [
                "fluff-bestiary",
                "fluff-monster",
                "bestiary-fluff",
                "monster-fluff",
            ],
            ContentType.ITEM_FLUFF: ["fluff-item", "item-fluff"],
        }

        all_files = self.content_manager.get_all_content_files()

        # Track files already assigned to avoid conflicts
        assigned_files = set()

        # Organize content types by priority
        fluff_content_types = [
            ct for ct in content_patterns.keys() if ct.value.endswith("Fluff")
        ]
        regular_content_types = [
            ct for ct in content_patterns.keys() if not ct.value.endswith("Fluff")
        ]
        all_content_types = fluff_content_types + regular_content_types

        # PHASE 1: Assign files based on directory names (high confidence)
        for content_type in all_content_types:
            patterns = content_patterns[content_type]
            type_paths = []

            # Search through all source files for directory matches
            for source_name, files in all_files.items():
                for file_path in files:
                    # Skip files already assigned or should be filtered
                    if (
                        file_path in assigned_files
                        or self._should_skip_file_at_discovery(file_path)
                    ):
                        continue

                    file_name = file_path.name.lower()
                    parent_name = file_path.parent.name.lower()

                    # Check parent directory names
                    if any(pattern in parent_name for pattern in patterns):
                        # Special case: exclude monsterfeatures from feat matching
                        if (
                            content_type == ContentType.FEAT
                            and "monsterfeature" in file_name
                        ):
                            continue
                        type_paths.append(file_path)
                        assigned_files.add(file_path)

            if type_paths:
                data_paths[content_type] = type_paths

        # PHASE 2: Assign remaining files based on filename patterns (lower confidence)
        for content_type in all_content_types:
            patterns = content_patterns[content_type]
            type_paths = data_paths.get(content_type, [])

            # Search through all source files for filename matches
            for source_name, files in all_files.items():
                for file_path in files:
                    # Skip files already assigned or should be filtered
                    if (
                        file_path in assigned_files
                        or self._should_skip_file_at_discovery(file_path)
                    ):
                        continue

                    file_name = file_path.name.lower()

                    # Check filename patterns
                    if any(pattern in file_name for pattern in patterns):
                        # Special case: exclude monsterfeatures from feat matching
                        if (
                            content_type == ContentType.FEAT
                            and "monsterfeature" in file_name
                        ):
                            continue
                        type_paths.append(file_path)
                        assigned_files.add(file_path)

            if type_paths:
                data_paths[content_type] = type_paths

        self._data_paths_cache = data_paths

        logger.info("Discovered data files (metadata for adventures/books):")
        for content_type, paths in data_paths.items():
            logger.info(f"  {content_type.value}: {len(paths)} files")

        return data_paths

    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation to full source information."""
        if self._source_info_cache is None:
            self._build_source_info_cache()

        return (
            self._source_info_cache.get(source_abbrev)
            if self._source_info_cache
            else None
        )

    def get_source_priority(self, source_abbrev: str) -> int:
        """Get priority for a source (lower numbers = higher priority)."""
        # Official D&D 5e sources get higher priority
        official_sources = {
            "PHB": 1,  # Player's Handbook
            "MM": 2,  # Monster Manual
            "DMG": 3,  # Dungeon Master's Guide
            "SCAG": 10,  # Sword Coast Adventurer's Guide
            "VGM": 11,  # Volo's Guide to Monsters
            "XGE": 12,  # Xanathar's Guide to Everything
            "MTF": 13,  # Mordenkainen's Tome of Foes
            "TCE": 14,  # Tasha's Cauldron of Everything
            "MPMM": 15,  # Mordenkainen Presents: Monsters of the Multiverse
            "FTD": 16,  # Fizban's Treasury of Dragons
            "SAiS": 17,  # Spelljammer: Adventures in Space
            "BMT": 18,  # The Book of Many Things
        }

        return official_sources.get(
            source_abbrev, 1000
        )  # High number for unknown sources

    def _build_source_info_cache(self) -> None:
        """Build comprehensive source information from all configured sources."""
        source_info = {}

        # Add comprehensive D&D 5e source information
        official_sources = {
            "PHB": {"name": "Player's Handbook", "official": True, "year": 2014},
            "MM": {"name": "Monster Manual", "official": True, "year": 2014},
            "DMG": {"name": "Dungeon Master's Guide", "official": True, "year": 2014},
            "SCAG": {
                "name": "Sword Coast Adventurer's Guide",
                "official": True,
                "year": 2015,
            },
            "VGM": {"name": "Volo's Guide to Monsters", "official": True, "year": 2016},
            "XGE": {
                "name": "Xanathar's Guide to Everything",
                "official": True,
                "year": 2017,
            },
            "MTF": {
                "name": "Mordenkainen's Tome of Foes",
                "official": True,
                "year": 2018,
            },
            "GGR": {
                "name": "Guildmasters' Guide to Ravnica",
                "official": True,
                "year": 2018,
            },
            "AI": {"name": "Acquisitions Incorporated", "official": True, "year": 2019},
            "ERLW": {
                "name": "Eberron: Rising from the Last War",
                "official": True,
                "year": 2019,
            },
            "EGW": {
                "name": "Explorer's Guide to Wildemount",
                "official": True,
                "year": 2020,
            },
            "MOT": {
                "name": "Mythic Odysseys of Theros",
                "official": True,
                "year": 2020,
            },
            "IDRotF": {
                "name": "Icewind Dale: Rime of the Frostmaiden",
                "official": True,
                "year": 2020,
            },
            "TCE": {
                "name": "Tasha's Cauldron of Everything",
                "official": True,
                "year": 2020,
            },
            "VRGtR": {
                "name": "Van Richten's Guide to Ravenloft",
                "official": True,
                "year": 2021,
            },
            "WBtW": {
                "name": "The Wild Beyond the Witchlight",
                "official": True,
                "year": 2021,
            },
            "SCC": {
                "name": "Strixhaven: A Curriculum of Chaos",
                "official": True,
                "year": 2021,
            },
            "MPMM": {
                "name": "Mordenkainen Presents: Monsters of the Multiverse",
                "official": True,
                "year": 2022,
            },
            "FTD": {
                "name": "Fizban's Treasury of Dragons",
                "official": True,
                "year": 2021,
            },
            "SAiS": {
                "name": "Spelljammer: Adventures in Space",
                "official": True,
                "year": 2022,
            },
            "BMT": {"name": "The Book of Many Things", "official": True, "year": 2023},
            # Adventures
            "CoS": {
                "name": "Curse of Strahd",
                "official": True,
                "year": 2016,
                "type": "adventure",
            },
            "HotDQ": {
                "name": "Hoard of the Dragon Queen",
                "official": True,
                "year": 2014,
                "type": "adventure",
            },
            "RoT": {
                "name": "The Rise of Tiamat",
                "official": True,
                "year": 2014,
                "type": "adventure",
            },
            "PotA": {
                "name": "Princes of the Apocalypse",
                "official": True,
                "year": 2015,
                "type": "adventure",
            },
            "OotA": {
                "name": "Out of the Abyss",
                "official": True,
                "year": 2015,
                "type": "adventure",
            },
            "SKT": {
                "name": "Storm King's Thunder",
                "official": True,
                "year": 2016,
                "type": "adventure",
            },
            "ToA": {
                "name": "Tomb of Annihilation",
                "official": True,
                "year": 2017,
                "type": "adventure",
            },
            "WDH": {
                "name": "Waterdeep: Dragon Heist",
                "official": True,
                "year": 2018,
                "type": "adventure",
            },
            "WDMM": {
                "name": "Waterdeep: Dungeon of the Mad Mage",
                "official": True,
                "year": 2018,
                "type": "adventure",
            },
            "GoS": {
                "name": "Ghosts of Saltmarsh",
                "official": True,
                "year": 2019,
                "type": "adventure",
            },
            "BGDIA": {
                "name": "Baldur's Gate: Descent into Avernus",
                "official": True,
                "year": 2019,
                "type": "adventure",
            },
            "DIP": {
                "name": "Dragon of Icespire Peak",
                "official": True,
                "year": 2019,
                "type": "adventure",
            },
        }

        # Add abbreviation field and set defaults
        for abbrev, info in official_sources.items():
            info["abbreviation"] = abbrev
            source_info[abbrev] = info

        # Add any additional sources discovered from content
        enabled_sources = self.config.get_enabled_sources()
        for source in enabled_sources:
            # Mark configured sources
            if source.name not in source_info:
                source_info[source.name] = {
                    "name": source.name.replace("-", " ").title(),
                    "abbreviation": source.name,
                    "official": False,
                    "source_type": source.type.value,
                }

        self._source_info_cache = source_info

    def clear_cache(self) -> None:
        """Clear internal caches to force rebuild."""
        self._data_paths_cache = None
        self._source_info_cache = None

    def get_all_sources(self) -> list[str]:
        """Get list of all available source abbreviations."""
        if self._source_info_cache is None:
            self._build_source_info_cache()
        return list(self._source_info_cache.keys()) if self._source_info_cache else []

    def get_content_statistics(self) -> dict[str, Any]:
        """Get statistics about available content."""
        stats: dict[str, Any] = {"sources": len(self.config.get_enabled_sources())}

        data_paths = self.get_data_paths()
        stats["content_types"] = len(data_paths)
        stats["total_files"] = sum(len(paths) for paths in data_paths.values())

        by_type: dict[str, int] = {}
        for content_type, paths in data_paths.items():
            by_type[content_type.value] = len(paths)
        stats["by_type"] = by_type

        return stats

    def get_metadata_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to metadata files organized by content type.

        Metadata files contain lightweight index information (names, IDs, TOC)
        and are loaded by the omnidexer. Content files are excluded.

        Returns:
            Dictionary mapping content types to metadata file paths
        """
        if not self.content_manager._index_built:
            logger.warning(
                "Content index not built. Run async ensure_sources_ready() first."
            )
            return {}

        metadata_paths: dict[ContentType, list[Path]] = {}
        all_files = self.content_manager.get_all_content_files()

        # Find metadata files
        for source_name, files in all_files.items():
            for file_path in files:
                if self._is_metadata_file(file_path):
                    filename = file_path.name.lower()

                    # Map metadata files to content types
                    if filename == "adventures.json":
                        if ContentType.ADVENTURE not in metadata_paths:
                            metadata_paths[ContentType.ADVENTURE] = []
                        metadata_paths[ContentType.ADVENTURE].append(file_path)
                    elif filename == "books.json":
                        if ContentType.BOOK not in metadata_paths:
                            metadata_paths[ContentType.BOOK] = []
                        metadata_paths[ContentType.BOOK].append(file_path)

        logger.info("Discovered metadata files:")
        for content_type, paths in metadata_paths.items():
            logger.info(f"  {content_type.value}: {len(paths)} files")

        return metadata_paths

    def get_content_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to content files organized by content type.

        Content files contain the actual entry data for adventures and books.
        These are loaded on-demand and merged with metadata.

        Returns:
            Dictionary mapping content types to content file paths
        """
        if not self.content_manager._index_built:
            logger.warning(
                "Content index not built. Run async ensure_sources_ready() first."
            )
            return {}

        content_paths: dict[ContentType, list[Path]] = {}
        all_files = self.content_manager.get_all_content_files()

        # Find content files
        for source_name, files in all_files.items():
            for file_path in files:
                if self._is_content_file(file_path):
                    filename = file_path.name.lower()

                    # Map content files to content types
                    if filename.startswith("adventure-"):
                        if ContentType.ADVENTURE not in content_paths:
                            content_paths[ContentType.ADVENTURE] = []
                        content_paths[ContentType.ADVENTURE].append(file_path)
                    elif filename.startswith("book-"):
                        if ContentType.BOOK not in content_paths:
                            content_paths[ContentType.BOOK] = []
                        content_paths[ContentType.BOOK].append(file_path)

        logger.info("Discovered content files:")
        for content_type, paths in content_paths.items():
            logger.info(f"  {content_type.value}: {len(paths)} files")

        return content_paths

    def _is_metadata_file(self, file_path: Path) -> bool:
        """Check if file is a metadata file (adventures.json, books.json).

        Metadata files contain lightweight index information with names, IDs,
        and table of contents structure, but no actual content data.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is a metadata file
        """
        filename = file_path.name.lower()

        # Metadata files have exact names
        metadata_files = {"adventures.json", "books.json"}

        return filename in metadata_files

    def _is_content_file(self, file_path: Path) -> bool:
        """Check if file is a content file (adventure-*.json, book-*.json).

        Content files contain the actual entry data for adventures and books,
        but have minimal metadata information.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is a content file
        """
        filename = file_path.name.lower()

        # Content files follow specific patterns
        content_patterns = [
            "adventure-",  # adventure-cos.json, adventure-hotdq.json, etc.
            "book-",  # book-phb.json, book-mm.json, etc.
        ]

        return filename.endswith(".json") and any(
            filename.startswith(pattern) for pattern in content_patterns
        )

    def _should_skip_file_at_discovery(self, file_path: Path) -> bool:
        """Check if file should be skipped during discovery phase."""
        filename = file_path.name.lower()
        file_path.parent.name.lower()
        str(file_path).lower()

        # Skip non-JSON files
        if not filename.endswith(".json"):
            return True

        # Skip specific directories
        skip_directories = {
            "search",  # Search indices
            "generated",  # Generated metadata
            "node_modules",  # Node.js dependencies
            ".git",  # Git directory
            "test",  # Test files
            "tests",  # Test files
            "spec",  # Specification files
            "docs",  # Documentation
            "build",  # Build artifacts
            "dist",  # Distribution files
        }

        # Check if any parent directory should be skipped
        path_parts = file_path.parts
        for part in path_parts:
            if part.lower() in skip_directories:
                return True

        # Skip specific file patterns
        skip_file_patterns = [
            "cspell.json",
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "eslint.config",
            "jest.config",
            "webpack.config",
            "rollup.config",
            "vite.config",
            "manifest.json",
            "sw-",  # Service worker files
            "gendata-",  # Generated data files
            "index-",  # Search index files
            "-template",  # Template files
            "template-",  # Template files
            "browserconfig.xml",
            "open-search.xml",
        ]

        for pattern in skip_file_patterns:
            if pattern in filename:
                return True

        # Skip content files during discovery - they will be loaded on-demand
        # Only metadata files should be loaded by the omnidexer
        if self._is_content_file(file_path):
            return True

        return False
