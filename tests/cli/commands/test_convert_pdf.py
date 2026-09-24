"""Tests for compiling the .tex file a convert command wrote."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import typer

from studiorum.cli.commands.convert.run import compile_pdf


@pytest.fixture
def tex_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.tex"
    path.write_text("\\documentclass{article}\\begin{document}Test\\end{document}")
    return path


def compiler_returning(result: object = None, error: Exception | None = None) -> Mock:
    compiler = Mock()
    compiler.compile_document = AsyncMock(return_value=result, side_effect=error)
    return compiler


@pytest.mark.cli
@pytest.mark.asyncio
class TestCompilePdf:
    async def test_success_compiles_the_file_next_to_itself(self, tex_file: Path):
        result = Mock(success=True, warnings=[], error_message=None)
        compiler = compiler_returning(result)
        with patch(
            "studiorum.cli.commands.convert.run.create_latex_compiler",
            return_value=compiler,
        ):
            await compile_pdf(tex_file)

        compiler.compile_document.assert_awaited_once()
        kwargs = compiler.compile_document.call_args.kwargs
        assert kwargs == {"output_name": "test", "working_dir": tex_file.parent}

    async def test_failed_compilation_exits(self, tex_file: Path):
        result = Mock(success=False, warnings=[], error_message="LaTeX error")
        with (
            patch(
                "studiorum.cli.commands.convert.run.create_latex_compiler",
                return_value=compiler_returning(result),
            ),
            pytest.raises(typer.Exit),
        ):
            await compile_pdf(tex_file)

    async def test_missing_latex_engine_exits(self, tex_file: Path):
        compiler = compiler_returning(error=FileNotFoundError("lualatex not found"))
        with (
            patch(
                "studiorum.cli.commands.convert.run.create_latex_compiler",
                return_value=compiler,
            ),
            pytest.raises(typer.Exit),
        ):
            await compile_pdf(tex_file)
