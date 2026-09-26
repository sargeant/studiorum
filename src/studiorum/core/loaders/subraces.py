"""Races as 5etools' races page loads them: "Genasi" and "Air" make "Genasi (Air)".

A port of ``DataUtil.race.getPostProcessedSiteJson`` and
``Renderer.race.mergeSubraces`` with base races (``js/utils.js``,
``js/render.js``), which every 5etools page that looks up a race runs, so a
statblock or tag that names "Genasi (Air)|EEPC" or "Dwarf|PHB" finds a race:

- a race with subraces becomes a base race, which lists its subraces, and one
  race per subrace merged into it. A nameless subrace holds the race's
  defaults: merged, it keeps the race's name, and the base race is renamed
  "Human (Base)".
- a race with a 2014 lineage (MPMM, VRGR) gets the ability scores and
  languages that lineage gives.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from ..logging import get_logger
from ..text.parser import source_abbreviation

logger = get_logger(__name__)

type Raw = dict[str, Any]

# What the base race doesn't pass on to its subraces
_NOT_INHERITED = (
    "subraces",
    "srd",
    "srd52",
    "basicRules",
    "basicRules2024",
    "_versions",
    "hasFluff",
    "hasFluffImages",
    "reprintedAs",
)
_BRACKETS = re.compile(r"^(.*?)(\(.*?\))$")


def subrace_name(race_name: str, subrace_name: str | None) -> str:
    """5etools' name for a merged subrace: "Genasi (Air)", "Elf (Variant; Drow)"."""
    if not subrace_name:
        return race_name
    match = _BRACKETS.match(race_name)
    if not match:
        return f"{race_name} ({subrace_name})"
    return f"{match[1]}({match[2][1:-1]}; {subrace_name})"


def merge(races: list[Raw], subraces: list[Raw]) -> list[Raw]:
    """Every race as 5etools lists it: base races, merged subraces and the rest."""
    attached: dict[tuple[str, str], list[Raw]] = {}
    keys = {
        (str(r.get("name", "")), str(r.get("source", "")))
        for r in races
        if "_copy" not in r
    }
    for subrace in subraces:
        if "_copy" in subrace:
            continue
        key = (str(subrace.get("raceName", "")), str(subrace.get("raceSource", "")))
        if key not in keys:
            logger.debug(f"No race for subrace {subrace.get('name')}")
            continue
        attached.setdefault(key, []).append(subrace)

    out = []
    for race in races:
        if "_copy" in race:
            continue
        race = _with_lineage(race)
        own = attached.get((str(race.get("name", "")), str(race.get("source", ""))))
        if not own:
            out.append(race)
            continue
        own = sorted(
            ({**sr, "source": sr.get("source") or race.get("source")} for sr in own),
            key=lambda sr: (
                str(sr.get("name") or "_").lower(),
                str(sr["source"]).lower(),
            ),
        )
        out.append(_base_race(race, own))
        for subrace in own:
            try:
                out.append(_merged(race, subrace))
            except ValueError as e:
                logger.warning(
                    f"Could not merge subrace {subrace.get('name')} into "
                    f"{race['name']}: {e}"
                )
    return out


_LANGUAGES = {
    "type": "entries",
    "name": "Languages",
    "entries": [
        "You can speak, read, and write Common and one other language that you "
        "and your DM agree is appropriate for your character."
    ],
}
_ALL_ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]
_LINEAGE_ABILITIES = {
    "VRGR": [
        {"choose": {"weighted": {"from": _ALL_ABILITIES, "weights": [2, 1]}}},
        {"choose": {"weighted": {"from": _ALL_ABILITIES, "weights": [1, 1, 1]}}},
    ],
    "UA1": [{"choose": {"weighted": {"from": _ALL_ABILITIES, "weights": [2, 1]}}}],
}


def _with_lineage(race: Raw) -> Raw:
    """What a 2014 lineage gives a race that doesn't say: abilities and languages."""
    lineage = race.get("lineage")
    if not lineage or lineage is True or race.get("edition") not in (None, "classic"):
        return race
    race = copy.deepcopy(race)
    if lineage in _LINEAGE_ABILITIES:
        race["ability"] = race.get("ability") or copy.deepcopy(
            _LINEAGE_ABILITIES[lineage]
        )
    if not race.get("languageProficiencies"):
        race.setdefault("entries", []).append(copy.deepcopy(_LANGUAGES))
        race["languageProficiencies"] = [{"common": True, "anyStandard": 1}]
    return race


