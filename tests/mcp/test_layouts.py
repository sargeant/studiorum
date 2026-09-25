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
