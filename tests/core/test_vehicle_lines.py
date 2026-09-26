"""What 5etools shows for a vehicle; lines.mjs checks every vehicle in the data."""

import pytest

from studiorum.core.models.vehicles import Vehicle
from studiorum.core.vehicle_lines import (
    VehicleSection,
    cost_text,
    vehicle_block,
    weight_text,
)


def test_a_ship_has_its_attributes_hull_and_parts() -> None:
    ship = Vehicle.model_validate(
        {
            "name": "Battle Balloon",
            "source": "AI",
            "vehicleType": "SHIP",
            "size": "G",
            "dimensions": ["80 ft.", "20 ft."],
            "terrain": ["air"],
            "capCrew": 20,
            "capPassenger": 10,
            "capCargo": 1,
            "pace": 9,
            "str": 18,
            "dex": 17,
            "con": 20,
            "int": 0,
            "wis": 0,
            "cha": 0,
            "immune": ["poison", "psychic"],
            "hull": {"ac": 15, "hp": 500, "dt": 15},
            "movement": [
                {
                    "name": "Propeller",
                    "ac": 12,
                    "hp": 100,
                    "hpNote": "-5 ft. speed per 25 damage taken",
                    "speed": [{"mode": "air", "entries": ["80 ft."]}],
                }
            ],
            "weapon": [
                {
                    "name": "Harpoon Gun",
                    "count": 3,
                    "ac": 15,
                    "hp": 50,
                    "entries": ["Hit."],
                }
            ],
        }
    )

    block = vehicle_block(ship)

    assert block.type_line == "{@i Gargantuan vehicle (air; 80 ft. by 20 ft.)}"
    assert block.attributes == [
        "{@b Creature Capacity} 20 crew, 10 passengers",
        "{@b Cargo Capacity} 1 ton",
        "{@b Travel Pace} 9 miles per hour (216 miles per day)",
    ]
    assert block.note == "[{@b Speed} 90 ft.]"
    assert block.abilities == {
        "str": 18,
        "dex": 17,
        "con": 20,
        "int": 0,
        "wis": 0,
        "cha": 0,
    }
    assert block.details == [("Damage Immunities", "poison, psychic")]
    assert block.sections == [
        VehicleSection(
            "Hull", ["{@b Armor Class} 15", "{@b Hit Points} 500 (damage threshold 15)"]
        ),
        VehicleSection(
            "Movement: Propeller",
            [
                "{@b Armor Class} 12",
                "{@b Hit Points} 100; -5 ft. speed per 25 damage taken",
            ],
            [
                {
                    "type": "list",
                    "style": "list-hang-notitle",
                    "items": [
                        {"type": "item", "name": "Speed (air)", "entries": ["80 ft."]}
                    ],
                }
            ],
        ),
        VehicleSection(
            "Weapons: Harpoon Gun (3)",
            ["{@b Armor Class} 15", "{@b Hit Points} 50 each"],
            ["Hit."],
        ),
    ]


def test_a_spelljammer_ship_has_a_summary_table_and_weapon_stations() -> None:
    ship = Vehicle.model_validate(
        {
            "name": "Wasp Ship",
            "source": "AAG",
            "vehicleType": "SPELLJAMMER",
            "dimensions": ["80 ft.", "20 ft."],
            "capCrew": 5,
            "capCargo": 10,
            "cost": 2000000,
            "pace": {"fly": "5½"},
            "speed": {"fly": 50},
            "hull": {"ac": 15, "acFrom": ["wood"], "hp": 250, "dt": 15},
            "weapon": [
                {
                    "name": "Ballista",
                    "crew": 3,
                    "ac": 15,
                    "hp": 50,
                    "costs": [{"cost": 5000, "note": "ballista"}],
                    "entries": ["Load, aim, fire."],
                    "action": [{"name": "Bolt", "entries": ["Hit."]}],
                }
            ],
        }
    )

    block = vehicle_block(ship)

    assert block.summary == {
        "type": "table",
        "style": "summary",
        "colStyles": ["col-6", "col-6"],
        "rows": [
            ["{@b Armor Class:} 15 (wood)", "{@b Cargo:} 10 tons"],
            ["{@b Hit Points:} 250", "{@b Crew:} 5"],
            ["{@b Damage Threshold:} 15", "{@b Keel/Beam:} 80 ft./20 ft."],
            [
                "{@b Speed:} fly 50 ft. ({@tip 5½ mph|132 miles per day})",
                "{@b Cost:} 20,000 gp",
            ],
        ],
    }
    assert block.sections == [
        VehicleSection(
            "Ballista (Crew: 3)",
            [
                "{@b Armor Class:} 15",
                "{@b Hit Points:} 50",
                "{@b Cost:} 50 gp (ballista)",
            ],
            ["Load, aim, fire.", {"name": "Bolt", "entries": ["Hit."]}],
        )
    ]


