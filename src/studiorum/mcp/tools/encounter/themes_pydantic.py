"""Pydantic implementations of encounter theme models.

This module provides Pydantic BaseModel versions of the encounter theme dataclasses,
adding validation, serialization, and enhanced type safety for MCP tools and APIs.

These models maintain API compatibility with the original dataclass implementations
while adding field validation and JSON serialization capabilities.
"""

from typing import TYPE_CHECKING, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from studiorum.core.models.creatures import Creature

from studiorum.core.logging import get_logger

from .themes import EncounterTheme, EnvironmentType

logger = get_logger(__name__)


class EnvironmentalProfile(BaseModel):
    """Complete environmental profile for encounter generation with validation."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
    )

    environment: EnvironmentType
    climate: str = Field(
        default="temperate",
        pattern=r"^(temperate|tropical|cold|arid)$",
        description="Climate type affecting creature suitability",
    )
    terrain_difficulty: str = Field(
        default="normal",
        pattern=r"^(easy|normal|difficult|extreme)$",
        description="Terrain difficulty affecting movement and encounters",
    )
    lighting: str = Field(
        default="normal",
        pattern=r"^(bright|dim|dark|magical|normal)$",
        description="Lighting conditions affecting creature behavior",
    )
    weather: str = Field(
        default="clear",
        description="Current weather conditions",
    )

    # Environmental factors affecting encounters
    visibility_range: int = Field(
        default=120,
        ge=0,
        le=1000,
        description="Visibility range in feet",
    )
    movement_penalty: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        description="Movement speed multiplier (1.0 = normal)",
    )
    stealth_modifier: int = Field(
        default=0,
        ge=-10,
        le=10,
        description="Bonus/penalty to stealth checks",
    )
    sound_propagation: float = Field(
        default=1.0,
        gt=0.0,
        le=5.0,
        description="How far sounds carry (multiplier)",
    )

    # Creature type preferences (multipliers for suitability)
    creature_affinities: dict[str, float] = Field(
        default_factory=dict,
        description="Creature type affinity multipliers",
    )

    @field_validator("weather")
    @classmethod
    def validate_weather(cls, v: str) -> str:
        """Validate weather conditions.

        Args:
            v: Weather condition string

        Returns:
            Validated weather condition

        Raises:
            ValueError: If weather condition is invalid type
        """
        if not isinstance(v, str):
            raise ValueError(f"Weather must be a string, got: {type(v).__name__}")

        valid_weather = {
            "clear",
            "rain",
            "storm",
            "fog",
            "mist",
            "snow",
            "blizzard",
            "hail",
            "sleet",
            "wind",
            "calm",
            "overcast",
            "sunny",
        }

        normalized = v.strip().lower()
        if normalized not in valid_weather:
            logger.warning(
                f"Unknown weather condition: {v}. Valid options: {sorted(valid_weather)}"
            )

        return v

    @field_validator("creature_affinities")
    @classmethod
    def validate_creature_affinities(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate creature affinity values.

        Args:
            v: Dictionary mapping creature types to affinity multipliers

        Returns:
            Validated creature affinities dictionary

        Raises:
            ValueError: If any affinity value is outside valid range
        """
        for creature_type, affinity in v.items():
            if not isinstance(creature_type, str) or not creature_type.strip():
                raise ValueError(
                    f"Creature type must be a non-empty string, got: {creature_type}"
                )
            if not isinstance(affinity, int | float):
                raise ValueError(
                    f"Affinity for {creature_type} must be numeric, got: {type(affinity).__name__}"
                )
            if not 0.0 <= affinity <= 3.0:
                raise ValueError(
                    f"Creature affinity for {creature_type} must be between 0.0 and 3.0, got {affinity}"
                )
        return v

    @model_validator(mode="after")
    def initialize_creature_affinities(self) -> "EnvironmentalProfile":
        """Initialize creature affinities based on environment type if not provided."""
        if not self.creature_affinities:
            # Use object.__setattr__ to avoid triggering validation again
            object.__setattr__(
                self, "creature_affinities", self._get_default_affinities()
            )
        return self

    def _get_default_affinities(self) -> dict[str, float]:
        """Get default creature type affinities for this environment."""
        # Convert string back to enum for lookup since use_enum_values=True stores as string
        try:
            env_enum = EnvironmentType(self.environment)
        except (ValueError, TypeError):
            return {}  # Return empty dict if environment is invalid

        affinities = {
            EnvironmentType.FOREST: {
                "beast": 1.5,
                "fey": 1.4,
                "plant": 1.6,
                "elemental": 0.9,
                "humanoid": 1.1,
                "monstrosity": 1.0,
                "dragon": 0.8,
                "undead": 0.7,
                "fiend": 0.6,
                "celestial": 0.5,
            },
            EnvironmentType.DUNGEON: {
                "undead": 1.6,
                "construct": 1.3,
                "monstrosity": 1.4,
                "aberration": 1.2,
                "ooze": 1.5,
                "humanoid": 1.2,
                "fiend": 1.1,
                "elemental": 0.9,
                "beast": 0.7,
                "fey": 0.5,
                "celestial": 0.4,
            },
            EnvironmentType.DESERT: {
                "elemental": 1.5,
                "beast": 1.2,
                "monstrosity": 1.1,
                "dragon": 1.3,
                "construct": 1.1,
                "undead": 1.0,
                "humanoid": 0.9,
                "plant": 0.3,
                "fey": 0.4,
                "ooze": 0.2,
            },
            EnvironmentType.ARCTIC: {
                "elemental": 1.6,
                "giant": 1.5,
                "beast": 1.3,
                "dragon": 1.2,
                "monstrosity": 1.0,
                "construct": 0.9,
                "undead": 1.1,
                "plant": 0.2,
                "ooze": 0.3,
                "fey": 0.5,
            },
            EnvironmentType.SWAMP: {
                "undead": 1.4,
                "beast": 1.3,
                "dragon": 1.2,
                "plant": 1.5,
                "monstrosity": 1.3,
                "ooze": 1.4,
                "elemental": 1.0,
                "fey": 1.1,
                "fiend": 0.9,
                "celestial": 0.3,
            },
            EnvironmentType.MOUNTAIN: {
                "giant": 1.6,
                "dragon": 1.5,
                "elemental": 1.3,
                "beast": 1.2,
                "monstrosity": 1.1,
                "construct": 1.0,
                "humanoid": 0.9,
                "undead": 0.8,
                "fey": 0.7,
                "ooze": 0.4,
            },
            EnvironmentType.URBAN: {
                "humanoid": 1.6,
                "construct": 1.2,
                "monstrosity": 0.9,
                "fiend": 1.1,
                "undead": 1.0,
                "aberration": 0.8,
                "beast": 0.6,
                "elemental": 0.7,
                "fey": 0.5,
                "plant": 0.3,
            },
            EnvironmentType.COASTAL: {
                "beast": 1.4,
                "elemental": 1.3,
                "dragon": 1.1,
                "monstrosity": 1.2,
                "humanoid": 1.1,
                "fey": 1.0,
                "plant": 0.8,
                "undead": 0.9,
                "construct": 0.8,
                "ooze": 0.7,
            },
            EnvironmentType.UNDERWATER: {
                "elemental": 1.8,
                "beast": 1.6,
                "dragon": 1.3,
                "monstrosity": 1.4,
                "ooze": 1.2,
                "aberration": 1.1,
                "undead": 0.5,
                "construct": 0.6,
                "humanoid": 0.4,
                "fey": 0.3,
            },
            EnvironmentType.UNDERDARK: {
                "aberration": 1.7,
                "monstrosity": 1.5,
                "undead": 1.4,
                "ooze": 1.6,
                "construct": 1.2,
                "elemental": 1.1,
                "fiend": 1.2,
                "humanoid": 1.0,
                "beast": 0.8,
                "fey": 0.6,
                "celestial": 0.2,
            },
        }

        return affinities.get(env_enum, {})

    def calculate_creature_suitability(self, creature: "Creature") -> float:
        """Calculate creature suitability for this environment.

        Args:
            creature: Creature to evaluate

        Returns:
            Suitability score (0.0-2.0, where 1.0 is neutral)
        """
        base_score = 1.0

        # Get creature type
        creature_type = self._extract_creature_type(creature)
        if creature_type in self.creature_affinities:
            base_score *= self.creature_affinities[creature_type]

        # Apply environmental modifiers
        base_score *= self._apply_environmental_factors(creature)

        return min(2.0, max(0.0, base_score))

    def _extract_creature_type(self, creature: "Creature") -> str:
        """Extract primary creature type from creature data.

        Args:
            creature: Creature object to analyze

        Returns:
            Lowercase creature type string
        """
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                extracted_type = type_data.get("type", "unknown")
                return str(extracted_type).lower() if extracted_type else "unknown"
            elif isinstance(type_data, str):
                return type_data.lower()
        return "unknown"

    def _apply_environmental_factors(self, creature: "Creature") -> float:
        """Apply environmental factors to creature suitability.

        Args:
            creature: Creature to evaluate

        Returns:
            Environmental suitability modifier (0.1-2.0)
        """
        modifier = 1.0

        # Lighting considerations
        if self.lighting == "dark":
            # Creatures with darkvision are more suitable
            if self._creature_has_darkvision(creature):
                modifier *= 1.2
            else:
                modifier *= 0.8

        # Movement considerations
        if self.terrain_difficulty == "difficult":
            # Flying creatures have advantage in difficult terrain
            if self._creature_can_fly(creature):
                modifier *= 1.3
            else:
                modifier *= 0.9
        elif self.terrain_difficulty == "extreme":
            if self._creature_can_fly(creature):
                modifier *= 1.5
            else:
                modifier *= 0.7

        # Weather considerations
        if self.weather in ["storm", "blizzard"]:
            # Flying creatures struggle in storms
            if self._creature_can_fly(creature):
                modifier *= 0.7

        # Ensure modifier stays within reasonable bounds
        return max(0.1, min(2.0, modifier))

    def _creature_has_darkvision(self, creature: "Creature") -> bool:
        """Check if creature has darkvision.

        Args:
            creature: Creature to check

        Returns:
            True if creature has darkvision ability
        """
        if hasattr(creature, "senses") and creature.senses:
            senses_text = str(creature.senses).lower()
            return "darkvision" in senses_text
        return False

    def _creature_can_fly(self, creature: "Creature") -> bool:
        """Check if creature has fly speed.

        Args:
            creature: Creature to check

        Returns:
            True if creature has flight capability
        """
        if hasattr(creature, "speed") and isinstance(creature.speed, dict):
            return "fly" in creature.speed
        return False


