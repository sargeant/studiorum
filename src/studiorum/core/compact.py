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

from .models.table import Table, TableGroup

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


_BUILDERS: tuple[
    tuple[type[Any], Callable[[Any, Omnidexer | None], list[Any]]], ...
] = (
    (Table, _table),
    (TableGroup, _table_group),
)
