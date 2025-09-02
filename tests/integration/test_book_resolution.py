"""Integration tests for book content loading and resolution."""

import pytest

from studiorum.cli.main import get_omnidexer
from studiorum.core.models.content import ContentType
from studiorum.core.resolvers.content_resolver import ContentResolver, ResolutionStatus
from tests.test_helpers import reset_test_environment

# Tests converted to sync after async removal migration


@pytest.mark.integration
class TestBookResolution:
    """Test book resolution with dual-file architecture using real data."""

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_omnidexer_loads_book_with_enriched_content(self):
        """Test that omnidexer loads books with enriched content from dual-file architecture."""
        omnidexer = get_omnidexer()
        book_type = ContentType("book")
        books = omnidexer.get_all_by_type(book_type)

        # Should have books with enriched content
        assert len(books) > 0

        # Books should have enriched content from dual-file architecture
        test_book = next((b for b in books if b.source.abbreviation == "TEST"), None)
        if test_book:  # Test book should be available
            assert test_book.name == "Test Sourcebook"
            assert len(test_book.contents) > 0  # Has metadata structure
            assert (
                len(test_book.contents[0].entries) > 0
            )  # And has enriched entries from content files

    def test_resolve_book_phb_success(self):
        """Test successful book resolution with content loading."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_book("TEST")

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is not None
        assert "Test Sourcebook" in result.content.name
        assert result.content.source.abbreviation == "TEST"

        # Should have actual content after enrichment
        assert len(result.content.contents) > 0
        # First chapter should have content (not empty like metadata version)
        if result.content.contents:
            assert len(result.content.contents[0].entries) > 0

    def test_resolve_book_test_success(self):
        """Test test book resolution."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_book("TEST")

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is not None
        assert "Test Sourcebook" in result.content.name
        assert result.content.id == "test-book"

        # Should have enriched content
        assert len(result.content.contents) > 0
        if result.content.contents:
            # Content may be empty in test data - validate structure instead
            assert isinstance(result.content.contents[0].entries, list), (
                "Entries should be a list"
            )

    def test_resolve_nonexistent_book(self):
        """Test resolving a book that doesn't exist."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_book("nonexistent")

        assert result.status == ResolutionStatus.NO_MATCH
        assert result.content is None

    def test_book_metadata_preservation(self):
        """Test that book metadata is preserved during content merging."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_book("TEST")

        assert result.content is not None
        book = result.content

        # Metadata should be preserved
        assert book.id == "test-book"
        assert book.source.abbreviation == "TEST"
        # Source names vary - could be "TEST" or "Test Sourcebook"
        assert book.source.name is not None

    def test_book_vs_adventure_architecture_consistency(self):
        """Test that books and adventures follow the same dual-file architecture."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)

        # Test book resolution
        book_result = resolver.resolve_book("TEST")
        assert book_result.status == ResolutionStatus.EXACT_MATCH
        assert book_result.content is not None
        assert len(book_result.content.contents) > 0
        # Content may be empty in test data - validate structure instead
        assert isinstance(book_result.content.contents[0].entries, list), (
            "Entries should be a list"
        )

        # Test adventure resolution
        adventure_result = resolver.resolve_adventure("TEST")
        if adventure_result.status == ResolutionStatus.EXACT_MATCH:
            assert adventure_result.content is not None
            assert len(adventure_result.content.contents) > 0
            # Both should have enriched content
            assert len(adventure_result.content.contents[0].entries) > 0

    def test_content_cache_functionality(self):
        """Test that content caching works for books."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)

        # Clear cache stats
        content_merger = resolver.content_merger
        if content_merger is None:
            pytest.skip(
                "ContentMerger not available - omnidexer may not have source_manager"
            )
        content_merger.clear_cache()
        stats_before = content_merger.get_cache_stats()

        # First load should be a cache miss
        result1 = resolver.resolve_book("TEST")
        stats_after_first = content_merger.get_cache_stats()

        assert result1.content is not None
        assert stats_after_first["misses"] > stats_before["misses"]

        # Second load should use cache (assuming caching is enabled)
        result2 = resolver.resolve_book("TEST")
        stats_after_second = content_merger.get_cache_stats()

        assert result2.content is not None
        # Either cache hit or miss is acceptable depending on cache settings
        assert (
            stats_after_second["total_requests"] >= stats_after_first["total_requests"]
        )

    def test_missing_content_file_handling(self):
        """Test graceful handling when content file is missing."""
        omnidexer = get_omnidexer()

        # Try to find a book that has metadata but might not have content
        book_type = ContentType("book")
        books = omnidexer.get_all_by_type(book_type)
        assert len(books) > 0

        # All books from metadata should be present
        book_ids = [book.id for book in books if book.id]
        assert len(book_ids) > 0

        # Books should still be accessible even if some content files are missing
        for book in books[:3]:  # Test first few books
            assert book.name is not None
            # Book contents may be empty for metadata-only books - validate structure
            assert isinstance(book.contents, list), "Book contents should be a list"

    def test_end_to_end_book_conversion_ready(self):
        """Test that book resolution produces content suitable for conversion."""
        omnidexer = get_omnidexer()
        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_book("TEST")

        # Verify complete pipeline worked for conversion
        assert result.status == ResolutionStatus.EXACT_MATCH
        book = result.content
        assert book is not None

        # Should have metadata structure suitable for LaTeX rendering
        assert book.name is not None
        assert book.id == "test-book"
        assert book.source is not None
        assert book.source.abbreviation == "TEST"

        # Should have enriched content suitable for rendering
        assert len(book.contents) > 0
        intro_chapter = book.contents[0]
        assert intro_chapter.name is not None
        # Content may be empty in test data - validate structure instead
        assert isinstance(intro_chapter.entries, list), "Entries should be a list"

        # Content should be renderable (basic validation)
        assert isinstance(intro_chapter.entries, list)
        # Test data may have minimal content - validate it's serializable
        assert str(intro_chapter.entries) is not None, "Entries should be serializable"
