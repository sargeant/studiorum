"""Input parsing functions for creature filtering and collection."""

import sys
from pathlib import Path
from typing import Any


def parse_cr_value(cr_string: str) -> float | None:
    """Parse CR values including fractions: '1/4', '1/2', '0', '10', 'varies'.

    Args:
        cr_string: The CR string to parse

    Returns:
        Float CR value or None for variable CR

    Raises:
        ValueError: If CR string format is invalid
    """
    cr_string = cr_string.strip().lower()
    if cr_string in ["varies", "variable"]:
        return None  # Handle variable CR
    if "/" in cr_string:
        # Handle fractions: 1/4 = 0.25, 1/8 = 0.125, 1/2 = 0.5
        try:
            numerator, denominator = cr_string.split("/")
            return float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            raise ValueError(f"Invalid fractional CR format: {cr_string}")

    try:
        return float(cr_string)
    except ValueError:
        raise ValueError(f"Invalid CR value: {cr_string}")


def parse_cr_range(cr_string: str) -> tuple[float, float]:
    """Parse CR range formats: '1/4-5', '10+', '0', '<1'.

    Args:
        cr_string: The CR range string to parse

    Returns:
        Tuple of (min_cr, max_cr)

    Raises:
        ValueError: If CR range format is invalid
    """
    cr_string = cr_string.strip()

    if "+" in cr_string:
        # Handle "10+" format
        min_cr_str = cr_string.replace("+", "")
        min_cr = parse_cr_value(min_cr_str)
        if min_cr is None:
            raise ValueError(f"Variable CR not allowed in range: {cr_string}")
        return (min_cr, 30.0)  # Max CR in D&D

    elif "<" in cr_string:
        # Handle "<1" format
        max_cr_str = cr_string.replace("<", "")
        max_cr = parse_cr_value(max_cr_str)
        if max_cr is None:
            raise ValueError(f"Variable CR not allowed in range: {cr_string}")
        return (0.0, max_cr)

    elif "-" in cr_string:
        # Handle "1/4-5" format
        try:
            min_str, max_str = cr_string.split("-", 1)
            min_cr = parse_cr_value(min_str)
            max_cr = parse_cr_value(max_str)

            if min_cr is None or max_cr is None:
                raise ValueError(f"Variable CR not allowed in range: {cr_string}")

            if min_cr > max_cr:
                raise ValueError(f"Invalid CR range - min ({min_cr}) > max ({max_cr})")

            return (min_cr, max_cr)
        except ValueError as e:
            if "Variable CR" in str(e) or "Invalid CR range" in str(e):
                raise
            raise ValueError(f"Invalid CR range format: {cr_string}")

    else:
        # Single CR value
        cr = parse_cr_value(cr_string)
        if cr is None:
            raise ValueError(f"Variable CR not allowed in range: {cr_string}")
        return (cr, cr)


def parse_creature_type_data(creature: dict[str, Any]) -> tuple[str, list[str]]:
    """Parse 5e.tools creature type structure.

    Args:
        creature: Creature data dictionary from 5e.tools

    Returns:
        Tuple of (main_type, tags_list)
    """
    type_data = creature.get("type", "")

    if isinstance(type_data, str):
        # Simple string type
        return (type_data.lower(), [])
    elif isinstance(type_data, dict):
        # Complex type object: {"type": "humanoid", "tags": ["aarakocra"]}
        main_type = type_data.get("type", "").lower()
        tags = type_data.get("tags", [])
        # Normalize tags to lowercase strings
        normalized_tags = [
            tag.lower() if isinstance(tag, str) else str(tag).lower() for tag in tags
        ]
        return (main_type, normalized_tags)

    return ("unknown", [])


def detect_movement_abilities(creature: dict[str, Any]) -> dict[str, bool]:
    """Detect movement abilities from 5e.tools speed data.

    Args:
        creature: Creature data dictionary from 5e.tools

    Returns:
        Dictionary with movement ability flags
    """
    speed_data = creature.get("speed", {})
    if not isinstance(speed_data, dict):
        return {
            "has_fly_speed": False,
            "has_swim_speed": False,
            "has_climb_speed": False,
            "has_burrow_speed": False,
        }

    return {
        "has_fly_speed": "fly" in speed_data,
        "has_swim_speed": "swim" in speed_data,
        "has_climb_speed": "climb" in speed_data,
        "has_burrow_speed": "burrow" in speed_data,
    }


def detect_senses(creature: dict[str, Any]) -> dict[str, bool]:
    """Detect special senses from 5e.tools senses data.

    Args:
        creature: Creature data dictionary from 5e.tools

    Returns:
        Dictionary with sense ability flags
    """
    senses_data = creature.get("senses", [])

    if isinstance(senses_data, list):
        senses_text = " ".join(str(sense) for sense in senses_data)
    else:
        senses_text = str(senses_data)

    senses_text = senses_text.lower()

    return {
        "has_darkvision": "darkvision" in senses_text,
        "has_blindsight": "blindsight" in senses_text,
        "has_tremorsense": "tremorsense" in senses_text,
        "has_truesight": "truesight" in senses_text,
    }


