"""Encounter tools: XP budgets, rating a group of creatures, and creatures that fit."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from studiorum.core import encounter
from studiorum.core.encounter import Rules
from studiorum.core.models.content import ContentType
from studiorum.core.models.creatures import Creature
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.models import (
    CreatureSuggestions,
    EncounterBudget,
    EncounterRating,
    RatedCreature,
    SuggestedCreature,
)
from studiorum.mcp.tools.lookup import find_one
from studiorum.mcp.tools.search import (
    LatestOnly,
    Offset,
    reprint_uids,
    split_srd,
    type_name,
)
from studiorum.services import Services

PartyLevels = Annotated[
    list[Annotated[int, Field(ge=1, le=20)]],
    Field(min_length=1, max_length=12, description="Each character's level"),
]
RulesChoice = Annotated[
    Rules,
    Field(
        description="2024: low, moderate and high XP budgets. "
        "2014: easy to deadly thresholds, with a multiplier for group size."
    ),
]
Difficulty = Literal["low", "moderate", "high", "easy", "medium", "hard", "deadly"]
Environment = Literal[
    "arctic",
    "coastal",
    "desert",
    "forest",
    "grassland",
    "hill",
    "mountain",
    "swamp",
    "underdark",
    "underwater",
    "urban",
    "planar",
]


class CreatureCount(BaseModel):
    name: str
    source: str | None = Field(None, description="Source abbreviation; else the first")
    count: Annotated[int, Field(ge=1, le=50)] = 1


async def calculate_encounter_budget(
    party_levels: PartyLevels, rules: RulesChoice = "2024"
) -> EncounterBudget:
    """The XP for each encounter difficulty for a party, from the DMG tables."""
    return EncounterBudget(
        rules=rules,
        party_levels=party_levels,
        xp=encounter.budgets(party_levels, rules),
    )


async def rate_encounter(
    party_levels: PartyLevels,
    creatures: Annotated[list[CreatureCount], Field(min_length=1)],
    rules: RulesChoice = "2024",
    srd_only: SrdOnly = None,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> EncounterRating:
    """How hard a group of creatures is for a party: total and adjusted XP, and difficulty."""
    srd_only = default_srd if srd_only is None else srd_only
    rated: list[RatedCreature] = []
    problems: list[str] = []
    notes: list[str] = []
    for wanted in creatures:
        try:
            found = find_one(services, "creature", wanted.name, wanted.source, srd_only)
        except ToolError as e:
            problems.append(str(e))
            continue
        if not isinstance(found, Creature):
            problems.append(f"{found.name} is not a creature.")
            continue
        notes += [
            f"{found.name} ({found.source.abbreviation}) was reprinted as {uid}; "
            "pass its name and source to use that version."
            for uid in reprint_uids(found)
        ]
        rated.append(
            RatedCreature(
                name=found.name,
                source=found.source.abbreviation,
                srd=found.is_srd,
                cr=found.get_cr_text(),
                xp=encounter.creature_xp(found.cr),
                count=wanted.count,
            )
        )
    if problems:
        raise ToolError(" ".join(problems))
    total = sum((c.xp or 0) * c.count for c in rated)
    factor = encounter.multiplier(sum(c.count for c in rated), len(party_levels), rules)
    adjusted = int(total * factor)
    return EncounterRating(
        rules=rules,
        party_levels=party_levels,
        creatures=rated,
        total_xp=total,
        multiplier=factor,
        adjusted_xp=adjusted,
        difficulty=encounter.difficulty(adjusted, party_levels, rules),
        budgets=encounter.budgets(party_levels, rules),
        notes=notes,
    )


async def suggest_creatures(
    party_levels: PartyLevels,
    difficulty: Difficulty,
    count: Annotated[
        int, Field(ge=1, le=20, description="How many of the creature to fight")
    ] = 1,
    environment: Environment | None = None,
    creature_type: Annotated[
        str | None, Field(description="e.g. dragon, humanoid, undead")
    ] = None,
    rules: RulesChoice = "2024",
    include_minions: Annotated[
        bool,
        Field(
            description="Include creatures whose XP isn't their CR's, such as "
            "Flee Mortals minions and retainers"
        ),
    ] = False,
    srd_only: SrdOnly = None,
    latest_only: LatestOnly = True,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    offset: Offset = 0,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> CreatureSuggestions:
    """Creatures that, `count` at a time, make an encounter of this difficulty, strongest first.

    Environments are the ones 5etools tags creatures with. Check a mixed group
    with rate_encounter.
    """
    srd_only = default_srd if srd_only is None else srd_only
    try:
        low, high = encounter.xp_range(difficulty, party_levels, rules)
    except ValueError as e:
        raise ToolError(str(e)) from e
    per = count * encounter.multiplier(count, len(party_levels), rules)
    each = (math.ceil(low / per), math.floor(high / per))
    fits: list[tuple[int, Creature]] = []
    for c in services.omnidexer.get_all_by_type(ContentType.CREATURE):
        if not isinstance(c, Creature):
            continue
        xp = encounter.creature_xp(c.cr)
        if xp is None or not each[0] <= xp <= each[1]:
            continue
        if not include_minions and xp != encounter.table_xp(c.cr):
            continue
        if creature_type and type_name(c).lower() != creature_type.lower():
            continue
        if environment and not any(
            e == environment or e.startswith(f"{environment},")
            for e in _environments(c)
        ):
            continue
        fits.append((xp, c))
    kept, hidden = split_srd([c for _, c in fits], srd_only, latest_only)
    fits = [f for f in fits if id(f[1]) in set(map(id, kept))]
    fits.sort(key=lambda f: (-f[0], f[1].name.lower(), f[1].source.abbreviation))
    return CreatureSuggestions(
        srd_only=srd_only,
        hidden_by_srd=hidden,
        rules=rules,
        difficulty=difficulty,
        count=count,
        xp_each=each,
        total=len(fits),
        results=[
            SuggestedCreature(
                name=c.name,
                source=c.source.abbreviation,
                srd=c.is_srd,
                cr=c.get_cr_text(),
                xp=xp,
                type=type_name(c),
                environment=_environments(c),
            )
            for xp, c in fits[offset : offset + limit]
        ],
    )


def _environments(creature: Creature) -> list[str]:
    found = getattr(creature, "environment", None)
    return [str(e) for e in found] if isinstance(found, list) else []
