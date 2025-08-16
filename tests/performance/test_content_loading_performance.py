"""
Performance tests for content loading functionality.

This module tests the performance characteristics of the new
dual-file architecture content loading system.
"""

import time

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.resolvers.content_resolver import ContentResolver

# Tests converted to sync after async removal migration


class TestContentLoadingPerformance:
    """Test performance of content loading system."""

    @pytest.mark.slow
    @pytest.mark.requires_data
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
    def test_content_resolution_performance(self):
        """Test that content resolution is reasonably fast."""
        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        omnidexer.load_all_data()

        resolver = ContentResolver(omnidexer)

        # Test adventure resolution performance
        start_time = time.time()
        adventure_result = resolver.resolve_adventure("LMoP")  # Lost Mine of Phandelver
        end_time = time.time()

        adventure_time = end_time - start_time

        assert adventure_result.is_success, "Should resolve adventure"
        assert adventure_time < 10, (
            f"Adventure resolution took too long: {adventure_time:.2f}s"
        )

        # Test book resolution performance
        start_time = time.time()
        book_result = resolver.resolve_book("PHB")  # Player's Handbook
        end_time = time.time()

        book_time = end_time - start_time

        assert book_result.is_success, "Should resolve book"
        assert book_time < 15, f"Book resolution took too long: {book_time:.2f}s"

    @pytest.mark.requires_data
    def test_repeated_resolution_consistency(self):
        """Test that repeated resolutions are consistent."""
        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        omnidexer.load_all_data()

        resolver = ContentResolver(omnidexer)

        # Resolve the same content twice
        result1 = resolver.resolve_adventure("LMoP")  # Lost Mine of Phandelver
        result2 = resolver.resolve_adventure("LMoP")

        assert result1.is_success and result2.is_success, (
            "Both resolutions should succeed"
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
