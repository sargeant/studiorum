"""Homebrew multi-type content loader for handling single-file homebrew collections."""

import logging
from pathlib import Path
from typing import Any

from studiorum.core.models.content import ContentType
from studiorum.core.registry.registry_manager import RegistryManager

from .json_loader import JsonDataLoader

logger = logging.getLogger(__name__)


class HomebrewMultiTypeLoader:
    """Loader for homebrew files containing multiple content types in a single file.

    Homebrew files like wsc.json contain multiple content types:
    {
        "_meta": {...},
        "item": [...],
        "monster": [...],
        "adventure": [...],
        "adventureData": [...]
    }

    This loader processes all content types from a single file and returns
    them organized by type for the Omnidexer to index appropriately.
    """

    # Mapping from JSON keys to ContentType enum values
    CONTENT_TYPE_MAPPING = {
        "monster": ContentType.CREATURE,
        "monsterFluff": ContentType.CREATURE_FLUFF,
        "item": ContentType.ITEM,
        "itemFluff": ContentType.ITEM_FLUFF,
        "spell": ContentType.SPELL,
        "spellFluff": ContentType.SPELL_FLUFF,
        "feat": ContentType.FEAT,
        "featFluff": ContentType.FEAT_FLUFF,
        "race": ContentType.RACE,
        "raceFluff": ContentType.RACE_FLUFF,
        "background": ContentType.BACKGROUND,
        "backgroundFluff": ContentType.BACKGROUND_FLUFF,
        "class": ContentType.CLASS,
        "classFluff": ContentType.CLASS_FLUFF,
        "variantrule": ContentType.VARIANTRULE,
        "action": ContentType.ACTION,
        "condition": ContentType.CONDITION,
        "sense": ContentType.SENSE,
        "hazard": ContentType.HAZARD,
        "status": ContentType.STATUS,
        "adventure": ContentType.ADVENTURE,
        "adventureData": ContentType.ADVENTURE,  # Both map to ADVENTURE
        "book": ContentType.BOOK,
        "bookData": ContentType.BOOK,  # Both map to BOOK
    }

    def __init__(self) -> None:
        """Initialize the homebrew multi-type loader."""
        self._loaders: dict[ContentType, JsonDataLoader] = {}
        self._registry_manager = RegistryManager()

    def _get_loader(self, content_type: ContentType) -> JsonDataLoader:
        """Get or create a loader for the specified content type."""
        if content_type not in self._loaders:
            self._loaders[content_type] = JsonDataLoader.create_for_type(content_type)
        return self._loaders[content_type]

    def is_multi_type_file(self, path: Path) -> bool:
        """Check if a file contains multiple content types.

        Args:
            path: Path to the JSON file

        Returns:
            True if the file contains multiple content types, False otherwise
        """
        try:
            import json

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return False

            # Check for multiple content type keys (excluding _meta)
            content_keys = [
                key
                for key in data.keys()
                if key in self.CONTENT_TYPE_MAPPING and isinstance(data[key], list)
            ]

            # It's a multi-type file if it has more than one content type
            return len(content_keys) > 1

        except Exception as e:
            logger.debug(f"Error checking if {path} is multi-type: {e}")
            return False

    def load(self, path: Path) -> dict[ContentType, list[Any]]:
        """Load all content types from a homebrew file.

        Args:
            path: Path to the homebrew JSON file

        Returns:
            Dictionary mapping ContentType to list of loaded content items
        """
        import json

        logger.info(f"Loading multi-type homebrew file: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning(f"Homebrew file {path} is not a dictionary")
            return {}

        # Extract source information from _meta if available
        source_info = None
        if "_meta" in data and "sources" in data["_meta"]:
            sources = data["_meta"]["sources"]
            if sources and isinstance(sources, list) and len(sources) > 0:
                source_info = sources[0].get("json") or sources[0].get("abbreviation")

        # Process each content type
        result: dict[ContentType, list[Any]] = {}

        for json_key, content_type in self.CONTENT_TYPE_MAPPING.items():
            if json_key not in data:
                continue

            content_list = data[json_key]
            if not isinstance(content_list, list):
                logger.warning(
                    f"Content for {json_key} in {path} is not a list, skipping"
                )
                continue

            if not content_list:
                continue

            logger.debug(f"Processing {len(content_list)} {json_key} items from {path}")

            # Get the appropriate loader for this content type
            loader = self._get_loader(content_type)

            # Ensure source information is present in each item
            if source_info:
                for item in content_list:
                    if isinstance(item, dict) and "source" not in item:
                        item["source"] = source_info

            # Use the loader's validation and processing
            try:
                # Create a temporary data structure for the loader
                temp_data = {json_key: content_list}
                validated_items = loader.load_from_data(temp_data, path)

                if validated_items:
                    if content_type not in result:
                        result[content_type] = []
                    result[content_type].extend(validated_items)

                    logger.info(
                        f"Loaded {len(validated_items)} {content_type.value} items from {path}"
                    )

            except Exception as e:
                logger.error(f"Failed to load {json_key} content from {path}: {e}")

        # Handle special case: merge adventure metadata and adventureData
        if ContentType.ADVENTURE in result and len(result[ContentType.ADVENTURE]) > 1:
            adventure_items = result[ContentType.ADVENTURE]

            # Find the metadata adventure (has proper name) and data adventure (has extensive content)
            metadata_adventure = None
            data_adventure = None

            for item in adventure_items:
                # Check if this is the metadata adventure (has proper name, not "Unknown Adventure")
                if hasattr(item, "name") and item.name != "Unknown Adventure":
                    metadata_adventure = item
                # Check if this is the data adventure (content from adventureData section)
                elif hasattr(item, "name") and item.name == "Unknown Adventure":
                    data_adventure = item

            # If we found both, merge the content from data adventure into metadata adventure
            if metadata_adventure and data_adventure:
                logger.debug(
                    f"Merging adventure metadata and content for '{metadata_adventure.name}'"
                )

                # Replace the minimal contents in metadata with the rich content from data
                if hasattr(data_adventure, "contents") and data_adventure.contents:
                    metadata_adventure.contents = data_adventure.contents
                    logger.info(
                        f"Successfully merged {len(data_adventure.contents)} content sections "
                        f"into adventure '{metadata_adventure.name}'"
                    )

                # Keep only the merged metadata adventure
                result[ContentType.ADVENTURE] = [metadata_adventure]
            else:
                logger.warning(
                    "Could not identify metadata and data adventures for merging"
                )

        return result

    def load_single_type(self, path: Path, content_type: ContentType) -> list[Any]:
        """Load a specific content type from a homebrew file.

        Args:
            path: Path to the homebrew JSON file
            content_type: The content type to extract

        Returns:
            List of loaded content items of the specified type
        """
        all_content = self.load(path)
        return all_content.get(content_type, [])
