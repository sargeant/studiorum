"""The lines 5etools shows around an entity's entries, as 5etools entries.

A trap's subtitle and trigger, a feat's category and prerequisite, a deity's
pantheon: each type's ``getCompactRenderedString`` (``js/render.js``) builds
these from the entity's fields. The functions here return the same text as
entries, in the order 5etools shows it, with 2014 ("classic") wording, so the
entry renderer can set them without any LaTeX in Python.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .text.parser import (
    ABILITIES,
    ABILITY_NAMES,
    OPT_FEATURE_TYPES,
    TRAP_HAZARD_TYPES,
    TRAP_INITIATIVES,
    VEHICLE_UPGRADE_TYPES,
    alignment_abv_to_full,
    duration_entry,
    feat_category,
    tier_to_full_level,
)
from .text.prerequisites import prerequisite_entry
from .text.stats import (
    ability_entry,
    condition_text,
    damage_text,
    senses_entry,
    size_text,
    speed_text,
)
from .text.strings import (
    common_prefix,
    join_conjunct,
    number_to_text,
    title_case,
    to_plural,
)

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


# Renderer.deity._BASE_PART_TRANSLATORS: label and how a list shows
_DEITY_PARTS: tuple[tuple[str, str, Callable[[Any], str] | None], ...] = (
    (
        "alignment",
        "Alignment",
        lambda v: title_case(" ".join(alignment_abv_to_full(a) for a in v)),
    ),
    ("pantheon", "Pantheon", None),
    ("category", "Category", lambda v: v if isinstance(v, str) else ", ".join(v)),
    ("domains", "Domains", ", ".join),
    ("province", "Province", None),
    ("dogma", "Dogma", None),
    ("altNames", "Alternate Names", ", ".join),
    ("plane", "Home Plane", None),
    ("worshipers", "Typical Worshipers", None),
    ("symbol", "Symbol", None),
    ("favoredWeapons", "Favored Weapons", None),
)


def deity_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.deity``: labelled lines in alphabetical order, then entries."""
    return [*deity_lines(content), *(raw(content).get("entries") or [])]


def deity_lines(content: BaseModel) -> list[str]:
    """A deity's labelled lines, which 5etools sets flush above its entries."""
    data = raw(content)
    lines = [
        (label, f"{{@b {label}:}} {show(data[prop]) if show else data[prop]}")
        for prop, label, show in _DEITY_PARTS
        if data.get(prop) is not None
    ]
    lines += [
        (name, f"{{@b {name}:}} {value}")
        for name, value in (data.get("customProperties") or {}).items()
    ]
    lines.sort(key=lambda line: line[0].lower())
    return [text for _, text in lines]


def deity_heading(content: BaseModel, name: str) -> str:
    """5etools names a deity with its title: "Paladine, the Valiant Warrior"."""
    title = raw(content).get("title")
    return f"{name}, {title_case(title)}" if title else name


def optional_feature_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.optionalfeature``: prerequisite and cost, entries, then its type."""
    data = raw(content)
    prerequisite = prerequisite_entry(data.get("prerequisite"), style=STYLE)
    return [
        *([f"{{@i {prerequisite}}}"] if prerequisite else []),
        *_cost(data.get("consumes") or {}),
        *(data.get("entries") or []),
        f"{{@note Type: {_feature_type(data.get('featureType') or [])}}}",
    ]


def _cost(consumes: Raw) -> list[str]:
    """``getCostEntry``: "Cost: 2 Sorcery Points"."""
    if not consumes.get("name"):
        return []
    words = [w for w in consumes["name"].split(" ") if w]
    most = consumes.get("amountMax", consumes.get("amount"))
    if most is not None and most != 1:
        words[-1] = to_plural(words[-1])
    unit = " ".join(words)
    if consumes.get("amountMin") is not None and consumes.get("amountMax") is not None:
        return [
            f"{{@i Cost: {consumes['amountMin']}\u2013{consumes['amountMax']} {unit}}}"
        ]
    return [f"{{@i Cost: {consumes.get('amount', 1)} {unit}}}"]


def _feature_type(types: list[str]) -> str:
    """``getTypeText``: "Fighting Style; Fighter/Paladin"."""
    names = [OPT_FEATURE_TYPES.get(t, t) for t in types]
    prefix = common_prefix(names) if len(names) > 1 else ""
    rest = "/".join(n[len(prefix) :] for n in names)
    return " ".join(t for t in (prefix.strip(), rest) if t)


_SPACE_SQUARES = {"cramped": 4, "roomy": 16, "vast": 36}
_SPACE_COST_DAYS = {"cramped": (500, 20), "roomy": (1000, 45), "vast": (3000, 125)}
_SPACES = ("cramped", "roomy", "vast")


def facility_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.facility``: level, prerequisite, space, hirelings, orders, entries."""
    data = raw(content)
    items: list[Raw] = []
    if data.get("prerequisite"):
        # 5etools writes a facility's prerequisite in the 2024 style
        text = prerequisite_entry(data["prerequisite"], style="one", skip_prefix=True)
        items.append({"type": "item", "name": "Prerequisite:", "entry": text})
    elif data.get("facilityType") != "basic":
        items.append({"type": "item", "name": "Prerequisite:", "entry": "None"})
    basic = data.get("facilityType") == "basic"
    if space := join_conjunct(
        [_space(s, basic=basic) for s in data.get("space") or []], ", ", " or "
    ):
        items.append({"type": "item", "name": "Space:", "entry": space})
    if hirelings := _hirelings(data.get("hirelings") or []):
        items.append({"type": "item", "name": "Hirelings:", "entry": hirelings})
    if orders := data.get("orders"):
        text = join_conjunct([title_case(o) for o in orders], ", ", " or ")
        name = "Order:" if len(orders) == 1 else "Orders:"
        items.append({"type": "item", "name": name, "entry": text})
    level = (
        [f"{{@i Level {data['level']} Bastion Facility}}"] if data.get("level") else []
    )
    listed = (
        [{"type": "list", "style": "list-hang-notitle", "items": items}]
        if items
        else []
    )
    return [*level, *listed, *(data.get("entries") or [])]


