"""Optional feature data models for character features like fighting styles and invocations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry, validate_entries


class Prerequisite(BaseModel):
    """Represents a prerequisite for an optional feature."""

    spell: list[str] | None = Field(None, description="Required spells")
    level: dict[str, Any] | None = Field(None, description="Level requirements")
    feature: list[str] | None = Field(None, description="Required features")
    proficiency: list[dict[str, Any]] | None = Field(
        None, description="Required proficiencies"
    )
    ability: list[dict[str, Any]] | None = Field(
        None, description="Ability score requirements"
    )
    patron: list[str] | None = Field(None, description="Required patron type")
    pact: str | None = Field(None, description="Required pact boon")
    race: list[dict[str, str]] | None = Field(None, description="Race requirements")
    psionics: bool | None = Field(None, description="Requires psionics")

    class Config:
        extra = "allow"  # Allow additional prerequisite types


class ResourceConsumption(BaseModel):
    """Represents resource consumption for features."""

    name: str = Field(..., description="Name of consumed resource")
    amount: int | None = Field(None, description="Amount consumed")


class AdditionalSpells(BaseModel):
    """Additional spells granted by the feature."""

    prepared: dict[str, list[str]] | None = Field(
        None, description="Prepared spells by level"
    )
    expanded: dict[str, list[str]] | None = Field(
        None, description="Expanded spell list by level"
    )
    innate: dict[str, dict[str, Any]] | None = Field(
        None, description="Innate spellcasting"
    )
    known: dict[str, list[str]] | None = Field(
        None, description="Known spells by level"
    )

    class Config:
        extra = "allow"  # Allow other spell granting mechanisms


@content_type(
    enum_value="optionalfeature",
    file_patterns=["optionalfeature", "optionalfeatures"],
    statblock_tags=["optionalfeature"],
    loader_type="json",
)
class OptionalFeature(BaseContent):
    """Optional character features like fighting styles, invocations, and metamagic."""

    feature_type: list[str] = Field(
        ..., alias="featureType", description="Type codes for this feature"
    )
    prerequisite: list[Prerequisite] | None = Field(
        None, description="Prerequisites for this feature"
    )
    consumes: ResourceConsumption | None = Field(
        None, description="Resources consumed by this feature"
    )
    additional_spells: list[AdditionalSpells] | None = Field(
        None, alias="additionalSpells", description="Additional spells granted"
    )
    is_class_feature_variant: bool | None = Field(
        None,
        alias="isClassFeatureVariant",
        description="Whether this is a class feature variant",
    )
    reprinted_as: list[dict[str, str]] | None = Field(
        None, alias="reprintedAs", description="Later reprints of this feature"
    )
    entries: list[Entry] = Field(..., description="Feature description and rules")

    @field_validator("feature_type")
    @classmethod
    def validate_feature_type(cls, v: list[str]) -> list[str]:
        """Validate feature type codes."""
        if not v:
            raise ValueError("Feature type cannot be empty")

        # Known feature type prefixes from 5etools
        valid_prefixes = {
            "EI",  # Eldritch Invocation
            "FS:",  # Fighting Style
            "MV:",  # Maneuver
            "MM:",  # Metamagic
            "AI:",  # Arcane Invocation
            "PB:",  # Pact Boon
            "AS:",  # Additional Spell
            "IWM:",  # Invocation: War Magic
            "OR:",  # Onomancy Resonant
            "RN:",  # Rune
        }

        for feature_code in v:
            # Check if any known prefix matches
            if not any(feature_code.startswith(prefix) for prefix in valid_prefixes):
                # Allow unknown codes but could log warning in production
                pass

        return v

    @field_validator("entries", mode="before")
    @classmethod
    def validate_entries(cls, v: list[str | dict[str, Any]] | None) -> list[Entry]:
        """Validate entries using the standard validator."""
        if v is None:
            return []
        if not isinstance(v, list):
            # Malformed data - let Pydantic's normal validation catch it
            raise ValueError(f"Expected list or None for entries, got {type(v)}")
        return validate_entries(v)

    def get_feature_types_display(self) -> list[str]:
        """Get human-readable feature type names."""
        type_map = {
            "EI": "Eldritch Invocation",
            "FS:": "Fighting Style",
            "MV:": "Maneuver",
            "MM:": "Metamagic",
            "AI:": "Arcane Invocation",
            "PB:": "Pact Boon",
            "AS:": "Additional Spell",
            "IWM:": "War Magic Invocation",
            "OR:": "Onomancy Resonant",
            "RN:": "Rune",
        }

        display_types = []
        for feature_code in self.feature_type:
            # Find matching prefix
            display_name = feature_code
            for prefix, name in type_map.items():
                if feature_code.startswith(prefix):
                    if ":" in prefix and ":" in feature_code:
                        # Extract subtype (e.g., "FS:F" -> "Fighting Style (Fighter)")
                        subtype = feature_code.split(":", 1)[1]
                        display_name = f"{name} ({subtype})"
                    else:
                        display_name = name
                    break
            display_types.append(display_name)

        return display_types
