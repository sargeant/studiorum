"""Trap content model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class TrapHazardType(str, Enum):
    """Enumeration of trap and hazard types."""

    MECHANICAL = "MECH"  # Mechanical trap
    MAGICAL = "MAG"  # Magical trap
    ENVIRONMENTAL = "ENV"  # Environmental hazard
    COMPLEX = "CPLX"  # Complex trap
    SIMPLE = "SMPL"  # Simple trap
    UNKNOWN = "UNK"  # Unknown type


class ThreatLevel(str, Enum):
    """Enumeration of threat levels."""

    SETBACK = "setback"
    DANGEROUS = "dangerous"
    DEADLY = "deadly"
    UNKNOWN = "unknown"


class Tier(int, Enum):
    """Enumeration of character tiers."""

    TIER_1 = 1  # Levels 1-4
    TIER_2 = 2  # Levels 5-10
    TIER_3 = 3  # Levels 11-16
    TIER_4 = 4  # Levels 17-20


@content_type(
    enum_value="trap",
    file_patterns=["trap", "traps", "trapshazards"],
    loader_type="json",
    statblock_tags=["trap"],
)
class Trap(BaseContent):
    """Trap model for mechanical and magical traps and hazards.

    Traps represent dangerous obstacles with threat ratings,
    detection methods, and disarm procedures.
    """

    # Required fields
    entries: list[Entry] = Field(
        default_factory=list, description="Trap description entries"
    )

    # Optional fields
    trap_hazard_type: TrapHazardType = Field(
        TrapHazardType.UNKNOWN,
        description="Type of trap or hazard",
        alias="trapHazType",
    )
    rating: list[dict[str, Any]] | None = Field(
        None, description="Threat rating by tier"
    )
    trigger: list[str] | None = Field(None, description="Trigger conditions")
    effect: list[str] | None = Field(None, description="Trap effects")
    countermeasures: list[str] | None = Field(
        None, description="Ways to counter or disable"
    )
    initiative: int | None = Field(
        None, description="Initiative modifier", ge=-5, le=10
    )
    initiative_note: str | None = Field(
        None, description="Initiative note", alias="initiativeNote"
    )
    damage_immunities: list[str] | None = Field(
        None, description="Damage immunities", alias="immune"
    )
    condition_immunities: list[str] | None = Field(
        None, description="Condition immunities", alias="conditionImmune"
    )
    senses: list[str] | None = Field(None, description="Trap senses")
    ac: int | None = Field(None, description="Armor Class", ge=1, le=30)
    hp: int | None = Field(None, description="Hit Points", ge=1)
    skill_check: list[dict[str, Any]] | None = Field(
        None, description="Required skill checks", alias="skillCheck"
    )
    saving_throw: list[dict[str, Any]] | None = Field(
        None, description="Required saving throws", alias="savingThrow"
    )
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this trap",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this trap",
        alias="otherSources",
    )

    @field_validator("trap_hazard_type", mode="before")
    @classmethod
    def validate_trap_hazard_type(cls, v: Any) -> TrapHazardType:
        """Validate and normalize trap hazard type."""
        if isinstance(v, str):
            try:
                return TrapHazardType(v.upper())
            except ValueError:
                return TrapHazardType.UNKNOWN
        return TrapHazardType.UNKNOWN

    @field_validator("rating", mode="before")
    @classmethod
    def validate_rating(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate rating structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
        return None

    @field_validator("trigger", mode="before")
    @classmethod
    def validate_trigger(cls, v: Any) -> list[str] | None:
        """Validate trigger structure."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None

    @field_validator("effect", mode="before")
    @classmethod
    def validate_effect(cls, v: Any) -> list[str] | None:
        """Validate effect structure."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None

    @field_validator("countermeasures", mode="before")
    @classmethod
    def validate_countermeasures(cls, v: Any) -> list[str] | None:
        """Validate countermeasures structure."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Trap name cannot be empty")
        return str(v).strip()

    def get_trap_hazard_type(self) -> TrapHazardType:
        """Get the trap hazard type."""
        return self.trap_hazard_type

    def get_trap_type_description(self) -> str:
        """Get human-readable trap type description."""
        descriptions = {
            TrapHazardType.MECHANICAL: "Mechanical Trap",
            TrapHazardType.MAGICAL: "Magical Trap",
            TrapHazardType.ENVIRONMENTAL: "Environmental Hazard",
            TrapHazardType.COMPLEX: "Complex Trap",
            TrapHazardType.SIMPLE: "Simple Trap",
            TrapHazardType.UNKNOWN: "Unknown Trap Type",
        }
        return descriptions.get(self.trap_hazard_type, "Unknown")

    def is_mechanical(self) -> bool:
        """Check if this is a mechanical trap."""
        return self.trap_hazard_type == TrapHazardType.MECHANICAL

    def is_magical(self) -> bool:
        """Check if this is a magical trap."""
        return self.trap_hazard_type == TrapHazardType.MAGICAL

    def is_environmental_hazard(self) -> bool:
        """Check if this is an environmental hazard."""
        return self.trap_hazard_type == TrapHazardType.ENVIRONMENTAL

    def is_complex(self) -> bool:
        """Check if this is a complex trap."""
        return self.trap_hazard_type == TrapHazardType.COMPLEX

    def is_simple(self) -> bool:
        """Check if this is a simple trap."""
        return self.trap_hazard_type == TrapHazardType.SIMPLE

    def has_rating(self) -> bool:
        """Check if this trap has threat ratings."""
        return bool(self.rating)

    def has_triggers(self) -> bool:
        """Check if this trap has trigger conditions."""
        return bool(self.trigger)

    def has_effects(self) -> bool:
        """Check if this trap has documented effects."""
        return bool(self.effect)

    def has_countermeasures(self) -> bool:
        """Check if this trap has countermeasures."""
        return bool(self.countermeasures)

    def has_initiative(self) -> bool:
        """Check if this trap acts on initiative."""
        return self.initiative is not None

    def has_defenses(self) -> bool:
        """Check if this trap has AC/HP."""
        return self.ac is not None or self.hp is not None

    def has_immunities(self) -> bool:
        """Check if this trap has damage or condition immunities."""
        return bool(self.damage_immunities) or bool(self.condition_immunities)

    def requires_skill_checks(self) -> bool:
        """Check if this trap requires skill checks."""
        return bool(self.skill_check)

    def requires_saving_throws(self) -> bool:
        """Check if this trap requires saving throws."""
        return bool(self.saving_throw)

    def get_ratings_by_tier(self, tier: int) -> list[dict[str, Any]]:
        """Get threat ratings for a specific tier."""
        if not self.rating:
            return []

        return [rating for rating in self.rating if rating.get("tier") == tier]

    def get_threat_level_for_tier(self, tier: int) -> ThreatLevel:
        """Get threat level for a specific tier."""
        ratings = self.get_ratings_by_tier(tier)
        if not ratings:
            return ThreatLevel.UNKNOWN

        threat = ratings[0].get("threat", "unknown")
        try:
            return ThreatLevel(threat.lower())
        except ValueError:
            return ThreatLevel.UNKNOWN

    def get_threat_level_description(self, tier: int) -> str:
        """Get human-readable threat level for a tier."""
        threat_level = self.get_threat_level_for_tier(tier)
        descriptions = {
            ThreatLevel.SETBACK: "Setback",
            ThreatLevel.DANGEROUS: "Dangerous",
            ThreatLevel.DEADLY: "Deadly",
            ThreatLevel.UNKNOWN: "Unknown Threat",
        }
        return descriptions.get(threat_level, "Unknown")

    def is_deadly_for_tier(self, tier: int) -> bool:
        """Check if this trap is deadly for a specific tier."""
        return self.get_threat_level_for_tier(tier) == ThreatLevel.DEADLY

    def is_dangerous_for_tier(self, tier: int) -> bool:
        """Check if this trap is dangerous for a specific tier."""
        return self.get_threat_level_for_tier(tier) == ThreatLevel.DANGEROUS

    def get_all_threat_levels(self) -> dict[int, ThreatLevel]:
        """Get threat levels for all tiers."""
        if not self.rating:
            return {}

        threat_levels = {}
        for rating in self.rating:
            tier = rating.get("tier")
            threat = rating.get("threat", "unknown")
            if tier is not None:
                try:
                    threat_levels[tier] = ThreatLevel(threat.lower())
                except ValueError:
                    threat_levels[tier] = ThreatLevel.UNKNOWN

        return threat_levels

    def get_trigger_count(self) -> int:
        """Get the number of trigger conditions."""
        return len(self.trigger) if self.trigger else 0

    def get_effect_count(self) -> int:
        """Get the number of effects."""
        return len(self.effect) if self.effect else 0

    def get_countermeasure_count(self) -> int:
        """Get the number of countermeasures."""
        return len(self.countermeasures) if self.countermeasures else 0

    def get_damage_immunities_list(self) -> list[str]:
        """Get list of damage immunities."""
        return self.damage_immunities or []

    def get_condition_immunities_list(self) -> list[str]:
        """Get list of condition immunities."""
        return self.condition_immunities or []

    def get_senses_list(self) -> list[str]:
        """Get list of trap senses."""
        return self.senses or []

    def get_skill_checks_list(self) -> list[dict[str, Any]]:
        """Get list of required skill checks."""
        return self.skill_check or []

    def get_saving_throws_list(self) -> list[dict[str, Any]]:
        """Get list of required saving throws."""
        return self.saving_throw or []

    def can_be_detected(self) -> bool:
        """Check if trap can be detected (has skill checks)."""
        return self.requires_skill_checks()

    def can_be_disabled(self) -> bool:
        """Check if trap can be disabled (has countermeasures)."""
        return self.has_countermeasures()

    def get_detection_difficulty(self) -> int | None:
        """Get detection difficulty from skill checks."""
        if not self.skill_check:
            return None

        # Look for perception or investigation checks
        for check in self.skill_check:
            if check.get("skill") in ["Perception", "Investigation"]:
                return check.get("dc")

        # Return first skill check DC if no specific detection skill found
        if self.skill_check:
            return self.skill_check[0].get("dc")

        return None

    def get_disarm_difficulty(self) -> int | None:
        """Get disarm difficulty from skill checks."""
        if not self.skill_check:
            return None

        # Look for thieves' tools or related checks
        for check in self.skill_check:
            skill = check.get("skill", "").lower()
            if "thieves" in skill or "disable" in skill:
                return check.get("dc")

        return None

    def get_complexity_rating(self) -> str:
        """Get complexity rating based on components."""
        complexity_score = 0

        if self.has_triggers():
            complexity_score += self.get_trigger_count()

        if self.has_effects():
            complexity_score += self.get_effect_count()

        if self.has_countermeasures():
            complexity_score += 1

        if self.has_defenses():
            complexity_score += 1

        if self.has_immunities():
            complexity_score += 1

        if self.has_initiative():
            complexity_score += 2

        if complexity_score <= 2:
            return "Simple"
        elif complexity_score <= 5:
            return "Moderate"
        else:
            return "Complex"

    def get_trap_summary(self) -> str:
        """Get a summary description of this trap."""
        parts = [self.get_trap_type_description()]

        # Add threat levels
        threat_levels = self.get_all_threat_levels()
        if threat_levels:
            threat_descriptions = []
            for tier, threat in sorted(threat_levels.items()):
                threat_descriptions.append(f"T{tier}: {threat.value}")
            parts.append(f"({'/'.join(threat_descriptions)})")

        # Add key characteristics
        if self.get_trigger_count() > 0:
            parts.append(
                f"{self.get_trigger_count()} trigger{'s' if self.get_trigger_count() != 1 else ''}"
            )

        if self.can_be_detected():
            detection_dc = self.get_detection_difficulty()
            if detection_dc:
                parts.append(f"detect DC {detection_dc}")

        if self.can_be_disabled():
            disarm_dc = self.get_disarm_difficulty()
            if disarm_dc:
                parts.append(f"disable DC {disarm_dc}")

        parts.append(f"{self.get_complexity_rating().lower()} complexity")

        return ", ".join(parts)
