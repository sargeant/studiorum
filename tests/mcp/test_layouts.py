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


def test_a_creature_shows_initiative_immunities_and_challenge_as_5etools_does() -> None:
    dragon = {
        "name": "Dragon",
        "source": "XMM",
        "size": ["H"],
        "type": "dragon",
        "dex": 10,
        "initiative": {"proficiency": 2},
        "immune": [
            "poison",
            {"immune": ["bludgeoning", "slashing"], "note": "from nonmagical attacks"},
        ],
        "conditionImmune": ["charmed", "poisoned"],
        "cr": {"cr": "17", "xpLair": 20000},
        "spellcasting": [
            {"name": "Spellcasting", "spells": {"6": {"slots": 1, "spells": ["x"]}}}
        ],
    }

    text = to_markdown("creature", dragon)

    assert "**Initiative** +12 (22)" in text
    assert (
        "**Immunities** poison; bludgeoning and slashing from nonmagical attacks"
        in text
    )
    assert "**Condition Immunities** charmed, poisoned" in text
    assert "**Challenge** 17 (18,000 XP, or 20,000 in its lair; PB +6)" in text
    assert "Level 6 (1 slot): x" in text


def test_an_optional_feature_names_its_type_and_cost() -> None:
    invocation = {
        "name": "Agonizing Blast",
        "source": "XPHB",
        "featureType": ["EI"],
        "prerequisite": [
            {
                "level": {
                    "level": 2,
                    "class": {
                        "name": "Warlock",
                        "source": "XPHB",
                        "visibleStats": True,
                    },
                }
            }
        ],
        "consumes": {"name": "Sorcery Point", "amount": 2},
        "entries": ["Add your Charisma modifier."],
    }

    text = to_markdown("optionalfeature", invocation)

    assert "*Eldritch Invocation* · *XPHB*" in text
    assert "**Prerequisite** 2nd level Warlock\n**Cost** 2 Sorcery Points" in text


def test_a_language_shows_its_kind_and_origin() -> None:
    cant = {
        "name": "Thieves' Cant",
        "source": "XPHB",
        "type": "rare",
        "origin": "Various criminal guilds",
    }

    text = to_markdown("language", cant)

    assert text == (
        "# Thieves' Cant\n\n*Rare language* · *XPHB*\n\n"
        "**Origin:** Various criminal guilds"
    )
