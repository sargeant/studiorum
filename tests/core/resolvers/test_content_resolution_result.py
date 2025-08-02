"""Comprehensive tests for ContentResolutionResult Pydantic model."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from dnd5e.core.models.adventures import Adventure
from dnd5e.core.models.books import Book
from dnd5e.core.models.content import BaseContent, Source
from dnd5e.core.resolvers.content_resolver import (
    ContentResolutionResult,
    ResolutionStatus,
)


class TestResolutionStatus:
    """Tests for ResolutionStatus enum."""

    def test_resolution_status_values(self) -> None:
        """Test ResolutionStatus enum values."""
        assert ResolutionStatus.EXACT_MATCH.value == "exact_match"
        assert ResolutionStatus.MULTIPLE_MATCHES.value == "multiple_matches"
        assert ResolutionStatus.NO_MATCH.value == "no_match"
        assert ResolutionStatus.FUZZY_MATCH.value == "fuzzy_match"

    def test_resolution_status_membership(self) -> None:
        """Test ResolutionStatus membership checks."""
        assert "exact_match" in ResolutionStatus
        assert "fuzzy_match" in ResolutionStatus
        assert "invalid_status" not in ResolutionStatus


class TestContentResolutionResult:
    """Tests for ContentResolutionResult Pydantic model."""

    @pytest.fixture
    def sample_source(self) -> Source:
        """Create sample source for testing."""
        return Source(abbreviation="COS", name="Curse of Strahd")

    @pytest.fixture
    def sample_adventure(self, sample_source: Source) -> Adventure:
        """Create sample adventure for testing."""
        return Adventure(
            name="Curse of Strahd",
            source=sample_source,
            contents=[],
            id="cos",
            metadata={},
            published=None,
            author=None,
            cover=None,
        )

    @pytest.fixture
    def sample_book(self) -> Book:
        """Create sample book for testing."""
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

    @pytest.fixture
    def multiple_adventures(self) -> list[Adventure]:
        """Create multiple adventures for testing."""
        return [
            Adventure(
                name="Curse of Strahd",
                source=Source(abbreviation="COS1", name="Curse of Strahd v1"),
                contents=[],
                id="cos1",
                metadata={},
                published=None,
                author=None,
                cover=None,
            ),
            Adventure(
                name="Curse of Strahd Revised",
                source=Source(abbreviation="COS2", name="Curse of Strahd v2"),
                contents=[],
                id="cos2",
                metadata={},
                published=None,
                author=None,
                cover=None,
            ),
        ]

    def test_content_resolution_result_creation_minimal(self) -> None:
        """Test creating ContentResolutionResult with minimal fields."""
        result = ContentResolutionResult(status=ResolutionStatus.EXACT_MATCH)

        assert result.status == ResolutionStatus.EXACT_MATCH
        assert result.content is None
        assert result.matches == []
        assert result.suggestions == []
        assert result.query == ""

    def test_content_resolution_result_creation_full(
        self, sample_adventure: Adventure, multiple_adventures: list[Adventure]
    ) -> None:
        """Test creating ContentResolutionResult with all fields."""
        suggestions = ["cos", "lmop", "hotdq"]

        result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES,
            content=sample_adventure,
            matches=multiple_adventures,
            suggestions=suggestions,
            query="curse of strahd",
        )

        assert result.status == ResolutionStatus.MULTIPLE_MATCHES
        assert result.content == sample_adventure
        assert result.matches == multiple_adventures
        assert result.suggestions == suggestions
        assert result.query == "curse of strahd"

    def test_content_resolution_result_status_validation(
        self, sample_adventure: Adventure
    ) -> None:
        """Test status field validation."""
        # Valid status
        result = ContentResolutionResult(status=ResolutionStatus.EXACT_MATCH)
        assert result.status == ResolutionStatus.EXACT_MATCH

        # Test all valid status values
        for status in ResolutionStatus:
            result = ContentResolutionResult(status=status)
            assert result.status == status

        # Invalid status type should fail
        with pytest.raises(ValidationError) as exc_info:
            ContentResolutionResult(status="invalid_status")  # type: ignore
        assert "Input should be" in str(exc_info.value)

    def test_content_resolution_result_query_validation(self) -> None:
        """Test query field validation."""
        # Empty query (default)
        result = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)
        assert result.query == ""

        # String query
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, query="test query"
        )
        assert result.query == "test query"

        # Query preserves original input (including whitespace)
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, query="  test query  "
        )
        assert result.query == "  test query  "

        # Unicode query
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, query="tëst qüery"
        )
        assert result.query == "tëst qüery"

    def test_content_resolution_result_suggestions_validation(self) -> None:
        """Test suggestions field validation."""
        # Empty suggestions (default)
        result = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)
        assert result.suggestions == []

        # Valid suggestions
        suggestions = ["cos", "lmop", "hotdq"]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=suggestions
        )
        assert result.suggestions == suggestions

        # Suggestions with whitespace get cleaned
        suggestions_with_whitespace = ["  cos  ", "lmop", "  hotdq  "]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=suggestions_with_whitespace
        )
        assert result.suggestions == ["cos", "lmop", "hotdq"]

        # Empty strings are removed
        suggestions_with_empty = ["cos", "", "lmop", "   ", "hotdq"]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=suggestions_with_empty
        )
        assert result.suggestions == ["cos", "lmop", "hotdq"]

        # Duplicates are removed while preserving order
        suggestions_with_duplicates = ["cos", "lmop", "cos", "hotdq", "lmop"]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=suggestions_with_duplicates
        )
        assert result.suggestions == ["cos", "lmop", "hotdq"]

    def test_content_resolution_result_is_success_property(self) -> None:
        """Test is_success property."""
        # Exact match is success
        result = ContentResolutionResult(status=ResolutionStatus.EXACT_MATCH)
        assert result.is_success is True

        # Other statuses are not success
        for status in [
            ResolutionStatus.FUZZY_MATCH,
            ResolutionStatus.MULTIPLE_MATCHES,
            ResolutionStatus.NO_MATCH,
        ]:
            result = ContentResolutionResult(status=status)
            assert result.is_success is False

    def test_content_resolution_result_needs_user_selection_property(self) -> None:
        """Test needs_user_selection property."""
        # Multiple matches needs user selection
        result = ContentResolutionResult(status=ResolutionStatus.MULTIPLE_MATCHES)
        assert result.needs_user_selection is True

        # Other statuses do not need user selection
        for status in [
            ResolutionStatus.EXACT_MATCH,
            ResolutionStatus.FUZZY_MATCH,
            ResolutionStatus.NO_MATCH,
        ]:
            result = ContentResolutionResult(status=status)
            assert result.needs_user_selection is False

    def test_content_resolution_result_has_suggestions_property(self) -> None:
        """Test has_suggestions property."""
        # With suggestions
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=["cos", "lmop"]
        )
        assert result.has_suggestions is True

        # Empty suggestions
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=[]
        )
        assert result.has_suggestions is False

        # None suggestions (default)
        result = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)
        assert result.has_suggestions is False

    def test_content_resolution_result_arbitrary_types_allowed(self) -> None:
        """Test that arbitrary types are allowed for content and matches."""
        # Mock content should work
        mock_content = Mock(spec=BaseContent)
        result = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH, content=mock_content
        )
        assert result.content == mock_content

        # Mock matches should work
        mock_matches = [Mock(spec=BaseContent), Mock(spec=BaseContent)]
        result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES, matches=mock_matches
        )
        assert result.matches == mock_matches

    def test_content_resolution_result_typical_success_scenario(
        self, sample_adventure: Adventure
    ) -> None:
        """Test typical successful resolution scenario."""
        result = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH, content=sample_adventure, query="cos"
        )

        assert result.is_success
        assert not result.needs_user_selection
        assert not result.has_suggestions
        assert result.content == sample_adventure
        assert result.query == "cos"

    def test_content_resolution_result_typical_multiple_matches_scenario(
        self, multiple_adventures: list[Adventure]
    ) -> None:
        """Test typical multiple matches scenario."""
        result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES,
            matches=multiple_adventures,
            query="cos",
        )

        assert not result.is_success
        assert result.needs_user_selection
        assert not result.has_suggestions
        assert result.content is None
        assert result.matches == multiple_adventures
        assert result.query == "cos"

    def test_content_resolution_result_typical_no_match_with_suggestions_scenario(
        self,
    ) -> None:
        """Test typical no match with suggestions scenario."""
        suggestions = ["cos", "lmop", "hotdq"]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=suggestions, query="co"
        )

        assert not result.is_success
        assert not result.needs_user_selection
        assert result.has_suggestions
        assert result.content is None
        assert result.matches == []
        assert result.suggestions == suggestions
        assert result.query == "co"

    def test_content_resolution_result_fuzzy_match_scenario(
        self, sample_adventure: Adventure
    ) -> None:
        """Test fuzzy match scenario."""
        result = ContentResolutionResult(
            status=ResolutionStatus.FUZZY_MATCH,
            content=sample_adventure,
            query="cs",  # Close to "cos"
        )

        assert not result.is_success  # Fuzzy match is not considered success
        assert not result.needs_user_selection
        assert not result.has_suggestions
        assert result.content == sample_adventure
        assert result.query == "cs"

    def test_content_resolution_result_edge_cases(self) -> None:
        """Test edge cases and boundary conditions."""
        # Very long query
        long_query = "a" * 1000
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, query=long_query
        )
        assert result.query == long_query

        # Very long suggestions - make them unique to avoid deduplication
        long_suggestions = [f"suggestion_{i}_" + "a" * 100 for i in range(50)]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=long_suggestions
        )
        assert result.suggestions == long_suggestions

        # Unicode in suggestions
        unicode_suggestions = ["cös", "lömp", "hötdq"]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=unicode_suggestions
        )
        assert result.suggestions == unicode_suggestions

    def test_content_resolution_result_suggestions_order_preservation(self) -> None:
        """Test that suggestions preserve order after deduplication."""
        # Order should be preserved when removing duplicates
        suggestions = ["third", "first", "second", "first", "third", "fourth"]
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=suggestions
        )
        # Should preserve first occurrence order
        assert result.suggestions == ["third", "first", "second", "fourth"]

    def test_content_resolution_result_mixed_content_types(
        self, sample_adventure: Adventure, sample_book: Book
    ) -> None:
        """Test with mixed content types in matches."""
        mixed_matches = [sample_adventure, sample_book]
        result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES,
            matches=mixed_matches,
            query="test",
        )

        assert result.matches == mixed_matches
        assert len(result.matches) == 2
        assert isinstance(result.matches[0], Adventure)
        assert isinstance(result.matches[1], Book)

    def test_content_resolution_result_status_consistency_validation(self) -> None:
        """Test status consistency validation."""
        # The model should accept any valid ResolutionStatus
        for status in ResolutionStatus:
            result = ContentResolutionResult(status=status)
            assert result.status == status

        # Custom validator should reject non-ResolutionStatus types
        with pytest.raises(ValidationError) as exc_info:
            # This should fail at Pydantic level before reaching custom validator
            ContentResolutionResult(status="not_a_status")  # type: ignore

        # The error should be about invalid enum value
        error_msg = str(exc_info.value)
        assert "Input should be" in error_msg

    def test_content_resolution_result_default_factory_behavior(self) -> None:
        """Test that default_factory creates new instances for mutable fields."""
        # Create two results with default values
        result1 = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)
        result2 = ContentResolutionResult(status=ResolutionStatus.NO_MATCH)

        # Lists should be different instances (not shared)
        assert result1.matches is not result2.matches
        assert result1.suggestions is not result2.suggestions

        # Modifying one shouldn't affect the other
        result1.matches.append(Mock(spec=BaseContent))
        result1.suggestions.append("test")

        assert len(result1.matches) == 1
        assert len(result1.suggestions) == 1
        assert len(result2.matches) == 0
        assert len(result2.suggestions) == 0

    def test_content_resolution_result_complex_suggestions_scenarios(self) -> None:
        """Test complex suggestions validation scenarios."""
        # Mix of valid and invalid suggestions
        complex_suggestions = [
            "valid1",
            "  valid2  ",  # Will be stripped
            "",  # Will be removed
            "valid3",
            "   ",  # Will be removed (whitespace only)
            "valid1",  # Duplicate, will be removed
            "valid4",
            None,  # Should cause validation error
        ]

        # This should raise a validation error because of None
        with pytest.raises(ValidationError):
            ContentResolutionResult(
                status=ResolutionStatus.NO_MATCH,
                suggestions=complex_suggestions,  # type: ignore
            )

        # Without None, it should work
        valid_complex_suggestions = [
            "valid1",
            "  valid2  ",
            "",
            "valid3",
            "   ",
            "valid1",  # Duplicate
            "valid4",
        ]

        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=valid_complex_suggestions
        )

        # Should clean up and deduplicate
        assert result.suggestions == ["valid1", "valid2", "valid3", "valid4"]

    def test_content_resolution_result_serialization_compatibility(
        self, sample_adventure: Adventure
    ) -> None:
        """Test that the model can be serialized and deserialized."""
        # Create a result with all fields populated
        original = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH,
            content=sample_adventure,
            matches=[sample_adventure],
            suggestions=["cos", "lmop"],
            query="cos",
        )

        # Convert to dict (simulating serialization)
        result_dict = original.model_dump()

        # Verify dict structure - status should be the enum object
        assert result_dict["status"] == ResolutionStatus.EXACT_MATCH
        assert result_dict["query"] == "cos"
        assert result_dict["suggestions"] == ["cos", "lmop"]
        # Note: content and matches contain complex objects, so we don't deeply validate here

        # Create new instance from dict (simulating deserialization)
        # Note: This would require proper content deserialization in practice
        reconstructed = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH,
            content=sample_adventure,  # Would need proper deserialization
            matches=[sample_adventure],  # Would need proper deserialization
            suggestions=result_dict["suggestions"],
            query=result_dict["query"],
        )

        assert reconstructed.status == original.status
        assert reconstructed.query == original.query
        assert reconstructed.suggestions == original.suggestions
