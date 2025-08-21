"""Enhanced creature collection service for encounter building.

This module extends the base CreatureCollector with encounter-specific functionality,
including constraint-based filtering, XP budget matching, and tactical analysis.

Maintains <200ms performance targets through optimized queries and caching while
providing sophisticated encounter generation capabilities.
"""

from dataclasses import dataclass
from typing import Any, cast

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.logging import get_logger
from studiorum.core.models.creatures import Creature
from studiorum.core.models.encounter_types import (
    XP,
    ChallengeRating,
    EncounterConstraints,
    EncounterId,
    EnvironmentalModifiers,
    PartyComposition,
)
from studiorum.core.services.creature_collector import (
    CreatureCollectionResult,
    CreatureCollector,
)
from studiorum.mcp.tools.encounter.budget import EncounterBudgetCalculator

logger = get_logger(__name__)


@dataclass
class EncounterCreature:
    """Represents a creature with encounter-specific metadata.

    Extends basic creature information with tactical role analysis
    and encounter context.
    """

    creature: Creature
    quantity: int = 1
    tactical_role: str = "combatant"  # combatant, minion, boss, support
    xp_contribution: XP = XP(0)
    environmental_suitability: float = 1.0
    threat_rating: float = 1.0

    def __post_init__(self) -> None:
        """Calculate derived values after initialization."""
        if self.xp_contribution == XP(0):
            self.xp_contribution = XP(
                EncounterBudgetCalculator._get_creature_xp(self.creature)
                * self.quantity
            )


@dataclass
class EncounterGenerationResult:
    """Results from encounter generation with analysis and suggestions."""

    encounter_id: EncounterId
    creatures: list[EncounterCreature]
    total_base_xp: XP
    total_adjusted_xp: XP
    difficulty_rating: str
    balance_score: float  # 0.0-1.0, higher is better balanced
    tactical_analysis: dict[str, Any]
    environmental_fit: float  # 0.0-1.0, higher is better environmental match
    rebalance_suggestions: list[str]
    generation_time_ms: float

    @property
    def creature_count(self) -> int:
        """Total number of individual creatures in encounter."""
        return sum(enc_creature.quantity for enc_creature in self.creatures)

    @property
    def unique_creatures(self) -> int:
        """Number of unique creature types in encounter."""
        return len(self.creatures)