def _base_race(race: Raw, own: list[Raw]) -> Raw:
    """``mergeSubraces`` with ``isAddBaseRaces``: the race, listing its subraces."""
    base = copy.deepcopy(race)
    base["_isBaseRace"] = True
    name = str(race["name"])
    if any(not sr.get("name") for sr in own):
        base["_rawName"] = name
        base["name"] = f"{name} (Base)"
    counts: dict[str, int] = {}
    for sr in own:
        key = str(sr.get("name") or "_").lower()
        counts[key] = counts.get(key, 0) + 1
    items = []
    for sr in own:
        full = subrace_name(name, sr.get("name"))
        # 5etools shows the source when two subraces share a name
        shown = (
            f"|{full} ({source_abbreviation(sr['source'])})"
            if counts[str(sr.get("name") or "_").lower()] > 1
            else ""
        )
        items.append(f"{{@race {full}|{sr['source']}{shown}}}")
    listed = {
        "type": "section",
        "entries": [
            "This race has multiple subraces, as listed below:",
            {"type": "list", "items": items},
        ],
    }
    traits = {
        "type": "section",
        "entries": [
            {
                "type": "entries",
                "entries": [
                    {
                        "type": "entries",
                        "name": "Traits",
                        "entries": copy.deepcopy(race.get("entries") or []),
                    }
                ],
            }
        ],
    }
    base["_baseRaceEntries"] = [listed, *([traits] if race.get("entries") else [])]
    base["_subraces"] = [
        {"name": subrace_name(name, sr.get("name")), "source": sr["source"]}
        for sr in own
    ]
    return base


def _merged(race: Raw, subrace: Raw) -> Raw:
    merged = {k: copy.deepcopy(v) for k, v in race.items() if k not in _NOT_INHERITED}
    sub = copy.deepcopy(subrace)
    overwrite = sub.pop("overwrite", None) or {}
    sub.pop("raceName", None)
    sub.pop("raceSource", None)
    sub.setdefault("source", race.get("source"))

    merged["name"] = subrace_name(str(race["name"]), sub.pop("name", None))
    if ability := sub.pop("ability", None):
        if overwrite.get("ability") or not merged.get("ability"):
            merged["ability"] = [{} for _ in ability]
        if len(merged["ability"]) != len(ability):
            raise ValueError("race and subrace ability lists differ in length")
        for mine, theirs in zip(merged["ability"], ability, strict=True):
            mine.update(theirs)
    if entries := sub.pop("entries", None):
        merged_entries = merged.setdefault("entries", [])
        for entry in entries:
            name = _overwrites(entry)
            index = next(
                (
                    i
                    for i, e in enumerate(merged_entries)
                    if name
                    and isinstance(e, dict)
                    and str(e.get("name", "")).lower().strip() == name
                ),
                None,
            )
            if index is None:
                merged_entries.append(entry)
            else:
                merged_entries[index] = entry
    for prop in ("traitTags", "languageProficiencies"):
        if values := sub.pop(prop, None):
            merged[prop] = (
                values if overwrite.get(prop) else [*merged.get(prop, []), *values]
            )
    if skills := sub.pop("skillProficiencies", None):
        merged["skillProficiencies"] = _merged_skills(
            merged.get("skillProficiencies"),
            skills,
            bool(overwrite.get("skillProficiencies")),
        )
    merged.update(sub)
    return {k: v for k, v in merged.items() if v is not None}


def _overwrites(entry: Any) -> str | None:
    """The name of the race entry this subrace entry replaces, if any."""
    if not isinstance(entry, dict):
        return None
    name = (entry.get("data") or {}).get("overwrite")
    return str(name).lower().strip() if name else None


def _merged_skills(mine: Any, theirs: list[Raw], overwrite: bool) -> Any:
    if not mine or overwrite:
        return theirs
    if len(mine) > 1 or len(theirs) > 1:
        raise ValueError("merging skill proficiency choices is not supported")
    return [{**mine[0], **theirs[0]}]
