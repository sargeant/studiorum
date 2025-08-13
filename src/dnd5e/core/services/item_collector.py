"""Item collection service for advanced item filtering and gathering."""

import difflib
import logging
from typing import Any

from ..loaders.omnidexer import Omnidexer
from ..models.content import ContentType
from ..models.item_filters import ItemCollectionResult, ItemFilterCriteria
from ..models.items import Item, ItemRarity, ItemType

logger = logging.getLogger(__name__)


class ItemCollector:
    """Service for collecting items based on advanced filter criteria.

    This service handles both treasure hoard use cases (specific item names) and
    shop/equipment list use cases (type/rarity-based filtering) with comprehensive
    filtering capabilities.
    """

    def __init__(self, omnidexer: Omnidexer):
        """Initialize the item collector with an omnidexer instance.

        Args:
            omnidexer: The omnidexer instance for content lookup
        """
        self.omnidexer = omnidexer

    def collect_items(self, criteria: ItemFilterCriteria) -> ItemCollectionResult:
        """Collect items matching the given criteria.

        Args:
            criteria: The filtering criteria to apply

        Returns:
            ItemCollectionResult with matched items and metadata
        """
        result = ItemCollectionResult()

        # Handle name-only filtering (treasure hoard use case)
        if criteria.is_name_only_filter() and criteria.item_names:
            return self._collect_by_names(criteria.item_names, criteria.sources)

        # Handle item names with source filtering
        if criteria.item_names:
            name_result = self._collect_by_names(criteria.item_names, criteria.sources)
            # Filter the name-based results by the same criteria (excluding name and source filters)
            for item in name_result.items:
                if self._matches_criteria(item, criteria):
                    # Check if already added to avoid duplicates
                    if item not in result.items:
                        source_abbrev = None
                        if hasattr(item.source, "abbreviation"):
                            source_abbrev = item.source.abbreviation
                        result.add_item(item, source_abbrev)

            # Add unresolved names
            result.unresolved_names.extend(name_result.unresolved_names)
            result.suggestions.update(name_result.suggestions)

        # Handle non-name-based filtering (type/rarity/etc.)
        else:
            # Get all items from relevant sources
            if criteria.sources:
                all_items = []
                item_type = ContentType("item")
                for source in criteria.sources:
                    source_items = self.omnidexer.get_all_by_source(source)
                    # Filter to only items of the correct type
                    for item in source_items:
                        if isinstance(item, Item):
                            all_items.append(item)
            else:
                # Get all items from all sources
                item_type = ContentType("item")
                all_content = self.omnidexer.get_all_by_type(item_type)
                all_items = [item for item in all_content if isinstance(item, Item)]

            if not all_items:
                logger.warning("No items found in omnidexer")
                return result

            logger.debug(f"Filtering {len(all_items)} items with criteria")

            # Apply filters
            for item_content in all_items:
                if not isinstance(item_content, Item):
                    logger.debug(f"Skipping non-item content: {type(item_content)}")
                    continue

                if self._matches_criteria(item_content, criteria):
                    # Get source abbreviation for tracking
                    source_abbrev = None
                    if hasattr(item_content.source, "abbreviation"):
                        source_abbrev = item_content.source.abbreviation

                    result.add_item(item_content, source_abbrev)

        logger.info(f"Collected {result.total_count} items matching criteria")
        return result

    def collect_by_names(self, names: list[str]) -> ItemCollectionResult:
        """Collect specific items by name with fuzzy matching.

        Args:
            names: List of item names to find

        Returns:
            ItemCollectionResult with found items and unresolved names
        """
        return self._collect_by_names(names)

    def collect_by_type_and_rarity(
        self, types: list[str], rarities: list[str]
    ) -> ItemCollectionResult:
        """Collect all items of given types and rarities.

        Args:
            types: List of item types (e.g., ['weapon', 'armor'])
            rarities: List of item rarities (e.g., ['common', 'uncommon'])

        Returns:
            ItemCollectionResult with collected items
        """
        # Create filter criteria for type/rarity filtering
        criteria = ItemFilterCriteria(item_types=types, rarities=rarities)

        return self.collect_items(criteria)

    def collect_equipment_pack(self, pack_name: str) -> ItemCollectionResult:
        """Collect all items in a standard equipment pack.

        Args:
            pack_name: Name of the equipment pack

        Returns:
            ItemCollectionResult with pack items
        """
        # This would require equipment pack data - for now return empty result
        # TODO: Implement equipment pack lookup
        result = ItemCollectionResult()
        result.add_unresolved(pack_name, ["Equipment pack lookup not yet implemented"])
        return result

    def _collect_by_names(
        self, names: list[str], sources: list[str] | None = None
    ) -> ItemCollectionResult:
        """Internal method to collect items by specific names.

        Args:
            names: List of item names to find
            sources: Optional list of source abbreviations to limit search
        """
        result = ItemCollectionResult()
        item_type = ContentType("item")

        for name in names:
            # Try exact match first
            matches = self.omnidexer.find_all(item_type, name)

            if matches:
                # Filter by sources if specified
                if sources:
                    filtered_matches: list[Item] = []
                    for item in matches:
                        if isinstance(item, Item) and self._matches_sources(
                            item, sources
                        ):
                            filtered_matches.append(item)
                    item_matches = filtered_matches
                else:
                    item_matches = [item for item in matches if isinstance(item, Item)]

                # Add all matching items
                for item in item_matches:
                    source_abbrev = None
                    if hasattr(item.source, "abbreviation"):
                        source_abbrev = item.source.abbreviation
                    result.add_item(item, source_abbrev)

                # If no matches after source filtering, treat as unresolved
                if sources and not item_matches:
                    suggestions = self._find_item_suggestions(name, sources)
                    result.add_unresolved(name, suggestions)
            else:
                # No exact match, try fuzzy matching
                suggestions = self._find_item_suggestions(name, sources)
                result.add_unresolved(name, suggestions)

        return result

    def _matches_criteria(self, item: Item, criteria: ItemFilterCriteria) -> bool:
        """Check if an item matches the given criteria.

        Args:
            item: The item to check
            criteria: The filter criteria

        Returns:
            True if the item matches all criteria
        """
        # Type filtering
        if criteria.item_types and not criteria.matches_item_type(item.type):
            return False

        # Rarity filtering
        if criteria.rarities and not criteria.matches_rarity(item.rarity):
            return False

        # Magic/mundane filtering
        if criteria.magic_only and not item.is_magic_item():
            return False

        if criteria.mundane_only and item.is_magic_item():
            return False

        # Value filtering
        if not self._matches_value_criteria(item, criteria):
            return False

        # Weight filtering
        if criteria.max_weight is not None:
            if item.weight is None or item.weight > criteria.max_weight:
                return False

        # Weapon-specific filtering
        if not self._matches_weapon_criteria(item, criteria):
            return False

        # Armor-specific filtering
        if not self._matches_armor_criteria(item, criteria):
            return False

        # Magic item filtering
        if not self._matches_magic_item_criteria(item, criteria):
            return False

        # Source filtering
        if criteria.sources and not self._matches_sources(item, criteria.sources):
            return False

        return True

    def _matches_value_criteria(self, item: Item, criteria: ItemFilterCriteria) -> bool:
        """Check if item value matches the criteria.

        Args:
            item: The item to check
            criteria: The filter criteria

        Returns:
            True if value criteria match
        """
        if criteria.min_value is not None or criteria.max_value is not None:
            item_value = self._get_item_value_in_gp(item)
            if item_value is None:
                return False  # Skip items without value information

            if criteria.min_value is not None and item_value < criteria.min_value:
                return False

            if criteria.max_value is not None and item_value > criteria.max_value:
                return False

        return True

    def _matches_weapon_criteria(
        self, item: Item, criteria: ItemFilterCriteria
    ) -> bool:
        """Check if weapon-specific criteria match.

        Args:
            item: The item to check
            criteria: The filter criteria

        Returns:
            True if weapon criteria match
        """
        # Only apply weapon criteria if item is a weapon
        if not item.is_weapon():
            return True  # Non-weapons pass weapon criteria

        # Weapon category filtering
        if criteria.weapon_categories:
            weapon_cat = None
            if item.weapon_data and item.weapon_data.weapon_category:
                weapon_cat = item.weapon_data.weapon_category.lower()
            elif item.weapon_category:
                weapon_cat = item.weapon_category.lower()

            if not weapon_cat or weapon_cat not in criteria.weapon_categories:
                return False

        # Weapon properties filtering
        if criteria.weapon_properties:
            weapon_props = []
            if item.weapon_data and item.weapon_data.properties:
                weapon_props = [prop.lower() for prop in item.weapon_data.properties]
            elif item.properties:
                weapon_props = [prop.lower() for prop in item.properties]

            # Check if item has all required properties
            for required_prop in criteria.weapon_properties:
                if required_prop not in weapon_props:
                    return False

        # Damage type filtering
        if criteria.damage_types:
            damage_type = None
            if item.weapon_data and item.weapon_data.damage_type:
                damage_type = item.weapon_data.damage_type.lower()
            elif item.damage_type:
                damage_type = item.damage_type.lower()

            if not damage_type or damage_type not in criteria.damage_types:
                return False

        return True

    def _matches_armor_criteria(self, item: Item, criteria: ItemFilterCriteria) -> bool:
        """Check if armor-specific criteria match.

        Args:
            item: The item to check
            criteria: The filter criteria

        Returns:
            True if armor criteria match
        """
        # Only apply armor criteria if item is armor
        if not item.is_armor():
            return True  # Non-armor passes armor criteria

        # Armor type filtering
        if criteria.armor_types:
            armor_type = None
            if item.armor_data and item.armor_data.armor_type:
                armor_type = item.armor_data.armor_type.lower()
            elif item.armor_type:
                armor_type = item.armor_type.lower()

            if not armor_type or armor_type not in criteria.armor_types:
                return False

        # Minimum AC filtering
        if criteria.min_ac is not None:
            ac = None
            if item.armor_data and item.armor_data.ac:
                ac = item.armor_data.ac
            elif item.ac:
                ac = item.ac

            if not ac or ac < criteria.min_ac:
                return False

        # Strength requirement filtering
        if criteria.max_strength_req is not None:
            strength_req = None
            if item.armor_data and item.armor_data.strength:
                strength_req = item.armor_data.strength
            elif item.strength:
                strength_req = item.strength

            if strength_req is not None and strength_req > criteria.max_strength_req:
                return False

        if criteria.no_strength_req:
            strength_req = None
            if item.armor_data and item.armor_data.strength:
                strength_req = item.armor_data.strength
            elif item.strength:
                strength_req = item.strength

            if strength_req is not None:
                return False

        # Stealth disadvantage filtering
        if criteria.no_stealth_disadvantage:
            stealth_disadvantage = False
            if item.armor_data:
                stealth_disadvantage = item.armor_data.stealth or False
            elif item.stealth is not None:
                stealth_disadvantage = item.stealth

            if stealth_disadvantage:
                return False

        return True

    def _matches_magic_item_criteria(
        self, item: Item, criteria: ItemFilterCriteria
    ) -> bool:
        """Check if magic item criteria match.

        Args:
            item: The item to check
            criteria: The filter criteria

        Returns:
            True if magic item criteria match
        """
        # Attunement filtering
        if criteria.requires_attunement is not None:
            item_requires_attunement = bool(item.requires_attunement)
            if item_requires_attunement != criteria.requires_attunement:
                return False

        # Specific attunement type filtering
        if criteria.attunement_type is not None:
            if not item.requires_attunement:
                return False
            if isinstance(item.requires_attunement, str):
                if (
                    criteria.attunement_type.lower()
                    not in item.requires_attunement.lower()
                ):
                    return False
            # If requires_attunement is True but we need a specific type, it doesn't match
            elif item.requires_attunement is True:
                return False

        # Charges filtering
        if criteria.has_charges is not None:
            item_has_charges = bool(item.charges)
            if item_has_charges != criteria.has_charges:
                return False

        # Consumable filtering (heuristic: potions, scrolls, ammunition)
        if criteria.consumable is not None:
            item_is_consumable = self._is_consumable_item(item)
            if item_is_consumable != criteria.consumable:
                return False

        return True

    def _matches_sources(self, item: Item, target_sources: list[str]) -> bool:
        """Check if item source matches target sources.

        Args:
            item: The item to check
            target_sources: List of source abbreviations

        Returns:
            True if item source is in target sources
        """
        if hasattr(item.source, "abbreviation"):
            source_abbrev = item.source.abbreviation.upper()
            return source_abbrev in [src.upper() for src in target_sources]

        return False

    def _get_item_value_in_gp(self, item: Item) -> float | None:
        """Get item value converted to gold pieces.

        Args:
            item: The item to get value for

        Returns:
            Value in gold pieces or None if no value
        """
        if not item.value:
            return None

        if isinstance(item.value, int | float):
            # Assume value is in copper pieces, convert to GP
            return float(item.value) / 100

        # For complex value structures, try to extract numeric value
        # This is a simplified implementation - might need enhancement
        if hasattr(item.value, "amount"):
            amount = item.value.amount
            unit = getattr(item.value, "unit", "cp").lower()

            if unit in ["gp", "gold"]:
                return float(amount)
            elif unit in ["sp", "silver"]:
                return float(amount) / 10
            elif unit in ["cp", "copper"]:
                return float(amount) / 100
            else:
                # Unknown unit, assume GP
                return float(amount)

        return None

    def _is_consumable_item(self, item: Item) -> bool:
        """Determine if an item is consumable based on type and properties.

        Args:
            item: The item to check

        Returns:
            True if item is consumable
        """
        item_type = item.get_type_text().lower()
        consumable_types = ["potion", "scroll", "ammunition"]

        return item_type in consumable_types

    def _find_item_suggestions(
        self, name: str, sources: list[str] | None = None
    ) -> list[str]:
        """Find suggestions for a misspelled item name.

        Args:
            name: The item name to find suggestions for
            sources: Optional list of source abbreviations to limit suggestions

        Returns:
            List of suggested item names
        """
        item_type = ContentType("item")

        # Get items from specified sources or all sources
        if sources:
            all_items = []
            for source in sources:
                source_items = self.omnidexer.get_all_by_source(source)
                for item in source_items:
                    if isinstance(item, Item):
                        all_items.append(item)
        else:
            all_content = self.omnidexer.get_all_by_type(item_type)
            all_items = [item for item in all_content if isinstance(item, Item)]

        if not all_items:
            return []

        # Get all item names
        item_names = []
        for item in all_items:
            if isinstance(item, Item):
                item_names.append(item.name)

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(name, item_names, n=5, cutoff=0.4)

        return suggestions

    def get_available_types(self) -> list[str]:
        """Get list of all item types available.

        Returns:
            List of item types
        """
        item_type = ContentType("item")
        all_items = self.omnidexer.get_all_by_type(item_type)

        if not all_items:
            return []

        types = set()
        for item in all_items:
            if isinstance(item, Item):
                types.add(item.get_type_text().lower())

        return sorted(types)

    def get_available_rarities(self) -> list[str]:
        """Get list of all item rarities available.

        Returns:
            List of item rarities
        """
        item_type = ContentType("item")
        all_items = self.omnidexer.get_all_by_type(item_type)

        if not all_items:
            return []

        rarities = set()
        for item in all_items:
            if isinstance(item, Item):
                rarity = item.get_rarity_text()
                if rarity:
                    rarities.add(rarity.lower())

        return sorted(rarities)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about available items.

        Returns:
            Dictionary with item statistics
        """
        item_type = ContentType("item")
        all_items = self.omnidexer.get_all_by_type(item_type)

        if not all_items:
            return {"total": 0}

        stats: dict[str, Any] = {
            "total": len(all_items),
            "by_type": {},
            "by_rarity": {},
            "by_source": {},
            "types": self.get_available_types(),
            "rarities": self.get_available_rarities(),
        }

        for item in all_items:
            if isinstance(item, Item):
                # Count by type
                item_type_str = item.get_type_text()
                stats["by_type"][item_type_str] = (
                    stats["by_type"].get(item_type_str, 0) + 1
                )

                # Count by rarity
                rarity = item.get_rarity_text() or "common"
                stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1

                # Count by source
                if hasattr(item.source, "abbreviation"):
                    source = item.source.abbreviation
                    stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        return stats
