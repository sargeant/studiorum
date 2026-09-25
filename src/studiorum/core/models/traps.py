"""Trap content models for mechanical challenges and dangers."""

from pydantic import BaseModel, Field

from .content import BaseContent
from .entry_types import Entry


class TrapRating(BaseModel):
    """Represents a trap's difficulty rating."""

    tier: int = Field(..., description="Character tier (1-4)")
    threat: str = Field(..., description="Threat level (setback, dangerous, deadly)")


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
    trigger: list[Entry] | None = Field(None, description="What triggers the trap")
    effect: list[Entry] | None = Field(
        None, description="What the trap does when triggered"
    )
    countermeasures: list[Entry] | None = Field(
        None, description="How to disable or avoid the trap"
    )

    # Optional properties
    simple: bool = Field(False, description="Whether this is a simple trap")
    complex: bool = Field(False, description="Whether this is a complex trap")
