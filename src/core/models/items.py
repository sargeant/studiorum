"""Item data models."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .content import BaseContent


class ItemType(str, Enum):
    """Enumeration of item types."""

    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    ADVENTURING_GEAR = "adventuring gear"
    TOOL = "tool"
    MOUNT = "mount"
    VEHICLE = "vehicle"
    TREASURE = "treasure"
    WONDROUS_ITEM = "wondrous item"
    POTION = "potion"
    SCROLL = "scroll"
    RING = "ring"
    ROD = "rod"
    STAFF = "staff"
    WAND = "wand"
    AMMUNITION = "ammunition"


class ItemRarity(str, Enum):
    """Enumeration of item rarities."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very rare"
    LEGENDARY = "legendary"
    ARTIFACT = "artifact"
    VARIES = "varies"
    UNKNOWN = "unknown"


class ItemProperty(BaseModel):
    """Represents an item property."""

    name: str = Field(..., description="Property name")
    description: Optional[str] = Field(None, description="Property description")


class WeaponData(BaseModel):
    """Weapon-specific data."""

    damage: Optional[str] = Field(None, description="Damage dice")
    damage_type: Optional[str] = Field(
        None, alias="damageType", description="Damage type"
    )
    properties: Optional[List[str]] = Field(None, description="Weapon properties")
    range: Optional[str] = Field(None, description="Weapon range")
    weapon_category: Optional[str] = Field(
        None, alias="weaponCategory", description="Weapon category"
    )


class ArmorData(BaseModel):
    """Armor-specific data."""

    ac: Optional[int] = Field(None, description="Base armor class")
    ac_from: Optional[List[str]] = Field(
        None, alias="acFrom", description="AC calculation method"
    )
    strength: Optional[int] = Field(None, description="Strength requirement")
    stealth: Optional[bool] = Field(None, description="Stealth disadvantage")
    armor_type: Optional[str] = Field(None, alias="armorType", description="Armor type")


