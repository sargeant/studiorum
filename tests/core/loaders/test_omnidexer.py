"""The Omnidexer loads a data set once, resolving _copy before it validates."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from studiorum.core.config.unified_config import ApplicationConfig, set_app_config
from studiorum.core.loaders.data_dir import DataDir, DataSet
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType
from studiorum.core.models.creatures import Creature

REPO_ROOT = Path(__file__).resolve().parents[3]


def _srd_creature(name: str) -> dict[str, Any]:
    data = json.loads((REPO_ROOT / "srd-data/bestiary/bestiary-srd.json").read_text())
    return next(m for m in data["monster"] if m["name"] == name)


def _write(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


def _load(root: Path, *homebrew: Path) -> Omnidexer:
    omnidexer = Omnidexer(DataSet((DataDir(root),), homebrew))
    omnidexer.load_all_data()
    return omnidexer


def test_a_variant_keeps_its_own_cr_and_actions(tmp_path: Path) -> None:
    captain = {
        "name": "Captain Test",
        "source": "TST",
        "cr": "5",
        "action": [{"name": "Rally", "entries": ["The captain rallies."]}],
        "_copy": {
            "name": "Veteran",
            "source": "SRD",
            "_mod": {
                "action": {
                    "mode": "appendArr",
                    "items": {"name": "Parry", "entries": []},
                }
            },
        },
    }
    _write(
        tmp_path / "bestiary/bestiary-srd.json",
        {"monster": [_srd_creature("Veteran"), captain]},
    )

    found = _load(tmp_path).find(ContentType.CREATURE, "Captain Test", "TST")

    assert isinstance(found, Creature)
    assert found.cr == "5"
    assert [a.name for a in found.action or []] == ["Rally", "Parry"]
    assert found.strength == _srd_creature("Veteran")["str"]


def test_a_copy_with_no_parent_is_not_loaded(tmp_path: Path) -> None:
    orphan = {
        "name": "Orphan",
        "source": "TST",
        "_copy": {"name": "Nobody", "source": "MM"},
    }
    _write(
        tmp_path / "bestiary/bestiary-tst.json",
        {"monster": [orphan, _srd_creature("Goblin")]},
    )

    omnidexer = _load(tmp_path)

    assert omnidexer.find(ContentType.CREATURE, "Orphan") is None
    assert omnidexer.find(ContentType.CREATURE, "Goblin") is not None


def test_a_reprint_alias_never_replaces_the_reprint(tmp_path: Path) -> None:
    old = {**_srd_creature("Goblin"), "reprintedAs": ["Goblin|NEW"]}
    new = {
        **_srd_creature("Goblin"),
        "source": "NEW",
        "hp": {"average": 99, "formula": "1d1"},
    }
    _write(tmp_path / "bestiary/bestiary-a.json", {"monster": [old]})
    _write(tmp_path / "bestiary/bestiary-b.json", {"monster": [new]})

    found = _load(tmp_path).find(ContentType.CREATURE, "Goblin", "NEW")

    assert found is not None
    assert found.hp.average == 99  # type: ignore[attr-defined]


def test_the_first_directory_wins_a_clash(tmp_path: Path) -> None:
    first = {**_srd_creature("Goblin"), "hp": {"average": 1, "formula": "1d1"}}
    _write(tmp_path / "a/bestiary/bestiary-srd.json", {"monster": [first]})
    _write(
        tmp_path / "b/bestiary/bestiary-srd.json",
        {"monster": [_srd_creature("Goblin")]},
    )

    omnidexer = Omnidexer(DataSet((DataDir(tmp_path / "a"), DataDir(tmp_path / "b"))))
    omnidexer.load_all_data()

    assert omnidexer.find(ContentType.CREATURE, "Goblin").hp.average == 1  # type: ignore[union-attr]


def test_invalid_entities_are_skipped_unless_strict(tmp_path: Path) -> None:
    bad = {**_srd_creature("Goblin"), "name": "Bad", "size": 5}
    _write(
        tmp_path / "bestiary/bestiary-tst.json",
        {"monster": [bad, _srd_creature("Goblin")]},
    )

    omnidexer = _load(tmp_path)
    assert omnidexer.find(ContentType.CREATURE, "Goblin") is not None
    assert omnidexer.find(ContentType.CREATURE, "Bad") is None

    config = ApplicationConfig()
    config.validation.strictness = "strict"
    set_app_config(config)
    with pytest.raises(ValidationError):
        _load(tmp_path)


def test_fluff_that_fails_validation_keeps_its_name(tmp_path: Path) -> None:
    fluff = {"name": "Goblin", "source": "SRD", "images": "not a list"}
    _write(tmp_path / "bestiary/fluff-bestiary-srd.json", {"monsterFluff": [fluff]})

    found = _load(tmp_path).find(ContentType.CREATURE_FLUFF, "Goblin", "SRD")

    assert found is not None


def test_adventure_text_loads_when_asked_for(tmp_path: Path) -> None:
    metadata = {
        "name": "The Test",
        "id": "TT",
        "source": "TT",
        "contents": [{"name": "Chapter 1"}],
    }
    _write(tmp_path / "adventures.json", {"adventure": [metadata]})
    text = {
        "data": [{"type": "section", "name": "Chapter 1", "entries": ["It begins."]}]
    }
    _write(tmp_path / "adventure/adventure-tt.json", text)

    omnidexer = _load(tmp_path)
    listed = omnidexer.get_all_by_type(ContentType.ADVENTURE)
    found = omnidexer.find(ContentType.ADVENTURE, "The Test")

    assert listed[0].contents[0].entries == []  # type: ignore[attr-defined]
    assert found.contents[0].entries == ["It begins."]  # type: ignore[union-attr]
    assert omnidexer.get_all_by_type(ContentType.ADVENTURE) == [found]


def test_homebrew_adventure_text_loads_from_adventure_data(tmp_path: Path) -> None:
    brew = _write(
        tmp_path / "brew.json",
        {
            "adventure": [
                {
                    "name": "Brew",
                    "id": "BRW",
                    "source": "BRW",
                    "contents": [{"name": "One"}],
                }
            ],
            "adventureData": [
                {
                    "id": "BRW",
                    "data": [{"type": "section", "name": "One", "entries": ["Hi."]}],
                }
            ],
        },
    )
    (tmp_path / "data").mkdir()

    found = _load(tmp_path / "data", brew).find(ContentType.ADVENTURE, "Brew")

    assert found.contents[0].entries == ["Hi."]  # type: ignore[union-attr]


def test_magic_variants_take_their_source_from_inherits(tmp_path: Path) -> None:
    variant = {
        "name": "+1 Test",
        "type": "GV|DMG",
        "requires": [{"weapon": True}],
        "inherits": {"source": "DMG", "namePrefix": "+1 ", "rarity": "uncommon"},
    }
    _write(tmp_path / "magicvariants.json", {"magicvariant": [variant]})

    omnidexer = _load(tmp_path)

    assert omnidexer.find(ContentType.MAGICVARIANT, "+1 Test", "DMG") is not None
