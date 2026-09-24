#!/usr/bin/env python3
"""
Fast encounter XP calculator using pre-computed creature XP data.

First run: generates .static-creature-xp.json from studiorum data (~10s)
Subsequent runs: loads from cache (~0.01s)

Usage:
    scripts/static-encounter-calc.py <creatures.txt> [party_size]
    scripts/static-encounter-calc.py --rebuild  # force rebuild cache
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / ".static-creature-xp.json"

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


def build_cache() -> dict[str, dict]:
    """Build creature XP cache from studiorum data."""
    import os

    os.environ["STUDIORUM_PROGRESS"] = "false"
    sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

    import logfire

    logfire.configure(console=False, send_to_logfire=False)

    from studiorum.core.logging.logger import StudiorumLogger

    StudiorumLogger._initialized = True

    from studiorum.core.config.unified_config import load_config
    from studiorum.services import build_services

    print("Building creature XP cache (one-time operation)...")
    omnidexer = build_services(load_config()).omnidexer

    cache: dict[str, dict] = {}
    creatures = list(omnidexer.get_all_by_type("creature"))

    for creature in creatures:
        cr_str = str(creature.cr).lower().strip() if creature.cr else "0"
        xp = CR_TO_XP.get(cr_str, 0)

        key = f"{creature.name.lower()}|{creature.source.abbreviation.lower()}"
        cache[key] = {
            "name": creature.name,
            "source": creature.source.abbreviation,
            "cr": str(creature.cr) if creature.cr else "?",
            "xp": xp,
        }

        name_only = creature.name.lower()
        if name_only not in cache:
            cache[name_only] = cache[key]

    return cache


def save_cache(cache: dict[str, dict]) -> None:
    """Save cache to disk using orjson."""
    import orjson

    CACHE_FILE.write_bytes(orjson.dumps(cache, option=orjson.OPT_INDENT_2))
    print(f"Cache saved: {CACHE_FILE} ({len(cache)} entries)")


def load_cache() -> dict[str, dict]:
    """Load cache from disk."""
    import orjson

    return orjson.loads(CACHE_FILE.read_bytes())


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


def lookup_creature(
    cache: dict[str, dict], name: str, source: str | None
) -> dict | None:
    """Look up creature in cache."""
    if source:
        key = f"{name.lower()}|{source.lower()}"
        if key in cache:
            return cache[key]

    return cache.get(name.lower())


def difficulty_label(total_xp: int, party_size: int, level: int) -> str:
    """Return difficulty label for given XP total."""
    low, mod, high = XP_BUDGET[level]
    budget_low = low * party_size
    budget_mod = mod * party_size
    budget_high = high * party_size

    if total_xp >= budget_high:
        return "HIGH"
    if total_xp >= budget_mod:
        return "Moderate"
    if total_xp >= budget_low:
        return "Low"
    return "Trivial"


def main():
    if len(sys.argv) < 2:
        print("Usage: static-encounter-calc.py <creatures.txt> [party_size]")
        print("       static-encounter-calc.py --rebuild")
        sys.exit(1)

    if sys.argv[1] == "--rebuild":
        cache = build_cache()
        save_cache(cache)
        sys.exit(0)

    filepath = Path(sys.argv[1])
    party_size = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    if not CACHE_FILE.exists():
        cache = build_cache()
        save_cache(cache)
    else:
        cache = load_cache()

    creatures = parse_creature_file(filepath)
    if not creatures:
        print("No creatures found in file.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("ENCOUNTER REPORT")
    print(f"{'=' * 60}\n")

    total_xp = 0
    print(f"{'Count':<6} {'Creature':<30} {'CR':<6} {'XP':<8}")
    print("-" * 60)

    for count, name, source in creatures:
        creature = lookup_creature(cache, name, source)
        if creature:
            line_xp = creature["xp"] * count
            total_xp += line_xp
            print(
                f"{count:<6} {creature['name']:<30} {creature['cr']:<6} {line_xp:>7,}"
            )
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
