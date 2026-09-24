"""The spells a subclass, feature or race grants (5etools ``additionalSpells``).

Each grant maps a level to the spells gained there. The level key is a
character level ("3"), a spell slot level ("s1") or "_" for any level. The
spells are a list, or grouped by how often they can be cast.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpellList(BaseModel):
    """Named spells to choose from."""

    model_config = ConfigDict(extra="forbid")

    from_: list[str] = Field(..., alias="from", description="Spells to choose from")
    count: int | None = Field(None, description="How many to choose")


class SpellChoice(BaseModel):
    """A spell picked from a filter, e.g. {"choose": "level=0|class=Wizard"}."""

    model_config = ConfigDict(extra="forbid")

    choose: str | SpellList | None = Field(
        None, description="Filter or list to choose from"
    )
    all: str | None = Field(None, description="Filter whose every spell is granted")
    count: int | None = Field(None, description="How many to choose")


SpellRef = str | SpellChoice
UsesBySlot = dict[str, list[SpellRef]]


class SpellUses(BaseModel):
    """Spells grouped by how often they can be cast."""

    model_config = ConfigDict(extra="forbid")

    will: list[SpellRef] | None = Field(None, description="At will")
    ritual: list[SpellRef] | None = Field(None, description="As rituals")
    daily: UsesBySlot | None = Field(None, description="Per day, keyed '1' or '1e'")
    rest: UsesBySlot | None = Field(None, description="Per short or long rest")
    limited: UsesBySlot | None = Field(None, description="A limited number of times")
    resource: UsesBySlot | None = Field(None, description="By spending a resource")
    any_use: list[SpellRef] | None = Field(
        None, alias="_", description="With no limit given"
    )


SpellsAtLevel = list[SpellRef] | SpellUses


class AdditionalSpells(BaseModel):
    """One set of granted spells; a subclass or feature can offer several."""

    model_config = ConfigDict(extra="allow")  # Allow other spell granting mechanisms

    name: str | None = Field(None, description="Name of this option")
    ability: str | dict[str, Any] | None = Field(
        None, description="Spellcasting ability, or {'choose': [...]}"
    )
    resource_name: str | None = Field(
        None, alias="resourceName", description="Resource the spells cost"
    )
    prepared: dict[str, SpellsAtLevel] | None = Field(
        None, description="Always-prepared spells by level"
    )
    expanded: dict[str, SpellsAtLevel] | None = Field(
        None, description="Expanded spell list by level"
    )
    known: dict[str, SpellsAtLevel] | None = Field(
        None, description="Known spells by level"
    )
    innate: dict[str, SpellsAtLevel] | None = Field(
        None, description="Innate spellcasting by level"
    )
