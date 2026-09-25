"""5etools' abbreviations in full, ported from ``Parser`` in ``js/parser.js``
and a few ``Renderer`` helpers that only format text."""

from __future__ import annotations

from typing import Any

from .strings import join_conjunct, ordinal

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_NAMES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}
SIZES = {
    "F": "Fine",
    "D": "Diminutive",
    "T": "Tiny",
    "S": "Small",
    "M": "Medium",
    "L": "Large",
    "H": "Huge",
    "G": "Gargantuan",
    "C": "Colossal",
    "V": "Varies",
}
_ALIGNMENTS = {
    "L": "lawful",
    "N": "neutral",
    "NX": "neutral (law/chaos axis)",
    "NY": "neutral (good/evil axis)",
    "C": "chaotic",
    "G": "good",
    "E": "evil",
    "U": "unaligned",
    "A": "any alignment",
}
FEAT_CATEGORIES = {
    "D": "Dragonmark",
    "DG": "Dark Gift",
    "G": "General",
    "O": "Origin",
    "FS": "Fighting Style",
    "FS:P": "Fighting Style Replacement (Paladin)",
    "FS:R": "Fighting Style Replacement (Ranger)",
    "EB": "Epic Boon",
}
OPT_FEATURE_TYPES = {
    "AI": "Artificer Infusion",
    "ED": "Elemental Discipline",
    "EI": "Eldritch Invocation",
    "MM": "Metamagic",
    "MV": "Maneuver",
    "MV:B": "Maneuver, Battle Master",
    "MV:C2-UA": "Maneuver, Cavalier V2 (UA)",
    "AS:V1-UA": "Arcane Shot, V1 (UA)",
    "AS:V2-UA": "Arcane Shot, V2 (UA)",
    "AS": "Arcane Shot",
    "OTH": "Other",
    "FS:F": "Fighting Style; Fighter",
    "FS:B": "Fighting Style; Bard",
    "FS:P": "Fighting Style; Paladin",
    "FS:R": "Fighting Style; Ranger",
    "PB": "Pact Boon",
    "OR": "Onomancy Resonant",
    "RN": "Rune Knight Rune",
    "AF": "Alchemical Formula",
    "TT": "Traveler's Trick",
    "RP": "Renown Perk",
}
TRAP_HAZARD_TYPES = {
    "MECH": "Mechanical Trap",
    "MAG": "Magical Trap",
    "SMPL": "Simple Trap",
    "CMPX": "Complex Trap",
    "HAZ": "Hazard",
    "WTH": "Weather",
    "ENV": "Environmental Hazard",
    "WLD": "Wilderness Hazard",
    "GEN": "Generic",
    "EST": "Eldritch Storm",
    "TRP": "Trap",
    "HAUNT": "Haunted Trap",
}
TRAP_INITIATIVES = {
    1: "initiative count 10",
    2: "initiative count 20",
    3: "initiative count 20 and initiative count 10",
}
VEHICLE_UPGRADE_TYPES = {
    "SHP:H": "Ship Upgrade, Hull",
    "SHP:M": "Ship Upgrade, Movement",
    "SHP:W": "Ship Upgrade, Weapon",
    "SHP:F": "Ship Upgrade, Figurehead",
    "SHP:O": "Ship Upgrade, Miscellaneous",
    "IWM:W": "Infernal War Machine Variant, Weapon",
    "IWM:A": "Infernal War Machine Upgrade, Armor",
    "IWM:G": "Infernal War Machine Upgrade, Gadget",
}
_PACTS = {"Chain", "Tome", "Blade", "Talisman"}
_TIER_LEVELS = {1: (1, 4), 2: (5, 10), 3: (11, 16), 4: (17, 20)}


def alignment_abv_to_full(alignment: Any) -> str:
    """``Parser.alignmentAbvToFull``."""
    if isinstance(alignment, dict):
        if alignment.get("special") is not None:
            return str(alignment["special"])
        chance = f" ({alignment['chance']}%)" if alignment.get("chance") else ""
        note = f" ({alignment['note']})" if alignment.get("note") else ""
        return f"{alignment_list_to_full(alignment.get('alignment'))}{chance}{note}"
    code = str(alignment).upper()
    return _ALIGNMENTS.get(code, code)


