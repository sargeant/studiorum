"""Shared fixtures for integration tests."""

import pytest

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType


@pytest.fixture
def book_data():
    """Fixture to provide book data, skipping test if unavailable."""
    omnidexer = Omnidexer(enable_deep_indexing=True)

    try:
        omnidexer.load_all_data()
        books = omnidexer.get_all_by_type(ContentType.BOOK)
        if not books:
            pytest.skip("No books found in data sources")
        return books, omnidexer
    except Exception as e:
        pytest.skip(f"Book data not available: {e}")


@pytest.fixture
def adventure_data():
    """Fixture to provide adventure data, skipping test if unavailable."""
    omnidexer = Omnidexer(enable_deep_indexing=True)

    try:
        omnidexer.load_all_data()
        adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
        if not adventures:
            pytest.skip("No adventures found in data sources")
        return adventures, omnidexer
    except Exception as e:
        pytest.skip(f"Adventure data not available: {e}")


@pytest.fixture
def full_dataset():
    """Fixture to provide full dataset, skipping test if unavailable."""
    omnidexer = Omnidexer(enable_deep_indexing=True)

    try:
        stats = omnidexer.load_all_data()
        total_loaded = sum(stats.values())
        if total_loaded == 0:
            pytest.skip("No data loaded from sources")
        return omnidexer, stats
    except Exception as e:
        pytest.skip(f"Full dataset not available: {e}")


@pytest.fixture
def spell_data():
    """Fixture to provide spell data, skipping test if unavailable."""
    omnidexer = Omnidexer()

    try:
        omnidexer.load_all_data()
        spells = omnidexer.get_all_by_type(ContentType.SPELL)
        if not spells:
            pytest.skip("No spells found in data sources")
        return spells, omnidexer
    except Exception as e:
        pytest.skip(f"Spell data not available: {e}")


@pytest.fixture
def creature_data():
    """Fixture to provide creature data, skipping test if unavailable."""
    omnidexer = Omnidexer()

    try:
        omnidexer.load_all_data()
        creatures = omnidexer.get_all_by_type(ContentType.CREATURE)
        if not creatures:
            pytest.skip("No creatures found in data sources")
        return creatures, omnidexer
    except Exception as e:
        pytest.skip(f"Creature data not available: {e}")
