"""
Typed entry models to replace dict[str, Any] patterns.

This module provides specific Pydantic models for different types of entries
that appear in D&D content, replacing the generic dict[str, Any] pattern
with type-safe, validated structures.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseEntry(BaseModel):
    """Base class for all entry types."""

    model_config = ConfigDict(extra="forbid")


class TextEntry(BaseEntry):
    """Simple text entry."""

    type: Literal["text"] = "text"
    text: str = Field(..., description="The text content")


class ActionEntry(BaseEntry):
    """Action entry with attack and damage information."""

    type: Literal["action"] = "action"
    name: str = Field(..., description="Name of the action")
    attack: dict[str, Any] | None = Field(None, description="Attack details")
    damage: dict[str, Any] | None = Field(None, description="Damage details")
    description: str | None = Field(None, description="Action description")


class TableEntry(BaseEntry):
    """Table entry with headers and rows."""

    type: Literal["table"] = "table"
    caption: str | None = Field(None, description="Table caption")
    colLabels: list[str] | None = Field(None, description="Column headers")
    colStyles: list[str] | None = Field(None, description="Column styles")
    rows: list[list[str]] = Field(default_factory=list, description="Table rows")


class ListEntry(BaseEntry):
    """List entry with items and style."""

    type: Literal["list"] = "list"
    style: str | None = Field(
        None, description="List style (e.g., list, unordered, list-hang-notitle)"
    )
    items: list[str | dict[str, Any]] = Field(
        default_factory=list, description="List items"
    )


class InsetEntry(BaseEntry):
    """Inset/sidebar entry with contained content."""

    type: Literal["inset"] = "inset"
    name: str | None = Field(None, description="Inset title")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Inset content"
    )


class EntriesEntry(BaseEntry):
    """Container entry with nested entries."""

    type: Literal["entries"] = "entries"
    name: str | None = Field(None, description="Section name")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Nested entries"
    )


class OptionsEntry(BaseEntry):
    """Options entry for choices."""

    type: Literal["options"] = "options"
    count: int | None = Field(None, description="Number of options to choose")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Available options"
    )


class VariantEntry(BaseEntry):
    """Variant rule entry."""

    type: Literal["variant"] = "variant"
    name: str = Field(..., description="Variant name")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Variant description"
    )
    source: str | None = Field(None, description="Variant source")


class QuoteEntry(BaseEntry):
    """Quote or flavor text entry."""

    type: Literal["quote"] = "quote"
    entries: list[str] = Field(default_factory=list, description="Quote text")
    by: str | None = Field(None, description="Quote attribution")


class ImageEntry(BaseEntry):
    """Image entry."""

    type: Literal["image"] = "image"
    href: dict[str, str] | None = Field(None, description="Image reference")
    title: str | None = Field(None, description="Image title")
    altText: str | None = Field(None, description="Image alt text")


class ItemEntry(BaseEntry):
    """Item reference entry."""

    type: Literal["item"] = "item"
    name: str = Field(..., description="Item name")
    source: str | None = Field(None, description="Item source")


class SpellEntry(BaseEntry):
    """Spell reference entry."""

    type: Literal["spell"] = "spell"
    name: str = Field(..., description="Spell name")
    source: str | None = Field(None, description="Spell source")


class CreatureEntry(BaseEntry):
    """Creature reference entry."""

    type: Literal["creature"] = "creature"
    name: str = Field(..., description="Creature name")
    source: str | None = Field(None, description="Creature source")


class GenericEntry(BaseEntry):
    """Fallback for unknown entry types."""

    type: str = Field(..., description="Entry type")

    # Allow extra fields for unknown entry types
    model_config = ConfigDict(extra="allow")

    @field_validator("type")
    @classmethod
    def validate_type_not_known(cls, v: str) -> str:
        """Warn about unknown entry types."""
        known_types = {
            "text",
            "action",
            "table",
            "list",
            "inset",
            "entries",
            "options",
            "variant",
            "quote",
            "image",
            "item",
            "spell",
            "creature",
        }
        if v in known_types:
            raise ValueError(
                f"Use specific entry class for type '{v}' instead of GenericEntry"
            )
        return v


# Union type for all possible entry types
Entry = (
    str
    | TextEntry
    | ActionEntry
    | TableEntry
    | ListEntry
    | InsetEntry
    | EntriesEntry
    | OptionsEntry
    | VariantEntry
    | QuoteEntry
    | ImageEntry
    | ItemEntry
    | SpellEntry
    | CreatureEntry
    | GenericEntry  # Fallback for unknown types
)


def create_entry(data: str | dict[str, Any]) -> Entry:
    """
    Factory function to create the appropriate entry type from data.

    Args:
        data: Either a string (for simple text) or dict with type information

    Returns:
        Appropriate Entry subclass instance

    Raises:
        ValueError: If data format is invalid
    """
    if isinstance(data, str):
        return data

    if not isinstance(data, dict):
        raise ValueError(f"Entry data must be str or dict, got {type(data)}")

    entry_type = data.get("type")
    if not entry_type:
        raise ValueError("Entry dict must have 'type' field")

    # Map entry types to their classes
    entry_classes = {
        "text": TextEntry,
        "action": ActionEntry,
        "table": TableEntry,
        "list": ListEntry,
        "inset": InsetEntry,
        "entries": EntriesEntry,
        "options": OptionsEntry,
        "variant": VariantEntry,
        "quote": QuoteEntry,
        "image": ImageEntry,
        "item": ItemEntry,
        "spell": SpellEntry,
        "creature": CreatureEntry,
    }

    entry_class = entry_classes.get(entry_type)
    if entry_class:
        return entry_class.model_validate(data)
    else:
        # Use GenericEntry for unknown types
        return GenericEntry.model_validate(data)


def validate_entries(entries: list[str | dict[str, Any]]) -> list[Entry]:
    """
    Validate a list of entry data and convert to typed Entry objects.

    Args:
        entries: List of entry data (strings or dicts)

    Returns:
        List of validated Entry objects

    Raises:
        ValueError: If any entry is invalid
    """
    return [create_entry(entry) for entry in entries]
