"""
Performance tests for content loading functionality.

This module tests the performance characteristics of the new
dual-file architecture content loading system.
"""

import os
import time

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.resolvers.content_resolver import ContentResolver

# Tests converted to sync after async removal migration


class TestContentLoadingPerformance:
    """Test performance of content loading system."""

    def setup_method(self) -> None:
        """Reset environment before each test for proper isolation."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

    @pytest.mark.slow
    @pytest.mark.requires_data
    @pytest.mark.skipif(
        os.getenv("DND5E_CONFIG_FILE") == "test-config.yaml",
        reason="Performance tests require full 5etools dataset, not test data",
    )
    def test_omnidexer_loading_performance(self):
        """Test that omnidexer loading completes in reasonable time."""
        start_time = time.time()

        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        omnidexer.load_all_data()

        end_time = time.time()
        loading_time = end_time - start_time

        # Omnidexer should load within 30 seconds
        assert loading_time < 30, (
            f"Omnidexer loading took too long: {loading_time:.2f}s"
        )

        # Verify data was loaded
        adventures = omnidexer.get_all_by_type("adventure")
        books = omnidexer.get_all_by_type("book")

        assert len(adventures) > 0, "Should have loaded adventures"
        assert len(books) > 0, "Should have loaded books"

    @pytest.mark.slow
    @pytest.mark.requires_data
    @pytest.mark.skipif(
        os.getenv("DND5E_CONFIG_FILE") == "test-config.yaml",
        reason="Performance tests require full 5etools dataset, not test data",
    )
    def test_content_resolution_performance(self):
        """Test that content resolution is reasonably fast."""
        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        omnidexer.load_all_data()

        # Verify we have sufficient data for meaningful performance testing
        adventures = omnidexer.get_all_by_type("adventure")
        books = omnidexer.get_all_by_type("book")

        print(f"DEBUG: Found {len(adventures)} adventures and {len(books)} books")
        if len(adventures) < 5 or len(books) < 5:
            pytest.skip(
                f"Insufficient data for meaningful performance testing: {len(adventures)} adventures, {len(books)} books"
            )

        resolver = ContentResolver(omnidexer)

        # Use well-known content by source abbreviation (ContentResolver handles these)
        test_adventure = "LMoP"  # Lost Mine of Phandelver
        test_book = "PHB"  # Player's Handbook (2014)

        # Test adventure resolution performance
        start_time = time.time()
        adventure_result = resolver.resolve_adventure(test_adventure)
        end_time = time.time()

        adventure_time = end_time - start_time

        assert adventure_result.is_success, (
            f"Should resolve adventure '{test_adventure}'"
        )
        assert adventure_time < 10, (
            f"Adventure resolution took too long: {adventure_time:.2f}s"
        )

        # Test book resolution performance
        start_time = time.time()
        book_result = resolver.resolve_book(test_book)
        end_time = time.time()

        book_time = end_time - start_time

        assert book_result.is_success, f"Should resolve book '{test_book}'"
        assert book_time < 15, f"Book resolution took too long: {book_time:.2f}s"

    @pytest.mark.requires_data
    @pytest.mark.skipif(
        os.getenv("DND5E_CONFIG_FILE") == "test-config.yaml",
        reason="Performance tests require full 5etools dataset, not test data",
    )
    def test_repeated_resolution_consistency(self):
        """Test that repeated resolutions are consistent."""
        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        omnidexer.load_all_data()

        # Verify we have sufficient data for meaningful performance testing
        adventures = omnidexer.get_all_by_type("adventure")

        if len(adventures) < 5:
            pytest.skip("Insufficient data for meaningful performance testing")

        resolver = ContentResolver(omnidexer)

        # Use well-known content by source abbreviation (ContentResolver handles these)
        test_adventure = "LMoP"  # Lost Mine of Phandelver

        # Resolve the same content twice
        result1 = resolver.resolve_adventure(test_adventure)
        result2 = resolver.resolve_adventure(test_adventure)

        assert result1.is_success and result2.is_success, (
            f"Both resolutions should succeed for '{test_adventure}'"
        )

        # Content should be identical (cached or not)
        assert result1.content.name == result2.content.name, (
            "Content should be identical across repeated resolutions"
        )


if __name__ == "__main__":
    # Simple test runner for performance testing
    import pytest

    # Ensure async tests work properly
    pytest.main([__file__, "-v"])


# Module converted to sync after async removal migration
