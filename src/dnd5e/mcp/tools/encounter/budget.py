"""DMG-accurate encounter budget calculation system.

This module implements the encounter building rules from the Dungeon Master's Guide
(p. 82-85) for calculating encounter difficulty, XP budgets, and multipliers.

Provides mathematical precision for encounter balancing with full support for:
- Party size adjustments
- Multiple creature encounter multipliers
- Mixed-level party calculations
- Environmental and tactical modifiers
"""

import logging
from typing import Any

from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.encounter_types import (
    XP,
    ChallengeRating,
    EncounterBudget,
    EncounterDifficulty,
    PartyComposition,
    PartyLevel,
)

logger = logging.getLogger(__name__)


class EncounterBudgetCalculator:
    """DMG-compliant encounter budget calculator.

    Implements precise encounter difficulty calculations according to DMG rules
    with support for complex party compositions and creature combinations.
    """

    @staticmethod
    def calculate_encounter_budget(
        party: PartyComposition, difficulty: str = "medium"
    ) -> EncounterBudget:
        """Calculate encounter XP budget for given party and difficulty.

        Args:
            party: Party composition details
            difficulty: Target difficulty (easy/medium/hard/deadly)

        Returns:
            Complete encounter budget with thresholds and modifiers

        Raises:
            ValueError: If difficulty level is invalid
        """
        if difficulty not in ["easy", "medium", "hard", "deadly"]:
            raise ValueError(
                f"Invalid difficulty: {difficulty}. Must be easy/medium/hard/deadly"
            )

        # Calculate base difficulty thresholds
        thresholds = EncounterDifficulty.calculate_for_party(party)

        # Get target budget for requested difficulty
        budget_map = {
            "easy": thresholds.easy,
            "medium": thresholds.medium,
            "hard": thresholds.hard,
            "deadly": thresholds.deadly,
        }

        base_budget = budget_map[difficulty]

        # Apply party composition bonuses/penalties
        composition_modifier = (
            EncounterBudgetCalculator._calculate_composition_modifier(party)
        )
        adjusted_budget = XP(int(base_budget * composition_modifier))

        return EncounterBudget(
            difficulty=difficulty,
            base_xp_budget=base_budget,
            adjusted_xp_budget=adjusted_budget,
            party_level=party.get_effective_level(),
            party_size=party.size,
            party_composition_bonus=composition_modifier - 1.0,
        )

    @staticmethod
    def calculate_creature_xp_with_multiplier(
        creatures: list[Creature],
    ) -> tuple[XP, XP]:
        """Calculate total creature XP with encounter multipliers.

        Implements DMG Table 1-2 (p. 82) encounter multipliers based on
        number of creatures in the encounter.

        Args:
            creatures: List of creatures in the encounter

        Returns:
            Tuple of (base_xp_total, adjusted_xp_total)
        """
        if not creatures:
            return XP(0), XP(0)

        # Calculate base XP total
        base_xp = XP(
            sum(
                EncounterBudgetCalculator._get_creature_xp(creature)
                for creature in creatures
            )
        )

        # Get encounter multiplier based on creature count
        creature_count = len(creatures)
        multiplier = EncounterBudgetCalculator._get_encounter_multiplier(creature_count)

        # Apply multiplier to get adjusted XP
        adjusted_xp = XP(int(base_xp * multiplier))

        logger.debug(
            f"Encounter XP: {creature_count} creatures, {base_xp} base XP, "
            f"{multiplier}x multiplier = {adjusted_xp} adjusted XP"
        )

        return base_xp, adjusted_xp

    @staticmethod
    def calculate_encounter_difficulty_rating(
        creatures: list[Creature], party: PartyComposition
    ) -> dict[str, Any]:
        """Determine encounter difficulty rating for given creatures vs party.

        Args:
            creatures: Creatures in the encounter
            party: Party composition

        Returns:
            Dictionary with difficulty analysis
        """
        if not creatures:
            return {
                "difficulty": "trivial",
                "confidence": 1.0,
                "base_xp": 0,
                "adjusted_xp": 0,
                "recommendations": ["Add creatures to create meaningful encounter"],
            }

        # Calculate encounter XP
        base_xp, adjusted_xp = (
            EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(creatures)
        )

        # Get party thresholds
        thresholds = EncounterDifficulty.calculate_for_party(party)

        # Determine difficulty rating
        if adjusted_xp <= thresholds.easy:
            difficulty = "easy"
            confidence = 0.9
        elif adjusted_xp <= thresholds.medium:
            difficulty = "medium"
            confidence = 0.95
        elif adjusted_xp <= thresholds.hard:
            difficulty = "hard"
            confidence = 0.9
        elif adjusted_xp <= thresholds.deadly:
            difficulty = "deadly"
            confidence = 0.85
        else:
            difficulty = "overwhelming"
            confidence = 0.7

        # Generate recommendations
        recommendations = (
            EncounterBudgetCalculator._generate_difficulty_recommendations(
                difficulty, adjusted_xp, thresholds, len(creatures)
            )
        )

        return {
            "difficulty": difficulty,
            "confidence": confidence,
            "base_xp": int(base_xp),
            "adjusted_xp": int(adjusted_xp),
            "thresholds": {
                "easy": int(thresholds.easy),
                "medium": int(thresholds.medium),
                "hard": int(thresholds.hard),
                "deadly": int(thresholds.deadly),
            },
            "creature_count": len(creatures),
            "recommendations": recommendations,
        }

    @staticmethod
    def _get_creature_xp(creature: Creature) -> int:
        """Extract XP value from creature based on CR.

        Args:
            creature: Creature to get XP for

        Returns:
            XP value for the creature
        """
        if not hasattr(creature, "cr") or creature.cr is None:
            logger.warning(f"Creature {creature.name} has no CR data")
            return 0

        cr_string = str(creature.cr).lower().strip()

        # DMG Table A.1: Challenge Rating and XP
        cr_to_xp = {
            "0": 10,
            "1/8": 25,
            "1/4": 50,
            "1/2": 100,
            "1": 200,
            "2": 450,
            "3": 700,
            "4": 1100,
            "5": 1800,
            "6": 2300,
            "7": 2900,
            "8": 3900,
            "9": 5000,
            "10": 5900,
            "11": 7200,
            "12": 8400,
            "13": 10000,
            "14": 11500,
            "15": 13000,
            "16": 15000,
            "17": 18000,
            "18": 20000,
            "19": 22000,
            "20": 25000,
            "21": 33000,
            "22": 41000,
            "23": 50000,
            "24": 62000,
            "25": 75000,
            "26": 90000,
            "27": 105000,
            "28": 120000,
            "29": 135000,
            "30": 155000,
        }

        if cr_string in cr_to_xp:
            return cr_to_xp[cr_string]

        # Handle variable CR
        if cr_string in ["varies", "variable"]:
            logger.warning(f"Creature {creature.name} has variable CR, using 0 XP")
            return 0

        # Try parsing as float for custom CRs
        try:
            cr_float = float(cr_string)
            if cr_float <= 0:
                return 10
            elif cr_float <= 30:
                # Interpolate for fractional CRs not in table
                lower_cr = int(cr_float)
                if lower_cr in cr_to_xp:
                    return cr_to_xp[str(lower_cr)]
                else:
                    return 25000  # Default high CR
            else:
                return 155000  # Cap at CR 30 equivalent
        except ValueError:
            logger.warning(
                f"Could not parse CR '{cr_string}' for creature {creature.name}"
            )
            return 0

    @staticmethod
    def _get_encounter_multiplier(creature_count: int) -> float:
        """Get encounter multiplier based on creature count.

        From DMG Table 1-2 (p. 82):
        - 1 creature: ×1
        - 2 creatures: ×1.5
        - 3-6 creatures: ×2
        - 7-10 creatures: ×2.5
        - 11-14 creatures: ×3
        - 15+ creatures: ×4

        Args:
            creature_count: Number of creatures in encounter

        Returns:
            Encounter multiplier
        """
        if creature_count <= 1:
            return 1.0
        elif creature_count == 2:
            return 1.5
        elif creature_count <= 6:
            return 2.0
        elif creature_count <= 10:
            return 2.5
        elif creature_count <= 14:
            return 3.0
        else:
            return 4.0

    @staticmethod
    def _calculate_composition_modifier(party: PartyComposition) -> float:
        """Calculate party composition modifier for encounter difficulty.

        Args:
            party: Party composition details

        Returns:
            Multiplier for encounter difficulty (1.0 = standard)
        """
        # Base modifier from party size (already handled in PartyComposition.get_size_multiplier())
        size_modifier = party.get_size_multiplier()

        # Additional modifiers for mixed-level parties
        level_modifier = 1.0
        if party.individual_levels and len(set(party.individual_levels)) > 1:
            # Mixed-level parties are slightly harder to balance
            level_spread = max(party.individual_levels) - min(party.individual_levels)
            if level_spread > 2:
                level_modifier = 1.1  # 10% harder

        return size_modifier * level_modifier

    @staticmethod
    def _generate_difficulty_recommendations(
        difficulty: str,
        adjusted_xp: XP,
        thresholds: EncounterDifficulty,
        creature_count: int,
    ) -> list[str]:
        """Generate recommendations for encounter difficulty adjustment.

        Args:
            difficulty: Current difficulty rating
            adjusted_xp: Current encounter adjusted XP
            thresholds: Party difficulty thresholds
            creature_count: Number of creatures

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if difficulty == "trivial":
            recommendations.append(
                "Encounter is too easy - add more creatures or increase CR"
            )
            recommendations.append(
                f"Target XP: {thresholds.easy} (easy) to {thresholds.medium} (medium)"
            )

        elif difficulty == "overwhelming":
            recommendations.append(
                "Encounter may be overwhelming - consider reducing creature count or CR"
            )
            recommendations.append(
                f"Current XP ({adjusted_xp}) exceeds deadly threshold ({thresholds.deadly})"
            )

        elif difficulty == "deadly":
            recommendations.append("Deadly encounter - ensure party has full resources")
            recommendations.append(
                "Consider environmental escape routes or tactical advantages for PCs"
            )

        # Creature count recommendations
        if creature_count == 1:
            recommendations.append(
                "Single creature encounter - consider legendary/lair actions"
            )
        elif creature_count > 8:
            recommendations.append("Large encounter - may slow combat significantly")

        # XP efficiency recommendations
        if creature_count >= 3:
            multiplier = EncounterBudgetCalculator._get_encounter_multiplier(
                creature_count
            )
            base_xp = XP(int(adjusted_xp / multiplier))
            recommendations.append(
                f"Encounter multiplier: ×{multiplier} ({base_xp} base XP → {adjusted_xp} adjusted)"
            )

        return recommendations


def calculate_encounter_budget(
    party_size: int,
    party_level: int,
    difficulty: str = "medium",
    individual_levels: list[int] | None = None,
) -> dict[str, Any]:
    """Calculate encounter budget for MCP tool interface.

    Args:
        party_size: Number of party members
        party_level: Average party level
        difficulty: Target difficulty (easy/medium/hard/deadly)
        individual_levels: Individual character levels for mixed parties

    Returns:
        Dictionary with encounter budget details

    Raises:
        ValueError: If parameters are invalid
    """
    if party_size < 1 or party_size > 8:
        raise ValueError("Party size must be between 1 and 8")

    if party_level < 1 or party_level > 20:
        raise ValueError("Party level must be between 1 and 20")

    if individual_levels:
        if len(individual_levels) != party_size:
            raise ValueError("individual_levels length must match party_size")
        if any(level < 1 or level > 20 for level in individual_levels):
            raise ValueError("All individual levels must be between 1 and 20")

    try:
        # Create party composition
        party = PartyComposition(
            size=party_size,
            level=PartyLevel(party_level),
            individual_levels=individual_levels,
        )

        # Calculate budget
        budget = EncounterBudgetCalculator.calculate_encounter_budget(party, difficulty)

        # Get all thresholds for reference
        thresholds = EncounterDifficulty.calculate_for_party(party)

        return {
            "target_difficulty": difficulty,
            "base_xp_budget": int(budget.base_xp_budget),
            "adjusted_xp_budget": int(budget.adjusted_xp_budget),
            "party_level": int(budget.party_level),
            "party_size": budget.party_size,
            "composition_modifier": round(budget.party_composition_bonus + 1.0, 2),
            "thresholds": {
                "easy": int(thresholds.easy),
                "medium": int(thresholds.medium),
                "hard": int(thresholds.hard),
                "deadly": int(thresholds.deadly),
            },
            "recommendations": [
                f"Target {difficulty} encounter: {int(budget.adjusted_xp_budget)} adjusted XP",
                f"Party size modifier: {party.get_size_multiplier()}x",
                f"Effective party level: {party.get_effective_level()}",
            ],
        }

    except Exception as e:
        logger.error(f"Encounter budget calculation failed: {e}")
        raise ValueError(f"Budget calculation failed: {e}")
