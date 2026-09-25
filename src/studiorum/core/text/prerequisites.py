"""Prerequisites as 5etools writes them, a port of ``Renderer.utils.prerequisite``.

``prerequisite_entry`` returns 5etools markup ("Prerequisite: {@feat Alert}"),
so a renderer resolves the tags; ``strip_tags`` gives plain text. ``style`` is
5etools' style hint: "classic" (2014 wording, "4th level") or "one" ("Level 4+").
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from .parser import (
    ABILITIES,
    ABILITY_NAMES,
    FEAT_CATEGORIES,
    alignment_list_to_full,
    pact_to_full,
)
from .strings import (
    article,
    common_suffix,
    join_conjunct,
    number_to_text,
    ordinal,
    title_case,
)

type Raw = dict[str, Any]

# The order 5etools lists a prerequisite's parts in
_WEIGHTS = {
    key: i
    for i, key in enumerate(
        (
            "level",
            "pact",
            "patron",
            "spell",
            "race",
            "alignment",
            "ability",
            "proficiency",
            "expertise",
            "spellcasting",
            "spellcasting2020",
            "spellcastingFeature",
            "spellcastingPrepared",
            "spellcastingFocus",
            "psionics",
            "feature",
            "feat",
            "featCategory",
            "optionalfeature",
            "background",
            "item",
            "itemType",
            "itemProperty",
            "campaign",
            "culture",
            "group",
            "other",
            "otherSummary",
            "exclusiveFeatCategory",
        )
    )
}
_FOCUSES = {
    "arcane": "Arcane Focus",
    "druid": "Druidic Focus",
    "holy": "Holy Symbol",
    "artisansTool": "Artisan’s Tools",
}


def prerequisite_entry(
    prerequisites: list[Raw] | None,
    *,
    style: str = "classic",
    skip_prefix: bool = False,
) -> str:
    """``getEntry``: each item is one way to qualify; "" when there are none."""
    if not prerequisites:
        return ""
    prerequisites = [_plain(p) for p in prerequisites]
    shared: Raw = {}
    if len(prerequisites) > 1:
        first = prerequisites[0]
        shared = {
            k: v
            for k, v in first.items()
            if all(p.get(k, _MISSING) == v for p in prerequisites)
        }
    shared_text = (
        prerequisite_entry([shared], style=style, skip_prefix=True) if shared else ""
    )

    count = 0
    has_note = False
    choices = []
    for prereq in prerequisites:
        note = prereq.get("note")
        has_note = has_note or bool(note)
        keys = sorted((k for k in prereq if not shared.get(k)), key=_Weighted)
        parts = []
        for key in keys:
            if key == "note":
                continue
            count += 1
            parts.append(_PARTS[key](prereq[key], style))
        parts = [p for p in parts if p]
        joined = ("; " if any(" or " in p for p in parts) else ", ").join(parts)
        choice = ". ".join(t for t in (joined, note) if t)
        if choice:
            choices.append(choice)

    if not choices and not shared_text:
        return ""
    suffix = common_suffix(choices)
    trimmed = [c[: -len(suffix)] for c in choices] if suffix else choices
    if has_note:
        joined_choices = " Or, ".join(trimmed) + suffix
    else:
        sep = "; " if any(" or " in c for c in trimmed) else ", "
        joined_choices = join_conjunct(trimmed, sep, " or ") + suffix

    prefix = "" if skip_prefix else f"Prerequisite{'' if count == 1 else 's'}: "
    both = [t for t in (shared_text, joined_choices) if t]
    if len(both) < 2:
        return prefix + ", ".join(both)
    if any("," in t for t in both):
        joiner = "; plus " if any(";" in t for t in both) else "; "
    else:
        joiner = ", "
    return prefix + joiner.join(both)


_MISSING = object()


class _Weighted:
    """5etools' sort: a key it has no weight for compares as NaN, so stays put."""

    def __init__(self, key: str) -> None:
        self.weight = _WEIGHTS.get(key, math.nan)

    def __lt__(self, other: _Weighted) -> bool:
        return self.weight - other.weight < 0


def _plain(value: Any) -> Any:
    """Pydantic models as the dicts 5etools has."""
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    return value


