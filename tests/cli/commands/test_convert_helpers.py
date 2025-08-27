"""Tests for error handling and special cases in CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.books import Book
from studiorum.core.models.content import Source
from studiorum.core.text.tag_resolver import TagResolver
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestErrorHandlingPaths:
    """Test error handling in various scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
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

    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.adventure.create_latex_engine")
    @patch("builtins.open")
    def test_renderer_exception(
        self, mock_builtin_open, mock_engine_factory, mock_tag_resolver, mock_omnidexer
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

        # Mock engine to raise exception
        mock_engine = Mock()
        mock_engine.render_document.side_effect = Exception("Renderer error")
        mock_engine_factory.return_value = mock_engine

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

    @patch("studiorum.cli.commands.convert.book.get_omnidexer")
    @patch("studiorum.cli.commands.convert.shared.get_omnidexer")
    @patch("studiorum.cli.commands.convert.book.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    @patch("studiorum.cli.commands.convert.book.create_latex_engine")
    @patch("studiorum.cli.commands.convert.book.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    @pytest.mark.skip(reason="Test requires proper isolation from global container")
    def test_phb_abbreviation_fallback(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_engine_factory,
        mock_user_config,
        mock_app_config,
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
        mock_omnidexer_instance.get_all_by_type.return_value = []  # Return empty list for any content type
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_shared_omnidexer.return_value = (
            mock_omnidexer_instance  # Use same mock instance
        )
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = False
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock LaTeX engine
        mock_engine = Mock()
        mock_engine.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_engine_factory.return_value = mock_engine

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
