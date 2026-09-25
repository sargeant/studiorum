"""Races merged with their subraces: "Genasi" and "Air" make "Genasi (Air)".

A port of 5etools' ``Renderer.race.adoptSubraces`` and ``_getMergedSubrace``
(``js/render.js``), which the races page runs when it loads, so a statblock or
tag that names "Genasi (Air)|EEPC" finds a race. Nameless subraces hold a
race's defaults and are left out, as the loader leaves them out elsewhere.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from ..logging import get_logger

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
    """Each named subrace merged into its race, as a race of its own."""
    by_key = {
        (str(r.get("name", "")), str(r.get("source", ""))): r
        for r in races
        if "_copy" not in r
    }
    out = []
    for subrace in subraces:
        if not subrace.get("name") or "_copy" in subrace:
            continue
        race = by_key.get(
            (str(subrace.get("raceName", "")), str(subrace.get("raceSource", "")))
        )
        if race is None:
            logger.debug(f"No race for subrace {subrace.get('name')}")
            continue
        try:
            out.append(_merged(race, subrace))
        except ValueError as e:
            logger.warning(
                f"Could not merge subrace {subrace['name']} into {race['name']}: {e}"
            )
    return out


def _merged(race: Raw, subrace: Raw) -> Raw:
    merged = {k: copy.deepcopy(v) for k, v in race.items() if k not in _NOT_INHERITED}
    sub = copy.deepcopy(subrace)
    overwrite = sub.pop("overwrite", None) or {}
    sub.pop("raceName", None)
    sub.pop("raceSource", None)
    sub.setdefault("source", race.get("source"))

    merged["name"] = subrace_name(str(race["name"]), sub.pop("name"))
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
