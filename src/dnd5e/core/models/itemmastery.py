"""ItemMastery content type models for D&D 5e.

Provides Pydantic models for the 2024 weapon mastery system that defines
special techniques and abilities for weapon users.
"""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="itemMastery",
    file_patterns=["itemMastery", "itemmastery", "items-base"],
    loader_type="json",
    statblock_tags=["itemMastery"],
)
class ItemMastery(BaseContent):
    """A weapon mastery technique from the 2024 D&D rules.

    Item masteries represent special combat techniques that can be
    performed with specific weapons when a character has proficiency
    and meets the mastery requirements.
    """

    # Mastery mechanics
    trigger: str | None = Field(None, description="What triggers this mastery")
    effect: str | None = Field(None, description="The effect of the mastery")
    frequency: str | None = Field(None, description="How often this can be used")
    requirements: list[str] = Field(
        default_factory=list, description="Requirements to use this mastery"
    )

    # Associated weapons
    applicable_weapons: list[str] = Field(
        default_factory=list,
        alias="applicableWeapons",
        description="Weapons this mastery applies to",
    )

    # Mastery category
    category: str | None = Field(None, description="Category of mastery")

    def get_display_name(self) -> str:
        """Get display name for the mastery."""
        return self.name

    def has_requirements(self) -> bool:
        """Check if this mastery has specific requirements."""
        return len(self.requirements) > 0

    def get_requirements(self) -> list[str]:
        """Get the requirements for this mastery."""
        return self.requirements.copy()

    def has_frequency_limitation(self) -> bool:
        """Check if this mastery has usage frequency limitations."""
        return self.frequency is not None

    def get_frequency(self) -> str | None:
        """Get the frequency limitation."""
        return self.frequency

    def applies_to_weapon(self, weapon_name: str) -> bool:
        """Check if this mastery applies to a specific weapon."""
        if not self.applicable_weapons:
            return True  # No restrictions
        return weapon_name.lower() in [w.lower() for w in self.applicable_weapons]

    def get_trigger_condition(self) -> str | None:
        """Get what triggers this mastery."""
        return self.trigger

    def get_effect_description(self) -> str | None:
        """Get the effect description."""
        return self.effect

    def is_attack_mastery(self) -> bool:
        """Check if this mastery relates to attack actions."""
        attack_indicators = ["attack", "hit", "damage", "strike"]
        description = (self.get_description() or "").lower()

        for indicator in attack_indicators:
            if indicator in description:
                return True

        return False

    def is_defensive_mastery(self) -> bool:
        """Check if this mastery provides defensive benefits."""
        defensive_indicators = ["defend", "ac", "save", "resistance"]
        description = (self.get_description() or "").lower()

        for indicator in defensive_indicators:
            if indicator in description:
                return True

        return False

    def is_utility_mastery(self) -> bool:
        """Check if this mastery provides utility benefits."""
        utility_indicators = ["move", "push", "prone", "advantage", "disadvantage"]
        description = (self.get_description() or "").lower()

        for indicator in utility_indicators:
            if indicator in description:
                return True

        return False

    def get_mastery_type(self) -> str:
        """Determine the type of mastery based on its effects."""
        if self.is_attack_mastery():
            return "Attack"
        elif self.is_defensive_mastery():
            return "Defensive"
        elif self.is_utility_mastery():
            return "Utility"
        else:
            return "General"

    def get_description(self) -> str | None:
        """Get a description of the mastery from entries."""
        if not self.entries:
            return None

        # Extract text from entries
        descriptions = []
        for entry in self.entries:
            if isinstance(entry, str):
                descriptions.append(entry)
            elif isinstance(entry, dict) and "entries" in entry:
                # Nested entries
                for nested in entry["entries"]:
                    if isinstance(nested, str):
                        descriptions.append(nested)

        return " ".join(descriptions) if descriptions else None

    def requires_proficiency(self) -> bool:
        """Check if this mastery requires weapon proficiency."""
        # Most masteries require proficiency, but check requirements
        if self.requirements:
            return any("proficiency" in req.lower() for req in self.requirements)
        return True  # Default assumption

    def has_usage_limit(self) -> bool:
        """Check if this mastery has a usage limit per turn/rest/etc."""
        description = (self.get_description() or "").lower()
        limit_indicators = ["once per turn", "per rest", "per day", "limit"]

        return any(indicator in description for indicator in limit_indicators)