def detect_special_abilities(creature: dict[str, Any]) -> dict[str, bool]:
    """Detect special abilities from creature data.

    Args:
        creature: Creature data dictionary from 5e.tools

    Returns:
        Dictionary with special ability flags
    """
    abilities = {
        "has_spellcasting": False,
        "has_innate_spellcasting": False,
        "has_legendary_actions": False,
        "has_multiattack": False,
        "has_reactions": False,
        "has_bonus_actions": False,
    }

    # Check spellcasting in dedicated field
    if creature.get("spellcasting"):
        abilities["has_spellcasting"] = True

    # Check traits for spellcasting abilities
    traits = creature.get("trait", [])
    if traits:
        for trait in traits:
            if isinstance(trait, dict) and "name" in trait:
                trait_name = str(trait["name"]).lower()
                if "spellcasting" in trait_name:
                    abilities["has_spellcasting"] = True
                elif "innate spellcasting" in trait_name:
                    abilities["has_innate_spellcasting"] = True

    # Check actions for multiattack
    actions = creature.get("action", [])
    if actions:
        for action in actions:
            if isinstance(action, dict) and "name" in action:
                action_name = str(action["name"]).lower()
                if "multiattack" in action_name:
                    abilities["has_multiattack"] = True

    # Check for legendary actions
    if creature.get("legendary"):
        abilities["has_legendary_actions"] = True

    # Check for reactions
    if creature.get("reaction"):
        abilities["has_reactions"] = True

    # Check for bonus actions
    if creature.get("bonus"):
        abilities["has_bonus_actions"] = True

    return abilities


def parse_creature_names_from_file(file_path: Path) -> list[str]:
    """Parse creature names from a file (one creature per line).

    Args:
        file_path: Path to the file containing creature names

    Returns:
        List of creature names

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file can't be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except PermissionError:
        raise PermissionError(f"Cannot read file: {file_path}")

    creature_names = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Handle inline comments
        if "#" in line:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

        creature_names.append(line)

    if not creature_names:
        raise ValueError(f"No creature names found in file: {file_path}")

    return creature_names


def parse_creature_names_from_stdin() -> list[str]:
    """Read creature names from stdin (one creature per line).

    Returns:
        List of creature names

    Raises:
        ValueError: If no names provided via stdin
    """
    if sys.stdin.isatty():
        raise ValueError("No input provided via stdin")

    lines = []
    try:
        for line in sys.stdin:
            lines.append(line.strip())
    except KeyboardInterrupt:
        raise ValueError("Input interrupted")

    creature_names = []
    for line in lines:
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Handle inline comments
        if "#" in line:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

        creature_names.append(line)

    if not creature_names:
        raise ValueError("No creature names found in stdin")

    return creature_names


def normalize_creature_name(name: str) -> str:
    """Normalize creature name for consistent matching.

    Args:
        name: Raw creature name

    Returns:
        Normalized creature name
    """
    # Basic normalization - trim whitespace
    name = name.strip()

    # Handle common variations (could be extended)
    # For now, just return the trimmed name
    return name


def validate_creature_list(names: list[str]) -> list[str]:
    """Validate and normalize a list of creature names.

    Args:
        names: List of creature names to validate

    Returns:
        List of validated and normalized names

    Raises:
        ValueError: If no valid names provided
    """
    if not names:
        raise ValueError("No creature names provided")

    valid_names = []
    for name in names:
        normalized = normalize_creature_name(name)
        if normalized:
            valid_names.append(normalized)

    if not valid_names:
        raise ValueError("No valid creature names found")

    # Remove duplicates while preserving order
    seen = set()
    deduplicated = []
    for name in valid_names:
        if name.lower() not in seen:
            seen.add(name.lower())
            deduplicated.append(name)

    return deduplicated


def parse_size_abbreviations(sizes: list[str]) -> list[str]:
    """Parse size names, expanding abbreviations to full names.

    Args:
        sizes: List of size names/abbreviations

    Returns:
        List of normalized size names
    """
    size_map = {
        "t": "tiny",
        "s": "small",
        "m": "medium",
        "l": "large",
        "h": "huge",
        "g": "gargantuan",
    }

    normalized = []
    for size in sizes:
        size_clean = size.strip().lower()
        if size_clean in size_map:
            normalized.append(size_map[size_clean])
        else:
            normalized.append(size_clean)

    return normalized


def parse_alignment_abbreviations(alignments: list[str]) -> list[str]:
    """Parse alignment names, expanding abbreviations.

    Args:
        alignments: List of alignment names/abbreviations

    Returns:
        List of normalized alignment names
    """
    alignment_map = {
        "lg": "lawful good",
        "ln": "lawful neutral",
        "le": "lawful evil",
        "ng": "neutral good",
        "n": "neutral",
        "ne": "neutral evil",
        "cg": "chaotic good",
        "cn": "chaotic neutral",
        "ce": "chaotic evil",
    }

    normalized = []
    for alignment in alignments:
        alignment_clean = alignment.strip().lower()
        if alignment_clean in alignment_map:
            normalized.append(alignment_map[alignment_clean])
        else:
            normalized.append(alignment_clean)

    return normalized
