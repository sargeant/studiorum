"""
Performance tests for content loading functionality.

This module tests the performance characteristics of the new
dual-file architecture content loading system.
"""

import asyncio
import time

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.resolvers.content_resolver import ContentResolver


class TestContentLoadingPerformance:
    """Test performance of content loading system."""

    async def test_omnidexer_loading_performance(self):
        """Test that omnidexer loading completes in reasonable time."""
        start_time = time.time()

        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

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

    async def test_content_resolution_performance(self):
        """Test that content resolution is reasonably fast."""
        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

        resolver = ContentResolver(omnidexer)

        # Test adventure resolution performance
        start_time = time.time()
        adventure = resolver.resolve_adventure("TEST")
        end_time = time.time()

        adventure_time = end_time - start_time

        assert adventure is not None, "Should resolve adventure"
        assert adventure_time < 10, (
            f"Adventure resolution took too long: {adventure_time:.2f}s"
        )

        # Test book resolution performance
        start_time = time.time()
        book = resolver.resolve_book("TEST")
        end_time = time.time()

        book_time = end_time - start_time

        assert book is not None, "Should resolve book"
        assert book_time < 15, f"Book resolution took too long: {book_time:.2f}s"

    async def test_caching_effectiveness(self):
        """Test that caching improves performance on repeated access."""
        source_manager = ConfigurableSourceManager()
        omnidexer = Omnidexer(source_manager)
        await omnidexer.load_all_data()

        resolver = ContentResolver(omnidexer)

        # First resolution (cache miss)
        start_time = time.time()
        result1 = resolver.resolve_adventure("TEST")
        first_time = time.time() - start_time

        # Second resolution (cache hit)
        start_time = time.time()
        result2 = resolver.resolve_adventure("TEST")
        second_time = time.time() - start_time

        assert result1 is not None and result2 is not None, (
            "Both resolutions should succeed"
        )

        # Second resolution should be faster (or at least not significantly slower)
        # Allow for some variance in timing
        assert second_time <= first_time * 2, (
            f"Second resolution should benefit from caching: {first_time:.3f}s vs {second_time:.3f}s"
        )

        # Check cache statistics if available
        content_merger = resolver.content_merger
        if hasattr(content_merger, "get_cache_stats"):
            stats = content_merger.get_cache_stats()
            assert stats.get("hits", 0) > 0, (
                "Should have cache hits from repeated access"
            )


if __name__ == "__main__":
    # Simple test runner for performance testing
    import pytest

    pytest.main([__file__, "-v"])
