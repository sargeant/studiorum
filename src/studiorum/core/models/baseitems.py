"""BaseItem content type models for D&D 5e.

Provides Pydantic models for base items that serve as foundations
for magic variants and item generation systems.
"""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="baseitem",
    file_patterns=["baseitem", "baseitems", "items-base"],
    loader_type="json",
    statblock_tags=["baseitem"],
)
class BaseItem(BaseContent):
    """A base item that can serve as foundation for magic variants.

    Base items represent the fundamental properties of equipment
    without magical enhancements, serving as templates for
    magic item generation.
    """

    # Item type and classification
    type: str | None = Field(None, description="Item type code")
    rarity: str | None = Field(None, description="Base rarity")
    value_rarity: str | None = Field(
        None, alias="valueRarity", description="Value-based rarity"
    )

    # Physical properties
    weight: float | None = Field(None, description="Item weight")
    value: int | None = Field(None, description="Base value in copper pieces")

    # Weapon properties
    weapon_category: str | None = Field(
        None, alias="weaponCategory", description="Weapon category (simple, martial)"
    )
    property: list[str] = Field(
        default_factory=list, description="Weapon/armor properties"
    )
    mastery: list[str] = Field(
        default_factory=list, description="2024 weapon mastery properties"
    )
    range: str | None = Field(None, description="Weapon range")
    reload: int | None = Field(None, description="Reload value for firearms")
    dmg1: str | None = Field(None, description="Primary damage dice")
    dmg2: str | None = Field(None, description="Secondary damage dice")
    dmg_type: str | None = Field(None, alias="dmgType", description="Damage type")

    # Item flags
    weapon: bool = Field(False, description="Is this a weapon")
    armor: bool = Field(False, description="Is this armor")
    shield: bool = Field(False, description="Is this a shield")
    firearm: bool = Field(False, description="Is this a firearm")
    arrow: bool = Field(False, description="Is this an arrow/ammunition")

    # Special properties
    age: str | None = Field(None, description="Technological age (modern, futuristic)")
    ammo_type: str | None = Field(
        None, alias="ammoType", description="Required ammunition type"
    )
    ac: int | None = Field(None, description="Armor class for armor")
    strength: str | None = Field(None, description="Strength requirement")
    stealth: bool | None = Field(None, description="Stealth disadvantage")

    # Edition tracking
    edition: str | None = Field(None, description="D&D edition (classic, one)")

    def get_display_name(self) -> str:
        """Get display name for the base item."""
        return self.name

    def is_weapon(self) -> bool:
        """Check if this is a weapon."""
        return self.weapon or bool(self.dmg1)

    def is_armor(self) -> bool:
        """Check if this is armor."""
        return self.armor or self.ac is not None

    def is_shield(self) -> bool:
        """Check if this is a shield."""
        return self.shield

    def is_firearm(self) -> bool:
        """Check if this is a firearm."""
        return self.firearm

    def has_properties(self) -> bool:
        """Check if this item has weapon/armor properties."""
        return len(self.property) > 0

    def has_mastery(self) -> bool:
        """Check if this item has mastery properties."""
        return len(self.mastery) > 0

    def get_properties(self) -> list[str]:
        """Get list of item properties."""
        return self.property.copy()

    def get_mastery_properties(self) -> list[str]:
        """Get list of mastery properties."""
        return self.mastery.copy()

    def requires_ammunition(self) -> bool:
        """Check if this weapon requires ammunition."""
        return self.ammo_type is not None

    def get_damage_info(self) -> dict[str, Any]:
        """Get damage information for weapons."""
        info = {}
        if self.dmg1:
            info["primary"] = self.dmg1
        if self.dmg2:
            info["secondary"] = self.dmg2
        if self.dmg_type:
            info["type"] = self.dmg_type
        return info

    def has_range(self) -> bool:
        """Check if this weapon has range information."""
        return self.range is not None

    def is_ranged_weapon(self) -> bool:
        """Check if this is a ranged weapon."""
        return self.range is not None or self.firearm

    def get_item_category(self) -> str:
        """Get the primary category of this item."""
        if self.is_weapon():
            return "Weapon"
        elif self.is_armor():
            return "Armor"
        elif self.is_shield():
            return "Shield"
        elif self.arrow:
            return "Ammunition"
        else:
            return "Item"
