"""Classes and subclasses as the entries 5etools' compact renderer shows.

A port of ``Renderer.class`` and ``Renderer.subclass`` compact rendering
(``js/render.js``) in 5etools' default "one" style: a class's core traits,
its class table and every feature in full; a subclass's features in full.
Features are stored by uid; they and the ``refClassFeature``,
``refSubclassFeature``, ``refOptionalfeature`` and ``refFeat`` entries inside them are
looked up as 5etools' dereferencer does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models.content import ContentType

if TYPE_CHECKING:
    from .loaders.omnidexer import Omnidexer
    from .models.classes import Class
    from .models.subclasses import Subclass

type Raw = dict[str, Any]

ABILITIES = {"str": "Strength", "dex": "Dexterity", "con": "Constitution", "int": "Intelligence", "wis": "Wisdom", "cha": "Charisma"}  # fmt: skip
_REFS = {
    "refClassFeature": ("classFeature", ContentType.CLASS_FEATURE),
    "refSubclassFeature": ("subclassFeature", ContentType.SUBCLASS_FEATURE),
    "refOptionalfeature": ("optionalfeature", ContentType.OPTIONALFEATURE),
    "refFeat": ("feat", ContentType.FEAT),
}
# Their tags' default source, for a uid that gives none
_DEFAULT_SOURCE = {ContentType.OPTIONALFEATURE: "PHB", ContentType.FEAT: "PHB"}
# Props a looked-up feature keeps as an entry
_FEATURE_PROPS = ("name", "entries", "level")
_SKILL_COUNT = 18  # a choice from every skill


def class_entries(cls: Class, omnidexer: Omnidexer | None) -> list[Any]:
    """Core traits, the class table, then every class feature, "Level N: Name"."""
    data = cls.model_dump(by_alias=True, exclude_none=True)
    features = [
        _feature(uid, ContentType.CLASS_FEATURE, omnidexer)
        for uid in _uids(data.get("classFeatures", []), "classFeature")
    ]
    found = [f for f in features if f is not None]
    for feature in found:
        if feature.get("level") and feature.get("name"):
            feature["name"] = f"Level {feature['level']}: {feature['name']}"
    return [*_core_traits(data), _class_table(data), *found]


def subclass_entries(subclass: Subclass, omnidexer: Omnidexer | None) -> list[Any]:
    """Every subclass feature; features within one are "Level N: Name"."""
    data = subclass.model_dump(by_alias=True, exclude_none=True)
    features = [
        f
        for uid in _uids(data.get("subclassFeatures", []), "subclassFeature")
        if (f := _feature(uid, ContentType.SUBCLASS_FEATURE, omnidexer)) is not None
    ]
    for feature in features:
        feature["entries"] = [_level_named(e) for e in feature.get("entries", [])]
    if features and features[0].get("name") == subclass.name:
        del features[0]["name"]
    return features


def _uids(values: list[Any], key: str) -> list[str]:
    return [str(v.get(key, "")) if isinstance(v, dict) else str(v) for v in values]


def _level_named(entry: Any) -> Any:
    if (
        isinstance(entry, dict)
        and entry.get("type") == "entries"
        and entry.get("name")
        and entry.get("level")
    ):
        return {**entry, "name": f"Level {entry['level']}: {entry['name']}"}
    return entry


def _feature(uid: str, kind: ContentType, omnidexer: Omnidexer | None) -> Raw | None:
    """A feature by uid as an entries entry, its own references resolved."""
    if omnidexer is None:
        return None
    found = omnidexer.find_uid(kind, uid)
    if found is None:
        return None
    data = found.model_dump(by_alias=True, exclude_none=True)
    entry = {"type": "entries", **{k: data[k] for k in _FEATURE_PROPS if k in data}}
    entry["entries"] = _dereferenced(entry.get("entries", []), omnidexer)
    return entry


def _dereferenced(entries: Any, omnidexer: Omnidexer) -> Any:
    """Entries with each feature reference replaced by the feature."""
    if isinstance(entries, list):
        return [_dereferenced(e, omnidexer) for e in entries]
    if not isinstance(entries, dict):
        return entries
    ref = _REFS.get(str(entries.get("type")))
    if ref is None:
        return {k: _dereferenced(v, omnidexer) for k, v in entries.items()}
    key, kind = ref
    uid = str(entries.get(key, ""))
    if kind in _DEFAULT_SOURCE and "|" not in uid:
        uid = f"{uid}|{_DEFAULT_SOURCE[kind]}"
    feature = _feature(uid, kind, omnidexer)
    if feature is None:
        return {"type": "entries", "entries": []}
    if entries.get("name"):
        feature["name"] = entries["name"]
    return feature


# region Core traits


def _core_traits(cls: Raw) -> list[Any]:
    name = cls["name"]
    hd = cls.get("hd") or {}
    start = cls.get("startingProficiencies") or {}
    lines: list[tuple[str, str]] = []
    if primary := cls.get("primaryAbility"):
        lines.append(
            (
                "Primary Ability",
                _conjunct(
                    [
                        _conjunct([ABILITIES[k] for k, v in p.items() if v], "and")
                        for p in primary
                    ],
                    "or",
                ),
            )
        )
    if hd.get("faces"):
        number, faces = hd.get("number", 1), hd["faces"]
        die = f"{{@dice {number}d{faces}|{'' if number == 1 else number}D{faces}|Hit die}}"
        lines += [
            ("Hit Point Die", f"{die} per {name} level"),
            ("Hit Points at Level 1", f"{number * faces} + Con. modifier"),
            (
                f"Hit Points per additional {name} Level",
                f"{die} + your Con. modifier, or, {number * faces // 2 + 1} + your Con. modifier",
            ),
        ]
    if saves := cls.get("proficiency"):
        lines.append(
            (
                "Saving Throw Proficiencies",
                ", ".join(ABILITIES.get(str(s), str(s)) for s in saves),
            )
        )
    if skills := start.get("skills"):
        lines.append(("Skill Proficiencies", _skills(skills)))
    if weapons := start.get("weapons"):
        lines.append(
            (
                "Weapon Proficiencies",
                _proficiencies(weapons, ("simple", "martial"), "weapons"),
            )
        )
    if tools := start.get("tools"):
        lines.append(("Tool Proficiencies", _conjunct([str(t) for t in tools], "and")))
    if armor := start.get("armor"):
        lines.append(
            (
                "Armor Training",
                _proficiencies(armor, ("light", "medium", "heavy"), "armor"),
            )
        )
    out: list[Any] = [f"{{@b {label}:}} {value}" for label, value in lines]
    return out + _starting_equipment(cls.get("startingEquipment") or {})


def _conjunct(parts: list[str], word: str) -> str:
    """5etools' joinConjunct: "a, b and c"."""
    if len(parts) < 2:
        return "".join(parts)
    return f"{', '.join(parts[:-1])} {word} {parts[-1]}"


