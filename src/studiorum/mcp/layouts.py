"""One entry as Markdown: a statblock, a spell, an item, a class, or name and text."""

from __future__ import annotations

from typing import Any

from studiorum.core import encounter
from studiorum.core.loaders import item_types
from studiorum.mcp.markdown import render, strip_tags

type Raw = dict[str, Any]

_SIZES = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large", "H": "Huge", "G": "Gargantuan"}  # fmt: skip
_ALIGNMENTS = {"L": "lawful", "N": "neutral", "NX": "neutral", "NY": "neutral", "C": "chaotic", "G": "good", "E": "evil", "U": "unaligned", "A": "any alignment"}  # fmt: skip
# 5etools writes "any evil alignment" and the like as the set of codes it allows
_ALIGNMENT_SETS = {
    frozenset({"L", "NX", "C", "G", "NY", "E"}): "any alignment",
    frozenset({"L", "NX", "C", "E"}): "any evil alignment",
    frozenset({"L", "NX", "C", "G"}): "any good alignment",
    frozenset({"L", "G", "NY", "E"}): "any lawful alignment",
    frozenset({"C", "G", "NY", "E"}): "any chaotic alignment",
    frozenset({"L", "NX", "C", "NY", "E"}): "any non-good alignment",
    frozenset({"L", "NX", "C", "NY", "G"}): "any non-evil alignment",
    frozenset({"NX", "C", "G", "NY", "E"}): "any non-lawful alignment",
    frozenset({"L", "NX", "G", "NY", "E"}): "any non-chaotic alignment",
}
_ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
_ABILITY_NAMES = {"str": "Strength", "dex": "Dexterity", "con": "Constitution", "int": "Intelligence", "wis": "Wisdom", "cha": "Charisma"}  # fmt: skip
_SCHOOLS = {"A": "Abjuration", "C": "Conjuration", "D": "Divination", "E": "Enchantment", "V": "Evocation", "I": "Illusion", "N": "Necromancy", "T": "Transmutation"}  # fmt: skip
_DAMAGE = {"B": "Bludgeoning", "P": "Piercing", "S": "Slashing", "N": "Necrotic", "R": "Radiant", "O": "Force", "F": "Fire", "C": "Cold", "L": "Lightning", "T": "Thunder", "A": "Acid", "I": "Poison", "Y": "Psychic"}  # fmt: skip
_PROPERTIES = {"A": "Ammunition", "F": "Finesse", "H": "Heavy", "L": "Light", "LD": "Loading", "R": "Reach", "S": "Special", "T": "Thrown", "2H": "Two-Handed", "V": "Versatile", "RLD": "Reload", "BF": "Burst Fire"}  # fmt: skip


def to_markdown(content_type: str, data: Raw) -> str:
    """The entry laid out for reading, with tags reduced to their text."""
    layout = {
        "creature": _creature,
        "spell": _spell,
        "item": _item,
        "class": _class,
        "subclass": _subclass,
    }.get(content_type, _generic)
    return "\n\n".join(p for p in layout(data, content_type) if p)


def _title(data: Raw) -> str:
    return f"# {strip_tags(str(data.get('name', '')))}"


def _source(data: Raw) -> str:
    source = data.get("source", "")
    return f"{source}, p. {data['page']}" if data.get("page") else str(source)


def _line(label: str, value: str) -> str:
    return f"**{label}** {value}" if value else ""


def _join(values: Any, sep: str = ", ") -> str:
    """5etools lists of strings or nested dicts ({"resist": [...], "note": ...}) as text."""
    if isinstance(values, str):
        return strip_tags(values)
    if isinstance(values, list):
        return sep.join(t for t in (_join(v) for v in values) if t)
    if isinstance(values, dict):
        if "special" in values:
            return strip_tags(str(values["special"]))
        inner = next((v for k, v in values.items() if isinstance(v, list)), [])
        parts = [values.get("preNote", ""), _join(inner), values.get("note", "")]
        return " ".join(strip_tags(str(p)) for p in parts if p)
    return str(values)


