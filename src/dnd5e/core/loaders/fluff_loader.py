"""Fluff data loader with liberal parsing for descriptive content."""

import json
from pathlib import Path
from typing import Any

from ..logging import get_logger
from ..models.content import ContentType
from ..models.fluff import (
    BackgroundFluff,
    BaseFluff,
    ClassFluff,
    CreatureFluff,
    FeatFluff,
    ItemFluff,
    RaceFluff,
    SpellFluff,
)
from .base import DataLoader

logger = get_logger(__name__)


class FluffDataLoader(DataLoader[BaseFluff]):
    """Loads fluff data with liberal parsing to handle inconsistent structures."""

    def __init__(self, content_type: ContentType):
        self._content_type = content_type
        self._fluff_model_map = {
            ContentType.SPELL: SpellFluff,
            ContentType.CREATURE: CreatureFluff,
            ContentType.ITEM: ItemFluff,
            ContentType.RACE: RaceFluff,
            ContentType.FEAT: FeatFluff,
            ContentType.CLASS: ClassFluff,
            ContentType.BACKGROUND: BackgroundFluff,
        }
        self._fluff_key_map = {
            ContentType.SPELL: ["spellFluff", "spell_fluff"],
            ContentType.CREATURE: ["monsterFluff", "monster_fluff", "creatureFluff"],
            ContentType.ITEM: ["itemFluff", "item_fluff"],
            ContentType.RACE: ["raceFluff", "race_fluff"],
            ContentType.FEAT: ["featFluff", "feat_fluff"],
            ContentType.CLASS: ["classFluff", "class_fluff"],
            ContentType.BACKGROUND: ["backgroundFluff", "background_fluff"],
        }

    def load(self, path: Path) -> list[BaseFluff]:
        """Load fluff data with liberal parsing."""
        try:
            logger.info(f"Loading {self._content_type.value} fluff data from {path}")

            # Read JSON file synchronously
            with open(path, encoding="utf-8") as f:
                content = f.read()
                data = json.loads(content)

            # Extract fluff content
            fluff_list = self._extract_fluff_content(data, path)

            # Parse each fluff item liberally
            model_class = self._fluff_model_map.get(self._content_type, BaseFluff)
            parsed_fluff = []

            for item in fluff_list:
                try:
                    # Ensure basic required fields
                    if not item.get("name"):
                        logger.debug(f"Skipping fluff item without name in {path}")
                        continue

                    # Liberal parsing - if validation fails, try to extract what we can
                    fluff_item = self._parse_fluff_item(item, model_class, path)
                    if fluff_item:
                        parsed_fluff.append(fluff_item)

                except Exception as e:
                    logger.debug(
                        f"Skipping fluff item {item.get('name', 'unknown')} in {path}: {e}"
                    )

            logger.info(
                f"Successfully loaded {len(parsed_fluff)} {self._content_type.value} fluff items from {path}"
            )
            return parsed_fluff

        except Exception as e:
            logger.warning(f"Failed to load fluff from {path}: {e}")
            return []

    def get_content_type(self) -> ContentType:
        return self._content_type

    def get_model_class(self) -> type[BaseFluff]:
        return self._fluff_model_map.get(self._content_type, BaseFluff)

    def _extract_fluff_content(
        self, data: dict[str, Any], path: Path
    ) -> list[dict[str, Any]]:
        """Extract fluff content from various JSON structures."""
        # Try specific fluff keys first
        fluff_keys = self._fluff_key_map.get(self._content_type, [])
        for fluff_key in fluff_keys:
            if fluff_key in data:
                content = data[fluff_key]
                if isinstance(content, list):
                    return content

        # Try generic patterns
        for possible_key in [
            f"{self._content_type.value}Fluff",
            f"{self._content_type.value}fluff",
            "fluff",
            "fluffData",
        ]:
            if possible_key in data:
                content = data[possible_key]
                if isinstance(content, list):
                    return content

        # Look for any key ending with "fluff"
        for key, value in data.items():
            if key.lower().endswith("fluff") and isinstance(value, list):
                logger.debug(
                    f"Found fluff data in key '{key}' for {self._content_type.value}"
                )
                return value

        logger.debug(f"No fluff content found for {self._content_type.value} in {path}")
        return []

    def _parse_fluff_item(
        self, item: dict[str, Any], model_class: type[BaseFluff], path: Path
    ) -> BaseFluff:
        """Parse fluff item with liberal validation."""
        try:
            # First try normal validation
            return model_class.model_validate(item)
        except Exception:
            # If that fails, try liberal parsing
            return self._liberal_parse(item, model_class, path)

    def _liberal_parse(
        self, item: dict[str, Any], model_class: type[BaseFluff], path: Path
    ) -> BaseFluff:
        """Liberal parsing that extracts what it can and ignores errors."""
        # Start with basic required fields
        parsed_item = {
            "name": item.get("name", "Unknown"),
            "source": item.get("source", "Unknown"),
        }

        # Try to extract entries
        for entry_key in ["entries", "entry", "text", "description"]:
            if entry_key in item:
                entries_data = item[entry_key]
                break
        else:
            entries_data = None

        if entries_data:
            parsed_item["entries"] = entries_data

        # Try to extract images
        if "images" in item:
            parsed_item["images"] = item["images"]

        # Store any additional data for potential future use
        extra_data = {
            k: v
            for k, v in item.items()
            if k not in ["name", "source", "entries", "images"]
        }
        if extra_data:
            parsed_item["extra_data"] = extra_data

        try:
            return model_class.model_validate(parsed_item)
        except Exception as e:
            logger.debug(
                f"Even liberal parsing failed for {item.get('name', 'unknown')} in {path}: {e}"
            )
            # Create minimal valid object
            return model_class(
                name=item.get("name", "Unknown"), source=item.get("source", "Unknown")
            )

    @classmethod
    def create_for_type(cls, content_type: ContentType) -> "FluffDataLoader":
        """Create a FluffDataLoader instance for a given content type."""
        return cls(content_type)
