"""Tests for ConfigurableSourceManager content type detection."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.models.content import ContentType


class TestConfigurableSourceManager:
    """Test configurable source manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a ConfigurableSourceManager for testing."""
        with patch("dnd5e.core.loaders.configurable_source_manager.get_content_config"):
            with patch(
                "dnd5e.core.loaders.configurable_source_manager.ContentSourceManager"
            ):
                manager = ConfigurableSourceManager()
                manager.content_manager._index_built = True
                return manager

    def test_directory_priority_over_filename_for_races(self, manager):
        """Test that directory names have priority over filename patterns for race files."""
        # Mock file that has "monsters" in filename but is in race directory
        problematic_file = Path(
            "/cache/homebrew/race/Foxfire94; Volos Original Guide to Monsters.json"
        )

        # Mock the content manager to return our test file
        manager.content_manager.get_all_content_files = Mock(
            return_value={"homebrew": [problematic_file]}
        )

        # Get data paths
        data_paths = manager.get_data_paths()

        # File should be assigned to RACE, not CREATURE
        assert ContentType.RACE in data_paths
        assert problematic_file in data_paths[ContentType.RACE]

        # File should NOT be assigned to CREATURE
        if ContentType.CREATURE in data_paths:
            assert problematic_file not in data_paths[ContentType.CREATURE]

    def test_directory_priority_over_filename_for_items(self, manager):
        """Test that spell component items are correctly identified as items."""
        # Mock spell component file
        spell_component_file = Path(
            "/cache/homebrew/item/5eTools; Spell Components (inc. UA).json"
        )

        manager.content_manager.get_all_content_files = Mock(
            return_value={"homebrew": [spell_component_file]}
        )

        data_paths = manager.get_data_paths()

        # File should be assigned to ITEM
        assert ContentType.ITEM in data_paths
        assert spell_component_file in data_paths[ContentType.ITEM]

        # File should NOT be assigned to SPELL even though it has "Spell" in filename
        if ContentType.SPELL in data_paths:
            assert spell_component_file not in data_paths[ContentType.SPELL]

    def test_creature_files_in_creature_directory(self, manager):
        """Test that creature files in creature directories are correctly identified."""
        creature_file = Path(
            "/cache/homebrew/creature/Angry Golem Games; Monster Manual (A-G).json"
        )

        manager.content_manager.get_all_content_files = Mock(
            return_value={"homebrew": [creature_file]}
        )

        data_paths = manager.get_data_paths()

        # File should be assigned to CREATURE
        assert ContentType.CREATURE in data_paths
        assert creature_file in data_paths[ContentType.CREATURE]

    def test_multiple_conflicting_files(self, manager):
        """Test handling of multiple files with conflicting patterns."""
        files = [
            Path(
                "/cache/homebrew/race/Foxfire94; Volos Original Guide to Monsters.json"
            ),  # Should be RACE
            Path(
                "/cache/homebrew/creature/Angry Golem Games; Monster Manual (A-G).json"
            ),  # Should be CREATURE
            Path(
                "/cache/homebrew/item/5eTools; Spell Components (inc. UA).json"
            ),  # Should be ITEM
            Path(
                "/cache/homebrew/spell/Sample - Giddy; Assorted Marginalia.json"
            ),  # Should be SPELL
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"homebrew": files}
        )

        data_paths = manager.get_data_paths()

        # Check each file is assigned to correct type based on directory
        assert files[0] in data_paths[ContentType.RACE]  # race directory
        assert files[1] in data_paths[ContentType.CREATURE]  # creature directory
        assert files[2] in data_paths[ContentType.ITEM]  # item directory
        assert files[3] in data_paths[ContentType.SPELL]  # spell directory

        # Check files are not double-assigned
        all_assigned_files = []
        for file_list in data_paths.values():
            all_assigned_files.extend(file_list)

        # Each file should appear exactly once
        for file in files:
            assert all_assigned_files.count(file) == 1

    def test_filename_pattern_as_fallback(self, manager):
        """Test that filename patterns work when directory doesn't match."""
        # File with clear filename pattern but in generic directory
        spell_file = Path("/cache/content/some-spell-collection.json")

        manager.content_manager.get_all_content_files = Mock(
            return_value={"content": [spell_file]}
        )

        data_paths = manager.get_data_paths()

        # Should be assigned based on filename pattern
        assert ContentType.SPELL in data_paths
        assert spell_file in data_paths[ContentType.SPELL]

    def test_fluff_files_get_priority(self, manager):
        """Test that fluff files are processed before regular files."""
        files = [
            Path(
                "/cache/homebrew/fluff-spell/spell-fluff-data.json"
            ),  # Should be SPELL_FLUFF
            Path(
                "/cache/homebrew/creature/monster-fluff.json"
            ),  # Should be CREATURE_FLUFF
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"homebrew": files}
        )

        data_paths = manager.get_data_paths()

        # Check fluff files are assigned correctly
        assert ContentType.SPELL_FLUFF in data_paths
        assert files[0] in data_paths[ContentType.SPELL_FLUFF]

        assert ContentType.CREATURE_FLUFF in data_paths
        assert files[1] in data_paths[ContentType.CREATURE_FLUFF]

    def test_no_double_assignment(self, manager):
        """Test that files are not assigned to multiple content types."""
        # This file could match both item and spell patterns
        ambiguous_file = Path("/cache/homebrew/item/magic-items-with-spells.json")

        manager.content_manager.get_all_content_files = Mock(
            return_value={"homebrew": [ambiguous_file]}
        )

        data_paths = manager.get_data_paths()

        # Count how many times file appears across all content types
        total_assignments = 0
        for file_list in data_paths.values():
            if ambiguous_file in file_list:
                total_assignments += 1

        # Should be assigned exactly once
        assert total_assignments == 1

        # Should be assigned to ITEM based on directory
        assert ContentType.ITEM in data_paths
        assert ambiguous_file in data_paths[ContentType.ITEM]
