"""Content attribution manager for 5e source metadata and priority resolution.

This module provides the ContentAttributionManager class that handles content
attribution (which 5e book content comes from) separately from data repository
management. This extracts the content attribution functionality from ConfigurableSourceManager.
"""

from __future__ import annotations

from typing import Any

from ..config.sources import get_content_config
from ..logging import get_logger

logger = get_logger(__name__)


class ContentAttributionError(Exception):
    """Content attribution resolution failed."""


class ContentAttributionManager:
    """Content attribution manager for handling 5e source metadata.

    Manages 5e source attribution (PHB, MM, DMG, etc.) and priority
    resolution. Separates content attribution from data repository concerns.

    This manager provides:
    - Source abbreviation resolution (PHB → Player's Handbook)
    - Source priority determination (official sources get higher priority)
    - Comprehensive metadata about 5e publications
    - Support for both official WotC content and third-party sources
    """

    def __init__(self) -> None:
        """Initialize with content configuration."""
        self.config = get_content_config()
        self._source_info_cache: dict[str, dict[str, Any]] | None = None

    def get_service_name(self) -> str:
        """Return service name for debugging and logging."""
        return "ContentAttributionManager"

    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation to full source information.

        Args:
            source_abbrev: Source abbreviation (e.g., 'PHB', 'MM', 'DMG')

        Returns:
            Source information dictionary or None if not found
        """
        if self._source_info_cache is None:
            self._build_source_info_cache()

        return (
            self._source_info_cache.get(source_abbrev)
            if self._source_info_cache
            else None
        )

    def get_source_priority(self, source_abbrev: str) -> int:
        """Get priority for a source (lower numbers = higher priority).

        Args:
            source_abbrev: Source abbreviation to check

        Returns:
            Priority value (0 = highest priority)
        """
        # Official 5e sources get higher priority
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

    def get_all_sources(self) -> list[str]:
        """Get list of all known source abbreviations.

        Returns:
            List of source abbreviations in priority order
        """
        if self._source_info_cache is None:
            self._build_source_info_cache()

        # Sort by priority (lower priority number = higher priority)
        all_sources = (
            list(self._source_info_cache.keys()) if self._source_info_cache else []
        )
        return sorted(all_sources, key=self.get_source_priority)

    def get_source_metadata(self, source_abbrev: str) -> dict[str, Any] | None:
        """Get detailed metadata for a source.

        Args:
            source_abbrev: Source abbreviation

        Returns:
            Metadata dictionary with publication info, type, etc.
        """
        return self.resolve_source(source_abbrev)

    def clear_cache(self) -> None:
        """Clear internal caches to force rebuild."""
        self._source_info_cache = None

    def get_attribution_statistics(self) -> dict[str, Any]:
        """Get statistics about source attribution.

        Returns:
            Dictionary with source counts, official vs third-party breakdown
        """
        if self._source_info_cache is None:
            self._build_source_info_cache()

        if not self._source_info_cache:
            return {"total_sources": 0, "official_sources": 0, "third_party_sources": 0}

        official_count = sum(
            1
            for info in self._source_info_cache.values()
            if info.get("official", False)
        )

        return {
            "total_sources": len(self._source_info_cache),
            "official_sources": official_count,
            "third_party_sources": len(self._source_info_cache) - official_count,
        }

    def _build_source_info_cache(self) -> None:
        """Build comprehensive source information from all configured sources."""
        source_info = {}

        # Add comprehensive 5e source information
        official_sources = {
            # Core 5e Books
            "PHB": {
                "name": "Player's Handbook",
                "official": True,
                "year": 2014,
                "type": "core",
            },
            "MM": {
                "name": "Monster Manual",
                "official": True,
                "year": 2014,
                "type": "core",
            },
            "DMG": {
                "name": "Dungeon Master's Guide",
                "official": True,
                "year": 2014,
                "type": "core",
            },
            # Expansion Books
            "SCAG": {
                "name": "Sword Coast Adventurer's Guide",
                "official": True,
                "year": 2015,
                "type": "expansion",
            },
            "VGM": {
                "name": "Volo's Guide to Monsters",
                "official": True,
                "year": 2016,
                "type": "expansion",
            },
            "XGE": {
                "name": "Xanathar's Guide to Everything",
                "official": True,
                "year": 2017,
                "type": "expansion",
            },
            "MTF": {
                "name": "Mordenkainen's Tome of Foes",
                "official": True,
                "year": 2018,
                "type": "expansion",
            },
            "GGR": {
                "name": "Guildmasters' Guide to Ravnica",
                "official": True,
                "year": 2018,
                "type": "setting",
            },
            "AI": {
                "name": "Acquisitions Incorporated",
                "official": True,
                "year": 2019,
                "type": "expansion",
            },
            "ERLW": {
                "name": "Eberron: Rising from the Last War",
                "official": True,
                "year": 2019,
                "type": "setting",
            },
            "EGW": {
                "name": "Explorer's Guide to Wildemount",
                "official": True,
                "year": 2020,
                "type": "setting",
            },
            "MOT": {
                "name": "Mythic Odysseys of Theros",
                "official": True,
                "year": 2020,
                "type": "setting",
            },
            "IDRotF": {
                "name": "Icewind Dale: Rime of the Frostmaiden",
                "official": True,
                "year": 2020,
                "type": "adventure",
            },
            "TCE": {
                "name": "Tasha's Cauldron of Everything",
                "official": True,
                "year": 2020,
                "type": "expansion",
            },
            "VRGtR": {
                "name": "Van Richten's Guide to Ravenloft",
                "official": True,
                "year": 2021,
                "type": "setting",
            },
            "WBtW": {
                "name": "The Wild Beyond the Witchlight",
                "official": True,
                "year": 2021,
                "type": "adventure",
            },
            "SCC": {
                "name": "Strixhaven: A Curriculum of Chaos",
                "official": True,
                "year": 2021,
                "type": "setting",
            },
            "MPMM": {
                "name": "Mordenkainen Presents: Monsters of the Multiverse",
                "official": True,
                "year": 2022,
                "type": "expansion",
            },
            "CRCotN": {
                "name": "Critical Role: Call of the Netherdeep",
                "official": True,
                "year": 2022,
                "type": "adventure",
            },
            "FTD": {
                "name": "Fizban's Treasury of Dragons",
                "official": True,
                "year": 2021,
                "type": "expansion",
            },
            "SAiS": {
                "name": "Spelljammer: Adventures in Space",
                "official": True,
                "year": 2022,
                "type": "setting",
            },
            "DoD": {
                "name": "Dragonlance: Shadow of the Dragon Queen",
                "official": True,
                "year": 2022,
                "type": "setting",
            },
            "KftGV": {
                "name": "Keys from the Golden Vault",
                "official": True,
                "year": 2023,
                "type": "adventure",
            },
            "BMT": {
                "name": "The Book of Many Things",
                "official": True,
                "year": 2023,
                "type": "expansion",
            },
            # Classic Adventures
            "LMoP": {
                "name": "Lost Mine of Phandelver",
                "official": True,
                "year": 2014,
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
            "CoS": {
                "name": "Curse of Strahd",
                "official": True,
                "year": 2016,
                "type": "adventure",
            },
            "SKT": {
                "name": "Storm King's Thunder",
                "official": True,
                "year": 2016,
                "type": "adventure",
            },
            "TftYP": {
                "name": "Tales from the Yawning Portal",
                "official": True,
                "year": 2017,
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

        # Add any additional sources discovered from content configuration
        enabled_sources = self.config.get_enabled_sources()
        for source in enabled_sources:
            # Mark configured sources
            if source.name not in source_info:
                source_info[source.name] = {
                    "name": source.name.replace("-", " ").title(),
                    "abbreviation": source.name,
                    "official": False,
                    "source_type": source.type.value,
                    "type": "third-party",
                }

        self._source_info_cache = source_info

        logger.debug(f"Built source attribution cache with {len(source_info)} sources")
        official_count = sum(
            1 for info in source_info.values() if info.get("official", False)
        )
        logger.debug(
            f"Official sources: {official_count}, Third-party sources: {len(source_info) - official_count}"
        )
