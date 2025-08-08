"""Optional feature content model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class OptionalFeatureType(str, Enum):
    """Enumeration of optional feature types."""

    ELDRITCH_INVOCATION = "EI"  # Eldritch Invocations
    MANEUVER_VARIANT_BATTLEMASTER = "MV:B"  # Battle Master Maneuvers
    MANEUVER_VARIANT_CAVALIER = "MV:C2-UA"  # Cavalier Maneuvers
    FIGHTING_STYLE = "FS:F"  # Fighting Styles - Fighter
    FIGHTING_STYLE_PALADIN = "FS:P"  # Fighting Styles - Paladin
    FIGHTING_STYLE_RANGER = "FS:R"  # Fighting Styles - Ranger
    METAMAGIC = "MM"  # Metamagic Options
    PACT_BOON = "PB"  # Pact Boons
    ARTIFICER_INFUSION = "AI"  # Artificer Infusions
    CANTRIP_VARIANT = "OTH"  # Other/Miscellaneous


@content_type(
    enum_value="optfeature",
    file_patterns=["optfeature", "optfeatures", "optionalfeature", "optionalfeatures"],
    loader_type="json",
    statblock_tags=["optfeature", "optionalfeature"],
)
class OptionalFeature(BaseContent):
    """Optional feature model for class features, invocations, and variants.

    Optional features represent additional choices for character classes,
    such as Eldritch Invocations, Fighting Styles, Metamagic options, etc.
    """

    # Required fields
    feature_type: list[str] = Field(
        ..., description="Feature type codes", alias="featureType"
    )

    # Optional fields
    prerequisite: list[dict[str, Any]] | None = Field(
        None, description="Prerequisites for this optional feature"
    )
    entries: list[Entry] = Field(
        default_factory=list, description="Optional feature description entries"
    )
    consumes: dict[str, Any] | None = Field(
        None,
        description="Resources consumed by this feature (spell slots, superiority dice, etc.)",
    )
    is_class_feature_variant: bool | None = Field(
        None,
        description="Whether this is a class feature variant",
        alias="isClassFeatureVariant",
    )
    level: int | None = Field(
        None, description="Minimum level required for this feature", ge=1, le=20
    )
    class_restriction: dict[str, Any] | None = Field(
        None, description="Class restrictions for this feature"
    )
    additional_spells: list[dict[str, Any]] | None = Field(
        None,
        description="Additional spells granted by this feature",
        alias="additionalSpells",
    )
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this feature",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this feature",
        alias="otherSources",
    )
    reprinted_as: list[str] | None = Field(
        None, description="Reprints of this feature", alias="reprintedAs"
    )

    @field_validator("feature_type", mode="before")
    @classmethod
    def validate_feature_type(cls, v: Any) -> list[str]:
        """Validate and normalize feature type list."""
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        if not v:
            raise ValueError("Optional feature type cannot be empty")
        return [str(v)]

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

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: Any) -> int | None:
        """Validate level value."""
        if v is None:
            return None
        try:
            level_val = int(v)
            if level_val < 1 or level_val > 20:
                raise ValueError("Level must be between 1 and 20")
            return level_val
        except (ValueError, TypeError):
            return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Optional feature name cannot be empty")
        return str(v).strip()

    def get_feature_types(self) -> list[str]:
        """Get list of feature type codes."""
        return self.feature_type or []

    def get_primary_feature_type(self) -> str:
        """Get the primary (first) feature type."""
        types = self.get_feature_types()
        return types[0] if types else "UNKNOWN"

    def has_prerequisite(self) -> bool:
        """Check if this feature has prerequisites."""
        return bool(self.prerequisite)

    def has_level_requirement(self) -> bool:
        """Check if this feature has a minimum level requirement."""
        return self.level is not None

    def get_minimum_level(self) -> int:
        """Get the minimum level required, defaulting to 1 if not specified."""
        return self.level or 1

    def is_eldritch_invocation(self) -> bool:
        """Check if this is an Eldritch Invocation."""
        return "EI" in self.get_feature_types()

    def is_fighting_style(self) -> bool:
        """Check if this is a Fighting Style."""
        types = self.get_feature_types()
        return any(t.startswith("FS:") for t in types)

    def is_maneuver(self) -> bool:
        """Check if this is a Battle Master or other maneuver."""
        types = self.get_feature_types()
        return any(t.startswith("MV:") for t in types)

    def is_metamagic(self) -> bool:
        """Check if this is a Metamagic option."""
        return "MM" in self.get_feature_types()

    def is_artificer_infusion(self) -> bool:
        """Check if this is an Artificer Infusion."""
        return "AI" in self.get_feature_types()

    def is_class_variant(self) -> bool:
        """Check if this is a class feature variant."""
        return self.is_class_feature_variant is True

    def consumes_resources(self) -> bool:
        """Check if this feature consumes resources."""
        return bool(self.consumes)

    def get_consumed_resource(self) -> str | None:
        """Get the name of the resource consumed by this feature."""
        if not self.consumes:
            return None
        return self.consumes.get("name")

    def grants_additional_spells(self) -> bool:
        """Check if this feature grants additional spells."""
        return bool(self.additional_spells)

    def get_prerequisite_summary(self) -> str:
        """Get a human-readable summary of prerequisites."""
        if not self.prerequisite:
            return "No prerequisites"

        summaries = []
        for prereq in self.prerequisite:
            parts = []

            if "spell" in prereq:
                spells = prereq["spell"]
                if isinstance(spells, list):
                    spell_names = []
                    for spell in spells:
                        if isinstance(spell, str):
                            spell_names.append(spell.replace("#c", ""))
                        elif isinstance(spell, dict):
                            spell_names.append(spell.get("entry", "Unknown spell"))
                    parts.append(f"Spell: {', '.join(spell_names)}")
                else:
                    parts.append(f"Spell: {spells}")

            if "level" in prereq:
                level_req = prereq["level"]
                if isinstance(level_req, dict):
                    level_val = level_req.get("level", "Unknown")
                    class_info = level_req.get("class", {})
                    class_name = (
                        class_info.get("name", "Unknown")
                        if isinstance(class_info, dict)
                        else str(class_info)
                    )
                    parts.append(f"Level {level_val} {class_name}")
                else:
                    parts.append(f"Level {level_req}")

            if "pact" in prereq:
                parts.append(f"Pact: {prereq['pact']}")

            if parts:
                summaries.append("; ".join(parts))

        return " | ".join(summaries) if summaries else "No prerequisites"

    def get_feature_category(self) -> OptionalFeatureType | None:
        """Get the standard feature category enum if this matches a known type."""
        primary_type = self.get_primary_feature_type()
        try:
            return OptionalFeatureType(primary_type)
        except ValueError:
            return None
