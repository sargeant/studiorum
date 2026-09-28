"""Markdown layouts for get_content."""

from studiorum.mcp.layouts import to_markdown


def test_an_item_group_lists_its_items() -> None:
    group = {
        "name": "Potion of Resistance",
        "source": "DMG",
        "type": "P",
        "rarity": "uncommon",
        "items": ["Potion of Acid Resistance", "Potion of Cold Resistance|DMG"],
    }

    text = to_markdown("item", group)

    assert "Multiple variations of this item exist" in text
    assert "Potion of Cold Resistance" in text
    assert "{@" not in text


def test_a_race_shows_speed_abilities_and_subraces_as_5etools_does() -> None:
    fairy = {
        "name": "Fairy",
        "source": "MPMM",
        "size": ["S"],
        "speed": {"walk": 30, "fly": True},
        "ability": [
            {"choose": {"weighted": {"from": ["str", "dex"], "weights": [2, 1]}}}
        ],
        "_subraces": [{"name": "Fairy (Pixie)", "source": "MPMM"}],
    }

    text = to_markdown("race", fairy)

    assert "**Speed** 30 ft., fly equal to your walking speed" in text
    assert "**Ability Scores** From Strength and Dexterity choose one ability" in text
    assert "**Subraces** Fairy (Pixie)" in text


def test_a_vehicle_shows_5etools_lines_and_its_stations() -> None:
    text = to_markdown(
        "vehicle",
        {
            "name": "Wasp Ship",
            "source": "AAG",
            "vehicleType": "SPELLJAMMER",
            "capCrew": 5,
            "hull": {"ac": 15, "hp": 250, "dt": 15},
            "weapon": [
                {
                    "name": "Ballista",
                    "crew": 3,
                    "ac": 15,
                    "hp": 50,
                    "entries": ["Load, aim, fire."],
                    "action": [{"name": "Bolt", "entries": ["It hits."]}],
                }
            ],
        },
    )

    assert "| **Hit Points:** 250 | **Crew:** 5 |" in text
    assert "## Ballista (Crew: 3)\n\n**Armor Class:** 15\n**Hit Points:** 50" in text
    assert "***Bolt.*** It hits." in text


def test_a_creature_vehicle_is_laid_out_as_a_creature() -> None:
    text = to_markdown(
        "vehicle",
        {
            "name": "Stahlmaster",
            "source": "DD",
            "vehicleType": "CREATURE",
            "size": ["L"],
            "ac": [16],
            "hp": {"average": 67, "formula": "9d10 + 18"},
            "speed": {"walk": 30},
        },
    )

    assert "**Hit Points** 67 (9d10 + 18)" in text


def test_a_background_leaves_its_ability_scores_to_its_entries() -> None:
    sage = {
        "name": "Sage",
        "source": "XPHB",
        "ability": [
            {
                "choose": {
                    "weighted": {"from": ["con", "int", "wis"], "weights": [2, 1]}
                }
            },
            {
                "choose": {
                    "weighted": {"from": ["con", "int", "wis"], "weights": [1, 1, 1]}
                }
            },
        ],
        "entries": [
            {
                "type": "list",
                "items": [
                    {
                        "type": "item",
                        "name": "Ability Scores:",
                        "entry": "Constitution, Intelligence, Wisdom",
                    }
                ],
            }
        ],
    }

    text = to_markdown("background", sage)

    assert "Ability Score Increase" not in text
    assert "**Ability Scores:** Constitution, Intelligence, Wisdom" in text


def test_a_feat_shows_its_increase_as_5etools_does() -> None:
    boon = {
        "name": "Boon of Irresistible Offense",
        "source": "XPHB",
        "category": "EB",
        "ability": [{"choose": {"from": ["str", "dex"]}, "max": 30}],
        "entries": [
            "You gain the following benefits.",
            {"type": "entries", "name": "Overcome Defenses", "entries": ["Text."]},
        ],
    }

    text = to_markdown("feat", boon)

    assert "## Ability Score Increase" in text
    assert "Increase your Strength or Dexterity by 1, to a maximum of 30." in text
    assert boon["entries"][1]["name"] == "Overcome Defenses"


def test_a_feat_with_a_list_gains_its_increase_without_changing_the_data() -> None:
    feat = {
        "name": "Athlete",
        "source": "XPHB",
        "ability": [{"choose": {"from": ["str", "dex"]}}],
        "entries": [
            {
                "type": "list",
                "items": [{"type": "item", "name": "Climb Speed.", "entry": "Text."}],
            }
        ],
    }

    first = to_markdown("feat", feat)

    assert first == to_markdown("feat", feat)
    assert first.count("Increase your Strength or Dexterity by 1") == 1
    assert len(feat["entries"][0]["items"]) == 1
