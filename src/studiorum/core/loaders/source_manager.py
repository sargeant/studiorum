"""File system-based source manager."""

from pathlib import Path
from typing import Any

from ..config.unified_config import get_app_config
from ..logging import get_logger
from ..models.content import ContentType
from .base import SourceManager

logger = get_logger(__name__)


class _PathConfigCompat:
    """Compatibility wrapper for legacy path_config interface."""

    def __init__(self, source_manager: "FileSystemSourceManager"):
        self._source_manager = source_manager

    @property
    def data_path(self) -> Path | None:
        """Get the data path from the app config."""
        return self._source_manager.app_config.paths.data_path

    @data_path.setter
    def data_path(self, value: Path) -> None:
        """Set the data path in the app config."""
        self._source_manager.app_config.paths.data_path = value


class FileSystemSourceManager(SourceManager):
    """Manages data sources from the file system."""

    def __init__(self, root_path: Path | None = None):
        self.root_path = root_path or Path.cwd()
        self.app_config = get_app_config()
        self._source_info = self._build_source_info()
        # Compatibility wrapper for legacy path_config interface
        self.path_config = _PathConfigCompat(self)

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to data files organized by content type.

        For adventures and books, this returns only metadata files to prevent
        duplicate loading. Content files are loaded on-demand by ContentResolver.
        """
        return self._get_data_paths()

    def get_metadata_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to metadata files organized by content type.

        FileSystemSourceManager doesn't separate metadata and content files,
        so this returns empty dictionaries for adventures and books.

        Returns:
            Empty dictionary for metadata files
        """
        # FileSystemSourceManager doesn't implement the dual-file pattern
        # used by 5etools, so metadata files concept doesn't apply
        return {}

    def get_content_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to content files organized by content type.

        FileSystemSourceManager doesn't separate metadata and content files,
        so this returns empty dictionaries for adventures and books.

        Returns:
            Empty dictionary for content files
        """
        # FileSystemSourceManager doesn't implement the dual-file pattern
        # used by 5etools, so content files concept doesn't apply
        return {}

    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation to full source information."""
        return self._source_info.get(source_abbrev)

    def get_source_priority(self, source_abbrev: str) -> int:
        """Get priority for a source (lower numbers = higher priority)."""
        # Official sources get higher priority
        official_sources = {
            "PHB": 1,  # Player's Handbook
            "MM": 2,  # Monster Manual
            "DMG": 3,  # Dungeon Master's Guide
            "SCAG": 10,  # Sword Coast Adventurer's Guide
            "VGM": 11,  # Volo's Guide to Monsters
            "XGE": 12,  # Xanathar's Guide to Everything
            "MTF": 13,  # Mordenkainen's Tome of Foes
            "TCE": 14,  # Tasha's Cauldron of Everything
        }

        return official_sources.get(
            source_abbrev, 1000
        )  # High number for unknown sources

    def _build_source_info(self) -> dict[str, dict[str, Any]]:
        """Build source information database."""
        # This would ideally be loaded from a sources.json file
        # For now, we'll use a basic mapping
        return {
            "PHB": {
                "name": "Player's Handbook",
                "abbreviation": "PHB",
                "official": True,
                "year": 2014,
            },
            "MM": {
                "name": "Monster Manual",
                "abbreviation": "MM",
                "official": True,
                "year": 2014,
            },
            "DMG": {
                "name": "Dungeon Master's Guide",
                "abbreviation": "DMG",
                "official": True,
                "year": 2014,
            },
            "SCAG": {
                "name": "Sword Coast Adventurer's Guide",
                "abbreviation": "SCAG",
                "official": True,
                "year": 2015,
            },
            "VGM": {
                "name": "Volo's Guide to Monsters",
                "abbreviation": "VGM",
                "official": True,
                "year": 2016,
            },
            "XGE": {
                "name": "Xanathar's Guide to Everything",
                "abbreviation": "XGE",
                "official": True,
                "year": 2017,
            },
            "MTF": {
                "name": "Mordenkainen's Tome of Foes",
                "abbreviation": "MTF",
                "official": True,
                "year": 2018,
            },
            "TCE": {
                "name": "Tasha's Cauldron of Everything",
                "abbreviation": "TCE",
                "official": True,
                "year": 2020,
            },
            "CoS": {
                "name": "Curse of Strahd",
                "abbreviation": "CoS",
                "official": True,
                "year": 2016,
                "type": "adventure",
            },
        }

    def _get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Get data file paths organized by content type."""
        paths = {}

        # Try multiple data source locations
        data_dirs = []
        if self.app_config.paths.data_path and self.app_config.paths.data_path.exists():
            data_dirs.append(self.app_config.paths.data_path)

        # Check for srd-data directory
        srd_data = self.root_path / "srd-data"
        if srd_data.exists():
            data_dirs.append(srd_data)

        # Use string-based mappings and only convert to ContentType if they exist
        # This avoids the chicken-and-egg problem with dynamic ContentTypes
        string_mappings = {
            "spell": ["spells", "spell"],
            "creature": ["bestiary", "monster", "creatures"],
            "item": ["items", "item"],
            "adventure": ["adventure", "adventures"],
            "book": ["book", "books"],
            "class": ["class", "classes"],
            "background": ["background", "backgrounds"],
            "feat": ["feat", "feats"],
            "race": ["race", "races"],
        }

        # Convert to ContentType only if the enum member exists
        content_mappings = {}
        for type_str, subdirs in string_mappings.items():
            try:
                content_type = ContentType(type_str)
                content_mappings[content_type] = subdirs
            except ValueError:
                # Skip content types that don't exist as enum members yet
                # They will be handled by UnifiedSourceManager after registry initialization
                continue

        for content_type, subdirs in content_mappings.items():
            type_paths = []

            for data_dir in data_dirs:
                # Check each possible subdirectory
                for subdir in subdirs:
                    subdir_path = data_dir / subdir
                    if subdir_path.exists():
                        # Find JSON files in this directory
                        json_files = list(subdir_path.glob("*.json"))
                        type_paths.extend(json_files)

                # Also check for files in root data directory using string comparisons
                if content_type.value == "spell":
                    type_paths.extend(data_dir.glob("spells*.json"))
                elif content_type.value == "creature":
                    type_paths.extend(data_dir.glob("bestiary*.json"))
                    type_paths.extend(data_dir.glob("*monster*.json"))
                elif content_type.value == "item":
                    type_paths.extend(data_dir.glob("items*.json"))
                elif content_type.value == "background":
                    type_paths.extend(data_dir.glob("background*.json"))
                elif content_type.value == "feat":
                    type_paths.extend(data_dir.glob("feat*.json"))
                elif content_type.value == "race":
                    type_paths.extend(data_dir.glob("race*.json"))
                elif content_type.value == "class":
                    # Classes have a directory structure, already handled above
                    pass

            if type_paths:
                paths[content_type] = type_paths

        return paths
