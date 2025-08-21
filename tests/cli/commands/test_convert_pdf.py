"""Tests for PDF compilation functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from studiorum.cli.commands.convert.shared import compile_pdf as _compile_pdf


@pytest.mark.cli
class TestPDFCompilation:
    """Test PDF compilation functionality."""

    @pytest.mark.asyncio
    @patch("builtins.open")
    @patch("studiorum.cli.commands.convert.shared.create_latex_compiler")
    @patch("studiorum.cli.commands.convert.shared.display_manager")
    async def test_compile_pdf_success(
        self, mock_display, mock_create_latex_compiler, mock_builtin_open
    ):
        """Test successful PDF compilation."""
        # Mock file reading
        mock_file = Mock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock LaTeX compiler
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_result.warnings = []  # Add missing warnings attribute

        # For async methods, we need to return a coroutine
        async def mock_compile_document(*args, **kwargs):
            return mock_result

        mock_compiler.compile_document = mock_compile_document
        mock_create_latex_compiler.return_value = mock_compiler

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test compilation
        latex_path = Path("/tmp/test.tex")
        await _compile_pdf(latex_path)

        # Verify LaTeX compiler was used correctly
        mock_create_latex_compiler.assert_called_once()
        # Note: compile_document calls can't be easily asserted since we replaced it with an async function

    @pytest.mark.asyncio
    @patch("builtins.open")
    @patch("studiorum.cli.commands.convert.shared.create_latex_compiler")
    @patch("studiorum.cli.commands.convert.shared.display_manager")
    async def test_compile_pdf_failure(
        self, mock_display, mock_create_latex_compiler, mock_builtin_open
    ):
        """Test PDF compilation failure handling."""
        # Mock file reading
        mock_file = Mock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock failed LaTeX compiler
        mock_compiler = Mock()

        # For async methods, we need to return a coroutine that raises
        async def mock_failing_compile_document(*args, **kwargs):
            raise Exception("LaTeX error")

        mock_compiler.compile_document = mock_failing_compile_document
        mock_create_latex_compiler.return_value = mock_compiler

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test compilation - should raise typer.Exit on failure
        latex_path = Path("/tmp/test.tex")
        with pytest.raises(typer.Exit):
            await _compile_pdf(latex_path)

        # Verify LaTeX compiler was called
        mock_create_latex_compiler.assert_called_once()

    @pytest.mark.asyncio
    @patch("builtins.open")
    @patch("studiorum.cli.commands.convert.shared.create_latex_compiler")
    @patch("studiorum.cli.commands.convert.shared.display_manager")
    async def test_compile_pdf_latex_not_found(
        self, mock_display, mock_create_latex_compiler, mock_builtin_open
    ):
        """Test handling when LaTeX engine is not installed."""
        # Mock file reading
        mock_file = Mock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock FileNotFoundError (LaTeX engine not found)
        mock_compiler = Mock()

        # For async methods, we need to return a coroutine that raises
        async def mock_failing_compile_document(*args, **kwargs):
            raise FileNotFoundError("lualatex not found")

        mock_compiler.compile_document = mock_failing_compile_document
        mock_create_latex_compiler.return_value = mock_compiler

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test compilation - should raise typer.Exit on failure
        latex_path = Path("/tmp/test.tex")
        with pytest.raises(typer.Exit):
            await _compile_pdf(latex_path)

        # Verify LaTeX compiler was called
        mock_create_latex_compiler.assert_called_once()
