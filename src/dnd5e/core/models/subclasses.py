"""Subclass data models for class specializations like wizard schools and cleric domains."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry, validate_entries


class SubclassAdditionalSpells(BaseModel):
    """Additional spells granted by the subclass."""

    prepared: dict[str, list[str]] | None = Field(
        None, description="Prepared spells by level"
    )
    expanded: dict[str, list[str]] | None = Field(
        None, description="Expanded spell list by level"
    )
    known: dict[str, list[str]] | None = Field(
        None, description="Known spells by level"
    )
    innate: dict[str, dict[str, Any]] | None = Field(
        None, description="Innate spellcasting"
    )

    class Config:
        extra = "allow"  # Allow other spell granting mechanisms


class CopyMetadata(BaseModel):
    """Metadata for content copying/inheritance."""

    name: str = Field(..., description="Name of the content to copy from")
    source: str = Field(..., description="Source of the content to copy from")
    mod: dict[str, Any] | None = Field(
        None, description="Modifications to apply to copied content"
    )

    class Config:
        extra = "allow"  # Allow additional copy metadata


@content_type(
    enum_value="subclass",
    file_patterns=["class", "classes"],  # Subclasses are embedded in class files
    statblock_tags=["subclass"],
    loader_type="json",
)
class Subclass(BaseContent):
    """Class specializations like wizard schools, cleric domains, and warlock patrons."""

    short_name: str = Field(
        ..., alias="shortName", description="Abbreviated name for the subclass"
    )
    class_name: str = Field(
        ..., alias="className", description="Name of the parent class"
    )
    class_source: str = Field(
        ..., alias="classSource", description="Source of the parent class"
    )
    subclass_features: list[str] = Field(
        ..., alias="subclassFeatures", description="List of subclass feature references"
    )
    additional_spells: list[SubclassAdditionalSpells] | None = Field(
        None,
        alias="additionalSpells",
        description="Additional spells granted by subclass",
    )
    caster_progression: str | None = Field(
        None, alias="casterProgression", description="Spellcasting progression type"
    )
    cant_known: list[dict[str, Any]] | None = Field(
        None, alias="cantKnown", description="Cantrips known progression"
    )
    spells_known_progression: list[dict[str, Any]] | None = Field(
        None, alias="spellsKnownProgression", description="Spells known progression"
    )
    edition: str | None = Field(None, description="Edition this subclass is from")
    copy_metadata: CopyMetadata | None = Field(
        None, alias="_copy", description="Copy/inheritance metadata"
    )
    reprinted_as: list[dict[str, str]] | None = Field(
        None, alias="reprintedAs", description="Later reprints of this subclass"
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Subclass description and lore"
    )

    @field_validator("short_name")
    @classmethod
    def validate_short_name(cls, v: str) -> str:
        """Validate short name is not empty."""
        if not v.strip():
            raise ValueError("Short name cannot be empty")
        return v.strip()

    @field_validator("class_name")
    @classmethod
    def validate_class_name(cls, v: str) -> str:
        """Validate class name is not empty."""
        if not v.strip():
            raise ValueError("Class name cannot be empty")
        return v.strip()

    @field_validator("subclass_features")
    @classmethod
    def validate_subclass_features(cls, v: list[str]) -> list[str]:
        """Validate subclass features list."""
        if not v:
            raise ValueError("Subclass must have at least one feature")

        # Validate format: "Feature Name|Class|Source|Subclass||Level"
        for feature_ref in v:
            if not feature_ref.strip():
                raise ValueError("Feature reference cannot be empty")

            parts = feature_ref.split("|")
            if len(parts) < 6:
                # Some references might have fewer parts, be flexible
                continue

            # Validate level if present (should be integer)
            try:
                if parts[5].strip():
                    level = int(parts[5])
                    if level < 1 or level > 20:
                        raise ValueError(f"Invalid level {level} in feature reference")
            except (ValueError, IndexError):
                # Skip validation if level is not a number or missing
                pass

        return v

    @field_validator("entries", mode="before")
    @classmethod
    def validate_entries(cls, v: list[str | dict[str, Any]] | None) -> list[Entry]:
        """Handle missing entries and validate using the standard validator."""
        if v is None:
            return []  # Subclasses might not have direct entries
        if not isinstance(v, list):
            # Malformed data - let Pydantic's normal validation catch it
            raise ValueError(f"Expected list or None for entries, got {type(v)}")
        return validate_entries(v)

    def get_class_identifier(self) -> str:
        """Get unique identifier for the parent class."""
        return f"{self.class_name}|{self.class_source}"

    def get_subclass_identifier(self) -> str:
        """Get unique identifier for this subclass."""
        return f"{self.class_name}|{self.class_source}|{self.short_name}|{self.source.abbreviation}"

    def get_feature_level_map(self) -> dict[int, list[str]]:
        """Extract features organized by level."""
        level_map: dict[int, list[str]] = {}

        for feature_ref in self.subclass_features:
            parts = feature_ref.split("|")
            if len(parts) >= 6:
                try:
                    level = int(parts[5]) if parts[5].strip() else 1
                    feature_name = parts[0]

                    if level not in level_map:
                        level_map[level] = []
                    level_map[level].append(feature_name)
                except (ValueError, IndexError):
                    # Default to level 1 if parsing fails
                    if 1 not in level_map:
                        level_map[1] = []
                    level_map[1].append(parts[0] if parts else feature_ref)

        return level_map
