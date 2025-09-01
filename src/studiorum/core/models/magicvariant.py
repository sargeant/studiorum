"""Magic variant content model."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


@content_type(
    enum_value="magicvariant",
    file_patterns=["magicvariant", "magicvariants"],
    loader_type="json",
    statblock_tags=["magicvariant"],
)
class MagicVariant(BaseContent):
    """Magic variant model for magic item variations and generic templates.

    Magic variants represent templates that can be applied to create variations
    of magic items, such as +1/+2/+3 weapons or armor with different properties.
    """

    # Required fields
    variant_type: str = Field(
        ..., description="Type of magic variant (e.g., 'GV|DMG')", alias="type"
    )

    # Optional fields
    requires: list[dict[str, Any]] | None = Field(
        None, description="Requirements for items this variant can be applied to"
    )
    inherits: dict[str, Any] | None = Field(
        None, description="Properties and values inherited by items using this variant"
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Magic variant description entries"
    )
    edition: str | None = Field(
        None, description="Game edition this variant is from (classic, etc.)"
    )
    ammo: bool | None = Field(
        None, description="Whether this variant applies to ammunition"
    )
    armor: bool | None = Field(
        None, description="Whether this variant applies to armor"
    )
    weapon: bool | None = Field(
        None, description="Whether this variant applies to weapons"
    )
    generic: dict[str, Any] | None = Field(
        None, description="Generic item properties for this variant"
    )
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this variant",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this variant",
        alias="otherSources",
    )

    @field_validator("variant_type", mode="before")
    @classmethod
    def validate_variant_type(cls, v: Any) -> str:
        """Validate variant type."""
        if not v:
            raise ValueError("Magic variant type cannot be empty")
        return str(v)

    @field_validator("requires", mode="before")
    @classmethod
    def validate_requires(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate requirements structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
        return None

    @field_validator("inherits", mode="before")
    @classmethod
    def validate_inherits(cls, v: Any) -> dict[str, Any] | None:
        """Validate inherits structure."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Magic variant name cannot be empty")
        return str(v).strip()

    def get_variant_type(self) -> str:
        """Get the variant type."""
        return self.variant_type

    def has_requirements(self) -> bool:
        """Check if this variant has item requirements."""
        return bool(self.requires)

    def has_inherited_properties(self) -> bool:
        """Check if this variant has inherited properties."""
        return bool(self.inherits)

    def applies_to_ammunition(self) -> bool:
        """Check if this variant applies to ammunition."""
        return self.ammo is True

    def applies_to_armor(self) -> bool:
        """Check if this variant applies to armor."""
        return self.armor is True

    def applies_to_weapons(self) -> bool:
        """Check if this variant applies to weapons."""
        return self.weapon is True

    def is_generic_variant(self) -> bool:
        """Check if this is a generic variant template."""
        return "GV" in self.variant_type

    def get_edition(self) -> str:
        """Get the edition this variant is from, defaulting to 'current' if not specified."""
        return self.edition or "current"

    def get_requirement_count(self) -> int:
        """Get the number of requirements for this variant."""
        return len(self.requires) if self.requires else 0

    def get_inherited_properties(self) -> dict[str, Any]:
        """Get the inherited properties, returning empty dict if none."""
        return self.inherits or {}

    def matches_item_type(self, item_type: str) -> bool:
        """Check if this variant matches a specific item type requirement."""
        if not self.requires:
            return False

        for requirement in self.requires:
            if "type" in requirement:
                req_type = requirement["type"]
                if item_type in req_type or req_type in item_type:
                    return True

        return False

    def get_bonus_value(self) -> str | None:
        """Get the bonus value from inherited properties if available."""
        if not self.inherits:
            return None

        # Check common bonus fields
        bonus_fields = ["bonusWeapon", "bonusAc", "bonus"]
        for field in bonus_fields:
            if field in self.inherits:
                return str(self.inherits[field])

        return None

    def get_name_prefix(self) -> str | None:
        """Get the name prefix from inherited properties if available."""
        if not self.inherits:
            return None
        return self.inherits.get("namePrefix")

    def get_rarity(self) -> str | None:
        """Get the rarity from inherited properties if available."""
        if not self.inherits:
            return None
        return self.inherits.get("rarity")
