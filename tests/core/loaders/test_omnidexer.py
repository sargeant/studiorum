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


def test_an_item_property_is_named_after_its_first_entry(tmp_path: Path) -> None:
    prop = {
        "abbreviation": "2H",
        "source": "XPHB",
        "entries": [{"type": "entries", "name": "Two-Handed", "entries": ["..."]}],
    }
    _write(tmp_path / "items-base.json", {"itemProperty": [prop]})

    omnidexer = _load(tmp_path)

    assert omnidexer.find(ContentType.ITEM_PROPERTY, "Two-Handed", "XPHB") is not None


def test_a_nameless_subrace_is_left_to_its_race(tmp_path: Path) -> None:
    default = {"source": "PHB", "raceName": "Human", "raceSource": "PHB"}
    named = {**default, "name": "Variant", "entries": ["..."]}
    _write(tmp_path / "races.json", {"subrace": [default, named]})

    omnidexer = _load(tmp_path)

    assert [s.name for s in omnidexer.get_all_by_type(ContentType.SUBRACE)] == [
        "Variant"
    ]


def _feature(class_name: str, level: int, source: str = "PHB") -> dict[str, Any]:
    return {
        "name": "Ability Score Improvement",
        "source": source,
        "className": class_name,
        "classSource": source,
        "level": level,
        "entries": [f"{class_name} {level}"],
    }


def test_same_named_features_of_different_classes_are_all_indexed(
    tmp_path: Path,
) -> None:
    features = [_feature("Fighter", 4), _feature("Fighter", 6), _feature("Rogue", 4)]
    _write(tmp_path / "class/class-test.json", {"classFeature": features})
    _write(tmp_path / "class/index.json", {"test": "class-test.json"})

    omnidexer = _load(tmp_path)
    found = omnidexer.find_all(ContentType.CLASS_FEATURE, "Ability Score Improvement")

    assert [f.entries for f in found] == [["Fighter 4"], ["Fighter 6"], ["Rogue 4"]]  # type: ignore[attr-defined]
    # find() still gives the first loaded
    first = omnidexer.find(
        ContentType.CLASS_FEATURE, "Ability Score Improvement", "PHB"
    )
    assert first is found[0]


@pytest.mark.parametrize(
    ("uid", "expected"),
    [
        ("Ability Score Improvement|Fighter||6", ["Fighter 6"]),
        ("ability score improvement|rogue|phb|4|phb", ["Rogue 4"]),
        ("Ability Score Improvement|Rogue|XPHB|4", None),
        ("Ability Score Improvement|Wizard||4", None),
    ],
)
def test_find_uid_reads_5etools_uids(
    tmp_path: Path, uid: str, expected: list[str] | None
) -> None:
    features = [_feature("Fighter", 4), _feature("Fighter", 6), _feature("Rogue", 4)]
    _write(tmp_path / "class/class-test.json", {"classFeature": features})
    _write(tmp_path / "class/index.json", {"test": "class-test.json"})

    found = _load(tmp_path).find_uid(ContentType.CLASS_FEATURE, uid)

    assert (found.entries if found else None) == expected  # type: ignore[attr-defined]


def test_a_subclass_reprint_is_aliased_only_when_the_reprint_is_missing(
    tmp_path: Path,
) -> None:
    def subclass(name: str, short: str, source: str, **extra: object) -> dict[str, Any]:
        return {
            "name": name,
            "shortName": short,
            "source": source,
            "className": "Barbarian",
            "classSource": source,
            "subclassFeatures": [f"{name}|Barbarian||{short}||3"],
            **extra,
        }

    totem = subclass(
        "Path of the Totem Warrior",
        "Totem Warrior",
        "PHB",
        reprintedAs=["Wild Heart|Barbarian|XPHB|XPHB"],
    )
    berserker = subclass(
        "Path of the Berserker",
        "Berserker",
        "PHB",
        reprintedAs=["Berserker|Barbarian|XPHB|XPHB"],
    )
    wild_heart = subclass("Path of the Wild Heart", "Wild Heart", "XPHB")
    _write(
        tmp_path / "class/class-test.json", {"subclass": [totem, berserker, wild_heart]}
    )
    _write(tmp_path / "class/index.json", {"test": "class-test.json"})

    omnidexer = _load(tmp_path)
    xphb = [
        s.name
        for s in omnidexer.get_all_by_type(ContentType.SUBCLASS)
        if s.source.abbreviation == "XPHB"
    ]

    assert sorted(xphb) == ["Path of the Berserker", "Path of the Wild Heart"]
    alias = omnidexer.find_uid(ContentType.SUBCLASS, "Berserker|Barbarian|XPHB|XPHB")
    assert alias is not None
    assert alias.class_source == "XPHB"  # type: ignore[attr-defined]


def test_a_reprint_tagged_as_another_type_is_not_aliased(tmp_path: Path) -> None:
    style = {
        "name": "Archery",
        "source": "PHB",
        "featureType": ["FS:F"],
        "entries": ["..."],
        "reprintedAs": [{"uid": "Archery|XPHB", "tag": "feat"}],
    }
    _write(tmp_path / "optionalfeatures.json", {"optionalfeature": [style]})

    omnidexer = _load(tmp_path)

    assert omnidexer.find(ContentType.OPTIONALFEATURE, "Archery", "XPHB") is None


def test_an_item_property_reprint_is_read_by_abbreviation(tmp_path: Path) -> None:
    def prop(source: str, **extra: object) -> dict[str, Any]:
        entry = {"type": "entries", "name": "Two-Handed", "entries": [source]}
        return {"abbreviation": "2H", "source": source, "entries": [entry], **extra}

    old = prop("PHB", reprintedAs=["2H|XPHB"])
    _write(tmp_path / "items-base.json", {"itemProperty": [old, prop("XPHB")]})

    omnidexer = _load(tmp_path)

    assert [
        (p.name, p.source.abbreviation)
        for p in omnidexer.get_all_by_type(ContentType.ITEM_PROPERTY)
    ] == [("Two-Handed", "PHB"), ("Two-Handed", "XPHB")]
    found = omnidexer.find_uid(ContentType.ITEM_PROPERTY, "2H|XPHB")
    assert found is not None
    assert found.entries[0].entries == ["XPHB"]  # type: ignore[attr-defined]
