"""Classes and subclasses as 5etools' compact renderer shows them."""

from typing import Any
from unittest.mock import Mock

from studiorum.data.class_entries import (
    class_entries,
    nested_features,
    subclass_entries,
)
from studiorum.data.models.classes import Class, ClassFeature, SubclassFeature
from studiorum.data.models.content import ContentType
from studiorum.data.models.optional_features import OptionalFeature
from studiorum.data.models.subclasses import Subclass


def _class_feature(name: str, level: int, entries: list[Any]) -> ClassFeature:
    return ClassFeature.model_validate(
        {
            "name": name,
            "source": "PHB",
            "className": "Fighter",
            "classSource": "PHB",
            "level": level,
            "header": 1,
            "entries": entries,
        }
    )


def _subclass_feature(name: str, level: int, entries: list[Any]) -> SubclassFeature:
    return SubclassFeature.model_validate(
        {
            "name": name,
            "source": "PHB",
            "className": "Fighter",
            "classSource": "PHB",
            "subclassShortName": "Champion",
            "subclassSource": "PHB",
            "level": level,
            "entries": entries,
        }
    )


FEATURES = {
    "Fighting Style|Fighter||1": _class_feature(
        "Fighting Style",
        1,
        [
            "Adopt a style.",
            {
                "type": "options",
                "entries": [
                    {"type": "refOptionalfeature", "optionalfeature": "Archery"}
                ],
            },
        ],
    ),
    "Extra Attack|Fighter||5": _class_feature("Extra Attack", 5, ["Attack twice."]),
    "Archery|PHB": OptionalFeature.model_validate(
        {
            "name": "Archery",
            "source": "PHB",
            "featureType": ["FS:F"],
            "prerequisite": [{"level": {"level": 1}}],
            "entries": ["+2 to ranged attacks."],
        }
    ),
    "Champion|Fighter||Champion||3": _subclass_feature(
        "Champion",
        3,
        [
            "The archetypal champion.",
            {
                "type": "refSubclassFeature",
                "subclassFeature": "Improved Critical|Fighter||Champion||3",
            },
        ],
    ),
    "Improved Critical|Fighter||Champion||3": _subclass_feature(
        "Improved Critical", 3, ["Crit on 19."]
    ),
    "Remarkable Athlete|Fighter||Champion||7": _subclass_feature(
        "Remarkable Athlete", 7, ["Half proficiency."]
    ),
}


def _catalogue() -> Mock:
    return Mock(find_uid=Mock(side_effect=lambda _kind, uid: FEATURES.get(uid)))


FIGHTER = Class.model_validate(
    {
        "name": "Fighter",
        "source": "PHB",
        "hd": {"number": 1, "faces": 10},
        "proficiency": ["str", "con"],
        "startingProficiencies": {
            "armor": ["light", "medium", "heavy", "shield"],
            "weapons": ["simple", "martial"],
            "skills": [{"choose": {"from": ["acrobatics", "athletics"], "count": 2}}],
        },
        "classTableGroups": [
            {
                "title": "Spell Slots per Spell Level",
                "colLabels": ["1st"],
                "rowsSpellProgression": [[0]] * 2 + [[2]] * 18,
            }
        ],
        "classFeatures": [
            "Fighting Style|Fighter||1",
            {"classFeature": "Extra Attack|Fighter||5", "gainSubclassFeature": False},
        ],
    }
)


def test_a_class_has_core_traits_a_table_and_its_features() -> None:
    entries = class_entries(FIGHTER, _catalogue())
    texts = [e for e in entries if isinstance(e, str)]
    table = next(e for e in entries if isinstance(e, dict) and e["type"] == "table")
    features = [e for e in entries if isinstance(e, dict) and e["type"] == "entries"]

    assert texts[:3] == [
        "{@b Hit Point Die:} {@dice 1d10|D10|Hit die} per Fighter level",
        "{@b Hit Points at Level 1:} 10 + Con. modifier",
        "{@b Hit Points per additional Fighter Level:} {@dice 1d10|D10|Hit die}"
        " + your Con. modifier, or, 6 + your Con. modifier",
    ]
    assert "{@b Skill Proficiencies:} {@i Choose 2:} Acrobatics or Athletics." in texts
    assert "{@b Weapon Proficiencies:} Simple and Martial weapons" in texts
    assert (
        "{@b Armor Training:} Light, Medium and Heavy armor and "
        "{@item shield|XPHB|Shields}"
    ) in texts
    assert table["wide"] is True
    assert table["colLabels"] == ["Level", "Proficiency Bonus", "Features", "1st"]
    assert table["rows"][0] == ["1st", "+2", "Fighting Style", "—"]
    assert table["rows"][4] == ["5th", "+3", "Extra Attack", 2]
    assert [f["name"] for f in features] == [
        "Level 1: Fighting Style",
        "Level 5: Extra Attack",
    ]
    option = features[0]["entries"][1]["entries"][0]
    assert option == {
        "type": "entries",
        "name": "Archery",
        "entries": ["+2 to ranged attacks."],
    }


def test_a_subclass_is_its_features_with_levels_on_the_nested_ones() -> None:
    champion = Subclass.model_validate(
        {
            "name": "Champion",
            "shortName": "Champion",
            "source": "PHB",
            "className": "Fighter",
            "classSource": "PHB",
            "subclassFeatures": [
                "Champion|Fighter||Champion||3",
                "Remarkable Athlete|Fighter||Champion||7",
            ],
        }
    )

    entries = subclass_entries(champion, _catalogue())

    assert "name" not in entries[0]
    assert entries[0]["entries"][1]["name"] == "Level 3: Improved Critical"
    assert entries[1]["name"] == "Remarkable Athlete"


def test_features_are_looked_up_by_uid() -> None:
    catalogue = _catalogue()
    class_entries(FIGHTER, catalogue)

    catalogue.find_uid.assert_any_call(
        ContentType.CLASS_FEATURE, "Fighting Style|Fighter||1"
    )
    catalogue.find_uid.assert_any_call(ContentType.OPTIONALFEATURE, "Archery|PHB")


def test_nested_features_lists_the_features_a_feature_refers_to() -> None:
    # Class and subclass features only, not the options a feature offers
    assert nested_features(
        "Champion|Fighter||Champion||3", ContentType.SUBCLASS_FEATURE, _catalogue()
    ) == [(ContentType.SUBCLASS_FEATURE, "Improved Critical|Fighter||Champion||3")]
    assert (
        nested_features(
            "Fighting Style|Fighter||1", ContentType.CLASS_FEATURE, _catalogue()
        )
        == []
    )