def _entries(entries: Any, depth: int = 2) -> str:
    return render(entries, depth) if entries else ""


def _named_blocks(heading: str, blocks: Any, intro: Any = None) -> str:
    """Traits and actions: a heading, then each as ***Name.*** text."""
    if not blocks:
        return ""
    lines = [f"## {heading}", _entries(intro)]
    for block in blocks:
        if not isinstance(block, dict):
            lines.append(_entries(block))
            continue
        name = strip_tags(str(block.get("name", "")))
        body = _entries(block.get("entries"), 3)
        first, _, rest = body.partition("\n\n")
        lines.append(f"***{name}.*** {first}".strip() + (f"\n\n{rest}" if rest else ""))
    return "\n\n".join(line for line in lines if line)


def _alignment(codes: Any) -> str:
    if not isinstance(codes, list) or not codes:
        return ""
    if all(isinstance(c, dict) for c in codes):
        return " or ".join(
            str(c["special"]) if "special" in c else _alignment(c.get("alignment"))
            for c in codes
        )
    as_set = frozenset(str(c) for c in codes)
    if as_set in _ALIGNMENT_SETS:
        return _ALIGNMENT_SETS[as_set]
    if as_set in ({"N"}, {"N"}):
        return "neutral"
    return " ".join(_ALIGNMENTS.get(str(c), str(c)) for c in codes)


def _creature_type(kind: Any) -> str:
    if isinstance(kind, dict):
        base = kind.get("type")
        if isinstance(base, dict):
            base = " or ".join(base.get("choose", []))
        tags = [
            t if isinstance(t, str) else t.get("tag", "") for t in kind.get("tags", [])
        ]
        return f"{base} ({', '.join(tags)})" if tags else str(base)
    return str(kind or "")


def _ac(values: Any) -> str:
    parts = []
    for value in values if isinstance(values, list) else [values]:
        if isinstance(value, dict):
            if "special" in value:
                parts.append(strip_tags(str(value["special"])))
                continue
            text = str(value.get("ac", ""))
            if value.get("from"):
                text += f" ({_join(value['from'])})"
            if value.get("condition"):
                text += f" {strip_tags(value['condition'])}"
            parts.append(text)
        else:
            parts.append(str(value))
    return ", ".join(parts)


def _speed(speed: Any) -> str:
    if not isinstance(speed, dict):
        return str(speed or "")
    parts = []
    for mode in ("walk", "burrow", "climb", "fly", "swim"):
        value = speed.get(mode)
        if value is None:
            continue
        if isinstance(value, dict):
            text = f"{value.get('number')} ft. {strip_tags(str(value.get('condition', '')))}".strip()
        else:
            text = f"{value} ft."
        if mode == "fly" and speed.get("canHover") and "hover" not in text:
            text += " (hover)"
        parts.append(text if mode == "walk" else f"{mode.title()} {text}")
    return ", ".join(parts)


def _abilities(data: Raw) -> str:
    scores = [data.get(a) for a in _ABILITIES]
    if not all(isinstance(s, int) for s in scores):
        return ""
    cells = [f"{s} ({(s - 10) // 2:+d})" for s in scores if isinstance(s, int)]
    header = " | ".join(a.upper() for a in _ABILITIES)
    return f"| {header} |\n|{'---|' * 6}\n| {' | '.join(cells)} |"


def _bonuses(values: Any, names: dict[str, str] | None = None) -> str:
    if not isinstance(values, dict):
        return ""
    return ", ".join(
        f"{(names or {}).get(k, k.title())} {v}"
        for k, v in values.items()
        if isinstance(v, str)
    )


def _challenge(cr: Any) -> str:
    base = cr.get("cr") if isinstance(cr, dict) else cr
    if base is None:
        return ""
    xp = encounter.creature_xp(cr)
    text = f"{base} ({xp:,} XP)" if xp is not None else str(base)
    if isinstance(cr, dict) and cr.get("lair"):
        text += f", or {cr['lair']} in its lair"
    return text


