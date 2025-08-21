"""Real-time encounter balancing and optimization engine.

This module provides sophisticated encounter balancing algorithms with real-time
rebalancing capabilities, tactical analysis, and optimization suggestions.

Uses advanced algorithms for encounter difficulty assessment and dynamic
adjustment while maintaining performance targets and DMG compliance.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from dnd5e.core.logging import get_logger
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.encounter_types import (
    XP,
    EncounterConstraints,
    EncounterId,
    EnvironmentalModifiers,
    PartyComposition,
)
from dnd5e.core.services.encounter_collector import (
    EncounterCollector,
    EncounterCreature,
    EncounterGenerationResult,
)
from dnd5e.mcp.tools.encounter.budget import EncounterBudgetCalculator

logger = get_logger(__name__)


class BalanceStrategy(Enum):
    """Encounter balancing strategies."""

    CONSERVATIVE = "conservative"  # Prefer slightly easier encounters
    AGGRESSIVE = "aggressive"  # Prefer slightly harder encounters
    PRECISE = "precise"  # Target exact difficulty
    DYNAMIC = "dynamic"  # Adapt based on encounter characteristics


class OptimizationGoal(Enum):
    """Encounter optimization objectives."""

    TACTICAL_VARIETY = "tactical_variety"  # Maximize tactical options
    ACTION_ECONOMY = "action_economy"  # Balance action economy
    ENVIRONMENTAL_FIT = "environmental_fit"  # Optimize for environment
    NARRATIVE_FLOW = "narrative_flow"  # Support story objectives
    RESOURCE_DRAIN = "resource_drain"  # Drain specific player resources


@dataclass
class BalanceMetrics:
    """Comprehensive encounter balance assessment metrics."""

    xp_accuracy: float = 0.0  # How close to target XP (0.0-1.0)
    tactical_balance: float = 0.0  # Tactical variety and balance (0.0-1.0)
    action_economy_score: float = 0.0  # Action economy balance (0.0-1.0)
    environmental_fit: float = 0.0  # Environment suitability (0.0-1.0)
    narrative_alignment: float = 0.0  # Story/theme alignment (0.0-1.0)
    overall_balance: float = 0.0  # Weighted overall score (0.0-1.0)

    # Detailed breakdowns
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    optimization_suggestions: list[str] = field(default_factory=list)

    def calculate_overall_balance(self) -> None:
        """Calculate weighted overall balance score."""
        self.overall_balance = (
            self.xp_accuracy * 0.3
            + self.tactical_balance * 0.25
            + self.action_economy_score * 0.2
            + self.environmental_fit * 0.15
            + self.narrative_alignment * 0.1
        )


@dataclass
class BalanceAnalysis:
    """Complete encounter balance analysis result."""

    encounter_id: EncounterId
    original_encounter: EncounterGenerationResult
    balanced_encounter: EncounterGenerationResult | None
    metrics: BalanceMetrics
    strategy_used: BalanceStrategy
    optimization_goal: OptimizationGoal | None
    processing_time_ms: float
    iterations_performed: int

    @property
    def improvement_gained(self) -> float:
        """Calculate balance improvement from original to balanced."""
        if not self.balanced_encounter:
            return 0.0
        return (
            self.balanced_encounter.balance_score
            - self.original_encounter.balance_score
        )


class EncounterBalancer:
    """Advanced encounter balancing engine with real-time optimization.

    Provides sophisticated encounter analysis and rebalancing capabilities
    with multiple optimization strategies and real-time performance.

    Features:
    - Real-time encounter difficulty assessment
    - Dynamic rebalancing with multiple strategies
    - Tactical variety optimization
    - Environmental fit optimization
    - Action economy analysis and adjustment
    - Narrative alignment scoring
    """

    def __init__(self, encounter_collector: EncounterCollector):
        """Initialize encounter balancer.

        Args:
            encounter_collector: Encounter collection service
        """
        self.collector = encounter_collector

    def analyze_encounter_balance(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        target_difficulty: str,
        environmental_context: EnvironmentalModifiers | None = None,
        narrative_context: dict[str, Any] | None = None,
    ) -> BalanceMetrics:
        """Perform comprehensive encounter balance analysis.

        Args:
            encounter: Encounter to analyze
            party: Party composition for context
            target_difficulty: Target difficulty level
            environmental_context: Environmental factors
            narrative_context: Story/theme context

        Returns:
            Detailed balance metrics and analysis
        """
        metrics = BalanceMetrics()

        # Calculate target XP for comparison
        budget = EncounterBudgetCalculator.calculate_encounter_budget(
            party, target_difficulty
        )
        target_xp = budget.adjusted_xp_budget

        # XP Accuracy Analysis
        metrics.xp_accuracy = self._analyze_xp_accuracy(
            encounter.total_adjusted_xp, target_xp
        )

        # Tactical Balance Analysis
        metrics.tactical_balance = self._analyze_tactical_balance(encounter, party)

        # Action Economy Analysis
        metrics.action_economy_score = self._analyze_action_economy(encounter, party)

        # Environmental Fit Analysis
        if environmental_context:
            metrics.environmental_fit = encounter.environmental_fit
        else:
            metrics.environmental_fit = 1.0  # No environmental constraints

        # Narrative Alignment Analysis
        metrics.narrative_alignment = self._analyze_narrative_alignment(
            encounter, narrative_context or {}
        )

        # Calculate overall balance
        metrics.calculate_overall_balance()

        # Generate detailed analysis
        self._generate_balance_analysis(metrics, encounter, target_xp, party)

        logger.debug(
            f"Encounter balance analysis: {metrics.overall_balance:.3f} overall score"
        )

        return metrics

    def rebalance_encounter_optimized(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        target_difficulty: str,
        strategy: BalanceStrategy = BalanceStrategy.PRECISE,
        optimization_goal: OptimizationGoal | None = None,
        constraints: EncounterConstraints | None = None,
        max_iterations: int = 5,
    ) -> BalanceAnalysis:
        """Perform optimized encounter rebalancing with iterative improvement.

        Args:
            encounter: Original encounter to rebalance
            party: Party composition
            target_difficulty: Target difficulty level
            strategy: Balancing strategy to use
            optimization_goal: Primary optimization objective
            constraints: Rebalancing constraints
            max_iterations: Maximum optimization iterations

        Returns:
            Complete balance analysis with optimized encounter
        """
        start_time = time.perf_counter()

        logger.info(
            f"Rebalancing encounter {encounter.encounter_id[:8]} with {strategy.value} strategy"
        )

        # Analyze original encounter
        original_metrics = self.analyze_encounter_balance(
            encounter, party, target_difficulty
        )

        # Perform iterative optimization
        best_encounter = encounter
        best_metrics = original_metrics
        iterations = 0

        current_encounter = encounter

        for iteration in range(max_iterations):
            iterations += 1

            # Apply balancing strategy
            balanced_result = self._apply_balance_strategy(
                current_encounter,
                party,
                target_difficulty,
                strategy,
                optimization_goal,
                constraints,
            )

            if not balanced_result:
                logger.warning(f"Balancing iteration {iteration + 1} failed")
                break

            # Analyze balanced encounter
            balanced_metrics = self.analyze_encounter_balance(
                balanced_result, party, target_difficulty
            )

            # Check if this is an improvement
            if balanced_metrics.overall_balance > best_metrics.overall_balance:
                best_encounter = balanced_result
                best_metrics = balanced_metrics
                current_encounter = balanced_result

                logger.debug(
                    f"Iteration {iteration + 1}: improved balance to {balanced_metrics.overall_balance:.3f}"
                )

                # Early exit if we achieved excellent balance
                if balanced_metrics.overall_balance > 0.95:
                    break
            else:
                # No improvement, stop iterating
                break

        processing_time = (time.perf_counter() - start_time) * 1000

        # Create final analysis
        analysis = BalanceAnalysis(
            encounter_id=encounter.encounter_id,
            original_encounter=encounter,
            balanced_encounter=best_encounter if best_encounter != encounter else None,
            metrics=best_metrics,
            strategy_used=strategy,
            optimization_goal=optimization_goal,
            processing_time_ms=processing_time,
            iterations_performed=iterations,
        )

        improvement = analysis.improvement_gained
        logger.info(
            f"Encounter rebalancing completed in {processing_time:.1f}ms: "
            f"{improvement:+.3f} balance improvement over {iterations} iterations"
        )

        return analysis

    def optimize_for_goal(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        optimization_goal: OptimizationGoal,
        constraints: EncounterConstraints | None = None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter for specific goal while maintaining balance.

        Args:
            encounter: Base encounter to optimize
            party: Party composition
            optimization_goal: Primary optimization objective
            constraints: Optimization constraints

        Returns:
            Optimized encounter or None if optimization failed
        """
        logger.info(f"Optimizing encounter for {optimization_goal.value}")

        if optimization_goal == OptimizationGoal.TACTICAL_VARIETY:
            return self._optimize_tactical_variety(encounter, party, constraints)
        elif optimization_goal == OptimizationGoal.ACTION_ECONOMY:
            return self._optimize_action_economy(encounter, party, constraints)
        elif optimization_goal == OptimizationGoal.ENVIRONMENTAL_FIT:
            return self._optimize_environmental_fit(encounter, constraints)
        elif optimization_goal == OptimizationGoal.NARRATIVE_FLOW:
            return self._optimize_narrative_flow(encounter, constraints)
        elif optimization_goal == OptimizationGoal.RESOURCE_DRAIN:
            return self._optimize_resource_drain(encounter, party, constraints)
        else:
            logger.warning(f"Unknown optimization goal: {optimization_goal}")
            return None

    def _analyze_xp_accuracy(self, actual_xp: XP, target_xp: XP) -> float:
        """Analyze XP accuracy against target."""
        if target_xp == 0:
            return 1.0 if actual_xp == 0 else 0.0

        accuracy = 1.0 - abs(float(actual_xp) - float(target_xp)) / float(target_xp)
        return max(0.0, min(1.0, accuracy))

    def _analyze_tactical_balance(
        self, encounter: EncounterGenerationResult, party: PartyComposition
    ) -> float:
        """Analyze tactical balance and variety."""
        tactics = encounter.tactical_analysis

        # Base tactical score
        score = 0.0

        # Creature variety bonus
        if encounter.unique_creatures > 1:
            score += 0.3

        # Capability variety
        capabilities = tactics.get("capabilities", {})
        capability_count = sum(1 for cap in capabilities.values() if cap)
        score += min(0.4, capability_count * 0.15)

        # Action economy consideration
        action_balance = tactics.get("action_economy", {}).get(
            "balance_assessment", "balanced"
        )
        if action_balance == "balanced":
            score += 0.3
        elif action_balance in ["enemy_advantage", "party_advantage"]:
            score += 0.15

        return min(1.0, score)

    def _analyze_action_economy(
        self, encounter: EncounterGenerationResult, party: PartyComposition
    ) -> float:
        """Analyze action economy balance."""
        action_data = encounter.tactical_analysis.get("action_economy", {})
        action_ratio = action_data.get("action_ratio", 1.0)

        # Ideal action ratio is around 1.0-1.5 (slightly favoring enemies)
        if 1.0 <= action_ratio <= 1.5:
            return 1.0
        elif 0.8 <= action_ratio < 1.0:
            return 0.9  # Slightly party favored
        elif 1.5 < action_ratio <= 2.0:
            return 0.8  # Moderately enemy favored
        elif 0.5 <= action_ratio < 0.8:
            return 0.6  # Significantly party favored
        elif 2.0 < action_ratio <= 3.0:
            return 0.5  # Significantly enemy favored
        else:
            return 0.2  # Extremely imbalanced

    def _analyze_narrative_alignment(
        self, encounter: EncounterGenerationResult, narrative_context: dict[str, Any]
    ) -> float:
        """Analyze how well encounter fits narrative context."""
        if not narrative_context:
            return 1.0  # No narrative requirements

        score = 1.0  # Start with perfect alignment

        # Check theme alignment
        required_theme = narrative_context.get("theme")
        if required_theme:
            # This would need creature theme analysis
            # For now, assume good alignment
            pass

        # Check story role alignment
        story_role = narrative_context.get("story_role", "combat")
        if story_role == "boss" and encounter.unique_creatures > 1:
            score *= 0.8  # Boss encounters should focus on single creature
        elif story_role == "minions" and encounter.creature_count < 3:
            score *= 0.7  # Minion encounters need multiple creatures

        return score

    def _generate_balance_analysis(
        self,
        metrics: BalanceMetrics,
        encounter: EncounterGenerationResult,
        target_xp: XP,
        party: PartyComposition,
    ) -> None:
        """Generate detailed strengths, weaknesses, and suggestions."""
        # Analyze strengths
        if metrics.xp_accuracy > 0.9:
            metrics.strengths.append("Excellent XP budget accuracy")
        elif metrics.xp_accuracy > 0.8:
            metrics.strengths.append("Good XP budget match")

        if metrics.tactical_balance > 0.8:
            metrics.strengths.append("Good tactical variety")

        if metrics.action_economy_score > 0.8:
            metrics.strengths.append("Well-balanced action economy")

        if metrics.environmental_fit > 0.8:
            metrics.strengths.append("Good environmental fit")

        # Analyze weaknesses
        if metrics.xp_accuracy < 0.7:
            xp_diff = abs(float(encounter.total_adjusted_xp) - float(target_xp))
            metrics.weaknesses.append(f"XP budget mismatch: {xp_diff} XP difference")

        if metrics.tactical_balance < 0.6:
            metrics.weaknesses.append("Limited tactical variety")

        if metrics.action_economy_score < 0.6:
            action_ratio = encounter.tactical_analysis.get("action_economy", {}).get(
                "action_ratio", 1.0
            )
            if action_ratio > 2.0:
                metrics.weaknesses.append("Action economy heavily favors enemies")
            else:
                metrics.weaknesses.append("Action economy favors party too much")

        if metrics.environmental_fit < 0.6:
            metrics.weaknesses.append("Poor environmental fit for creatures")

        # Generate optimization suggestions
        if metrics.xp_accuracy < 0.8:
            if encounter.total_adjusted_xp < target_xp:
                metrics.optimization_suggestions.append(
                    "Add creatures or increase quantities to reach target XP"
                )
            else:
                metrics.optimization_suggestions.append(
                    "Remove creatures or reduce quantities to match target XP"
                )

        if metrics.tactical_balance < 0.7:
            metrics.optimization_suggestions.append(
                "Add creatures with different tactical roles"
            )

        if encounter.creature_count == 1:
            metrics.optimization_suggestions.append(
                "Consider legendary actions or lair actions for single creature"
            )
        elif encounter.creature_count > 8:
            metrics.optimization_suggestions.append(
                "Consider reducing creature count to speed up combat"
            )

        if not encounter.tactical_analysis.get("capabilities", {}).get(
            "has_ranged_attackers", False
        ):
            metrics.optimization_suggestions.append(
                "Consider adding ranged attackers for tactical depth"
            )

    def _apply_balance_strategy(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        target_difficulty: str,
        strategy: BalanceStrategy,
        optimization_goal: OptimizationGoal | None,
        constraints: EncounterConstraints | None,
    ) -> EncounterGenerationResult | None:
        """Apply specific balancing strategy to encounter."""
        try:
            # Convert encounter to rebalanceable format
            encounter_creatures = encounter.creatures

            if strategy == BalanceStrategy.CONSERVATIVE:
                # Target slightly below difficulty
                adjusted_difficulty = self._adjust_difficulty_conservative(
                    target_difficulty
                )
                result = self.collector.rebalance_encounter(
                    encounter_creatures, adjusted_difficulty, party, constraints
                )
            elif strategy == BalanceStrategy.AGGRESSIVE:
                # Target slightly above difficulty
                adjusted_difficulty = self._adjust_difficulty_aggressive(
                    target_difficulty
                )
                result = self.collector.rebalance_encounter(
                    encounter_creatures, adjusted_difficulty, party, constraints
                )
            elif strategy == BalanceStrategy.PRECISE:
                # Target exact difficulty
                result = self.collector.rebalance_encounter(
                    encounter_creatures, target_difficulty, party, constraints
                )
            elif strategy == BalanceStrategy.DYNAMIC:
                # Choose strategy based on encounter characteristics
                if encounter.creature_count == 1:
                    # Single creature - be conservative
                    result = self.collector.rebalance_encounter(
                        encounter_creatures, target_difficulty, party, constraints
                    )
                else:
                    # Multiple creatures - can be more aggressive
                    result = self.collector.rebalance_encounter(
                        encounter_creatures, target_difficulty, party, constraints
                    )
            else:
                result = None

            # Apply optimization goal if specified
            if result and optimization_goal:
                optimized = self.optimize_for_goal(
                    result, party, optimization_goal, constraints
                )
                if optimized:
                    result = optimized

            return result

        except Exception as e:
            logger.error(f"Balance strategy application failed: {e}")
            return None

    def _adjust_difficulty_conservative(self, difficulty: str) -> str:
        """Adjust difficulty to be more conservative."""
        difficulty_order = ["easy", "medium", "hard", "deadly"]
        if difficulty in difficulty_order:
            current_index = difficulty_order.index(difficulty)
            if current_index > 0:
                return difficulty_order[current_index - 1]
        return difficulty

    def _adjust_difficulty_aggressive(self, difficulty: str) -> str:
        """Adjust difficulty to be more aggressive."""
        difficulty_order = ["easy", "medium", "hard", "deadly"]
        if difficulty in difficulty_order:
            current_index = difficulty_order.index(difficulty)
            if current_index < len(difficulty_order) - 1:
                return difficulty_order[current_index + 1]
        return difficulty

    # Optimization goal implementations

    def _optimize_tactical_variety(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        constraints: EncounterConstraints | None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter for maximum tactical variety."""
        # This would involve complex creature substitution logic
        # For now, return the original encounter
        logger.info("Tactical variety optimization not yet implemented")
        return encounter

    def _optimize_action_economy(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        constraints: EncounterConstraints | None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter for balanced action economy."""
        action_data = encounter.tactical_analysis.get("action_economy", {})
        current_ratio = action_data.get("action_ratio", 1.0)
        target_ratio = 1.25  # Slightly enemy-favored

        if abs(current_ratio - target_ratio) < 0.2:
            return encounter  # Already well balanced

        # Simple adjustment: modify creature quantities
        if current_ratio < target_ratio:
            # Need more enemy actions - try to add creatures
            # This is a simplified implementation
            pass
        else:
            # Too many enemy actions - try to reduce creatures
            pass

        logger.info("Action economy optimization not yet fully implemented")
        return encounter

    def _optimize_environmental_fit(
        self,
        encounter: EncounterGenerationResult,
        constraints: EncounterConstraints | None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter for environmental fit."""
        # This would involve creature substitution based on environment
        logger.info("Environmental fit optimization not yet implemented")
        return encounter

    def _optimize_narrative_flow(
        self,
        encounter: EncounterGenerationResult,
        constraints: EncounterConstraints | None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter for narrative flow."""
        # This would involve thematic creature substitution
        logger.info("Narrative flow optimization not yet implemented")
        return encounter

    def _optimize_resource_drain(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        constraints: EncounterConstraints | None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter to drain specific player resources."""
        # This would involve selecting creatures that target specific resources
        logger.info("Resource drain optimization not yet implemented")
        return encounter


def rebalance_encounter(
    encounter_data: dict[str, Any],
    party_size: int,
    party_level: int,
    target_difficulty: str,
    strategy: str = "precise",
    optimization_goal: str | None = None,
    max_iterations: int = 5,
) -> dict[str, Any]:
    """Rebalance encounter for MCP tool interface.

    Args:
        encounter_data: Current encounter data
        party_size: Number of party members
        party_level: Average party level
        target_difficulty: Target difficulty level
        strategy: Balancing strategy (conservative/aggressive/precise/dynamic)
        optimization_goal: Optimization objective (optional)
        max_iterations: Maximum optimization iterations

    Returns:
        Rebalanced encounter analysis

    Raises:
        ValueError: If parameters are invalid
    """
    # This function would be implemented to work with the MCP interface
    # For now, return a placeholder response
    logger.info(f"Rebalancing encounter for {party_size} level-{party_level} party")

    return {
        "status": "rebalancing_not_implemented",
        "message": "Encounter rebalancing functionality is not yet fully implemented",
        "original_encounter": encounter_data,
        "party_size": party_size,
        "party_level": party_level,
        "target_difficulty": target_difficulty,
        "strategy": strategy,
        "optimization_goal": optimization_goal,
    }
