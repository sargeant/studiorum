"""Trap content models for mechanical challenges and dangers."""

from typing import Any

from pydantic import BaseModel, Field

from ..registry import content_type
from .content import BaseContent


class TrapRating(BaseModel):
    """Represents a trap's difficulty rating."""

    tier: int = Field(..., description="Character tier (1-4)")
    threat: str = Field(..., description="Threat level (setback, dangerous, deadly)")


@content_type(
    enum_value="trap",
    file_patterns=["trap", "traps", "trapshazards"],
    loader_type="json",
    statblock_tags=["trap"],
)
class Trap(BaseContent):
    """Trap mechanics and dangers for dungeons."""

    # Core trap properties
    trap_haz_type: str | None = Field(
        None, alias="trapHazType", description="Trap type (MECH, MAG, etc.)"
    )
    rating: list[TrapRating] = Field(
        default_factory=list, description="Difficulty ratings by tier"
    )

    # Detection and mechanics
    trigger: str | None = Field(None, description="What triggers the trap")
    effect: str | None = Field(None, description="What the trap does when triggered")
    countermeasures: str | None = Field(
        None, description="How to disable or avoid the trap"
    )

    # Optional properties
    simple: bool = Field(False, description="Whether this is a simple trap")
    complex: bool = Field(False, description="Whether this is a complex trap")

    def get_tier_rating(self, tier: int) -> TrapRating | None:
        """Get the rating for a specific character tier."""
        for rating in self.rating:
            if rating.tier == tier:
                return rating
        return None

    def get_threat_level(self, tier: int = 1) -> str:
        """Get the threat level for a specific tier (defaults to tier 1)."""
        rating = self.get_tier_rating(tier)
        return rating.threat if rating else "unknown"

    def is_mechanical(self) -> bool:
        """Check if this is a mechanical trap."""
        return self.trap_haz_type == "MECH"

    def is_magical(self) -> bool:
        """Check if this is a magical trap."""
        return self.trap_haz_type == "MAG"