def _space(space: str, *, basic: bool) -> str:
    squares = _SPACE_SQUARES.get(space)
    parts = [f"{{@tip {squares} sq|{squares} squares}}"] if squares else []
    if basic and space in _SPACE_COST_DAYS:
        cost, days = _SPACE_COST_DAYS[space]
        text = f"{cost} GP, {days} days"
        tip = f"{cost} GP and {days} days to add"
        index = _SPACES.index(space)
        if index:
            smaller = _SPACES[index - 1]
            less_cost, less_days = _SPACE_COST_DAYS[smaller]
            tip += (
                f", or, {cost - less_cost} GP and {days - less_days} days to expand "
                f"from a {title_case(smaller)} facility"
            )
        parts.append(f"{{@tip {text}|{tip}}}")
    if not parts:
        return title_case(space)
    # 5etools joins a note that starts with a space with a space
    return f"{title_case(space)}  {{@style [{'; '.join(parts)}]|muted;small}}"


def _hirelings(hirelings: list[Raw]) -> str:
    parts = []
    for hire in hirelings:
        space = (
            f" {{@style ({title_case(hire['space'])})|muted}}"
            if hire.get("space")
            else ""
        )
        if hire.get("exact") is not None:
            parts.append(f"{hire['exact']}{space}")
        elif hire.get("min") is not None and hire.get("max") is not None:
            parts.append(f"{hire['min']}\u2013{hire['max']}{space}")
        elif hire.get("min") is not None:
            parts.append(f"{hire['min']}+ (see below{';' if space else ''}{space})")
    return join_conjunct(parts, ", ", " or ")


def object_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.object``: size, attributes, entries, then actions."""
    data = raw(content)
    return [
        *object_lines(content),
        *(data.get("entries") or []),
        *(data.get("actionEntries") or []),
    ]


def object_lines(content: BaseModel) -> list[str]:
    """An object's size and attributes, which 5etools sets flush above its entries."""
    data = raw(content)
    if data.get("objectType") == "GEN":
        size = "Variable size object"
    else:
        size = f"{size_text(data.get('size'))} {data.get('creatureType') or 'object'}"
    return [f"{{@i {size}}}", *_object_attributes(data)]


def _object_attributes(data: Raw) -> list[str]:
    lines: list[tuple[str, str]] = []
    if data.get("capCrew") is not None or data.get("capPassenger") is not None:
        lines.append(("Creature Capacity", creature_capacity(data)))
    if data.get("capCargo") is not None:
        lines.append(("Cargo Capacity", cargo_capacity(data["capCargo"])))
    for prop, label in (("ac", "Armor Class"), ("hp", "Hit Points")):
        value = data.get(prop)
        if value is not None:
            special = value.get("special") if isinstance(value, dict) else None
            lines.append((label, str(special if special is not None else value)))
    if data.get("speed") is not None:
        lines.append(("Speed", speed_text(data, style=STYLE)))
    if any(data.get(a) is not None for a in ABILITIES):
        scores = ", ".join(
            f"{a.upper()}\u00a0{ability_entry(data, a)}"
            for a in ABILITIES
            if data.get(a) is not None
        )
        lines.append(("Ability Scores", scores))
    # The model gives absent lists as empty ones
    for prop, label, text in (
        ("immune", "Damage Immunities", damage_text),
        ("resist", "Damage Resistances", damage_text),
        ("vulnerable", "Damage Vulnerabilities", damage_text),
        ("conditionImmune", "Condition Immunities", condition_text),
    ):
        if data.get(prop):
            lines.append((label, text(data[prop])))
    if data.get("senses"):
        lines.append(("Senses", senses_entry(data["senses"], style=STYLE)))
    return [f"{{@b {label}:}} {value}" for label, value in lines]


