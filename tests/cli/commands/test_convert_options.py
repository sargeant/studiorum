"""The convert commands' shared options: config defaults, flags over config.

These drive the real CLI against test-data/ and srd-data/ with a config file
written per test, and read the .tex file back.
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from studiorum.cli.commands.convert.run import append_appendix, read_names
from studiorum.cli.main import app
from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

REPO_ROOT = Path(__file__).resolve().parents[3]
CREATURES = ["convert", "creatures", "Goblin", "--sources", "SRD"]


@pytest.fixture
def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run the CLI with a config file holding ``document`` and ``extra``."""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(
        LaTeXTemplateEngine, "check_dnd_template_availability", lambda self: True
    )

    def invoke(args: list[str], document: dict | None = None, **extra: object):
        config = {
            "data_sources": {"primary_override": {"enabled": False}},
            "rendering": {"latex": {"document": document or {}}, **extra},
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump(config))
        output = tmp_path / "out.tex"
        result = CliRunner().invoke(
            app, ["-c", str(config_file), *args, "--output", str(output)]
        )
        tex = output.read_text() if output.exists() else ""
        return result, tex

    return invoke


def class_options(tex: str) -> list[str]:
    match = re.search(r"\\documentclass\[([^\]]*)\]", tex)
    assert match, "no \\documentclass line"
    return [option.strip() for option in match.group(1).split(",")]


def test_defaults_render_the_class_options_documents_always_had(run) -> None:
    result, tex = run(CREATURES)

    assert result.exit_code == 0, result.output
    assert class_options(tex) == [
        "letterpaper",
        "11pt",
        "bg=full",
        "twocolumn",
        "stats=modern",
    ]
    assert "\\printindex" not in tex


def test_config_values_reach_the_document(run) -> None:
    document = {
        "paper_size": "a4",
        "high_contrast": True,
        "fancy_headers": True,
        "no_outline": True,
        "show_index": True,
        "extra_class_options": ["draft"],
    }
    result, tex = run(CREATURES, document)

    assert result.exit_code == 0, result.output
    options = class_options(tex)
    for option in ("a4paper", "highcontrast", "fancy", "nooutline", "draft"):
        assert option in options
    assert "\\makeindex" in tex
    assert "\\printindex" in tex


def test_flags_override_config_both_ways(run) -> None:
    document = {
        "high_contrast": True,
        "no_outline": True,
        "show_index": True,
        "show_toc": True,
    }
    args = [*CREATURES, "--no-high-contrast", "--outline", "--no-index", "--no-toc"]
    result, tex = run(args, document)

    assert result.exit_code == 0, result.output
    options = class_options(tex)
    assert "highcontrast" not in options
    assert "nooutline" not in options
    assert "\\printindex" not in tex
    assert "\\tableofcontents" not in tex

    result, tex = run([*CREATURES, "--high-contrast", "--no-outline", "--index"])
    options = class_options(tex)
    assert "highcontrast" in options
    assert "nooutline" in options
    assert "\\printindex" in tex


def test_invalid_layout_value_exits_with_the_field(run) -> None:
    result, _ = run([*CREATURES, "--paper", "b5"])

    assert result.exit_code == 1
    assert "paper_size" in result.output


@pytest.mark.parametrize(("flag", "compiled"), [([], True), (["--no-pdf"], False)])
def test_pdf_defaults_to_the_config(run, flag: list[str], compiled: bool) -> None:
    with patch(
        "studiorum.cli.commands.convert.run.compile_pdf", new_callable=AsyncMock
    ) as compile_pdf:
        result, _ = run([*CREATURES, *flag], compilation={"auto_compile_pdf": True})

    assert result.exit_code == 0, result.output
    assert compile_pdf.await_count == (1 if compiled else 0)


def test_adventure_appendix_flags_default_to_the_config(run) -> None:
    with patch(
        "studiorum.cli.commands.convert.adventure.create_latex_engine"
    ) as create_engine:
        engine = create_engine.return_value
        engine.render_document.return_value = "\\documentclass{dndbook}"
        result, _ = run(
            ["convert", "adventure", "test", "--no-items"],
            content={"appendix_spells": True, "appendix_items": True},
        )

    assert result.exit_code == 0, result.output
    captured = engine.render_document.call_args.args[1].metadata
    assert captured["appendix_spells"] is True
    assert captured["appendix_items"] is False
    assert captured["appendix_creatures"] is False


class TestReadNames:
    def test_counts_sources_and_comments(self, tmp_path: Path) -> None:
        names = tmp_path / "names.txt"
        names.write_text("# party\nGoblin\n3 Orc|MM\nGoblin  # again\n\n")

        result = read_names(["Lich"], names, False, "creature")

        assert result.names == ["Lich", "Goblin", "Orc"]
        assert result.counts == {"Goblin": 2, "Orc": 3}
        assert result.sources == {"Orc": "MM"}
        assert result.total == 5

    def test_key_decides_what_counts_as_a_duplicate(self, tmp_path: Path) -> None:
        names = tmp_path / "names.txt"
        names.write_text("Goblin\nGoblin|MM\nGoblin|MM\n")

        result = read_names(
            None, names, False, "creature", key=lambda n, s: (n, s or "default")
        )

        assert result.names == ["Goblin", "Goblin"]

    def test_missing_file_exits(self, tmp_path: Path) -> None:
        import typer

        with pytest.raises(typer.Exit):
            read_names(None, tmp_path / "missing.txt", False, "spell")


class TestAppendAppendix:
    def test_no_sections_leaves_the_document_alone(self) -> None:
        latex = "\\begin{document}x\\end{document}"
        assert append_appendix(latex, [], gap_after="\n") == latex

    def test_sections_go_before_end_document(self) -> None:
        class Section:
            content = "APPENDIX"

        latex = "\\begin{document}x\\end{document}\n"
        assert (
            append_appendix(latex, [Section()], gap_after="\n")
            == "\\begin{document}x\n\nAPPENDIX\n\\end{document}\n"
        )
