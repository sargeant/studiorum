"""Search tools: spells, creatures and items, filtered as the CLI's collectors filter."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, Literal

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.core.loaders import item_types
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.models.creature_filters import CreatureFilterCriteria
from studiorum.core.models.creatures import Creature
from studiorum.core.models.item_filters import ItemFilterCriteria
from studiorum.core.models.items import Item
from studiorum.core.models.spell_filters import SpellFilterCriteria
from studiorum.core.models.spells import Spell
from studiorum.core.services.creature_collector import CreatureCollector
from studiorum.core.services.item_collector import ItemCollector
from studiorum.core.services.spell_collector import SpellCollector
from studiorum.mcp.deps import SrdOnly, get_services, srd_default
from studiorum.mcp.models import (
    CreatureResults,
    CreatureSummary,
    ItemResults,
    ItemSummary,
    SpellResults,
    SpellSummary,
)
from studiorum.services import Services

School = Literal[
    "abjuration",
    "conjuration",
    "divination",
    "enchantment",
    "evocation",
    "illusion",
    "necromancy",
    "transmutation",
]
Rarity = Literal[
    "none",
    "common",
    "uncommon",
    "rare",
    "very rare",
    "legendary",
    "artifact",
    "varies",
    "unknown",
    "unknown (magic)",
]
Query = Annotated[str | None, Field(description="Text the name must contain")]
Sources = Annotated[
    list[str] | None, Field(description="Source abbreviations, e.g. ['XPHB']")
]
Limit = Annotated[int, Field(ge=1, le=100)]


def _given(**filters: Any) -> dict[str, Any]:
    """The filters a caller set; the collectors reject criteria with none."""
    return {k: v for k, v in filters.items() if v is not None}


def _all[T: BaseContent](
    services: Services, ctype: ContentType, model: type[T]
) -> list[T]:
    return [
        c for c in services.omnidexer.get_all_by_type(ctype) if isinstance(c, model)
    ]


def _narrow[T: BaseContent](
    found: Sequence[T], query: str | None, srd_only: bool
) -> list[T]:
    needle = (query or "").lower()
    return sorted(
        (c for c in found if needle in c.name.lower() and (c.is_srd or not srd_only)),
        key=lambda c: (c.name.lower(), c.source.abbreviation),
    )


async def search_spells(
    query: Query = None,
    level: Annotated[int | None, Field(ge=0, le=9)] = None,
    school: School | None = None,
    spell_class: Annotated[
        str | None, Field(description="A class whose list has the spell, e.g. wizard")
    ] = None,
    ritual: bool | None = None,
    concentration: bool | None = None,
    sources: Sources = None,
    srd_only: SrdOnly = None,
    limit: Limit = 20,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> SpellResults:
    """Find spells by name, level, school, class list, ritual or concentration."""
    srd_only = default_srd if srd_only is None else srd_only
    filters = _given(
        levels=[level] if level is not None else None,
        schools=[school] if school else None,
        classes=[spell_class] if spell_class else None,
        ritual=ritual,
        concentration=concentration,
        sources=sources,
    )
    found: list[Spell] = (
        SpellCollector(services.omnidexer)
        .collect_spells(SpellFilterCriteria(**filters))
        .spells
        if filters
        else _all(services, ContentType.SPELL, Spell)
    )
    spells = _narrow(found, query, srd_only)
    return SpellResults(
        total=len(spells),
        results=[
            SpellSummary(
                name=s.name,
                source=s.source.abbreviation,
                srd=s.is_srd,
                level=s.level,
                school=s.school,
            )
            for s in spells[:limit]
        ],
    )


async def search_creatures(
    query: Query = None,
    cr_min: Annotated[float | None, Field(ge=0, le=30)] = None,
    cr_max: Annotated[float | None, Field(ge=0, le=30)] = None,
    creature_type: Annotated[
        str | None, Field(description="e.g. dragon, humanoid, undead")
    ] = None,
    sources: Sources = None,
    srd_only: SrdOnly = None,
    limit: Limit = 20,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> CreatureResults:
    """Find creatures by name, challenge rating range and creature type."""
    srd_only = default_srd if srd_only is None else srd_only
    filters = _given(
        min_cr=cr_min,
        max_cr=cr_max,
        creature_types=[creature_type] if creature_type else None,
        sources=sources,
    )
    found: list[Creature] = (
        CreatureCollector(services.omnidexer)
        .collect_creatures(CreatureFilterCriteria(**filters))
        .creatures
        if filters
        else _all(services, ContentType.CREATURE, Creature)
    )
    creatures = _narrow(found, query, srd_only)
    return CreatureResults(
        total=len(creatures),
        results=[
            CreatureSummary(
                name=c.name,
                source=c.source.abbreviation,
                srd=c.is_srd,
                cr=c.get_cr_text(),
                type=type_name(c),
            )
            for c in creatures[:limit]
        ],
    )


async def search_items(
    query: Query = None,
    rarity: Rarity | None = None,
    magic_only: bool = False,
    requires_attunement: bool | None = None,
    sources: Sources = None,
    srd_only: SrdOnly = None,
    limit: Limit = 20,
    default_srd: bool = Depends(srd_default),
    services: Services = Depends(get_services),
) -> ItemResults:
    """Find items by name, rarity, attunement, or magic items only."""
    srd_only = default_srd if srd_only is None else srd_only
    filters = _given(
        rarities=[rarity] if rarity else None,
        magic_only=magic_only or None,
        requires_attunement=requires_attunement,
        sources=sources,
    )
    found: list[Item] = (
        ItemCollector(services.omnidexer)
        .collect_items(ItemFilterCriteria(**filters))
        .items
        if filters
        else _all(services, ContentType.ITEM, Item)
    )
    items = _narrow(found, query, srd_only)
    return ItemResults(
        total=len(items),
        results=[
            ItemSummary(
                name=i.name,
                source=i.source.abbreviation,
                srd=i.is_srd,
                type=item_types.name(str(i.type)) if i.type is not None else None,
                rarity=str(i.rarity) if i.rarity is not None else None,
            )
            for i in items[:limit]
        ],
    )


def type_name(creature: Creature) -> str:
    """The creature's type name, e.g. humanoid."""
    kind = creature.type
    if isinstance(kind, str):
        return kind
    if isinstance(kind, dict):
        return str(kind.get("type", ""))
    return str(getattr(kind, "type", kind))
