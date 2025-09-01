"""Disease content type models for D&D 5e.

Provides Pydantic models for diseases and afflictions that can affect
characters during gameplay.
"""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="disease",
    file_patterns=["disease", "diseases", "conditionsdiseases"],
    loader_type="json",
    statblock_tags=["disease"],
)
class Disease(BaseContent):
    """A disease that can afflict characters.

    Diseases represent harmful conditions that can be contracted
    through various means and have ongoing effects on characters.
    """

    # Optional fields for disease mechanics
    transmission: list[str] | None = Field(
        None, description="How the disease is transmitted"
    )
    incubation_period: str | None = Field(
        None, alias="incubationPeriod", description="Time before symptoms appear"
    )
    symptoms: list[str] | None = Field(None, description="Symptoms of the disease")
    effects: list[dict[str, Any]] | None = Field(
        None, description="Mechanical effects of the disease"
    )
    cure: str | dict[str, Any] | None = Field(
        None, description="How to cure or treat the disease"
    )
    save_dc: int | None = Field(
        None, alias="saveDC", description="DC for saving throws against the disease"
    )
    save_ability: str | None = Field(
        None, alias="saveAbility", description="Ability used for saves against disease"
    )
    duration: str | None = Field(None, description="How long the disease lasts")

    def get_display_name(self) -> str:
        """Get display name for the disease."""
        return self.name

    def has_transmission_info(self) -> bool:
        """Check if transmission information is available."""
        return bool(self.transmission and len(self.transmission) > 0)

    def has_symptoms(self) -> bool:
        """Check if symptom information is available."""
        return bool(self.symptoms and len(self.symptoms) > 0)

    def has_mechanical_effects(self) -> bool:
        """Check if the disease has defined mechanical effects."""
        return bool(self.effects and len(self.effects) > 0)

    def requires_saving_throw(self) -> bool:
        """Check if the disease requires saving throws."""
        return self.save_dc is not None

    def get_save_info(self) -> dict[str, Any] | None:
        """Get saving throw information."""
        if not self.requires_saving_throw():
            return None

        return {
            "dc": self.save_dc,
            "ability": self.save_ability or "Constitution",
        }

    def has_cure_information(self) -> bool:
        """Check if cure information is available."""
        return self.cure is not None

    def get_cure_description(self) -> str:
        """Get a description of how to cure the disease."""
        if not self.cure:
            return "No cure information available"

        if isinstance(self.cure, str):
            return self.cure
        elif isinstance(self.cure, dict):
            # Handle structured cure information
            return str(self.cure.get("description", "Structured cure information"))
        else:
            return str(self.cure)
