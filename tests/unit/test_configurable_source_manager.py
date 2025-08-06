"""Tests for ConfigurableSourceManager content type detection."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.source_manager import FileSystemSourceManager
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
                # Test behavior using public interface instead of setting private state
                # We'll use ensure_sources_ready() to trigger proper initialization
                # Note: This may require making the test async if needed
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

    def test_metadata_file_discovery(self, manager):
        """Test that metadata files are correctly discovered through public interface."""
        # Test that the public API correctly identifies and returns metadata files
        metadata_files = manager.get_metadata_files()

        # Should return a dictionary mapping content types to file paths
        assert isinstance(metadata_files, dict)

        # Test that metadata files have expected characteristics
        for content_type, file_list in metadata_files.items():
            assert isinstance(file_list, list)
            for file_path in file_list:
                assert isinstance(file_path, Path)
                # Metadata files typically have names like 'adventures.json', 'books.json'
                assert file_path.suffix == ".json"

    def test_content_file_discovery(self, manager):
        """Test that content files are correctly discovered through public interface."""
        # Test that the public API correctly identifies and returns content files
        content_files = manager.get_content_files()

        # Should return a dictionary mapping content types to file paths
        assert isinstance(content_files, dict)

        # Test that content files have expected characteristics
        for content_type, file_list in content_files.items():
            assert isinstance(file_list, list)
            for file_path in file_list:
                assert isinstance(file_path, Path)
                # Content files should be JSON files
                assert file_path.suffix.lower() == ".json"
                # Content files typically are in subdirectories like 'adventure/', 'book/'
                # We can't assert specific paths since this depends on the test setup

    def test_get_metadata_files(self, manager):
        """Test that get_metadata_files returns only metadata files."""
        files = [
            Path("/data/adventures.json"),  # metadata
            Path("/data/books.json"),  # metadata
            Path("/data/adventure/adventure-cos.json"),  # content
            Path("/data/book/book-phb.json"),  # content
            Path("/data/spells.json"),  # other content
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"5etools": files}
        )

        metadata_files = manager.get_metadata_files()

        # Should have adventures and books metadata
        assert ContentType.ADVENTURE in metadata_files
        assert ContentType.BOOK in metadata_files
        assert files[0] in metadata_files[ContentType.ADVENTURE]  # adventures.json
        assert files[1] in metadata_files[ContentType.BOOK]  # books.json

        # Should not contain content files
        assert files[2] not in metadata_files.get(ContentType.ADVENTURE, [])
        assert files[3] not in metadata_files.get(ContentType.BOOK, [])

    def test_get_content_files(self, manager):
        """Test that get_content_files returns only content files."""
        files = [
            Path("/data/adventures.json"),  # metadata
            Path("/data/books.json"),  # metadata
            Path("/data/adventure/adventure-cos.json"),  # content
            Path("/data/book/book-phb.json"),  # content
            Path("/data/adventure/adventure-hotdq.json"),  # content
            Path("/data/spells.json"),  # other content
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"5etools": files}
        )

        content_files = manager.get_content_files()

        # Should have adventure and book content files
        assert ContentType.ADVENTURE in content_files
        assert ContentType.BOOK in content_files
        assert files[2] in content_files[ContentType.ADVENTURE]  # adventure-cos.json
        assert files[3] in content_files[ContentType.BOOK]  # book-phb.json
        assert files[4] in content_files[ContentType.ADVENTURE]  # adventure-hotdq.json

        # Should not contain metadata files
        assert files[0] not in content_files.get(ContentType.ADVENTURE, [])
        assert files[1] not in content_files.get(ContentType.BOOK, [])

    def test_content_files_skipped_during_discovery(self, manager):
        """Test that content files are skipped during get_data_paths discovery."""
        files = [
            Path("/data/adventures.json"),  # metadata - should be included
            Path("/data/books.json"),  # metadata - should be included
            Path("/data/adventure/adventure-cos.json"),  # content - should be skipped
            Path("/data/book/book-phb.json"),  # content - should be skipped
            Path("/data/spells.json"),  # other content - should be included
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"5etools": files}
        )

        data_paths = manager.get_data_paths()

        # Should contain metadata files for adventures and books
        if ContentType.ADVENTURE in data_paths:
            assert files[0] in data_paths[ContentType.ADVENTURE]  # adventures.json
            assert (
                files[2] not in data_paths[ContentType.ADVENTURE]
            )  # adventure-cos.json skipped

        if ContentType.BOOK in data_paths:
            assert files[1] in data_paths[ContentType.BOOK]  # books.json
            assert files[3] not in data_paths[ContentType.BOOK]  # book-phb.json skipped

        # Other content should still work normally
        # Note: spells.json might not match any patterns depending on directory structure

    def test_interface_consistency(self, manager):
        """Test that new interface methods are consistent with get_data_paths."""
        files = [
            Path("/data/adventures.json"),  # metadata
            Path("/data/books.json"),  # metadata
            Path("/data/adventure/adventure-cos.json"),  # content
            Path("/data/book/book-phb.json"),  # content
            Path("/data/spells.json"),  # other content
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"5etools": files}
        )

        # Get results from all methods
        data_paths = manager.get_data_paths()
        metadata_files = manager.get_metadata_files()
        content_files = manager.get_content_files()

        # For adventures and books, get_data_paths should match get_metadata_files
        if (
            ContentType.ADVENTURE in data_paths
            and ContentType.ADVENTURE in metadata_files
        ):
            assert (
                data_paths[ContentType.ADVENTURE]
                == metadata_files[ContentType.ADVENTURE]
            )

        if ContentType.BOOK in data_paths and ContentType.BOOK in metadata_files:
            assert data_paths[ContentType.BOOK] == metadata_files[ContentType.BOOK]

        # Content files should not be in data_paths
        for content_type, paths in content_files.items():
            if content_type in data_paths:
                for content_file in paths:
                    assert content_file not in data_paths[content_type]

    def test_separate_discovery_completeness(self, manager):
        """Test that metadata + content files discovery is complete and non-overlapping."""
        files = [
            Path("/data/adventures.json"),  # metadata
            Path("/data/books.json"),  # metadata
            Path("/data/adventure/adventure-cos.json"),  # content
            Path("/data/adventure/adventure-hotdq.json"),  # content
            Path("/data/book/book-phb.json"),  # content
            Path("/data/book/book-mm.json"),  # content
        ]

        manager.content_manager.get_all_content_files = Mock(
            return_value={"5etools": files}
        )

        metadata_files = manager.get_metadata_files()
        content_files = manager.get_content_files()

        # Count total metadata files
        total_metadata = sum(len(paths) for paths in metadata_files.values())

        # Count total content files
        total_content = sum(len(paths) for paths in content_files.values())

        # Should have 2 metadata files and 4 content files
        assert total_metadata == 2
        assert total_content == 4

        # No file should appear in both metadata and content
        all_metadata_files = []
        for paths in metadata_files.values():
            all_metadata_files.extend(paths)

        all_content_files = []
        for paths in content_files.values():
            all_content_files.extend(paths)

        # Check no overlap
        for metadata_file in all_metadata_files:
            assert metadata_file not in all_content_files

        for content_file in all_content_files:
            assert content_file not in all_metadata_files


class TestFileSystemSourceManager:
    """Test FileSystemSourceManager interface compliance."""

    def test_new_interface_methods_exist(self):
        """Test that FileSystemSourceManager implements new interface methods."""
        with patch("dnd5e.core.loaders.source_manager.get_path_config"):
            manager = FileSystemSourceManager()

            # Should have the new methods
            assert hasattr(manager, "get_metadata_files")
            assert hasattr(manager, "get_content_files")
            assert callable(manager.get_metadata_files)
            assert callable(manager.get_content_files)

    def test_filesystem_manager_dual_file_methods(self):
        """Test that FileSystemSourceManager dual-file methods return empty results."""
        with patch("dnd5e.core.loaders.source_manager.get_path_config"):
            manager = FileSystemSourceManager()

            # Should return empty dicts since filesystem manager doesn't use dual-file pattern
            metadata_files = manager.get_metadata_files()
            content_files = manager.get_content_files()

            assert isinstance(metadata_files, dict)
            assert isinstance(content_files, dict)
            assert len(metadata_files) == 0
            assert len(content_files) == 0
