"""Configurable source manager that integrates with the new content source system."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.settings import get_logger
from ..config.sources import get_content_config
from ..models.content import ContentType
from ..sources import ContentSourceManager
from .base import SourceManager

logger = get_logger(__name__)


class ConfigurableSourceManager(SourceManager):
    """Source manager that uses configurable content sources."""

    def __init__(self):
        """Initialize with content configuration."""
        self.config = get_content_config()
        self.content_manager = ContentSourceManager(self.config)
        self._data_paths_cache: Optional[Dict[ContentType, List[Path]]] = None
        self._source_info_cache: Optional[Dict[str, Dict[str, Any]]] = None

    async def ensure_sources_ready(self) -> None:
        """Ensure all content sources are available and indexed."""
        await self.content_manager.ensure_all_sources()
        await self.content_manager.build_content_index()

    def get_data_paths(self) -> Dict[ContentType, List[Path]]:
        """Return paths to data files organized by content type."""
        if self._data_paths_cache is not None:
            return self._data_paths_cache

        # Check if content index is built
        if not self.content_manager._index_built:
            logger.warning(
                "Content index not built. Run async ensure_sources_ready() first."
            )
            return {}

        # Map content types to file patterns
        content_patterns = {
            ContentType.SPELL: ["spell", "spells"],
            ContentType.CREATURE: ["bestiary", "monster", "creatures"],
            ContentType.ITEM: ["item", "items"],
            ContentType.ADVENTURE: ["adventure", "adventures"],
            ContentType.BOOK: ["book", "books"],
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

        data_paths = {}
        all_files = self.content_manager.get_all_content_files()

        # Track files already assigned to avoid conflicts
        assigned_files = set()

        # First pass: assign fluff files (more specific patterns)
        fluff_content_types = [
            ct for ct in content_patterns.keys() if ct.value.endswith("Fluff")
        ]
        regular_content_types = [
            ct for ct in content_patterns.keys() if not ct.value.endswith("Fluff")
        ]

        # Process fluff types first to get priority
        for content_type in fluff_content_types + regular_content_types:
            patterns = content_patterns[content_type]
            type_paths = []

            # Search through all source files
            for source_name, files in all_files.items():
                for file_path in files:
                    # Skip files already assigned to another content type
                    if file_path in assigned_files:
                        continue

                    # Skip files that should be filtered at discovery level
                    if self._should_skip_file_at_discovery(file_path):
                        continue

                    file_name = file_path.name.lower()

                    # Check if file matches any pattern for this content type
                    if any(pattern in file_name for pattern in patterns):
                        # Special case: exclude monsterfeatures from feat matching
                        if (
                            content_type == ContentType.FEAT
                            and "monsterfeature" in file_name
                        ):
                            continue
                        type_paths.append(file_path)
                        assigned_files.add(file_path)

                    # Also check parent directory names
                    elif (
                        file_path not in assigned_files
                    ):  # Only if not already assigned
                        parent_name = file_path.parent.name.lower()
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

        self._data_paths_cache = data_paths

        logger.info("Discovered content files:")
        for content_type, paths in data_paths.items():
            logger.info(f"  {content_type.value}: {len(paths)} files")

        return data_paths

    def resolve_source(self, source_abbrev: str) -> Optional[Dict[str, Any]]:
        """Resolve source abbreviation to full source information."""
        if self._source_info_cache is None:
            self._build_source_info_cache()

        return self._source_info_cache.get(source_abbrev)

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

    def get_all_sources(self) -> List[str]:
        """Get list of all available source abbreviations."""
        if self._source_info_cache is None:
            self._build_source_info_cache()
        return list(self._source_info_cache.keys())

    def get_content_statistics(self) -> Dict[str, Any]:
        """Get statistics about available content."""
        stats = {"sources": len(self.config.get_enabled_sources())}

        data_paths = self.get_data_paths()
        stats["content_types"] = len(data_paths)
        stats["total_files"] = sum(len(paths) for paths in data_paths.values())

        by_type = {}
        for content_type, paths in data_paths.items():
            by_type[content_type.value] = len(paths)
        stats["by_type"] = by_type

        return stats

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

        return False
