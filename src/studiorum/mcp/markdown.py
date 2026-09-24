"""5etools entries as Markdown, with tags reduced to their display text.

The tag splitting and display rules follow 5etools' ``Renderer.stripTags``
(``js/render.js``).
"""

from __future__ import annotations

from typing import Any

from studiorum.core.logging import get_logger
from studiorum.core.text.tags import (
    display_part,
    is_tag,
    split_by_pipe,
    split_by_tags,
    split_tag,
)

logger = get_logger(__name__)

_ABILITIES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}
_FIXED = {
    "h": "*Hit:* ",
    "m": "*Miss:* ",
    "hom": "*Hit or Miss:* ",
    "actSaveSuccess": "*Success:*",
    "actSaveSuccessOrFail": "*Failure or Success:*",
    "actTrigger": "*Trigger:*",
    "hitYourSpellAttack": "your spell attack modifier",
    "dcYourSpellSave": "your spell save DC",
    "coinflip": "flip a coin",
}


def strip_tags(text: str) -> str:
    """``The {@creature goblin|MM}`` becomes ``The goblin``, recursively."""
    if "{@" not in text:
        return text
    out = []
    for part in split_by_tags(text):
        if is_tag(part):
            out.append(strip_tags(_display(*split_tag(part))))
        else:
            out.append(part)
    return "".join(out)


def _display(tag: str, args: str) -> str:
    parts = split_by_pipe(args) or [""]
    first, second = parts[0], parts[1] if len(parts) > 1 else ""
    if tag in _FIXED:
        return (
            second
            if tag in ("hitYourSpellAttack", "dcYourSpellSave") and second
            else _FIXED[tag]
        )
    if tag in ("b", "bold"):
        return f"**{first}**"
    if tag in ("i", "italic"):
        return f"*{first}*"
    if tag in ("damage", "dice", "autodice"):
        return second or first.replace(";", "/")
    if tag in ("d20", "hit", "initiative"):
        return second or (f"+{first}" if first.isdigit() else first)
    if tag in ("savingThrow", "skillCheck"):
        return second or first
    if tag == "chance":
        return second or f"{first} percent"
    if tag == "recharge":
        number = first or "6"
        return f"(Recharge {number}{'–6' if number != '6' else ''})"
    if tag == "dc":
        return f"DC {second or first}"
    if tag in ("scaledice", "scaledamage"):
        return parts[3] if len(parts) > 3 else parts[-1]
    if tag == "atk":
        return f"*{_attack(first)}:*"
    if tag == "atkr":
        return f"*{_attack(first)} Roll:*"
    if tag == "actSave":
        return f"*{_ABILITIES.get(first, first)} Saving Throw:*"
    if tag == "actSaveFail":
        return "*Failure:*"
    if tag == "actResponse":
        return "*Response—*" if "d" in first else "*Response:*"
    if tag == "area":
        flags = parts[2] if len(parts) > 2 else ""
        return first if "x" in flags else f"{'A' if 'u' in flags else 'a'}rea {first}"
    return display_part(tag, parts)


def _attack(codes: str) -> str:
    kinds = {"m": "Melee", "r": "Ranged", "g": "Magical", "a": "Area"}
    methods = {"w": "Weapon", "s": "Spell", "p": "Power"}
    names = []
    for group in codes.lower().split(","):
        kind = next((kinds[c] for c in kinds if c in group), "")
        method = next((methods[c] for c in methods if c in group), "")
        names.append(" ".join(n for n in (kind, method) if n))
    return f"{' or '.join(names)} Attack".strip()


