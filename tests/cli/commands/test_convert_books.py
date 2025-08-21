"""Tests for book conversion CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.text.tag_resolver import TagResolver
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestConvertBookCommand:
    """Test book conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

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

    @patch("studiorum.cli.commands.convert.book.get_omnidexer")
    @patch("studiorum.cli.commands.convert.book.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.book.create_latex_engine")
    @patch("studiorum.cli.commands.convert.book.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_file_path(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_engine_factory,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting book from file path."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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

    @patch("studiorum.cli.commands.convert.book.get_omnidexer")
    @patch("studiorum.cli.commands.convert.book.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.book.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    @patch("studiorum.cli.commands.convert.book.create_latex_engine")
    @patch("studiorum.cli.commands.convert.book.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_custom_options(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_engine_factory,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test book conversion with custom options."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "a5"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.two_column = False
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
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