def _spellcasting(blocks: Any) -> list[Raw]:
    """Spellcasting blocks as traits, with their spell lists as text."""
    out = []
    for block in blocks or []:
        lines = list(block.get("headerEntries", []))
        if block.get("will"):
            lines.append(f"At will: {_join(block['will'])}")
        for key, label in (("daily", "/day"), ("rest", "/rest")):
            for uses, spells in (block.get(key) or {}).items():
                each = " each" if uses.endswith("e") else ""
                lines.append(f"{uses.rstrip('e')}{label}{each}: {_join(spells)}")
        for level, spells in sorted((block.get("spells") or {}).items()):
            slots = f" ({spells['slots']} slots)" if spells.get("slots") else ""
            label = "Cantrips" if level == "0" else f"Level {level}{slots}"
            lines.append(f"{label}: {_join(spells.get('spells', []))}")
        lines += block.get("footerEntries", [])
        out.append({"name": block.get("name", "Spellcasting"), "entries": lines})
    return out


def _creature(data: Raw, _: str) -> list[str]:
    size = " or ".join(_SIZES.get(str(s), str(s)) for s in data.get("size", []))
    kind = f"*{size} {_creature_type(data.get('type'))}, {_alignment(data.get('alignment'))}*"
    hp = data.get("hp") or {}
    hp_text = (
        hp.get("special") or f"{hp.get('average')} ({hp.get('formula')})" if hp else ""
    )
    senses = _join(data.get("senses") or [])
    passive = f"Passive Perception {data['passive']}" if data.get("passive") else ""
    spellcasting = _spellcasting(data.get("spellcasting"))
    by_place: dict[str, list[Raw]] = {}
    for block, raw in zip(spellcasting, data.get("spellcasting") or [], strict=True):
        by_place.setdefault(raw.get("displayAs", "trait"), []).append(block)
    stats = [
        _line("Armor Class", _ac(data.get("ac"))),
        _line("Hit Points", strip_tags(str(hp_text))),
        _line("Speed", _speed(data.get("speed"))),
    ]
    details = [
        _line("Saving Throws", _bonuses(data.get("save"), _ABILITY_NAMES)),
        _line("Skills", _bonuses(data.get("skill"))),
        _line("Vulnerabilities", _join(data.get("vulnerable") or [])),
        _line("Resistances", _join(data.get("resist") or [])),
        _line("Immunities", _join(data.get("immune") or [])),
        _line("Condition Immunities", _join(data.get("conditionImmune") or [])),
        _line("Senses", ", ".join(s for s in (senses, passive) if s)),
        _line("Languages", _join(data.get("languages") or []) or "None"),
        _line("Challenge", _challenge(data.get("cr"))),
    ]
    uses = data.get("legendaryActions", 3)
    if data.get("legendaryActionsLair"):
        uses = f"{uses} ({data['legendaryActionsLair']} in its lair)"
    legendary_intro = data.get("legendaryHeader") or (
        [
            f"The {data.get('name', 'creature').lower()} can take {uses} legendary actions."
        ]
        if data.get("legendary")
        else None
    )
    return [
        _title(data),
        kind,
        f"*{_source(data)}*",
        "\n".join(s for s in stats if s),
        _abilities(data),
        "\n".join(d for d in details if d),
        _named_blocks(
            "Traits", [*(data.get("trait") or []), *by_place.get("trait", [])]
        ),
        _named_blocks(
            "Actions", [*(data.get("action") or []), *by_place.get("action", [])]
        ),
        _named_blocks(
            "Bonus Actions", [*(data.get("bonus") or []), *by_place.get("bonus", [])]
        ),
        _named_blocks(
            "Reactions", [*(data.get("reaction") or []), *by_place.get("reaction", [])]
        ),
        _named_blocks("Legendary Actions", data.get("legendary"), legendary_intro),
        _named_blocks("Mythic Actions", data.get("mythic"), data.get("mythicHeader")),
    ]


