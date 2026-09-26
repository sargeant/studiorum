"""What 5etools shows for a vehicle, as 5etools markup and entries.

A port of ``Renderer.vehicle`` (``js/render.js``): one layout per
``vehicleType`` (ship, Spelljammer ship, elemental airship, infernal war
machine, and object as ``Renderer.object``), in 2014 ("classic") wording. The lines and summary are the markup
5etools builds in its ``get*RenderableEntriesMeta`` functions; the section
titles are the text of its HTML headers. The vehicle template sets them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cmp_to_key
from typing import TYPE_CHECKING, Any

from .text.parser import SIZES
from .text.stats import SPEED_MODES, condition_text, damage_text, size_text, speed_text
from .text.strings import join_conjunct
from .text.tags import plain_text
from .type_lines import cargo_capacity, creature_capacity, object_lines, raw

if TYPE_CHECKING:
    from pydantic import BaseModel

type Raw = dict[str, Any]

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
# Parser.DEFAULT_CURRENCY_CONVERSION_TABLE, gold as the fallback
_COINS = (("cp", 1.0), ("sp", 0.1), ("gp", 0.01))
_VULGAR = {
    "⅛": 1 / 8,
    "¼": 1 / 4,
    "⅜": 3 / 8,
    "½": 1 / 2,
    "⅝": 5 / 8,
    "¾": 3 / 4,
    "⅞": 7 / 8,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "⅙": 1 / 6,
    "⅚": 5 / 6,
}
# SortUtil._MON_TRAIT_ORDER
_TRAIT_ORDER = ("temporary statblock", "special equipment", "shapechanger")
_DETAILS = (
    ("vulnerable", "Damage Vulnerabilities", damage_text),
    ("resist", "Damage Resistances", damage_text),
    ("immune", "Damage Immunities", damage_text),
    ("conditionImmune", "Condition Immunities", condition_text),
)


@dataclass(frozen=True)
class VehicleSection:
    """A titled part of the statblock: its labelled lines, then its entries."""

    title: str
    lines: list[str] = field(default_factory=list)
    entries: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class VehicleBlock:
    """A vehicle's statblock, top to bottom, as 5etools markup and entries.

    ``summary`` is a table entry (Spelljammer ships and elemental airships);
    ``note`` is the small bracketed line under the attributes; ``details``
    pairs each immunity label with its text; ``entries`` (an object's) come
    before the sections.
    """

    type_line: str | None = None
    attributes: list[str] = field(default_factory=list)
    note: str | None = None
    summary: Raw | None = None
    abilities: dict[str, int] | None = None
    details: list[tuple[str, str]] = field(default_factory=list)
    entries: list[Any] = field(default_factory=list)
    sections: list[VehicleSection] = field(default_factory=list)


def vehicle_block(content: BaseModel | Raw) -> VehicleBlock:
    """The statblock for a vehicle, by its ``vehicleType`` (ships by default)."""
    # The model gives absent lists (ac, size, entries) as empty ones
    data = {k: v for k, v in raw(content).items() if v != []}
    match data.get("vehicleType") or "SHIP":
        case "SPELLJAMMER":
            return _spelljammer(data)
        case "ELEMENTAL_AIRSHIP":
            return _elemental_airship(data)
        case "INFWAR":
            return _infwar(data)
        case "SHIP":
            return _ship(data)
        case "OBJECT":
            return _object(data)
        case other:
            raise ValueError(f"No vehicle layout for {other!r}")


def _ship(data: Raw) -> VehicleBlock:
    """``_getRenderedString_ship``."""
    others = data.get("other") or []
    place = "; ".join(
        p
        for p in (
            join_conjunct(data["terrain"], ", ", " and ")
            if data.get("terrain")
            else "",
            " by ".join(data["dimensions"]) if data.get("dimensions") else "",
        )
        if p
    )
    size = SIZES.get(str(data.get("size")), str(data.get("size")))
    attributes = []
    if data.get("capCrew") is not None or data.get("capPassenger") is not None:
        attributes.append(f"{{@b Creature Capacity}} {creature_capacity(data)}")
    if data.get("capCargo") is not None:
        attributes.append(f"{{@b Cargo Capacity}} {cargo_capacity(data['capCargo'])}")
    if data.get("initiative"):
        attributes.append(
            f"{{@b Initiative}} {{@initiative {_js(data['initiative'])}}}"
        )
    pace = data.get("pace")
    if pace is not None:
        attributes.append(
            f"{{@b Travel Pace}} {_js(pace)} miles per hour "
            f"({_js(pace * 24)} miles per day)"
        )
    sections = []
    if data.get("action"):
        sections.append(VehicleSection("Actions", entries=data["action"]))
    sections += [_other(o) for o in others if o.get("name") == "Actions"]
    if hull := data.get("hull"):
        sections.append(VehicleSection("Hull", _hp_lines(hull)))
    if traits := _ordered_traits(data):
        sections.append(VehicleSection("Traits", entries=traits))
    sections += [
        VehicleSection(f"Control: {c['name']}", _hp_lines(c), c.get("entries") or [])
        for c in data.get("control") or []
    ]
    sections += [_movement(m) for m in data.get("movement") or []]
    sections += [
        VehicleSection(
            f"Weapons: {w['name']}" + (f" ({w['count']})" if w.get("count") else ""),
            _hp_lines(w, each=bool(w.get("count"))),
            w.get("entries") or [],
        )
        for w in data.get("weapon") or []
    ]
    sections += [_other(o) for o in others if o.get("name") != "Actions"]
    return VehicleBlock(
        type_line=f"{{@i {size} vehicle{f' ({place})' if place else ''}}}",
        attributes=attributes,
        note=f"[{{@b Speed}} {_js(pace * 10)} ft.]" if pace is not None else None,
        abilities=_abilities(data),
        details=_details(data),
        sections=sections,
    )


def _object(data: Raw) -> VehicleBlock:
    """``Renderer.object``: size, attributes, entries, then actions."""
    size, *attributes = object_lines(data)
    return VehicleBlock(
        type_line=size,
        attributes=attributes,
        entries=[*(data.get("entries") or []), *(data.get("actionEntries") or [])],
    )


def _hp_lines(part: Raw, *, each: bool = False) -> list[str]:
    """``getSectionHpEntriesMeta_``: a part's armour class and hit points."""
    lines = []
    if part.get("ac"):
        lines.append(f"{{@b Armor Class}} {_js(part['ac'])}")
    if part.get("hp"):
        threshold = f" (damage threshold {_js(part['dt'])})" if part.get("dt") else ""
        note = f"; {part['hpNote']}" if part.get("hpNote") else ""
        lines.append(
            f"{{@b Hit Points}} {_js(part['hp'])}{' each' if each else ''}"
            f"{threshold}{note}"
        )
    return lines


def _movement(move: Raw) -> VehicleSection:
    """``getMovementSection_``: locomotion and speeds as hanging lists."""
    control = "Control and " if move.get("isControl") else ""
    entries = [
        _hanging(f"{label} ({mode['mode']})", mode.get("entries"))
        for label, prop in (("Locomotion", "locomotion"), ("Speed", "speed"))
        for mode in move.get(prop) or []
    ]
    return VehicleSection(
        f"{control}Movement: {move['name']}", _hp_lines(move), entries
    )


def _hanging(name: str, entries: Any) -> Raw:
    item: Raw = {"type": "item", "name": name}
    if entries is not None:
        item["entries"] = entries
    return {"type": "list", "style": "list-hang-notitle", "items": [item]}


def _other(other: Raw) -> VehicleSection:
    return VehicleSection(other["name"], _hp_lines(other), other.get("entries") or [])


def _spelljammer(data: Raw) -> VehicleBlock:
    """``_getRenderedString_spelljammer``: summary, then weapon stations."""
    lines = _summary_lines(data)
    speed = (
        speed_text(data, skip_zero_walk=True) if data.get("speed") is not None else ""
    )
    pace = _pace(data)
    speed_pace = " ".join(p for p in (speed, f"({pace})" if speed else pace) if p)
    dimensions = "/".join(data.get("dimensions") or ["—"])
    rows = [
        [lines["ac"], lines["cargo"]],
        [lines["hp"], lines["crew"]],
        [lines["dt"], f"{{@b Keel/Beam:}} {dimensions}"],
        [f"{{@b Speed:}} {speed_pace}", lines["cost"]],
    ]
    sections = []
    for weapon in data.get("weapon") or []:
        count = weapon.get("count")
        many = count is not None and count > 1
        crew = (
            f" (Crew: {_js(weapon['crew'])}{' each' if many else ''})"
            if weapon.get("crew")
            else ""
        )
        title = f"{f'{_js(count)} ' if many else ''}{weapon['name']}{crew}"
        sections.append(_station(title, weapon, empty_cost=True))
    return VehicleBlock(summary=_summary(rows), sections=sections)


def _elemental_airship(data: Raw) -> VehicleBlock:
    """``_getRenderedString_elementalAirship``: summary, weapons, then stations."""
    lines = _summary_lines(data)
    speed = (
        speed_text(data, skip_zero_walk=True) if data.get("speed") is not None else ""
    )
    pace_speed = " ".join(p for p in (_pace(data), f"({speed})" if speed else "") if p)
    passengers = data.get("capPassenger")
    rows = [
        [lines["ac"], lines["crew"]],
        [lines["hp"], f"{{@b Passengers:}} {_js(passengers) if passengers else '—'}"],
        [lines["dt"], lines["cargo"]],
        [f"{{@b Speed:}} {pace_speed}", lines["cost"]],
    ]
    sections = []
    for station in [*(data.get("weapon") or []), *(data.get("station") or [])]:
        count = station.get("count")
        many = count is not None and count > 1
        title = f"{station['name']}{f' ({_js(count)})' if many else ''}"
        sections.append(_station(title, station, empty_cost=False))
    return VehicleBlock(summary=_summary(rows), sections=sections)


def _summary_lines(data: Raw) -> dict[str, str]:
    """``spelljammerElementalAirship.getRenderableEntriesMeta``."""
    hull = data.get("hull") or {}
    ac = "—"
    if hull.get("ac"):
        ac_from = f" ({', '.join(hull['acFrom'])})" if hull.get("acFrom") else ""
        ac = f"{_js(hull['ac'])}{ac_from}"
    cargo = data.get("capCargo")
    crew = data.get("capCrew")
    crew_note = f" {data['capCrewNote']}" if data.get("capCrewNote") else ""
    return {
        "ac": f"{{@b Armor Class:}} {ac}",
        "cargo": "{@b Cargo:} "
        + (f"{_js(cargo)} ton{'' if cargo == 1 else 's'}" if cargo else "—"),
        "hp": f"{{@b Hit Points:}} {_js(hull['hp']) if hull.get('hp') is not None else '—'}",
        "crew": f"{{@b Crew:}} {_js(crew) if crew is not None else '—'}{crew_note}",
        "dt": f"{{@b Damage Threshold:}} {_js(hull['dt']) if hull.get('dt') is not None else '—'}",
        "cost": f"{{@b Cost:}} {cost_text(data) if data.get('cost') is not None else '—'}",
    }


def _pace(data: Raw) -> str:
    """Each pace in miles per hour, with miles per day as its tooltip."""
    pace = data.get("pace")
    if not pace:
        return ""
    many = len(pace) > 1
    return ", ".join(
        f"{{@tip {mode + ' ' if many and mode != 'walk' else ''}{_js(pace[mode])} mph"
        f"|{_js(_vulgar_to_number(pace[mode]) * 24)} miles per day}}"
        for mode in SPEED_MODES
        if pace.get(mode)
    )


def _summary(rows: list[list[str]]) -> Raw:
    return {
        "type": "table",
        "style": "summary",
        "colStyles": ["col-6", "col-6"],
        "rows": rows,
    }


def _station(title: str, station: Raw, *, empty_cost: bool) -> VehicleSection:
    """``spelljammerElementalAirship.getStationSection_``."""
    lines = []
    if station.get("size"):
        lines.append(f"{{@i {size_text(station['size'])} Object}}")
    lines.append(f"{{@b Armor Class:}} {_js(station.get('ac', '—'))}")
    lines.append(f"{{@b Hit Points:}} {_js(station.get('hp', '—'))}")
    costs = station.get("costs") or []
    if empty_cost or costs:
        text = (
            ", ".join(
                (cost_text(c) or "—") + (f" ({c['note']})" if c.get("note") else "")
                for c in costs
            )
            or "—"
        )
        lines.append(f"{{@b Cost:}} {text}")
    return VehicleSection(
        title, lines, [*(station.get("entries") or []), *(station.get("action") or [])]
    )


def _infwar(data: Raw) -> VehicleBlock:
    """``_getRenderedString_infwar``."""
    hp = data.get("hp") or {}
    dex_mod = math.floor((data.get("dex", 10) - 10) / 2)
    # 5etools reads `ac ?? dexMod === 0 ? ...`, so any set AC prints 19
    ac = (
        "19"
        if (bool(data["ac"]) if data.get("ac") is not None else dex_mod == 0)
        else f"{19 + dex_mod} (19 while motionless)"
    )
    thresholds = ", ".join(
        f"{label} {_js(hp[key])}"
        for key, label in (("dt", "damage threshold"), ("mt", "mishap threshold"))
        if hp.get(key) is not None
    )
    speed = data.get("speed", 0)
    sections = []
    if traits := _ordered_traits(data):
        sections.append(VehicleSection("Traits", entries=traits))
    for prop, title in (
        ("actionStation", "Action Stations"),
        ("reaction", "Reactions"),
    ):
        if data.get(prop):
            note = f" ({data[prop + 'Note']})" if data.get(prop + "Note") else ""
            sections.append(VehicleSection(title + note, entries=data[prop]))
    return VehicleBlock(
        type_line=(
            f"{{@i {SIZES.get(str(data.get('size')), '')} vehicle "
            f"({_locale(data.get('weight', 0))} lb.)}}"
        ),
        attributes=[
            f"{{@b Creature Capacity}} {_js(data.get('capCreature'))} Medium creatures",
            f"{{@b Cargo Capacity}} {weight_text(data.get('capCargo', 0))}",
            f"{{@b Armor Class}} {ac}",
            f"{{@b Hit Points}} {_js(hp.get('hp'))}"
            + (f" ({thresholds})" if thresholds else ""),
            f"{{@b Speed}} {_js(speed)} ft.",
        ],
        note=(
            f"[{{@b Travel Pace}} {math.floor(speed / 10)} miles per hour "
            f"({math.floor(speed * 24 / 10)} miles per day)]"
        ),
        abilities=_abilities(data),
        details=_details(data),
        sections=sections,
    )


def _abilities(data: Raw) -> dict[str, int] | None:
    if not any(data.get(a) is not None for a in ABILITIES):
        return None
    return {a: data[a] for a in ABILITIES if data.get(a) is not None}


def _details(data: Raw) -> list[tuple[str, str]]:
    """``getVehicleRenderableEntriesMeta``: immunities, resistances and the like."""
    return [
        (label, text(data[prop])) for prop, label, text in _DETAILS if data.get(prop)
    ]


def _ordered_traits(data: Raw) -> list[Any]:
    """``Renderer.monster.getOrderedTraits``: sorted by ``SortUtil.monTraitSort``."""
    traits = data.get("trait") or []
    return sorted(traits, key=cmp_to_key(_trait_cmp))


def _trait_cmp(a: Raw, b: Raw) -> int:
    if a.get("sort") is not None and b.get("sort") is not None:
        return int(a["sort"] - b["sort"])
    if a.get("sort") is not None or b.get("sort") is not None:
        return -1 if a.get("sort") is not None else 1
    if not a.get("name") and not b.get("name"):
        return 0
    name_a, name_b = a.get("name", ""), b.get("name", "")
    clean_a, clean_b = (plain_text(n).lower().strip() for n in (name_a, name_b))
    only_a, only_b = name_a.endswith(" Only)"), name_b.endswith(" Only)")
    if only_a != only_b:
        return 1 if only_a else -1
    in_a, in_b = clean_a in _TRAIT_ORDER, clean_b in _TRAIT_ORDER
    if in_a and in_b:
        return _TRAIT_ORDER.index(clean_a) - _TRAIT_ORDER.index(clean_b)
    if in_a or in_b:
        return -1 if in_a else 1
    return (clean_a > clean_b) - (clean_a < clean_b)


def cost_text(data: Raw) -> str:
    """``Parser.vehicleCostToFull``: a cost in copper as "20,000 gp"."""
    value = data.get("cost")
    if value is None:
        return ""
    coin, mult = _coin(value)
    return f"{_locale(value * mult)} {coin}"


def _coin(value: float) -> tuple[str, float]:
    """``Parser.getCurrencyAndMultiplier`` over the default coins."""
    if not value:
        return _COINS[-1]
    if not float(value).is_integer() and value < _COINS[0][1]:
        return _COINS[0]
    for coin, mult in reversed(_COINS):
        if float(value * mult).is_integer():
            return coin, mult
    return _COINS[-1]


def weight_text(pounds: int) -> str:
    """``Parser.weightToFull``: "1 ton, 500 lb."."""
    tons, pounds = divmod(pounds, 2000)
    return ", ".join(
        p
        for p in (
            f"{tons} ton{'' if tons == 1 else 's'}" if tons else "",
            f"{pounds} lb." if pounds else "",
        )
        if p
    )


def _vulgar_to_number(value: Any) -> float:
    """``Parser.vulgarToNumber``: "5½" as 5.5."""
    text = str(value)
    vulgar = text[-1] if text and text[-1] in _VULGAR else ""
    leading = text[: -1 if vulgar else None]
    return (float(leading) if leading else 0.0) + _VULGAR.get(vulgar, 0.0)


def _locale(number: float) -> str:
    """``toLocaleStringVe`` in English: thousands separated, at most five decimals."""
    text = f"{round(number, 5):,}"
    return text.removesuffix(".0")


def _js(value: Any) -> str:
    """A value as JavaScript prints it in a template string: 8.0 as "8"."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