def _skills(skills: list[Any]) -> str:
    out = []
    for skill in skills:
        if not isinstance(skill, dict):
            out.append(str(skill).title())
            continue
        if "any" in skill:
            count = skill["any"]
            out.append(
                f"{{@i Choose any {count} {'skill' if count == 1 else 'skills'}}}"
            )
            continue
        named = [k.title() for k, v in sorted(skill.items()) if k != "choose" and v]
        if choose := skill.get("choose"):
            count = choose.get("count", 1)
            options = choose.get("from", [])
            if len(options) == _SKILL_COUNT:
                named.append(
                    f"{{@i Choose any {count} {'skill' if count == 1 else 'skills'}}}"
                )
            else:
                named.append(
                    f"{{@i Choose {count}:}} {_conjunct([o.title() for o in options], 'or')}"
                )
        out.append(", ".join(named))
    return "; ".join(out) + "."


def _proficiencies(values: list[Any], kinds: tuple[str, ...], noun: str) -> str:
    """ "Simple and Martial weapons", "Light and Medium armor and Shields"."""
    grouped = [str(v).title() for v in values if v in kinds]
    others = []
    for value in values:
        if value in kinds:
            continue
        if isinstance(value, dict):
            others.append(str(value.get("full") or value.get("proficiency") or ""))
        elif value == "shield":
            others.append("{@item shield|XPHB|Shields}")
        else:
            others.append(str(value))
    group = f"{_conjunct(grouped, 'and')} {noun}" if grouped else ""
    return _conjunct([p for p in (group, *others) if p], "and")


def _starting_equipment(equipment: Raw) -> list[Any]:
    if equipment.get("additionalFromBackground") and equipment.get("default"):
        out: list[Any] = [
            "{@b Starting Equipment:} You start with the following items, plus anything provided by your background.",
            {"type": "list", "items": equipment["default"]},
        ]
        if (gold := equipment.get("goldAlternative")) is not None:
            out.append(
                f"Alternatively, you may start with {gold} gp to buy your own equipment."
            )
        return out
    entries = equipment.get("entries") or []
    if entries and isinstance(entries[0], str):
        return [f"{{@b Starting Equipment:}} {entries[0]}", *entries[1:]]
    return list(entries)


# endregion

# region Class table


def _class_table(cls: Raw) -> Raw:
    """Level, proficiency bonus, features, then the class's own columns."""
    names: dict[int, list[str]] = {}
    for uid in _uids(cls.get("classFeatures", []), "classFeature"):
        parts = uid.split("|")
        if len(parts) > 3 and parts[3].isdigit():
            names.setdefault(int(parts[3]), []).append(parts[0])
    labels = ["Level", "Proficiency Bonus", "Features"]
    styles = ["col-1 text-center", "col-1 text-center", "col-8"]
    columns: list[list[Any]] = []
    for group in cls.get("classTableGroups", []):
        rows = group.get("rows") or []
        if slots := group.get("rowsSpellProgression"):
            # No slots of a level show as a dash
            rows = [[cell or "\u2014" for cell in row] for row in slots]
        for i, label in enumerate(group.get("colLabels", [])):
            labels.append(label)
            styles.append("col-1 text-center")
            columns.append([row[i] if i < len(row) else "" for row in rows])
    rows = [
        [
            _ordinal(level),
            f"+{(level - 1) // 4 + 2}",
            ", ".join(names.get(level, [])) or "—",
            *(
                column[level - 1] if level - 1 < len(column) else ""
                for column in columns
            ),
        ]
        for level in range(1, 21)
    ]
    return {
        "type": "table",
        "caption": f"The {cls['name']}",
        "colLabels": labels,
        "colStyles": styles,
        "rows": rows,
        "wide": True,
    }


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


# endregion
