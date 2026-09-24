"""Tests for load_config: one YAML file, environment on top, no silent fallback."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.config.unified_config import (
    ConfigFileNotFoundError,
    load_config,
)


def write_config(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_yaml_file(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path / "config.yaml",
        "rendering:\n  compilation:\n    auto_compile_pdf: true\n",
    )
    assert load_config(config_file).rendering.compilation.auto_compile_pdf is True


def test_environment_overrides_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = write_config(tmp_path / "config.yaml", "logging:\n  level: DEBUG\n")
    monkeypatch.setenv("STUDIORUM_LOGGING__LEVEL", "ERROR")
    assert load_config(config_file).logging.level == "ERROR"


def test_env_var_names_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = write_config(tmp_path / "other.yaml", "logging:\n  level: ERROR\n")
    monkeypatch.setenv("STUDIORUM_CONFIG_FILE", str(config_file))
    assert load_config().logging.level == "ERROR"


def test_missing_named_file_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STUDIORUM_CONFIG_FILE", str(tmp_path / "missing.yaml"))
    with pytest.raises(ConfigFileNotFoundError):
        load_config()
    with pytest.raises(ConfigFileNotFoundError):
        load_config(tmp_path / "also-missing.yaml")


def test_missing_default_file_uses_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STUDIORUM_CONFIG_FILE")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert load_config().logging.level == "WARNING"


def test_cli_rejects_missing_config_file(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["-c", str(tmp_path / "missing.yaml"), "config", "show"]
    )
    assert result.exit_code == 1
    assert "not found" in result.output


@pytest.mark.parametrize("auto_compile", [True, False])
def test_config_file_sets_convert_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, auto_compile: bool
) -> None:
    """The --pdf default comes from the -c file, read after the callback loads it."""
    from unittest.mock import AsyncMock

    from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

    monkeypatch.setattr(
        LaTeXTemplateEngine, "check_dnd_template_availability", lambda self: True
    )
    compile_pdf = AsyncMock()
    monkeypatch.setattr(
        "studiorum.cli.commands.convert.run.compile_pdf",
        compile_pdf,
    )
    config_file = write_config(
        tmp_path / "other.yaml",
        f"rendering:\n  compilation:\n    auto_compile_pdf: {str(auto_compile).lower()}\n",
    )
    result = CliRunner().invoke(
        app,
        [
            "-c",
            str(config_file),
            "convert",
            "creatures",
            "Goblin",
            "--sources",
            "SRD",
            "--output",
            str(tmp_path / "out.tex"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert compile_pdf.called is auto_compile
