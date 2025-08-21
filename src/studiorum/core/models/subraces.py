"""Subrace data models for racial variants like hill dwarfs and high elfs."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry, validate_entries


@content_type(
    enum_value="subrace",
    file_patterns=["race", "races"],  # Subraces are embedded in race files
    statblock_tags=["subrace"],
    loader_type="json",
)
class Subrace(BaseContent):
    """Racial variants like hill dwarfs, high elfs, and tiefling bloodlines."""

    race_name: str = Field(..., alias="raceName", description="Name of the parent race")
    race_source: str = Field(
        ..., alias="raceSource", description="Source of the parent race"
    )
    ability: list[dict[str, Any]] | None = Field(
        None, description="Ability score increases"
    )
    skill_proficiencies: list[dict[str, Any]] | None = Field(
        None, alias="skillProficiencies", description="Skill proficiencies granted"
    )
    weapon_proficiencies: list[dict[str, Any]] | None = Field(
        None, alias="weaponProficiencies", description="Weapon proficiencies granted"
    )
    armor_proficiencies: list[dict[str, Any]] | None = Field(
        None, alias="armorProficiencies", description="Armor proficiencies granted"
    )
    tool_proficiencies: list[dict[str, Any]] | None = Field(
        None, alias="toolProficiencies", description="Tool proficiencies granted"
    )
    language_proficiencies: list[dict[str, Any]] | None = Field(
        None,
        alias="languageProficiencies",
        description="Language proficiencies granted",
    )
    darkvision: int | None = Field(None, description="Darkvision range in feet")
    speed: dict[str, Any] | None = Field(None, description="Movement speeds")
    resist: list[str] | None = Field(None, description="Damage resistances")
    immune: list[str] | None = Field(None, description="Damage immunities")
    condition_immune: list[str] | None = Field(
        None, alias="conditionImmune", description="Condition immunities"
    )
    spellcasting_ability: str | None = Field(
        None,
        alias="spellcastingAbility",
        description="Spellcasting ability for racial spells",
    )
    additional_spells: list[dict[str, Any]] | None = Field(
        None, alias="additionalSpells", description="Additional spells granted"
    )
    has_fluff: bool | None = Field(
        None, alias="hasFluff", description="Whether fluff content exists"
    )
    has_fluff_images: bool | None = Field(
        None, alias="hasFluffImages", description="Whether fluff images exist"
    )
    reprinted_as: list[dict[str, str]] | None = Field(
        None, alias="reprintedAs", description="Later reprints of this subrace"
    )
    entries: list[Entry] = Field(..., description="Subrace traits and abilities")

    @field_validator("race_name")
    @classmethod
    def validate_race_name(cls, v: str) -> str:
        """Validate race name is not empty."""
        if not v.strip():
            raise ValueError("Race name cannot be empty")
        return v.strip()

    @field_validator("darkvision")
    @classmethod
    def validate_darkvision(cls, v: int | None) -> int | None:
        """Validate darkvision range."""
        if v is not None and (v < 0 or v > 240):
            raise ValueError("Darkvision range should be between 0 and 240 feet")
        return v

    @field_validator("entries", mode="before")
    @classmethod
    def validate_entries(cls, v: list[str | dict[str, Any]] | None) -> list[Entry]:
        """Validate entries using the standard validator."""
        if v is None:
            return []
        if not isinstance(v, list):
            # Malformed data - let Pydantic's normal validation catch it
            raise ValueError(f"Expected list or None for entries, got {type(v)}")
        return validate_entries(v)

    def get_race_identifier(self) -> str:
        """Get unique identifier for the parent race."""
        return f"{self.race_name}|{self.race_source}"

    def get_subrace_identifier(self) -> str:
        """Get unique identifier for this subrace."""
        return f"{self.race_name}|{self.race_source}|{self.name}|{self.source.abbreviation}"
