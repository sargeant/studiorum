"""Creature spellcasting blocks as entries, for layouts and the Markdown renderer."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Raw = dict[str, Any]


def spellcasting_entries(block: Raw) -> Raw:
    """A spellcasting block as a named entry, its spell lists as lines of 5etools
    markup (``Renderer._renderSpellcasting_getEntries``)."""
    hidden = set(block.get("hidden") or [])
    shown = {k: v for k, v in block.items() if k not in hidden}
    lines = list(block.get("headerEntries", []))
    if shown.get("constant"):
        lines.append(f"Constant: {_spell_list(shown['constant'])}")
    if shown.get("will"):
        lines.append(f"At will: {_spell_list(shown['will'])}")
    for key, per in _PER_USE:
        lines += [
            f"{per(uses)}: {_spell_list(spells)}"
            for uses, spells in sorted(
                (shown.get(key) or {}).items(), key=_uses_order, reverse=True
            )
        ]
    if shown.get("ritual"):
        lines.append(f"Rituals: {_spell_list(shown['ritual'])}")
    for level, spells in sorted((shown.get("spells") or {}).items()):
        lines.append(
            f"{_slot_label(level, spells)}: {_spell_list(spells.get('spells', []))}"
        )
    lines += block.get("footerEntries", [])
    return {"name": block.get("name", "Spellcasting"), "entries": lines}


def _slot_label(level: str, spells: Raw) -> str:
    """A spell level's label: Cantrips, Level 3 (2 slots), or for slots of one
    level that cast lower spells, Levels 1-5 (2 level 5 slots)."""
    if level == "0":
        return "Cantrips"
    count, lower = spells.get("slots"), spells.get("lower")
    plural = "s" if count != 1 else ""
    if lower and str(lower) != level:
        slots = f" ({count} level {level} slot{plural})" if count else ""
        return f"Levels {lower}-{level}{slots}"
    return f"Level {level}" + (f" ({count} slot{plural})" if count else "")


def _per(unit: str, *, prefix: bool = True) -> Callable[[str], str]:
    """A use key such as "3" or "1e" ("each") as "3/day" or "1/day each"."""

    def label(uses: str) -> str:
        count = uses.rstrip("e")
        each = " each" if uses.endswith("e") else ""
        text = unit.format(n=count, s="" if count == "1" else "s")
        return f"{count if prefix else ''}{text}{each}"

    return label


# 5etools' spellcasting use keys in its order, each with its label
_PER_USE: tuple[tuple[str, Callable[[str], str]], ...] = (
    ("recharge", _per("Recharge {n}", prefix=False)),
    ("legendary", _per(" legendary action{s}")),
    ("charges", _per(" charge{s}")),
    ("rest", _per("/rest")),
    ("restLong", _per("/long rest")),
    ("daily", _per("/day")),
    ("weekly", _per("/week")),
    ("monthly", _per("/month")),
    ("yearly", _per("/year")),
)


def _uses_order(item: tuple[str, Any]) -> tuple[int, bool]:
    uses = item[0]
    return int(uses.rstrip("e") or 0), uses.endswith("e")


def _spell_list(spells: Any) -> str:
    """A spell list without its hidden spells; a spell may be {"entry", "hidden"}."""
    return ", ".join(
        str(s.get("entry", "")) if isinstance(s, dict) else str(s)
        for s in spells or []
        if not (isinstance(s, dict) and s.get("hidden"))
    )
