"""Typed entries accept the shapes 5etools ships."""

from __future__ import annotations

from typing import Any

import pytest

from studiorum.core.models.entry_types import (
    EntriesEntry,
    ItemEntry,
    QuoteEntry,
    TableEntry,
    create_entry,
)

# Each taken from 5etools data, trimmed
REAL_ENTRIES: list[dict[str, Any]] = [
    # races.json: a subrace trait that replaces its race's
    {
        "type": "entries",
        "name": "Age",
        "entries": ["Humans reach adulthood in their late teens."],
        "data": {"overwrite": "Age"},
    },
    # items.json: Wand of Wonder's generated table
    {
        "type": "table",
        "caption": "Wand of Wonder Effects",
        "colLabels": ["d100", "Effect"],
        "rows": [["01-05", "You cast {@spell slow}."]],
        "page": 212,
        "srd52": True,
        "basicRules2024": True,
        "data": {"genTables": {"tableName": "Wand of Wonder Effects"}},
    },
    # renderdemo.json: a styled row object
    {
        "type": "table",
        "rows": [{"type": "row", "style": "row-indent-first", "row": ["a"]}],
    },
    {"type": "list", "page": 102, "start": 3, "items": ["one"]},
    {"type": "options", "style": "list-hang-notitle", "entries": []},
    {"type": "quote", "entries": [{"type": "list", "items": ["x"]}], "from": "Volo"},
    {"type": "item", "name": "Dexterity.", "entry": "You gain...", "nameDot": False},
    # legendarygroups.json: an item with no name
    {"type": "item", "entries": ["Thickets form labyrinthine passages."]},
    {"type": "variant", "name": "Variant", "entries": [], "_version": {"name": "x"}},
]


@pytest.mark.parametrize("data", REAL_ENTRIES, ids=lambda d: d["type"])
def test_real_entries_validate(data: dict[str, Any]) -> None:
    create_entry(data)


def test_fields_keep_their_values() -> None:
    table = create_entry(REAL_ENTRIES[1])
    assert isinstance(table, TableEntry)
    assert table.data == {"genTables": {"tableName": "Wand of Wonder Effects"}}
    assert table.srd52 is True

    age = create_entry(REAL_ENTRIES[0])
    assert isinstance(age, EntriesEntry)
    assert age.data == {"overwrite": "Age"}

    assert isinstance(quote := create_entry(REAL_ENTRIES[5]), QuoteEntry)
    assert quote.from_ == "Volo"
    assert isinstance(item := create_entry(REAL_ENTRIES[6]), ItemEntry)
    assert item.entry == "You gain..."


def test_unknown_props_are_still_rejected() -> None:
    with pytest.raises(ValueError, match="Extra inputs"):
        create_entry({"type": "entries", "entries": [], "colour": "red"})
