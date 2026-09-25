"""latexmk compilation and the log summary."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from studiorum.core.config.unified_config import LaTeXEngineConfig
from studiorum.core.result import Error, Success
from studiorum.latex_engine.latexmk import build_pdf, summarise_log

MISSING_CLASS = """\
(./doc.tex
LaTeX2e <2025-06-01>
./doc.tex:1: LaTeX Error: File `dndbook.cls' not found.

Type X to quit or <RETURN> to proceed,
or enter new name. (Default extension: cls)

Enter file name:
./doc.tex:1: Emergency stop.
<read *>
"""

UNDEFINED = """\
./doc.tex:12: Undefined control sequence.
l.12 \\DndNoSuchMacro
                    {x}
"""


def test_summary_names_the_error_and_hints_at_the_class(tmp_path: Path) -> None:
    log = tmp_path / "doc.log"
    log.write_text(MISSING_CLASS)

    summary = summarise_log(log)

    assert summary.startswith("./doc.tex:1: LaTeX Error: File `dndbook.cls' not found.")
    assert "Hint: Install the DND 5e LaTeX template" in summary
    assert str(log) in summary


def test_summary_shows_the_source_line(tmp_path: Path) -> None:
    log = tmp_path / "doc.log"
    log.write_text(UNDEFINED)

    summary = summarise_log(log)

    assert "l.12 \\DndNoSuchMacro" in summary
    assert "Hint: A macro is undefined" in summary


def test_summary_reads_a_message_tex_wrapped(tmp_path: Path) -> None:
    line = "/texmf/tex/latex/fontspec/fontspec.sty:101: Fatal Package fontspec Error: The fontspec package requires either XeTeX or"
    log = tmp_path / "doc.log"
    log.write_text(f"{line[:79]}\n{line[79:]}\n(fontspec) LuaTeX.\n")

    summary = summarise_log(log)

    assert summary.startswith(line)
    assert "Hint: The template's fonts need xelatex or lualatex" in summary


def test_summary_without_an_error_points_at_the_log(tmp_path: Path) -> None:
    log = tmp_path / "doc.log"
    log.write_text("This is XeTeX\nOutput written on doc.pdf\n")

    assert summarise_log(log).startswith("no error found in the log")
    assert summarise_log(tmp_path / "none.log").startswith("no log was written")


def fake_latexmk(returncodes: dict[str, int], tex: Path):
    """A subprocess.run that writes a PDF or a log depending on the engine."""
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        engine = command[1].lstrip("-")
        code = returncodes[engine]
        if code == 0:
            tex.with_suffix(".pdf").write_bytes(b"%PDF")
        else:
            tex.with_suffix(".log").write_text(UNDEFINED)
        return subprocess.CompletedProcess(command, code, "", "")

    return run, calls


@pytest.fixture
def tex(tmp_path: Path) -> Path:
    path = tmp_path / "doc.tex"
    path.write_text("\\documentclass{article}")
    return path


def installed(*names: str):
    return lambda name: f"/bin/{name}" if name in names else None


def test_falls_back_to_the_next_engine(tex: Path) -> None:
    run, calls = fake_latexmk({"lualatex": 12, "xelatex": 0}, tex)
    engines = LaTeXEngineConfig(primary_engine="lualatex", fallback_engines=["xelatex"])
    with (
        patch(
            "studiorum.latex_engine.latexmk.get_safe_executable",
            return_value="/bin/latexmk",
        ),
        patch(
            "studiorum.latex_engine.latexmk.shutil.which",
            installed("lualatex", "xelatex"),
        ),
        patch("studiorum.latex_engine.latexmk.subprocess.run", run),
    ):
        result = build_pdf(tex, engines)

    assert result == Success(tex.with_suffix(".pdf"))
    assert [c[1] for c in calls] == ["-lualatex", "-xelatex"]
    assert calls[0][2:] == [
        "-interaction=nonstopmode",
        "-file-line-error",
        "-halt-on-error",
        f"-outdir={tex.parent}",
        "doc.tex",
    ]


def test_reports_each_engine_when_all_fail(tex: Path) -> None:
    run, _ = fake_latexmk({"xelatex": 12}, tex)
    engines = LaTeXEngineConfig(primary_engine="xelatex", fallback_engines=["pdflatex"])
    with (
        patch(
            "studiorum.latex_engine.latexmk.get_safe_executable",
            return_value="/bin/latexmk",
        ),
        patch("studiorum.latex_engine.latexmk.shutil.which", installed("xelatex")),
        patch("studiorum.latex_engine.latexmk.subprocess.run", run),
    ):
        result = build_pdf(tex, engines)

    assert isinstance(result, Error)
    assert "xelatex: ./doc.tex:12: Undefined control sequence." in result.error
    assert "pdflatex: not installed" in result.error


def test_timeout_is_reported(tex: Path) -> None:
    def run(command: list[str], **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    engines = LaTeXEngineConfig(primary_engine="xelatex", fallback_engines=[])
    with (
        patch(
            "studiorum.latex_engine.latexmk.get_safe_executable",
            return_value="/bin/latexmk",
        ),
        patch("studiorum.latex_engine.latexmk.shutil.which", installed("xelatex")),
        patch("studiorum.latex_engine.latexmk.subprocess.run", run),
    ):
        result = build_pdf(tex, engines)

    assert result == Error(f"xelatex: timed out after {engines.timeout} s")
