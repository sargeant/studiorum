"""
Typed entry models to replace dict[str, Any] patterns.

This module provides specific Pydantic models for different types of entries
that appear in 5e content, replacing the generic dict[str, Any] pattern
with type-safe, validated structures.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseEntry(BaseModel):
    """Base class for all entry types, with the props 5etools allows on any entry."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(None, description="Stable id for links into the entry")
    page: int | str | None = Field(None, description="Page number reference")
    data: dict[str, Any] | None = Field(
        None, description="Tool hints, e.g. a subrace's {'overwrite': 'Age'}"
    )
    srd: bool | str | None = Field(None, description="In the 2014 SRD (or its name)")
    srd52: bool | str | None = Field(None, description="In the 5.2 SRD (or its name)")
    basicRules: bool | None = Field(None, description="In the 2014 basic rules")
    basicRules2024: bool | None = Field(None, description="In the 2024 basic rules")


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
    rows: list[list[str | dict[str, Any] | int] | dict[str, Any]] = Field(
        default_factory=list, description="Table rows, or {'type': 'row'} objects"
    )
    footnotes: list[str | dict[str, Any]] | None = Field(
        None, description="Table footnotes"
    )
    colLabelRows: list[list[str | dict[str, Any]]] | None = Field(
        None, description="Several rows of column headers"
    )
    isStriped: bool | None = Field(None, description="Whether rows alternate shading")
    isNameGenerator: bool | None = Field(
        None, description="Whether the table rolls a name"
    )


class ListEntry(BaseEntry):
    """List entry with items and style."""

    type: Literal["list"] = "list"
    name: str | None = Field(None, description="List name/title")
    style: str | None = Field(
        None, description="List style (e.g., list, unordered, list-hang-notitle)"
    )
    items: list[str | dict[str, Any]] = Field(
        default_factory=list, description="List items"
    )
    columns: int | None = Field(None, description="Number of columns for list display")
    start: int | None = Field(None, description="First number of a numbered list")


class InsetEntry(BaseEntry):
    """Inset/sidebar entry with contained content."""

    type: Literal["inset"] = "inset"
    name: str | None = Field(None, description="Inset title")
    source: str | None = Field(None, description="Source book reference")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Inset content"
    )
    style: str | None = Field(None, description="Display style")
    header: int | None = Field(None, description="Heading level")
    token: dict[str, Any] | None = Field(None, description="Token image reference")
    otherSources: list[dict[str, Any]] | None = Field(
        None, description="Other sources with the same text"
    )
    version: dict[str, Any] | None = Field(
        None, alias="_version", description="5etools version marker"
    )
    className: str | None = Field(None, description="Class the inset belongs to")
    classSource: str | None = Field(None, description="Source of that class")
    subclassShortName: str | None = Field(None, description="Subclass it belongs to")
    subclassSource: str | None = Field(None, description="Source of that subclass")
    level: int | None = Field(None, description="Level of the feature it describes")


class EntriesEntry(BaseEntry):
    """Container entry with nested entries."""

    type: Literal["entries"] = "entries"
    name: str | None = Field(None, description="Section name")
    source: str | None = Field(None, description="Source reference")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Nested entries"
    )
    style: str | None = Field(None, description="Display style")
    alias: list[str] | None = Field(None, description="Other names for the section")
    ruleType: str | None = Field(None, description="Rule category (C, O, V, VO)")


class OptionsEntry(BaseEntry):
    """Options entry for choices."""

    type: Literal["options"] = "options"
    count: int | None = Field(None, description="Number of options to choose")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Available options"
    )
    style: str | None = Field(None, description="Display style")


class VariantEntry(BaseEntry):
    """Variant rule entry."""

    type: Literal["variant"] = "variant"
    name: str = Field(..., description="Variant name")
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Variant description"
    )
    source: str | None = Field(None, description="Variant source")
    version: dict[str, Any] | None = Field(
        None, alias="_version", description="5etools version marker"
    )


class QuoteEntry(BaseEntry):
    """Quote or flavor text entry."""

    type: Literal["quote"] = "quote"
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Quote text"
    )
    by: str | None = Field(None, description="Quote attribution")
    from_: str | None = Field(None, alias="from", description="Where the quote is from")
    style: str | None = Field(None, description="Display style")
    skipMarks: bool | None = Field(None, description="Omit the quotation marks")
    skipItalics: bool | None = Field(None, description="Don't italicise the quote")


