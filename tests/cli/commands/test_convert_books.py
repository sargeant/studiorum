"""Tests for book conversion CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.loaders.omnidexer import Omnidexer


@pytest.mark.cli
class TestConvertBookCommand:
    """Test book conversion command."""

    def setup_method(self):
        """Set up test fixtures."""

        self.runner = CliRunner()
        self.mock_book_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1",
                    "entries": ["This is chapter 1 content."],
                }
            ]
        }

    @patch("studiorum.services.Services.load_omnidexer")
    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.adventure.render_latex")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    @pytest.mark.skip(reason="Test requires proper isolation from global container")
    def test_convert_book_with_file_path(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_engine_factory,
        mock_omnidexer,
        mock_shared_omnidexer,
    ):
        """Test converting book from file path."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies - create a mock that passes isinstance checks
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer_instance.source_manager = Mock()  # Add source_manager attribute
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_shared_omnidexer.return_value = (
            mock_omnidexer_instance  # Use same mock for shared module
        )

        # Mock LaTeX engine
        mock_engine_factory.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_book_data, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["convert", "book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

        finally:
            Path(file_path).unlink()

    @patch("studiorum.cli.commands.convert.adventure.render_latex")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_custom_options(
        self,
        mock_mkdir,
        mock_display,
        mock_engine_factory,
    ):
        """Test book conversion with custom options."""
        # Mock dependencies

        # Mock LaTeX engine
        mock_engine_factory.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_book_data, f)
            file_path = f.name

        try:
            # Test command with options
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "book",
                    file_path,
                    "--title",
                    "Custom Title",
                    "--images",
                    "--no-index",
                    "--output",
                    "custom_output.tex",
                ],
            )

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

        finally:
            Path(file_path).unlink()
