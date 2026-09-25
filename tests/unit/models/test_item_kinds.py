"""An item's kind: its type, else its category, as filters and compendiums use it."""

import pytest

from studiorum.core.models.item_filters import ItemFilterCriteria
from studiorum.core.models.items import Item


def _item(**data: object) -> Item:
    return Item.model_validate({"name": "Thing", "source": "DMG", **data})


def test_an_untyped_wondrous_item_is_a_wondrous_item() -> None:
    item = _item(wondrous=True, rarity="rare")

    assert item.get_type_text() == ""
    assert item.get_kind_text() == "wondrous item"
    assert item.get_item_metadata_line() == "Wondrous item, rare"


def test_kinds_are_lower_case() -> None:
    assert _item(type="LA").get_kind_text() == "light armor"
    assert _item().get_kind_text() == "other"


@pytest.mark.parametrize(
    ("wanted", "kind", "matches"),
    [
        ("armor", "light armor", True),
        ("armor", "wondrous item", False),
        ("weapon", "ranged weapon", True),
        ("wondrous item", "wondrous item", True),
        ("potion", "light armor", False),
    ],
)
def test_a_type_filter_matches_the_kind_or_its_last_word(
    wanted: str, kind: str, matches: bool
) -> None:
    assert ItemFilterCriteria(item_types=[wanted]).matches_item_type(kind) is matches
