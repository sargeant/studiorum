"""The lines 5etools shows around an entity's entries; lines.mjs checks all of them."""

from studiorum.core.compact import compact_entries
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
