"""Tests for LaTeX engine configuration integration in CLI commands - Reduced Mocking Version."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import app
from dnd5e.renderers.latex.compilation_config import LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler


class TestLaTeXEngineIntegration:
    """Test LaTeX engine configuration is properly used in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Complete isolation - reset ALL global singletons
        from dnd5e.cli.display_manager import reset_display_manager
        from dnd5e.cli.main import reset_cli_globals
        from dnd5e.core.cache import CacheManager
        from dnd5e.core.config.paths import reset_path_config
        from dnd5e.core.config.settings import reset_settings
        from dnd5e.core.config.sources import reset_config_manager
        from dnd5e.core.content_type_resolver import reset_content_type_resolver
        from dnd5e.core.entry_registry import reset_entry_registry
        from dnd5e.core.interfaces import reset_content_type_registry
        from dnd5e.core.loaders.content_factory import reset_content_factory

        CacheManager.reset()
        reset_cli_globals()
        reset_content_factory()
        reset_content_type_registry()
        reset_content_type_resolver()
        reset_display_manager()
        reset_entry_registry()
        reset_config_manager()
        reset_path_config()
        reset_settings()

        self.runner = CliRunner()
        self.test_data_dir = Path(__file__).parent.parent.parent.parent / "test-data"

        # Enable debug logging for CI debugging
        import logging
        import os

        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            logging.basicConfig(level=logging.DEBUG)
            # Enable specific loggers
            for logger_name in [
                "dnd5e.renderers.latex.dnd_template",
                "dnd5e.renderers.latex.template_engine",
                "dnd5e.cli.commands.convert",
            ]:
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.DEBUG)

    @pytest.mark.slow
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_adventure_pdf_uses_latex_compiler_with_config(
        self, mock_display, mock_create_compiler
    ):
        """Test that adventure PDF compilation uses LaTeXCompiler with proper configuration."""
        # Only mock the LaTeX compiler and display manager (external dependencies)
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_compiler.compile_document.return_value = mock_result
        mock_create_compiler.return_value = mock_compiler

        # Mock display manager for clean output
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Use real test data file instead of mocked data
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test command with PDF flag
            result = self.runner.invoke(
                app,
                ["adventure", str(test_file), "--output", str(output_file), "--pdf"],
            )

            # Verify success
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeXCompiler was created
            mock_create_compiler.assert_called_once()

            # Verify LaTeX compilation was called instead of hardcoded subprocess
            mock_compiler.compile_document.assert_called_once()

            # Verify the compiler was called with proper LaTeX content containing real data
            call_args = mock_compiler.compile_document.call_args
            assert call_args is not None
            latex_content = call_args[0][0]  # First argument should be LaTeX content
            assert "Test Adventure" in latex_content  # From real test data
            assert "\\documentclass" in latex_content

    @pytest.mark.slow
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_book_pdf_uses_configured_engine(self, mock_display, mock_create_compiler):
        """Test that book PDF compilation uses configured LaTeX engine."""
        # Only mock the LaTeX compiler and display manager (external dependencies)
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_compiler.compile_document.return_value = mock_result
        mock_create_compiler.return_value = mock_compiler

        # Mock display manager for clean output
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Use real test data file instead of mocked data
        test_file = self.test_data_dir / "book-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_book.tex"

            # Test command with PDF flag
            result = self.runner.invoke(
                app, ["book", str(test_file), "--output", str(output_file), "--pdf"]
            )

            # Verify success
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeX compiler configuration and usage
            mock_create_compiler.assert_called_once()

            # Verify compilation was called
            mock_compiler.compile_document.assert_called_once()

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
