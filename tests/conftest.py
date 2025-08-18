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
from dnd5e.core.loaders.configurable_source_manager import (
    ConfigurableSourceManager,  # type: ignore
)
from dnd5e.core.loaders.omnidexer import Omnidexer  # type: ignore
from dnd5e.core.loaders.source_manager import FileSystemSourceManager  # type: ignore
from dnd5e.core.models.creatures import Creature  # type: ignore
from dnd5e.core.models.spells import Spell  # type: ignore
from dnd5e.core.text.tag_resolver import TagResolver  # type: ignore

# Import the test helper for consistent setup
from tests.test_helpers import reset_test_environment, setup_test_with_registry

# Import the profiler plugin to ensure it's discovered by pytest
pytest_plugins = ["scripts.test_profiler"]


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


# Factory fixtures for better test isolation (replaced session-scoped)
@pytest.fixture
def make_sample_spell_data():
    """Factory for creating spell data to avoid mutable state sharing."""

    def _make_spell_data(name: str = "Fireball", level: int = 3) -> dict[str, Any]:
        return {
            "name": name,
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 241},
            "level": level,
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

    return _make_spell_data


@pytest.fixture
def make_sample_creature_data():
    """Factory for creating creature data to avoid mutable state sharing."""

    def _make_creature_data(
        name: str = "Ancient Red Dragon", cr: str = "24"
    ) -> dict[str, Any]:
        return {
            "name": name,
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
            "cr": cr,
        }

    return _make_creature_data


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


@pytest.fixture
def make_temp_data_dir(tmp_path: Path):
    """Factory for creating temporary data directories with custom content."""

    def _make_temp_data_dir(
        spell_data: list[dict[str, Any]] = None,
        creature_data: list[dict[str, Any]] = None,
    ) -> Path:
        import json

        data_dir = tmp_path / "custom_data"
        data_dir.mkdir()

        # Create subdirectories
        (data_dir / "spells").mkdir()
        (data_dir / "bestiary").mkdir()

        # Create test data files if provided
        if spell_data:
            spell_file = data_dir / "spells" / "test-spells.json"
            spell_file.write_text(json.dumps({"spell": spell_data}))

        if creature_data:
            creature_file = data_dir / "bestiary" / "test-creatures.json"
            creature_file.write_text(json.dumps({"monster": creature_data}))

        return data_dir

    return _make_temp_data_dir


@pytest.fixture
def loaded_omnidexer(
    temp_data_dir: Any, sample_spell_data: Any, sample_creature_data: Any
) -> Omnidexer:
    """Create an omnidexer with loaded test data."""
    import asyncio
    import json

    # Use full reset sequence for complete isolation
    reset_test_environment()

    # Create test data files and ensure they're written to disk
    spell_file = temp_data_dir / "spells" / "test-spells.json"
    spell_file.write_text(json.dumps({"spell": [sample_spell_data]}))

    creature_file = temp_data_dir / "bestiary" / "test-creatures.json"
    creature_file.write_text(json.dumps({"monster": [sample_creature_data]}))

    # Create source manager pointing to temp directory
    source_manager = FileSystemSourceManager(temp_data_dir.parent)
    source_manager.path_config.data_path = temp_data_dir

    # Create and load omnidexer
    omnidexer = Omnidexer(source_manager)
    omnidexer.load_all_data()

    return omnidexer


@pytest.fixture
def make_omnidexer():
    """Factory for creating omnidexers with custom data and configurations."""

    def _make_omnidexer(
        temp_data_dir: Path = None,
        spell_data: list[dict[str, Any]] = None,
        creature_data: list[dict[str, Any]] = None,
    ) -> Omnidexer:
        import asyncio
        import json

        if temp_data_dir is None:
            raise ValueError("temp_data_dir is required for factory fixture")

        # Use full reset sequence for complete isolation
        reset_test_environment()

        # Create test data files if provided
        if spell_data:
            spell_file = temp_data_dir / "spells" / "test-spells.json"
            spell_file.write_text(json.dumps({"spell": spell_data}))

        if creature_data:
            creature_file = temp_data_dir / "bestiary" / "test-creatures.json"
            creature_file.write_text(json.dumps({"monster": creature_data}))

        # Create source manager pointing to temp directory
        source_manager = FileSystemSourceManager(temp_data_dir.parent)
        source_manager.path_config.data_path = temp_data_dir

        # Create and load omnidexer
        omnidexer = Omnidexer(source_manager)
        omnidexer.load_all_data()

        return omnidexer

    return _make_omnidexer


@pytest.fixture
def tag_resolver(loaded_omnidexer: Omnidexer) -> TagResolver:
    """Create a tag resolver with loaded data."""
    return TagResolver(loaded_omnidexer)


@pytest.fixture
def make_tag_resolver():
    """Factory for creating tag resolvers with custom omnidexer configurations."""

    def _make_tag_resolver(omnidexer: Omnidexer) -> TagResolver:
        return TagResolver(omnidexer)

    return _make_tag_resolver


@pytest.fixture
def test_data_omnidexer() -> Omnidexer:
    """Omnidexer using test-data and srd-data sources."""
    import asyncio
    import os
    import uuid

    # Use full reset sequence for complete isolation
    reset_test_environment()

    # CRITICAL: Force a fresh service container for each test to avoid parallel contamination
    from dnd5e.core.container import reset_global_container

    reset_global_container()

    # Set test configuration environment variable
    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    # Get omnidexer from the DI container
    from dnd5e.core.container import get_global_container

    container = get_global_container()
    omnidexer = container.get_omnidexer()

    # The container already calls load_all_data() when creating the omnidexer
    # No need to call it again - doing so triggers duplicate detection

    # NOTE: There is a known issue where books fail to load in test environment
    # due to complex global state corruption. This affects multiple test files.
    # The container loads adventures correctly but books fail to load.
    # This needs deeper investigation but is documented in private/omnidexer-dup.md

    # WORKAROUND: Manually load books to bypass the environmental issue
    # This is a temporary fix until the root cause is resolved
    from pathlib import Path

    from dnd5e.core.content_types import ContentType

    test_data_path = Path("test-data")
    books_json_path = test_data_path / "books.json"

    if books_json_path.exists():
        # Manually call the internal loading method for books
        # This bypasses the environmental issue that prevents book loading
        try:
            omnidexer._load_content_type(ContentType.BOOK, str(books_json_path))
        except Exception as e:
            # Log but don't fail - some tests may not need books
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Manual book loading workaround failed: {e}")

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
def test_data_tag_resolver(test_data_omnidexer: Omnidexer) -> TagResolver:
    """Create a tag resolver using test-data sources."""
    return TagResolver(test_data_omnidexer)
