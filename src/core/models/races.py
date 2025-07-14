"""Pydantic models for races."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .content import BaseContent


class AbilityAdjustment(BaseModel):
    """Represents an ability score adjustment for a race."""

    choose: Optional[Dict[str, Any]] = None
    cha: Optional[int] = None
    con: Optional[int] = None
    dex: Optional[int] = None
    intelligence: Optional[int] = Field(None, alias="int")
    strength: Optional[int] = Field(None, alias="str")
    wis: Optional[int] = None


class AdditionalSpell(BaseModel):
    """A spell that can be cast in addition to the race."""

    name: Optional[str] = None
    level: Optional[int] = None
    innate: Optional[Dict[str, Any]] = None
    known: Optional[Dict[str, Any]] = None
    ability: Optional[Union[str, Dict[str, Any]]] = None


class Race(BaseContent):
    """A playable race."""

    ability: List[AbilityAdjustment] = Field(default_factory=list)
    creature_types: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None, alias="creatureTypes"
    )
    size: List[str] = Field(default_factory=list)
    speed: Union[int, Dict[str, Any]]
    entries: List[Any]
    additionalSpells: Optional[List[AdditionalSpell]] = Field(
        default=None, alias="additionalSpells"
    )
    darkvision: Optional[int] = None
    skill_proficiencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="skillProficiencies"
    )
    language_proficiencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="languageProficiencies"
    )
    weapon_proficiencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="weaponProficiencies"
    )
    armor_proficiencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="armorProficiencies"
    )
    tool_proficiencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="toolProficiencies"
    )
    saving_throw_proficiencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="savingThrowProficiencies"
    )
    condition_immunities: Optional[List[str]] = Field(
        default=None, alias="conditionImmunities"
    )
    resistances: Optional[List[str]] = None
    vulnerabilities: Optional[List[str]] = None
