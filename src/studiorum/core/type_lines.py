"""The lines 5etools shows around an entity's entries, as 5etools entries.

A trap's subtitle and trigger, a feat's category and prerequisite, a deity's
pantheon: each type's ``getCompactRenderedString`` (``js/render.js``) builds
these from the entity's fields. The functions here return the same text as
entries, in the order 5etools shows it, with 2014 ("classic") wording, so the
entry renderer can set them without any LaTeX in Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .text.parser import (
    ABILITY_NAMES,
    TRAP_HAZARD_TYPES,
    TRAP_INITIATIVES,
    duration_entry,
    feat_category,
    tier_to_full_level,
)
from .text.prerequisites import prerequisite_entry
from .text.strings import join_conjunct, title_case

if TYPE_CHECKING:
    from pydantic import BaseModel

    from .loaders.omnidexer import Omnidexer

type Raw = dict[str, Any]

STYLE = "classic"

# Traps whose attributes come before their entries, as a hanging list
_CLASSIC_TRAPS = ("MECH", "MAG", "TRP", "HAUNT")


def raw(content: BaseModel) -> Raw:
    """The content as 5etools data."""
    return content.model_dump(by_alias=True, exclude_none=True)


def trap_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.traphazard`` and ``Renderer.trap``: subtitle, then parts and entries."""
    data = raw(content)
    entries = list(data.get("entries") or [])
    kind = data.get("trapHazType")
    if kind in _CLASSIC_TRAPS:
        items = _classic_trap_items(data)
        header = [{"type": "list", "style": "list-hang-notitle", "items": items}]
        body = (header if items else []) + entries
    else:
        body = entries + _trap_attributes(data)
    return [*_subtitle(data), *body]


def hazard_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    data = raw(content)
    return [*_subtitle(data), *(data.get("entries") or [])]


def _subtitle(data: Raw) -> list[str]:
    """``getSubtitle``: "Dangerous Simple Trap (1st–4th Level)"."""
    kind = data.get("trapHazType") or "HAZ"
    if kind == "GEN":
        return []
    name = TRAP_HAZARD_TYPES.get(kind, kind)
    ratings = [_rating(r, name) for r in data.get("rating") or []]
    text = join_conjunct([r for r in ratings if r], ", ", " or ") if ratings else name
    return [f"{{@i {text}}}"] if text else []


def _rating(rating: Raw, name: str) -> str:
    threat = " ".join(t for t in (title_case(rating.get("threat") or ""), name) if t)
    levels = _rating_levels(rating)
    return f"{threat} ({levels})" if levels else threat


def _rating_levels(rating: Raw) -> str:
    if rating.get("tier"):
        return tier_to_full_level(rating["tier"], style=STYLE)
    level = rating.get("level") or {}
    if level.get("min") is None or level.get("max") is None:
        return ""
    label = "level" if STYLE == "classic" else "Levels"
    upper = f"–{level['max']}" if level["min"] != level["max"] else ""
    return f"{label} {level['min']}{upper}"


def _classic_trap_items(data: Raw) -> list[Raw]:
    items: list[Raw] = []
    if data.get("trigger"):
        items.append({"type": "item", "name": "Trigger:", "entries": data["trigger"]})
    if data.get("duration"):
        duration = duration_entry(data["duration"], style=STYLE)
        items.append({"type": "item", "name": "Duration:", "entries": [duration]})
    bonus = data.get("hauntBonus")
    if bonus:
        items.append({"type": "item", "name": "Haunt Bonus:", "entry": bonus})
        if str(bonus).lstrip("+-").isdigit():
            detection = (
                "passive Wisdom ({@skill Perception}) score equals or exceeds "
                f"{10 + int(bonus)}"
            )
            items.append({"type": "item", "name": "Detection:", "entry": detection})
    return items


