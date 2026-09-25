"""The files that make up a data set: 5etools data directories plus homebrew.

A ``DataDir`` is a 5etools-shaped ``data/`` directory. Its entities live in
the top-level JSON files and in ``bestiary/``, ``spells/`` and ``class/``,
whose ``index.json`` and ``fluff-index.json`` manifests list their files (the
SRD bundle has no manifests, so those directories are globbed instead), and
the tables 5etools generates from book and adventure text.
Adventure and book text lives in ``adventure/`` and ``book/``, one file per
id, and is read only when an adventure or book is asked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson

from ..config.data_sources import DataConfig
from ..models.content import ContentType

# Subdirectories whose files are listed by index.json and fluff-index.json
_MANIFEST_DIRS = ("bestiary", "spells", "class")
# Entity files in those subdirectories that the manifests do not list
_UNLISTED = {"bestiary": ("legendarygroups.json",)}
# Files in them that hold something other than entities
_NOT_ENTITIES = {
    "index.json",
    "fluff-index.json",
    "foundry.json",
    "template.json",
    "sources.json",
}
# Generated files 5etools loads as entities: the tables page reads the tables
# extracted from books and adventures (DataUtil.table.loadJSON)
_GENERATED = ("gendata-tables.json",)
_CONTENT_DIRS = {ContentType.ADVENTURE: "adventure", ContentType.BOOK: "book"}


def read_json(path: Path) -> Any:
    return orjson.loads(path.read_bytes())


@dataclass(frozen=True)
class DataDir:
    """One 5etools-shaped data directory."""

    root: Path

    def entity_files(self) -> list[Path]:
        """Files holding entities, sorted by path; adventure and book text excluded."""
        # adventure-<id>.json and book-<id>.json are text, never entities
        files = [
            p
            for p in self.root.glob("*.json")
            if not p.name.startswith(("foundry", "adventure-", "book-"))
        ]
        for name in _MANIFEST_DIRS:
            files += self._manifest_files(self.root / name)
        files += [
            p for name in _GENERATED if (p := self.root / "generated" / name).exists()
        ]
        return sorted(files, key=lambda p: p.relative_to(self.root).as_posix())

    def _manifest_files(self, directory: Path) -> list[Path]:
        if not directory.is_dir():
            return []
        manifests = [directory / "index.json", directory / "fluff-index.json"]
        if not manifests[0].exists():
            return [p for p in directory.glob("*.json") if p.name not in _NOT_ENTITIES]
        files = [
            directory / filename
            for manifest in manifests
            if manifest.exists()
            for filename in read_json(manifest).values()
        ]
        files += [directory / name for name in _UNLISTED.get(directory.name, ())]
        return [p for p in files if p.exists()]

    def content_file(self, content_type: ContentType, content_id: str) -> Path | None:
        """The text of an adventure or book: ``adventure/adventure-<id>.json``."""
        folder = _CONTENT_DIRS.get(content_type)
        if folder is None:
            return None
        path = self.root / folder / f"{folder}-{content_id.lower()}.json"
        return path if path.exists() else None

    def templates(self) -> dict[str, list[dict[str, Any]]]:
        """The ``_copy`` templates in ``bestiary/template.json``, by the prop they apply to."""
        path = self.root / "bestiary" / "template.json"
        if not path.exists():
            return {}
        data = read_json(path)
        return {
            "monster": data.get("monsterTemplate", []),
            "legendaryGroup": data.get("legendaryGroupTemplate", []),
        }


@dataclass(frozen=True)
class DataSet:
    """Data directories in priority order, then homebrew files."""

    dirs: tuple[DataDir, ...]
    homebrew: tuple[Path, ...] = field(default=())

    @classmethod
    def from_config(cls, config: DataConfig) -> DataSet:
        return cls(tuple(DataDir(p) for p in config.dirs), tuple(config.homebrew))

    def files(self) -> list[Path]:
        """Every entity file, dirs first in order, then homebrew."""
        files = [f for d in self.dirs if d.root.is_dir() for f in d.entity_files()]
        for path in self.homebrew:
            if path.is_dir():
                files += sorted(path.rglob("*.json"))
            elif path.is_file():
                files.append(path)
        return files

    def content_file(self, content_type: ContentType, content_id: str) -> Path | None:
        for data_dir in self.dirs:
            found = data_dir.content_file(content_type, content_id)
            if found is not None:
                return found
        return None

    def templates(self) -> dict[str, list[dict[str, Any]]]:
        """Templates from the first directory that has them."""
        for data_dir in self.dirs:
            templates = data_dir.templates()
            if templates:
                return templates
        return {}

    def problems(self) -> list[str]:
        """Configured paths that are missing or hold no JSON."""
        problems = []
        if not self.dirs:
            problems.append("No data directories configured (data.dirs)")
        for data_dir in self.dirs:
            if not data_dir.root.is_dir():
                problems.append(f"Data directory not found: {data_dir.root}")
            elif not data_dir.entity_files():
                problems.append(f"No JSON files in data directory: {data_dir.root}")
        problems += [
            f"Homebrew not found: {p}" for p in self.homebrew if not p.exists()
        ]
        return problems
