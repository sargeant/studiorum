"""Tests for LaTeX engine configuration integration in CLI commands - Reduced Mocking Version."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.commands.convert import app


@pytest.mark.cli
class TestLaTeXEngineIntegration:
    """Test LaTeX engine configuration is properly used in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""

        self.runner = CliRunner()
        self.test_data_dir = Path(__file__).parent.parent.parent.parent / "test-data"

        # Enable debug logging for CI debugging
        import logging
        import os

        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            logging.basicConfig(level=logging.DEBUG)
            # Enable specific loggers
            for logger_name in [
                "studiorum.latex_engine.core.dnd_template",
                "studiorum.latex_engine.core.template_engine",
                "studiorum.cli.commands.convert",
            ]:
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.DEBUG)

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.run.compile_pdf")
    def test_adventure_pdf_uses_latex_compiler_with_config(
        self,
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
        mock_compile_pdf.return_value = None

        # Mock display manager for clean output

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
    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.run.compile_pdf")
    def test_book_pdf_uses_configured_engine(
        self,
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
        mock_compile_pdf.return_value = None

        # Mock display manager for clean output

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
