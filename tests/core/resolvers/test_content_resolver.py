"""Tests for ContentResolver."""

from unittest.mock import Mock

import pytest

from dnd5e.core.models.adventures import Adventure
from dnd5e.core.models.books import Book
from dnd5e.core.models.content import ContentType, Source
from dnd5e.core.resolvers.content_resolver import (
    ContentResolutionResult,
    ContentResolver,
    ResolutionStatus,
)

# Async tests are marked per-class as needed


class TestContentResolutionResult:
    """Test ContentResolutionResult dataclass."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        result = ContentResolutionResult(status=ResolutionStatus.EXACT_MATCH)

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is None
        assert result.matches == []
        assert result.suggestions == []
        assert result.query == ""

    def test_init_with_values(self) -> None:
        """Test initialization with provided values."""
        content = Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST", name="Test Source"),
        )
        matches = [
            Adventure(
                name="Match 1", source=Source(abbreviation="M1", name="Match 1 Source")
            ),
            Adventure(
                name="Match 2", source=Source(abbreviation="M2", name="Match 2 Source")
            ),
        ]
        suggestions = ["cos", "lmop"]

        result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES,
            content=content,
            matches=matches,
            suggestions=suggestions,
            query="test",
        )

        assert result.status == ResolutionStatus.MULTIPLE_MATCHES
        assert result.content == content
        assert result.matches == matches
        assert result.suggestions == suggestions
        assert result.query == "test"

    def test_is_success_property(self) -> None:
        """Test is_success property."""
        exact_result = ContentResolutionResult(status=ResolutionStatus.EXACT_MATCH)
        fuzzy_result = ContentResolutionResult(status=ResolutionStatus.FUZZY_MATCH)
        no_match_result = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)

        assert exact_result.is_success is True
        assert fuzzy_result.is_success is False
        assert no_match_result.is_success is False

    def test_needs_user_selection_property(self) -> None:
        """Test needs_user_selection property."""
        multiple_result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES
        )
        exact_result = ContentResolutionResult(status=ResolutionStatus.EXACT_MATCH)

        assert multiple_result.needs_user_selection is True
        assert exact_result.needs_user_selection is False

    def test_has_suggestions_property(self) -> None:
        """Test has_suggestions property."""
        with_suggestions = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=["cos", "lmop"]
        )
        without_suggestions = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)

        assert with_suggestions.has_suggestions is True
        assert without_suggestions.has_suggestions is False


@pytest.mark.asyncio
class TestContentResolver:
    """Test ContentResolver."""

    @pytest.fixture
    def mock_omnidexer(self) -> Mock:
        """Create mock omnidexer."""
        omnidexer = Mock()
        omnidexer.get_all_by_type.return_value = []
        omnidexer.search.return_value = []
        return omnidexer

    @pytest.fixture
    def resolver(self, mock_omnidexer: Mock) -> ContentResolver:
        """Create ContentResolver with mock omnidexer."""
        return ContentResolver(mock_omnidexer)

    @pytest.fixture
    def sample_adventure(self) -> Adventure:
        """Create sample adventure content."""
        source = Source(abbreviation="COS", name="Curse of Strahd")
        return Adventure(
            name="Curse of Strahd",
            source=source,
            contents=[],
            id="cos",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

    @pytest.fixture
    def sample_book(self) -> Book:
        """Create sample book content."""
        source = Source(abbreviation="PHB", name="Player's Handbook")
        return Book(
            name="Player's Handbook",
            source=source,
            contents=[],
            id="phb",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

    def test_init(self, mock_omnidexer) -> None:
        """Test ContentResolver initialization."""
        resolver = ContentResolver(mock_omnidexer)
        assert resolver.omnidexer == mock_omnidexer

    async def test_resolve_adventure_exact_match(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test resolving adventure with exact match."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]

        result = await resolver.resolve_adventure("cos")

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content == sample_adventure
        assert result.query == "cos"
        mock_omnidexer.get_all_by_type.assert_called_with(ContentType.ADVENTURE)

    async def test_resolve_adventure_case_insensitive(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test resolving adventure is case insensitive."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]

        result = await resolver.resolve_adventure("COS")

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content == sample_adventure

    async def test_resolve_book_exact_match(
        self, resolver, mock_omnidexer, sample_book
    ) -> None:
        """Test resolving book with exact match."""
        mock_omnidexer.get_all_by_type.return_value = [sample_book]

        result = await resolver.resolve_book("phb")

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content == sample_book
        assert result.query == "phb"
        mock_omnidexer.get_all_by_type.assert_called_with(ContentType.BOOK)

    async def test_resolve_adventure_multiple_matches_picks_preferred(
        self, resolver, mock_omnidexer
    ) -> None:
        """Test resolving adventure with multiple exact matches picks preferred one."""
        source1 = Source(abbreviation="TEST", name="Test Adventure 1")
        source2 = Source(abbreviation="TEST", name="Test Adventure 2")
        adventure1 = Adventure(
            name="Test Adventure (2024)",
            source=source1,
            contents=[],
            id="test1",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )
        adventure2 = Adventure(
            name="Test Adventure (2023)",
            source=source2,
            contents=[],
            id="test2",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

        mock_omnidexer.get_all_by_type.return_value = [adventure1, adventure2]

        result = await resolver.resolve_adventure("test")

        # When multiple exact matches exist, resolver picks preferred one (shortest name)
        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is not None
        assert result.content in [adventure1, adventure2]
        # Should pick the one with shorter name as tiebreaker (both have same length, picks first)
        assert result.content == adventure1

    async def test_resolve_adventure_no_match_with_suggestions(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test resolving adventure with no match but suggestions."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]

        result = await resolver.resolve_adventure("co")  # Close to "cos"

        assert result.status == ResolutionStatus.NO_MATCH
        assert result.content is None
        assert "cos" in result.suggestions

    async def test_resolve_adventure_empty_abbreviation(
        self, resolver, mock_omnidexer
    ) -> None:
        """Test resolving with empty abbreviation."""
        result = await resolver.resolve_adventure("")

        assert result.status == ResolutionStatus.NO_MATCH
        assert result.query == ""
        mock_omnidexer.get_all_by_type.assert_not_called()

    async def test_resolve_adventure_whitespace_abbreviation(
        self, resolver, mock_omnidexer
    ) -> None:
        """Test resolving with whitespace-only abbreviation."""
        result = await resolver.resolve_adventure("   ")

        assert result.status == ResolutionStatus.NO_MATCH
        assert result.query == "   "

    async def test_resolve_adventure_no_content_available(
        self, resolver, mock_omnidexer
    ) -> None:
        """Test resolving when no content is available."""
        mock_omnidexer.get_all_by_type.return_value = []

        result = await resolver.resolve_adventure("cos")

        assert result.status == ResolutionStatus.NO_MATCH
        assert result.content is None
        assert result.suggestions == []

    async def test_resolve_adventure_fuzzy_match(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test resolving adventure with fuzzy matching."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]
        mock_omnidexer.search.return_value = [sample_adventure]

        result = await resolver.resolve_adventure("cs")  # Close to "cos"

        # Should find fuzzy match through search
        assert result.status == ResolutionStatus.FUZZY_MATCH
        assert result.content == sample_adventure

    async def test_resolve_any_with_content_type(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test resolve_any with specific content type."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]

        result = await resolver.resolve_any("cos", ContentType.ADVENTURE)

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content == sample_adventure

    async def test_resolve_any_without_content_type(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test resolve_any without content type specified."""
        mock_omnidexer.get_all_by_type.side_effect = (
            lambda ct: [sample_adventure] if ct == ContentType.ADVENTURE else []
        )

        result = await resolver.resolve_any("cos")

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content == sample_adventure

    def test_find_suggestions_basic(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test find_suggestions basic functionality."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]

        suggestions = resolver.find_suggestions("co", ContentType.ADVENTURE)

        assert "cos" in suggestions
        assert len(suggestions) <= 5

    def test_find_suggestions_no_content(self, resolver, mock_omnidexer) -> None:
        """Test find_suggestions with no content available."""
        mock_omnidexer.get_all_by_type.return_value = []

        suggestions = resolver.find_suggestions("cos", ContentType.ADVENTURE)

        assert suggestions == []

    def test_find_suggestions_limit(self, resolver, mock_omnidexer) -> None:
        """Test find_suggestions respects limit parameter."""
        # Create many adventures with similar abbreviations
        adventures = []
        for i in range(10):
            source = Source(abbreviation=f"TEST{i}", name=f"Test {i}")
            adventure = Adventure(
                name=f"Test {i}",
                source=source,
                contents=[],
                id=f"test{i}",
                metadata={},
                published=None,
                author=None,
                cover=None,
            )
            adventures.append(adventure)

        mock_omnidexer.get_all_by_type.return_value = adventures

        suggestions = resolver.find_suggestions("test", ContentType.ADVENTURE, limit=3)

        assert len(suggestions) <= 3

    async def test_resolve_content_source_without_abbreviation(
        self, resolver, mock_omnidexer
    ) -> None:
        """Test resolving content where source doesn't have abbreviation attribute."""
        # Create content with source that doesn't have abbreviation
        source = Mock()
        del source.abbreviation  # Remove abbreviation attribute
        adventure = Adventure(
            name="Test",
            source=source,
            contents=[],
            id="test",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

        mock_omnidexer.get_all_by_type.return_value = [adventure]

        result = await resolver.resolve_adventure("test")

        assert result.status == ResolutionStatus.NO_MATCH

    async def test_fuzzy_matching_multiple_results(
        self, resolver, mock_omnidexer
    ) -> None:
        """Test fuzzy matching with multiple results."""
        source1 = Source(abbreviation="COS1", name="Test 1")
        source2 = Source(abbreviation="COS2", name="Test 2")
        adventure1 = Adventure(
            name="Test 1",
            source=source1,
            contents=[],
            id="test1",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )
        adventure2 = Adventure(
            name="Test 2",
            source=source2,
            contents=[],
            id="test2",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

        mock_omnidexer.get_all_by_type.return_value = [adventure1, adventure2]
        mock_omnidexer.search.return_value = [adventure1, adventure2]

        result = await resolver.resolve_adventure("cos")

        assert result.status == ResolutionStatus.MULTIPLE_MATCHES
        assert len(result.matches) == 2

    async def test_search_fallback_no_fuzzy_matches(
        self, resolver, mock_omnidexer, sample_adventure
    ) -> None:
        """Test search fallback when no fuzzy matches are found."""
        different_source = Source(abbreviation="DMG", name="Dungeon Master's Guide")
        different_adventure = Adventure(
            name="Different",
            source=different_source,
            contents=[],
            id="diff",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

        mock_omnidexer.get_all_by_type.return_value = [
            sample_adventure,
            different_adventure,
        ]
        mock_omnidexer.search.return_value = [
            different_adventure
        ]  # Search returns different content

        result = await resolver.resolve_adventure(
            "co"
        )  # Close to COS, should get suggestions

        assert result.status == ResolutionStatus.NO_MATCH
        # Should get suggestions from get_all_by_type content
        assert result.has_suggestions

    @pytest.mark.parametrize(
        "input_abbrev,expected_match",
        [
            ("cos", True),
            ("COS", True),
            ("CoS", True),
            ("  cos  ", True),
            ("xyz", False),
            ("", False),
        ],
    )
    async def test_various_input_formats(
        self, resolver, mock_omnidexer, sample_adventure, input_abbrev, expected_match
    ) -> None:
        """Test various input formats for abbreviations."""
        mock_omnidexer.get_all_by_type.return_value = [sample_adventure]

        result = await resolver.resolve_adventure(input_abbrev)

        if expected_match:
            assert result.status == ResolutionStatus.EXACT_MATCH
            assert result.content == sample_adventure
        else:
            assert result.status != ResolutionStatus.EXACT_MATCH