class ImageEntry(BaseEntry):
    """Image entry."""

    type: Literal["image"] = "image"
    href: dict[str, str] | None = Field(None, description="Image reference")
    title: str | None = Field(None, description="Image title")
    altText: str | None = Field(None, description="Image alt text")
    credit: str | None = Field(None, description="Image credit/attribution")
    style: str | None = Field(None, description="Display style")
    width: int | None = Field(None, description="Width in pixels")
    height: int | None = Field(None, description="Height in pixels")
    maxWidth: int | None = Field(None, description="Maximum display width")
    maxHeight: int | None = Field(None, description="Maximum display height")
    imageType: str | None = Field(None, description="map, mapPlayer and so on")
    hrefThumbnail: dict[str, str] | None = Field(
        None, description="Thumbnail reference"
    )
    expectsLightBackground: bool | None = Field(
        None, description="Whether the image needs a light background"
    )
    grid: dict[str, Any] | None = Field(None, description="Map grid")
    mapParent: dict[str, Any] | None = Field(None, description="The map this one shows")
    mapRegions: list[dict[str, Any]] | None = Field(
        None, description="Named areas of the map"
    )
    mapName: str | None = Field(None, description="Name of the map")


class GalleryEntry(BaseEntry):
    """Gallery entry for multiple images with layout control."""

    type: Literal["gallery"] = "gallery"
    images: list[dict[str, Any]] = Field(
        default_factory=list, description="List of image entries in the gallery"
    )
    layout: str | None = Field(
        None, description="Gallery layout: grid, showcase, sequential, comparison"
    )
    caption: str | None = Field(None, description="Overall gallery caption")
    title: str | None = Field(None, description="Gallery title")
    columns: int | None = Field(
        None, ge=1, le=6, description="Number of columns for grid layouts"
    )
    maxWidth: str | None = Field(
        None, description="Maximum width specification for the gallery"
    )


class ItemEntry(BaseEntry):
    """A list item with a name, e.g. "**Dexterity.** You gain..."."""

    type: Literal["item"] = "item"
    name: str | None = Field(None, description="Item name")
    source: str | None = Field(None, description="Item source")
    entry: str | None = Field(None, description="The item's text")
    entries: list[str | dict[str, Any]] | None = Field(
        None, description="The item's text as entries"
    )
    nameDot: bool | None = Field(
        None, description="Whether a full stop follows the name"
    )
    style: str | None = Field(None, description="Display style")
    className: str | None = Field(None, description="Class the item belongs to")
    classSource: str | None = Field(None, description="Source of that class")
    subclassShortName: str | None = Field(None, description="Subclass it belongs to")
    subclassSource: str | None = Field(None, description="Source of that subclass")
    level: int | None = Field(None, description="Level of the feature it describes")


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


# Discriminated union for entry types that have a 'type' field with Literal values
# This enables efficient validation by checking the discriminator field first
DiscriminatedEntry = Annotated[
    TableEntry
    | ActionEntry
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
    | TextEntry,
    Field(discriminator="type"),
]

# Full Entry type includes discriminated entries, generic fallback, and plain strings
# Order matters: try discriminated first, then generic, then string
Entry = str | DiscriminatedEntry | GenericEntry


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

    # Map entry types to their classes - handle each case explicitly for proper typing
    if entry_type == "text":
        return TextEntry.model_validate(data)
    if entry_type == "action":
        return ActionEntry.model_validate(data)
    if entry_type == "table":
        return TableEntry.model_validate(data)
    if entry_type == "list":
        return ListEntry.model_validate(data)
    if entry_type == "inset":
        return InsetEntry.model_validate(data)
    if entry_type == "entries":
        return EntriesEntry.model_validate(data)
    if entry_type == "options":
        return OptionsEntry.model_validate(data)
    if entry_type == "variant":
        return VariantEntry.model_validate(data)
    if entry_type == "quote":
        return QuoteEntry.model_validate(data)
    if entry_type == "image":
        return ImageEntry.model_validate(data)
    if entry_type == "item":
        return ItemEntry.model_validate(data)
    if entry_type == "spell":
        return SpellEntry.model_validate(data)
    if entry_type == "creature":
        return CreatureEntry.model_validate(data)
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
