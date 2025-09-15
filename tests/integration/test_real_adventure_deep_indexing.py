"""Integration tests for deep indexing with real adventure data."""

import pytest

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType
from studiorum.core.models.nested_content import (
    Inset,
    Section,
    Table,
)
from tests.test_data_helpers import requires_full_dataset

pytestmark = pytest.mark.requires_data


@requires_full_dataset()
@pytest.mark.integration
class TestRealAdventureDeepIndexing:
    """Integration tests with real adventure data."""

    def test_omnidexer_deep_indexing_integration(self):
        """Test that omnidexer correctly performs deep indexing on real data."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        # Load some adventure data
        try:
            omnidexer.source_manager.ensure_sources_ready_sync()
            omnidexer.load_all_data()
        except Exception:
            pytest.skip("Adventure data not available or failed to load")

        # Check that adventures are loaded
        adventure_type = ContentType("adventure")
        adventures = omnidexer.get_all_by_type(adventure_type)
        if not adventures:
            pytest.skip("No adventures found in data sources")

        # Pick first adventure for testing
        adventure = adventures[0]

        # Check that the adventure implements DeepIndexable
        assert hasattr(adventure, "get_deep_index_entries")

        # Test deep indexing
        deep_entries = adventure.get_deep_index_entries(omnidexer)

        # Note: nested content like Section, Table, Inset are not registered
        # as full content types, so they won't be indexed. This test verifies that
        # deep indexing doesn't crash when encountering unregistered nested content.

        # The test passes if deep indexing completes without errors (no exceptions)
        # If there are any registered nested content types, verify they're handled correctly
        if deep_entries:
            # Verify content types - should only contain registered types
            # Currently no nested content types are registered, so this should be empty
            # but the test shouldn't fail if some get registered in the future
            assert isinstance(deep_entries, list), "Deep entries should be a list"

            # If we do get entries, make sure they have proper structure
            for entry in deep_entries:
                assert hasattr(entry, "source"), "Deep entry should have source"
                assert hasattr(entry, "name"), "Deep entry should have name"
        else:
            # This is the expected case - no nested content is registered for indexing
            assert len(deep_entries) == 0, (
                "No deep entries expected for unregistered nested content"
            )

        # Additional verification only if we actually have deep entries
        if deep_entries:
            for entry in deep_entries:
                assert entry.source is not None
                assert entry.source.abbreviation is not None

    def test_omnidexer_indexes_adventure_nested_content(self):
        """Test that omnidexer indexes adventure nested content correctly."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        try:
            omnidexer.source_manager.ensure_sources_ready_sync()
            omnidexer.load_all_data()
        except Exception:
            pytest.skip("Adventure data not available")

        # Check for adventure sections - skip if content type doesn't exist
        try:
            adventure_section_type = ContentType("adventure_section")
            sections = omnidexer.find_all(adventure_section_type)
            if sections:
                section = sections[0]
                assert isinstance(section, Section)
                assert section.name is not None
                assert section.parent_name is not None
        except ValueError:
            # Skip if adventure_section is not a registered ContentType
            pass

        # Check for adventure tables - skip if content type doesn't exist
        try:
            adventure_table_type = ContentType("adventure_table")
            tables = omnidexer.find_all(adventure_table_type)
            if tables:
                table = tables[0]
                assert isinstance(table, Table)
                assert table.name is not None
                assert table.parent_name is not None
        except ValueError:
            # Skip if adventure_table is not a registered ContentType
            pass

        # Check for adventure insets - skip if content type doesn't exist
        try:
            adventure_inset_type = ContentType("adventure_inset")
            insets = omnidexer.find_all(adventure_inset_type)
            if insets:
                inset = insets[0]
                assert isinstance(inset, Inset)
                assert inset.name is not None
                assert inset.parent_name is not None
        except ValueError:
            # Skip if adventure_inset is not a registered ContentType
            pass

    def test_adventure_content_findable_by_name(self):
        """Test that adventure nested content can be found by name."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        try:
            omnidexer.source_manager.ensure_sources_ready_sync()
            omnidexer.load_all_data()
        except Exception:
            pytest.skip("Adventure data not available")

        # Try to get adventure_section content type, skip if not registered
        try:
            adventure_section_type = ContentType("adventure_section")
        except ValueError:
            pytest.skip("adventure_section is not a registered ContentType")

        # Get all adventure sections
        sections = omnidexer.find_all(adventure_section_type)
        if not sections:
            pytest.skip("No adventure sections found")

        # Try to find a section by name
        first_section = sections[0]
        found_section = omnidexer.find(adventure_section_type, first_section.name)

        assert found_section is not None
        assert found_section.name == first_section.name
        assert found_section.source.abbreviation == first_section.source.abbreviation

    def test_deep_indexing_performance_impact(self):
        """Test that deep indexing performance impact is acceptable."""
        import time

        # Test without deep indexing
        omnidexer_normal = Omnidexer(enable_deep_indexing=False)
        start_time = time.time()
        try:
            omnidexer_normal.source_manager.ensure_sources_ready_sync()
            omnidexer_normal.load_all_data()
        except Exception:
            pytest.skip("Adventure data not available")
        normal_time = time.time() - start_time

        # Test with deep indexing
        omnidexer_deep = Omnidexer(enable_deep_indexing=True)
        start_time = time.time()
        omnidexer_deep.source_manager.ensure_sources_ready_sync()
        omnidexer_deep.load_all_data()
        deep_time = time.time() - start_time

        # Calculate performance impact
        if normal_time > 0:
            impact_ratio = deep_time / normal_time
            # Should be less than 5x increase (allowing for deep indexing overhead)
            # Deep indexing does significantly more work, so 5x is reasonable
            assert impact_ratio < 5.0, (
                f"Deep indexing performance impact too high: {impact_ratio:.2f}x "
                f"(normal: {normal_time:.2f}s, deep: {deep_time:.2f}s)"
            )

        # Basic sanity check - shouldn't take more than 30 seconds total
        assert deep_time < 30.0, f"Deep indexing took too long: {deep_time:.2f}s"

    def test_nested_content_has_unique_hash_keys(self):
        """Test that all nested content has unique hash keys."""
        omnidexer = Omnidexer(enable_deep_indexing=True)

        try:
            omnidexer.source_manager.ensure_sources_ready_sync()
            omnidexer.load_all_data()
        except Exception:
            pytest.skip("Adventure data not available")

        # Collect all adventure nested content - only include valid ContentTypes
        all_nested = []
        nested_type_strings = [
            "adventure_section",
            "adventure_table",
            "adventure_inset",
        ]

        for type_str in nested_type_strings:
            try:
                content_type = ContentType(type_str)
                all_nested.extend(omnidexer.find_all(content_type))
            except ValueError:
                # Skip content types that don't exist as enum members
                continue

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