def creature_capacity(data: Raw) -> str:
    """``getShipCreatureCapacity``: "20 crew, 10 passengers"."""
    crew, passengers = data.get("capCrew"), data.get("capPassenger")
    parts = [f"{crew} crew"] if crew else []
    if passengers:
        parts.append(f"{passengers} passenger{'' if passengers == 1 else 's'}")
    return ", ".join(parts)


def cargo_capacity(cargo: Any) -> str:
    """``getShipCargoCapacity``: "100 tons"."""
    return (
        cargo if isinstance(cargo, str) else f"{cargo} ton{'' if cargo == 1 else 's'}"
    )


def race_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.race``: ability scores, creature type, size and speed, entries,
    then the height and weight table."""
    data = raw(content)
    items = [
        data.get("abilityEntry")
        or _item("Ability Scores:", ability_text(data.get("ability") or [])),
        data.get("creatureTypesEntry") or _race_creature_type(data),
        data.get("sizeEntry") or _item("Size:", size_text(data.get("size"))),
        data.get("speedEntry")
        or _item("Speed:", speed_text(data, style=STYLE, long_form=True))
        if data.get("speed") is not None
        else None,
    ]
    listed = [i for i in items if i]
    header = [{"type": "list", "style": "list-hang-notitle", "items": listed}]
    if data.get("_isBaseRace"):
        return [*(header if listed else []), *(data.get("_baseRaceEntries") or [])]
    return [
        *(header if listed else []),
        *(data.get("entries") or []),
        *_height_and_weight(data.get("heightAndWeight")),
    ]


def _item(name: str, entry: str) -> Raw | None:
    return {"type": "item", "name": name, "entry": entry} if entry else None


def _race_creature_type(data: Raw) -> Raw | None:
    """Only a creature type other than humanoid, in the classic style."""
    types = [t for t in data.get("creatureTypes") or [] if str(t).lower() != "humanoid"]
    if not types:
        return None
    choosing = any(isinstance(t, dict) and t.get("choose") for t in types)
    # Parser.monTypeToFullObj(type).asText for a plain type
    names = [
        join_conjunct(
            [title_case(c) for c in sorted(t["choose"], key=str.lower)], ", ", " or "
        )
        if isinstance(t, dict) and t.get("choose")
        else title_case(str(t))
        for t in types
    ]
    return _item(
        "Creature Type:", join_conjunct(names, "; " if choosing else ", ", " and ")
    )


def _height_and_weight(hw: Raw | None) -> list[Any]:
    """``getHeightAndWeightEntries``, without the roller."""
    if not hw:
        return []
    height = hw["baseHeight"]
    feet, inches = height // 12, height % 12
    base_height = (f"{feet}'" if feet else "") + (f'{inches}"' if inches else "")
    return [
        "You may roll for your character's height and weight on the Random Height "
        "and Weight table. The roll in the Height Modifier column adds a number (in "
        "inches) to the character's base height. To get a weight, multiply the "
        "number you rolled for height by the roll in the Weight Modifier column and "
        "add the result (in pounds) to the base weight.",
        {
            "type": "table",
            "caption": "Random Height and Weight",
            "colLabels": [
                "Base Height",
                "Base Weight",
                "Height Modifier",
                "Weight Modifier",
            ],
            "colStyles": [
                "col-2-3 text-center",
                "col-2-3 text-center",
                "col-2-3 text-center",
                "col-2 text-center",
            ],
            "rows": [
                [
                    base_height,
                    f"{hw['baseWeight']} lb.",
                    f"+{hw['heightMod']}",
                    f"\u00d7 {hw.get('weightMod') or '1'} lb.",
                ]
            ],
        },
    ]


def _bonus(value: int) -> str:
    return f"+{value}" if value >= 0 else f"\u2212{abs(value)}"


def ability_text(options: list[Raw]) -> str:
    """``Renderer.getAbilityData(...).asText``: "Strength +2; Choose any other +1"."""
    texts = [_ability_option(o) for o in options]
    if len(texts) <= 1:
        return texts[0] if texts else ""
    letters = " ".join(f"({chr(97 + i)}) {t}" for i, t in enumerate(texts))
    return f"Choose one of: {letters}"


def _ability_option(option: Raw) -> str:
    fixed = sorted(
        (a for a in ABILITIES if option.get(a) is not None),
        key=lambda a: -(option.get(a) or 0),
    )
    texts = [f"{ABILITY_NAMES[a]} {_bonus(option[a])}" for a in fixed]
    choose = option.get("choose") or {}
    if weighted := choose.get("weighted"):
        texts.append(_weighted(weighted))
    if choose.get("from") is not None:
        texts.append(_choose_from(choose, fixed))
    return "; ".join(texts)


def _weighted(weighted: Raw) -> str:
    choices, weights = weighted["from"], weighted["weights"]
    any_ = len(choices) == 6
    equal = len(set(weights)) == 1
    done = 0

    def parts(values: list[int], verb: str) -> list[str]:
        nonlocal done
        if any_ and equal and len(weights) > 1 and values and values[0] == weights[0]:
            return [
                f"{'choose ' if done else ''}{number_to_text(len(weights))} different {_bonus(values[0])}"
            ]
        out = []
        for value in values:
            if any_:
                out.append(
                    f"{'choose ' if done else ''}any {'other ' if done else ''}{_bonus(value)}"
                )
            else:
                out.append(
                    f"one {'other ' if done else ''}ability to {verb} by {abs(value)}"
                )
            done += 1
        return out

    increases = parts(sorted((w for w in weights if w >= 0), reverse=True), "increase")
    reductions = parts(sorted((w for w in weights if w < 0), reverse=True), "decrease")
    if any_:
        return "Choose " + "; ".join(increases + reductions)
    names = join_conjunct([ABILITY_NAMES[a] for a in choices], ", ", " and ")
    return f"From {names} choose " + join_conjunct(
        increases + reductions, ", ", " and "
    )


def _choose_from(choose: Raw, fixed: list[str]) -> str:
    choices = choose["from"]
    every = len(choices) == 6
    with_fixed = len({*fixed, *(c.lower() for c in choices)}) == 6
    amount = _bonus(choose.get("amount", 1))
    count = choose.get("count") or 0
    parts = ["any"] if every else ["any other"] if with_fixed else []
    if count > 1:
        parts.append(number_to_text(count))
    if every or with_fixed:
        parts.append(f"{'unique ' if count > 1 else ''}{amount}")
    else:
        names = join_conjunct([ABILITY_NAMES[a] for a in choices], ", ", " or ")
        parts.append(f"{names} {amount}")
    return "Choose " + " ".join(parts)


def background_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.generic``: the prerequisite, then entries."""
    data = raw(content)
    prerequisite = prerequisite_entry(data.get("prerequisite"), style=STYLE)
    return [*([prerequisite] if prerequisite else []), *(data.get("entries") or [])]


