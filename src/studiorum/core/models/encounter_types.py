"""Mathematical types and data structures for encounter building.

This module defines NewType aliases and core data models for the encounter building
system, providing type safety for XP calculations, party composition, and encounter
identification.

Used throughout the encounter building pipeline for type-safe mathematical operations
and clear separation between different numeric concepts.
"""

from typing import Any, NewType

from pydantic import BaseModel, Field

from studiorum.core.models.creature_filters import CreatureFilterCriteria

# Mathematical NewTypes for type safety
XP = NewType("XP", int)
"""Experience points type for encounter budget calculations."""

PartyLevel = NewType("PartyLevel", int)
"""Party level type for encounter balancing."""

EncounterId = NewType("EncounterId", str)
"""Unique identifier for encounter instances."""

ChallengeRating = NewType("ChallengeRating", float)
"""Challenge rating type for creatures and encounters."""


class PartyComposition(BaseModel):
    """Represents party composition for encounter calculations.

    Tracks party size, level, and composition bonuses for accurate
    encounter difficulty calculations.
    """

    size: int = Field(ge=1, le=8, description="Number of party members")
    level: PartyLevel = Field(ge=1, le=20, description="Average party level")
    individual_levels: list[int] | None = Field(
        None, description="Individual character levels for mixed-level parties"
    )

    def get_effective_level(self) -> PartyLevel:
        """Calculate effective party level.

        For mixed-level parties, uses weighted average.
        For same-level parties, returns the common level.

        Returns:
            Effective party level for encounter calculations
        """
        if self.individual_levels:
            return PartyLevel(
                sum(self.individual_levels) // len(self.individual_levels)
            )
        return self.level

    def get_size_multiplier(self) -> float:
        """Get encounter multiplier based on party size.

        DMG p. 82 - smaller/larger parties modify encounter difficulty:
        - 3-4 characters: standard multiplier
        - 5-6 characters: encounters are easier
        - 7-8 characters: encounters are much easier
        - 1-2 characters: encounters are harder

        Returns:
            Multiplier for encounter XP budget adjustments
        """
        if self.size <= 2:
            return 1.5  # Encounters are harder for small parties
        elif self.size >= 7:
            return 0.5  # Encounters are easier for large parties
        elif self.size >= 5:
            return 0.75  # Encounters are somewhat easier
        else:
            return 1.0  # Standard difficulty for 3-4 characters


class EncounterDifficulty(BaseModel):
    """Represents encounter difficulty thresholds and budgets.

    Based on DMG encounter building rules with XP thresholds
    for different difficulty levels.
    """

    easy: XP = Field(description="Easy encounter XP threshold")
    medium: XP = Field(description="Medium encounter XP threshold")
    hard: XP = Field(description="Hard encounter XP threshold")
    deadly: XP = Field(description="Deadly encounter XP threshold")

    @classmethod
    def calculate_for_party(cls, party: PartyComposition) -> "EncounterDifficulty":
        """Calculate encounter difficulty thresholds for a party.

        Uses DMG Table 1-1 (p. 82) encounter thresholds per character level,
        adjusted for party size and composition.

        Args:
            party: Party composition to calculate for

        Returns:
            Encounter difficulty thresholds
        """
        level = party.get_effective_level()
        size = party.size

        # DMG Table 1-1: Encounter Thresholds by Character Level
        thresholds_per_level = {
            1: (25, 50, 75, 100),
            2: (50, 100, 150, 200),
            3: (75, 150, 225, 300),
            4: (125, 250, 375, 500),
            5: (250, 500, 750, 1100),
            6: (300, 600, 900, 1400),
            7: (350, 750, 1100, 1700),
            8: (450, 900, 1400, 2100),
            9: (550, 1100, 1600, 2400),
            10: (600, 1200, 1900, 2800),
            11: (800, 1600, 2400, 3600),
            12: (1000, 2000, 3000, 4500),
            13: (1100, 2200, 3400, 5100),
            14: (1250, 2500, 3800, 5700),
            15: (1400, 2800, 4300, 6400),
            16: (1600, 3200, 4800, 7200),
            17: (2000, 3900, 5900, 8800),
            18: (2100, 4200, 6300, 9500),
            19: (2400, 4900, 7300, 10900),
            20: (2800, 5700, 8500, 12700),
        }

        easy, medium, hard, deadly = thresholds_per_level.get(
            level, (250, 500, 750, 1100)
        )

        # Multiply by party size
        party_easy = XP(easy * size)
        party_medium = XP(medium * size)
        party_hard = XP(hard * size)
        party_deadly = XP(deadly * size)

        # Apply party size modifier
        size_multiplier = party.get_size_multiplier()

        return cls(
            easy=XP(int(party_easy * size_multiplier)),
            medium=XP(int(party_medium * size_multiplier)),
            hard=XP(int(party_hard * size_multiplier)),
            deadly=XP(int(party_deadly * size_multiplier)),
        )