def _level(value: Any, style: str) -> str:
    def level_text(level: Any) -> str:
        return (
            f"{ordinal(int(level))} level" if style == "classic" else f"Level {level}+"
        )

    if not isinstance(value, dict):
        return level_text(value)
    cls: Any = value.get("class")
    subclass: Any = value.get("subclass")
    if not cls and not subclass:
        return level_text(value["level"])
    subclass_shown = bool(
        subclass and (subclass.get("visible") or subclass.get("visibleStats"))
    )
    class_shown = bool(
        cls and (cls.get("visible") or subclass_shown or cls.get("visibleStats"))
    )
    class_part = ""
    if class_shown and subclass_shown:
        class_part = f" {cls['name']} ({subclass['name']})"
    elif class_shown:
        class_part = f" {cls['name']}"
    elif subclass_shown:
        class_part = f" <remember to insert class name here> ({subclass['name']})"
    level = level_text(value["level"]) if value.get("level") != 1 else ""
    return " ".join(t for t in (level, class_part) if t)


def _spell(value: list[Any], _: str) -> str:
    out = []
    for spell in value:
        if not isinstance(spell, str):
            out.append(f"{{@filter {spell['entry']}|spells|{spell['choose']}}}")
            continue
        text, _sep, suffix = spell.partition("#")
        if not suffix:
            out.append(f"{{@spell {spell}}}")
        elif suffix == "c":
            out.append(f"{{@spell {text}}} cantrip")
        elif suffix == "x":
            out.append("{@spell hex} spell or a warlock feature that curses")
        else:
            out.append(spell)
    return join_conjunct(out, ", ", " or ")


def _uid_tag(tag: str) -> Callable[[list[str], str], str]:
    def render(value: list[str], style: str) -> str:
        uids = [
            uid
            if style == "classic"
            else "|".join(
                title_case(p) if i == 0 else p for i, p in enumerate(uid.split("|"))
            )
            for uid in value
        ]
        return join_conjunct([f"{{@{tag} {uid}}}" for uid in uids], ", ", " or ")

    return render


def _feat_category(value: list[Any], _: str) -> str:
    names = [
        FEAT_CATEGORIES.get(c, c)
        if isinstance(c, str)
        else f"{number_to_text(c['count'])} {FEAT_CATEGORIES.get(c['category'], c['category'])}"
        for c in value
    ]
    plural = "" if isinstance(value[-1], str) else "s"
    return f"Any {join_conjunct(names, ', ', ' or ')} Feat{plural}"


def _exclusive_feat_category(value: list[str], _: str) -> str:
    names = [FEAT_CATEGORIES.get(c, c) for c in value]
    return f"Can't Have Another {join_conjunct(names, ', ', ' or ')} Feat"


def _feature(value: list[str], style: str) -> str:
    names = join_conjunct(value, ", ", " or ")
    if style == "classic":
        return names
    return f"{names} Feature{'' if len(value) == 1 else 's'}"


def _named(subrace: bool) -> Callable[[list[Raw], str], str]:
    """Races and backgrounds: the first name in title case (every name in "one")."""

    def render(value: list[Raw], style: str) -> str:
        parts = []
        for i, it in enumerate(value):
            name = it.get("displayEntry") or (
                title_case(it["name"]) if i == 0 or style != "classic" else it["name"]
            )
            if subrace and it.get("subrace") is not None:
                name += f" ({it['subrace']})"
            parts.append(name)
        return join_conjunct(parts, ", ", " or ")

    return render


def _ability(value: list[Raw], style: str) -> str:
    higher = " or higher" if style == "classic" else "+"
    all_equal: Any = None
    for option in value:
        for required in option.values():
            if all_equal is None:
                all_equal = required
            elif required != all_equal:
                all_equal = None
                break
        else:
            continue
        break

    multiple = multi_multiple = False
    options = []
    for option in value:
        if all_equal:
            abilities = list(option)
            multiple = multiple or len(abilities) > 1
            options.append(
                join_conjunct([ABILITY_NAMES[a] for a in abilities], ", ", " and ")
            )
            continue
        groups: dict[Any, list[str]] = {}
        for ability, required in option.items():
            groups.setdefault(required, []).append(ability)
        is_multi = False
        by_score = []
        for required, abilities in sorted(groups.items(), key=lambda g: -float(g[0])):
            multiple = multiple or len(abilities) > 1
            if len(abilities) > 1:
                multi_multiple = is_multi = True
            abilities.sort(key=_ability_order)
            names = join_conjunct([ABILITY_NAMES[a] for a in abilities], ", ", " and ")
            by_score.append(f"{names} {required}{higher}")
        options.append(join_conjunct(by_score, "; " if is_multi else ", ", " and "))

    complex_ = multi_multiple or multiple or all_equal is None
    joined = join_conjunct(
        options,
        " - " if multi_multiple else "; " if multiple else ", ",
        " {@i or} " if complex_ else " or ",
    )
    return joined + (f" {all_equal}{higher}" if all_equal is not None else "")


