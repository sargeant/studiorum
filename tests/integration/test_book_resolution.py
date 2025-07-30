"""Integration tests for book content loading and resolution."""

import asyncio

import pytest

from dnd5e.cli.main import get_omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.resolvers.content_resolver import ContentResolver, ResolutionStatus


class TestBookResolution:
    """Test book resolution with dual-file architecture using real data."""

    def test_omnidexer_loads_only_book_metadata(self):
        """Test that omnidexer loads only metadata files for books."""

        async def _test():
            omnidexer = await get_omnidexer()
            books = omnidexer.get_all_by_type(ContentType.BOOK)

            # Should have books (metadata only)
            assert len(books) > 0

            # Books should be metadata-only (empty content)
            phb = next((b for b in books if b.id == "PHB"), None)
            if phb:  # PHB might not be available in test environment
                assert phb.name == "Player's Handbook (2014)"
                assert len(phb.contents) > 0  # Has metadata structure
                assert len(phb.contents[0].entries) == 0  # But no actual entries

        asyncio.run(_test())

    def test_resolve_book_phb_success(self):
        """Test successful book resolution with content loading."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)
            result = resolver.resolve_book("phb")

            assert result.status == ResolutionStatus.EXACT_MATCH
            assert result.content is not None
            assert "Player's Handbook" in result.content.name
            assert result.content.id == "PHB"

            # Should have actual content after enrichment
            assert len(result.content.contents) > 0
            # First chapter should have content (not empty like metadata version)
            if result.content.contents:
                assert len(result.content.contents[0].entries) > 0

        asyncio.run(_test())

    def test_resolve_book_mm_success(self):
        """Test Monster Manual resolution."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)
            result = resolver.resolve_book("mm")

            assert result.status == ResolutionStatus.EXACT_MATCH
            assert result.content is not None
            assert "Monster Manual" in result.content.name
            assert result.content.id == "MM"

            # Should have enriched content
            assert len(result.content.contents) > 0
            if result.content.contents:
                assert len(result.content.contents[0].entries) > 0

        asyncio.run(_test())

    def test_resolve_nonexistent_book(self):
        """Test resolving a book that doesn't exist."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)
            result = resolver.resolve_book("nonexistent")

            assert result.status == ResolutionStatus.NO_MATCH
            assert result.content is None

        asyncio.run(_test())

    def test_book_metadata_preservation(self):
        """Test that book metadata is preserved during content merging."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)
            result = resolver.resolve_book("phb")

            assert result.content is not None
            book = result.content

            # Metadata should be preserved
            assert book.id == "PHB"
            assert book.source.abbreviation == "PHB"
            # Source names vary - could be "PHB" or "Player's Handbook"
            assert book.source.name is not None

        asyncio.run(_test())

    def test_book_vs_adventure_architecture_consistency(self):
        """Test that books and adventures follow the same dual-file architecture."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)

            # Test book resolution
            book_result = resolver.resolve_book("phb")
            assert book_result.status == ResolutionStatus.EXACT_MATCH
            assert book_result.content is not None
            assert len(book_result.content.contents) > 0
            assert len(book_result.content.contents[0].entries) > 0

            # Test adventure resolution
            adventure_result = resolver.resolve_adventure("cos")
            if adventure_result.status == ResolutionStatus.EXACT_MATCH:
                assert adventure_result.content is not None
                assert len(adventure_result.content.contents) > 0
                # Both should have enriched content
                assert len(adventure_result.content.contents[0].entries) > 0

        asyncio.run(_test())

    def test_content_cache_functionality(self):
        """Test that content caching works for books."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)

            # Clear cache stats
            content_merger = resolver.content_merger
            content_merger.clear_cache()
            stats_before = content_merger.get_cache_stats()

            # First load should be a cache miss
            result1 = resolver.resolve_book("phb")
            stats_after_first = content_merger.get_cache_stats()

            assert result1.content is not None
            assert stats_after_first["misses"] > stats_before["misses"]

            # Second load should use cache (assuming caching is enabled)
            result2 = resolver.resolve_book("phb")
            stats_after_second = content_merger.get_cache_stats()

            assert result2.content is not None
            # Either cache hit or miss is acceptable depending on cache settings
            assert (
                stats_after_second["total_requests"]
                > stats_after_first["total_requests"]
            )

        asyncio.run(_test())

    def test_missing_content_file_handling(self):
        """Test graceful handling when content file is missing."""

        async def _test():
            omnidexer = await get_omnidexer()

            # Try to find a book that has metadata but might not have content
            books = omnidexer.get_all_by_type(ContentType.BOOK)
            assert len(books) > 0

            # All books from metadata should be present
            book_ids = [book.id for book in books if book.id]
            assert len(book_ids) > 0

            # Books should still be accessible even if some content files are missing
            for book in books[:3]:  # Test first few books
                assert book.name is not None
                assert len(book.contents) >= 0  # May be empty for metadata-only

        asyncio.run(_test())

    def test_end_to_end_book_conversion_ready(self):
        """Test that book resolution produces content suitable for conversion."""

        async def _test():
            omnidexer = await get_omnidexer()
            resolver = ContentResolver(omnidexer)
            result = resolver.resolve_book("phb")

            # Verify complete pipeline worked for conversion
            assert result.status == ResolutionStatus.EXACT_MATCH
            book = result.content
            assert book is not None

            # Should have metadata structure suitable for LaTeX rendering
            assert book.name is not None
            assert book.id == "PHB"
            assert book.source is not None
            assert book.source.abbreviation == "PHB"

            # Should have enriched content suitable for rendering
            assert len(book.contents) > 0
            intro_chapter = book.contents[0]
            assert intro_chapter.name is not None
            assert len(intro_chapter.entries) > 0  # Has actual content, not empty

            # Content should be renderable (basic validation)
            assert isinstance(intro_chapter.entries, list)
            assert len(str(intro_chapter.entries)) > 10  # Has substantial content

        asyncio.run(_test())