class EncounterBudget(BaseModel):
    """Represents an encounter's XP budget and difficulty assessment.

    Tracks both base creature XP and adjusted XP based on encounter
    multipliers from multiple creatures.
    """

    difficulty: str = Field(
        description="Encounter difficulty (easy/medium/hard/deadly)"
    )
    base_xp_budget: XP = Field(description="Target XP budget for this difficulty")
    adjusted_xp_budget: XP = Field(description="Actual XP budget with multipliers")
    party_level: PartyLevel = Field(description="Party level for this encounter")
    party_size: int = Field(ge=1, le=8, description="Number of party members")
    party_composition_bonus: float = Field(
        default=0.0, description="Bonus/penalty from party composition"
    )

    def get_difficulty_rating(self, actual_xp: XP) -> str:
        """Determine encounter difficulty based on actual XP.

        Args:
            actual_xp: Total adjusted XP of encounter creatures

        Returns:
            Difficulty rating string
        """
        if actual_xp <= self.base_xp_budget * 0.5:
            return "trivial"
        elif actual_xp <= self.base_xp_budget:
            return self.difficulty
        elif actual_xp <= self.base_xp_budget * 1.5:
            return "hard" if self.difficulty == "medium" else "deadly"
        else:
            return "overwhelming"


class EncounterConstraints(CreatureFilterCriteria):
    """Extended creature filtering criteria for encounter-specific constraints.

    Builds on the existing CreatureFilterCriteria with additional constraints
    specific to encounter building, such as legendary creature limits and
    environmental considerations.
    """

    # Encounter-specific constraints
    no_legendary: bool = Field(
        default=False, description="Exclude creatures with legendary actions"
    )
    no_lair_actions: bool = Field(
        default=False, description="Exclude creatures with lair actions"
    )
    environment: str | None = Field(
        None, description="Environmental constraint (forest, dungeon, etc.)"
    )
    max_creatures: int | None = Field(
        None, ge=1, le=12, description="Maximum number of creatures in encounter"
    )
    encounter_theme: str | None = Field(
        None, description="Thematic constraint (undead, elemental, etc.)"
    )

    # Budget constraints
    min_xp_per_creature: XP | None = Field(
        None, ge=0, description="Minimum XP value per creature"
    )
    max_xp_per_creature: XP | None = Field(
        None, ge=0, description="Maximum XP value per creature"
    )
    allow_single_powerful: bool = Field(
        default=True, description="Allow single high-CR creatures"
    )
    prefer_multiple_weaker: bool = Field(
        default=False, description="Prefer multiple weaker creatures"
    )

    # Tactical constraints
    require_minions: bool = Field(
        default=False, description="Require low-CR minion creatures"
    )
    require_boss: bool = Field(
        default=False, description="Require single high-CR boss creature"
    )
    mixed_creature_types: bool = Field(
        default=False, description="Mix different creature types"
    )

    def model_post_init(self, __context: dict | None = None) -> None:
        """Validate logical consistency of filter criteria including encounter-specific ones."""
        # Check CR range consistency
        if (
            self.min_cr is not None
            and self.max_cr is not None
            and self.min_cr > self.max_cr
        ):
            raise ValueError("min_cr cannot be greater than max_cr")

        # Check AC range consistency
        if (
            self.min_ac is not None
            and self.max_ac is not None
            and self.min_ac > self.max_ac
        ):
            raise ValueError("min_ac cannot be greater than max_ac")

        # Check HP range consistency
        if (
            self.min_hp is not None
            and self.max_hp is not None
            and self.min_hp > self.max_hp
        ):
            raise ValueError("min_hp cannot be greater than max_hp")

        # Validate that at least one filtering criterion is provided
        # Include both base criteria and encounter-specific criteria
        has_base_criteria = any(
            [
                self.min_cr is not None,
                self.max_cr is not None,
                self.cr_range is not None,
                self.creature_types is not None,
                self.creature_tags is not None,
                self.sizes is not None,
                self.alignments is not None,
                self.min_ac is not None,
                self.max_ac is not None,
                self.min_hp is not None,
                self.max_hp is not None,
                self.damage_immunities is not None,
                self.damage_resistances is not None,
                self.damage_vulnerabilities is not None,
                self.condition_immunities is not None,
                self.has_spellcasting is not None,
                self.has_innate_spellcasting is not None,
                self.has_legendary_actions is not None,
                self.has_multiattack is not None,
                self.has_reactions is not None,
                self.has_bonus_actions is not None,
                self.has_fly_speed is not None,
                self.has_swim_speed is not None,
                self.has_climb_speed is not None,
                self.has_burrow_speed is not None,
                self.has_darkvision is not None,
                self.has_blindsight is not None,
                self.has_tremorsense is not None,
                self.has_truesight is not None,
                self.speaks_language is not None,
                self.has_skill is not None,
                self.sources is not None,
                self.creature_names is not None,
            ]
        )

        # Check encounter-specific criteria
        has_encounter_criteria = any(
            [
                self.no_legendary,
                self.no_lair_actions,
                self.environment is not None,
                self.max_creatures is not None,
                self.encounter_theme is not None,
                self.min_xp_per_creature is not None,
                self.max_xp_per_creature is not None,
                not self.allow_single_powerful,  # Only count when explicitly disabled
                self.prefer_multiple_weaker,
                self.require_minions,
                self.require_boss,
                self.mixed_creature_types,
            ]
        )

        if not (has_base_criteria or has_encounter_criteria):
            raise ValueError("At least one filtering criterion must be provided")

    def validate_for_encounter(self) -> None:
        """Validate constraint combination for encounter building.

        Raises:
            ValueError: If constraints are contradictory
        """
        if self.require_boss and self.prefer_multiple_weaker:
            raise ValueError("Cannot require boss and prefer multiple weaker creatures")

        if self.max_creatures is not None and self.max_creatures < 1:
            raise ValueError("max_creatures must be at least 1")

        if (
            self.min_xp_per_creature is not None
            and self.max_xp_per_creature is not None
            and self.min_xp_per_creature > self.max_xp_per_creature
        ):
            raise ValueError("min_xp_per_creature cannot exceed max_xp_per_creature")


