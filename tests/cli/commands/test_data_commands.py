"""studiorum data show: the configured data directories and homebrew."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from studiorum.cli.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def data_show(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run ``data show`` with the given ``data`` config (default: the repo's)."""
    monkeypatch.chdir(REPO_ROOT)

    def invoke(**data: object):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump({"data": data} if data else {}))
        return CliRunner().invoke(app, ["-c", str(config_file), "data", "show"])

    return invoke


def test_default_shows_test_data_and_srd(data_show) -> None:
    result = data_show()

    assert result.exit_code == 0, result.output
    assert "test-data" in result.output
    assert "srd-data" in result.output


def test_homebrew_is_listed_after_the_dirs(data_show, tmp_path: Path) -> None:
    brew = tmp_path / "brew.json"
    brew.write_text('{"monster": []}')

    result = data_show(dirs=[str(REPO_ROOT / "srd-data")], homebrew=[str(brew)])

    assert result.exit_code == 0, result.output
    assert result.output.index("srd-data") < result.output.index("homebrew")


def test_missing_paths_are_marked(data_show, tmp_path: Path) -> None:
    result = data_show(dirs=[str(tmp_path / "gone")])

    assert result.exit_code == 0, result.output
    assert "missing" in result.output


def test_no_data_configured_exits_1(data_show) -> None:
    result = data_show(dirs=[])

    assert result.exit_code == 1
    assert "data.dirs" in result.output


def test_old_config_sections_name_their_replacement(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("data_sources:\n  primary_override:\n    enabled: true\n")

    result = CliRunner().invoke(app, ["-c", str(config_file), "data", "show"])

    assert result.exit_code == 1
    assert "data.dirs" in result.output
