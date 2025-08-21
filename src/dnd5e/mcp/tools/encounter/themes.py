"""Environmental and thematic creature selection for encounters.

This module provides sophisticated environment-based creature filtering and
thematic encounter generation, supporting immersive world-building and
narrative-appropriate encounters.

Leverages existing creature type/tag filtering with advanced environmental
modeling and thematic coherence scoring.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.encounter_types import (
    EncounterConstraints,
    EnvironmentalModifiers,
)
from dnd5e.core.services.encounter_collector import (
    EncounterCollector,
    EncounterCreature,
)

logger = logging.getLogger(__name__)


class EnvironmentType(Enum):
    """Standard D&D environment types with creature affinity data."""

    FOREST = "forest"
    DUNGEON = "dungeon"
    DESERT = "desert"
    ARCTIC = "arctic"
    SWAMP = "swamp"
    MOUNTAIN = "mountain"
    URBAN = "urban"
    COASTAL = "coastal"
    UNDERWATER = "underwater"
    PLANAR = "planar"
    UNDERDARK = "underdark"


class EncounterTheme(Enum):
    """Thematic encounter categories for narrative coherence."""

    UNDEAD_HORROR = "undead_horror"
    ELEMENTAL_CHAOS = "elemental_chaos"
    FIENDISH_CORRUPTION = "fiendish_corruption"
    FEY_MYSTERY = "fey_mystery"
    DRACONIC_POWER = "draconic_power"
    GIANT_MIGHT = "giant_might"
    BEAST_WILDERNESS = "beast_wilderness"
    HUMANOID_CONFLICT = "humanoid_conflict"
    CELESTIAL_DIVINE = "celestial_divine"
    ABERRANT_MADNESS = "aberrant_madness"
    CONSTRUCT_ANCIENT = "construct_ancient"
    OOZE_PRIMAL = "ooze_primal"
    PLANT_NATURE = "plant_nature"
    MIXED_CHAOS = "mixed_chaos"


@dataclass
class EnvironmentalProfile:
    """Complete environmental profile for encounter generation."""

    environment: EnvironmentType
    climate: str = "temperate"  # temperate, tropical, cold, arid
    terrain_difficulty: str = "normal"  # easy, normal, difficult, extreme
    lighting: str = "normal"  # bright, dim, dark, magical
    weather: str = "clear"  # clear, rain, storm, fog, etc.

    # Environmental factors affecting encounters
    visibility_range: int = 120  # feet
    movement_penalty: float = 1.0  # multiplier for movement
    stealth_modifier: int = 0  # bonus/penalty to stealth
    sound_propagation: float = 1.0  # how far sounds carry

    # Creature type preferences (multipliers for suitability)
    creature_affinities: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize creature affinities based on environment type."""
        if not self.creature_affinities:
            self.creature_affinities = self._get_default_affinities()

    def _get_default_affinities(self) -> dict[str, float]:
        """Get default creature type affinities for this environment."""
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

        return affinities.get(self.environment, {})

    def calculate_creature_suitability(self, creature: Creature) -> float:
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

    def _extract_creature_type(self, creature: Creature) -> str:
        """Extract primary creature type from creature data."""
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                return type_data.get("type", "unknown").lower()
            elif isinstance(type_data, str):
                return type_data.lower()
        return "unknown"

    def _apply_environmental_factors(self, creature: Creature) -> float:
        """Apply environmental factors to creature suitability."""
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

        return modifier

    def _creature_has_darkvision(self, creature: Creature) -> bool:
        """Check if creature has darkvision."""
        if hasattr(creature, "senses") and creature.senses:
            senses_text = str(creature.senses).lower()
            return "darkvision" in senses_text
        return False

    def _creature_can_fly(self, creature: Creature) -> bool:
        """Check if creature has fly speed."""
        if hasattr(creature, "speed") and isinstance(creature.speed, dict):
            return "fly" in creature.speed
        return False


@dataclass
class ThematicProfile:
    """Thematic profile for narrative-coherent encounters."""

    theme: EncounterTheme
    intensity: float = 1.0  # 0.0-2.0, how strongly to enforce theme
    allow_mixed: bool = False  # Allow creatures outside theme
    narrative_context: dict[str, Any] = field(default_factory=dict)

    def calculate_thematic_fit(self, creature: Creature) -> float:
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

    def _get_base_thematic_fit(self, creature: Creature) -> float:
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

        affinities = theme_affinities.get(self.theme, {})
        return affinities.get(creature_type, 1.0 if self.allow_mixed else 0.5)

    def _extract_creature_type(self, creature: Creature) -> str:
        """Extract creature type for thematic analysis."""
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                return type_data.get("type", "unknown").lower()
            elif isinstance(type_data, str):
                return type_data.lower()
        return "unknown"


