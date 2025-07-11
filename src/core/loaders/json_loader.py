"""JSON data loader with Pydantic validation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Type

from pydantic import ValidationError

from ..config.settings import get_logger
from ..models.content import ContentType
from .base import DataLoader, T

logger = get_logger(__name__)


class JsonDataLoader(DataLoader[T]):
    """Loads and validates JSON data using Pydantic models."""

    def __init__(self, model_class: Type[T], content_type: ContentType):
        self.model_class = model_class
        self.content_type = content_type

    async def load(self, path: Path) -> List[T]:
        """Load JSON file and validate against Pydantic model."""
        try:
            logger.info(f"Loading {self.content_type.value} data from {path}")

            # Read JSON file
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Extract content based on file structure
            content_list = self._extract_content(data, path)

            # Validate each item
            validated_content = []
            for item in content_list:
                try:
                    # Ensure source information is present
                    item = self._ensure_source_info(item, path)

                    validated_item = self.model_class.model_validate(item)
                    validated_content.append(validated_item)
                except ValidationError as e:
                    logger.warning(
                        f"Validation failed for item {item.get('name', 'unknown')} in {path}: {e}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error validating item in {path}: {e}")

            logger.info(
                f"Successfully loaded {len(validated_content)} {self.content_type.value} items from {path}"
            )
            return validated_content

        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return []

    def get_content_type(self) -> ContentType:
        return self.content_type

    def get_model_class(self) -> Type[T]:
        return self.model_class

    def _extract_content(
        self, data: Dict[str, Any], path: Path
    ) -> List[Dict[str, Any]]:
        """Extract content list from various JSON structures."""
        # Handle different JSON structures from 5etools

        # Direct content arrays
        if self.content_type == ContentType.SPELL and "spell" in data:
            return data["spell"]
        elif self.content_type == ContentType.CREATURE and "monster" in data:
            return data["monster"]
        elif self.content_type == ContentType.ITEM and "item" in data:
            return data["item"]
        elif self.content_type == ContentType.ADVENTURE:
            if "adventure" in data:
                return data["adventure"]
            elif "adventureData" in data:
                # Handle adventure data format
                adventure_data = data["adventureData"]
                if isinstance(adventure_data, list) and adventure_data:
                    return adventure_data
            return []
        elif self.content_type == ContentType.BOOK:
            if "book" in data:
                return data["book"]
            elif "bookData" in data:
                # Handle book data format
                book_data = data["bookData"]
                if isinstance(book_data, list) and book_data:
                    return book_data
            return []

        # Generic fallbacks
        content_type_name = self.content_type.value
        if content_type_name in data:
            return data[content_type_name]

        # Try plural forms
        plural_name = content_type_name + "s"
        if plural_name in data:
            return data[plural_name]

        # If the data itself is a list, use it directly
        if isinstance(data, list):
            return data

        # Look for any list in the data as a fallback
        for key, value in data.items():
            if isinstance(value, list) and value:
                logger.debug(
                    f"Using '{key}' array as content for {self.content_type.value}"
                )
                return value

        logger.warning(f"No content found for {self.content_type.value} in {path}")
        return []

    def _ensure_source_info(self, item: Dict[str, Any], path: Path) -> Dict[str, Any]:
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


# Factory functions for common loaders
def create_spell_loader() -> JsonDataLoader:
    """Create a spell data loader."""
    from ..models.spells import Spell

    return JsonDataLoader(Spell, ContentType.SPELL)


def create_creature_loader() -> JsonDataLoader:
    """Create a creature data loader."""
    from ..models.creatures import Creature

    return JsonDataLoader(Creature, ContentType.CREATURE)


def create_item_loader() -> JsonDataLoader:
    """Create an item data loader."""
    from ..models.items import Item

    return JsonDataLoader(Item, ContentType.ITEM)


def create_adventure_loader() -> JsonDataLoader:
    """Create an adventure data loader."""
    from ..models.adventures import Adventure

    return JsonDataLoader(Adventure, ContentType.ADVENTURE)


def create_book_loader() -> JsonDataLoader:
    """Create a book data loader."""
    from ..models.books import Book

    return JsonDataLoader(Book, ContentType.BOOK)
