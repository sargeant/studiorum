"""Tests for error handling and special cases in CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.main import app
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.books import Book
from dnd5e.core.models.content import Source
from dnd5e.core.text.tag_resolver import TagResolver
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestErrorHandlingPaths:
    """Test error handling in various scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    @patch("dnd5e.cli.commands.convert.adventure.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.adventure.get_tag_resolver")
    @patch("builtins.open")
    def test_json_decode_error(
        self, mock_builtin_open, mock_tag_resolver, mock_omnidexer
    ):
        """Test handling of invalid JSON files."""
        # Mock file operations - invalid JSON
        mock_file = Mock()
        mock_file.read.return_value = "invalid json content {"
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["convert", "adventure", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.adventure.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.adventure.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.adventure.LaTeXDocumentRenderer")
    @patch("builtins.open")
    def test_renderer_exception(
        self, mock_builtin_open, mock_renderer_class, mock_tag_resolver, mock_omnidexer
    ):
        """Test handling of renderer exceptions."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(
            {
                "adventure": [
                    {
                        "name": "Test Adventure",
                        "source": {"abbreviation": "TEST", "name": "Test Source"},
                        "id": "test",
                        "metadata": {},
                        "published": None,
                        "author": None,
                        "cover": None,
                        "contents": [],
                    }
                ]
            }
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock renderer to raise exception
        mock_renderer = Mock()
        mock_renderer.render_document.side_effect = Exception("Renderer error")
        mock_renderer_class.return_value = mock_renderer

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "data"}, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["convert", "adventure", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()


@pytest.mark.cli
class TestSpecialCases:
    """Test special cases and edge conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    @patch("dnd5e.cli.commands.convert.book.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.shared.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.book.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.book.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.book.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_phb_abbreviation_fallback(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_shared_omnidexer,
        mock_omnidexer,
    ):
        """Test PHB abbreviation fallback to content resolver."""
        # Mock book data for file loading
        mock_book_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1",
                    "entries": ["This is chapter 1 content."],
                }
            ]
        }

        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies - use proper mocks instead of real instances
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        # Add the missing source_manager attribute
        mock_omnidexer_instance.source_manager = Mock()
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_shared_omnidexer.return_value = (
            mock_omnidexer_instance  # Use same mock instance
        )
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(mock_book_data, f)
            file_path = f.name

        try:
            # Test command with file path instead of abbreviation
            result = self.runner.invoke(app, ["convert", "book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

        finally:
            Path(file_path).unlink()
