"""Common type definitions for the studiorum package.

This module defines reusable TypedDict schemas to replace dict[str, Any] usage
throughout the codebase. These provide better type safety while maintaining
flexibility for JSON-like data structures.
"""

from __future__ import annotations

from typing import Any, TypedDict


# Creature-specific Types
class SpeedDict(TypedDict, total=False):
    """Dict structure for complex speed values."""

    number: int
    condition: str


class DamageDict(TypedDict, total=False):
    """Dict structure for damage resistance/immunity/vulnerability."""

    type: str
    note: str
    preNote: str
    resist: list[str | dict[str, Any]]
    immune: list[str | dict[str, Any]]
    vulnerable: list[str | dict[str, Any]]
    special: str
    cond: bool


class CreatureTypeDict(TypedDict, total=False):
    """Dict structure for complex creature types."""

    type: str
    note: str
    prefix: str
    suffix: str
    choose: list[str]
    tag: str
    special: str


class AlignmentDict(TypedDict, total=False):
    """Dict structure for complex alignment values."""

    alignment: list[str]
    chance: int
    note: str


class ChallengeRatingDict(TypedDict, total=False):
    """Dict structure for complex challenge ratings.

    Supports various CR formats from 5etools:
    - Base CR with optional XP override
    - Lair variant with optional xpLair
    - Coven variant with optional xpCoven
    - Special text for custom displays
    """

    cr: str  # Base challenge rating (e.g., "24", "1/4")
    xp: int | None  # Optional base XP override
    lair: str | None  # Lair CR value (e.g., "24" for same CR in lair)
    xpLair: int | None  # Lair XP override (e.g., 75000 for Ancient Red Dragon)
    coven: str | None  # Coven CR value (e.g., "5" for Green Hag)
    xpCoven: int | None  # Coven XP override
    special: str | None  # Special text override for entire CR display


# Entry Parser Types
class EntryDict(TypedDict, total=False):
    """Base structure for 5e.tools entry dictionaries."""

    type: str
    name: str
    entries: list[Any]  # Recursive structure
    id: str
    page: int


class SectionEntry(EntryDict, total=False):
    """Section entry structure."""

    # Inherits type, name, entries, id, page from EntryDict


class TableEntry(EntryDict, total=False):
    """Table entry structure."""

    caption: str
    colLabels: list[str]
    rows: list[list[str]]


class InsetEntry(EntryDict, total=False):
    """Inset/sidebar entry structure."""

    # type is typically "inset" or "insetReadaloud"


class NestedEntriesEntry(EntryDict, total=False):
    """Nested entries structure (variant rules, subsections)."""

    # type is typically "entries"


class ParsingStatistics(TypedDict):
    """Statistics for entry parsing operations."""

    entries_processed: int
    errors_encountered: int
    source: str
    parent_name: str
    registry_statistics: dict[str, int]
    unknown_types: list[str]
