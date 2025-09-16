"""Tests for ContentListWriter service."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.result import Error, Success
from studiorum.core.services.content_list_writer import (
    ContentListWriter,
    ContentListWriterError,
)
from tests.test_helpers import reset_test_environment


@pytest.mark.fast
class TestContentListWriter:
    """Test ContentListWriter service functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()
        self.writer = ContentListWriter()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_service_name(self) -> None:
        """Test service returns correct name."""
        assert self.writer.get_service_name() == "ContentListWriter"

    def test_write_content_list_success(self) -> None:
        """Test successful content list writing."""
        # Setup mock content tracker
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 3},
                {"name": "Orc", "source": "MM", "reference_count": 1},
            ],
            "spell": [
                {"name": "Fireball", "source": "PHB", "reference_count": 2},
            ],
        }

        output_path = self.temp_dir / "test_content.txt"

        result = self.writer.write_content_list(
            tracker, output_path, title="Test Adventure", sort_by_count=True
        )

        # Verify result
        assert isinstance(result, Success)
        assert result.unwrap() == 3  # Total entries written

        # Verify file was created
        assert output_path.exists()

        # Verify file contents
        content = output_path.read_text(encoding="utf-8")
        assert "# Generated content list for adventure: Test Adventure" in content
        assert "# Format: [Count] Name|Source" in content
        assert "3 Goblin|MM" in content
        assert "2 Fireball|PHB" in content
        assert "1 Orc|MM" in content

    def test_write_content_list_with_filter(self) -> None:
        """Test content list writing with content type filter."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 3},
            ],
            "spell": [
                {"name": "Fireball", "source": "PHB", "reference_count": 2},
            ],
        }

        output_path = self.temp_dir / "creatures_only.txt"

        result = self.writer.write_content_list(
            tracker, output_path, content_type_filter="creature", title="Test Adventure"
        )

        assert isinstance(result, Success)
        assert result.unwrap() == 1

        content = output_path.read_text(encoding="utf-8")
        assert "3 Goblin|MM" in content
        assert "Fireball" not in content

    def test_write_content_list_sort_by_name(self) -> None:
        """Test content list writing sorted by name."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Zebra", "source": "MM", "reference_count": 1},
                {"name": "Ant", "source": "MM", "reference_count": 2},
                {"name": "Bear", "source": "MM", "reference_count": 3},
            ],
        }

        output_path = self.temp_dir / "sorted_by_name.txt"

        result = self.writer.write_content_list(
            tracker,
            output_path,
            sort_by_count=False,  # Sort by name
        )

        assert isinstance(result, Success)

        content = output_path.read_text(encoding="utf-8")
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.startswith("#")
        ]

        # Should be sorted alphabetically
        assert lines[0] == "2 Ant|MM"
        assert lines[1] == "3 Bear|MM"
        assert lines[2] == "1 Zebra|MM"

    def test_write_content_list_sort_by_count(self) -> None:
        """Test content list writing sorted by count."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Low Count", "source": "MM", "reference_count": 1},
                {"name": "High Count", "source": "MM", "reference_count": 5},
                {"name": "Mid Count", "source": "MM", "reference_count": 3},
            ],
        }

        output_path = self.temp_dir / "sorted_by_count.txt"

        result = self.writer.write_content_list(
            tracker, output_path, sort_by_count=True
        )

        assert isinstance(result, Success)

        content = output_path.read_text(encoding="utf-8")
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.startswith("#")
        ]

        # Should be sorted by count (descending), then by name
        assert lines[0] == "5 High Count|MM"
        assert lines[1] == "3 Mid Count|MM"
        assert lines[2] == "1 Low Count|MM"

    def test_write_content_list_include_zero_counts(self) -> None:
        """Test content list writing with zero count inclusion."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Used Creature", "source": "MM", "reference_count": 2},
                {"name": "Unused Creature", "source": "MM", "reference_count": 0},
            ],
        }

        output_path = self.temp_dir / "with_zero_counts.txt"

        result = self.writer.write_content_list(
            tracker, output_path, include_zero_counts=True
        )

        assert isinstance(result, Success)
        assert result.unwrap() == 2

        content = output_path.read_text(encoding="utf-8")
        assert "2 Used Creature|MM" in content
        assert "0 Unused Creature|MM" in content

    def test_write_content_list_exclude_zero_counts(self) -> None:
        """Test content list writing with zero count exclusion (default)."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Used Creature", "source": "MM", "reference_count": 2},
                {"name": "Unused Creature", "source": "MM", "reference_count": 0},
            ],
        }

        output_path = self.temp_dir / "without_zero_counts.txt"

        result = self.writer.write_content_list(
            tracker, output_path, include_zero_counts=False
        )

        assert isinstance(result, Success)
        assert result.unwrap() == 1

        content = output_path.read_text(encoding="utf-8")
        assert "2 Used Creature|MM" in content
        assert "Unused Creature" not in content

    def test_write_content_list_missing_source(self) -> None:
        """Test content list writing with missing source information."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 2},
                {"name": "Custom Creature", "reference_count": 1},  # No source
            ],
        }

        output_path = self.temp_dir / "missing_source.txt"

        result = self.writer.write_content_list(tracker, output_path)

        assert isinstance(result, Success)
        assert result.unwrap() == 2

        content = output_path.read_text(encoding="utf-8")
        assert "2 Goblin|MM" in content
        assert "1 Custom Creature|Unknown" in content

    def test_write_content_list_empty_tracker(self) -> None:
        """Test content list writing with empty tracker."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {}

        output_path = self.temp_dir / "empty.txt"

        result = self.writer.write_content_list(
            tracker, output_path, title="Empty Adventure"
        )

        assert isinstance(result, Success)
        assert result.unwrap() == 0

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# Generated content list for adventure: Empty Adventure" in content
        assert "# No content entries found" in content

    def test_write_content_list_invalid_filter(self) -> None:
        """Test content list writing with invalid content type filter."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 2},
            ],
        }

        output_path = self.temp_dir / "invalid_filter.txt"

        result = self.writer.write_content_list(
            tracker, output_path, content_type_filter="nonexistent"
        )

        assert isinstance(result, Success)
        assert result.unwrap() == 0  # Empty file created

    def test_write_content_list_directory_creation(self) -> None:
        """Test content list writing creates necessary directories."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 2},
            ],
        }

        # Use nested directory that doesn't exist
        output_path = self.temp_dir / "subdir" / "nested" / "content.txt"

        result = self.writer.write_content_list(tracker, output_path)

        assert isinstance(result, Success)
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_write_content_list_file_error(self) -> None:
        """Test content list writing handles file I/O errors."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 2},
            ],
        }

        # Use invalid path (directory as file)
        output_path = self.temp_dir

        result = self.writer.write_content_list(tracker, output_path)

        assert isinstance(result, Error)
        assert isinstance(result.error, ContentListWriterError)
        assert "Failed to write content list" in str(result.error)

    def test_write_all_content_types_success(self) -> None:
        """Test writing all content types to separate files."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 3},
                {"name": "Orc", "source": "MM", "reference_count": 1},
            ],
            "spell": [
                {"name": "Fireball", "source": "PHB", "reference_count": 2},
            ],
            "item": [
                {"name": "Longsword", "source": "PHB", "reference_count": 1},
            ],
        }

        output_dir = self.temp_dir / "all_content"

        result = self.writer.write_all_content_types(
            tracker, output_dir, title="Test Adventure"
        )

        assert isinstance(result, Success)
        counts = result.unwrap()
        assert counts["creature"] == 2
        assert counts["spell"] == 1
        assert counts["item"] == 1

        # Verify individual files
        creature_file = output_dir / "creature.txt"
        spell_file = output_dir / "spell.txt"
        item_file = output_dir / "item.txt"

        assert creature_file.exists()
        assert spell_file.exists()
        assert item_file.exists()

        creature_content = creature_file.read_text(encoding="utf-8")
        assert "3 Goblin|MM" in creature_content
        assert "1 Orc|MM" in creature_content
        assert "Fireball" not in creature_content  # Not in creature file

    def test_write_all_content_types_empty_tracker(self) -> None:
        """Test writing all content types with empty tracker."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {}

        output_dir = self.temp_dir / "empty_all"

        result = self.writer.write_all_content_types(tracker, output_dir)

        assert isinstance(result, Success)
        counts = result.unwrap()
        assert counts == {}  # No files written

        # Directory should still be created
        assert output_dir.exists()

    def test_write_all_content_types_partial_failure(self) -> None:
        """Test writing all content types with partial failure."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 3},
            ],
        }

        # Create a directory that will cause write failure
        output_dir = self.temp_dir / "partial_fail"
        output_dir.mkdir()
        (output_dir / "creature.txt").mkdir()  # Create directory with same name as file

        result = self.writer.write_all_content_types(tracker, output_dir)

        assert isinstance(result, Error)
        assert isinstance(result.error, ContentListWriterError)

    @patch("studiorum.core.services.content_list_writer.datetime")
    def test_file_header_format(self, mock_datetime) -> None:
        """Test file header contains correct format and timestamp."""
        from datetime import datetime

        # Mock datetime to ensure consistent output
        mock_now = datetime(2025, 9, 15, 14, 30, 0)
        mock_datetime.now.return_value = mock_now

        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 1},
            ],
        }

        output_path = self.temp_dir / "header_test.txt"

        result = self.writer.write_content_list(
            tracker, output_path, title="Header Test Adventure"
        )

        assert isinstance(result, Success)

        content = output_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        assert (
            lines[0] == "# Generated content list for adventure: Header Test Adventure"
        )
        assert lines[1] == "# Format: [Count] Name|Source"
        assert lines[2] == "# Generated: 2025-09-15 14:30:00"
        assert lines[3] == "#"

    def test_file_header_no_title(self) -> None:
        """Test file header without title."""
        tracker = Mock(spec=ContentTracker)
        tracker.export_for_appendix.return_value = {
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 1},
            ],
        }

        output_path = self.temp_dir / "no_title.txt"

        result = self.writer.write_content_list(tracker, output_path)

        assert isinstance(result, Success)

        content = output_path.read_text(encoding="utf-8")
        assert "# Generated content list for content tracking session" in content
