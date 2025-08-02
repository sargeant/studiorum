"""Item data models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent
from .spells import EntryContent, SpellEntry


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


class ValueDetails(BaseModel):
    """Structured item value information."""

    amount: int | float = Field(..., description="Value amount")
    unit: str | None = Field(None, description="Currency unit (gp, sp, cp)")
    note: str | None = Field(None, description="Additional value notes")


class ChargeDetails(BaseModel):
    """Structured item charges and recharge information."""

    charges: int = Field(..., description="Number of charges")
    recharge: str | None = Field(None, description="Recharge conditions")
    max_charges: int | None = Field(None, description="Maximum charges")
    recharge_amount: str | int | None = Field(None, description="Amount recharged")


class ItemProperty(BaseModel):
    """Represents an item property."""

    name: str = Field(..., description="Property name")
    description: str | None = Field(None, description="Property description")


class WeaponData(BaseModel):
    """Weapon-specific data."""

    damage: str | None = Field(None, description="Damage dice")
    damage_type: str | None = Field(None, alias="damageType", description="Damage type")
    properties: list[str] | None = Field(None, description="Weapon properties")
    range: str | None = Field(None, description="Weapon range")
    weapon_category: str | None = Field(
        None, alias="weaponCategory", description="Weapon category"
    )


class ArmorData(BaseModel):
    """Armor-specific data."""

    ac: int | None = Field(None, description="Base armor class")
    ac_from: list[str] | None = Field(
        None, alias="acFrom", description="AC calculation method"
    )
    strength: int | None = Field(None, description="Strength requirement")
    stealth: bool | None = Field(None, description="Stealth disadvantage")
    armor_type: str | None = Field(None, alias="armorType", description="Armor type")


class Item(BaseContent):
    """Represents a D&D item."""

    type: str | ItemType = Field(..., description="Item type")
    rarity: str | ItemRarity | None = Field(None, description="Item rarity")
    weight: int | float | None = Field(None, description="Item weight in pounds")
    value: int | float | ValueDetails | dict[str, Any] | None = Field(
        None, description="Item value"
    )
    entries: list[SpellEntry] | None = Field(None, description="Item description")

    # Optional item-specific data
    weapon_data: WeaponData | None = Field(
        None, description="Weapon-specific properties"
    )
    armor_data: ArmorData | None = Field(None, description="Armor-specific properties")

    # Magic item properties
    requires_attunement: bool | str | None = Field(
        None, alias="reqAttune", description="Attunement requirement"
    )
    charges: int | str | ChargeDetails | dict[str, Any] | None = Field(
        None, description="Item charges"
    )
    recharge: str | None = Field(None, description="Recharge conditions")

    # Weapon properties (for backwards compatibility)
    damage: str | None = Field(None, description="Weapon damage")
    damage_type: str | None = Field(
        None, alias="damageType", description="Weapon damage type"
    )
    properties: list[str] | None = Field(None, description="Weapon properties")
    range: str | None = Field(None, description="Weapon range")
    weapon_category: str | None = Field(
        None, alias="weaponCategory", description="Weapon category"
    )

    # Armor properties (for backwards compatibility)
    ac: int | None = Field(None, description="Armor class")
    ac_from: list[str] | None = Field(None, alias="acFrom", description="AC sources")
    strength: int | None = Field(None, description="Strength requirement")
    stealth: bool | None = Field(None, description="Stealth disadvantage")
    armor_type: str | None = Field(None, alias="armorType", description="Armor type")

    @field_validator("value", mode="before")
    @classmethod
    def parse_value(cls, v: Any) -> Any:
        """Parse value field, converting structured dicts to ValueDetails."""
        if isinstance(v, dict) and "amount" in v:
            # Convert structured value dict to ValueDetails
            return ValueDetails.model_validate(v)
        # Keep as-is for simple numbers and legacy complex dicts
        return v

    @field_validator("charges", mode="before")
    @classmethod
    def parse_charges(cls, v: Any) -> Any:
        """Parse charges field, converting structured dicts to ChargeDetails."""
        if isinstance(v, dict) and "charges" in v:
            # Convert structured charge dict to ChargeDetails
            return ChargeDetails.model_validate(v)
        # Keep as-is for simple numbers/strings and legacy dicts
        return v

    def model_post_init(self, __context: Any) -> None:
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
                damageType=self.damage_type,
                properties=self.properties,
                range=self.range,
                weaponCategory=self.weapon_category,
            )

        # Create armor_data from individual armor fields
        if any([self.ac, self.ac_from, self.strength, self.stealth, self.armor_type]):
            self.armor_data = ArmorData(
                ac=self.ac,
                acFrom=self.ac_from,
                strength=self.strength,
                stealth=self.stealth,
                armorType=self.armor_type,
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

        if isinstance(self.value, int | float):
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
        elif isinstance(self.value, ValueDetails):
            # Handle structured value format
            if self.value.unit:
                return f"{self.value.amount} {self.value.unit}"
            else:
                # Convert to standard currency format
                return self._format_currency_value(self.value.amount)
        elif isinstance(self.value, dict):
            # Handle legacy complex value format
            return str(self.value)

        return str(self.value)

    def get_description_text(self) -> str:
        """Extract text from complex entry structures."""
        if not self.entries:
            return ""
        return self._extract_text_from_entries(self.entries)

    def _extract_text_from_entries(self, entries: Any) -> str:
        """Recursively extract text from complex entry structures."""
        text_parts = []

        if isinstance(entries, list):
            for entry in entries:
                result = self._extract_text_from_entries(entry)
                if result:
                    text_parts.append(result)
        elif isinstance(entries, EntryContent):
            # Handle Pydantic EntryContent objects
            if entries.name:
                text_parts.append(f"**{entries.name}**")
            if entries.entries:
                result = self._extract_text_from_entries(entries.entries)
                if result:
                    text_parts.append(result)
            # Handle items if present in the extra fields
            if hasattr(entries, "items") and entries.items:
                items = entries.items
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str):
                            text_parts.append(f"• {item}")
                        elif isinstance(item, dict):
                            item_text_parts = []
                            if "name" in item:
                                item_text_parts.append(f"**{item['name']}**")
                            if "text" in item:
                                item_text_parts.append(item["text"])
                            if item_text_parts:
                                text_parts.append(f"• {' '.join(item_text_parts)}")
            # Handle text if present in the extra fields
            if hasattr(entries, "text") and entries.text:
                text_parts.append(entries.text)
        elif isinstance(entries, dict):
            # Handle structured dict entries (current 5etools format)
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
                    elif isinstance(item, dict):
                        item_text_parts = []
                        if "name" in item:
                            item_text_parts.append(f"**{item['name']}**")
                        if "text" in item:
                            item_text_parts.append(item["text"])
                        if item_text_parts:
                            text_parts.append(f"• {' '.join(item_text_parts)}")
        elif isinstance(entries, str):
            text_parts.append(entries)

        return " ".join(text_parts) if text_parts else ""

    def get_item_metadata_line(self) -> str:
        """Get formatted metadata line (type, rarity, attunement)."""
        parts = []

        # Add type
        type_text = self.get_type_text()
        if type_text:
            parts.append(type_text)

        # Add rarity with attunement
        rarity_text = self.get_enhanced_rarity_text()
        if rarity_text:
            parts.append(rarity_text)

        return ", ".join(parts) if parts else ""

    def get_enhanced_rarity_text(self) -> str:
        """Get enhanced rarity text with attunement."""
        rarity_text = self.get_rarity_text()
        attunement_text = self.get_attunement_text()

        if rarity_text and attunement_text:
            return f"{rarity_text} {attunement_text}"
        elif rarity_text:
            return rarity_text
        elif attunement_text:
            return attunement_text
        else:
            return ""

    def get_attunement_text(self) -> str:
        """Get formatted attunement requirements."""
        if not self.requires_attunement:
            return ""

        if isinstance(self.requires_attunement, bool):
            return "(requires attunement)"
        elif isinstance(self.requires_attunement, str):
            return f"(requires attunement {self.requires_attunement})"
        else:
            return "(requires attunement)"

    def get_ac_text(self) -> str:
        """Get formatted AC text for armor items."""
        if not self.armor_data or not self.armor_data.ac:
            if self.ac:  # fallback to direct ac field
                return str(self.ac)
            return ""

        ac_text = str(self.armor_data.ac)

        # Add AC calculation method if available
        if self.armor_data.ac_from:
            ac_from_text = " + ".join(self.armor_data.ac_from)
            ac_text += f" ({ac_from_text})"

        return ac_text

    def get_damage_text(self) -> str:
        """Get formatted damage text for weapon items."""
        if not self.weapon_data or not self.weapon_data.damage:
            if self.damage:  # fallback to direct damage field
                damage_text = str(self.damage)
                if self.damage_type:
                    damage_text += f" {self.damage_type}"
                return damage_text
            return ""

        damage_text = str(self.weapon_data.damage)
        if self.weapon_data.damage_type:
            damage_text += f" {self.weapon_data.damage_type}"

        return damage_text

    def get_range_text(self) -> str:
        """Get formatted range text for weapon items."""
        if not self.weapon_data or not self.weapon_data.range:
            if self.range:  # fallback to direct range field
                return str(self.range)
            return ""

        return str(self.weapon_data.range)

    def get_properties_text(self) -> list[str]:
        """Get formatted weapon properties list."""
        if not self.weapon_data or not self.weapon_data.properties:
            if self.properties:  # fallback to direct properties field
                return self.properties
            return []

        return self.weapon_data.properties

    def get_charges_text(self) -> str:
        """Get formatted charges/uses text."""
        if not self.charges:
            return ""

        if isinstance(self.charges, int | str):
            charge_text = str(self.charges)
            if isinstance(self.charges, int) and self.charges == 1:
                charge_text += " charge"
            else:
                charge_text += " charges"

            # Add recharge info if available
            if self.recharge:
                charge_text += f" (recharges {self.recharge})"

            return charge_text
        elif isinstance(self.charges, ChargeDetails):
            # Handle structured charge format
            charge_text = (
                f"{self.charges.charges} charge"
                if self.charges.charges == 1
                else f"{self.charges.charges} charges"
            )

            if self.charges.recharge:
                charge_text += f" (recharges {self.charges.recharge})"

            return charge_text
        elif isinstance(self.charges, dict):
            # Handle legacy complex charge structures
            if "charges" in self.charges:
                charges_val = self.charges["charges"]
                charge_text = (
                    f"{charges_val} charge"
                    if charges_val == 1
                    else f"{charges_val} charges"
                )

                if "recharge" in self.charges:
                    charge_text += f" (recharges {self.charges['recharge']})"

                return charge_text
            else:
                return str(self.charges)
        else:
            return str(self.charges)

    def _format_currency_value(self, amount: int | float) -> str:
        """Format numeric value as currency."""
        # Convert to copper pieces for calculation
        copper_value = int(amount * 100) if isinstance(amount, float) else amount

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
