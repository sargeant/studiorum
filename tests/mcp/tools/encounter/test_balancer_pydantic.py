"""Tests for Pydantic encounter balancer models.

Comprehensive tests validating the enhanced Pydantic implementations
with proper type safety, validation, and JSON serialization.
"""

import pytest
from pydantic import ValidationError

from studiorum.core.models.encounter_types import EncounterId
from studiorum.mcp.tools.encounter.balancer import BalanceStrategy, OptimizationGoal
from studiorum.mcp.tools.encounter.balancer_pydantic import (
    BalanceAnalysis,
    BalanceMetrics,
)


def create_test_encounter_result(
    balance_score: float = 0.75, encounter_id: str | None = None, **kwargs
):
    """Create a test EncounterGenerationResult object."""
    import uuid

    from studiorum.core.models.encounter_types import XP
    from studiorum.core.services.encounter_collector import (
        EncounterCreature,
        EncounterGenerationResult,
    )

    if encounter_id is None:
        encounter_id = f"test_encounter_{str(uuid.uuid4())[:8]}"

    # Create a simple test creature dict for the encounter
    test_creature = {
        "name": "Goblin",
        "cr": "1/4",
        "type": {"type": "humanoid"},
        "source": {"abbreviation": "MM", "page": 166},
    }

    creatures = [
        EncounterCreature(
            creature=test_creature,
            quantity=3,
            tactical_role="minion",
            xp_contribution=XP(400),
            environmental_suitability=0.8,
        )
    ]

    tactical_analysis = {
        "total_creatures": 3,
        "unique_creature_types": 2,
        "creature_roles": {"minion": 3},
        "capabilities": {
            "has_ranged_attackers": True,
            "has_spellcasters": False,
            "has_tanks": True,
        },
        "action_economy": {"action_ratio": 1.25, "balance_assessment": "balanced"},
    }

    defaults = {
        "encounter_id": EncounterId(encounter_id),
        "creatures": creatures,
        "total_base_xp": XP(400),
        "total_adjusted_xp": XP(1200),
        "difficulty_rating": "medium",
        "balance_score": balance_score,
        "tactical_analysis": tactical_analysis,
        "environmental_fit": 0.8,
        "rebalance_suggestions": ["Consider adding variety"],
        "generation_time_ms": 125.0,
    }

    return EncounterGenerationResult(**{**defaults, **kwargs})


