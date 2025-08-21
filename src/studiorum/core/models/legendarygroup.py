"""Legendary group content model."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


@content_type(
    enum_value="legendarygroup",
    file_patterns=["legendarygroup", "legendarygroups"],
    loader_type="json",
    statblock_tags=["legendarygroup"],
)
class LegendaryGroup(BaseContent):
    """Legendary group model for creature lair actions and regional effects.

    Legendary groups define the special lair actions and regional effects
    associated with legendary creatures in their home territories.
    """

    # Optional fields
    lair_actions: list[Entry] | None = Field(
        None,
        description="Actions the creature can take in its lair",
        alias="lairActions",
    )
    regional_effects: list[Entry] | None = Field(
        None,
        description="Effects the creature has on the surrounding region",
        alias="regionalEffects",
    )
    mythic_encounter: list[Entry] | None = Field(
        None, description="Special mythic encounter mechanics", alias="mythicEncounter"
    )
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this legendary group",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this group",
        alias="otherSources",
    )

    @field_validator("lair_actions", mode="before")
    @classmethod
    def validate_lair_actions(cls, v: Any) -> list[Entry] | None:
        """Validate lair actions structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        return None

    @field_validator("regional_effects", mode="before")
    @classmethod
    def validate_regional_effects(cls, v: Any) -> list[Entry] | None:
        """Validate regional effects structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        return None

    @field_validator("mythic_encounter", mode="before")
    @classmethod
    def validate_mythic_encounter(cls, v: Any) -> list[Entry] | None:
        """Validate mythic encounter structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Legendary group name cannot be empty")
        return str(v).strip()

    def has_lair_actions(self) -> bool:
        """Check if this legendary group has lair actions."""
        return bool(self.lair_actions)

    def has_regional_effects(self) -> bool:
        """Check if this legendary group has regional effects."""
        return bool(self.regional_effects)

    def has_mythic_encounter(self) -> bool:
        """Check if this legendary group has mythic encounter mechanics."""
        return bool(self.mythic_encounter)

    def get_lair_action_count(self) -> int:
        """Get the number of lair actions."""
        return len(self.lair_actions) if self.lair_actions else 0

    def get_regional_effect_count(self) -> int:
        """Get the number of regional effects."""
        return len(self.regional_effects) if self.regional_effects else 0

    def get_mythic_encounter_count(self) -> int:
        """Get the number of mythic encounter entries."""
        return len(self.mythic_encounter) if self.mythic_encounter else 0

    def is_lair_based(self) -> bool:
        """Check if this legendary group is primarily lair-based."""
        return self.has_lair_actions() and not self.has_regional_effects()

    def is_regional_based(self) -> bool:
        """Check if this legendary group affects the surrounding region."""
        return self.has_regional_effects()

    def get_summary(self) -> str:
        """Get a summary of this legendary group's capabilities."""
        parts = []
        if self.has_lair_actions():
            parts.append(f"{self.get_lair_action_count()} lair actions")
        if self.has_regional_effects():
            parts.append(f"{self.get_regional_effect_count()} regional effects")
        if self.has_mythic_encounter():
            parts.append(
                f"{self.get_mythic_encounter_count()} mythic encounter mechanics"
            )

        if not parts:
            return "No special mechanics"

        return ", ".join(parts)
