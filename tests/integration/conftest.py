"""Shared fixtures for integration tests."""

import pytest

from studiorum.data.catalogue import Catalogue
from studiorum.data.models.content import ContentType


@pytest.fixture
def book_data():
    """Fixture to provide book data, skipping test if unavailable."""
    catalogue = Catalogue(enable_deep_indexing=True)

    try:
        catalogue.load_all_data()
        books = catalogue.get_all_by_type(ContentType.BOOK)
        if not books:
            pytest.skip("No books found in data sources")
        return books, catalogue
    except Exception as e:
        pytest.skip(f"Book data not available: {e}")


@pytest.fixture
def adventure_data():
    """Fixture to provide adventure data, skipping test if unavailable."""
    catalogue = Catalogue(enable_deep_indexing=True)

    try:
        catalogue.load_all_data()
        adventures = catalogue.get_all_by_type(ContentType.ADVENTURE)
        if not adventures:
            pytest.skip("No adventures found in data sources")
        return adventures, catalogue
    except Exception as e:
        pytest.skip(f"Adventure data not available: {e}")


@pytest.fixture
def full_dataset():
    """Fixture to provide full dataset, skipping test if unavailable."""
    catalogue = Catalogue(enable_deep_indexing=True)

    try:
        stats = catalogue.load_all_data()
        total_loaded = sum(stats.values())
        if total_loaded == 0:
            pytest.skip("No data loaded from sources")
        return catalogue, stats
    except Exception as e:
        pytest.skip(f"Full dataset not available: {e}")


@pytest.fixture
def spell_data():
    """Fixture to provide spell data, skipping test if unavailable."""
    catalogue = Catalogue()

    try:
        catalogue.load_all_data()
        spells = catalogue.get_all_by_type(ContentType.SPELL)
        if not spells:
            pytest.skip("No spells found in data sources")
        return spells, catalogue
    except Exception as e:
        pytest.skip(f"Spell data not available: {e}")


@pytest.fixture
def creature_data():
    """Fixture to provide creature data, skipping test if unavailable."""
    catalogue = Catalogue()

    try:
        catalogue.load_all_data()
        creatures = catalogue.get_all_by_type(ContentType.CREATURE)
        if not creatures:
            pytest.skip("No creatures found in data sources")
        return creatures, catalogue
    except Exception as e:
        pytest.skip(f"Creature data not available: {e}")
