"""Item input parsing utilities for various input formats."""

import re
import sys
from pathlib import Path
from typing import TextIO

from ..models.items import ItemRarity, ItemType


class ItemInputParser:
    """Utility class for parsing item names and parameters from various input sources.

    Handles file-based input, stdin input, and value range parsing for the
    item compendium generation system.
    """

    @staticmethod
    def parse_value_range(value_str: str) -> tuple[float | None, float | None]:
        """Parse value strings like '1-10', '5+', '<100' into min/max.

        Args:
            value_str: Value range string to parse

        Returns:
            Tuple of (min_value, max_value)

        Raises:
            ValueError: If the value string format is invalid
        """
        if not value_str.strip():
            raise ValueError("Value string cannot be empty")

        value_str = value_str.strip().lower()

        # Less than: "<100"
        if value_str.startswith("<"):
            try:
                max_value = float(value_str[1:].strip())
            except ValueError as e:
                raise ValueError(f"Invalid value number: {value_str}") from e

            if max_value < 0:
                raise ValueError("Value must be non-negative")

            return (None, max_value)

        # Greater than: ">50" or "50+"
        if value_str.startswith(">") or value_str.endswith("+"):
            if value_str.startswith(">"):
                value_part = value_str[1:].strip()
            else:
                value_part = value_str[:-1].strip()

            try:
                min_value = float(value_part)
            except ValueError as e:
                raise ValueError(f"Invalid value number: {value_str}") from e

            if min_value < 0:
                raise ValueError("Value must be non-negative")

            return (min_value, None)

        # Range: "1-10"
        if "-" in value_str:
            parts = value_str.split("-", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid value range format: {value_str}")

            try:
                min_value = float(parts[0].strip())
                max_value = float(parts[1].strip())
            except ValueError as e:
                raise ValueError(f"Invalid value numbers in range: {value_str}") from e

            if min_value < 0 or max_value < 0:
                raise ValueError("Values must be non-negative")

            if min_value > max_value:
                raise ValueError("Minimum value cannot be greater than maximum value")

            return (min_value, max_value)

        # Single value: "50"
        try:
            value = float(value_str)
        except ValueError as e:
            raise ValueError(f"Unable to parse value string: {value_str}") from e

        if value < 0:
            raise ValueError("Value must be non-negative")

        return (value, value)

    @staticmethod
    def parse_item_names_from_file(file_path: Path) -> list[str]:
        """Parse item names from file (one per line, ignore comments).

        Args:
            file_path: Path to the file containing item names

        Returns:
            List of item names

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Item file not found: {file_path}")

        if not file_path.is_file():
            raise OSError(f"Path is not a file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return ItemInputParser._parse_item_names_from_stream(f)
        except UnicodeDecodeError as e:
            raise OSError(f"File encoding error: {e}") from e
        except OSError as e:
            raise OSError(f"Error reading file: {e}") from e

    @staticmethod
    def parse_item_names_from_stdin() -> list[str]:
        """Parse item names from stdin.

        Returns:
            List of item names

        Raises:
            IOError: If stdin cannot be read
        """
        try:
            return ItemInputParser._parse_item_names_from_stream(sys.stdin)
        except OSError as e:
            raise OSError(f"Error reading from stdin: {e}") from e

    @staticmethod
    def _parse_item_names_from_stream(stream: TextIO) -> list[str]:
        """Parse item names from a text stream.

        Args:
            stream: Text stream to read from

        Returns:
            List of cleaned item names
        """
        item_names = []

        for line_num, line in enumerate(stream, 1):
            # Remove whitespace and skip empty lines
            line = line.strip()
            if not line:
                continue

            # Skip comment lines (starting with # or //)
            if line.startswith("#") or line.startswith("//"):
                continue

            # Handle inline comments
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if "//" in line:
                line = line.split("//", 1)[0].strip()

            # Skip if nothing left after removing comments
            if not line:
                continue

            # Handle multiple items on one line (comma or semicolon separated)
            if "," in line or ";" in line:
                # Split by comma or semicolon
                separators = r"[,;]"
                parts = re.split(separators, line)
                for part in parts:
                    item_name = part.strip()
                    if item_name:
                        item_names.append(item_name)
            else:
                item_names.append(line)

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in item_names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)

        return unique_names

    @staticmethod
    def parse_item_type(type_str: str) -> ItemType | str:
        """Parse item type string with fuzzy matching.

        Args:
            type_str: Item type string to parse

        Returns:
            ItemType enum or normalized string
        """
        if not type_str.strip():
            return type_str

        type_str = type_str.strip().lower()

        # Try exact enum match first
        try:
            return ItemType(type_str)
        except ValueError:
            pass

        # Try common aliases/abbreviations
        type_aliases = {
            "weapons": "weapon",
            "arms": "weapon",
            "armour": "armor",
            "armors": "armor",
            "shields": "shield",
            "gear": "adventuring gear",
            "adventuring": "adventuring gear",
            "adventure gear": "adventuring gear",
            "tools": "tool",
            "mounts": "mount",
            "vehicles": "vehicle",
            "treasures": "treasure",
            "magic item": "wondrous item",
            "magic items": "wondrous item",
            "wondrous": "wondrous item",
            "potions": "potion",
            "scrolls": "scroll",
            "rings": "ring",
            "rods": "rod",
            "staves": "staff",
            "staffs": "staff",
            "wands": "wand",
            "ammo": "ammunition",
            "arrows": "ammunition",
        }

        normalized_type = type_aliases.get(type_str, type_str)

        # Try enum match with normalized type
        try:
            return ItemType(normalized_type)
        except ValueError:
            # Return as normalized string for fuzzy matching later
            return normalized_type

    @staticmethod
    def parse_rarity_list(rarity_str: str) -> list[str | ItemRarity]:
        """Parse a comma-separated list of item rarities.

        Args:
            rarity_str: Comma-separated rarity names

        Returns:
            List of normalized rarity values
        """
        if not rarity_str.strip():
            return []

        rarities: list[str | ItemRarity] = []
        for rarity in rarity_str.split(","):
            rarity_name = rarity.strip().lower()
            if rarity_name:
                # Try to match to enum
                try:
                    rarities.append(ItemRarity(rarity_name))
                except ValueError:
                    # Keep as string for fuzzy matching
                    rarities.append(rarity_name)

        return rarities

    @staticmethod
    def parse_type_list(type_str: str) -> list[str | ItemType]:
        """Parse a comma-separated list of item types.

        Args:
            type_str: Comma-separated type names

        Returns:
            List of normalized type values
        """
        if not type_str.strip():
            return []

        types = []
        for item_type in type_str.split(","):
            parsed_type = ItemInputParser.parse_item_type(item_type.strip())
            if parsed_type:
                types.append(parsed_type)

        return types

    @staticmethod
    def parse_source_list(source_str: str) -> list[str]:
        """Parse a comma-separated list of source abbreviations.

        Args:
            source_str: Comma-separated source abbreviations

        Returns:
            List of normalized source abbreviations
        """
        if not source_str.strip():
            return []

        sources = []
        for src in source_str.split(","):
            src_name = src.strip().upper()
            if src_name:
                sources.append(src_name)

        return sources

    @staticmethod
    def parse_weapon_property_list(property_str: str) -> list[str]:
        """Parse a comma-separated list of weapon properties.

        Args:
            property_str: Comma-separated property names

        Returns:
            List of normalized property names
        """
        if not property_str.strip():
            return []

        properties = []
        for prop in property_str.split(","):
            prop_name = prop.strip().lower()
            if prop_name:
                # Handle common abbreviations
                property_aliases = {
                    "2h": "two-handed",
                    "2-h": "two-handed",
                    "1h": "one-handed",
                    "1-h": "one-handed",
                    "versa": "versatile",
                    "rea": "reach",
                    "fin": "finesse",
                    "ran": "ranged",
                    "throw": "thrown",
                }
                properties.append(property_aliases.get(prop_name, prop_name))

        return properties

    @staticmethod
    def parse_damage_type_list(damage_str: str) -> list[str]:
        """Parse a comma-separated list of damage types.

        Args:
            damage_str: Comma-separated damage type names

        Returns:
            List of normalized damage type names
        """
        if not damage_str.strip():
            return []

        damage_types = []
        for damage_type in damage_str.split(","):
            damage_name = damage_type.strip().lower()
            if damage_name:
                # Handle common abbreviations
                damage_aliases = {
                    "slash": "slashing",
                    "pier": "piercing",
                    "blud": "bludgeoning",
                    "mag": "magical",
                    "elem": "elemental",
                }
                damage_types.append(damage_aliases.get(damage_name, damage_name))

        return damage_types

    @staticmethod
    def validate_item_file(file_path: Path) -> tuple[bool, str]:
        """Validate that a file contains parseable item names.

        Args:
            file_path: Path to the item file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return (False, f"File does not exist: {file_path}")

            if not file_path.is_file():
                return (False, f"Path is not a file: {file_path}")

            item_names = ItemInputParser.parse_item_names_from_file(file_path)

            if not item_names:
                return (False, "File contains no valid item names")

            return (True, f"Found {len(item_names)} item names")

        except Exception as e:
            return (False, f"Error validating file: {e}")

    @staticmethod
    def merge_item_lists(*item_lists: list[str]) -> list[str]:
        """Merge multiple item name lists, removing duplicates.

        Args:
            *item_lists: Variable number of item name lists

        Returns:
            Merged list with duplicates removed, preserving order
        """
        seen = set()
        merged = []

        for item_list in item_lists:
            for item_name in item_list:
                # Normalize for comparison but preserve original case
                normalized = item_name.strip().lower()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged.append(item_name.strip())

        return merged

    @staticmethod
    def parse_weight_constraint(weight_str: str) -> tuple[float | None, float | None]:
        """Parse weight constraint strings like '<5', '1-10', '3+'.

        Args:
            weight_str: Weight constraint string

        Returns:
            Tuple of (min_weight, max_weight)

        Raises:
            ValueError: If the weight string format is invalid
        """
        if not weight_str.strip():
            raise ValueError("Weight string cannot be empty")

        weight_str = weight_str.strip().lower()

        # Less than: "<5"
        if weight_str.startswith("<"):
            try:
                max_weight = float(weight_str[1:].strip())
            except ValueError as e:
                raise ValueError(f"Invalid weight number: {weight_str}") from e

            if max_weight < 0:
                raise ValueError("Weight must be non-negative")

            return (None, max_weight)

        # Greater than: ">3" or "3+"
        if weight_str.startswith(">") or weight_str.endswith("+"):
            if weight_str.startswith(">"):
                weight_part = weight_str[1:].strip()
            else:
                weight_part = weight_str[:-1].strip()

            try:
                min_weight = float(weight_part)
            except ValueError as e:
                raise ValueError(f"Invalid weight number: {weight_str}") from e

            if min_weight < 0:
                raise ValueError("Weight must be non-negative")

            return (min_weight, None)

        # Range: "1-10"
        if "-" in weight_str:
            parts = weight_str.split("-", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid weight range format: {weight_str}")

            try:
                min_weight = float(parts[0].strip())
                max_weight = float(parts[1].strip())
            except ValueError as e:
                raise ValueError(
                    f"Invalid weight numbers in range: {weight_str}"
                ) from e

            if min_weight < 0 or max_weight < 0:
                raise ValueError("Weights must be non-negative")

            if min_weight > max_weight:
                raise ValueError("Minimum weight cannot be greater than maximum weight")

            return (min_weight, max_weight)

        # Single weight: "5"
        try:
            weight = float(weight_str)
        except ValueError as e:
            raise ValueError(f"Unable to parse weight string: {weight_str}") from e

        if weight < 0:
            raise ValueError("Weight must be non-negative")

        return (weight, weight)

    @staticmethod
    def normalize_equipment_pack_name(pack_name: str) -> str:
        """Normalize equipment pack name for consistent matching.

        Args:
            pack_name: Equipment pack name to normalize

        Returns:
            Normalized pack name
        """
        if not pack_name.strip():
            return pack_name

        name = pack_name.strip().lower()

        # Handle common variations
        pack_aliases = {
            "burglar": "burglar's pack",
            "burglars": "burglar's pack",
            "explorer": "explorer's pack",
            "explorers": "explorer's pack",
            "priest": "priest's pack",
            "priests": "priest's pack",
            "scholar": "scholar's pack",
            "scholars": "scholar's pack",
            "entertainer": "entertainer's pack",
            "entertainers": "entertainer's pack",
        }

        return pack_aliases.get(name, name)
