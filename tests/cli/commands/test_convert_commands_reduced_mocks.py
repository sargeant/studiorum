"""Refactored CLI tests with reduced mocking using real test data."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import app


class TestConvertCommandsWithReducedMocking:
    """Test convert commands with minimal mocking and real test data."""

    def setup_method(self):
        """Set up test fixtures."""
        # Complete isolation using service container pattern
        from dnd5e.cli.main import reset_cli_globals
        from dnd5e.core.cache import CacheManager
        from dnd5e.core.container import reset_global_container

        # Reset the service container (handles most singletons now)
        reset_global_container()

        # Reset remaining legacy global state
        CacheManager.reset()
        reset_cli_globals()

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
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_adventure_conversion_with_real_data_latex_only(
        self, mock_display, mock_create_compiler
    ):
        """Test adventure conversion using real test data, only mocking LaTeX compiler."""
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

        # Use real test data file
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test LaTeX generation (no PDF)
            result = self.runner.invoke(
                app, ["adventure", str(test_file), "--output", str(output_file)]
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
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_book_conversion_with_real_data_latex_only(
        self, mock_display, mock_create_compiler
    ):
        """Test book conversion using real test data, only mocking LaTeX compiler."""
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

        # Use real test data file
        test_file = self.test_data_dir / "book-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_book.tex"

            # Test LaTeX generation (no PDF)
            result = self.runner.invoke(
                app, ["book", str(test_file), "--output", str(output_file)]
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
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_pdf_compilation_uses_configured_compiler(
        self, mock_display, mock_create_compiler
    ):
        """Test that PDF compilation uses the configured LaTeX compiler."""
        # Mock the LaTeX compiler to verify it's called correctly
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

        # Use real test data file
        test_file = self.test_data_dir / "adventure-example.json"
        assert test_file.exists(), f"Test data file {test_file} not found"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_adventure.tex"

            # Test PDF generation
            result = self.runner.invoke(
                app,
                ["adventure", str(test_file), "--output", str(output_file), "--pdf"],
            )

            # Verify command executed successfully
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify LaTeX compiler was created and used
            mock_create_compiler.assert_called_once()
            mock_compiler.compile_document.assert_called_once()

            # Verify the compiler was called with proper LaTeX content
            call_args = mock_compiler.compile_document.call_args
            assert call_args is not None
            latex_content = call_args[0][0]  # First argument should be LaTeX content
            assert "Test Adventure" in latex_content
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
