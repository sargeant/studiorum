"""The encounter XP maths, checked against the DMG tables."""

from __future__ import annotations

import pytest

from studiorum.core.encounter import (
    budgets,
    creature_xp,
    difficulty,
    multiplier,
    xp_range,
)

FOUR_FIFTHS = [5, 5, 5, 5]


def test_2014_thresholds_sum_per_character() -> None:
    assert budgets(FOUR_FIFTHS, "2014") == {
        "easy": 1000,
        "medium": 2000,
        "hard": 3000,
        "deadly": 4400,
    }
    assert budgets([3], "2014")["deadly"] == 400
    assert budgets([18], "2014")["medium"] == 4100
    assert budgets([1, 20], "2014")["easy"] == 25 + 2800


def test_2024_budgets() -> None:
    assert budgets(FOUR_FIFTHS, "2024") == {
        "low": 2000,
        "moderate": 3000,
        "high": 4400,
    }


@pytest.mark.parametrize(
    ("cr", "xp"),
    [
        ("1/4", 50),
        ("30", 155000),
        ({"cr": "1/8", "xp": 5}, 5),
        ({"cr": "14", "xpLair": 13000}, 11500),
        ("Unknown", None),
        (None, None),
    ],
)
def test_creature_xp(cr: object, xp: int | None) -> None:
    assert creature_xp(cr) == xp


@pytest.mark.parametrize(
    ("creatures", "party", "expected"),
    [
        (1, 4, 1.0),
        (2, 4, 1.5),
        (6, 4, 2.0),
        (7, 4, 2.5),
        (14, 4, 3.0),
        (15, 4, 4.0),
        (1, 2, 1.5),
        (3, 2, 2.5),
        (11, 2, 4.0),
        (15, 2, 5.0),
        (1, 6, 0.5),
        (15, 6, 3.0),
    ],
)
def test_2014_multiplier(creatures: int, party: int, expected: float) -> None:
    assert multiplier(creatures, party, "2014") == expected


def test_2024_has_no_multiplier() -> None:
    assert multiplier(15, 2, "2024") == 1.0


def test_difficulty() -> None:
    assert difficulty(600, FOUR_FIFTHS, "2014") == "trivial"
    assert difficulty(1000, FOUR_FIFTHS, "2014") == "easy"
    assert difficulty(9000, FOUR_FIFTHS, "2014") == "deadly"
    assert difficulty(2000, FOUR_FIFTHS, "2024") == "low"
    assert difficulty(2001, FOUR_FIFTHS, "2024") == "moderate"
    assert difficulty(5000, FOUR_FIFTHS, "2024") == "above high"


def test_xp_range() -> None:
    assert xp_range("medium", FOUR_FIFTHS, "2014") == (2000, 2999)
    assert xp_range("deadly", FOUR_FIFTHS, "2014") == (4400, 5800)
    assert xp_range("low", FOUR_FIFTHS, "2024") == (1000, 2000)
    assert xp_range("moderate", FOUR_FIFTHS, "2024") == (2001, 3000)
    with pytest.raises(ValueError, match="2024 difficulties are low, moderate, high"):
        xp_range("deadly", FOUR_FIFTHS, "2024")
