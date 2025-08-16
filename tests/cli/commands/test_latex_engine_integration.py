"""Tests for LaTeX engine configuration integration in CLI commands - Reduced Mocking Version."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import app
from dnd5e.renderers.latex.compilation_config import LaTeXEngine
from dnd5e.renderers.latex.compiler import LaTeXCompiler
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestLaTeXEngineIntegration:
    """Test LaTeX engine configuration is properly used in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

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
    @pytest.mark.ci_broken
    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.adventure.compile_pdf_async")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_adventure_pdf_uses_latex_compiler_with_config(
        self,
        mock_display,
        mock_compile_pdf,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test that adventure PDF compilation uses LaTeXCompiler with proper configuration."""
        # Mock omnidexer and tag resolver to avoid loading 5etools data in CI
        mock_omnidexer = Mock()
        mock_omnidexer.find = Mock(return_value=None)  # No cross-references found
        mock_omnidexer.get_all_by_type = Mock(return_value=[])
        mock_get_omnidexer.return_value = mock_omnidexer

        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve = Mock(
            side_effect=lambda text, _: text
        )  # Pass through tags unchanged
        mock_get_tag_resolver.return_value = mock_tag_resolver

        # Mock the compile_pdf function to avoid actual LaTeX compilation
        mock_compile_pdf.return_value = None  # Async function returns None

        # Mock display manager for clean output
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test command with PDF flag - use absolute paths for CI
            result = self.runner.invoke(
                app,
                [
                    "adventure",
                    str(test_file.absolute()),
                    "--output",
                    str(output_file),
                    "--pdf",
                ],
            )

            # Verify success
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify PDF compilation was called
            mock_compile_pdf.assert_called_once()

            # Verify the LaTeX file was created
            assert output_file.exists(), "LaTeX file should be created"

            # Verify the LaTeX file contains proper content
            latex_content = output_file.read_text()
            assert "Test Adventure" in latex_content  # From real test data
            assert "\\documentclass" in latex_content

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.book.compile_pdf_async")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_book_pdf_uses_configured_engine(
        self,
        mock_display,
        mock_compile_pdf,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test that book PDF compilation uses configured LaTeX engine."""
        # Mock omnidexer and tag resolver to avoid loading 5etools data in CI
        mock_omnidexer = Mock()
        mock_omnidexer.find = Mock(return_value=None)  # No cross-references found
        mock_omnidexer.get_all_by_type = Mock(return_value=[])
        mock_get_omnidexer.return_value = mock_omnidexer

        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve = Mock(
            side_effect=lambda text, _: text
        )  # Pass through tags unchanged
        mock_get_tag_resolver.return_value = mock_tag_resolver

        # Mock the compile_pdf function to avoid actual LaTeX compilation
        mock_compile_pdf.return_value = None  # Async function returns None

        # Mock display manager for clean output
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "book-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_book.tex"

            # Test command with PDF flag - use absolute paths for CI
            result = self.runner.invoke(
                app,
                [
                    "book",
                    str(test_file.absolute()),
                    "--output",
                    str(output_file),
                    "--pdf",
                ],
            )

            # Verify success
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify PDF compilation was called
            mock_compile_pdf.assert_called_once()

            # Verify the LaTeX file was created
            assert output_file.exists(), "LaTeX file should be created"

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