class ThematicProfile(BaseModel):
    """Thematic profile for narrative-coherent encounters with validation."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
    )

    theme: EncounterTheme
    intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How strongly to enforce theme (0.0-2.0)",
    )
    allow_mixed: bool = Field(
        default=False,
        description="Allow creatures outside theme",
    )
    narrative_context: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Additional narrative context for encounter generation",
    )

    def calculate_thematic_fit(self, creature: "Creature") -> float:
        """Calculate how well creature fits the theme.

        Args:
            creature: Creature to evaluate

        Returns:
            Thematic fit score (0.0-2.0)
        """
        base_fit = self._get_base_thematic_fit(creature)

        # Apply intensity modifier
        if base_fit > 1.0:
            # Enhance good fits
            enhanced_fit = 1.0 + (base_fit - 1.0) * self.intensity
        else:
            # Penalize poor fits more strongly with high intensity
            enhanced_fit = base_fit**self.intensity

        # Allow mixed themes to have higher floor
        if self.allow_mixed:
            enhanced_fit = max(0.3, enhanced_fit)

        return min(2.0, max(0.0, enhanced_fit))

    def _get_base_thematic_fit(self, creature: "Creature") -> float:
        """Get base thematic fit for creature type."""
        creature_type = self._extract_creature_type(creature).lower()

        theme_affinities = {
            EncounterTheme.UNDEAD_HORROR: {
                "undead": 2.0,
                "construct": 1.2,
                "fiend": 1.1,
                "aberration": 1.3,
                "monstrosity": 1.1,
                "humanoid": 0.8,
                "beast": 0.3,
                "fey": 0.2,
                "celestial": 0.1,
            },
            EncounterTheme.ELEMENTAL_CHAOS: {
                "elemental": 2.0,
                "construct": 1.3,
                "dragon": 1.4,
                "monstrosity": 1.1,
                "beast": 0.8,
                "humanoid": 0.7,
                "undead": 0.5,
                "fey": 0.9,
            },
            EncounterTheme.FIENDISH_CORRUPTION: {
                "fiend": 2.0,
                "undead": 1.3,
                "monstrosity": 1.2,
                "aberration": 1.1,
                "construct": 1.0,
                "humanoid": 0.9,
                "celestial": 0.1,
                "fey": 0.4,
            },
            EncounterTheme.FEY_MYSTERY: {
                "fey": 2.0,
                "beast": 1.4,
                "plant": 1.5,
                "elemental": 1.2,
                "monstrosity": 1.0,
                "humanoid": 0.8,
                "undead": 0.3,
                "construct": 0.2,
            },
            EncounterTheme.DRACONIC_POWER: {
                "dragon": 2.0,
                "construct": 1.2,
                "elemental": 1.3,
                "monstrosity": 1.1,
                "humanoid": 1.0,
                "beast": 0.8,
                "undead": 0.6,
                "ooze": 0.4,
            },
            EncounterTheme.GIANT_MIGHT: {
                "giant": 2.0,
                "elemental": 1.2,
                "construct": 1.1,
                "beast": 1.3,
                "monstrosity": 1.0,
                "humanoid": 0.9,
                "dragon": 0.8,
                "ooze": 0.3,
            },
            EncounterTheme.BEAST_WILDERNESS: {
                "beast": 2.0,
                "monstrosity": 1.4,
                "plant": 1.3,
                "fey": 1.1,
                "elemental": 0.9,
                "humanoid": 0.6,
                "construct": 0.3,
                "undead": 0.2,
            },
            EncounterTheme.HUMANOID_CONFLICT: {
                "humanoid": 2.0,
                "construct": 1.1,
                "monstrosity": 0.8,
                "beast": 1.0,
                "undead": 0.7,
                "elemental": 0.6,
                "fey": 0.5,
                "celestial": 0.8,
            },
            EncounterTheme.CELESTIAL_DIVINE: {
                "celestial": 2.0,
                "construct": 1.2,
                "elemental": 1.1,
                "humanoid": 1.3,
                "fey": 1.0,
                "beast": 0.8,
                "fiend": 0.1,
                "undead": 0.2,
            },
            EncounterTheme.ABERRANT_MADNESS: {
                "aberration": 2.0,
                "monstrosity": 1.3,
                "ooze": 1.4,
                "construct": 1.1,
                "undead": 1.0,
                "humanoid": 0.7,
                "beast": 0.5,
                "celestial": 0.2,
            },
            EncounterTheme.CONSTRUCT_ANCIENT: {
                "construct": 2.0,
                "elemental": 1.2,
                "undead": 1.1,
                "monstrosity": 1.0,
                "aberration": 0.9,
                "humanoid": 0.8,
                "beast": 0.4,
                "fey": 0.3,
            },
            EncounterTheme.PLANT_NATURE: {
                "plant": 2.0,
                "fey": 1.5,
                "beast": 1.4,
                "elemental": 1.2,
                "monstrosity": 1.0,
                "humanoid": 0.7,
                "construct": 0.4,
                "undead": 0.2,
            },
        }

        # Convert string back to enum for lookup since use_enum_values=True stores as string
        try:
            theme_enum = EncounterTheme(self.theme)
        except (ValueError, TypeError):
            return 1.0 if self.allow_mixed else 0.5  # Fallback if theme is invalid

        affinities = theme_affinities.get(theme_enum, {})
        return affinities.get(creature_type, 1.0 if self.allow_mixed else 0.5)

    @field_validator("narrative_context")
    @classmethod
    def validate_narrative_context(
        cls, v: dict[str, str | int | float | bool]
    ) -> dict[str, str | int | float | bool]:
        """Validate narrative context contains only simple JSON-serializable values.

        Args:
            v: Narrative context dictionary

        Returns:
            Validated narrative context

        Raises:
            ValueError: If context contains invalid value types
        """
        for key, value in v.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"Context keys must be non-empty strings, got: {key}")
            if not isinstance(value, str | int | float | bool):
                raise ValueError(
                    f"Context value for '{key}' must be string, int, float, or bool, "
                    f"got: {type(value).__name__}"
                )
        return v

    def _extract_creature_type(self, creature: "Creature") -> str:
        """Extract creature type for thematic analysis.

        Args:
            creature: Creature object to analyze

        Returns:
            Lowercase creature type string for thematic matching
        """
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                extracted_type = type_data.get("type", "unknown")
                return str(extracted_type).lower() if extracted_type else "unknown"
            elif isinstance(type_data, str):
                return type_data.lower()
        return "unknown"