class Item(BaseContent):
    """Represents a D&D item."""

    type: Union[str, ItemType] = Field(..., description="Item type")
    rarity: Optional[Union[str, ItemRarity]] = Field(None, description="Item rarity")
    weight: Optional[Union[int, float]] = Field(
        None, description="Item weight in pounds"
    )
    value: Optional[Union[int, float, Dict[str, Any]]] = Field(
        None, description="Item value"
    )
    entries: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None, description="Item description"
    )

    # Optional item-specific data
    weapon_data: Optional[WeaponData] = Field(
        None, description="Weapon-specific properties"
    )
    armor_data: Optional[ArmorData] = Field(
        None, description="Armor-specific properties"
    )

    # Magic item properties
    requires_attunement: Optional[Union[bool, str]] = Field(
        None, alias="reqAttune", description="Attunement requirement"
    )
    charges: Optional[Union[int, str, Dict[str, Any]]] = Field(
        None, description="Item charges"
    )
    recharge: Optional[str] = Field(None, description="Recharge conditions")

    # Weapon properties (for backwards compatibility)
    damage: Optional[str] = Field(None, description="Weapon damage")
    damage_type: Optional[str] = Field(
        None, alias="damageType", description="Weapon damage type"
    )
    properties: Optional[List[str]] = Field(None, description="Weapon properties")
    range: Optional[str] = Field(None, description="Weapon range")
    weapon_category: Optional[str] = Field(
        None, alias="weaponCategory", description="Weapon category"
    )

    # Armor properties (for backwards compatibility)
    ac: Optional[int] = Field(None, description="Armor class")
    ac_from: Optional[List[str]] = Field(None, alias="acFrom", description="AC sources")
    strength: Optional[int] = Field(None, description="Strength requirement")
    stealth: Optional[bool] = Field(None, description="Stealth disadvantage")
    armor_type: Optional[str] = Field(None, alias="armorType", description="Armor type")

    def model_post_init(self, __context) -> None:
        """Post-process parsed data."""
        # Create weapon_data from individual weapon fields
        if any(
            [
                self.damage,
                self.damage_type,
                self.properties,
                self.range,
                self.weapon_category,
            ]
        ):
            self.weapon_data = WeaponData(
                damage=self.damage,
                damage_type=self.damage_type,
                properties=self.properties,
                range=self.range,
                weapon_category=self.weapon_category,
            )

        # Create armor_data from individual armor fields
        if any([self.ac, self.ac_from, self.strength, self.stealth, self.armor_type]):
            self.armor_data = ArmorData(
                ac=self.ac,
                ac_from=self.ac_from,
                strength=self.strength,
                stealth=self.stealth,
                armor_type=self.armor_type,
            )

    def is_magic_item(self) -> bool:
        """Check if this is a magic item."""
        if self.rarity and self.rarity not in [ItemRarity.COMMON, ItemRarity.UNKNOWN]:
            return True
        return bool(self.requires_attunement or self.charges)

    def is_weapon(self) -> bool:
        """Check if this is a weapon."""
        return (
            self.type == ItemType.WEAPON
            or self.weapon_data is not None
            or bool(self.damage)
        )

    def is_armor(self) -> bool:
        """Check if this is armor."""
        return (
            self.type in [ItemType.ARMOR, ItemType.SHIELD]
            or self.armor_data is not None
            or self.ac is not None
        )

    def get_type_text(self) -> str:
        """Get formatted item type text."""
        if isinstance(self.type, ItemType):
            return self.type.value
        return str(self.type)

    def get_rarity_text(self) -> str:
        """Get formatted rarity text."""
        if not self.rarity:
            return ""

        if isinstance(self.rarity, ItemRarity):
            rarity_text = self.rarity.value
        else:
            rarity_text = str(self.rarity)

        # Add attunement requirement
        if self.requires_attunement:
            if isinstance(self.requires_attunement, bool):
                return f"{rarity_text} (requires attunement)"
            else:
                return f"{rarity_text} (requires attunement {self.requires_attunement})"

        return rarity_text

    def get_weight_text(self) -> str:
        """Get formatted weight text."""
        if self.weight is None:
            return ""

        if self.weight == 1:
            return "1 lb."
        return f"{self.weight} lbs."

    def get_value_text(self) -> str:
        """Get formatted value text."""
        if not self.value:
            return ""

        if isinstance(self.value, (int, float)):
            # Convert to copper pieces for calculation
            copper_value = (
                int(self.value * 100) if isinstance(self.value, float) else self.value
            )

            if copper_value >= 100:
                gp = copper_value // 100
                remainder = copper_value % 100
                if remainder == 0:
                    return f"{gp:,} gp" if gp > 1 else "1 gp"
                else:
                    return f"{gp} gp, {remainder} cp"
            elif copper_value >= 10:
                sp = copper_value // 10
                remainder = copper_value % 10
                if remainder == 0:
                    return f"{sp} sp"
                else:
                    return f"{sp} sp, {remainder} cp"
            else:
                return f"{copper_value} cp"
        elif isinstance(self.value, dict):
            # Handle complex value format
            return str(self.value)

        return str(self.value)

    def get_description_text(self) -> str:
        """Extract text from complex entry structures."""
        if not self.entries:
            return ""
        return self._extract_text_from_entries(self.entries)

    def _extract_text_from_entries(self, entries) -> str:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                result = self._extract_text_from_entries(entry)
                if result:
                    text_parts.append(result)
        elif isinstance(entries, dict):
            # Handle different entry types
            if "entries" in entries:
                result = self._extract_text_from_entries(entries["entries"])
                if result:
                    text_parts.append(result)
            elif "text" in entries:
                text_parts.append(entries["text"])
            # Add name if present (for structured sections)
            if "name" in entries:
                text_parts.append(f"**{entries['name']}**")
            # Handle lists within entries
            if "items" in entries and isinstance(entries["items"], list):
                for item in entries["items"]:
                    if isinstance(item, str):
                        text_parts.append(f"• {item}")
                    elif isinstance(item, dict) and "text" in item:
                        text_parts.append(f"• {item['text']}")
        elif isinstance(entries, str):
            text_parts.append(entries)

        return " ".join(text_parts) if text_parts else ""
