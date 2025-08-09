"""Tests for ContentResolver on-demand loading functionality."""

from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.adventures import Adventure
from dnd5e.core.models.books import Book
from dnd5e.core.models.content import ContentType, Source
from dnd5e.core.resolvers.content_resolver import ContentResolver, ResolutionStatus

# Tests converted to sync after async removal migration


class TestContentResolverOnDemand:
    """Test ContentResolver on-demand content loading."""

    @pytest.fixture
    def mock_omnidexer(self):
        """Create mock omnidexer."""
        mock_omnidexer = Mock()
        mock_omnidexer.source_manager = Mock()
        return mock_omnidexer

    @pytest.fixture
    def mock_adventure_metadata(self):
        """Mock adventure metadata from omnidexer."""
        adventure = Mock()
        adventure.name = "Test Adventure"
        adventure.id = "TestAdv"
        adventure.source = Mock()
        adventure.source.abbreviation = "TA"
        adventure.model_dump = Mock(
            return_value={
                "name": "Test Adventure",
                "id": "TestAdv",
                "source": "TA",
                "contents": [
                    {"name": "Chapter 1", "headers": ["Scene 1"]},
                    {"name": "Chapter 2", "headers": ["Scene 2"]},
                ],
            }
        )
        return adventure

    @pytest.fixture
    def mock_content_data(self):
        """Mock content data that would be loaded from content file."""
        return {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1",
                    "id": "001",
                    "entries": ["Chapter 1 content"],
                },
                {
                    "type": "section",
                    "name": "Chapter 2",
                    "id": "002",
                    "entries": ["Chapter 2 content"],
                },
            ]
        }

    @pytest.fixture
    def content_resolver(self, mock_omnidexer):
        """Create ContentResolver instance."""
        return ContentResolver(mock_omnidexer)

    def test_resolver_initializes_content_merger(self, mock_omnidexer):
        """Test that ContentResolver initializes ContentMerger."""
        resolver = ContentResolver(mock_omnidexer)
        assert resolver.content_merger is not None
        assert resolver.content_merger.source_manager is mock_omnidexer.source_manager

    def test_enrich_content_non_dual_file_type(self, content_resolver):
        """Test that non-dual-file content types are returned unchanged."""
        spell = Mock()
        spell.name = "Fireball"

        result = content_resolver._enrich_content_if_needed(spell, ContentType("spell"))
        assert result is spell  # Should return the same object

    def test_enrich_content_adventure_no_id(self, content_resolver):
        """Test enrichment when adventure has no ID."""
        adventure = Mock()
        adventure.name = "Test Adventure"
        adventure.id = None

        result = content_resolver._enrich_content_if_needed(
            adventure, ContentType("adventure")
        )
        assert result is adventure  # Should return original if no ID

    @patch("dnd5e.core.resolvers.content_resolver.logger")
    def test_enrich_content_adventure_success(
        self, mock_logger, content_resolver, mock_adventure_metadata, mock_content_data
    ):
        """Test successful adventure enrichment."""
        # Mock the content merger
        content_resolver.content_merger.load_content_file = Mock(
            return_value=mock_content_data
        )
        content_resolver.content_merger.merge_metadata_content = Mock(
            return_value={
                "name": "Test Adventure",
                "id": "TestAdv",
                "source": "TA",
                "contents": [
                    {"name": "Chapter 1", "entries": ["Chapter 1 content"]},
                    {"name": "Chapter 2", "entries": ["Chapter 2 content"]},
                ],
            }
        )

        # Mock the adventure class to have model_validate
        mock_adventure_metadata.model_validate = Mock(
            return_value=Mock(name="Enriched Adventure")
        )
        adventure_class = type(mock_adventure_metadata)
        adventure_class.model_validate = Mock(
            return_value=Mock(name="Enriched Adventure")
        )

        content_resolver._enrich_content_if_needed(
            mock_adventure_metadata, ContentType("adventure")
        )

        # Verify content merger was called
        content_resolver.content_merger.load_content_file.assert_called_once_with(
            ContentType("adventure"), "TestAdv"
        )
        content_resolver.content_merger.merge_metadata_content.assert_called_once()

        # Verify model_validate was called to create enriched content
        adventure_class.model_validate.assert_called_once()

    @patch("dnd5e.core.resolvers.content_resolver.logger")
    def test_enrich_content_merger_failure(
        self, mock_logger, content_resolver, mock_adventure_metadata
    ):
        """Test enrichment when content merger fails."""
        # Mock content merger to raise exception
        content_resolver.content_merger.load_content_file = Mock(
            side_effect=Exception("Content load failed")
        )

        result = content_resolver._enrich_content_if_needed(
            mock_adventure_metadata, ContentType("adventure")
        )

        # Should return original content on failure
        assert result is mock_adventure_metadata
        mock_logger.error.assert_called_once()

    def test_resolve_adventure_with_enrichment(
        self, content_resolver, mock_adventure_metadata, mock_content_data
    ):
        """Test that resolve_adventure enriches the result."""
        # Mock omnidexer to return adventure
        content_resolver.omnidexer.get_all_by_type = Mock(
            return_value=[mock_adventure_metadata]
        )

        # Mock enrichment with proper Adventure instance
        enriched_adventure = Adventure(
            name="Enriched Test Adventure",
            source=Source(abbreviation="ETA", name="Enriched Test Adventure"),
        )
        content_resolver._enrich_content_if_needed = Mock(
            return_value=enriched_adventure
        )

        result = content_resolver.resolve_adventure("ta")

        # Verify resolution was successful
        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is enriched_adventure

        # Verify enrichment was called
        content_resolver._enrich_content_if_needed.assert_called_once_with(
            mock_adventure_metadata, ContentType("adventure")
        )

    def test_resolve_book_with_enrichment(self, content_resolver):
        """Test that resolve_book enriches the result."""
        # Mock book metadata
        book = Mock()
        book.name = "Test Book"
        book.id = "TB"
        book.source = Mock()
        book.source.abbreviation = "tb"

        # Mock omnidexer to return book
        content_resolver.omnidexer.get_all_by_type = Mock(return_value=[book])

        # Mock enrichment with proper Book instance
        enriched_book = Book(
            name="Enriched Test Book",
            source=Source(abbreviation="ETB", name="Enriched Test Book"),
        )
        content_resolver._enrich_content_if_needed = Mock(return_value=enriched_book)

        result = content_resolver.resolve_book("tb")

        # Verify resolution was successful
        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is enriched_book

        # Verify enrichment was called
        content_resolver._enrich_content_if_needed.assert_called_once_with(
            book, ContentType("book")
        )

    def test_resolve_multiple_matches_not_enriched(self, content_resolver):
        """Test that multiple matches are not enriched (returned as-is for user selection)."""
        # Mock multiple adventures with same abbreviation
        adventure1 = Adventure(
            name="Test Adventure 1",
            source=Source(abbreviation="test", name="Test Adventure 1"),
        )
        adventure2 = Adventure(
            name="Test Adventure 2",
            source=Source(abbreviation="test", name="Test Adventure 2"),
        )

        content_resolver.omnidexer.get_all_by_type = Mock(
            return_value=[adventure1, adventure2]
        )
        content_resolver._select_preferred_match = Mock(
            return_value=None
        )  # No preference

        # Mock enrichment (should not be called)
        content_resolver._enrich_content_if_needed = Mock()

        result = content_resolver.resolve_adventure("test")

        # Should return multiple matches without enrichment
        assert result.status == ResolutionStatus.MULTIPLE_MATCHES
        assert len(result.matches) == 2

        # Enrichment should not be called for multiple matches
        content_resolver._enrich_content_if_needed.assert_not_called()

    def test_preferred_match_with_enrichment(self, content_resolver):
        """Test that preferred matches from multiple matches are enriched."""
        # Create two adventures with same abbreviation
        adventure1 = Adventure(
            name="Test Adventure (2014)",
            source=Source(abbreviation="test", name="Test Adventure 2014"),
        )
        adventure2 = Adventure(
            name="Test Adventure",  # Preferred (no year suffix)
            source=Source(abbreviation="test", name="Test Adventure"),
        )

        content_resolver.omnidexer.get_all_by_type = Mock(
            return_value=[adventure1, adventure2]
        )

        # Mock preferred match selection (should prefer adventure2)
        content_resolver._select_preferred_match = Mock(return_value=adventure2)

        # Mock enrichment with proper Adventure instance
        enriched_adventure = Adventure(
            name="Enriched Test Adventure",
            source=Source(abbreviation="ETA", name="Enriched Test Adventure"),
        )
        content_resolver._enrich_content_if_needed = Mock(
            return_value=enriched_adventure
        )

        result = content_resolver.resolve_adventure("test")

        # Should resolve to preferred match and enrich it
        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is enriched_adventure

        # Verify enrichment was called with preferred match
        content_resolver._enrich_content_if_needed.assert_called_once_with(
            adventure2, ContentType("adventure")
        )
