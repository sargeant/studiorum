"""Encounter XP maths for the 2014 and 2024 Dungeon Master's Guide.

The tables match 5etools' encounter builder (``js/encounterbuilder/consts``).
2014 thresholds are the least XP for each difficulty, and the creature total is
adjusted by a multiplier for the number of creatures and the party size. 2024
budgets are the most XP for each difficulty, with no multiplier.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

Rules = Literal["2024", "2014"]

XP_BY_CR = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700,
    "4": 1100, "5": 1800, "6": 2300, "7": 2900, "8": 3900, "9": 5000,
    "10": 5900, "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
    "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000,
    "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000,
}  # fmt: skip

# XP per character, indexed by level (index 0 unused)
XP_BY_LEVEL: dict[Rules, dict[str, tuple[int, ...]]] = {
    "2014": {
        "easy": (0, 25, 50, 75, 125, 250, 300, 350, 450, 550, 600, 800, 1000, 1100, 1250, 1400, 1600, 2000, 2100, 2400, 2800),
        "medium": (0, 50, 100, 150, 250, 500, 600, 750, 900, 1100, 1200, 1600, 2000, 2200, 2500, 2800, 3200, 3900, 4100, 4900, 5700),
        "hard": (0, 75, 150, 225, 375, 750, 900, 1100, 1400, 1600, 1900, 2400, 3000, 3400, 3800, 4300, 4800, 5900, 6300, 7300, 8500),
        "deadly": (0, 100, 200, 400, 500, 1100, 1400, 1700, 2100, 2400, 2800, 3600, 4500, 5100, 5700, 6400, 7200, 8800, 9500, 10900, 12700),
    },
    "2024": {
        "low": (0, 50, 100, 150, 250, 500, 600, 750, 1000, 1300, 1600, 1900, 2200, 2600, 2900, 3300, 3800, 4500, 5000, 5500, 6400),
        "moderate": (0, 75, 150, 225, 375, 750, 1000, 1300, 1700, 2000, 2300, 2900, 3700, 4200, 4900, 5400, 6100, 7200, 8700, 10700, 13200),
        "high": (0, 100, 200, 400, 500, 1100, 1400, 1700, 2100, 2600, 3100, 4100, 4700, 5400, 6200, 7800, 9800, 11700, 14200, 17200, 22000),
    },
}  # fmt: skip

# 2014 multiplier for 1, 2, 3-6, 7-10, 11-14 and 15+ creatures
_MULTIPLIERS = ((1, 1.0), (2, 1.5), (6, 2.0), (10, 2.5), (14, 3.0))


def difficulties(rules: Rules) -> tuple[str, ...]:
    """The difficulty names, easiest first."""
    return tuple(XP_BY_LEVEL[rules])


def budgets(levels: Sequence[int], rules: Rules) -> dict[str, int]:
    """Each difficulty's XP for the whole party, summed per character."""
    return {
        name: sum(by_level[level] for level in levels)
        for name, by_level in XP_BY_LEVEL[rules].items()
    }


def creature_xp(cr: Any) -> int | None:
    """XP for a 5etools ``cr``: ``"1/4"``, or ``{"cr": "14", "xp": 5}``. None if unknown."""
    if isinstance(cr, dict):
        if isinstance(cr.get("xp"), int):
            return int(cr["xp"])
        cr = cr.get("cr")
    return XP_BY_CR.get(str(cr)) if cr is not None else None


def multiplier(creatures: int, party_size: int, rules: Rules) -> float:
    """2014: the multiplier for the creature count, shifted for small and large parties."""
    if rules == "2024" or creatures < 1:
        return 1.0
    base = next((m for most, m in _MULTIPLIERS if creatures <= most), 4.0)
    if party_size < 3:
        return base + 1 if base >= 3 else base + 0.5
    if party_size > 5:
        return 3.0 if base == 4 else base - 0.5
    return base


def difficulty(adjusted_xp: int, levels: Sequence[int], rules: Rules) -> str:
    """The difficulty an encounter's adjusted XP reaches."""
    by_name = budgets(levels, rules)
    if rules == "2014":
        reached = [name for name, least in by_name.items() if adjusted_xp >= least]
        return reached[-1] if reached else "trivial"
    return next(
        (name for name, most in by_name.items() if adjusted_xp <= most), "above high"
    )


def xp_range(name: str, levels: Sequence[int], rules: Rules) -> tuple[int, int]:
    """The adjusted XP an encounter needs to count as the named difficulty.

    2014: from its threshold to the next; deadly runs as far again past hard.
    2024: from the easier budget to its own; low starts at half its budget.
    """
    by_name = budgets(levels, rules)
    names = list(by_name)
    if name not in by_name:
        raise ValueError(f"{rules} difficulties are {', '.join(names)}, not {name!r}")
    i = names.index(name)
    if rules == "2014":
        if i + 1 < len(names):
            return by_name[name], by_name[names[i + 1]] - 1
        return by_name[name], 2 * by_name[name] - by_name[names[i - 1]]
    low = by_name[names[i - 1]] + 1 if i else by_name[name] // 2
    return low, by_name[name]
