"""Tests for token count functionality in TokenSheet."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from studiorum.core.models.tokens import TokenData, TokenSheet


class TestTokenSheetCounts:
    """Test TokenSheet creation with per-creature counts."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create mock creatures with different sizes
        self.mock_creature_small = Mock()
        self.mock_creature_small.name = "Goblin"
        self.mock_creature_small.size = ["S"]
        self.mock_creature_small.source = Mock()
        self.mock_creature_small.source.abbreviation = "MM"
        self.mock_creature_small.get_cr_text = Mock(return_value="1/4")

        self.mock_creature_medium = Mock()
        self.mock_creature_medium.name = "Orc"
        self.mock_creature_medium.size = ["M"]
        self.mock_creature_medium.source = Mock()
        self.mock_creature_medium.source.abbreviation = "MM"
        self.mock_creature_medium.get_cr_text = Mock(return_value="1")

        self.mock_creature_large = Mock()
        self.mock_creature_large.name = "Ogre"
        self.mock_creature_large.size = ["L"]
        self.mock_creature_large.source = Mock()
        self.mock_creature_large.source.abbreviation = "MM"
        self.mock_creature_large.get_cr_text = Mock(return_value="2")

        # Create mock image resolver
        self.mock_resolver = Mock()
        self.mock_resolver.resolve_token_image = Mock(
            return_value=Path("/fake/path.png")
        )

    def test_token_sheet_default_counts(self) -> None:
        """Test TokenSheet uses default_count when no creature_counts provided."""
        creatures = [self.mock_creature_small, self.mock_creature_medium]

        token_sheet = TokenSheet.from_creatures(
            creatures, self.mock_resolver, default_count=3
        )

        # Verify all tokens use default count
        small_tokens = token_sheet.get_tokens_for_size("small")
        medium_tokens = token_sheet.get_tokens_for_size("medium")

        assert len(small_tokens) == 1
        assert len(medium_tokens) == 1
        assert small_tokens[0].count == 3
        assert medium_tokens[0].count == 3
        assert small_tokens[0].creature_name == "Goblin"
        assert medium_tokens[0].creature_name == "Orc"

    def test_token_sheet_per_creature_counts(self) -> None:
        """Test TokenSheet uses per-creature counts when provided."""
        creatures = [
            self.mock_creature_small,
            self.mock_creature_medium,
            self.mock_creature_large,
        ]

        creature_counts = {"Goblin": 4, "Orc": 6, "Ogre": 2}

        token_sheet = TokenSheet.from_creatures(
            creatures,
            self.mock_resolver,
            default_count=1,  # Should be ignored in favor of creature_counts
            creature_counts=creature_counts,
        )

        # Verify tokens use per-creature counts
        small_tokens = token_sheet.get_tokens_for_size("small")
        medium_tokens = token_sheet.get_tokens_for_size("medium")
        large_tokens = token_sheet.get_tokens_for_size("large")

        assert len(small_tokens) == 1
        assert len(medium_tokens) == 1
        assert len(large_tokens) == 1

        assert small_tokens[0].count == 4  # Goblin
        assert medium_tokens[0].count == 6  # Orc
        assert large_tokens[0].count == 2  # Ogre

    def test_token_sheet_partial_creature_counts(self) -> None:
        """Test TokenSheet falls back to default for creatures not in creature_counts."""
        creatures = [
            self.mock_creature_small,
            self.mock_creature_medium,
            self.mock_creature_large,
        ]

        # Only provide counts for some creatures
        creature_counts = {
            "Goblin": 5,
            "Ogre": 3,
            # Orc is missing - should use default
        }

        token_sheet = TokenSheet.from_creatures(
            creatures,
            self.mock_resolver,
            default_count=2,
            creature_counts=creature_counts,
        )

        small_tokens = token_sheet.get_tokens_for_size("small")
        medium_tokens = token_sheet.get_tokens_for_size("medium")
        large_tokens = token_sheet.get_tokens_for_size("large")

        assert small_tokens[0].count == 5  # From creature_counts
        assert medium_tokens[0].count == 2  # Default (not in creature_counts)
        assert large_tokens[0].count == 3  # From creature_counts

    def test_token_sheet_total_count_calculation(self) -> None:
        """Test total token count calculation includes per-creature counts."""
        creatures = [self.mock_creature_small, self.mock_creature_medium]

        creature_counts = {"Goblin": 4, "Orc": 6}

        token_sheet = TokenSheet.from_creatures(
            creatures,
            self.mock_resolver,
            default_count=1,
            creature_counts=creature_counts,
        )

        # Total should be 4 + 6 = 10
        assert token_sheet.get_total_token_count() == 10

    def test_token_sheet_empty_creature_counts(self) -> None:
        """Test TokenSheet handles empty creature_counts dict correctly."""
        creatures = [self.mock_creature_small]

        token_sheet = TokenSheet.from_creatures(
            creatures,
            self.mock_resolver,
            default_count=3,
            creature_counts={},  # Empty dict
        )

        small_tokens = token_sheet.get_tokens_for_size("small")
        assert small_tokens[0].count == 3  # Should use default

    def test_token_sheet_none_creature_counts(self) -> None:
        """Test TokenSheet handles None creature_counts correctly."""
        creatures = [self.mock_creature_small]

        token_sheet = TokenSheet.from_creatures(
            creatures, self.mock_resolver, default_count=3, creature_counts=None
        )

        small_tokens = token_sheet.get_tokens_for_size("small")
        assert small_tokens[0].count == 3  # Should use default

    def test_backward_compatibility(self) -> None:
        """Test that existing code without creature_counts continues to work."""
        creatures = [self.mock_creature_small, self.mock_creature_medium]

        # Call without creature_counts parameter (backward compatibility)
        token_sheet = TokenSheet.from_creatures(
            creatures, self.mock_resolver, default_count=2
        )

        small_tokens = token_sheet.get_tokens_for_size("small")
        medium_tokens = token_sheet.get_tokens_for_size("medium")

        assert small_tokens[0].count == 2
        assert medium_tokens[0].count == 2
