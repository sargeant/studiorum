"""Tests for per-creature source mapping functionality."""

from unittest.mock import Mock

import pytest

from studiorum.core.models.content import ContentType
from studiorum.core.models.creature_filters import CreatureFilterCriteria
from studiorum.core.models.creatures import Creature
from studiorum.core.services.creature_collector import CreatureCollector


@pytest.mark.fast
class TestCreatureSourceMapping:
    """Test suite for per-creature source mapping functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Create mock omnidexer
        self.mock_omnidexer = Mock()
        # Mock get_all_by_type to return empty list (for lair actions)
        self.mock_omnidexer.get_all_by_type.return_value = []
        self.collector = CreatureCollector(self.mock_omnidexer)

        # Create mock creatures for testing
        self.mock_creature_mm = Mock(spec=Creature)
        self.mock_creature_mm.name = "Goblin"
        self.mock_creature_mm.source = Mock()
        self.mock_creature_mm.source.abbreviation = "MM"

        self.mock_creature_vgm = Mock(spec=Creature)
        self.mock_creature_vgm.name = "Goblin"
        self.mock_creature_vgm.source = Mock()
        self.mock_creature_vgm.source.abbreviation = "VGM"

    def test_creature_source_map_field_exists(self):
        """Test that CreatureFilterCriteria supports creature_source_map field."""
        criteria = CreatureFilterCriteria(
            creature_names=["Goblin"], creature_source_map={"Goblin": "MM"}
        )

        assert criteria.creature_source_map == {"Goblin": "MM"}
        assert criteria.creature_names == ["Goblin"]

    def test_is_name_only_filter_with_source_map(self):
        """Test that is_name_only_filter works correctly with source mapping."""
        # Should be considered name-only even with source mapping
        criteria = CreatureFilterCriteria(
            creature_names=["Goblin"], creature_source_map={"Goblin": "MM"}
        )

        assert criteria.is_name_only_filter() is True

    def test_is_name_only_filter_with_additional_criteria(self):
        """Test that is_name_only_filter is False with additional criteria."""
        criteria = CreatureFilterCriteria(
            creature_names=["Goblin"],
            creature_source_map={"Goblin": "MM"},
            min_cr=1.0,  # Additional filter
        )

        assert criteria.is_name_only_filter() is False

    def test_collect_by_names_with_source_mapping(self):
        """Test that collect_by_names uses per-creature source specifications."""
        # Setup mock to return specific creature when called with source
        self.mock_omnidexer.find.return_value = self.mock_creature_mm

        # Test collection with source mapping
        result = self.collector.collect_by_names(
            names=["Goblin"], creature_source_map={"Goblin": "MM"}
        )

        # Verify find was called with specific source
        self.mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Goblin", "MM"
        )

        # Verify result contains the creature
        assert len(result.creatures) == 1
        assert result.creatures[0] == self.mock_creature_mm

    def test_collect_by_names_without_source_mapping(self):
        """Test that collect_by_names falls back to find_all without source mapping."""
        # Setup mock to return multiple creatures
        self.mock_omnidexer.find_all.return_value = [
            self.mock_creature_mm,
            self.mock_creature_vgm,
        ]

        # Test collection without source mapping
        self.collector.collect_by_names(names=["Goblin"], sources=["MM", "VGM"])

        # Verify find_all was called
        self.mock_omnidexer.find_all.assert_called_once_with(
            ContentType.CREATURE, "Goblin"
        )

        # find_all should have been called, not find
        self.mock_omnidexer.find.assert_not_called()

    def test_collect_by_names_mixed_source_mapping(self):
        """Test collection with some creatures having specific sources and others not."""
        # Setup mocks
        self.mock_omnidexer.find.return_value = self.mock_creature_mm
        self.mock_omnidexer.find_all.return_value = [self.mock_creature_vgm]

        # Test with mixed mapping (one creature with specific source, one without)
        self.collector.collect_by_names(
            names=["Goblin", "Orc"],
            sources=["VGM"],
            creature_source_map={"Goblin": "MM"},  # Only Goblin has specific source
        )

        # Verify both methods were called appropriately
        self.mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Goblin", "MM"
        )
        self.mock_omnidexer.find_all.assert_called_once_with(
            ContentType.CREATURE, "Orc"
        )

    def test_creature_source_map_validation_in_criteria(self):
        """Test that creature_source_map is included in criteria validation."""
        # Should be valid with just creature_source_map
        criteria = CreatureFilterCriteria(creature_source_map={"Goblin": "MM"})

        # This should not raise a validation error
        assert criteria.creature_source_map == {"Goblin": "MM"}

    def test_empty_source_map_handling(self):
        """Test that empty or None source maps are handled correctly."""
        # Test with None
        criteria_none = CreatureFilterCriteria(
            creature_names=["Goblin"], creature_source_map=None
        )
        assert criteria_none.creature_source_map is None

        # Test with empty dict
        criteria_empty = CreatureFilterCriteria(
            creature_names=["Goblin"], creature_source_map={}
        )
        assert criteria_empty.creature_source_map == {}

    def test_collect_creatures_passes_source_map(self):
        """Test that collect_creatures passes source_map to _collect_by_names."""
        # Setup mock
        self.mock_omnidexer.find.return_value = self.mock_creature_mm

        # Create criteria with source mapping
        criteria = CreatureFilterCriteria(
            creature_names=["Goblin"], creature_source_map={"Goblin": "MM"}
        )

        # Collect creatures
        result = self.collector.collect_creatures(criteria)

        # Verify the source-specific find was called
        self.mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Goblin", "MM"
        )

        # Verify result
        assert len(result.creatures) == 1
        assert result.creatures[0] == self.mock_creature_mm
