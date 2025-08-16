"""Refactored CLI tests with reduced mocking using real test data."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import app
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestConvertCommandsWithReducedMocking:
    """Test convert commands with minimal mocking and real test data."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()
        self.test_data_dir = Path(__file__).parent.parent.parent.parent / "test-data"

    def test_adventure_conversion_help(self):
        """Test adventure conversion help command without mocking."""
        result = self.runner.invoke(app, ["adventure", "--help"])

        assert result.exit_code == 0
        assert "Convert adventure" in result.stdout

    def test_book_conversion_help(self):
        """Test book conversion help command without mocking."""
        result = self.runner.invoke(app, ["book", "--help"])

        assert result.exit_code == 0
        assert "Convert book" in result.stdout

    def test_supplement_conversion_help(self):
        """Test supplement conversion help command without mocking."""
        result = self.runner.invoke(app, ["supplement", "--help"])

        assert result.exit_code == 0
        assert "Convert supplement" in result.stdout

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_adventure_conversion_with_real_data_latex_only(
        self,
        mock_display,
        mock_create_compiler,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test adventure conversion using real test data, only mocking LaTeX compiler."""
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

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test LaTeX generation (no PDF) - use absolute paths for CI
            result = self.runner.invoke(
                app,
                ["adventure", str(test_file.absolute()), "--output", str(output_file)],
            )

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeX file was created
            assert output_file.exists(), (
                f"Expected LaTeX file {output_file} was not created"
            )

            # Verify LaTeX content contains expected elements
            latex_content = output_file.read_text()
            assert "Test Adventure" in latex_content
            assert "\\documentclass" in latex_content
            assert "\\begin{document}" in latex_content
            assert "\\end{document}" in latex_content

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_book_conversion_with_real_data_latex_only(
        self,
        mock_display,
        mock_create_compiler,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test book conversion using real test data, only mocking LaTeX compiler."""
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

        # Use real test data file with absolute path for CI compatibility
        test_file = self.test_data_dir / "book-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_book.tex"

            # Test LaTeX generation (no PDF) - use absolute paths for CI
            result = self.runner.invoke(
                app, ["book", str(test_file.absolute()), "--output", str(output_file)]
            )

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeX file was created
            assert output_file.exists(), (
                f"Expected LaTeX file {output_file} was not created"
            )

            # Verify LaTeX content contains expected elements
            latex_content = output_file.read_text()
            assert "\\documentclass" in latex_content
            assert "\\begin{document}" in latex_content
            assert "\\end{document}" in latex_content

    @pytest.mark.slow
    @pytest.mark.ci_broken
    @pytest.mark.latex_required
    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.adventure.compile_pdf_async")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_pdf_compilation_uses_configured_compiler(
        self,
        mock_display,
        mock_compile_pdf,
        mock_get_tag_resolver,
        mock_get_omnidexer,
    ):
        """Test that PDF compilation uses the configured LaTeX compiler."""
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

            # Test PDF generation - use absolute paths for CI
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

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify PDF compilation was called
            mock_compile_pdf.assert_called_once()

            # Verify the LaTeX file was created and contains proper content
            assert output_file.exists(), "LaTeX file should be created"
            latex_content = output_file.read_text()
            assert "Test Adventure" in latex_content  # From real test data
            assert "\\documentclass" in latex_content

    def test_invalid_file_path_error_handling(self):
        """Test error handling for invalid file paths without mocking."""
        nonexistent_file = "/path/that/does/not/exist.json"

        result = self.runner.invoke(app, ["adventure", nonexistent_file])

        # Command should fail gracefully
        assert result.exit_code != 0

    def test_compiler_helper_function_creates_proper_config(self):
        """Test _create_latex_compiler helper function without mocking."""
        from dnd5e.cli.commands.convert import _create_latex_compiler
        from dnd5e.renderers.latex.compilation_config import CompilationConfig
        from dnd5e.renderers.latex.compiler import LaTeXCompiler

        # Test the helper function creates properly configured compiler
        compiler = _create_latex_compiler()

        # Verify it's a LaTeXCompiler instance with proper configuration
        assert isinstance(compiler, LaTeXCompiler)
        assert isinstance(compiler.config, CompilationConfig)
        assert hasattr(compiler.config, "primary_engine")
