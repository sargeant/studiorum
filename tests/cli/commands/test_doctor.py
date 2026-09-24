"""studiorum doctor: configuration, data sources and cache in one check."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from studiorum.cli.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def doctor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run doctor against the repo's test data with extra data_sources config."""
    monkeypatch.chdir(REPO_ROOT)

    def invoke(**data_sources: object):
        config = {"data_sources": {"primary_override": {"enabled": False}}}
        config["data_sources"].update(data_sources)
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump(config))
        return CliRunner().invoke(app, ["-c", str(config_file), "doctor"])

    return invoke


def test_healthy_setup_passes(doctor) -> None:
    result = doctor()

    assert result.exit_code == 0, result.output
    assert "Loaded from" in result.output
    assert "content types" in result.output
    assert "All checks passed" in result.output


def test_missing_extension_is_a_warning(doctor, tmp_path: Path) -> None:
    missing = tmp_path / "nowhere.json"
    result = doctor(
        extensions=[{"name": "gone", "type": "file", "source": str(missing)}]
    )

    assert result.exit_code == 0, result.output
    assert "warning" in result.output


def test_no_data_files_fails(doctor) -> None:
    with patch(
        "studiorum.core.loaders.unified_source_manager.UnifiedSourceManager.get_source_statistics",
        return_value={"enabled_sources": 1, "total_files": 0},
    ):
        result = doctor()

    assert result.exit_code == 1
    assert "no files found" in result.output


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