def test_an_elemental_airship_lists_passengers_and_its_stations() -> None:
    ship = Vehicle.model_validate(
        {
            "name": "Lyrandar Skyskiff",
            "source": "EFA",
            "vehicleType": "ELEMENTAL_AIRSHIP",
            "capCrew": 2,
            "capPassenger": 2,
            "capCargo": 0.5,
            "cost": 2000000,
            "pace": {"fly": 7},
            "speed": {"fly": {"number": 70, "condition": "[hover]"}, "canHover": True},
            "hull": {"ac": 18, "hp": 150, "dt": 5},
            "station": [
                {
                    "name": "Helm",
                    "size": ["S"],
                    "ac": 15,
                    "hp": 20,
                    "entries": ["Steer."],
                }
            ],
        }
    )

    block = vehicle_block(ship)

    assert block.summary is not None
    assert block.summary["rows"][1] == ["{@b Hit Points:} 150", "{@b Passengers:} 2"]
    assert block.summary["rows"][3][0] == (
        "{@b Speed:} {@tip 7 mph|168 miles per day} (fly 70 ft. [hover])"
    )
    assert block.sections == [
        VehicleSection(
            "Helm",
            ["{@i Small Object}", "{@b Armor Class:} 15", "{@b Hit Points:} 20"],
            ["Steer."],
        )
    ]


def test_an_infernal_war_machine_has_its_thresholds_and_stations() -> None:
    machine = Vehicle.model_validate(
        {
            "name": "Devil's Ride",
            "source": "BGDIA",
            "vehicleType": "INFWAR",
            "size": "L",
            "weight": 500,
            "capCreature": 1,
            "capCargo": 2500,
            "speed": 120,
            "dex": 18,
            "hp": {"hp": 30, "dt": 5, "mt": 10},
            "trait": [
                {"name": "Stunt", "entries": ["Wheelie."]},
                {"name": "Jump", "entries": ["Far."]},
            ],
            "actionStation": [{"name": "Helm", "entries": ["Drive."]}],
        }
    )

    block = vehicle_block(machine)

    assert block.type_line == "{@i Large vehicle (500 lb.)}"
    assert block.attributes == [
        "{@b Creature Capacity} 1 Medium creatures",
        "{@b Cargo Capacity} 1 ton, 500 lb.",
        "{@b Armor Class} 23 (19 while motionless)",
        "{@b Hit Points} 30 (damage threshold 5, mishap threshold 10)",
        "{@b Speed} 120 ft.",
    ]
    assert block.note == "[{@b Travel Pace} 12 miles per hour (288 miles per day)]"
    assert [s.title for s in block.sections] == ["Traits", "Action Stations"]
    assert [t["name"] for t in block.sections[0].entries] == ["Jump", "Stunt"]


def test_a_vehicle_type_without_a_layout_is_an_error() -> None:
    vehicle = Vehicle.model_validate(
        {"name": "Rowboat", "source": "DMG", "vehicleType": "OBJECT"}
    )

    with pytest.raises(ValueError, match="OBJECT"):
        vehicle_block(vehicle)


@pytest.mark.parametrize(
    ("cost", "text"),
    [(2000000, "20,000 gp"), (150, "15 sp"), (5, "5 cp"), (0, "0 gp")],
)
def test_costs_are_in_the_largest_whole_coin(cost: int, text: str) -> None:
    assert cost_text({"cost": cost}) == text


def test_weight_is_in_tons_and_pounds() -> None:
    assert weight_text(4000) == "2 tons"
    assert weight_text(100) == "100 lb."
