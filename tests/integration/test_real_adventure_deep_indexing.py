"""Integration tests for deep indexing with real adventure data."""

import pytest

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.models.nested_content import (
    Inset,
    Section,
    Table,
)


@pytest.mark.integration
class TestRealAdventureDeepIndexing:
    """Integration tests with real adventure data."""

    @pytest.mark.asyncio
    async def test_omnidexer_deep_indexing_integration(self):
        """Test that omnidexer correctly performs deep indexing on real data."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        # Load some adventure data
        try:
            await omnidexer.load_adventures()
        except Exception:
            pytest.skip("Adventure data not available or failed to load")

        # Check that adventures are loaded
        adventure_type = ContentType("adventure")
        adventures = omnidexer.find_all(adventure_type)
        if not adventures:
            pytest.skip("No adventures found in data sources")

        # Pick first adventure for testing
        adventure = adventures[0]

        # Check that the adventure implements DeepIndexable
        assert hasattr(adventure, "get_deep_index_entries")

        # Test deep indexing
        deep_entries = adventure.get_deep_index_entries(omnidexer)

        # Should find some nested content
        assert len(deep_entries) > 0, f"No deep entries found for {adventure.name}"

        # Verify content types
        content_types = {type(entry).__name__ for entry in deep_entries}
        expected_types = {"Section", "Table", "Inset"}

        # Should have at least one type of nested content
        assert len(content_types & expected_types) > 0, (
            f"No expected content types found. Got: {content_types}"
        )

        # Verify all entries have proper source and parent references
        for entry in deep_entries:
            assert entry.source is not None
            assert entry.source.abbreviation is not None
            assert entry.parent_name is not None
            assert adventure.name in entry.parent_name

    @pytest.mark.asyncio
    async def test_omnidexer_indexes_adventure_nested_content(self):
        """Test that omnidexer indexes adventure nested content correctly."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        try:
            await omnidexer.load_adventures()
        except Exception:
            pytest.skip("Adventure data not available")

        # Check for adventure sections
        adventure_section_type = ContentType("adventure_section")
        sections = omnidexer.find_all(adventure_section_type)
        if sections:
            section = sections[0]
            assert isinstance(section, Section)
            assert section.name is not None
            assert section.parent_name is not None

        # Check for adventure tables
        adventure_table_type = ContentType("adventure_table")
        tables = omnidexer.find_all(adventure_table_type)
        if tables:
            table = tables[0]
            assert isinstance(table, Table)
            assert table.name is not None
            assert table.parent_name is not None

        # Check for adventure insets
        adventure_inset_type = ContentType("adventure_inset")
        insets = omnidexer.find_all(adventure_inset_type)
        if insets:
            inset = insets[0]
            assert isinstance(inset, Inset)
            assert inset.name is not None
            assert inset.parent_name is not None

    @pytest.mark.asyncio
    async def test_adventure_content_findable_by_name(self):
        """Test that adventure nested content can be found by name."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        try:
            await omnidexer.load_adventures()
        except Exception:
            pytest.skip("Adventure data not available")

        # Get all adventure sections
        adventure_section_type = ContentType("adventure_section")
        sections = omnidexer.find_all(adventure_section_type)
        if not sections:
            pytest.skip("No adventure sections found")

        # Try to find a section by name
        first_section = sections[0]
        adventure_section_type = ContentType("adventure_section")
        found_section = omnidexer.find(adventure_section_type, first_section.name)

        assert found_section is not None
        assert found_section.name == first_section.name
        assert found_section.source.abbreviation == first_section.source.abbreviation

    @pytest.mark.asyncio
    async def test_deep_indexing_performance_impact(self):
        """Test that deep indexing performance impact is acceptable."""
        import time

        # Test without deep indexing
        omnidexer_normal = Omnidexer(enable_deep_indexing=False)
        start_time = time.time()
        try:
            await omnidexer_normal.load_adventures()
        except Exception:
            pytest.skip("Adventure data not available")
        normal_time = time.time() - start_time

        # Test with deep indexing
        omnidexer_deep = Omnidexer(enable_deep_indexing=True)
        start_time = time.time()
        await omnidexer_deep.load_adventures()
        deep_time = time.time() - start_time

        # Calculate performance impact
        if normal_time > 0:
            impact_ratio = deep_time / normal_time
            # Should be less than 50% increase (1.5x)
            assert impact_ratio < 1.5, (
                f"Deep indexing performance impact too high: {impact_ratio:.2f}x "
                f"(normal: {normal_time:.2f}s, deep: {deep_time:.2f}s)"
            )

        # Basic sanity check - shouldn't take more than 30 seconds total
        assert deep_time < 30.0, f"Deep indexing took too long: {deep_time:.2f}s"

    @pytest.mark.asyncio
    async def test_nested_content_has_unique_hash_keys(self):
        """Test that all nested content has unique hash keys."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        try:
            await omnidexer.load_adventures()
        except Exception:
            pytest.skip("Adventure data not available")

        # Collect all adventure nested content
        all_nested = []
        all_nested.extend(omnidexer.find_all(ContentType.ADVENTURE_SECTION))
        all_nested.extend(omnidexer.find_all(ContentType.ADVENTURE_TABLE))
        all_nested.extend(omnidexer.find_all(ContentType.ADVENTURE_INSET))

        if not all_nested:
            pytest.skip("No adventure nested content found")

        # Check hash keys are unique
        hash_keys = [item.get_hash_key() for item in all_nested]
        unique_keys = set(hash_keys)

        assert len(hash_keys) == len(unique_keys), (
            f"Found duplicate hash keys: {len(hash_keys)} total, {len(unique_keys)} unique"
        )

        # Ensure hash keys contain expected components
        for i, key in enumerate(hash_keys[:5]):  # Check first 5
            assert ":" in key, f"Hash key {i} should contain colons: {key}"
            parts = key.split(":")
            assert len(parts) >= 3, f"Hash key {i} should have at least 3 parts: {key}"
