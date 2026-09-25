"""Tests for compiling the .tex file a convert command wrote."""

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from studiorum.cli.commands.convert.run import compile_pdf
from studiorum.core.result import Error, Success


@pytest.fixture
def tex_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.tex"
    path.write_text("\\documentclass{article}\\begin{document}Test\\end{document}")
    return path


@pytest.mark.cli
class TestCompilePdf:
    def test_compiles_with_the_configured_engines(self, tex_file: Path, capsys):
        with patch(
            "studiorum.cli.commands.convert.run.build_pdf",
            return_value=Success(tex_file.with_suffix(".pdf")),
        ) as build:
            compile_pdf(tex_file)

        path, engines = build.call_args.args
        assert path == tex_file
        assert engines.primary_engine in {"xelatex", "lualatex", "pdflatex"}
        assert "PDF compiled" in capsys.readouterr().out

    def test_failure_prints_the_summary_and_exits(self, tex_file: Path, capsys):
        with (
            patch(
                "studiorum.cli.commands.convert.run.build_pdf",
                return_value=Error(
                    "xelatex: ./test.tex:3: Undefined control sequence."
                ),
            ),
            pytest.raises(typer.Exit),
        ):
            compile_pdf(tex_file)

        assert "Undefined control sequence" in capsys.readouterr().out
