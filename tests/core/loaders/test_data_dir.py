"""DataDir picks entity files from a 5etools data directory by its manifests."""

import json
from pathlib import Path

from studiorum.core.loaders.data_dir import DataDir, DataSet
from studiorum.core.models.content import ContentType


def _write(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


def _data_dir(root: Path) -> DataDir:
    _write(root / "spells" / "index.json", {"PHB": "spells-phb.json"})
    _write(root / "spells" / "fluff-index.json", {"PHB": "fluff-spells-phb.json"})
    _write(root / "spells" / "spells-phb.json", {"spell": []})
    _write(root / "spells" / "fluff-spells-phb.json", {"spellFluff": []})
    _write(root / "spells" / "spells-unlisted.json", {"spell": []})
    _write(root / "spells" / "sources.json", {})
    _write(root / "bestiary" / "index.json", {"MM": "bestiary-mm.json"})
    _write(root / "bestiary" / "bestiary-mm.json", {"monster": []})
    _write(root / "bestiary" / "legendarygroups.json", {"legendaryGroup": []})
    _write(root / "bestiary" / "template.json", {"monsterTemplate": [{"name": "T"}]})
    _write(root / "class" / "class-wizard.json", {"class": []})
    _write(root / "items.json", {"item": []})
    _write(root / "adventures.json", {"adventure": []})
    _write(root / "foundry-items.json", {"item": []})
    _write(root / "adventure-example.json", {"adventure": []})
    _write(root / "adventure" / "adventure-cos.json", {"data": []})
    _write(root / "generated" / "gendata-tables.json", {"table": []})
    return DataDir(root)


def test_entity_files_follow_the_manifests(tmp_path: Path) -> None:
    files = [
        p.relative_to(tmp_path).as_posix() for p in _data_dir(tmp_path).entity_files()
    ]

    assert files == [
        "adventures.json",
        "bestiary/bestiary-mm.json",
        "bestiary/legendarygroups.json",
        "class/class-wizard.json",
        "items.json",
        "spells/fluff-spells-phb.json",
        "spells/spells-phb.json",
    ]


def test_a_directory_without_a_manifest_is_globbed(tmp_path: Path) -> None:
    _data_dir(tmp_path)

    files = DataDir(tmp_path).entity_files()

    assert tmp_path / "class" / "class-wizard.json" in files


def test_content_files_are_found_by_id(tmp_path: Path) -> None:
    data_dir = _data_dir(tmp_path)

    assert data_dir.content_file(ContentType.ADVENTURE, "CoS") == (
        tmp_path / "adventure" / "adventure-cos.json"
    )
    assert data_dir.content_file(ContentType.BOOK, "PHB") is None
    assert data_dir.content_file(ContentType.CREATURE, "CoS") is None


def test_templates_come_from_the_bestiary(tmp_path: Path) -> None:
    assert _data_dir(tmp_path).templates()["monster"] == [{"name": "T"}]


def test_a_data_set_lists_dirs_then_homebrew(tmp_path: Path) -> None:
    first = _data_dir(tmp_path / "first")
    brew_dir = tmp_path / "brew"
    _write(brew_dir / "a.json", {"monster": []})
    brew_file = _write(tmp_path / "b.json", {"monster": []})

    files = DataSet((first,), (brew_dir, brew_file)).files()

    assert files[-2:] == [brew_dir / "a.json", brew_file]
    assert files[0].is_relative_to(tmp_path / "first")


def test_problems_name_missing_paths(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    problems = DataSet(
        (DataDir(tmp_path / "gone"), DataDir(empty)), (tmp_path / "brew.json",)
    ).problems()

    assert problems == [
        f"Data directory not found: {tmp_path / 'gone'}",
        f"No JSON files in data directory: {empty}",
        f"Homebrew not found: {tmp_path / 'brew.json'}",
    ]
    assert DataSet(()).problems() == ["No data directories configured (data.dirs)"]