def _spell(data: Raw, _: str) -> list[str]:
    level = data.get("level", 0)
    school = _SCHOOLS.get(str(data.get("school")), str(data.get("school", "")))
    kind = f"{school} cantrip" if level == 0 else f"Level {level} {school}"
    if (data.get("meta") or {}).get("ritual"):
        kind += " (ritual)"
    classes = [
        c.get("name", "") for c in (data.get("classes") or {}).get("fromClassList", [])
    ]
    return [
        _title(data),
        f"*{kind}* · *{_source(data)}*",
        "\n".join(
            line
            for line in (
                _line("Casting Time", _time(data.get("time"))),
                _line("Range", _range(data.get("range"))),
                _line("Components", _components(data.get("components"))),
                _line("Duration", _duration(data.get("duration"))),
                _line("Classes", ", ".join(classes)),
            )
            if line
        ),
        _entries(data.get("entries")),
        _entries(data.get("entriesHigherLevel")),
    ]


def _time(times: Any) -> str:
    parts = []
    for t in times or []:
        unit = str(t.get("unit", ""))
        unit = {"bonus": "bonus action"}.get(unit, unit)
        number = t.get("number", 1)
        text = f"{number} {unit}{'s' if number != 1 else ''}"
        if t.get("condition"):
            text += f", {strip_tags(t['condition'])}"
        parts.append(text)
    return " or ".join(parts)


def _range(spell_range: Any) -> str:
    if not isinstance(spell_range, dict):
        return ""
    distance = spell_range.get("distance") or {}
    kind, amount = distance.get("type", ""), distance.get("amount")
    fixed = ("self", "touch", "sight", "unlimited")
    if spell_range.get("type") == "special" or (amount is None and kind not in fixed):
        return "Special"
    if spell_range.get("type") == "point":
        if kind in ("self", "touch", "sight", "unlimited"):
            return kind.title()
        return f"{amount} {kind}"
    return f"Self ({amount}-{kind.rstrip('s')} {spell_range.get('type')})"


def _components(components: Any) -> str:
    if not isinstance(components, dict):
        return ""
    parts = [c.upper() for c in ("v", "s") if components.get(c)]
    material = components.get("m")
    if material:
        text = material.get("text") if isinstance(material, dict) else material
        parts.append(f"M ({strip_tags(str(text))})" if isinstance(text, str) else "M")
    return ", ".join(parts)


def _duration(durations: Any) -> str:
    parts = []
    for d in durations or []:
        kind = d.get("type")
        if kind == "instant":
            parts.append("Instantaneous")
        elif kind == "timed":
            length = d.get("duration") or {}
            amount, unit = length.get("amount", 1), length.get("type", "")
            text = f"{amount} {unit}{'s' if amount != 1 else ''}"
            parts.append(
                f"Concentration, up to {text}" if d.get("concentration") else text
            )
        elif kind == "permanent":
            ends = " or ".join(d.get("ends", [])) or "dispelled"
            parts.append(f"Until {ends}")
        else:
            parts.append("Special")
    return " or ".join(parts)


def _item(data: Raw, _: str) -> list[str]:
    kind = item_types.name(str(data["type"])) if data.get("type") else ""
    rarity = data.get("rarity")
    attune = data.get("reqAttune")
    extras = [
        kind,
        str(rarity) if rarity and rarity != "none" else "",
        ("requires attunement " + strip_tags(attune)).strip()
        if isinstance(attune, str)
        else "requires attunement"
        if attune
        else "",
    ]
    damage = ""
    if data.get("dmg1"):
        damage = f"{data['dmg1']} {_DAMAGE.get(str(data.get('dmgType')), '')}".strip()
        if data.get("dmg2"):
            damage += f" (versatile {data['dmg2']})"
    properties = [_property(p) for p in data.get("property", [])]
    value = data.get("value")
    return [
        _title(data),
        f"*{', '.join(e for e in extras if e)}* · *{_source(data)}*",
        "\n".join(
            line
            for line in (
                _line("Damage", damage),
                _line("Range", f"{data['range']} ft." if data.get("range") else ""),
                _line("Properties", ", ".join(properties)),
                _line(
                    "Mastery",
                    ", ".join(_property(m) for m in data.get("mastery", [])),
                ),
                _line("Armor Class", str(data["ac"]) if data.get("ac") else ""),
                _line(
                    "Strength", str(data["strength"]) if data.get("strength") else ""
                ),
                _line("Stealth", "Disadvantage" if data.get("stealth") else ""),
                _line("Weight", f"{data['weight']} lb." if data.get("weight") else ""),
                _line(
                    "Cost",
                    f"{value / 100:g} gp" if isinstance(value, int | float) else "",
                ),
            )
            if line
        ),
        _entries(data.get("entries")),
    ]


