"""Collector filters on real SRD entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from studiorum.data.collectors.creature_collector import CreatureCollector
from studiorum.data.collectors.item_collector import ItemCollector
from studiorum.data.collectors.spell_collector import SpellCollector
from studiorum.data.models.creature_filters import CreatureFilterCriteria
from studiorum.data.models.creatures import Creature
from studiorum.data.models.item_filters import ItemFilterCriteria
from studiorum.data.models.items import Item
from studiorum.data.models.spell_filters import SpellFilterCriteria
from studiorum.data.models.spells import Spell

SRD_DATA = Path(__file__).parents[3] / "srd-data"


def _entries(path: Path, key: str, names: set[str]) -> list[dict[str, Any]]:
    return [e for e in json.loads(path.read_text())[key] if e["name"] in names]


def _catalogue(content: list[Any]) -> Mock:
    catalogue = Mock()
    catalogue.get_all_by_type.return_value = content
    return catalogue


def test_ritual_filters_spells() -> None:
    spells = [
        Spell.model_validate(e)
        for e in _entries(
            SRD_DATA / "spells" / "spells-srd.json", "spell", {"Alarm", "Fireball"}
        )
    ]
    collector = SpellCollector(_catalogue(spells))

    rituals = collector.collect_spells(SpellFilterCriteria(ritual=True)).spells
    others = collector.collect_spells(SpellFilterCriteria(ritual=False)).spells

    assert [s.name for s in rituals] == ["Alarm"]
    assert [s.name for s in others] == ["Fireball"]


def test_type_filter_reads_a_type_with_tags() -> None:
    creatures = [
        Creature.model_validate(e)
        for e in _entries(
            SRD_DATA / "bestiary" / "bestiary-srd.json",
            "monster",
            {"Goblin", "Young Red Dragon"},
        )
    ]
    collector = CreatureCollector(_catalogue(creatures))

    criteria = CreatureFilterCriteria(creature_types=["humanoid"])
    found = collector.collect_creatures(criteria).creatures

    assert [c.name for c in found] == ["Goblin"]


def _only_in(entry: dict[str, Any], source: str) -> dict[str, Any]:
    return {**entry, "source": source}


def _named(content: list[Any]) -> Mock:
    catalogue = Mock()
    catalogue.find_all.return_value = content
    catalogue.get_all_by_source.return_value = []
    catalogue.get_all_by_type.return_value = []
    return catalogue


def test_names_outside_the_default_sources_are_found() -> None:
    spell = Spell.model_validate(
        _only_in(
            _entries(SRD_DATA / "spells" / "spells-srd.json", "spell", {"Alarm"})[0],
            "XGE",
        )
    )
    item = Item.model_validate(
        _only_in(
            _entries(SRD_DATA / "items.json", "item", {"Bag of Holding"})[0], "TCE"
        )
    )
    creature = Creature.model_validate(
        _only_in(
            _entries(
                SRD_DATA / "bestiary" / "bestiary-srd.json", "monster", {"Goblin"}
            )[0],
            "MPMM",
        )
    )

    with patch("studiorum.config.get_default_sources", return_value=["xphb"]):
        spells = SpellCollector(_named([spell])).collect_by_names(["Alarm"])
        items = ItemCollector(_named([item])).collect_by_names(["Bag of Holding"])
        creatures = CreatureCollector(_named([creature])).collect_by_names(["Goblin"])

    assert [s.name for s in spells.spells] == ["Alarm"]
    assert [i.name for i in items.items] == ["Bag of Holding"]
    assert [c.name for c in creatures.creatures] == ["Goblin"]


def test_sources_passed_in_still_filter_names() -> None:
    spell = Spell.model_validate(
        _only_in(
            _entries(SRD_DATA / "spells" / "spells-srd.json", "spell", {"Alarm"})[0],
            "XGE",
        )
    )

    result = SpellCollector(_named([spell])).collect_spells(
        SpellFilterCriteria(spell_names=["Alarm"], sources=["XPHB"])
    )

    assert result.spells == []
    assert result.unresolved_names == ["Alarm"]


def _by_source(content: list[Any]) -> Mock:
    catalogue = _named(content)
    catalogue.find.side_effect = lambda _type, name, source=None: next(
        (
            c
            for c in content
            if c.name.lower() == name.lower()
            and c.source.abbreviation.lower() == (source or "").lower()
        ),
        None,
    )
    return catalogue


def test_a_source_given_with_a_name_picks_that_printing() -> None:
    alarm = _entries(SRD_DATA / "spells" / "spells-srd.json", "spell", {"Alarm"})[0]
    spells = [Spell.model_validate(_only_in(alarm, s)) for s in ("PHB", "XPHB")]
    bag = _entries(SRD_DATA / "items.json", "item", {"Bag of Holding"})[0]
    items = [Item.model_validate(_only_in(bag, s)) for s in ("DMG", "XDMG")]

    found_spells = SpellCollector(_by_source(spells)).collect_spells(
        SpellFilterCriteria(spell_names=["Alarm"], spell_source_map={"Alarm": "phb"})
    )
    found_items = ItemCollector(_by_source(items)).collect_items(
        ItemFilterCriteria(
            item_names=["Bag of Holding"], item_source_map={"Bag of Holding": "dmg"}
        )
    )

    assert [s.source.abbreviation for s in found_spells.spells] == ["PHB"]
    assert [i.source.abbreviation for i in found_items.items] == ["DMG"]


def test_a_source_given_with_a_name_that_lacks_it_is_unresolved() -> None:
    alarm = _entries(SRD_DATA / "spells" / "spells-srd.json", "spell", {"Alarm"})[0]
    spell = Spell.model_validate(_only_in(alarm, "XPHB"))

    result = SpellCollector(_by_source([spell])).collect_spells(
        SpellFilterCriteria(spell_names=["Alarm"], spell_source_map={"Alarm": "XGE"})
    )

    assert result.spells == []
    assert result.unresolved_names == ["Alarm"]
