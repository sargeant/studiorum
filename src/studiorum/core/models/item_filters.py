"""Item filtering models for advanced item collection and filtering."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from .items import ItemRarity, ItemType

if TYPE_CHECKING:
    from .items import Item


class ItemFilterCriteria(BaseModel):
    """Comprehensive criteria for filtering items with validation.

    This model supports both treasure hoard use cases (specific item names) and
    shop/equipment list use cases (type/rarity-based filtering) with advanced
    filtering options for value, weight, and item-specific properties.
    """

    # Type filtering
    item_types: list[str | ItemType] | None = Field(
        None, description="Item types to include"
    )

    # Rarity filtering
    rarities: list[str | ItemRarity] | None = Field(
        None, description="Item rarities to include"
    )
    magic_only: bool = Field(False, description="Include only magic items")
    mundane_only: bool = Field(False, description="Include only non-magic items")

    # Value filtering
    min_value: float | None = Field(None, ge=0, description="Minimum value in gp")
    max_value: float | None = Field(None, ge=0, description="Maximum value in gp")

    # Weight filtering
    max_weight: float | None = Field(None, ge=0, description="Maximum weight in lbs")

    # Weapon filtering
    weapon_categories: list[str] | None = Field(
        None, description="Weapon categories (martial, simple, etc.)"
    )
    weapon_properties: list[str] | None = Field(
        None, description="Required weapon properties"
    )
    damage_types: list[str] | None = Field(None, description="Weapon damage types")

    # Armor filtering
    armor_types: list[str] | None = Field(
        None, description="Armor types (light, medium, heavy)"
    )
    min_ac: int | None = Field(None, ge=10, description="Minimum AC value")
    max_strength_req: int | None = Field(
        None, ge=0, le=20, description="Maximum STR requirement"
    )
    no_strength_req: bool = Field(
        False, description="Exclude items with STR requirements"
    )
    no_stealth_disadvantage: bool = Field(
        False, description="Exclude items causing stealth disadvantage"
    )

    # Magic item filtering
    requires_attunement: bool | None = Field(
        None, description="Filter by attunement requirement"
    )
    attunement_type: str | None = Field(
        None, description="Specific attunement requirement (e.g., 'by a spellcaster')"
    )
    has_charges: bool | None = Field(None, description="Filter by charge/use system")
    consumable: bool | None = Field(None, description="Filter for consumable items")

    # Source filtering
    sources: list[str] | None = Field(None, description="Source book abbreviations")

    # Name filtering (for treasure hoard use case)
    item_names: list[str] | None = Field(
        None, description="Specific item names to include"
    )

    # Equipment pack filtering
    equipment_packs: list[str] | None = Field(
        None, description="Standard equipment pack names"
    )

    @field_validator("item_types")
    @classmethod
    def normalize_item_types(
        cls, v: list[str | ItemType] | None
    ) -> list[str | ItemType] | None:
        """Normalize item types to lowercase strings."""
        if v is None:
            return v

        normalized: list[str | ItemType] = []
        for item_type in v:
            if isinstance(item_type, ItemType):
                normalized.append(item_type)
            else:
                # Try to match to enum first, otherwise keep as string
                type_str = item_type.strip().lower()
                try:
                    enum_match = ItemType(type_str)
                    normalized.append(enum_match)
                except ValueError:
                    # Keep as normalized string for fuzzy matching
                    normalized.append(type_str)

        return normalized

    @field_validator("rarities")
    @classmethod
    def normalize_rarities(
        cls, v: list[str | ItemRarity] | None
    ) -> list[str | ItemRarity] | None:
        """Normalize rarity values."""
        if v is None:
            return v

        normalized: list[str | ItemRarity] = []
        for rarity in v:
            if isinstance(rarity, ItemRarity):
                normalized.append(rarity)
            else:
                # Try to match to enum first, otherwise keep as string
                rarity_str = rarity.strip().lower()
                try:
                    enum_match = ItemRarity(rarity_str)
                    normalized.append(enum_match)
                except ValueError:
                    # Keep as normalized string for fuzzy matching
                    normalized.append(rarity_str)

        return normalized

    @field_validator("weapon_categories")
    @classmethod
    def normalize_weapon_categories(cls, v: list[str] | None) -> list[str] | None:
        """Normalize weapon category names."""
        if v is None:
            return v
        return [cat.strip().lower() for cat in v if cat.strip()]

    @field_validator("weapon_properties")
    @classmethod
    def normalize_weapon_properties(cls, v: list[str] | None) -> list[str] | None:
        """Normalize weapon property names."""
        if v is None:
            return v
        return [prop.strip().lower() for prop in v if prop.strip()]

    @field_validator("damage_types")
    @classmethod
    def normalize_damage_types(cls, v: list[str] | None) -> list[str] | None:
        """Normalize damage type names."""
        if v is None:
            return v
        return [dt.strip().lower() for dt in v if dt.strip()]

    @field_validator("armor_types")
    @classmethod
    def normalize_armor_types(cls, v: list[str] | None) -> list[str] | None:
        """Normalize armor type names."""
        if v is None:
            return v
        return [at.strip().lower() for at in v if at.strip()]

    @field_validator("sources")
    @classmethod
    def normalize_sources(cls, v: list[str] | None) -> list[str] | None:
        """Normalize source abbreviations to uppercase."""
        if v is None:
            return v
        return [src.strip().upper() for src in v if src.strip()]

    @field_validator("item_names")
    @classmethod
    def normalize_item_names(cls, v: list[str] | None) -> list[str] | None:
        """Normalize item names for consistent matching."""
        if v is None:
            return v
        return [name.strip() for name in v if name.strip()]

    @field_validator("equipment_packs")
    @classmethod
    def normalize_equipment_packs(cls, v: list[str] | None) -> list[str] | None:
        """Normalize equipment pack names."""
        if v is None:
            return v
        return [pack.strip().lower() for pack in v if pack.strip()]

    def model_post_init(self, __context: dict | None = None) -> None:
        """Validate logical consistency of filter criteria."""
        # Check value range consistency
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value cannot be greater than max_value")

        # Check conflicting magic/mundane filters
        if self.magic_only and self.mundane_only:
            raise ValueError("Cannot filter for both magic and mundane items only")

        # Check conflicting attunement filters
        if self.requires_attunement is False and self.attunement_type is not None:
            raise ValueError(
                "Cannot specify attunement type while excluding attunement"
            )

        # Validate that at least one filtering criterion is provided
        has_criteria = any(
            [
                self.item_types is not None,
                self.rarities is not None,
                self.magic_only,
                self.mundane_only,
                self.min_value is not None,
                self.max_value is not None,
                self.max_weight is not None,
                self.weapon_categories is not None,
                self.weapon_properties is not None,
                self.damage_types is not None,
                self.armor_types is not None,
                self.min_ac is not None,
                self.max_strength_req is not None,
                self.no_strength_req,
                self.no_stealth_disadvantage,
                self.requires_attunement is not None,
                self.attunement_type is not None,
                self.has_charges is not None,
                self.consumable is not None,
                self.sources is not None,
                self.item_names is not None,
                self.equipment_packs is not None,
            ]
        )

        if not has_criteria:
            raise ValueError("At least one filtering criterion must be provided")

    def is_name_only_filter(self) -> bool:
        """Check if this is a name-only filter (treasure hoard use case).

        Returns:
            True if only item names are specified
        """
        return self.item_names is not None and all(
            criterion is None or (isinstance(criterion, bool) and not criterion)
            for attr, criterion in self.__dict__.items()
            if attr != "item_names"
        )

    def matches_item_type(self, item_type: str | ItemType) -> bool:
        """Check if an item type matches the filter criteria.

        Args:
            item_type: The item type to check

        Returns:
            True if the item type matches the criteria
        """
        if self.item_types is None:
            return True  # No type filtering

        # Convert to string for comparison
        type_str = (
            item_type.value if isinstance(item_type, ItemType) else str(item_type)
        )
        type_str = type_str.lower()

        for filter_type in self.item_types:
            if isinstance(filter_type, ItemType):
                if filter_type.value == type_str:
                    return True
            elif isinstance(filter_type, str):
                if filter_type == type_str:
                    return True

        return False

    def matches_rarity(self, rarity: str | ItemRarity | None) -> bool:
        """Check if an item rarity matches the filter criteria.

        Args:
            rarity: The item rarity to check

        Returns:
            True if the rarity matches the criteria
        """
        if self.rarities is None:
            return True  # No rarity filtering

        if rarity is None:
            return False

        # Convert to string for comparison
        rarity_str = rarity.value if isinstance(rarity, ItemRarity) else str(rarity)
        rarity_str = rarity_str.lower()

        for filter_rarity in self.rarities:
            if isinstance(filter_rarity, ItemRarity):
                if filter_rarity.value == rarity_str:
                    return True
            elif isinstance(filter_rarity, str):
                if filter_rarity == rarity_str:
                    return True

        return False


class ItemCollectionResult(BaseModel):
    """Result of item collection operation with metadata."""

    items: list = Field(default_factory=list, description="Collected items")
    total_count: int = Field(0, description="Total number of items collected")
    by_type: dict[str, int] = Field(
        default_factory=dict, description="Count by item type"
    )
    by_rarity: dict[str, int] = Field(
        default_factory=dict, description="Count by item rarity"
    )
    sources_used: list[str] = Field(
        default_factory=list, description="Source books used"
    )
    unresolved_names: list[str] = Field(
        default_factory=list, description="Item names that couldn't be resolved"
    )
    suggestions: dict[str, list[str]] = Field(
        default_factory=dict, description="Suggestions for unresolved names"
    )

    def add_item(self, item: "Item", source: str | None = None) -> None:
        """Add an item to the collection with metadata tracking."""
        self.items.append(item)
        self.total_count += 1

        # Track by type
        item_type = item.get_type_text()
        self.by_type[item_type] = self.by_type.get(item_type, 0) + 1

        # Track by rarity
        rarity = item.get_rarity_text() or "common"
        self.by_rarity[rarity] = self.by_rarity.get(rarity, 0) + 1

        # Track sources
        if source and source not in self.sources_used:
            self.sources_used.append(source)

    def add_unresolved(self, name: str, suggestions: list[str] | None = None) -> None:
        """Add an unresolved item name with optional suggestions."""
        if name not in self.unresolved_names:
            self.unresolved_names.append(name)

        if suggestions:
            self.suggestions[name] = suggestions

    def get_type_summary(self) -> str:
        """Get a formatted summary of items by type."""
        if not self.by_type:
            return "No items collected"

        parts = []
        for item_type in sorted(self.by_type.keys()):
            count = self.by_type[item_type]
            parts.append(f"{item_type.title()}: {count}")

        return ", ".join(parts)

    def get_rarity_summary(self) -> str:
        """Get a formatted summary of items by rarity."""
        if not self.by_rarity:
            return "No items collected"

        # Sort rarities in logical order
        rarity_order = [
            "common",
            "uncommon",
            "rare",
            "very rare",
            "legendary",
            "artifact",
        ]
        sorted_rarities = []

        for rarity in rarity_order:
            if rarity in self.by_rarity:
                sorted_rarities.append(rarity)

        # Add any remaining rarities not in the standard order
        for rarity in sorted(self.by_rarity.keys()):
            if rarity not in sorted_rarities:
                sorted_rarities.append(rarity)

        parts = []
        for rarity in sorted_rarities:
            count = self.by_rarity[rarity]
            parts.append(f"{rarity.title()}: {count}")

        return ", ".join(parts)
