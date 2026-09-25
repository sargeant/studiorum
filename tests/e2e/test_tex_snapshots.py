"""Snapshot the LaTeX output of the convert commands.

Each test drives the real CLI through CliRunner against test-data/ and
srd-data/, then compares the .tex file with a stored snapshot under
__snapshots__/. After an intended change to the output, refresh them with:

    uv run pytest tests/e2e --snapshot-update

The tests load tests/test-config.yaml through STUDIORUM_CONFIG_FILE, so the
developer's own ~/.studiorum/config.yaml (data sources, layout defaults)
cannot leak in.
"""

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode
from typer.testing import CliRunner

from studiorum.cli.main import app
from tests.test_helpers import reset_test_environment

REPO_ROOT = Path(__file__).resolve().parents[2]

# Layout options are passed explicitly so the output does not depend on
# config defaults.
LAYOUT = [
    "--document-class",
    "dndbook",
    "--paper",
    "letter",
    "--font-size",
    "11pt",
    "--background",
    "full",
    "--two-column",
    "--not-justified",
    "--statblock",
    "modern",
    "--no-images",
]

CASES = {
    "adventure": ["convert", "adventure", "test"],
    "bestiary": [
        "convert",
        "creatures",
        "Goblin",
        "Lich",
        "Adult Red Dragon",
        "--sources",
        "SRD",
    ],
    "spellbook": [
        "convert",
        "spells",
        "Fireball",
        "Shield",
        "Wish",
        "--sources",
        "SRD",
    ],
    "items": [
        "convert",
        "items",
        "Amulet of Health",
        "Bag of Holding",
        "Longsword",
        "--sources",
        "SRD",
    ],
}


class TexSnapshotExtension(SingleFileSnapshotExtension):
    """Store each snapshot as a plain .tex file so diffs read as LaTeX."""

    file_extension = "tex"
    _write_mode = WriteMode.TEXT


@pytest.fixture
def tex_snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(TexSnapshotExtension)


@pytest.fixture
def isolated_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Run the CLI against the repo's test data with no user configuration."""
    for name in [n for n in os.environ if n.startswith("STUDIORUM_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv(
        "STUDIORUM_CONFIG_FILE", str(REPO_ROOT / "tests" / "test-config.yaml")
    )
    monkeypatch.chdir(REPO_ROOT)
    reset_test_environment()
    yield tmp_path
    reset_test_environment()


def normalise(tex: str, tmp_path: Path) -> str:
    """Strip machine- and time-specific details from generated LaTeX."""
    tex = tex.replace(str(tmp_path), "<TMP>")
    tex = tex.replace(str(REPO_ROOT), "<REPO>")
    tex = re.sub(r"\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?", "<DATE>", tex)
    return re.sub(r"\b\d{2}:\d{2}:\d{2}\b", "<TIME>", tex)


@pytest.mark.parametrize("case", sorted(CASES))
def test_tex_output(
    case: str, isolated_cli: Path, tex_snapshot: SnapshotAssertion
) -> None:
    output = isolated_cli / f"{case}.tex"
    result = CliRunner().invoke(app, [*CASES[case], *LAYOUT, "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert normalise(output.read_text(encoding="utf-8"), isolated_cli) == tex_snapshot
