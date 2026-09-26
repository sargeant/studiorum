"""Content as the entries 5etools' compact renderer shows for it.

A statblock in a book or adventure embeds content that may have no
``entries`` of its own (a table, a recipe, a subclass). 5etools renders these
with each type's ``getCompactRenderedString`` (``js/render.js``); the
functions here build the same thing as 5etools entries, which the entry
renderer then turns into LaTeX. Anything else is its ``entries``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .class_entries import class_entries, subclass_entries
from .models.backgrounds import Background
from .models.classes import Class
from .models.deities import Deity
from .models.facilities import Facility
from .models.feats import Feat
from .models.languages import Language
from .models.objects import Object
from .models.optional_features import OptionalFeature
from .models.races import Race
from .models.recipes import Recipe
from .models.rule_types import Hazard
from .models.subclasses import Subclass
from .models.table import Table, TableGroup
from .models.traps import Trap
from .models.vehicles import VehicleUpgrade
from .text.properties import apply_properties
from .type_lines import (
    background_entries,
    deity_entries,
    deity_heading,
    facility_entries,
    feat_entries,
    hazard_entries,
    language_entries,
    object_entries,
    optional_feature_entries,
    race_entries,
    trap_entries,
    vehicle_upgrade_entries,
)

if TYPE_CHECKING:
    from .loaders.omnidexer import Omnidexer
    from .models.content import BaseContent

type Raw = dict[str, Any]

# Props a table carries over to its table entry
_TABLE_PROPS = (
    "caption",
    "colLabels",
    "colLabelRows",
    "colStyles",
    "rows",
    "footnotes",
    "isStriped",
)


def compact_entries(content: BaseContent, omnidexer: Omnidexer | None) -> list[Any]:
    """The entries to render for ``content`` in place of a statblock."""
    for kind, build in _BUILDERS:
        if isinstance(content, kind):
            return build(content, omnidexer)
    return list(content.model_dump().get("entries") or [])


def compact_heading(content: BaseContent, name: str) -> str:
    """The statblock's heading: its name, and for a deity its title."""
    return deity_heading(content, name) if isinstance(content, Deity) else name


def _table(table: Table, _: Omnidexer | None) -> list[Any]:
    data = table.model_dump(by_alias=True, exclude_none=True)
    return [*(table.intro or []), _table_entry(data, table.name), *(table.outro or [])]


def _table_group(group: TableGroup, _: Omnidexer | None) -> list[Any]:
    return [_table_entry(t, group.name) for t in group.tables]


def _table_entry(data: Raw, name: str) -> Raw:
    """A table entry; a caption that repeats the statblock's name is left out."""
    entry = {"type": "table", **{k: data[k] for k in _TABLE_PROPS if k in data}}
    if entry.get("caption") == name:
        del entry["caption"]
    return entry


def _recipe(recipe: Recipe, _: Omnidexer | None) -> list[Any]:
    """Recipe.getBodyHtml: servings, ingredients and equipment, notes, instructions."""
    data = recipe.model_dump(by_alias=True, exclude_none=True)
    out: list[Any] = []
    if makes := data.get("makes"):
        out.append(f"{{@b Makes}} {makes}")
    if serves := data.get("serves"):
        count = serves.get("min", serves.get("exact"))
        upper = f" to {serves['max']}" if "min" in serves and "max" in serves else ""
        note = f" {serves['note']}" if serves.get("note") else ""
        out.append(f"{{@b Serves}} {count}{upper}{note}")
    for name, prop in (("Ingredients", "ingredients"), ("Equipment", "equipment")):
        if items := data.get(prop):
            out.append(
                {
                    "type": "inset",
                    "name": name,
                    "entries": _listed(apply_properties(items)),
                }
            )
    out += data.get("instructions", [])
    if notes := data.get("noteCook"):
        italic = [f"{{@i {n}}}" if isinstance(n, str) else n for n in notes]
        out.append({"type": "entries", "name": "Cook's Notes", "entries": italic})
    return out


def _listed(items: list[Any]) -> list[Any]:
    """Each run of ingredients as a list; named groups keep their names."""
    out: list[Any] = []
    for item in items:
        if isinstance(item, dict) and item.get("type") == "entries":
            out.append({**item, "entries": _listed(item.get("entries", []))})
        elif out and isinstance(out[-1], dict) and out[-1].get("type") == "list":
            out[-1]["items"].append(item)
        else:
            out.append({"type": "list", "items": [item]})
    return out


_BUILDERS: tuple[
    tuple[type[Any], Callable[[Any, Omnidexer | None], list[Any]]], ...
] = (
    (Table, _table),
    (TableGroup, _table_group),
    (Recipe, _recipe),
    (Class, class_entries),
    (Subclass, subclass_entries),
    (Trap, trap_entries),
    (Hazard, hazard_entries),
    (Feat, feat_entries),
    (Deity, deity_entries),
    (OptionalFeature, optional_feature_entries),
    (Facility, facility_entries),
    (Object, object_entries),
    (Race, race_entries),
    (Background, background_entries),
    (VehicleUpgrade, vehicle_upgrade_entries),
    (Language, language_entries),
)
