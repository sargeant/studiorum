"""Statblock attributes as 5etools writes them: size, speed, immunities, senses.

Ports of ``Parser.getSpeedString``, ``Parser.getFullImmRes`` and
``Parser.getFullCondImm``, and ``Renderer.utils.getRenderedSize`` and
``getSensesEntry``, returning 5etools markup.
"""

from __future__ import annotations

import re
from typing import Any

from .parser import SIZES
from .strings import join_conjunct, title_case
from .tags import split_by_tags

type Raw = dict[str, Any]

SIZE_ORDER = ("T", "S", "M", "L", "H", "G", "V")
SPEED_MODES = ("walk", "burrow", "climb", "fly", "swim")
DAMAGE_TYPES = [
    *("acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic"),
    *("piercing", "poison", "psychic", "radiant", "slashing", "thunder"),
]
_SENSES = {
    "classic": (
        ("blindsight", "PHB"),
        ("darkvision", "PHB"),
        ("tremorsense", "MM"),
        ("truesight", "PHB"),
    ),
    "one": tuple(
        (s, "XPHB") for s in ("blindsight", "darkvision", "tremorsense", "truesight")
    ),
}
_BLIND = re.compile(r"(^| |\()(blind|blinded)(\)| |$)", re.IGNORECASE)
_IMM_RES_PROPS = ("immune", "resist", "vulnerable", "conditionImmune")


def size_text(size: Any) -> str:
    """``getRenderedSize``: sizes smallest first, "Tiny or Small"."""
    sizes = size if isinstance(size, list) else [size] if size else []
    ordered = sorted(
        sizes, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else -1
    )
    return join_conjunct([SIZES.get(s, str(s)) for s in ordered], ", ", " or ")


def speed_text(
    data: Raw,
    *,
    style: str = "classic",
    skip_zero_walk: bool = False,
    long_form: bool = False,
) -> str:
    """``getSpeedString``: "30 ft., fly 60 ft."."""
    speed = data.get("speed")
    if speed is None:
        return "—"
    unit = "feet" if long_form else "ft."
    if not isinstance(speed, dict):
        return f"{speed}" + ("" if speed == "Varies" else f" {unit} ")
    hidden = speed.get("hidden") or []
    parts: list[str] = []
    joiner = ", "
    for mode in SPEED_MODES:
        if mode in hidden:
            continue
        if speed.get(mode) or (not skip_zero_walk and mode == "walk"):
            parts.append(_speed(mode, speed.get(mode) or 0, unit, style))
        alternates = (speed.get("alternate") or {}).get(mode) or []
        parts.extend(_speed(mode, a, unit, style) for a in alternates)
    choose = speed.get("choose")
    if choose and "choose" not in hidden:
        joiner = "; "
        names = join_conjunct(
            [_speed_name(m, style).strip() for m in sorted(choose["from"])],
            ", ",
            " or ",
        )
        note = f" {choose['note']}" if choose.get("note") else ""
        parts.append(f"{names} {choose['amount']} {unit}{note}")
    note = f" {speed['note']}" if speed.get("note") else ""
    return joiner.join(parts) + note


def _speed(mode: str, speed: Any, unit: str, style: str) -> str:
    if speed is True and mode != "walk":
        value: Any = "equal to your walking speed"
    elif speed is True:
        value = 0
    else:
        value = speed["number"] if isinstance(speed, dict) else speed
    condition = (
        f" {speed['condition']}"
        if isinstance(speed, dict) and speed.get("condition")
        else ""
    )
    return f"{_speed_name(mode, style)}{value}{'' if speed is True else f' {unit}'}{condition}"


def _speed_name(mode: str, style: str) -> str:
    if mode == "walk":
        return ""
    return f"{mode if style == 'classic' else title_case(mode)} "


def damage_text(values: list[Any] | None) -> str:
    """``getFullImmRes``: "poison, psychic; bludgeoning from nonmagical attacks"."""
    if not values:
        return ""
    return _imm_res(values, conditions=False, group=False)


def condition_text(values: list[Any] | None) -> str:
    """``getFullCondImm`` as an entry, each condition tagged."""
    if not values:
        return ""
    return _imm_res(values, conditions=True, group=False)


def _simple(value: Any) -> bool:
    return (
        isinstance(value, str)
        or bool(value.get("special"))
        or not any(p in value for p in _IMM_RES_PROPS)
    )


def _imm_res(values: list[Any], *, conditions: bool, group: bool) -> str:
    if not conditions and values == DAMAGE_TYPES:
        return "all damage"
    out = []
    for i, value in enumerate(values):
        simple = _simple(value)
        if simple and isinstance(value, dict):
            text = str(value.get("special", ""))
        elif simple:
            text = f"{{@condition {value}}}" if conditions else str(value)
        else:
            text = " ".join(
                t
                for t in (
                    value.get("preNote"),
                    _imm_res(
                        value[next(p for p in _IMM_RES_PROPS if p in value)],
                        conditions=conditions,
                        group=True,
                    ),
                    value.get("note"),
                )
                if t
            )
        if i == len(values) - 1:
            out.append(text)
        elif not simple or not _simple(values[i + 1]):
            out.append(f"{text}; ")
        elif not group or i != len(values) - 2:
            out.append(f"{text}, ")
        elif len(values) == 2:
            out.append(f"{text} and ")
        else:
            out.append(f"{text}, and ")
    return "".join(out)


def senses_entry(senses: Any, *, style: str = "classic") -> str:
    """``getSensesEntry``: each sense tagged, and "blind" as the condition."""
    if isinstance(senses, str):
        senses = [senses]
    out = []
    for sense in senses:
        text = ""
        for part in split_by_tags(sense):
            if part.startswith("{@"):
                text += part
                continue
            for name, source in _SENSES[style]:
                part = _sense_pattern(name).sub(f"{{@sense \\g<sense>|{source}}}", part)
            text += part
        out.append(text)
    return _BLIND.sub(
        lambda m: f"{m[1]}{{@condition blinded||{m[2]}}}{m[3]}", ", ".join(out)
    )


def _sense_pattern(name: str) -> re.Pattern[str]:
    return re.compile(rf"\b(?P<sense>{re.escape(name)})\b", re.IGNORECASE)


def ability_entry(data: Raw, ability: str) -> str:
    """``getAbilityRollerEntry``: the score as an ability tag."""
    if data.get(ability) is None:
        return "—"
    return f"{{@ability {ability} {data[ability]}}}"
