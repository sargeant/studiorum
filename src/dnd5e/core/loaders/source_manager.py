"""File system-based source manager."""

from pathlib import Path
from typing import Any

from ..config.paths import get_path_config
from ..config.settings import get_logger
from ..models.content import ContentType
from .base import SourceManager

logger = get_logger(__name__)


class FileSystemSourceManager(SourceManager):
    """Manages data sources from the file system."""

    def __init__(self, root_path: Path | None = None):
        self.path_config = get_path_config(root_path)
        self._source_info = self._build_source_info()

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to data files organized by content type."""
        return self.path_config.get_data_paths()

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
