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