class EnvironmentalModifiers(BaseModel):
    """Environmental modifiers for encounter generation.

    Tracks environmental factors that affect creature selection
    and encounter balance.
    """

    environment_type: str = Field(
        description="Environment type (forest, dungeon, etc.)"
    )
    lighting: str | None = Field(
        None, description="Lighting conditions (bright, dim, dark)"
    )
    terrain_difficulty: str | None = Field(
        None, description="Terrain difficulty (easy, difficult, extreme)"
    )
    weather_conditions: str | None = Field(
        None, description="Weather conditions affecting encounter"
    )

    # Modifier effects
    stealth_modifier: float = Field(
        default=0.0, description="Stealth difficulty modifier"
    )
    mobility_modifier: float = Field(default=0.0, description="Movement penalty/bonus")
    visibility_modifier: float = Field(default=0.0, description="Vision range modifier")

    def get_creature_suitability(self, creature_tags: list[str]) -> float:
        """Calculate how suitable a creature is for this environment.

        Args:
            creature_tags: Creature type tags to evaluate

        Returns:
            Suitability score (0.0-2.0, where 1.0 is neutral)
        """
        base_score = 1.0

        # Environment-specific bonuses
        environment_bonuses = {
            "forest": {"beast": 0.3, "fey": 0.2, "plant": 0.4},
            "dungeon": {"undead": 0.2, "construct": 0.1, "monstrosity": 0.1},
            "desert": {"elemental": 0.2, "beast": 0.1},
            "arctic": {"elemental": 0.3, "giant": 0.1},
            "swamp": {"undead": 0.2, "beast": 0.1, "dragon": 0.1},
            "mountain": {"giant": 0.3, "dragon": 0.2, "elemental": 0.1},
            "urban": {"humanoid": 0.2, "construct": 0.1},
            "coastal": {"beast": 0.2, "elemental": 0.1},
            "underwater": {"elemental": 0.4, "beast": 0.3},
        }

        env_bonuses = environment_bonuses.get(self.environment_type.lower(), {})
        for tag in creature_tags:
            base_score += env_bonuses.get(tag.lower(), 0.0)

        # Lighting penalties for creatures without darkvision
        if self.lighting == "dark":
            # This would need creature data to properly evaluate
            # For now, assume neutral
            pass

        return min(2.0, max(0.0, base_score))
