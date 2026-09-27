"""Spell input parsing utilities for various input formats."""

import re
import sys
from pathlib import Path
from typing import TextIO


class SpellInputParser:
    """Utility class for parsing spell names and parameters from various input sources.

    Handles file-based input, stdin input, and level range parsing for the
    spell book generation system.
    """

    @staticmethod
    def parse_level_range(level_str: str) -> tuple[int | None, int | None]:
        """Parse level strings like '1-5', '3+', '0' into min/max values.

        Args:
            level_str: Level range string to parse

        Returns:
            Tuple of (min_level, max_level)

        Raises:
            ValueError: If the level string format is invalid
        """
        if not level_str.strip():
            raise ValueError("Level string cannot be empty")

        level_str = level_str.strip().lower()

        # Single level: "3" or "cantrip"
        if level_str.isdigit():
            level = int(level_str)
            if level < 0 or level > 9:
                raise ValueError(f"Spell level must be 0-9, got {level}")
            return (level, level)

        # Handle "cantrip" or "cantrips"
        if level_str in ["cantrip", "cantrips"]:
            return (0, 0)

        # Range: "1-5"
        if "-" in level_str:
            parts = level_str.split("-", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid level range format: {level_str}")

            try:
                min_level = int(parts[0].strip())
                max_level = int(parts[1].strip())
            except ValueError as e:
                raise ValueError(f"Invalid level numbers in range: {level_str}") from e

            if min_level < 0 or min_level > 9 or max_level < 0 or max_level > 9:
                raise ValueError("Spell levels must be 0-9")

            if min_level > max_level:
                raise ValueError("Minimum level cannot be greater than maximum level")

            return (min_level, max_level)

        # Level and above: "3+"
        if level_str.endswith("+"):
            try:
                min_level = int(level_str[:-1].strip())
            except ValueError as e:
                raise ValueError(f"Invalid level number: {level_str}") from e

            if min_level < 0 or min_level > 9:
                raise ValueError("Spell level must be 0-9")

            return (min_level, 9)

        # Try to parse as individual level names
        level_names = {
            "first": 1,
            "1st": 1,
            "second": 2,
            "2nd": 2,
            "third": 3,
            "3rd": 3,
            "fourth": 4,
            "4th": 4,
            "fifth": 5,
            "5th": 5,
            "sixth": 6,
            "6th": 6,
            "seventh": 7,
            "7th": 7,
            "eighth": 8,
            "8th": 8,
            "ninth": 9,
            "9th": 9,
        }

        if level_str in level_names:
            level = level_names[level_str]
            return (level, level)

        raise ValueError(f"Unable to parse level string: {level_str}")

    @staticmethod
    def parse_spell_names_from_file(file_path: Path) -> list[str]:
        """Parse spell names from file (one per line, ignore comments).

        Args:
            file_path: Path to the file containing spell names

        Returns:
            List of spell names

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Spell file not found: {file_path}")

        if not file_path.is_file():
            raise OSError(f"Path is not a file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return SpellInputParser._parse_spell_names_from_stream(f)
        except UnicodeDecodeError as e:
            raise OSError(f"File encoding error: {e}") from e
        except OSError as e:
            raise OSError(f"Error reading file: {e}") from e

    @staticmethod
    def parse_spell_names_from_stdin() -> list[str]:
        """Parse spell names from stdin.

        Returns:
            List of spell names

        Raises:
            IOError: If stdin cannot be read
        """
        try:
            return SpellInputParser._parse_spell_names_from_stream(sys.stdin)
        except OSError as e:
            raise OSError(f"Error reading from stdin: {e}") from e

    @staticmethod
    def _parse_spell_names_from_stream(stream: TextIO) -> list[str]:
        """Parse spell names from a text stream.

        Args:
            stream: Text stream to read from

        Returns:
            List of cleaned spell names
        """
        spell_names = []

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

            # Handle multiple spells on one line (comma or semicolon separated)
            if "," in line or ";" in line:
                # Split by comma or semicolon
                separators = r"[,;]"
                parts = re.split(separators, line)
                for part in parts:
                    spell_name = part.strip()
                    if spell_name:
                        spell_names.append(spell_name)
            else:
                spell_names.append(line)

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in spell_names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)

        return unique_names

    @staticmethod
    def parse_class_list(class_str: str) -> list[str]:
        """Parse a comma-separated list of class names.

        Args:
            class_str: Comma-separated class names

        Returns:
            List of normalized class names
        """
        if not class_str.strip():
            return []

        classes = []
        for cls in class_str.split(","):
            cls_name = cls.strip().lower()
            if cls_name:
                # Map common abbreviations
                class_map = {
                    "wiz": "wizard",
                    "sorc": "sorcerer",
                    "lock": "warlock",
                    "rang": "ranger",
                    "pal": "paladin",
                    "bar": "barbarian",
                    "figh": "fighter",
                }

                classes.append(class_map.get(cls_name, cls_name))

        return classes

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
    def validate_spell_file(file_path: Path) -> tuple[bool, str]:
        """Validate that a file contains parseable spell names.

        Args:
            file_path: Path to the spell file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return (False, f"File does not exist: {file_path}")

            if not file_path.is_file():
                return (False, f"Path is not a file: {file_path}")

            spell_names = SpellInputParser.parse_spell_names_from_file(file_path)

            if not spell_names:
                return (False, "File contains no valid spell names")

            return (True, f"Found {len(spell_names)} spell names")

        except Exception as e:
            return (False, f"Error validating file: {e}")

    @staticmethod
    def merge_spell_lists(*spell_lists: list[str]) -> list[str]:
        """Merge multiple spell name lists, removing duplicates.

        Args:
            *spell_lists: Variable number of spell name lists

        Returns:
            Merged list with duplicates removed, preserving order
        """
        seen = set()
        merged = []

        for spell_list in spell_lists:
            for spell_name in spell_list:
                # Normalize for comparison but preserve original case
                normalized = spell_name.strip().lower()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged.append(spell_name.strip())

        return merged

    @staticmethod
    def split_level_list(level_list_str: str) -> list[int]:
        """Parse a comma-separated list of spell levels.

        Args:
            level_list_str: Comma-separated level numbers

        Returns:
            List of spell level integers

        Raises:
            ValueError: If any level is invalid
        """
        if not level_list_str.strip():
            return []

        levels = []
        for level_str in level_list_str.split(","):
            level_str = level_str.strip()
            if not level_str:
                continue

            try:
                level = int(level_str)
                if level < 0 or level > 9:
                    raise ValueError(f"Spell level must be 0-9, got {level}")
                levels.append(level)
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid spell level: {level_str}") from e
                raise

        return sorted(list(set(levels)))  # Remove duplicates and sort
