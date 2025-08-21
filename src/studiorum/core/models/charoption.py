"""Character option content model."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


@content_type(
    enum_value="charoption",
    file_patterns=["charoption", "charcreationoptions"],
    loader_type="json",
    statblock_tags=["charoption"],
)
class CharacterOption(BaseContent):
    """Character option model for background variants and similar content.

    Character options provide alternative backgrounds, traits, and other
    character creation choices with specific prerequisites.
    """

    # Optional fields with defaults
    prerequisite: list[dict[str, Any]] | None = Field(
        None, description="Prerequisites for this character option"
    )
    option_type: list[str] | None = Field(
        None,
        description="Option type codes (CS, DG, RF:B, SG, etc.)",
        alias="optionType",
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Character option description entries"
    )
    has_fluff_images: bool | None = Field(
        None, description="Whether this option has fluff images", alias="hasFluffImages"
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this option",
        alias="otherSources",
    )

    @field_validator("option_type", mode="before")
    @classmethod
    def validate_option_type(cls, v: Any) -> list[str] | None:
        """Validate and normalize option type list."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None

    @field_validator("prerequisite", mode="before")
    @classmethod
    def validate_prerequisite(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate prerequisite structure."""
        if v is None:
            return None
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Character option name cannot be empty")
        return str(v).strip()

    def get_option_types(self) -> list[str]:
        """Get list of option type codes."""
        return self.option_type or []

    def has_prerequisite(self) -> bool:
        """Check if this option has prerequisites."""
        return bool(self.prerequisite)

    def get_prerequisite_summary(self) -> str:
        """Get a human-readable summary of prerequisites."""
        if not self.prerequisite:
            return "No prerequisites"

        summaries = []
        for prereq in self.prerequisite:
            parts = []
            if "race" in prereq:
                races = prereq["race"]
                if isinstance(races, list):
                    race_names = [r.get("name", str(r)) for r in races]
                    parts.append(f"Race: {', '.join(race_names)}")
                else:
                    parts.append(f"Race: {races}")

            if "background" in prereq:
                parts.append(f"Background: {prereq['background']}")

            if "note" in prereq:
                parts.append(f"Note: {prereq['note']}")

            if parts:
                summaries.append("; ".join(parts))

        return " | ".join(summaries)

    def matches_option_type(self, option_type: str) -> bool:
        """Check if this option matches a specific option type."""
        return option_type in self.get_option_types()