def vehicle_upgrade_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.vehicleUpgrade``: its types and prerequisite, then entries."""
    data = raw(content)
    # 5etools joins the types as an array: with a bare comma
    types = ",".join(
        VEHICLE_UPGRADE_TYPES.get(t, str(t)) for t in data.get("upgradeType") or []
    )
    prerequisite = prerequisite_entry(data.get("prerequisite"), style=STYLE)
    summary = ", ".join(t for t in (types, prerequisite) if t)
    # No upgrade in the data has a cost, so 5etools' cost line isn't ported
    return [*([f"{{@i {summary}}}"] if summary else []), *(data.get("entries") or [])]


def language_entries(content: BaseModel, _: Omnidexer | None) -> list[Any]:
    """``Renderer.language``: its kind, speakers, origin and script, then entries."""
    data = raw(content)
    lines = [
        f"{{@b {label}:}} {value}"
        for label, value in (
            ("Typical Speakers", ", ".join(data.get("typicalSpeakers") or [])),
            ("Origin", data.get("origin")),
            ("Script", data.get("script")),
        )
        if value
    ]
    entries = list(data.get("entries") or [])
    if dialects := data.get("dialects"):
        entries.append(
            "This language is a family which includes the following dialects: "
            f"{', '.join(sorted(dialects, key=str.lower))}. Creatures that speak "
            "different dialects of the same language can communicate with one another."
        )
    if not entries and not lines:
        entries = ["{@i No information available.}"]
    kind = [f"{{@i {title_case(data['type'])} language}}"] if data.get("type") else []
    return [*kind, *lines, *entries]
