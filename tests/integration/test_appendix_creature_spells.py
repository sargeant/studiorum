"""AppendixGenerator looks each tracked name up once."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from studiorum.data.catalogue import Catalogue
from studiorum.data.references.content_tracker import ContentTracker
from studiorum.render.appendices import AppendixFlags, AppendixGenerator


def _catalogue(*entries: tuple[str, str, str]) -> Any:
    """A catalogue holding (type, name, source) entries."""
    items = {
        (kind, name.lower(), source.lower()): SimpleNamespace(name=name, source=source)
        for kind, name, source in entries
    }
    catalogue = MagicMock(spec=Catalogue)
    catalogue.find.side_effect = lambda ct, name, source=None: items.get(
        (ct.value, name.lower(), (source or "").lower())
    )
    catalogue.find_all.side_effect = lambda ct, name: [
        item
        for (kind, n, _), item in items.items()
        if kind == ct.value and n == name.lower()
    ]
    return catalogue


def _generate(catalogue: Any, *refs: tuple[str, str, str], **flags: bool) -> Any:
    tracker = ContentTracker()
    for kind, name, source in refs:
        tracker.add_content(kind, name, source)
    return AppendixGenerator(catalogue).generate_appendices(
        tracker, AppendixFlags(**flags)
    )


def test_a_name_appears_once_from_the_source_its_reference_gave() -> None:
    catalogue = _catalogue(("spell", "Shield", "PHB"), ("spell", "Shield", "XPHB"))

    [appendix] = _generate(
        catalogue, ("spell", "Shield", ""), ("spell", "Shield", "XPHB"), spells=True
    )

    assert [(s.name, s.source) for s in appendix.items] == [("Shield", "XPHB")]


def test_a_reference_without_a_source_uses_5etools_default() -> None:
    catalogue = _catalogue(("spell", "Shield", "PHB"), ("spell", "Shield", "XPHB"))

    [appendix] = _generate(catalogue, ("spell", "Shield", ""), spells=True)

    assert [s.source for s in appendix.items] == ["PHB"]


def test_a_name_not_in_the_default_source_is_found_by_name() -> None:
    catalogue = _catalogue(("creature", "Frost Giant", "XMM"))

    [appendix] = _generate(catalogue, ("creature", "Frost Giant", ""), creatures=True)

    assert [c.source for c in appendix.items] == ["XMM"]


def test_appendices_come_creatures_items_spells_each_sorted() -> None:
    catalogue = _catalogue(
        ("spell", "Web", "PHB"),
        ("spell", "Blink", "PHB"),
        ("creature", "Goblin", "MM"),
        ("item", "Rope", "DMG"),
    )

    appendices = _generate(
        catalogue,
        ("spell", "Web", ""),
        ("spell", "Blink", ""),
        ("item", "Rope", ""),
        ("creature", "Goblin", ""),
        ("creature", "Nobody", ""),
        spells=True,
        items=True,
        creatures=True,
    )

    assert [(a.title, [i.name for i in a.items]) for a in appendices] == [
        ("Creatures", ["Goblin"]),
        ("Magic Items", ["Rope"]),
        ("Spells", ["Blink", "Web"]),
    ]
    assert [a.label for a in appendices] == [
        "ch:appendix-creatures",
        "ch:appendix-items",
        "ch:appendix-spells",
    ]