def _property(prop: Any) -> str:
    """A property code such as "V|XPHB", or {"uid": "2H|XPHB", "note": "unless mounted"}."""
    uid, note = (
        (prop.get("uid", ""), prop.get("note"))
        if isinstance(prop, dict)
        else (prop, None)
    )
    code = str(uid).split("|")[0]
    name = _PROPERTIES.get(code, code)
    return f"{name} ({note})" if note else name


def _class(data: Raw, _: str) -> list[str]:
    hd = data.get("hd") or {}
    start = data.get("startingProficiencies") or {}
    skills = []
    for choice in start.get("skills", []):
        pick = choice.get("choose") if isinstance(choice, dict) else None
        if pick:
            skills.append(
                f"choose {pick.get('count', 1)} from {', '.join(pick.get('from', []))}"
            )
    features = [
        "## Features",
        "Read one with get_content(content_type='classFeature', name=<uid>).",
    ]
    for feature in data.get("classFeatures", []):
        uid = feature.get("classFeature") if isinstance(feature, dict) else feature
        parts = str(uid).split("|")
        level = parts[3] if len(parts) > 3 else ""
        features.append(f"- Level {level}: {parts[0]} (`{uid}`)")
    subclasses = [
        f"- {s.get('name')} ({s.get('source')})"
        for s in data.get("subclasses", [])
        if isinstance(s, dict)
    ]
    return [
        _title(data),
        f"*{_source(data)}*",
        "\n".join(
            line
            for line in (
                _line("Hit Die", f"d{hd['faces']}" if hd.get("faces") else ""),
                _line(
                    "Saving Throws",
                    ", ".join(
                        _ABILITY_NAMES.get(str(p), str(p))
                        for p in data.get("proficiency", [])
                    ),
                ),
                _line("Armor", _join(start.get("armor", []))),
                _line("Weapons", _join(start.get("weapons", []))),
                _line("Skills", "; ".join(skills)),
            )
            if line
        ),
        "\n".join(features) if data.get("classFeatures") else "",
        "\n".join([f"## {data.get('subclassTitle', 'Subclasses')}", *subclasses])
        if subclasses
        else "",
    ]


def _subclass(data: Raw, _: str) -> list[str]:
    features = [
        "## Features",
        "Read one with get_content(content_type='subclassFeature', name=<uid>).",
    ]
    for feature in data.get("subclassFeatures", []):
        uid = feature.get("subclassFeature") if isinstance(feature, dict) else feature
        parts = str(uid).split("|")
        level = parts[5] if len(parts) > 5 else ""
        features.append(f"- Level {level}: {parts[0]} (`{uid}`)")
    return [
        _title(data),
        f"*{data.get('className', '')} subclass* · *{_source(data)}*",
        "\n".join(features) if data.get("subclassFeatures") else "",
        _entries(data.get("entries")),
    ]


def _generic(data: Raw, content_type: str) -> list[str]:
    kind = content_type
    if data.get("level") and (data.get("className") or data.get("subclassShortName")):
        owner = data.get("subclassShortName") or data.get("className")
        kind = f"Level {data['level']} {owner} feature"
    return [
        _title(data),
        f"*{kind}* · *{_source(data)}*",
        _entries(data.get("entries") or data.get("entry")),
    ]