def render(entry: Any, depth: int = 1) -> str:
    """One entry as Markdown; a named entry's heading is at ``depth``."""
    if isinstance(entry, str):
        return strip_tags(entry)
    if isinstance(entry, list):
        return _join(render(e, depth) for e in entry)
    if not isinstance(entry, dict):
        return str(entry)
    kind = entry.get("type", "entries")
    name = strip_tags(str(entry.get("name", "")))
    match kind:
        case "inset" | "insetReadaloud":
            body = _join([f"**{name}**" if name else "", _children(entry, depth + 1)])
            return _quote(body)
        case "quote":
            by = entry.get("by")
            return _quote(
                _join([_children(entry, depth), f"— {strip_tags(by)}" if by else ""])
            )
        case "list":
            return "\n".join(_item(item, depth) for item in entry.get("items", []))
        case "table":
            return _table(entry)
        case "tableGroup":
            return _join(_table(t) for t in entry.get("tables", []))
        case "image":
            title = (entry.get("title") or "").strip()
            label = "Map" if entry.get("imageType") == "map" else "Image"
            return f"*[{label}: {strip_tags(title)}]*" if title else ""
        case "gallery":
            return _join(render(i, depth) for i in entry.get("images", []))
        case "statblock":
            source = entry.get("source", "")
            if str(entry.get("prop", "")).endswith("Fluff"):
                return f"*[Lore: {name} ({source})]*"
            what = entry.get("tag", "creature")
            return f"*[{what.title()} statblock: {name} ({source})]*"
        case "hr":
            return "---"
        case "wrapper":
            return render(entry.get("wrapped"), depth)
        case "inline" | "inlineBlock":
            return "".join(render(e, depth) for e in entry.get("entries", []))
        case "link":
            return strip_tags(str(entry.get("text", "")))
        case "abilityDc" | "abilityAttackMod":
            attrs = _abilities(entry)
            if kind == "abilityDc":
                return f"**{name} save DC** = 8 + your proficiency bonus + your {attrs} modifier"
            return f"**{name} attack modifier** = your proficiency bonus + your {attrs} modifier"
        case "abilityGeneric":
            attrs = _abilities(entry)
            return f"**{name}** = {strip_tags(entry.get('text', ''))} {attrs}".strip()
    heading = f"{'#' * min(depth, 6)} {name}" if name else ""
    return _join([heading, _children(entry, depth + 1 if name else depth)])


def _abilities(entry: dict[str, Any]) -> str:
    return " or ".join(_ABILITIES.get(a, str(a)) for a in entry.get("attributes", []))


def _children(entry: dict[str, Any], depth: int) -> str:
    parts = [render(e, depth) for e in entry.get("entries", [])]
    if "entry" in entry:
        parts.append(render(entry["entry"], depth))
    if not parts and "items" in entry:
        parts.append(render({"type": "list", "items": entry["items"]}, depth))
    return _join(parts)


def _item(item: Any, depth: int, indent: str = "") -> str:
    if isinstance(item, dict) and item.get("type") == "list":
        return "\n".join(_item(i, depth, indent + "  ") for i in item.get("items", []))
    if isinstance(item, dict) and item.get("type") in ("item", "itemSub", "itemSpell"):
        name = strip_tags(str(item.get("name", "")))
        body = _inline(_children(item, depth))
        text = f"**{name}** {body}".strip() if name else body
    else:
        text = _inline(render(item, depth))
    return f"{indent}- {text}"


def _table(table: dict[str, Any]) -> str:
    rows = [[_cell(c) for c in row] for row in _rows(table)]
    labels = [_inline(strip_tags(str(c))) for c in table.get("colLabels", [])]
    width = max([len(labels), *(len(r) for r in rows)], default=0)
    if not width:
        return ""
    labels += [""] * (width - len(labels))
    lines = [
        "| " + " | ".join(labels) + " |",
        "|" + "---|" * width,
        *("| " + " | ".join(r + [""] * (width - len(r))) + " |" for r in rows),
    ]
    caption = table.get("caption")
    return _join([f"**{strip_tags(caption)}**" if caption else "", "\n".join(lines)])


