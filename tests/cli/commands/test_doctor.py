"""studiorum doctor: configuration, data and cache in one check."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from studiorum.cli.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def doctor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run doctor against the repo's test data, with ``data`` config if given."""
    monkeypatch.chdir(REPO_ROOT)

    def invoke(**data: object):
        config = {"data": data} if data else {}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump(config))
        return CliRunner().invoke(app, ["-c", str(config_file), "doctor"])

    return invoke


def test_healthy_setup_passes(doctor) -> None:
    result = doctor()

    assert result.exit_code == 0, result.output
    assert "Loaded from" in result.output
    assert "2 data directories" in result.output
    assert "All checks passed" in result.output


def test_missing_homebrew_fails(doctor, tmp_path: Path) -> None:
    result = doctor(
        dirs=[str(REPO_ROOT / "srd-data")], homebrew=[str(tmp_path / "gone.json")]
    )

    assert result.exit_code == 1
    assert "Homebrew not found" in result.output


def test_empty_data_directory_fails(doctor, tmp_path: Path) -> None:
    result = doctor(dirs=[str(tmp_path)])

    assert result.exit_code == 1
    assert "No JSON files" in result.output


def test_unwritable_cache_fails(doctor, tmp_path: Path) -> None:
    read_only = tmp_path / "cache"
    read_only.mkdir(mode=0o555)
    with patch(
        "studiorum.cli.commands.doctor.CacheManager.get_instance"
    ) as get_instance:
        get_instance.return_value.directory = str(read_only)
        result = doctor()
    read_only.chmod(0o755)

    assert result.exit_code == 1
    assert "not writable" in result.output
