"""Item data models."""

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..error_types import BaseError
    from ..result import Result
    from ..text.tag_resolver import TagResolver
    from .processors import ItemProcessor

from pydantic import BaseModel, Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


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


@content_type(
    enum_value="item",
    file_patterns=["item", "items", "magicitem"],
    statblock_tags=["item"],
    loader_type="json",
)
class Item(BaseContent):
    """Represents a 5e item."""

    type: str | ItemType | None = Field(None, description="Item type")
    rarity: str | ItemRarity | None = Field(None, description="Item rarity")
    weight: int | float | None = Field(None, description="Item weight in pounds")
    value: int | float | ValueDetails | dict[str, Any] | None = Field(
        None, description="Item value"
    )
    entries: list[Entry] | None = Field(None, description="Item description")

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

    # Special item categories
    staff: bool | None = Field(None, description="Is a staff")
    wand: bool | None = Field(None, description="Is a wand")
    rod: bool | None = Field(None, description="Is a rod")
    weapon: bool | None = Field(None, description="Is a weapon")
    potion: bool | None = Field(None, description="Is a potion")
    scroll: bool | None = Field(None, description="Is a scroll")
    wondrous: bool | None = Field(None, description="Is a wondrous item")
    tattoo: bool | None = Field(None, description="Is a tattoo")

    # Spell-related data
    attached_spells: dict[str, Any] | list[str] | None = Field(
        None, alias="attachedSpells", description="Attached spells with charges"
    )

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

    @field_validator("rarity", mode="before")
    @classmethod
    def parse_rarity(cls, v: Any) -> Any:
        """Parse rarity field, converting 'none' string to None."""
        if v == "none":
            return None
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

        # Handle abbreviated type formats
        type_str = str(self.type)

        # First try to resolve using the 5etools metadata system for $G|DMG format
        if "|" in type_str or type_str.startswith("$"):
            type_metadata = self._get_type_metadata(type_str)
            if type_metadata and "name" in type_metadata:
                return str(type_metadata["name"])

        # Map common abbreviations to full names based on 5etools data
        type_mappings = {
            "M": "melee weapon",
            "R": "ranged weapon",
            "P": "potion",
            "A": "armor",
            "S": "shield",
            "LA": "light armor",
            "MA": "medium armor",
            "HA": "heavy armor",
            "G": "adventuring gear",
            "RG": "ring",
            "WD": "wand",
            "RD": "rod",
            "SC": "scroll",
            "MNT": "mount",
            "VEH": "vehicle",
            "SHP": "ship",
            "TAH": "tack and harness",
            "TG": "trade good",
            "T": "tool",
            "AT": "artisan's tools",
            "GS": "gaming set",
            "INS": "instrument",
            "SCF": "spellcasting focus",
            "EXP": "explosive",
            "FD": "food",
            "GV": "generic variant",
            "TB": "trinket",
            "AIR": "vehicle (air)",
            "IDG": "magic item",
            "SPC": "specific variant",
            "OTH": "other",
        }

        if "|" in type_str:
            # Handle "M|XPHB" format
            abbreviation = type_str.split("|")[0]
            return type_mappings.get(abbreviation, type_str)
        else:
            # Handle simple "M" or "INS" format
            return type_mappings.get(type_str, type_str)

    def get_category_text(self) -> str:
        """Get item category text (Staff, Wand, etc.)."""
        if getattr(self, "staff", None):
            return "Staff"
        elif getattr(self, "wand", None):
            return "Wand"
        elif getattr(self, "rod", None):
            return "Rod"
        elif getattr(self, "potion", None):
            return "Potion"
        elif getattr(self, "scroll", None):
            return "Scroll"
        elif getattr(self, "wondrous", None):
            return "Wondrous item"
        elif getattr(self, "tattoo", None):
            return "Tattoo"
        return ""

    def get_spell_table_data(self) -> list[dict[str, Any]]:
        """Get spell table data for items with attached spells."""
        if (
            not hasattr(self, "attached_spells")
            or not self.attached_spells
            or not isinstance(self.attached_spells, dict)
            or "charges" not in self.attached_spells
        ):
            return []

        spell_data = []
        charges_data = self.attached_spells["charges"]

        for charge_cost, spells in charges_data.items():
            for spell_name in spells:
                spell_data.append({"name": spell_name, "charges": int(charge_cost)})

        # Sort by charge cost, then by name
        spell_data.sort(key=lambda x: (x["charges"], x["name"]))
        return spell_data

    def has_spell_table(self) -> bool:
        """Check if item has attached spells for table display."""
        return bool(
            hasattr(self, "attached_spells")
            and self.attached_spells
            and isinstance(self.attached_spells, dict)
            and "charges" in self.attached_spells
        )

    def get_rarity_text(self) -> str:
        """Get formatted rarity text without attunement info."""
        if not self.rarity or self.rarity == "none":
            return ""

        if isinstance(self.rarity, ItemRarity):
            rarity_text = self.rarity.value
        else:
            rarity_text = str(self.rarity)

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
        """Get item description text using modern service patterns."""
        processor = self.get_processor()

        try:
            # Try to get tag resolver from service container
            from ..container import get_global_container
            from ..result import Error
            from ..text.tag_resolver import TagResolver

            container = get_global_container()
            tag_resolver = container.get_service_sync(TagResolver)

            result = processor.get_description_with_context(tag_resolver)
            if isinstance(result, Error):
                return ""
            return result.unwrap()

        except Exception:
            # Fallback to simple text extraction
            return self._extract_simple_text_from_entries(self.entries or [])

    @staticmethod
    def _extract_simple_text_from_entries(entries: list[Any]) -> str:
        """Extract simple text from entries without processing."""
        if not entries:
            return ""

        text_parts = []

        def extract_text_recursive(entry: Any) -> None:
            if isinstance(entry, str):
                text_parts.append(entry)
            elif hasattr(entry, "model_dump"):
                # For Pydantic models, get the dict representation
                entry_data = entry.model_dump()
                extract_text_recursive(entry_data)
            elif isinstance(entry, dict):
                # Handle dict entries
                # Always include name if present (for entries with names)
                if "name" in entry:
                    text_parts.append(str(entry["name"]))

                # Always include "by" if present (for quote attributions)
                if "by" in entry:
                    text_parts.append(str(entry["by"]))

                if "text" in entry:
                    text_parts.append(str(entry["text"]))
                elif "entries" in entry:
                    # Recursively process nested entries
                    for nested_entry in entry["entries"]:
                        extract_text_recursive(nested_entry)
                else:
                    # Try to extract any string values from the dict (excluding name and by which we already handled)
                    for key, value in entry.items():
                        if key not in ("name", "by") and isinstance(value, str):
                            text_parts.append(value)
                        elif isinstance(value, list):
                            for item in value:
                                extract_text_recursive(item)
            elif isinstance(entry, list):
                for item in entry:
                    extract_text_recursive(item)
            else:
                text_parts.append(str(entry))

        for entry in entries:
            extract_text_recursive(entry)

        return " ".join(text_parts)

    def get_item_metadata_line(self) -> str:
        """Get formatted metadata line (category, type, rarity, attunement)."""
        parts = []

        # Add category (Staff, Wand, etc.)
        category_text = self.get_category_text()
        if category_text:
            parts.append(category_text.lower())

        # Add type (but avoid duplication with category)
        type_text = self.get_type_text()
        if type_text and type_text.lower() != category_text.lower():
            parts.append(type_text)

        # Add rarity with attunement
        rarity_text = self.get_enhanced_rarity_text()
        if rarity_text:
            parts.append(rarity_text)

        result = ", ".join(parts) if parts else ""
        # Capitalize the first letter
        return result[0].upper() + result[1:] if result else ""

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

    def _get_type_metadata(self, type_str: str) -> dict[str, Any] | None:
        """Get type metadata for item type resolution."""
        try:
            from ..loaders.json_loader import JsonDataLoader

            return JsonDataLoader.get_shared_type_metadata(type_str)
        except Exception:
            # Silently fall back if metadata not available
            return None

    def get_type_entries(self) -> list[str]:
        """Get entries from the item type definition for standard descriptions."""
        type_str = str(self.type)
        type_metadata = self._get_type_metadata(type_str)

        if type_metadata and "entries" in type_metadata and type_metadata["entries"]:
            return [str(entry) for entry in type_metadata["entries"]]
        return []

    def get_processor(self) -> "ItemProcessor":
        """Get processor for this item that can work with services."""
        from .processors import ItemProcessor

        return ItemProcessor(self)

    def resolve_tags_with_service(
        self, tag_resolver: "TagResolver"
    ) -> "Result[Item, BaseError]":
        """Resolve tags using provided tag resolver service."""
        processor = self.get_processor()
        return processor.resolve_tags(tag_resolver)