def _ability_order(ability: str) -> int:
    return len(ABILITIES) if ability == "special" else ABILITIES.index(ability)


def _proficiency(value: list[Raw], style: str) -> str:
    def one(kind: str, prof: Any) -> str:
        match kind:
            case "armor" if prof == "shield":
                return (
                    "Proficiency with shields"
                    if style == "classic"
                    else "Shield Training"
                )
            case "armor":
                if style == "classic":
                    return f"Proficiency with {prof} armor"
                return f"{title_case(prof)} Armor Training"
            case "weapon":
                return f"Proficiency with a {prof} weapon"
            case "weaponGroup":
                return f"{title_case(prof)} Weapon Proficiency"
            case "skill" if prof is True:
                return "Proficiency in a skill"
            case "skill":
                skills = [f"{{@skill {title_case(s)}}}" for s in prof]
                plural = "" if len(prof) == 1 else "s"
                return f"Proficiency in the {join_conjunct(skills, ', ', ' and ')} skill{plural}"
        raise ValueError(f"Unhandled proficiency type: {kind}")

    # 5etools joins several kinds in one object as an array, with commas
    parts = [",".join(one(k, v) for k, v in obj.items()) for obj in value]
    return join_conjunct(parts, ", ", " or ")


def _expertise(value: list[Raw], _: str) -> str:
    def one(kind: str, prof: Any) -> str:
        if kind != "skill":
            raise ValueError(f"Unhandled expertise type: {kind}")
        return (
            "Expertise in a skill"
            if prof is True
            else f"Expertise in {title_case(str(prof))}"
        )

    parts = [",".join(one(k, v) for k, v in obj.items()) for obj in value]
    return join_conjunct(parts, ", ", " or ")


def _spellcasting_focus(value: Any, style: str) -> str:
    suffix = (
        "spellcasting focus"
        if style == "classic"
        else "{@variantrule Spellcasting Focus|XPHB}"
    )
    if value is True:
        return f"Ability to use a {suffix}"
    source = "" if style == "classic" else "|XPHB"
    parts = []
    for i, focus in enumerate(value):
        name = _FOCUSES.get(focus)
        text = f"{{@item {name}{source}}}" if name else focus
        parts.append(f"{article(name or focus)} {text}" if i == 0 else text)
    return f"Ability to use {join_conjunct(parts, ', ', ' or ')} as a {suffix}"


# Neither is in 5etools' data, and the item tables live in the loader, so these
# print the abbreviations
def _item_type(value: list[str], _: str) -> str:
    return join_conjunct(value, ", ", " and ")


def _item_property(value: list[str] | None, _: str) -> str:
    if value is None:
        return "No Other Properties"
    return f"{join_conjunct(value, ', ', ' and ')} Property"


def _listed(suffix: str) -> Callable[[list[str], str], str]:
    return lambda value, _: f"{join_conjunct(value, ', ', ' or ')} {suffix}"


_PARTS: dict[str, Callable[[Any, str], str]] = {
    "level": _level,
    "pact": lambda v, _: pact_to_full(v),
    "patron": lambda v, _: f"{v} patron",
    "spell": _spell,
    "feat": _uid_tag("feat"),
    "featCategory": _feat_category,
    "exclusiveFeatCategory": _exclusive_feat_category,
    "optionalfeature": _uid_tag("optfeature"),
    "feature": _feature,
    "item": lambda v, _: join_conjunct(v, ", ", " or "),
    "itemType": _item_type,
    "itemProperty": _item_property,
    "otherSummary": lambda v, _: v["entry"],
    "other": lambda v, _: v,
    "race": _named(subrace=True),
    "background": _named(subrace=False),
    "ability": _ability,
    "proficiency": _proficiency,
    "expertise": _expertise,
    "spellcasting": lambda v, _: "The ability to cast at least one spell",
    "spellcasting2020": lambda v, s: (
        "Spellcasting or Pact Magic " + ("feature" if s == "classic" else "Feature")
    ),
    "spellcastingFeature": lambda v, _: "Spellcasting Feature",
    "spellcastingPrepared": lambda v, _: (
        "Spellcasting feature from a class that prepares spells"
    ),
    "spellcastingFocus": _spellcasting_focus,
    "psionics": lambda v, _: "Psionic Talent feature or Wild Talent feat",
    "alignment": lambda v, _: alignment_list_to_full(v),
    "campaign": _listed("Campaign"),
    "culture": _listed("Culture"),
    "membership": lambda v, _: f"Membership in the {join_conjunct(v, ', ', ' or ')}",
    "group": lambda v, _: (
        f"{join_conjunct([title_case(g) for g in v], ', ', ' or ')} Group"
    ),
}
