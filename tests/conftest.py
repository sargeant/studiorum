"""Pytest configuration and fixtures."""

import asyncio
from pathlib import Path
from typing import Any, Dict

import pytest

from src.core.indexer.tag_resolver import TagResolver
from src.core.loaders.omnidexer import Omnidexer
from src.core.loaders.source_manager import FileSystemSourceManager
from src.core.models.creatures import Creature
from src.core.models.spells import Spell


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_spell_data() -> Dict[str, Any]:
    """Sample spell data for testing."""
    return {
        "name": "Fireball",
        "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 241},
        "level": 3,
        "school": "V",
        "time": [{"number": 1, "unit": "action"}],
        "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
        "components": {
            "v": True,
            "s": True,
            "m": "a tiny ball of bat guano and sulfur",
        },
        "duration": [{"type": "instant"}],
        "entries": [
            "A bright streak flashes from your pointing finger to a point you choose within range and then blossoms with a low roar into an explosion of flame."
        ],
    }


@pytest.fixture
def sample_creature_data() -> Dict[str, Any]:
    """Sample creature data for testing."""
    return {
        "name": "Ancient Red Dragon",
        "source": {"abbreviation": "MM", "name": "Monster Manual", "page": 98},
        "size": ["G"],
        "type": "dragon",
        "alignment": ["C", "E"],
        "ac": [{"ac": 22, "from": ["natural armor"]}],
        "hp": {"average": 546, "formula": "28d20 + 252"},
        "speed": {"walk": 40, "climb": 40, "fly": 80},
        "str": 30,
        "dex": 10,
        "con": 29,
        "int": 18,
        "wis": 15,
        "cha": 23,
        "cr": "24",
    }


@pytest.fixture
def sample_spell(sample_spell_data) -> Spell:
    """Create a sample spell object."""
    return Spell.model_validate(sample_spell_data)


@pytest.fixture
def sample_creature(sample_creature_data) -> Creature:
    """Create a sample creature object."""
    return Creature.model_validate(sample_creature_data)


@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Create a temporary data directory with sample files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "spells").mkdir()
    (data_dir / "bestiary").mkdir()

    return data_dir


@pytest.fixture
async def loaded_omnidexer(
    temp_data_dir, sample_spell_data, sample_creature_data
) -> Omnidexer:
    """Create an omnidexer with loaded test data."""
    import json

    # Create test data files
    spell_file = temp_data_dir / "spells" / "test-spells.json"
    spell_file.write_text(json.dumps({"spell": [sample_spell_data]}))

    creature_file = temp_data_dir / "bestiary" / "test-creatures.json"
    creature_file.write_text(json.dumps({"monster": [sample_creature_data]}))

    # Create source manager pointing to temp directory
    source_manager = FileSystemSourceManager(temp_data_dir.parent)
    source_manager.path_config.data_path = temp_data_dir

    # Create and load omnidexer
    omnidexer = Omnidexer(source_manager)
    await omnidexer.load_all_data()

    return omnidexer


@pytest.fixture
async def tag_resolver(loaded_omnidexer) -> TagResolver:
    """Create a tag resolver with loaded data."""
    omnidexer = await loaded_omnidexer
    return TagResolver(omnidexer)
