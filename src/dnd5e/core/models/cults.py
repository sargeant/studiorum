"""Cult and boon content models for campaign elements."""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="cult",
    file_patterns=["cult", "cults", "cultsboons"],
    loader_type="json",
    statblock_tags=["cult"],
)
class Cult(BaseContent):
    """Cult organizations for campaigns."""

    # Core cult properties
    type: str = Field(..., description="Type of cult (Diabolical, Elder Evil, etc.)")

    # Organization structure
    goals: list[str] = Field(default_factory=list, description="Cult's primary goals")
    structure: str | None = Field(None, description="How the cult is organized")
    membership: str | None = Field(None, description="Who joins this cult")

    # Powers and abilities
    signature_spells: list[str] = Field(
        default_factory=list,
        alias="signatureSpells",
        description="Spells favored by the cult",
    )

    def get_cult_category(self) -> str:
        """Get the cult's category."""
        return self.type

    def is_diabolical(self) -> bool:
        """Check if this is a diabolical cult."""
        return self.type == "Diabolical"

    def is_elder_evil(self) -> bool:
        """Check if this is an elder evil cult."""
        return self.type == "Elder Evil"


@content_type(
    enum_value="boon",
    file_patterns=["boon", "boons", "cultsboons"],
    loader_type="json",
    statblock_tags=["boon"],
)
class Boon(BaseContent):
    """Supernatural boons and gifts."""

    # Core boon properties
    type: str | None = Field(None, description="Type of boon")
    ability: dict[str, Any] | None = Field(
        None, description="Ability granted by the boon"
    )

    # Requirements and restrictions
    prerequisite: str | None = Field(
        None, description="Prerequisites for receiving the boon"
    )
    duration: str | None = Field(None, description="How long the boon lasts")

    # Power level
    rarity: str | None = Field(None, description="Rarity of the boon")

    def is_permanent(self) -> bool:
        """Check if this boon is permanent."""
        return self.duration is None or "permanent" in str(self.duration).lower()

    def has_prerequisites(self) -> bool:
        """Check if this boon has prerequisites."""
        return self.prerequisite is not None

    def get_power_level(self) -> str:
        """Get an indication of the boon's power level."""
        if self.rarity:
            return self.rarity
        # Could analyze entries for power indicators
        return "unknown"
