"""Collector filters on real SRD entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from studiorum.core.models.creature_filters import CreatureFilterCriteria
from studiorum.core.models.creatures import Creature
from studiorum.core.models.spell_filters import SpellFilterCriteria
from studiorum.core.models.spells import Spell
from studiorum.core.services.creature_collector import CreatureCollector
from studiorum.core.services.spell_collector import SpellCollector

SRD_DATA = Path(__file__).parents[3] / "srd-data"


def _entries(path: Path, key: str, names: set[str]) -> list[dict[str, Any]]:
    return [e for e in json.loads(path.read_text())[key] if e["name"] in names]


def _omnidexer(content: list[Any]) -> Mock:
    omnidexer = Mock()
    omnidexer.get_all_by_type.return_value = content
    return omnidexer


def test_ritual_filters_spells() -> None:
    spells = [
        Spell.model_validate(e)
        for e in _entries(
            SRD_DATA / "spells" / "spells-srd.json", "spell", {"Alarm", "Fireball"}
        )
    ]
    collector = SpellCollector(_omnidexer(spells))

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
    collector = CreatureCollector(_omnidexer(creatures))

    criteria = CreatureFilterCriteria(creature_types=["humanoid"])
    found = collector.collect_creatures(criteria).creatures

    assert [c.name for c in found] == ["Goblin"]
