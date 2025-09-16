"""Tests for adventure content output features."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestAdventureContentOutput:
    """Test adventure content output functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_adventure_file(self) -> Path:
        """Create a test adventure JSON file."""
        adventure_data = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [
                {
                    "name": "Chapter 1",
                    "entries": [
                        "This is the first chapter.",
                        {
                            "type": "statblock",
                            "data": {
                                "name": "Goblin",
                                "source": "MM",
                                "type": "humanoid",
                            },
                        },
                        "More adventure text.",
                    ],
                }
            ],
        }

        file_path = self.temp_dir / "test_adventure.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(adventure_data, f)

        return file_path

    def create_mock_content_tracker(self):
        """Create a mock content tracker with test data."""
        mock_tracker = Mock()

        # Mock export data for ContentListWriter
        mock_tracker.export_for_appendix.return_value = {
            "spell": [
                {"name": "Fireball", "source": "PHB", "reference_count": 3},
                {"name": "Magic Missile", "source": "PHB", "reference_count": 2},
            ],
            "creature": [
                {"name": "Goblin", "source": "MM", "reference_count": 5},
                {"name": "Orc", "source": "MM", "reference_count": 1},
            ],
            "item": [
                {"name": "Longsword", "source": "PHB", "reference_count": 2},
            ],
        }

        return mock_tracker

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_spells_option(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test --output-spells option in adventure conversion."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter
        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(
            unwrap=lambda: 2
        )  # Success with 2 entries
        mock_get_writer.return_value = mock_writer

        # Mock template rendering
        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            # Mock ContentTracker creation and tracking
            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = self.create_mock_content_tracker()
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                spells_output = self.temp_dir / "spells.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--output-spells",
                        str(spells_output),
                    ],
                )

                assert result.exit_code == 0

                # Verify ContentListWriter was called for spells
                mock_writer.write_content_list.assert_called_once()
                call_args = mock_writer.write_content_list.call_args
                assert call_args[0][1] == spells_output  # output_path
                assert call_args[1]["content_type_filter"] == "spell"
                assert call_args[1]["title"] == "Test Adventure"

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_creatures_option(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test --output-creatures option in adventure conversion."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter
        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(
            unwrap=lambda: 2
        )  # Success with 2 entries
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = self.create_mock_content_tracker()
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                creatures_output = self.temp_dir / "creatures.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--output-creatures",
                        str(creatures_output),
                    ],
                )

                assert result.exit_code == 0

                # Verify ContentListWriter was called for creatures
                mock_writer.write_content_list.assert_called_once()
                call_args = mock_writer.write_content_list.call_args
                assert call_args[0][1] == creatures_output  # output_path
                assert call_args[1]["content_type_filter"] == "creature"

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_items_option(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test --output-items option in adventure conversion."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter
        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(
            unwrap=lambda: 1
        )  # Success with 1 entry
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = self.create_mock_content_tracker()
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                items_output = self.temp_dir / "items.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--output-items",
                        str(items_output),
                    ],
                )

                assert result.exit_code == 0

                # Verify ContentListWriter was called for items
                mock_writer.write_content_list.assert_called_once()
                call_args = mock_writer.write_content_list.call_args
                assert call_args[0][1] == items_output  # output_path
                assert call_args[1]["content_type_filter"] == "item"

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_all_content_types(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test outputting all content types in single command."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter
        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(unwrap=lambda: 2)  # Success
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = self.create_mock_content_tracker()
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                spells_output = self.temp_dir / "spells.txt"
                creatures_output = self.temp_dir / "creatures.txt"
                items_output = self.temp_dir / "items.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--output-spells",
                        str(spells_output),
                        "--output-creatures",
                        str(creatures_output),
                        "--output-items",
                        str(items_output),
                    ],
                )

                assert result.exit_code == 0

                # Verify ContentListWriter was called 3 times (once for each content type)
                assert mock_writer.write_content_list.call_count == 3

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_with_custom_title(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test content output with custom adventure title."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter
        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(unwrap=lambda: 2)  # Success
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = self.create_mock_content_tracker()
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                spells_output = self.temp_dir / "spells.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--title",
                        "Custom Adventure Title",
                        "--output-spells",
                        str(spells_output),
                    ],
                )

                assert result.exit_code == 0

                # Verify custom title was used
                call_args = mock_writer.write_content_list.call_args
                assert call_args[1]["title"] == "Custom Adventure Title"

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_content_list_error(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test error handling when content list writing fails."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter to return error
        from studiorum.core.result import Error
        from studiorum.core.services.content_list_writer import ContentListWriterError

        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Error(
            ContentListWriterError("Write failed")
        )
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = self.create_mock_content_tracker()
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                spells_output = self.temp_dir / "spells.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--output-spells",
                        str(spells_output),
                    ],
                )

                # Should still succeed with main conversion, but show warning about content list
                assert result.exit_code == 0
                assert "Warning" in result.stdout or "Failed" in result.stdout

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_output_empty_content_tracker(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test content output when content tracker is empty."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter
        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(
            unwrap=lambda: 0
        )  # Success but empty
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.TemplateService"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                # Empty content tracker
                mock_tracker = Mock()
                mock_tracker.export_for_appendix.return_value = {}
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_test_adventure_file()
                output_file = self.temp_dir / "adventure.tex"
                spells_output = self.temp_dir / "spells.txt"

                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file),
                        "--output-spells",
                        str(spells_output),
                    ],
                )

                assert result.exit_code == 0

                # Should still call ContentListWriter (which will create empty file)
                mock_writer.write_content_list.assert_called_once()

    def test_adventure_output_directory_creation(self):
        """Test that output directories are created automatically."""
        with patch(
            "studiorum.cli.commands.convert.adventure.get_content_list_writer"
        ) as mock_get_writer:
            with patch(
                "studiorum.cli.commands.convert.adventure.get_omnidexer"
            ) as mock_get_omnidexer:
                with patch(
                    "studiorum.cli.commands.convert.adventure.get_tag_resolver"
                ) as mock_tag_resolver:
                    # Setup mocks
                    mock_omnidexer = Mock()
                    mock_omnidexer.get_adventure.return_value = {
                        "name": "Test Adventure",
                        "source": "TEST",
                        "data": [],
                    }
                    mock_get_omnidexer.return_value = mock_omnidexer
                    mock_tag_resolver.return_value = Mock()

                    # Mock ContentListWriter
                    mock_writer = Mock()
                    mock_writer.write_content_list.return_value = Mock(unwrap=lambda: 1)
                    mock_get_writer.return_value = mock_writer

                    with patch(
                        "studiorum.cli.commands.convert.adventure.TemplateService"
                    ) as mock_template:
                        mock_template.return_value.render.return_value = (
                            "Mock LaTeX output"
                        )

                        with patch(
                            "studiorum.cli.commands.convert.adventure.ContentTracker"
                        ) as mock_tracker_class:
                            mock_tracker = self.create_mock_content_tracker()
                            mock_tracker_class.return_value = mock_tracker

                            adventure_file = self.create_test_adventure_file()
                            output_file = self.temp_dir / "adventure.tex"

                            # Use nested directory that doesn't exist
                            spells_output = (
                                self.temp_dir / "output" / "lists" / "spells.txt"
                            )

                            result = self.runner.invoke(
                                app,
                                [
                                    "convert",
                                    "adventure",
                                    str(adventure_file),
                                    "--output",
                                    str(output_file),
                                    "--output-spells",
                                    str(spells_output),
                                ],
                            )

                            assert result.exit_code == 0

                            # Verify the path was passed to ContentListWriter
                            # (ContentListWriter itself handles directory creation)
                            call_args = mock_writer.write_content_list.call_args
                            assert call_args[0][1] == spells_output

    def test_adventure_no_content_output_options(self):
        """Test adventure conversion without any content output options (normal behavior)."""
        with patch(
            "studiorum.cli.commands.convert.adventure.get_content_list_writer"
        ) as mock_get_writer:
            with patch(
                "studiorum.cli.commands.convert.adventure.get_omnidexer"
            ) as mock_get_omnidexer:
                with patch(
                    "studiorum.cli.commands.convert.adventure.get_tag_resolver"
                ) as mock_tag_resolver:
                    # Setup mocks
                    mock_omnidexer = Mock()
                    mock_omnidexer.get_adventure.return_value = {
                        "name": "Test Adventure",
                        "source": "TEST",
                        "data": [],
                    }
                    mock_get_omnidexer.return_value = mock_omnidexer
                    mock_tag_resolver.return_value = Mock()

                    # Mock ContentListWriter (should not be called)
                    mock_writer = Mock()
                    mock_get_writer.return_value = mock_writer

                    with patch(
                        "studiorum.cli.commands.convert.adventure.TemplateService"
                    ) as mock_template:
                        mock_template.return_value.render.return_value = (
                            "Mock LaTeX output"
                        )

                        with patch(
                            "studiorum.cli.commands.convert.adventure.ContentTracker"
                        ) as mock_tracker_class:
                            mock_tracker = self.create_mock_content_tracker()
                            mock_tracker_class.return_value = mock_tracker

                            adventure_file = self.create_test_adventure_file()
                            output_file = self.temp_dir / "adventure.tex"

                            result = self.runner.invoke(
                                app,
                                [
                                    "convert",
                                    "adventure",
                                    str(adventure_file),
                                    "--output",
                                    str(output_file),
                                ],
                            )

                            assert result.exit_code == 0

                            # ContentListWriter should not have been called
                            mock_writer.write_content_list.assert_not_called()