def _rows(table: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for row in table.get("rows", []):
        if isinstance(row, dict):
            row = row.get("row", [])
        if isinstance(row, list):
            rows.append(row)
    return rows


def _cell(cell: Any) -> str:
    if isinstance(cell, dict) and cell.get("type") == "cell":
        roll = cell.get("roll") or {}
        if "exact" in roll:
            return str(roll["exact"])
        if "min" in roll:
            return f"{roll['min']}–{roll.get('max', '')}"
        return _inline(render(cell.get("entry", ""), 6))
    return _inline(render(cell, 6))


def _inline(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _quote(text: str) -> str:
    return "\n".join(f"> {line}".rstrip() for line in text.splitlines())


def _join(parts: Any) -> str:
    return "\n\n".join(p for p in parts if p)


# Tags that name content get_content can read, with 5etools' default source
_CONTENT_TAGS = {
    "action": ("action", "PHB"),
    "background": ("background", "PHB"),
    "class": ("class", "PHB"),
    "condition": ("condition", "PHB"),
    "creature": ("creature", "MM"),
    "disease": ("disease", "DMG"),
    "feat": ("feat", "PHB"),
    "hazard": ("hazard", "DMG"),
    "item": ("item", "DMG"),
    "optfeature": ("optionalfeature", "PHB"),
    "race": ("race", "PHB"),
    "sense": ("sense", "PHB"),
    "spell": ("spell", "PHB"),
    "status": ("status", "PHB"),
    "trap": ("trap", "DMG"),
    "variantrule": ("variantrule", "DMG"),
    "vehicle": ("vehicle", "GoS"),
}
_FEATURE_TAGS = {"classFeature": 5, "subclassFeature": 7}


def references(value: Any) -> list[dict[str, str]]:
    """What tags and statblocks in some 5etools data point to, first mention first.

    Content comes as ``{"type", "name", "source"}``, for get_content; an
    ``{@area}`` link as ``{"type": "section", "name", "section_id"}``.
    """
    found: dict[tuple[str, ...], dict[str, str]] = {}

    def add(ref: dict[str, str]) -> None:
        key = tuple(v.lower() for v in ref.values())
        found.setdefault(key, ref)

    def text(s: str) -> None:
        for part in split_by_tags(s):
            if not is_tag(part):
                continue
            tag, args = split_tag(part)
            parts = split_by_pipe(args) or [""]
            if tag in _CONTENT_TAGS and parts[0]:
                kind, default = _CONTENT_TAGS[tag]
                source = parts[1] if len(parts) > 1 and parts[1] else default
                add({"type": kind, "name": strip_tags(parts[0]), "source": source})
            elif tag in _FEATURE_TAGS and parts[0]:
                uid = "|".join(parts[: _FEATURE_TAGS[tag]])
                add({"type": tag, "name": uid})
            elif tag in ("adventure", "book") and len(parts) > 1 and parts[1]:
                add(
                    {
                        "type": "publication",
                        "name": strip_tags(parts[0]),
                        "publication": parts[1],
                    }
                )
            elif tag == "area" and len(parts) > 1 and parts[1]:
                add(
                    {
                        "type": "section",
                        "name": strip_tags(parts[0]),
                        "section_id": parts[1],
                    }
                )
            # Nested tags, such as a creature inside a display text
            for inner in parts:
                if "{@" in inner:
                    text(inner)

    def walk(v: Any) -> None:
        if isinstance(v, str):
            text(v)
        elif isinstance(v, list):
            for item in v:
                walk(item)
        elif isinstance(v, dict):
            if v.get("type") == "statblock" and v.get("name"):
                kind = {"creature": "creature", "item": "item", "spell": "spell"}.get(
                    str(v.get("tag", "creature")), str(v.get("tag", "creature"))
                )
                add(
                    {
                        "type": kind,
                        "name": str(v["name"]),
                        "source": str(v.get("source", "")),
                    }
                )
            # 5etools lists what a creature carries or an item casts by uid
            for key, kind in (("attachedItems", "item"), ("attachedSpells", "spell")):
                for uid in _uids(v.get(key)):
                    name, _, source = uid.partition("|")
                    add(
                        {
                            "type": kind,
                            "name": name,
                            "source": source.split("|")[0]
                            or ("DMG" if kind == "item" else "PHB"),
                        }
                    )
            for item in v.values():
                walk(item)

    walk(value)
    return list(found.values())


def _uids(value: Any) -> list[str]:
    """Uids in a list, or in a dict of lists (attachedSpells by frequency)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [u for v in value for u in _uids(v)]
    if isinstance(value, dict):
        return [u for v in value.values() for u in _uids(v)]
    return []


def snippet(text: str, words: list[str], size: int = 240) -> str:
    """The text around the first of the words, flattened to one line."""
    flat = " ".join(w for w in text.split() if w.strip("#"))
    at = min((i for w in words if (i := flat.lower().find(w)) >= 0), default=0)
    start = max(0, at - size // 3)
    piece = flat[start : start + size]
    return ("…" if start else "") + piece + ("…" if start + size < len(flat) else "")
