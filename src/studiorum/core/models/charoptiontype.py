"""Character option type content model."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class CharOptionTypeCategory(str, Enum):
    """Enumeration of character option type categories."""

    SUPERNATURAL_GIFT = "SG"
    OPTIONAL_FEATURE = "OF"
    DARK_GIFT = "DG"
    REPLACEMENT_FEATURE_BACKGROUND = "RF:B"
    # Not a password, D&D 5e character option type abbreviation
    CHARACTER_SECRET = "CS"  # nosec B105


@content_type(
    enum_value="charoptiontype",
    file_patterns=["charoptiontype", "charoptiontypes"],
    loader_type="json",
    statblock_tags=["charoptiontype"],
)
class CharacterOptionType(BaseContent):
    """Character option type model for categorizing character creation options.

    Character option types represent categories like Supernatural Gifts, Dark Gifts,
    Character Secrets, etc. that group related character creation options.
    """

    # Required fields
    abbreviation: str = Field(
        ..., description="Short code for the option type (SG, DG, CS, etc.)"
    )
    full_name: str = Field(..., description="Full descriptive name of the option type")

    # Optional fields
    description: str | None = Field(
        None, description="Detailed description of this option type"
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Option type description entries"
    )
    examples: list[str] | None = Field(
        None, description="Examples of options in this category"
    )
    rules_source: str | None = Field(
        None, description="Source that defines the rules for this option type"
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None, description="Other sources that reference this type", alias="otherSources"
    )

    @field_validator("abbreviation", mode="before")
    @classmethod
    def validate_abbreviation(cls, v: Any) -> str:
        """Validate and normalize abbreviation."""
        if not v:
            raise ValueError("Option type abbreviation cannot be empty")
        return str(v).upper()

    @field_validator("full_name", mode="before")
    @classmethod
    def validate_full_name(cls, v: Any) -> str:
        """Validate full name."""
        if not v:
            raise ValueError("Option type full name cannot be empty")
        return str(v).strip()

    def get_category(self) -> CharOptionTypeCategory | None:
        """Get the standard category enum if this type matches a known one."""
        try:
            return CharOptionTypeCategory(self.abbreviation)
        except ValueError:
            return None

    def is_known_category(self) -> bool:
        """Check if this is a known/standard character option type."""
        return self.get_category() is not None

    def is_supernatural_gift(self) -> bool:
        """Check if this is a Supernatural Gift type."""
        return self.abbreviation == "SG"

    def is_dark_gift(self) -> bool:
        """Check if this is a Dark Gift type."""
        return self.abbreviation == "DG"

    def is_character_secret(self) -> bool:
        """Check if this is a Character Secret type."""
        return self.abbreviation == "CS"

    def is_replacement_feature(self) -> bool:
        """Check if this is a Replacement Feature type."""
        return self.abbreviation.startswith("RF:")

    def get_replacement_type(self) -> str | None:
        """Get the specific replacement type (e.g., 'Background' for RF:B)."""
        if not self.is_replacement_feature():
            return None
        parts = self.abbreviation.split(":", 1)
        return parts[1] if len(parts) > 1 else None

    @classmethod
    def create_standard_types(cls) -> Sequence[CharacterOptionType]:
        """Create instances for all standard character option types."""
        from .content import Source

        standard_types = [
            cls(
                name="Supernatural Gift",
                source=Source(abbreviation="CORE"),
                abbreviation="SG",
                full_name="Supernatural Gift",
                description="Supernatural gifts represent boons granted by powerful entities or cosmic forces.",
            ),
            cls(
                name="Dark Gift",
                source=Source(abbreviation="CORE"),
                abbreviation="DG",
                full_name="Dark Gift",
                description="Dark gifts are supernatural abilities that come with a price or curse.",
            ),
            cls(
                name="Character Secret",
                source=Source(abbreviation="IDRotF"),
                abbreviation="CS",
                full_name="Character Secret",
                description="Character secrets are background elements specific to certain campaigns.",
            ),
            cls(
                name="Replacement Feature - Background",
                source=Source(abbreviation="CORE"),
                abbreviation="RF:B",
                full_name="Replacement Feature: Background",
                description="Alternative features that replace standard background features.",
            ),
            cls(
                name="Optional Feature",
                source=Source(abbreviation="CORE"),
                abbreviation="OF",
                full_name="Optional Feature",
                description="Optional features that can be selected during character creation.",
            ),
        ]
        return standard_types
