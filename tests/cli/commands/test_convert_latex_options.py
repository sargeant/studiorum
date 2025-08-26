"""Tests for LaTeX document options in CLI commands."""

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
class TestLaTeXDocumentOptions:
    """Test LaTeX document class options in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()
        self.mock_adventure_data = {
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

    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    @patch("studiorum.cli.commands.convert.adventure.create_latex_engine")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_adventure_with_latex_options(
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
        """Test adventure command with LaTeX document options."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "10pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
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
            json.dump(self.mock_adventure_data, f)
            file_path = f.name

        try:
            # Test command with LaTeX options
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "adventure",
                    file_path,
                    "--document-class",
                    "dndarticle",
                    "--paper",
                    "a4",
                    "--font-size",
                    "12pt",
                    "--background",
                    "print",
                    "--high-contrast",
                    "--one-column",
                    "--not-justified",
                ],
            )

            # Verify success
            assert result.exit_code == 0
            assert "Adventure converted" in result.stdout

            # Verify engine was called with context containing latex_config
            mock_engine.render_document.assert_called_once()
            call_args = mock_engine.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            # Verify latex_config was passed and has correct values
            latex_config = context.metadata.get("latex_config")
            assert latex_config is not None
            assert latex_config.document.document_class == "dndarticle"
            assert latex_config.document.paper_size == "a4"
            assert latex_config.document.font_size == "12pt"
            assert latex_config.document.background == "print"
            assert latex_config.document.high_contrast is True
            assert latex_config.document.two_column is False
            assert latex_config.document.justified_text is False

        finally:
            Path(file_path).unlink()

    @patch("studiorum.cli.commands.convert.book.get_omnidexer")
    @patch("studiorum.cli.commands.convert.book.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.get_app_config")
    @patch("studiorum.core.config.sources.get_content_config")
    @patch("studiorum.cli.commands.convert.book.create_latex_engine")
    @patch("studiorum.cli.commands.convert.book.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_book_with_default_latex_options(
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
        """Test book command with default LaTeX options."""
        # Mock book data
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

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer_instance.get_all_by_type.return_value = []  # Return empty list for any content type
        mock_omnidexer.return_value = mock_omnidexer_instance
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
            # Test command with default options
            result = self.runner.invoke(app, ["convert", "book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

            # Verify default LaTeX config values
            mock_engine.render_document.assert_called_once()
            call_args = mock_engine.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            latex_config = context.metadata.get("latex_config")
            assert latex_config is not None
            assert latex_config.document.document_class == "dndbook"
            assert latex_config.document.paper_size == "letter"  # default from settings
            assert latex_config.document.font_size == "11pt"
            assert latex_config.document.background == "full"  # new default background
            assert latex_config.document.two_column is True
            assert latex_config.document.justified_text is False

        finally:
            Path(file_path).unlink()

    @patch("studiorum.cli.commands.convert.supplement.get_omnidexer")
    @patch("studiorum.cli.commands.convert.supplement.get_tag_resolver")
    @patch("studiorum.cli.commands.convert.supplement.create_latex_engine")
    @patch("studiorum.cli.commands.convert.supplement.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    @patch("studiorum.core.config.sources.get_content_config")
    @patch(
        "studiorum.cli.commands.convert.base.BaseConvertCommand.apply_config_hierarchy"
    )
    def test_supplement_with_paper_size_from_settings(
        self,
        mock_apply_config_hierarchy,
        mock_get_content_config,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_engine_factory,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test supplement command uses paper size from settings when not specified."""
        # Mock supplement data
        mock_supplement_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "level": 1,
                    "school": "A",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Test spell description"],
                }
            ]
        }

        # Mock apply_config_hierarchy to return config with custom paper size
        mock_config_dict = {
            "paper_size": "a5",
            "fonts": None,
            "background": "full",
            "high_contrast": False,
            "font_size": "11pt",
            "two_column": False,
            "justified": False,
            "no_outline": False,
        }
        mock_apply_config_hierarchy.return_value = mock_config_dict

        # Mock user config (should return None values to test fallback to app config)
        mock_user_config = Mock()
        mock_user_config.latex.paper_size = None
        mock_user_config.latex.fonts = None
        mock_user_config.latex.no_outline = None
        mock_user_config.latex.background = None
        mock_user_config.latex.high_contrast = None
        mock_user_config.latex.font_size = None
        mock_user_config.latex.two_column = None
        mock_user_config.latex.justified = None
        mock_get_content_config.return_value = mock_user_config

        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(mock_supplement_data)
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
            json.dump(mock_supplement_data, f)
            file_path = f.name

        try:
            # Test command without --paper flag
            result = self.runner.invoke(app, ["convert", "supplement", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Supplement converted" in result.stdout

            # Verify settings paper size was used
            mock_engine.render_document.assert_called_once()
            call_args = mock_engine.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            latex_config = context.metadata.get("latex_config")
            assert latex_config is not None
            assert latex_config.document.paper_size == "a5"

        finally:
            Path(file_path).unlink()