class TestBalanceMetrics:
    """Test BalanceMetrics Pydantic implementation."""

    def test_valid_balance_metrics_creation(self):
        """Test creating valid balance metrics."""
        metrics = BalanceMetrics(
            xp_accuracy=0.95,
            tactical_balance=0.85,
            action_economy_score=0.90,
            environmental_fit=0.80,
            narrative_alignment=0.75,
            overall_balance=0.87,
            strengths=["Excellent XP balance", "Good tactical variety"],
            weaknesses=["Limited environmental fit"],
            optimization_suggestions=[
                "Add flying creatures",
                "Consider weather effects",
            ],
        )

        assert metrics.xp_accuracy == 0.95
        assert metrics.tactical_balance == 0.85
        assert metrics.action_economy_score == 0.90
        assert metrics.environmental_fit == 0.80
        assert metrics.narrative_alignment == 0.75
        assert metrics.overall_balance == 0.87
        assert len(metrics.strengths) == 2
        assert len(metrics.weaknesses) == 1
        assert len(metrics.optimization_suggestions) == 2

    def test_default_values(self):
        """Test balance metrics with default values."""
        metrics = BalanceMetrics()

        assert metrics.xp_accuracy == 0.0
        assert metrics.tactical_balance == 0.0
        assert metrics.action_economy_score == 0.0
        assert metrics.environmental_fit == 0.0
        assert metrics.narrative_alignment == 0.0
        assert metrics.overall_balance == 0.0
        assert metrics.strengths == []
        assert metrics.weaknesses == []
        assert metrics.optimization_suggestions == []

    def test_score_validation(self):
        """Test score field validation (0.0-1.0 range)."""
        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            metrics = BalanceMetrics(xp_accuracy=score)
            assert metrics.xp_accuracy == score

        # Invalid score - too low
        with pytest.raises(ValidationError) as exc_info:
            BalanceMetrics(xp_accuracy=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Invalid score - too high
        with pytest.raises(ValidationError) as exc_info:
            BalanceMetrics(tactical_balance=1.1)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_string_list_validation(self):
        """Test validation of strengths, weaknesses, and suggestions lists."""
        # Valid string lists
        metrics = BalanceMetrics(
            strengths=["Good balance", "Nice variety"],
            weaknesses=["Too easy", "Missing ranged"],
            optimization_suggestions=["Add casters", "Increase CR"],
        )
        assert len(metrics.strengths) == 2
        assert len(metrics.weaknesses) == 2
        assert len(metrics.optimization_suggestions) == 2

        # Invalid - non-string item
        with pytest.raises(ValidationError) as exc_info:
            BalanceMetrics(strengths=["Good balance", 123])
        assert "Input should be a valid string" in str(
            exc_info.value
        )  # Pydantic 2.x format

        # Invalid - empty string
        with pytest.raises(ValidationError) as exc_info:
            BalanceMetrics(weaknesses=["Poor fit", ""])
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

        # Invalid - whitespace-only string
        with pytest.raises(ValidationError) as exc_info:
            BalanceMetrics(optimization_suggestions=["Add monsters", "   "])
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_calculate_overall_balance(self):
        """Test overall balance calculation."""
        metrics = BalanceMetrics(
            xp_accuracy=0.9,  # 30% weight = 0.27
            tactical_balance=0.8,  # 25% weight = 0.20
            action_economy_score=0.7,  # 20% weight = 0.14
            environmental_fit=0.6,  # 15% weight = 0.09
            narrative_alignment=0.5,  # 10% weight = 0.05
        )

        metrics.calculate_overall_balance()

        expected = (0.9 * 0.3) + (0.8 * 0.25) + (0.7 * 0.2) + (0.6 * 0.15) + (0.5 * 0.1)
        assert abs(metrics.overall_balance - expected) < 0.001

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original = BalanceMetrics(
            xp_accuracy=0.85,
            tactical_balance=0.75,
            strengths=["Good XP balance"],
            weaknesses=["Needs more variety"],
            optimization_suggestions=["Add flying creatures"],
        )
        original.calculate_overall_balance()

        # Serialize to dict
        data = original.model_dump()
        assert isinstance(data, dict)
        assert data["xp_accuracy"] == 0.85
        assert data["tactical_balance"] == 0.75
        assert len(data["strengths"]) == 1
        assert len(data["weaknesses"]) == 1
        assert len(data["optimization_suggestions"]) == 1

        # Deserialize back
        restored = BalanceMetrics.model_validate(data)
        assert restored.xp_accuracy == original.xp_accuracy
        assert restored.tactical_balance == original.tactical_balance
        assert restored.strengths == original.strengths
        assert restored.weaknesses == original.weaknesses
        assert restored.optimization_suggestions == original.optimization_suggestions

    def test_model_config(self):
        """Test model configuration settings."""
        # Test extra fields are forbidden
        with pytest.raises(ValidationError) as exc_info:
            BalanceMetrics(invalid_field="test")
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestBalanceAnalysis:
    """Test BalanceAnalysis Pydantic implementation."""

    def test_valid_balance_analysis_creation(self):
        """Test creating valid balance analysis."""
        encounter_id = "enc_12345"
        original_encounter = create_test_encounter_result(balance_score=0.6)
        balanced_encounter = create_test_encounter_result(balance_score=0.85)
        metrics = BalanceMetrics(
            xp_accuracy=0.9, tactical_balance=0.8, overall_balance=0.85
        )

        analysis = BalanceAnalysis(
            encounter_id=encounter_id,
            original_encounter=original_encounter,
            balanced_encounter=balanced_encounter,
            metrics=metrics,
            strategy_used=BalanceStrategy.PRECISE,
            optimization_goal=OptimizationGoal.TACTICAL_VARIETY,
            processing_time_ms=125.5,
            iterations_performed=3,
        )

        assert analysis.encounter_id == encounter_id
        assert analysis.original_encounter == original_encounter
        assert analysis.balanced_encounter == balanced_encounter
        assert analysis.metrics == metrics
        assert (
            analysis.strategy_used == BalanceStrategy.PRECISE.value
        )  # Pydantic stores enum values
        assert (
            analysis.optimization_goal == OptimizationGoal.TACTICAL_VARIETY.value
        )  # Pydantic stores enum values
        assert analysis.processing_time_ms == 125.5
        assert analysis.iterations_performed == 3

    def test_optional_fields(self):
        """Test analysis with optional fields."""
        analysis = BalanceAnalysis(
            encounter_id="enc_456",
            original_encounter=create_test_encounter_result(),
            metrics=BalanceMetrics(),
            strategy_used=BalanceStrategy.CONSERVATIVE,
            processing_time_ms=50.0,
            iterations_performed=1,
        )

        assert analysis.balanced_encounter is None
        assert analysis.optimization_goal is None

    def test_improvement_gained_property(self):
        """Test improvement gained calculation."""
        original = create_test_encounter_result(balance_score=0.6)
        improved = create_test_encounter_result(balance_score=0.85)

        # Analysis with improvement
        analysis = BalanceAnalysis(
            encounter_id="test",
            original_encounter=original,
            balanced_encounter=improved,
            metrics=BalanceMetrics(),
            strategy_used=BalanceStrategy.PRECISE,
            processing_time_ms=100.0,
            iterations_performed=2,
        )

        assert analysis.improvement_gained == 0.25  # 0.85 - 0.6

        # Analysis without balanced encounter
        analysis_no_balanced = BalanceAnalysis(
            encounter_id="test",
            original_encounter=original,
            metrics=BalanceMetrics(),
            strategy_used=BalanceStrategy.PRECISE,
            processing_time_ms=100.0,
            iterations_performed=2,
        )

        assert analysis_no_balanced.improvement_gained == 0.0

    def test_processing_time_validation(self):
        """Test processing time validation."""
        base_data = {
            "encounter_id": "test",
            "original_encounter": create_test_encounter_result(),
            "metrics": BalanceMetrics(),
            "strategy_used": BalanceStrategy.PRECISE,
            "iterations_performed": 1,
        }

        # Valid processing times
        for time_ms in [0.0, 100.5, 5000.0, 59999.9]:
            analysis = BalanceAnalysis(**base_data, processing_time_ms=time_ms)
            assert analysis.processing_time_ms == time_ms

        # Invalid - negative time
        with pytest.raises(ValidationError) as exc_info:
            BalanceAnalysis(**base_data, processing_time_ms=-1.0)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

        # Invalid - too high (> 60 seconds)
        with pytest.raises(ValidationError) as exc_info:
            BalanceAnalysis(**base_data, processing_time_ms=65000.0)
        assert "unreasonably high" in str(exc_info.value)

    def test_iterations_validation(self):
        """Test iterations performed validation."""
        base_data = {
            "encounter_id": "test",
            "original_encounter": create_test_encounter_result(),
            "metrics": BalanceMetrics(),
            "strategy_used": BalanceStrategy.PRECISE,
            "processing_time_ms": 100.0,
        }

        # Valid iteration counts
        for iterations in [0, 1, 5, 100, 1000]:
            analysis = BalanceAnalysis(**base_data, iterations_performed=iterations)
            assert analysis.iterations_performed == iterations

        # Invalid - negative iterations
        with pytest.raises(ValidationError) as exc_info:
            BalanceAnalysis(**base_data, iterations_performed=-1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

        # Invalid - too many iterations
        with pytest.raises(ValidationError) as exc_info:
            BalanceAnalysis(**base_data, iterations_performed=1001)
        assert "Too many iterations performed" in str(exc_info.value)

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original = BalanceAnalysis(
            encounter_id="enc_789",
            original_encounter=create_test_encounter_result(balance_score=0.5),
            balanced_encounter=create_test_encounter_result(balance_score=0.8),
            metrics=BalanceMetrics(xp_accuracy=0.9, tactical_balance=0.7),
            strategy_used=BalanceStrategy.AGGRESSIVE,
            optimization_goal=OptimizationGoal.ACTION_ECONOMY,
            processing_time_ms=200.5,
            iterations_performed=4,
        )

        # Serialize to dict
        data = original.model_dump()
        assert isinstance(data, dict)
        assert data["encounter_id"] == "enc_789"
        assert data["strategy_used"] == "aggressive"
        assert data["optimization_goal"] == "action_economy"
        assert data["processing_time_ms"] == 200.5
        assert data["iterations_performed"] == 4
        assert "metrics" in data
        assert "original_encounter" in data
        assert "balanced_encounter" in data

        # Note: For full deserialization test, we'd need proper EncounterGenerationResult
        # Pydantic models, which aren't available in this scope

    def test_enum_serialization(self):
        """Test enum field serialization."""
        analysis = BalanceAnalysis(
            encounter_id="test",
            original_encounter=create_test_encounter_result(),
            metrics=BalanceMetrics(),
            strategy_used=BalanceStrategy.DYNAMIC,
            optimization_goal=OptimizationGoal.RESOURCE_DRAIN,
            processing_time_ms=100.0,
            iterations_performed=1,
        )

        data = analysis.model_dump()
        assert data["strategy_used"] == "dynamic"
        assert data["optimization_goal"] == "resource_drain"

    def test_model_config(self):
        """Test model configuration settings."""
        # Test extra fields are forbidden
        with pytest.raises(ValidationError) as exc_info:
            BalanceAnalysis(
                encounter_id="test",
                original_encounter=create_test_encounter_result(),
                metrics=BalanceMetrics(),
                strategy_used=BalanceStrategy.PRECISE,
                processing_time_ms=100.0,
                iterations_performed=1,
                invalid_field="test",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestBalanceMetricsIntegration:
    """Test integration scenarios for balance metrics."""

    def test_realistic_balance_scenario(self):
        """Test a realistic encounter balancing scenario."""
        # Create metrics for a moderately unbalanced encounter
        metrics = BalanceMetrics(
            xp_accuracy=0.65,  # Slightly under XP budget
            tactical_balance=0.80,  # Good variety
            action_economy_score=0.45,  # Too many enemy actions
            environmental_fit=0.90,  # Great environmental match
            narrative_alignment=0.85,  # Good story fit
            strengths=[
                "Excellent environmental integration",
                "Strong narrative coherence",
                "Good creature variety",
            ],
            weaknesses=[
                "XP budget 15% under target",
                "Action economy heavily favors enemies",
                "May overwhelm party with too many actions per round",
            ],
            optimization_suggestions=[
                "Add 1-2 additional creatures to reach XP target",
                "Replace one multi-attack creature with single-action minions",
                "Consider legendary actions for boss to balance action economy",
            ],
        )

        # Calculate overall balance
        metrics.calculate_overall_balance()

        # Should be a moderate score due to action economy issues
        assert 0.6 <= metrics.overall_balance <= 0.8

        # Should have comprehensive analysis
        assert len(metrics.strengths) >= 2
        assert len(metrics.weaknesses) >= 2
        assert len(metrics.optimization_suggestions) >= 2

    def test_perfect_balance_scenario(self):
        """Test metrics for a perfectly balanced encounter."""
        perfect_metrics = BalanceMetrics(
            xp_accuracy=1.0,
            tactical_balance=0.95,
            action_economy_score=0.90,
            environmental_fit=0.85,
            narrative_alignment=0.80,
            strengths=[
                "Perfect XP budget match",
                "Excellent tactical variety",
                "Well-balanced action economy",
                "Good environmental fit",
            ],
            weaknesses=[],  # No significant weaknesses
            optimization_suggestions=[
                "Consider adding environmental hazards for extra challenge"
            ],
        )

        perfect_metrics.calculate_overall_balance()

        # Should be very high overall score
        assert perfect_metrics.overall_balance >= 0.9
        assert len(perfect_metrics.strengths) >= 4
        assert len(perfect_metrics.weaknesses) == 0

    def test_poor_balance_scenario(self):
        """Test metrics for a poorly balanced encounter."""
        poor_metrics = BalanceMetrics(
            xp_accuracy=0.25,  # Way off target
            tactical_balance=0.30,  # Poor variety
            action_economy_score=0.20,  # Terrible action economy
            environmental_fit=0.40,  # Poor fit
            narrative_alignment=0.50,  # Mediocre story fit
            strengths=["Creatures match basic challenge rating"],
            weaknesses=[
                "XP budget 75% over target - encounter too deadly",
                "Very limited tactical options",
                "Action economy extremely imbalanced",
                "Poor environmental creature selection",
                "Single creature type reduces variety",
            ],
            optimization_suggestions=[
                "Remove 2-3 creatures to match XP budget",
                "Add creatures with different tactical roles",
                "Replace some creatures with environment-appropriate types",
                "Consider legendary actions to balance single-boss encounters",
                "Add ranged attackers for tactical depth",
            ],
        )

        poor_metrics.calculate_overall_balance()

        # Should be low overall score
        assert poor_metrics.overall_balance <= 0.4
        assert len(poor_metrics.weaknesses) >= 4
        assert len(poor_metrics.optimization_suggestions) >= 4


def test_comprehensive_analysis_workflow():
    """Test a complete analysis workflow from creation to optimization."""
    # Step 1: Create initial unbalanced encounter analysis
    initial_metrics = BalanceMetrics(
        xp_accuracy=0.55,
        tactical_balance=0.70,
        action_economy_score=0.60,
        environmental_fit=0.80,
        narrative_alignment=0.75,
    )
    initial_metrics.calculate_overall_balance()

    initial_analysis = BalanceAnalysis(
        encounter_id="workflow_test_encounter",
        original_encounter=create_test_encounter_result(balance_score=0.62),
        metrics=initial_metrics,
        strategy_used=BalanceStrategy.PRECISE,
        processing_time_ms=150.0,
        iterations_performed=0,
    )

    # Step 2: Create improved encounter after optimization
    improved_metrics = BalanceMetrics(
        xp_accuracy=0.92,  # Much better
        tactical_balance=0.85,  # Improved
        action_economy_score=0.80,  # Better
        environmental_fit=0.80,  # Same
        narrative_alignment=0.75,  # Same
    )
    improved_metrics.calculate_overall_balance()

    final_analysis = BalanceAnalysis(
        encounter_id="workflow_test_encounter",
        original_encounter=initial_analysis.original_encounter,
        balanced_encounter=create_test_encounter_result(balance_score=0.84),
        metrics=improved_metrics,
        strategy_used=BalanceStrategy.PRECISE,
        optimization_goal=OptimizationGoal.TACTICAL_VARIETY,
        processing_time_ms=425.0,
        iterations_performed=3,
    )

    # Verify improvement
    assert final_analysis.improvement_gained > 0.15  # Significant improvement
    assert final_analysis.metrics.overall_balance > initial_metrics.overall_balance
    assert final_analysis.iterations_performed > 0
    assert final_analysis.processing_time_ms > initial_analysis.processing_time_ms

    # Verify the analysis makes sense
    assert final_analysis.encounter_id == initial_analysis.encounter_id
    assert final_analysis.original_encounter == initial_analysis.original_encounter
    assert final_analysis.balanced_encounter is not None