def alignment_list_to_full(codes: Any) -> str:
    """``Parser.alignmentListToFull``: ["L", "G"] as "lawful good"."""
    if not codes:
        return ""
    if any(not isinstance(c, str) for c in codes):
        return " or ".join(
            alignment_abv_to_full(c)
            if any(c.get(k) is not None for k in ("special", "chance", "note"))
            else alignment_list_to_full(c.get("alignment"))
            for c in codes
            if "alignment" not in c or c["alignment"] is not None
        )
    if len(codes) == 1:
        return alignment_abv_to_full(codes[0])
    if len(codes) == 2:
        return " ".join(alignment_abv_to_full(c) for c in codes)
    present = set(codes)
    if len(codes) == 3 and {"NX", "NY", "N"} <= present:
        return "any neutral alignment"
    if len(codes) == 5:
        for code, word in (
            ("G", "good"),
            ("E", "evil"),
            ("L", "lawful"),
            ("C", "chaotic"),
        ):
            if code not in present:
                return f"any non-{word} alignment"
    if len(codes) == 4:
        for a, b, word in (
            ("L", "NX", "chaotic"),
            ("G", "NY", "evil"),
            ("C", "NX", "lawful"),
            ("E", "NY", "good"),
        ):
            if a not in present and b not in present:
                return f"any {word} alignment"
    raise ValueError(f"Unmapped alignment: {codes}")


def pact_to_full(pact: str) -> str:
    """``Parser.prereqPactToFull``."""
    return f"Pact of the {pact}" if pact in _PACTS else pact


def tier_to_full_level(tier: Any, *, style: str = "classic") -> str:
    """``Parser.tierToFullLevel``: "1st–4th Level" (classic) or "Levels 1–4"."""
    levels = _TIER_LEVELS.get(int(tier)) if str(tier).isdigit() else None
    if levels is None:
        return f"Tier {tier}"
    if style == "classic":
        return "–".join(ordinal(n) for n in levels) + " Level"
    return f"Levels {levels[0]}–{levels[1]}"


def feat_category(category: str) -> str:
    """A feat's category as ``Renderer.feat.getJoinedCategoryPrerequisites`` names it."""
    full = FEAT_CATEGORIES.get(category, category)
    return full if category in ("FS:P", "FS:R") else f"{full} Feat"


_END_TYPES = {"dispel": "dispelled", "trigger": "triggered", "discharge": "discharged"}


def duration_entry(durations: list[Any], *, style: str = "classic") -> str:
    """``Renderer.generic.getRenderableDurationEntriesMeta``: "Up to 1 minute"."""
    status = "" if style == "classic" else "|XPHB"
    sub_or = False
    parts = []
    for duration in durations:
        condition = f" ({duration['condition']})" if duration.get("condition") else ""
        concentration = duration.get("concentration")
        match duration.get("type"):
            case "special" if concentration:
                parts.append(f"{{@status Concentration{status}}}")
            case "special":
                parts.append(f"Special{condition}")
            case "instant":
                parts.append(f"Instantaneous{condition}")
            case "timed":
                amount = duration["duration"]["amount"]
                unit = duration["duration"]["type"]
                up_to = duration["duration"].get("upTo")
                prefix = (
                    f"{{@status Concentration{status}}}, u"
                    if concentration
                    else "U"
                    if up_to
                    else ""
                )
                prefix += "p to " if concentration or up_to else ""
                parts.append(
                    f"{prefix}{amount} {unit if amount == 1 else unit + 's'}{condition}"
                )
            case "permanent" if duration.get("ends"):
                ends = [_END_TYPES.get(e, str(e)) for e in duration["ends"]]
                sub_or = sub_or or len(ends) > 1
                parts.append(f"Until {join_conjunct(ends, ', ', ' or ')}{condition}")
            case "permanent":
                parts.append(f"Permanent{condition}")
    joined = join_conjunct(parts, "; " if sub_or else ", ", " or ")
    return joined + (" (see below)" if len(durations) > 1 else "")
