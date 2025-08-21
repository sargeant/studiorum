"""Psionic content model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class PsionicType(str, Enum):
    """Enumeration of psionic types."""

    DISCIPLINE = "D"  # Psionic Discipline
    TALENT = "T"  # Psionic Talent
    POWER = "P"  # Psionic Power
    UNKNOWN = "U"  # Unknown/Other


class PsionicOrder(str, Enum):
    """Enumeration of psionic orders."""

    IMMORTAL = "immortal"
    AVATAR = "avatar"
    AWAKENED = "awakened"
    NOMAD = "nomad"
    WU_JEN = "wu jen"
    SOUL_KNIFE = "soul knife"
    UNKNOWN = "unknown"


@content_type(
    enum_value="psionic",
    file_patterns=["psionic", "psionics"],
    loader_type="json",
    statblock_tags=["psionic"],
)
class Psionic(BaseContent):
    """Psionic model for psionic disciplines, talents, and powers.

    Psionics represent mystical mental abilities with focus effects,
    modes of use, and psi point costs.
    """

    # Required fields
    psionic_type: PsionicType = Field(..., description="Type of psionic", alias="type")
    entries: list[Entry] = Field(
        default_factory=list, description="Psionic description entries"
    )

    # Optional fields
    order: PsionicOrder | None = Field(None, description="Psionic order")
    focus: str | None = Field(None, description="Focus effect description")
    modes: list[dict[str, Any]] | None = Field(None, description="Psionic modes")
    submodes: list[dict[str, Any]] | None = Field(None, description="Psionic submodes")
    cost: dict[str, int] | None = Field(None, description="Psi point cost")
    concentration: dict[str, Any] | None = Field(
        None, description="Concentration requirement"
    )
    level: int | None = Field(None, description="Level requirement", ge=1, le=20)
    prerequisites: list[str] | None = Field(
        None, description="Prerequisites for this psionic"
    )
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this psionic",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this psionic",
        alias="otherSources",
    )
    reprinted_as: list[str] | None = Field(
        None, description="Reprints of this psionic", alias="reprintedAs"
    )

    @field_validator("psionic_type", mode="before")
    @classmethod
    def validate_psionic_type(cls, v: Any) -> PsionicType:
        """Validate and normalize psionic type."""
        if isinstance(v, str):
            try:
                return PsionicType(v.upper())
            except ValueError:
                return PsionicType.UNKNOWN
        return PsionicType.UNKNOWN

    @field_validator("order", mode="before")
    @classmethod
    def validate_order(cls, v: Any) -> PsionicOrder | None:
        """Validate and normalize psionic order."""
        if not v:
            return None
        if isinstance(v, str):
            try:
                # Convert to lowercase and handle special cases
                order_value = str(v).lower().strip()
                return PsionicOrder(order_value)
            except ValueError:
                return PsionicOrder.UNKNOWN
        return None

    @field_validator("modes", mode="before")
    @classmethod
    def validate_modes(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate modes structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
        return None

    @field_validator("submodes", mode="before")
    @classmethod
    def validate_submodes(cls, v: Any) -> list[dict[str, Any]] | None:
        """Validate submodes structure."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
        return None

    @field_validator("cost", mode="before")
    @classmethod
    def validate_cost(cls, v: Any) -> dict[str, int] | None:
        """Validate cost structure."""
        if v is None:
            return None
        if isinstance(v, dict):
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
                return None
            return level_val
        except (ValueError, TypeError):
            return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Psionic name cannot be empty")
        return str(v).strip()

    def get_psionic_type(self) -> PsionicType:
        """Get the psionic type."""
        return self.psionic_type

    def get_psionic_type_description(self) -> str:
        """Get human-readable psionic type description."""
        descriptions = {
            PsionicType.DISCIPLINE: "Psionic Discipline",
            PsionicType.TALENT: "Psionic Talent",
            PsionicType.POWER: "Psionic Power",
            PsionicType.UNKNOWN: "Unknown Psionic Type",
        }
        return descriptions.get(self.psionic_type, "Unknown")

    def get_order(self) -> PsionicOrder | None:
        """Get the psionic order."""
        return self.order

    def get_order_description(self) -> str:
        """Get human-readable order description."""
        if not self.order:
            return "No order"

        descriptions = {
            PsionicOrder.IMMORTAL: "Order of the Immortal",
            PsionicOrder.AVATAR: "Order of the Avatar",
            PsionicOrder.AWAKENED: "Order of the Awakened",
            PsionicOrder.NOMAD: "Order of the Nomad",
            PsionicOrder.WU_JEN: "Order of the Wu Jen",
            PsionicOrder.SOUL_KNIFE: "Order of the Soul Knife",
            PsionicOrder.UNKNOWN: "Unknown Order",
        }
        return descriptions.get(self.order, "Unknown Order")

    def is_discipline(self) -> bool:
        """Check if this is a psionic discipline."""
        return self.psionic_type == PsionicType.DISCIPLINE

    def is_talent(self) -> bool:
        """Check if this is a psionic talent."""
        return self.psionic_type == PsionicType.TALENT

    def is_power(self) -> bool:
        """Check if this is a psionic power."""
        return self.psionic_type == PsionicType.POWER

    def has_focus_effect(self) -> bool:
        """Check if this psionic has a focus effect."""
        return bool(self.focus)

    def has_modes(self) -> bool:
        """Check if this psionic has modes."""
        return bool(self.modes)

    def has_submodes(self) -> bool:
        """Check if this psionic has submodes."""
        return bool(self.submodes)

    def has_cost(self) -> bool:
        """Check if this psionic has a psi point cost."""
        return bool(self.cost)

    def requires_concentration(self) -> bool:
        """Check if this psionic requires concentration."""
        return bool(self.concentration)

    def has_level_requirement(self) -> bool:
        """Check if this psionic has a minimum level requirement."""
        return self.level is not None

    def has_prerequisites(self) -> bool:
        """Check if this psionic has prerequisites."""
        return bool(self.prerequisites)

    def get_mode_count(self) -> int:
        """Get the number of modes."""
        return len(self.modes) if self.modes else 0

    def get_submode_count(self) -> int:
        """Get the number of submodes."""
        return len(self.submodes) if self.submodes else 0

    def get_min_cost(self) -> int | None:
        """Get minimum psi point cost."""
        if not self.cost:
            return None
        return self.cost.get("min")

    def get_max_cost(self) -> int | None:
        """Get maximum psi point cost."""
        if not self.cost:
            return None
        return self.cost.get("max")

    def get_cost_range(self) -> str:
        """Get cost range as string."""
        if not self.cost:
            return "No cost"

        min_cost = self.get_min_cost()
        max_cost = self.get_max_cost()

        if min_cost is None and max_cost is None:
            return "No cost"
        elif min_cost == max_cost:
            return f"{min_cost} psi points"
        else:
            return f"{min_cost}-{max_cost} psi points"

    def get_concentration_duration(self) -> str | None:
        """Get concentration duration if applicable."""
        if not self.concentration:
            return None

        duration = self.concentration.get("duration")
        unit = self.concentration.get("unit", "")

        if duration is None:
            return None

        return f"{duration} {unit}".strip()

    def get_minimum_level(self) -> int:
        """Get minimum level required, defaulting to 1."""
        return self.level or 1

    def get_prerequisites_list(self) -> list[str]:
        """Get list of prerequisites."""
        return self.prerequisites or []

    def get_modes_by_cost(self, cost: int) -> list[dict[str, Any]]:
        """Get modes with a specific cost."""
        if not self.modes:
            return []

        matching_modes = []
        for mode in self.modes:
            mode_cost = mode.get("cost", {})
            if isinstance(mode_cost, dict):
                min_cost = mode_cost.get("min")
                max_cost = mode_cost.get("max")
                if (
                    min_cost is not None
                    and max_cost is not None
                    and min_cost <= cost <= max_cost
                ):
                    matching_modes.append(mode)
            elif isinstance(mode_cost, int) and mode_cost == cost:
                matching_modes.append(mode)

        return matching_modes

    def belongs_to_order(self, order: str) -> bool:
        """Check if this psionic belongs to a specific order."""
        if not self.order:
            return False
        # Handle both string and enum values for robustness
        if isinstance(self.order, PsionicOrder):
            return self.order.value.lower() == order.lower()
        else:
            return str(self.order).lower() == order.lower()

    def get_complexity_rating(self) -> str:
        """Get complexity rating based on modes, submodes, and requirements."""
        complexity_score = 0

        if self.has_modes():
            complexity_score += self.get_mode_count()

        if self.has_submodes():
            complexity_score += self.get_submode_count() * 2

        if self.requires_concentration():
            complexity_score += 1

        if self.has_prerequisites():
            complexity_score += len(self.get_prerequisites_list())

        if complexity_score <= 2:
            return "Simple"
        elif complexity_score <= 5:
            return "Moderate"
        else:
            return "Complex"

    def get_psionic_summary(self) -> str:
        """Get a summary description of this psionic."""
        parts = [self.get_psionic_type_description()]

        if self.order:
            parts.append(self.get_order_description())

        if self.has_cost():
            parts.append(self.get_cost_range())

        if self.has_modes():
            mode_count = self.get_mode_count()
            parts.append(f"{mode_count} mode{'s' if mode_count != 1 else ''}")

        if self.requires_concentration():
            duration = self.get_concentration_duration()
            if duration:
                parts.append(f"concentration {duration}")
            else:
                parts.append("concentration required")

        parts.append(f"{self.get_complexity_rating().lower()} complexity")

        return ", ".join(parts)
