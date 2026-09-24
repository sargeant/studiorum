"""convert creatures --spells: track the spells creatures cast for an appendix."""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.references.content_tracker import ContentTracker

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(REPO_ROOT)

    def invoke(*flags: str):
        with patch(
            "studiorum.cli.commands.convert.creatures._render_bestiary",
            return_value="\\begin{document}\\end{document}",
        ) as render:
            result = CliRunner().invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "Lich",
                    "--sources",
                    "SRD",
                    "--output",
                    str(tmp_path / "bestiary.tex"),
                    *flags,
                ],
            )
        assert result.exit_code == 0, result.output
        return render.call_args.args[1]

    return invoke


def test_without_spells_nothing_is_tracked(run) -> None:
    context = run()

    assert context.content_tracker is None


def test_with_spells_the_appendix_generator_gets_the_tracker(run) -> None:
    with patch(
        "studiorum.core.services.appendix_generator.AppendixGenerator"
    ) as generator:
        generator.return_value.generate_appendices.return_value = []
        context = run("--spells")

    assert isinstance(context.content_tracker, ContentTracker)
    tracker, flags = generator.return_value.generate_appendices.call_args.args
    assert isinstance(tracker, ContentTracker)
    assert (flags.spells, flags.creatures, flags.items) == (True, False, False)