class EncounterCollector(CreatureCollector):
    """Enhanced creature collector with encounter-specific capabilities.

    Extends the base CreatureCollector with methods optimized for encounter
    building, including XP budget matching, environmental filtering, and
    tactical role assignment.

    Performance targets:
    - <200ms for creature search with encounter constraints
    - <500ms for complete encounter generation
    - Cache-friendly for repeated constraint variations
    """

    def __init__(self, omnidexer: Omnidexer):
        """Initialize encounter collector.

        Args:
            omnidexer: Content indexing service
        """
        super().__init__(omnidexer)

    def search_creatures_for_encounter(
        self,
        constraints: EncounterConstraints,
        xp_budget: XP | None = None,
        environmental_mods: EnvironmentalModifiers | None = None,
    ) -> CreatureCollectionResult:
        """Search creatures optimized for encounter building.

        Applies encounter-specific constraints and scoring to find creatures
        suitable for encounter generation within performance targets.

        Args:
            constraints: Encounter-specific creature constraints
            xp_budget: Optional XP budget for pre-filtering
            environmental_mods: Environmental modifiers for scoring

        Returns:
            Collection results with encounter suitability scoring
        """
        # Validate encounter constraints
        constraints.validate_for_encounter()

        # Start with base creature collection
        base_result = self.collect_creatures(constraints)

        if not base_result.creatures:
            logger.info("No creatures found matching base constraints")
            return base_result

        # Apply encounter-specific filters
        encounter_creatures = []

        for creature in base_result.creatures:
            # Apply encounter-specific constraints
            if not self._meets_encounter_constraints(creature, constraints):
                continue

            # Apply XP budget filtering if specified
            if xp_budget is not None:
                creature_xp = XP(EncounterBudgetCalculator._get_creature_xp(creature))
                if creature_xp > xp_budget:
                    continue  # Skip creatures that exceed budget

            # Calculate environmental suitability
            if environmental_mods is not None:
                self._calculate_environmental_suitability(creature, environmental_mods)

            # Add creature with encounter metadata
            encounter_creatures.append(creature)

        # Create enhanced result
        enhanced_result = CreatureCollectionResult()
        for creature in encounter_creatures:
            source_abbrev = None
            if hasattr(creature.source, "abbreviation"):
                source_abbrev = creature.source.abbreviation
            enhanced_result.add_creature(creature, source_abbrev)

        # Copy over unresolved names and suggestions
        enhanced_result.unresolved_names = base_result.unresolved_names
        enhanced_result.suggestions = base_result.suggestions

        logger.info(
            f"Encounter creature search: {len(encounter_creatures)} creatures "
            f"found matching encounter constraints (from {len(base_result.creatures)} base matches)"
        )

        return enhanced_result

    def generate_balanced_encounter(
        self,
        party: PartyComposition,
        target_difficulty: str,
        constraints: EncounterConstraints,
        environmental_mods: EnvironmentalModifiers | None = None,
    ) -> EncounterGenerationResult:
        """Generate a balanced encounter for the given party and constraints.

        Uses sophisticated algorithms to create encounters that match the target
        difficulty while respecting constraints and environmental factors.

        Args:
            party: Party composition for encounter balancing
            target_difficulty: Target difficulty (easy/medium/hard/deadly)
            constraints: Encounter generation constraints
            environmental_mods: Optional environmental modifiers

        Returns:
            Complete encounter with balance analysis

        Raises:
            ValueError: If encounter generation fails
        """
        import time
        import uuid

        start_time = time.perf_counter()
        encounter_id = EncounterId(str(uuid.uuid4()))

        # Calculate target XP budget
        budget = EncounterBudgetCalculator.calculate_encounter_budget(
            party, target_difficulty
        )
        target_xp = budget.adjusted_xp_budget

        logger.info(
            f"Generating {target_difficulty} encounter for {party.size} level-{party.level} "
            f"characters, target XP: {target_xp}"
        )

        # Get candidate creatures
        candidate_result = self.search_creatures_for_encounter(
            constraints,
            xp_budget=XP(int(target_xp * 1.5)),  # Allow higher CR creatures
            environmental_mods=environmental_mods,
        )

        if not candidate_result.creatures:
            raise ValueError("No creatures found matching encounter constraints")

        # Generate encounter combinations
        encounter_creatures = self._generate_encounter_combinations(
            candidate_result.creatures, target_xp, constraints, environmental_mods
        )

        if not encounter_creatures:
            raise ValueError(
                f"Could not generate encounter matching {target_difficulty} difficulty"
            )

        # Calculate encounter metrics
        base_xp, adjusted_xp = (
            EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
                [ec.creature for ec in encounter_creatures for _ in range(ec.quantity)]
            )
        )

        # Analyze encounter
        tactical_analysis = self._analyze_encounter_tactics(encounter_creatures, party)
        balance_score = self._calculate_balance_score(
            encounter_creatures, target_xp, adjusted_xp
        )

        # Environmental fit
        env_fit = 1.0
        if environmental_mods:
            env_fit = sum(
                ec.environmental_suitability for ec in encounter_creatures
            ) / len(encounter_creatures)

        # Generate rebalancing suggestions
        suggestions = self._generate_rebalance_suggestions(
            encounter_creatures, adjusted_xp, target_xp, tactical_analysis
        )

        # Determine difficulty rating
        difficulty_analysis = (
            EncounterBudgetCalculator.calculate_encounter_difficulty_rating(
                [ec.creature for ec in encounter_creatures for _ in range(ec.quantity)],
                party,
            )
        )

        generation_time = (time.perf_counter() - start_time) * 1000

        result = EncounterGenerationResult(
            encounter_id=encounter_id,
            creatures=encounter_creatures,
            total_base_xp=base_xp,
            total_adjusted_xp=adjusted_xp,
            difficulty_rating=difficulty_analysis["difficulty"],
            balance_score=balance_score,
            tactical_analysis=tactical_analysis,
            environmental_fit=env_fit,
            rebalance_suggestions=suggestions,
            generation_time_ms=generation_time,
        )

        logger.info(
            f"Generated encounter {encounter_id[:8]} in {generation_time:.1f}ms: "
            f"{result.creature_count} creatures, {adjusted_xp} XP, {result.difficulty_rating}"
        )

        return result

    def rebalance_encounter(
        self,
        current_creatures: list[EncounterCreature],
        target_difficulty: str,
        party: PartyComposition,
        constraints: EncounterConstraints | None = None,
    ) -> EncounterGenerationResult:
        """Rebalance an existing encounter to match target difficulty.

        Args:
            current_creatures: Current encounter creatures
            target_difficulty: Desired difficulty level
            party: Party composition
            constraints: Optional constraints for rebalancing

        Returns:
            Rebalanced encounter
        """
        import time
        import uuid

        start_time = time.perf_counter()
        encounter_id = EncounterId(str(uuid.uuid4()))

        # Calculate current and target XP
        current_creatures_list = [
            ec.creature for ec in current_creatures for _ in range(ec.quantity)
        ]
        _, current_xp = EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
            current_creatures_list
        )

        budget = EncounterBudgetCalculator.calculate_encounter_budget(
            party, target_difficulty
        )
        target_xp = budget.adjusted_xp_budget

        logger.info(
            f"Rebalancing encounter: {current_xp} → {target_xp} XP ({target_difficulty})"
        )

        # Determine rebalancing strategy
        xp_ratio = float(target_xp) / float(current_xp) if current_xp > 0 else 1.0

        rebalanced_creatures = []

        if 0.8 <= xp_ratio <= 1.2:
            # Small adjustment - modify quantities
            rebalanced_creatures = self._adjust_creature_quantities(
                current_creatures, xp_ratio
            )
        elif xp_ratio < 0.8:
            # Too difficult - remove creatures or reduce quantities
            rebalanced_creatures = self._reduce_encounter_difficulty(
                current_creatures, target_xp
            )
        else:
            # Too easy - add creatures or increase quantities
            rebalanced_creatures = self._increase_encounter_difficulty(
                current_creatures, target_xp, constraints
            )

        # Recalculate metrics
        rebalanced_creatures_list = [
            ec.creature for ec in rebalanced_creatures for _ in range(ec.quantity)
        ]
        base_xp, adjusted_xp = (
            EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
                rebalanced_creatures_list
            )
        )

        # Analyze rebalanced encounter
        tactical_analysis = self._analyze_encounter_tactics(rebalanced_creatures, party)
        balance_score = self._calculate_balance_score(
            rebalanced_creatures, target_xp, adjusted_xp
        )

        suggestions = self._generate_rebalance_suggestions(
            rebalanced_creatures, adjusted_xp, target_xp, tactical_analysis
        )

        difficulty_analysis = (
            EncounterBudgetCalculator.calculate_encounter_difficulty_rating(
                rebalanced_creatures_list, party
            )
        )

        generation_time = (time.perf_counter() - start_time) * 1000

        return EncounterGenerationResult(
            encounter_id=encounter_id,
            creatures=rebalanced_creatures,
            total_base_xp=base_xp,
            total_adjusted_xp=adjusted_xp,
            difficulty_rating=difficulty_analysis["difficulty"],
            balance_score=balance_score,
            tactical_analysis=tactical_analysis,
            environmental_fit=1.0,  # Maintain existing environmental fit
            rebalance_suggestions=suggestions,
            generation_time_ms=generation_time,
        )

    def _meets_encounter_constraints(
        self, creature: Creature, constraints: EncounterConstraints
    ) -> bool:
        """Check if creature meets encounter-specific constraints.

        Args:
            creature: Creature to validate
            constraints: Encounter constraints to apply

        Returns:
            True if creature meets encounter constraints
        """
        # Check legendary actions constraint
        if constraints.no_legendary and bool(getattr(creature, "legendary", None)):
            return False

        # Check lair actions (would need to parse creature abilities)
        if constraints.no_lair_actions:
            # This would require parsing creature traits/abilities
            # For now, assume no creatures have lair actions unless explicitly marked
            pass

        # Check XP constraints
        creature_xp = XP(EncounterBudgetCalculator._get_creature_xp(creature))

        if (
            constraints.min_xp_per_creature
            and creature_xp < constraints.min_xp_per_creature
        ):
            return False

        if (
            constraints.max_xp_per_creature
            and creature_xp > constraints.max_xp_per_creature
        ):
            return False

        # Check thematic constraints
        if constraints.encounter_theme:
            if not self._matches_theme(creature, constraints.encounter_theme):
                return False

        return True

    def _calculate_environmental_suitability(
        self, creature: Creature, environmental_mods: EnvironmentalModifiers
    ) -> float:
        """Calculate creature suitability for given environment.

        Args:
            creature: Creature to evaluate
            environmental_mods: Environmental context

        Returns:
            Suitability score (0.0-2.0)
        """
        # Extract creature tags/type for evaluation
        creature_tags = []
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                creature_tags.append(type_data.get("type", ""))
                tags = type_data.get("tags", [])
                if isinstance(tags, list):
                    creature_tags.extend(tags)
            elif isinstance(type_data, str):
                creature_tags.append(type_data)

        return environmental_mods.get_creature_suitability(creature_tags)

    def _generate_encounter_combinations(
        self,
        candidates: list[Creature],
        target_xp: XP,
        constraints: EncounterConstraints,
        environmental_mods: EnvironmentalModifiers | None,
    ) -> list[EncounterCreature]:
        """Generate optimal creature combinations for encounter.

        Uses a hybrid approach combining greedy algorithms with constraint
        satisfaction to generate balanced encounters.

        Args:
            candidates: Available creatures
            target_xp: Target encounter XP
            constraints: Generation constraints
            environmental_mods: Environmental context

        Returns:
            List of encounter creatures with quantities
        """
        # Sort candidates by XP efficiency and environmental fit
        scored_candidates = []
        for creature in candidates:
            creature_xp = EncounterBudgetCalculator._get_creature_xp(creature)
            env_score = 1.0
            if environmental_mods:
                env_score = self._calculate_environmental_suitability(
                    creature, environmental_mods
                )

            # Combined score: XP efficiency + environmental fit
            score = creature_xp * env_score
            scored_candidates.append((creature, creature_xp, env_score, score))

        scored_candidates.sort(key=lambda x: x[3], reverse=True)

        # Try different encounter patterns
        patterns = [
            self._try_single_creature_encounter,
            self._try_pair_encounter,
            self._try_group_encounter,
            self._try_mixed_encounter,
        ]

        best_encounter = []
        best_score = 0.0

        for pattern in patterns:
            try:
                encounter = pattern(scored_candidates, target_xp, constraints)
                if encounter:
                    # Calculate total XP with multipliers
                    creatures_list = [
                        ec.creature for ec in encounter for _ in range(ec.quantity)
                    ]
                    _, adjusted_xp = (
                        EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
                            creatures_list
                        )
                    )

                    # Score based on XP accuracy and constraint satisfaction
                    xp_accuracy = 1.0 - abs(
                        float(adjusted_xp) - float(target_xp)
                    ) / float(target_xp)
                    xp_accuracy = max(0.0, xp_accuracy)

                    if xp_accuracy > best_score:
                        best_encounter = encounter
                        best_score = xp_accuracy

                        # Early exit if we found a very good match
                        if xp_accuracy > 0.9:
                            break

            except Exception as e:
                logger.debug(f"Encounter pattern failed: {e}")
                continue

        return best_encounter

    def _try_single_creature_encounter(
        self,
        candidates: list[tuple[Creature, int, float, float]],
        target_xp: XP,
        constraints: EncounterConstraints,
    ) -> list[EncounterCreature]:
        """Try to create single creature encounter."""
        if not constraints.allow_single_powerful:
            return []

        # Find creature with XP closest to target (accounting for no multiplier)
        best_creature = None
        best_xp_diff = float("inf")
        best_env_score = 0.0

        for creature, creature_xp, env_score, _ in candidates:
            xp_diff = abs(creature_xp - int(target_xp))
            if xp_diff < best_xp_diff and creature_xp <= int(target_xp * 1.2):
                best_creature = creature
                best_xp_diff = xp_diff
                best_env_score = env_score

        if best_creature:
            return [
                EncounterCreature(
                    creature=best_creature,
                    quantity=1,
                    tactical_role="boss" if constraints.require_boss else "combatant",
                    environmental_suitability=best_env_score,
                )
            ]

        return []

    def _try_pair_encounter(
        self,
        candidates: list[tuple[Creature, int, float, float]],
        target_xp: XP,
        constraints: EncounterConstraints,
    ) -> list[EncounterCreature]:
        """Try to create two-creature encounter."""
        # Target XP for each creature (with 1.5x multiplier)
        single_target = int(target_xp / 1.5)

        for i, (creature1, xp1, env1, _) in enumerate(candidates):
            if xp1 > single_target * 1.2:
                continue

            for creature2, xp2, env2, _ in candidates[i:]:  # Avoid duplicates
                total_adjusted_xp = int((xp1 + xp2) * 1.5)

                if 0.8 * target_xp <= total_adjusted_xp <= 1.2 * target_xp:
                    return [
                        EncounterCreature(
                            creature=creature1,
                            quantity=1,
                            tactical_role="combatant",
                            environmental_suitability=env1,
                        ),
                        EncounterCreature(
                            creature=creature2,
                            quantity=1,
                            tactical_role="combatant",
                            environmental_suitability=env2,
                        ),
                    ]

        return []

    def _try_group_encounter(
        self,
        candidates: list[tuple[Creature, int, float, float]],
        target_xp: XP,
        constraints: EncounterConstraints,
    ) -> list[EncounterCreature]:
        """Try to create group encounter (3-6 creatures)."""
        if constraints.prefer_multiple_weaker:
            # Prefer many weaker creatures
            target_creature_xp = int(
                target_xp / 8
            )  # Assume 4 creatures with 2x multiplier
        else:
            target_creature_xp = int(target_xp / 4)  # More moderate approach

        suitable_creatures = [
            (creature, xp, env, score)
            for creature, xp, env, score in candidates
            if xp <= target_creature_xp * 2
        ]

        if not suitable_creatures:
            return []

        # Try different group sizes
        for group_size in [3, 4, 5, 6]:
            if constraints.max_creatures and group_size > constraints.max_creatures:
                continue

            multiplier = EncounterBudgetCalculator._get_encounter_multiplier(group_size)
            per_creature_target = int(target_xp / (group_size * multiplier))

            # Find creature closest to per-creature target
            best_creature = min(
                suitable_creatures, key=lambda x: abs(x[1] - per_creature_target)
            )

            creature, creature_xp, env_score, _ = best_creature
            total_adjusted_xp = int(creature_xp * group_size * multiplier)

            if 0.8 * target_xp <= total_adjusted_xp <= 1.2 * target_xp:
                return [
                    EncounterCreature(
                        creature=creature,
                        quantity=group_size,
                        tactical_role="minion"
                        if constraints.require_minions
                        else "combatant",
                        environmental_suitability=env_score,
                    )
                ]

        return []

    def _try_mixed_encounter(
        self,
        candidates: list[tuple[Creature, int, float, float]],
        target_xp: XP,
        constraints: EncounterConstraints,
    ) -> list[EncounterCreature]:
        """Try to create mixed encounter (different creature types)."""
        if not constraints.mixed_creature_types:
            return []

        # Simple mixed encounter: 1 stronger + 2-3 weaker
        boss_target = int(target_xp * 0.6)  # Boss takes 60% of budget
        minion_target = int((target_xp * 0.4) / 3)  # 3 minions split remaining 40%

        boss_creature = None
        for creature, xp, env, _ in candidates:
            if 0.8 * boss_target <= xp <= 1.2 * boss_target:
                boss_creature = (creature, env)
                break

        minion_creature = None
        for creature, xp, env, _ in candidates:
            if 0.8 * minion_target <= xp <= 1.2 * minion_target:
                minion_creature = (creature, env)
                break

        if boss_creature and minion_creature:
            # Calculate actual XP with multipliers (1 boss + 3 minions = 4 creatures = 2x multiplier)
            boss_xp = EncounterBudgetCalculator._get_creature_xp(boss_creature[0])
            minion_xp = EncounterBudgetCalculator._get_creature_xp(minion_creature[0])
            total_xp = int((boss_xp + minion_xp * 3) * 2.0)

            if 0.8 * target_xp <= total_xp <= 1.2 * target_xp:
                return [
                    EncounterCreature(
                        creature=boss_creature[0],
                        quantity=1,
                        tactical_role="boss",
                        environmental_suitability=boss_creature[1],
                    ),
                    EncounterCreature(
                        creature=minion_creature[0],
                        quantity=3,
                        tactical_role="minion",
                        environmental_suitability=minion_creature[1],
                    ),
                ]

        return []

    def _analyze_encounter_tactics(
        self, encounter_creatures: list[EncounterCreature], party: PartyComposition
    ) -> dict[str, Any]:
        """Analyze tactical aspects of the encounter.

        Args:
            encounter_creatures: Creatures in the encounter
            party: Party composition for context

        Returns:
            Dictionary with tactical analysis
        """
        total_creatures = sum(ec.quantity for ec in encounter_creatures)
        unique_types = len(encounter_creatures)

        # Analyze creature roles
        roles: dict[str, int] = {}
        for ec in encounter_creatures:
            roles[ec.tactical_role] = roles.get(ec.tactical_role, 0) + ec.quantity

        # Analyze capabilities
        has_spellcasters = any(
            self._creature_has_spellcasting(ec.creature) for ec in encounter_creatures
        )
        has_ranged = any(
            self._creature_has_ranged_attacks(ec.creature) for ec in encounter_creatures
        )
        has_aoe = any(
            self._creature_has_aoe_abilities(ec.creature) for ec in encounter_creatures
        )

        # Action economy analysis
        party_actions = party.size  # Assume 1 action per party member
        enemy_actions = total_creatures  # 1 action per creature
        action_ratio = enemy_actions / party_actions if party_actions > 0 else 1.0

        return {
            "total_creatures": total_creatures,
            "unique_creature_types": unique_types,
            "creature_roles": roles,
            "capabilities": {
                "has_spellcasters": has_spellcasters,
                "has_ranged_attackers": has_ranged,
                "has_aoe_abilities": has_aoe,
            },
            "action_economy": {
                "party_actions": party_actions,
                "enemy_actions": enemy_actions,
                "action_ratio": round(action_ratio, 2),
                "balance_assessment": (
                    "enemy_advantage"
                    if action_ratio > 1.5
                    else "party_advantage"
                    if action_ratio < 0.7
                    else "balanced"
                ),
            },
        }

    def _calculate_balance_score(
        self, encounter_creatures: list[EncounterCreature], target_xp: XP, actual_xp: XP
    ) -> float:
        """Calculate encounter balance score (0.0-1.0).

        Args:
            encounter_creatures: Creatures in encounter
            target_xp: Target XP budget
            actual_xp: Actual encounter XP

        Returns:
            Balance score where 1.0 is perfectly balanced
        """
        # XP accuracy component
        xp_accuracy = 1.0 - abs(float(actual_xp) - float(target_xp)) / float(target_xp)
        xp_accuracy = max(0.0, min(1.0, xp_accuracy))

        # Creature diversity component
        unique_creatures = len(encounter_creatures)
        total_creatures = sum(ec.quantity for ec in encounter_creatures)
        diversity_score = min(1.0, unique_creatures / max(1, total_creatures // 2))

        # Environmental fit component
        avg_env_fit = sum(
            ec.environmental_suitability for ec in encounter_creatures
        ) / len(encounter_creatures)
        env_score = min(1.0, avg_env_fit)

        # Weighted combination
        balance_score = (
            xp_accuracy * 0.5  # XP accuracy is most important
            + diversity_score * 0.3  # Creature diversity adds interest
            + env_score * 0.2  # Environmental fit for immersion
        )

        return round(balance_score, 3)

    def _generate_rebalance_suggestions(
        self,
        encounter_creatures: list[EncounterCreature],
        actual_xp: XP,
        target_xp: XP,
        tactical_analysis: dict[str, Any],
    ) -> list[str]:
        """Generate suggestions for encounter rebalancing.

        Args:
            encounter_creatures: Current encounter creatures
            actual_xp: Current encounter XP
            target_xp: Target XP budget
            tactical_analysis: Tactical analysis results

        Returns:
            List of rebalancing suggestions
        """
        suggestions = []

        xp_ratio = float(actual_xp) / float(target_xp)

        if xp_ratio < 0.8:
            suggestions.append(
                f"Encounter is under budget by {int((1 - xp_ratio) * 100)}% - consider adding creatures"
            )
        elif xp_ratio > 1.2:
            suggestions.append(
                f"Encounter is over budget by {int((xp_ratio - 1) * 100)}% - consider reducing creatures"
            )

        # Action economy suggestions
        action_ratio = tactical_analysis["action_economy"]["action_ratio"]
        if action_ratio > 2.0:
            suggestions.append(
                "High enemy action economy - consider fewer, stronger creatures"
            )
        elif action_ratio < 0.5:
            suggestions.append(
                "Low enemy action economy - consider more creatures for challenge"
            )

        # Tactical variety suggestions
        capabilities = tactical_analysis["capabilities"]
        if (
            not capabilities["has_spellcasters"]
            and not capabilities["has_ranged_attackers"]
        ):
            suggestions.append(
                "Consider adding ranged attackers or spellcasters for tactical variety"
            )

        if (
            not capabilities["has_aoe_abilities"]
            and tactical_analysis["total_creatures"] <= 2
        ):
            suggestions.append(
                "Single-target encounter - consider creatures with area abilities"
            )

        # Creature quantity suggestions
        total_creatures = tactical_analysis["total_creatures"]
        if total_creatures == 1:
            suggestions.append(
                "Single creature encounter - ensure it has legendary/lair actions"
            )
        elif total_creatures > 8:
            suggestions.append("Large encounter group - may slow combat significantly")

        return suggestions

    # Helper methods for creature analysis

    def _matches_theme(self, creature: Creature, theme: str) -> bool:
        """Check if creature matches encounter theme."""
        theme = theme.lower()

        # Extract creature type information
        creature_type = ""
        if hasattr(creature, "type"):
            type_data = creature.type
            if isinstance(type_data, dict):
                creature_type = type_data.get("type", "").lower()
            else:
                creature_type = str(type_data).lower()

        # Theme matching logic
        theme_matches = {
            "undead": ["undead"],
            "elemental": ["elemental"],
            "fiend": ["fiend", "devil", "demon"],
            "fey": ["fey"],
            "dragon": ["dragon"],
            "giant": ["giant"],
            "beast": ["beast"],
            "humanoid": ["humanoid"],
            "celestial": ["celestial"],
            "aberration": ["aberration"],
            "construct": ["construct"],
            "monstrosity": ["monstrosity"],
            "ooze": ["ooze"],
            "plant": ["plant"],
        }

        if theme in theme_matches:
            return creature_type in theme_matches[theme]

        return True  # Unknown theme, allow all creatures

    def _creature_has_ranged_attacks(self, creature: Creature) -> bool:
        """Check if creature has ranged attack capabilities."""
        # This would require parsing creature actions
        # For now, use heuristics based on creature type
        if hasattr(creature, "action") and creature.action:
            for action in creature.action:
                if isinstance(action, dict) and "name" in action:
                    action_name = str(action["name"]).lower()
                    if any(
                        word in action_name
                        for word in ["bow", "crossbow", "javelin", "dart", "sling"]
                    ):
                        return True

        return False

    def _creature_has_aoe_abilities(self, creature: Creature) -> bool:
        """Check if creature has area-of-effect abilities."""
        # Check for breath weapons, spellcasting, or special abilities
        if self._creature_has_spellcasting(creature):
            return True  # Assume spellcasters have AoE options

        if hasattr(creature, "action") and creature.action:
            for action in creature.action:
                if isinstance(action, dict) and "name" in action:
                    action_name = str(action["name"]).lower()
                    if any(
                        word in action_name
                        for word in ["breath", "roar", "stomp", "slam"]
                    ):
                        return True

        return False

    def _adjust_creature_quantities(
        self, creatures: list[EncounterCreature], ratio: float
    ) -> list[EncounterCreature]:
        """Adjust creature quantities by given ratio."""
        adjusted = []
        for ec in creatures:
            new_quantity = max(1, int(ec.quantity * ratio))
            adjusted.append(
                EncounterCreature(
                    creature=ec.creature,
                    quantity=new_quantity,
                    tactical_role=ec.tactical_role,
                    environmental_suitability=ec.environmental_suitability,
                )
            )
        return adjusted

    def _reduce_encounter_difficulty(
        self, creatures: list[EncounterCreature], target_xp: XP
    ) -> list[EncounterCreature]:
        """Reduce encounter difficulty to match target XP."""
        # Remove creatures starting with highest XP
        sorted_creatures = sorted(
            creatures,
            key=lambda ec: EncounterBudgetCalculator._get_creature_xp(ec.creature),
            reverse=True,
        )

        reduced: list[EncounterCreature] = []
        XP(0)

        for ec in sorted_creatures:
            XP(EncounterBudgetCalculator._get_creature_xp(ec.creature))

            # Try adding this creature type
            for quantity in range(ec.quantity, 0, -1):
                test_creatures = reduced + [
                    EncounterCreature(
                        creature=ec.creature,
                        quantity=quantity,
                        tactical_role=ec.tactical_role,
                        environmental_suitability=ec.environmental_suitability,
                    )
                ]

                test_creatures_list = [
                    tc.creature for tc in test_creatures for _ in range(tc.quantity)
                ]
                _, test_xp = (
                    EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
                        test_creatures_list
                    )
                )

                if test_xp <= target_xp * 1.1:  # Allow 10% over budget
                    reduced.append(
                        EncounterCreature(
                            creature=ec.creature,
                            quantity=quantity,
                            tactical_role=ec.tactical_role,
                            environmental_suitability=ec.environmental_suitability,
                        )
                    )
                    break

        return reduced or [creatures[0]]  # Return at least one creature

    def _increase_encounter_difficulty(
        self,
        creatures: list[EncounterCreature],
        target_xp: XP,
        constraints: EncounterConstraints | None,
    ) -> list[EncounterCreature]:
        """Increase encounter difficulty to match target XP."""
        # Start with current creatures
        increased = list(creatures)

        # Calculate current XP
        current_creatures_list = [
            ec.creature for ec in increased for _ in range(ec.quantity)
        ]
        _, current_xp = EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
            current_creatures_list
        )

        # Try increasing quantities first
        for ec in increased:
            if constraints and constraints.max_creatures:
                total_creatures = sum(ic.quantity for ic in increased)
                if total_creatures >= constraints.max_creatures:
                    break

            # Try adding one more of this creature type
            test_ec = EncounterCreature(
                creature=ec.creature,
                quantity=ec.quantity + 1,
                tactical_role=ec.tactical_role,
                environmental_suitability=ec.environmental_suitability,
            )

            test_increased = [
                test_ec if ic.creature == ec.creature else ic for ic in increased
            ]
            test_creatures_list = [
                tc.creature for tc in test_increased for _ in range(tc.quantity)
            ]
            _, test_xp = (
                EncounterBudgetCalculator.calculate_creature_xp_with_multiplier(
                    test_creatures_list
                )
            )

            if test_xp >= target_xp * 0.9:  # Within 10% of target
                ec.quantity += 1
                break

        return increased
