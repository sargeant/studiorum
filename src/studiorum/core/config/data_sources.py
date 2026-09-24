"""Where the 5etools data comes from.

``data.dirs`` are 5etools-shaped data directories (the ``data/`` of a 5etools
checkout, or the repo's ``srd-data``). ``data.homebrew`` are homebrew JSON
files, or directories of them. When two entities share a type, name and
source, the one loaded first wins: dirs in order, then homebrew.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _find_project_root() -> Path | None:
    """The nearest directory above the working directory holding test-data/ and srd-data/."""
    current = Path.cwd()
    for candidate in [current, *current.parents]:
        if (candidate / "test-data").is_dir() and (candidate / "srd-data").is_dir():
            return candidate
    return None


def default_data_dirs() -> list[Path]:
    """test-data/ and srd-data/ of the nearest project root, if there is one."""
    root = _find_project_root()
    return [root / "test-data", root / "srd-data"] if root else []


class DataConfig(BaseModel):
    """The data directories and homebrew to load."""

    model_config = ConfigDict(extra="forbid")

    dirs: list[Path] = Field(
        default_factory=default_data_dirs,
        description="5etools-shaped data directories, highest priority first",
    )
    homebrew: list[Path] = Field(
        default_factory=list,
        description="Homebrew JSON files, or directories of them",
    )

    @field_validator("dirs", "homebrew")
    @classmethod
    def _expand(cls, paths: list[Path]) -> list[Path]:
        return [Path(p).expanduser() for p in paths]
