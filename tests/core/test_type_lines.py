"""The lines 5etools shows around an entity's entries; lines.mjs checks all of them."""

from studiorum.core.compact import compact_entries, compact_heading
from studiorum.core.models.backgrounds import Background
from studiorum.core.models.deities import Deity
from studiorum.core.models.facilities import Facility
from studiorum.core.models.feats import Feat
from studiorum.core.models.objects import Object
from studiorum.core.models.optional_features import OptionalFeature
from studiorum.core.models.races import Race
from studiorum.core.models.rule_types import Hazard
from studiorum.core.models.traps import Trap


def test_a_simple_trap_has_its_subtitle_then_entries_then_parts() -> None:
    trap = Trap.model_validate(
        {
            "name": "Bear Trap",
            "source": "XGE",
            "trapHazType": "SMPL",
            "rating": [{"tier": 1, "threat": "dangerous"}],
            "entries": ["Iron jaws."],
            "trigger": ["Stepping on it."],
            "countermeasures": ["A DC 10 check."],
        }
    )

    assert compact_entries(trap, None) == [
        "{@i Dangerous Simple Trap (1st–4th Level)}",
        "Iron jaws.",
        {"type": "entries", "name": "Trigger", "entries": ["Stepping on it."]},
        {"type": "entries", "name": "Countermeasures", "entries": ["A DC 10 check."]},
    ]


def test_a_classic_trap_lists_trigger_and_duration_first() -> None:
    trap = Trap.model_validate(
        {
            "name": "Rolling Sphere",
            "source": "XDMG",
            "trapHazType": "TRP",
            "entries": ["A stone ball."],
            "trigger": ["A pressure plate."],
            "duration": [{"type": "instant"}],
        }
    )

    assert compact_entries(trap, None) == [
        "{@i Trap}",
        {
            "type": "list",
            "style": "list-hang-notitle",
            "items": [
                {"type": "item", "name": "Trigger:", "entries": ["A pressure plate."]},
                {"type": "item", "name": "Duration:", "entries": ["Instantaneous"]},
            ],
        },
        "A stone ball.",
    ]


def test_a_hazard_is_subtitled_by_its_kind() -> None:
    hazard = Hazard.model_validate(
        {
            "name": "Hailstorm",
            "source": "FRAiF",
            "trapHazType": "ENV",
            "entries": ["Ice."],
        }
    )

    assert compact_entries(hazard, None) == ["{@i Environmental Hazard}", "Ice."]


def test_a_feat_has_its_category_and_prerequisite_and_the_increase_in_its_list() -> (
    None
):
    feat = Feat.model_validate(
        {
            "name": "Initiate of High Sorcery",
            "source": "DSotDQ",
            "category": "O",
            "prerequisite": [{"level": 4}],
            "ability": [{"choose": {"from": ["int", "wis", "cha"]}}],
            "entries": [
                "You learn magic.",
                {"type": "list", "items": ["You learn a cantrip."]},
            ],
        }
    )

    assert compact_entries(feat, None) == [
        "{@i Origin Feat (Prerequisite: 4th level)}",
        "You learn magic.",
        {
            "type": "list",
            "items": [
                "Increase your Intelligence, Wisdom, or Charisma by 1, "
                "to a maximum of 20.",
                "You learn a cantrip.",
            ],
        },
    ]


def test_a_deity_has_labelled_lines_in_order_and_its_title_in_the_heading() -> None:
    deity = Deity.model_validate(
        {
            "name": "Paladine",
            "source": "DSotDQ",
            "pantheon": "Dragonlance",
            "title": "the valiant warrior",
            "alignment": ["L", "G"],
            "symbol": "Silver triangle",
            "category": "Good",
        }
    )

    assert compact_entries(deity, None) == [
        "{@b Alignment:} Lawful Good",
        "{@b Category:} Good",
        "{@b Pantheon:} Dragonlance",
        "{@b Symbol:} Silver triangle",
    ]
    assert compact_heading(deity, "Paladine") == "Paladine, The Valiant Warrior"


