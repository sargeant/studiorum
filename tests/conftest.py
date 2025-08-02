"""Pytest configuration and fixtures."""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from dnd5e.core.config.sources import (  # type: ignore
    ContentConfiguration,
    ContentSource,
    SourceType,
)
from dnd5e.core.indexer.tag_resolver import TagResolver  # type: ignore
from dnd5e.core.loaders.configurable_source_manager import (
    ConfigurableSourceManager,  # type: ignore
)
from dnd5e.core.loaders.omnidexer import Omnidexer  # type: ignore
from dnd5e.core.loaders.source_manager import FileSystemSourceManager  # type: ignore
from dnd5e.core.models.creatures import Creature  # type: ignore
from dnd5e.core.models.spells import Spell  # type: ignore


@pytest.fixture
def event_loop() -> Any:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_spell_data() -> dict[str, Any]:
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
def sample_creature_data() -> dict[str, Any]:
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


# Session-scoped versions for performance optimization
@pytest.fixture(scope="session")
def session_sample_spell_data() -> dict[str, Any]:
    """Sample spell data for testing (session-scoped for performance)."""
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


@pytest.fixture(scope="session")
def session_sample_creature_data() -> dict[str, Any]:
    """Sample creature data for testing (session-scoped for performance)."""
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
def sample_spell(sample_spell_data: Any) -> Spell:
    """Create a sample spell object."""
    return Spell.model_validate(sample_spell_data)


@pytest.fixture
def sample_creature(sample_creature_data: Any) -> Creature:
    """Create a sample creature object."""
    return Creature.model_validate(sample_creature_data)


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with sample files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "spells").mkdir()
    (data_dir / "bestiary").mkdir()

    return data_dir


@pytest.fixture(scope="session")
def session_temp_data_dir(tmp_path_factory: Any) -> Path:
    """Create a session-scoped temporary data directory for performance optimization."""
    tmp_path = tmp_path_factory.mktemp("5e2pdf_session_data")
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "spells").mkdir()
    (data_dir / "bestiary").mkdir()

    return data_dir


@pytest.fixture
async def loaded_omnidexer(
    temp_data_dir: Any, sample_spell_data: Any, sample_creature_data: Any
) -> Omnidexer:
    """Create an omnidexer with loaded test data."""
    import json

    # Create test data files
    spell_file = temp_data_dir / "spells" / "test-spells.json"
    spell_file.write_text(json.dumps({"spell": [sample_spell_data]}))

    creature_file = temp_data_dir / "bestiary" / "test-creatures.json"
    creature_file.write_text(json.dumps({"monster": [sample_creature_data]}))

    # Create source manager pointing to temp directory
    source_manager: Any = FileSystemSourceManager(temp_data_dir.parent)
    source_manager.path_config.data_path = temp_data_dir

    # Create and load omnidexer
    omnidexer = Omnidexer(source_manager)
    await omnidexer.load_all_data()

    return omnidexer


@pytest.fixture(scope="session")
async def session_loaded_omnidexer(
    session_temp_data_dir: Any,
    session_sample_spell_data: Any,
    session_sample_creature_data: Any,
) -> Omnidexer:
    """Create a session-scoped omnidexer with loaded test data for performance optimization."""
    import json

    # Create test data files
    spell_file = session_temp_data_dir / "spells" / "test-spells.json"
    spell_file.write_text(json.dumps({"spell": [session_sample_spell_data]}))

    creature_file = session_temp_data_dir / "bestiary" / "test-creatures.json"
    creature_file.write_text(json.dumps({"monster": [session_sample_creature_data]}))

    # Create source manager pointing to temp directory
    source_manager: Any = FileSystemSourceManager(session_temp_data_dir.parent)
    source_manager.path_config.data_path = session_temp_data_dir

    # Create and load omnidexer
    omnidexer = Omnidexer(source_manager)
    await omnidexer.load_all_data()

    return omnidexer


@pytest.fixture
async def tag_resolver(loaded_omnidexer: Omnidexer) -> TagResolver:
    """Create a tag resolver with loaded data."""
    return TagResolver(loaded_omnidexer)


@pytest.fixture(scope="session")
async def session_tag_resolver(session_loaded_omnidexer: Omnidexer) -> TagResolver:
    """Create a session-scoped tag resolver with loaded data for performance optimization."""
    return TagResolver(session_loaded_omnidexer)


@pytest.fixture
async def test_data_omnidexer() -> Omnidexer:
    """Omnidexer using test-data and srd-data sources."""
    # Use the ConfigurableSourceManager which automatically includes test-data
    source_manager = ConfigurableSourceManager()
    await source_manager.ensure_sources_ready()

    omnidexer = Omnidexer(source_manager)
    await omnidexer.load_all_data()
    return omnidexer


@pytest.fixture
def content_availability(test_data_omnidexer: Omnidexer) -> dict[str, bool]:
    """Check what content types are available for testing."""
    return {
        "adventures": len(test_data_omnidexer.get_all_by_type("adventure")) > 0,
        "books": len(test_data_omnidexer.get_all_by_type("book")) > 0,
        "vehicles": len(test_data_omnidexer.get_all_by_type("vehicle")) > 0,
        "spells": len(test_data_omnidexer.get_all_by_type("spell")) > 0,
        "creatures": len(test_data_omnidexer.get_all_by_type("monster")) > 0,
        "items": len(test_data_omnidexer.get_all_by_type("item")) > 0,
        "classes": len(test_data_omnidexer.get_all_by_type("class")) > 0,
        "backgrounds": len(test_data_omnidexer.get_all_by_type("background")) > 0,
        "races": len(test_data_omnidexer.get_all_by_type("race")) > 0,
        "feats": len(test_data_omnidexer.get_all_by_type("feat")) > 0,
    }


@pytest.fixture
async def test_data_tag_resolver(test_data_omnidexer: Omnidexer) -> TagResolver:
    """Create a tag resolver using test-data sources."""
    return TagResolver(test_data_omnidexer)
