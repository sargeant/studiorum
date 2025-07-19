"""Pydantic models for races."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .content import BaseContent


class AbilityAdjustment(BaseModel):
    """Represents an ability score adjustment for a race."""

    choose: dict[str, Any] | None = None
    cha: int | None = None
    con: int | None = None
    dex: int | None = None
    intelligence: int | None = Field(None, alias="int")
    strength: int | None = Field(None, alias="str")
    wis: int | None = None


class AdditionalSpell(BaseModel):
    """A spell that can be cast in addition to the race."""

    name: str | None = None
    level: int | None = None
    innate: dict[str, Any] | None = None
    known: dict[str, Any] | None = None
    ability: str | dict[str, Any] | None = None


class Race(BaseContent):
    """A playable race."""

    ability: list[AbilityAdjustment] = Field(default_factory=list)
    creature_types: list[str | dict[str, Any]] | None = Field(
        default=None, alias="creatureTypes"
    )
    size: list[str] = Field(default_factory=list)
    speed: int | dict[str, Any]
    entries: list[Any]
    additionalSpells: list[AdditionalSpell] | None = Field(
        default=None, alias="additionalSpells"
    )
    darkvision: int | None = None
    skill_proficiencies: list[dict[str, Any]] | None = Field(
        default=None, alias="skillProficiencies"
    )
    language_proficiencies: list[dict[str, Any]] | None = Field(
        default=None, alias="languageProficiencies"
    )
    weapon_proficiencies: list[dict[str, Any]] | None = Field(
        default=None, alias="weaponProficiencies"
    )
    armor_proficiencies: list[dict[str, Any]] | None = Field(
        default=None, alias="armorProficiencies"
    )
    tool_proficiencies: list[dict[str, Any]] | None = Field(
        default=None, alias="toolProficiencies"
    )
    saving_throw_proficiencies: list[dict[str, Any]] | None = Field(
        default=None, alias="savingThrowProficiencies"
    )
    condition_immunities: list[str] | None = Field(
        default=None, alias="conditionImmunities"
    )
    resistances: list[str] | None = None
    vulnerabilities: list[str] | None = None
