"""Collector filters on real SRD entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from studiorum.core.models.spell_filters import SpellFilterCriteria
from studiorum.core.models.spells import Spell
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