def test_an_optional_feature_has_its_cost_and_type() -> None:
    feature = OptionalFeature.model_validate(
        {
            "name": "Twinned Spell",
            "source": "PHB",
            "featureType": ["MM"],
            "consumes": {"name": "Sorcery Point", "amountMin": 1, "amountMax": 9},
            "entries": ["A second target."],
        }
    )

    assert compact_entries(feature, None) == [
        "{@i Cost: 1–9 Sorcery Points}",
        "A second target.",
        "{@note Type: Metamagic}",
    ]


def test_a_facility_lists_its_prerequisite_space_hirelings_and_orders() -> None:
    facility = Facility.model_validate(
        {
            "name": "Arcane Study",
            "source": "XDMG",
            "facilityType": "special",
            "level": 5,
            "prerequisite": [{"spellcastingFocus": ["arcane"]}],
            "space": ["roomy"],
            "hirelings": [{"exact": 1}],
            "orders": ["craft"],
            "entries": ["Books."],
        }
    )

    assert compact_entries(facility, None) == [
        "{@i Level 5 Bastion Facility}",
        {
            "type": "list",
            "style": "list-hang-notitle",
            "items": [
                {
                    "type": "item",
                    "name": "Prerequisite:",
                    "entry": "Ability to use an {@item Arcane Focus|XPHB} as a "
                    "{@variantrule Spellcasting Focus|XPHB}",
                },
                {
                    "type": "item",
                    "name": "Space:",
                    "entry": "Roomy  {@style [{@tip 16 sq|16 squares}]|muted;small}",
                },
                {"type": "item", "name": "Hirelings:", "entry": "1"},
                {"type": "item", "name": "Order:", "entry": "Craft"},
            ],
        },
        "Books.",
    ]


def test_an_object_has_its_size_attributes_and_actions() -> None:
    thing = Object.model_validate(
        {
            "name": "Boilerdrak",
            "source": "DSotDQ",
            "size": ["L"],
            "objectType": "SW",
            "ac": 15,
            "hp": 100,
            "immune": ["poison", "psychic"],
            "entries": ["A dragon-shaped device."],
            "actionEntries": [
                {"type": "entries", "name": "Flames", "entries": ["Fire."]}
            ],
        }
    )

    assert compact_entries(thing, None) == [
        "{@i Large object}",
        "{@b Armor Class:} 15",
        "{@b Hit Points:} 100",
        "{@b Damage Immunities:} poison, psychic",
        "A dragon-shaped device.",
        {"type": "entries", "name": "Flames", "entries": ["Fire."]},
    ]


def test_a_race_lists_its_attributes_before_its_entries() -> None:
    race = Race.model_validate(
        {
            "name": "Dhampir",
            "source": "RHW",
            "size": ["S", "M"],
            "speed": {"walk": 35, "climb": True},
            "creatureTypes": ["humanoid"],
            "entries": [
                {"type": "entries", "name": "Spider Climb", "entries": ["Up."]}
            ],
        }
    )

    assert compact_entries(race, None) == [
        {
            "type": "list",
            "style": "list-hang-notitle",
            "items": [
                {"type": "item", "name": "Size:", "entry": "Small or Medium"},
                {
                    "type": "item",
                    "name": "Speed:",
                    "entry": "35 feet, climb equal to your walking speed",
                },
            ],
        },
        {"type": "entries", "name": "Spider Climb", "entries": ["Up."]},
    ]


def test_a_background_puts_its_prerequisite_first() -> None:
    background = Background.model_validate(
        {
            "name": "Knight of Solamnia",
            "source": "DSotDQ",
            "prerequisite": [{"campaign": ["Dragonlance"]}],
            "entries": ["You are a knight."],
        }
    )

    assert compact_entries(background, None) == [
        "Prerequisite: Dragonlance Campaign",
        "You are a knight.",
    ]
