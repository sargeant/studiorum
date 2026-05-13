#!/usr/bin/env python3
"""Encounter XP calculator for 5e 2024 rules."""

import os
import sys
from pathlib import Path

os.environ["STUDIORUM_PROGRESS"] = "false"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logfire  # noqa: E402

logfire.configure(console=False, send_to_logfire=False)

from studiorum.core.logging.logger import StudiorumLogger  # noqa: E402

StudiorumLogger._initialized = True

from studiorum.cli.utils import get_omnidexer  # noqa: E402

XP_BUDGET = {
    1: (50, 75, 100),
    2: (100, 150, 200),
    3: (150, 225, 400),
    4: (250, 375, 500),
    5: (500, 750, 1100),
    6: (600, 1000, 1400),
    7: (750, 1300, 1700),
    8: (1000, 1700, 2100),
    9: (1300, 2000, 2600),
    10: (1600, 2300, 3100),
    11: (1900, 2900, 4100),
    12: (2200, 3700, 4700),
    13: (2600, 4200, 5400),
    14: (2900, 4900, 6200),
    15: (3300, 5400, 7800),
    16: (3800, 6100, 9800),
    17: (4500, 7200, 11700),
    18: (5000, 8700, 14200),
    19: (5500, 10700, 17200),
    20: (6400, 13200, 22000),
}


def parse_creature_file(filepath: Path) -> list[tuple[int, str, str | None]]:
    """Parse creature file. Returns list of (count, name, source)."""
    creatures = []
    for line in filepath.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("|")
        name_part = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else None

        tokens = name_part.split(maxsplit=1)
        if tokens[0].isdigit():
            count = int(tokens[0])
            name = tokens[1] if len(tokens) > 1 else ""
        else:
            count = 1
            name = name_part

        if name:
            creatures.append((count, name, source))

    return creatures


def find_creature(omnidexer, name: str, source: str | None):
    """Find creature by name, optionally filtered by source."""
    results = list(omnidexer.find_all("creature", name))

    if source:
        filtered = [
            c for c in results if c.source.abbreviation.upper() == source.upper()
        ]
        if filtered:
            return filtered[0]

    for c in results:
        if c.name.lower() == name.lower():
            return c

    return results[0] if results else None


CR_TO_XP = {
    "0": 10,
    "1/8": 25,
    "1/4": 50,
    "1/2": 100,
    "1": 200,
    "2": 450,
    "3": 700,
    "4": 1100,
    "5": 1800,
    "6": 2300,
    "7": 2900,
    "8": 3900,
    "9": 5000,
    "10": 5900,
    "11": 7200,
    "12": 8400,
    "13": 10000,
    "14": 11500,
    "15": 13000,
    "16": 15000,
    "17": 18000,
    "18": 20000,
    "19": 22000,
    "20": 25000,
    "21": 33000,
    "22": 41000,
    "23": 50000,
    "24": 62000,
    "25": 75000,
    "26": 90000,
    "27": 105000,
    "28": 120000,
    "29": 135000,
    "30": 155000,
}


def get_xp(creature) -> int:
    """Get XP value for a creature."""
    if not creature.cr:
        return 0
    cr_str = str(creature.cr).lower().strip()
    return CR_TO_XP.get(cr_str, 0)


def difficulty_label(total_xp: int, party_size: int, level: int) -> str:
    """Return difficulty label for given XP total."""
    low, mod, high = XP_BUDGET[level]
    budget_low = low * party_size
    budget_mod = mod * party_size
    budget_high = high * party_size

    if total_xp >= budget_high:
        return "HIGH"
    elif total_xp >= budget_mod:
        return "Moderate"
    elif total_xp >= budget_low:
        return "Low"
    else:
        return "Trivial"


def main():
    if len(sys.argv) < 2:
        print("Usage: encounter-report.py <creatures.txt> [party_size]")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    party_size = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    creatures = parse_creature_file(filepath)
    if not creatures:
        print("No creatures found in file.")
        sys.exit(1)

    omnidexer = get_omnidexer()

    print(f"\n{'=' * 60}")
    print("ENCOUNTER REPORT")
    print(f"{'=' * 60}\n")

    total_xp = 0
    print(f"{'Count':<6} {'Creature':<30} {'CR':<6} {'XP':<8}")
    print("-" * 60)

    for count, name, source in creatures:
        creature = find_creature(omnidexer, name, source)
        if creature:
            xp = get_xp(creature)
            line_xp = xp * count
            total_xp += line_xp
            cr_str = str(creature.cr) if creature.cr else "?"
            print(f"{count:<6} {creature.name:<30} {cr_str:<6} {line_xp:>7,}")
        else:
            print(f"{count:<6} {name:<30} {'???':<6} {'NOT FOUND':>8}")

    print("-" * 60)
    print(f"{'TOTAL':<44} {total_xp:>7,} XP\n")

    print(f"Difficulty for party of {party_size}:\n")
    print(f"{'Level':<6} {'Low':<12} {'Moderate':<12} {'High':<12} {'Rating':<10}")
    print("-" * 60)

    for level in range(1, 21):
        low, mod, high = XP_BUDGET[level]
        budget_low = low * party_size
        budget_mod = mod * party_size
        budget_high = high * party_size

        rating = difficulty_label(total_xp, party_size, level)

        print(
            f"{level:<6} {budget_low:>7,}     {budget_mod:>7,}     "
            f"{budget_high:>7,}     {rating:<10}"
        )

    print()


if __name__ == "__main__":
    main()