class ThematicEncounterGenerator:
    """Generator for thematically coherent encounters with environmental considerations."""

    def __init__(self, encounter_collector: EncounterCollector):
        """Initialize thematic encounter generator.

        Args:
            encounter_collector: Base encounter collection service
        """
        self.collector = encounter_collector

    def generate_environmental_encounter(
        self,
        environmental_profile: EnvironmentalProfile,
        encounter_constraints: EncounterConstraints,
        min_suitability: float = 0.7,
    ) -> list[EncounterCreature]:
        """Generate encounter optimized for specific environment.

        Args:
            environmental_profile: Target environment details
            encounter_constraints: Base encounter constraints
            min_suitability: Minimum environmental suitability threshold

        Returns:
            List of environmentally-suitable encounter creatures
        """
        logger.info(
            f"Generating encounter for {environmental_profile.environment.value} environment"
        )

        # Get candidate creatures matching base constraints
        candidates_result = self.collector.search_creatures_for_encounter(
            encounter_constraints
        )

        if not candidates_result.creatures:
            logger.warning("No creatures found matching base constraints")
            return []

        # Score creatures by environmental suitability
        scored_creatures = []
        for creature in candidates_result.creatures:
            suitability = environmental_profile.calculate_creature_suitability(creature)
            if suitability >= min_suitability:
                scored_creatures.append((creature, suitability))

        # Sort by suitability score
        scored_creatures.sort(key=lambda x: x[1], reverse=True)

        # Convert to EncounterCreature objects
        encounter_creatures = []
        for creature, suitability in scored_creatures[:20]:  # Limit to top 20
            encounter_creatures.append(
                EncounterCreature(
                    creature=creature,
                    environmental_suitability=suitability,
                    tactical_role="combatant",
                )
            )

        logger.info(
            f"Found {len(encounter_creatures)} environmentally suitable creatures"
        )
        return encounter_creatures

    def generate_thematic_encounter(
        self,
        thematic_profile: ThematicProfile,
        encounter_constraints: EncounterConstraints,
        min_fit: float = 0.8,
    ) -> list[EncounterCreature]:
        """Generate encounter matching specific theme.

        Args:
            thematic_profile: Target theme details
            encounter_constraints: Base encounter constraints
            min_fit: Minimum thematic fit threshold

        Returns:
            List of thematically-appropriate encounter creatures
        """
        logger.info(f"Generating {thematic_profile.theme.value} themed encounter")

        # Override encounter theme constraint
        themed_constraints = encounter_constraints.model_copy()
        themed_constraints.encounter_theme = thematic_profile.theme.value

        # Get candidate creatures
        candidates_result = self.collector.search_creatures_for_encounter(
            themed_constraints
        )

        if not candidates_result.creatures:
            logger.warning("No creatures found matching themed constraints")
            return []

        # Score creatures by thematic fit
        scored_creatures = []
        for creature in candidates_result.creatures:
            thematic_fit = thematic_profile.calculate_thematic_fit(creature)
            if thematic_fit >= min_fit:
                scored_creatures.append((creature, thematic_fit))

        # Sort by thematic fit
        scored_creatures.sort(key=lambda x: x[1], reverse=True)

        # Convert to EncounterCreature objects
        encounter_creatures = []
        for creature, fit_score in scored_creatures[:20]:  # Limit to top 20
            encounter_creatures.append(
                EncounterCreature(
                    creature=creature,
                    environmental_suitability=fit_score,  # Using fit as suitability proxy
                    tactical_role=self._determine_thematic_role(
                        creature, thematic_profile
                    ),
                )
            )

        logger.info(
            f"Found {len(encounter_creatures)} thematically appropriate creatures"
        )
        return encounter_creatures

    def generate_themed_environmental_encounter(
        self,
        environmental_profile: EnvironmentalProfile,
        thematic_profile: ThematicProfile,
        encounter_constraints: EncounterConstraints,
        balance_weight: float = 0.5,  # 0.0 = pure environmental, 1.0 = pure thematic
    ) -> list[EncounterCreature]:
        """Generate encounter balancing environmental and thematic considerations.

        Args:
            environmental_profile: Environment details
            thematic_profile: Theme details
            encounter_constraints: Base constraints
            balance_weight: How to balance environment vs theme (0.0-1.0)

        Returns:
            List of creatures balancing both environment and theme
        """
        logger.info(
            f"Generating themed environmental encounter: {environmental_profile.environment.value} "
            f"+ {thematic_profile.theme.value} (balance: {balance_weight:.1f})"
        )

        # Get base candidates
        candidates_result = self.collector.search_creatures_for_encounter(
            encounter_constraints
        )

        if not candidates_result.creatures:
            return []

        # Score creatures by combined environmental and thematic fit
        scored_creatures = []
        for creature in candidates_result.creatures:
            env_score = environmental_profile.calculate_creature_suitability(creature)
            theme_score = thematic_profile.calculate_thematic_fit(creature)

            # Weighted combination
            combined_score = (
                env_score * (1 - balance_weight) + theme_score * balance_weight
            )

            # Minimum threshold for inclusion (both factors must be reasonable)
            min_env = 0.5 if balance_weight > 0.7 else 0.7
            min_theme = 0.5 if balance_weight < 0.3 else 0.7

            if env_score >= min_env and theme_score >= min_theme:
                scored_creatures.append(
                    (creature, combined_score, env_score, theme_score)
                )

        # Sort by combined score
        scored_creatures.sort(key=lambda x: x[1], reverse=True)

        # Create encounter creatures with full metadata
        encounter_creatures = []
        for creature, combined_score, env_score, theme_score in scored_creatures[:20]:
            encounter_creatures.append(
                EncounterCreature(
                    creature=creature,
                    environmental_suitability=env_score,
                    tactical_role=self._determine_thematic_role(
                        creature, thematic_profile
                    ),
                    # Store additional scoring in creature metadata if needed
                )
            )

        logger.info(
            f"Generated {len(encounter_creatures)} creatures balancing environment and theme"
        )
        return encounter_creatures

    def _determine_thematic_role(
        self, creature: Creature, theme_profile: ThematicProfile
    ) -> str:
        """Determine tactical role based on creature and theme."""
        creature_type = self._extract_creature_type(creature).lower()

        # Role assignments based on theme
        role_mappings = {
            EncounterTheme.UNDEAD_HORROR: {
                "undead": "boss" if self._is_high_cr(creature) else "combatant",
                "default": "minion",
            },
            EncounterTheme.DRACONIC_POWER: {
                "dragon": "boss",
                "default": "minion",
            },
            EncounterTheme.GIANT_MIGHT: {
                "giant": "boss",
                "default": "minion",
            },
        }

        theme_roles = role_mappings.get(theme_profile.theme, {"default": "combatant"})
        return theme_roles.get(creature_type, theme_roles["default"])

    def _extract_creature_type(self, creature: Creature) -> str:
        """Extract creature type for role determination."""
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                return type_data.get("type", "unknown")
            elif isinstance(type_data, str):
                return type_data
        return "unknown"

    def _is_high_cr(self, creature: Creature) -> bool:
        """Check if creature is high challenge rating (CR 5+)."""
        if hasattr(creature, "cr") and creature.cr is not None:
            cr_str = str(creature.cr).lower()
            if cr_str.isdigit():
                return int(cr_str) >= 5
        return False


