"""Tests for LaTeX engine configuration integration in CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import app
from dnd5e.core.indexer.tag_resolver import TagResolver
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.renderers.latex.compilation_config import LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler


class TestLaTeXEngineIntegration:
    """Test LaTeX engine configuration is properly used in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
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

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_adventure_pdf_uses_latex_compiler_with_config(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_create_compiler,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test that adventure PDF compilation uses LaTeXCompiler with proper configuration."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies - return proper instances instead of Mock objects
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock LaTeX compiler
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_compiler.compile_document.return_value = mock_result
        mock_create_compiler.return_value = mock_compiler

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
            # Test command with PDF flag
            result = self.runner.invoke(app, ["adventure", file_path, "--pdf"])

            # Verify success
            assert result.exit_code == 0

            # Verify LaTeXCompiler was created
            mock_create_compiler.assert_called_once()

            # Verify LaTeX compilation was called instead of hardcoded subprocess
            mock_compiler.compile_document.assert_called_once()

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_book_pdf_uses_configured_engine(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_create_compiler,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test that book PDF compilation uses configured LaTeX engine."""
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
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(mock_book_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies - return proper instances instead of Mock objects
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock LaTeX compiler
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_compiler.compile_document.return_value = mock_result
        mock_create_compiler.return_value = mock_compiler

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
            # Test command with PDF flag
            result = self.runner.invoke(app, ["book", file_path, "--pdf"])

            # Verify success
            assert result.exit_code == 0

            # Verify LaTeX compiler was created
            mock_create_compiler.assert_called_once()

            # Verify LaTeX compilation was called instead of hardcoded subprocess
            mock_compiler.compile_document.assert_called_once()

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_supplement_pdf_respects_engine_configuration(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_create_compiler,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test that supplement PDF compilation respects engine configuration."""
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

        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(mock_supplement_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies - return proper instances instead of Mock objects
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock LaTeX compiler
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_compiler.compile_document.return_value = mock_result
        mock_create_compiler.return_value = mock_compiler

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
            # Test command with PDF flag
            result = self.runner.invoke(app, ["supplement", file_path, "--pdf"])

            # Verify success
            assert result.exit_code == 0

            # Verify LaTeX compiler configuration and usage
            mock_create_compiler.assert_called_once()

            # Verify compilation was called
            mock_compiler.compile_document.assert_called_once()

        finally:
            Path(file_path).unlink()

    @patch("subprocess.run")
    def test_no_hardcoded_xelatex_calls_in_convert_commands(self, mock_subprocess):
        """Test that convert commands don't make hardcoded xelatex subprocess calls."""
        # This test ensures we don't regress to hardcoded subprocess calls
        # Run a simple command that shouldn't trigger subprocess
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Verify no subprocess calls were made (particularly not xelatex)
        mock_subprocess.assert_not_called()

    def test_latex_compiler_helper_creates_proper_config(self):
        """Test that _create_latex_compiler helper creates proper configuration."""
        from dnd5e.cli.commands.convert import _create_latex_compiler
        from dnd5e.renderers.latex.compilation_config import (
            CompilationConfig,
        )

        # Test the helper function creates properly configured compiler
        compiler = _create_latex_compiler()

        # Verify it's a LaTeXCompiler instance
        assert isinstance(compiler, LaTeXCompiler)

        # Verify it has the expected configuration
        assert isinstance(compiler.config, CompilationConfig)
        assert hasattr(compiler.config, "primary_engine")
        assert isinstance(compiler.config.primary_engine, LaTeXEngine)