def _trap_attributes(data: Raw) -> list[Raw]:
    """Trigger and Effect (simple traps), Initiative and elements (complex ones)."""
    parts: list[tuple[str, Any]] = [
        ("Trigger", data.get("trigger")),
        ("Effect", data.get("effect")),
        ("Initiative", _initiative(data)),
        ("Active Elements", data.get("eActive")),
        ("Dynamic Elements", data.get("eDynamic")),
        ("Constant Elements", data.get("eConstant")),
        ("Countermeasures", data.get("countermeasures")),
    ]
    return [
        {"type": "entries", "name": name, "entries": entries}
        for name, entries in parts
        if entries
    ]


def _initiative(data: Raw) -> list[str] | None:
    initiative = data.get("initiative")
    if not initiative:
        return None
    note = f" ({data['initiativeNote']})" if data.get("initiativeNote") else ""
    return [f"The trap acts on {TRAP_INITIATIVES.get(initiative, initiative)}{note}."]


def feat_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.feat``: category and prerequisite, then entries with the increase."""
    data = raw(content)
    return [*_category_line(data), *_repeatable(data), *_full_entries(data)]


def _category_line(data: Raw) -> list[str]:
    """``getJoinedCategoryPrerequisites``: "General Feat (Prerequisite: ...)"."""
    category = feat_category(data["category"]) if data.get("category") else ""
    prerequisite = prerequisite_entry(data.get("prerequisite"), style=STYLE)
    if category and prerequisite:
        return [f"{{@i {category} ({prerequisite})}}"]
    text = category or prerequisite
    return [f"{{@i {text}}}"] if text else []


def _repeatable(data: Raw) -> list[str]:
    if data.get("repeatableHidden") or not data.get("repeatable"):
        return []
    return [f"{{@b Repeatable:}} {data.get('repeatableNote') or 'Yes'}"]


def _full_entries(data: Raw) -> list[Any]:
    """``Renderer.feat.initFullEntries``: the ability increase joins the entries."""
    entries = list(data.get("entries") or [])
    shown = [a for a in data.get("ability") or [] if not a.get("hidden")]
    if not shown:
        return entries
    lists = [e for e in entries if isinstance(e, dict) and e.get("type") == "list"]
    if lists:
        items = lists[0].setdefault("items", [])
        named = all(isinstance(i, dict) and i.get("type") == "item" for i in items)
        # 5etools puts each at the front in turn, so the last comes first
        for ability in shown:
            text = _increase_text(ability)
            item = (
                {"type": "item", "name": "Ability Score Increase.", "entry": text}
                if named
                else text
            )
            items.insert(0, item)
        return entries
    first = next(
        (
            i
            for i, e in enumerate(entries)
            if isinstance(e, dict) and e.get("type") == "entries"
        ),
        None,
    )
    texts = [_increase_text(a) for a in shown]
    if first is not None:
        increase = {
            "type": "entries",
            "name": "Ability Score Increase",
            "entries": texts,
        }
        return [*entries[:first], increase, *entries[first:]]
    return [*reversed(texts), *entries]


def _increase_text(ability: Raw) -> str:
    """``_mergeAbilityIncrease_getText``."""
    maximum = ability.get("max", 20)
    choose = ability.get("choose")
    if not choose:
        return " ".join(
            f"Increase your {ABILITY_NAMES[a]} score by {n}, to a maximum of {maximum}."
            for a, n in ability.items()
            if a != "max"
        )
    if weighted := choose.get("weighted"):
        weights = join_conjunct(
            [
                f"{'an' if i == 0 else 'another'} ability score to "
                f"{'increase' if w > 0 else 'decrease'} by {abs(w)}"
                for i, w in enumerate(weighted["weights"])
            ],
            ", ",
            " and ",
        )
        if len(weighted["from"]) == 6:
            return f"Choose {weights}."
        names = join_conjunct(
            [ABILITY_NAMES[a] for a in weighted["from"]], ", ", " and "
        )
        return f"Choose {weights} from among {names}."
    amount = choose.get("amount", 1)
    if len(choose["from"]) == 6:
        return choose.get("entry") or (
            f"Increase one ability score of your choice by {amount}, "
            f"to a maximum of {maximum}."
        )
    names = join_conjunct([ABILITY_NAMES[a] for a in choose["from"]], ", ", " or ")
    return f"Increase your {names} by {amount}, to a maximum of {maximum}."