# Convenience functions for MCP interface


def create_environmental_profile(
    environment: str,
    climate: str = "temperate",
    terrain_difficulty: str = "normal",
    lighting: str = "normal",
    weather: str = "clear",
) -> EnvironmentalProfile:
    """Create environmental profile from string parameters.

    Args:
        environment: Environment type string
        climate: Climate string
        terrain_difficulty: Terrain difficulty string
        lighting: Lighting conditions string
        weather: Weather conditions string

    Returns:
        Environmental profile object

    Raises:
        ValueError: If environment type is invalid
    """
    try:
        env_type = EnvironmentType(environment.lower())
    except ValueError:
        raise ValueError(
            f"Invalid environment type: {environment}. "
            f"Valid types: {[e.value for e in EnvironmentType]}"
        )

    return EnvironmentalProfile(
        environment=env_type,
        climate=climate,
        terrain_difficulty=terrain_difficulty,
        lighting=lighting,
        weather=weather,
    )


def create_thematic_profile(
    theme: str,
    intensity: float = 1.0,
    allow_mixed: bool = False,
    narrative_context: dict[str, Any] | None = None,
) -> ThematicProfile:
    """Create thematic profile from string parameters.

    Args:
        theme: Encounter theme string
        intensity: Theme enforcement intensity
        allow_mixed: Whether to allow creatures outside theme
        narrative_context: Additional narrative context

    Returns:
        Thematic profile object

    Raises:
        ValueError: If theme is invalid
    """
    try:
        theme_type = EncounterTheme(theme.lower())
    except ValueError:
        raise ValueError(
            f"Invalid theme: {theme}. Valid themes: {[t.value for t in EncounterTheme]}"
        )

    return ThematicProfile(
        theme=theme_type,
        intensity=intensity,
        allow_mixed=allow_mixed,
        narrative_context=narrative_context or {},
    )
