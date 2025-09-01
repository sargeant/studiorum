"""Tests for migration helpers between dataclass and Pydantic models.

Comprehensive tests validating the conversion utilities that maintain
API compatibility while adding Pydantic validation and serialization.
"""

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from studiorum.core.services.encounter_collector import EncounterGenerationResult
from studiorum.mcp.tools.encounter.balancer import BalanceStrategy, OptimizationGoal
from studiorum.mcp.tools.encounter.migration_helpers import (
    balance_analysis_to_dataclass,
    balance_analysis_to_pydantic,
    balance_metrics_to_dataclass,
    balance_metrics_to_pydantic,
    deserialize_balance_analysis,
    deserialize_balance_metrics,
    deserialize_environmental_profile,
    deserialize_thematic_profile,
    environmental_profile_to_dataclass,
    environmental_profile_to_pydantic,
    serialize_balance_analysis,
    serialize_balance_metrics,
    serialize_environmental_profile,
    serialize_thematic_profile,
    thematic_profile_to_dataclass,
    thematic_profile_to_pydantic,
)
from studiorum.mcp.tools.encounter.themes import EncounterTheme, EnvironmentType


def _create_simple_result(balance_score: float):
    """Create a simple test EncounterGenerationResult for testing."""
    import uuid

    from studiorum.core.models.encounter_types import XP, EncounterId
    from studiorum.core.services.encounter_collector import (
        EncounterCreature,
    )

    # Create a complete test creature dict for the encounter
    test_creature = {
        "name": "Orc",
        "cr": "1",
        "type": {"type": "humanoid"},
        "source": {"abbreviation": "MM", "page": 246},
        "size": ["M"],
        "alignment": ["L", "E"],
        "ac": [13, {"from": ["natural armor"]}],
        "hp": {"average": 15, "formula": "2d8 + 2"},
        "speed": {"walk": 30},
        "str": 16,
        "dex": 12,
        "con": 13,
        "int": 7,
        "wis": 11,
        "cha": 10,
        "languages": ["Common", "Orc"],
        "senses": ["darkvision 60 ft."],
        "passive": 10,
        "trait": [],
        "action": [],
        "environment": ["forest", "swamp", "hill"],
    }

    return EncounterGenerationResult(
        encounter_id=EncounterId(f"test_{str(uuid.uuid4())[:8]}"),
        creatures=[
            EncounterCreature(
                creature=test_creature,
                quantity=1,
                tactical_role="combatant",
                xp_contribution=XP(200),
                environmental_suitability=1.0,
            )
        ],
        total_base_xp=XP(200),
        total_adjusted_xp=XP(200),
        difficulty_rating="easy",
        balance_score=balance_score,
        tactical_analysis={"total_creatures": 1},
        environmental_fit=1.0,
        rebalance_suggestions=[],
        generation_time_ms=100.0,
    )


class TestEnvironmentalProfileConversions:
    """Test conversions between dataclass and Pydantic EnvironmentalProfile."""

    def test_dataclass_to_pydantic_basic(self):
        """Test basic dataclass to Pydantic conversion."""
        from studiorum.mcp.tools.encounter.themes import (
            EnvironmentalProfile as DataclassProfile,
        )

        # Create dataclass profile
        dataclass_profile = DataclassProfile(
            environment=EnvironmentType.FOREST,
            climate="tropical",
            terrain_difficulty="difficult",
            lighting="dim",
            weather="rain",
            visibility_range=80,
            movement_penalty=0.8,
            stealth_modifier=1,
            sound_propagation=0.9,
            creature_affinities={"beast": 1.5, "fey": 1.3},
        )

        # Convert to Pydantic
        pydantic_profile = environmental_profile_to_pydantic(dataclass_profile)

        # Verify all fields transferred correctly
        assert (
            pydantic_profile.environment == dataclass_profile.environment.value
        )  # Pydantic stores enum values
        assert pydantic_profile.climate == dataclass_profile.climate
        assert (
            pydantic_profile.terrain_difficulty == dataclass_profile.terrain_difficulty
        )
        assert pydantic_profile.lighting == dataclass_profile.lighting
        assert pydantic_profile.weather == dataclass_profile.weather
        assert pydantic_profile.visibility_range == dataclass_profile.visibility_range
        assert pydantic_profile.movement_penalty == dataclass_profile.movement_penalty
        assert pydantic_profile.stealth_modifier == dataclass_profile.stealth_modifier
        assert pydantic_profile.sound_propagation == dataclass_profile.sound_propagation
        assert (
            pydantic_profile.creature_affinities
            == dataclass_profile.creature_affinities
        )

    def test_pydantic_to_dataclass_basic(self):
        """Test basic Pydantic to dataclass conversion."""
        from studiorum.mcp.tools.encounter.themes_pydantic import (
            EnvironmentalProfile as PydanticProfile,
        )

        # Create Pydantic profile
        pydantic_profile = PydanticProfile(
            environment=EnvironmentType.SWAMP,
            climate="temperate",
            terrain_difficulty="extreme",
            lighting="dark",
            weather="fog",
            visibility_range=30,
            movement_penalty=0.6,
            stealth_modifier=-2,
            sound_propagation=1.2,
            creature_affinities={"undead": 1.8, "plant": 1.6},
        )

        # Convert to dataclass
        dataclass_profile = environmental_profile_to_dataclass(pydantic_profile)

        # Verify all fields transferred correctly
        assert (
            dataclass_profile.environment.value == pydantic_profile.environment
        )  # Dataclass has enum, Pydantic has string
        assert dataclass_profile.climate == pydantic_profile.climate
        assert (
            dataclass_profile.terrain_difficulty == pydantic_profile.terrain_difficulty
        )
        assert dataclass_profile.lighting == pydantic_profile.lighting
        assert dataclass_profile.weather == pydantic_profile.weather
        assert dataclass_profile.visibility_range == pydantic_profile.visibility_range
        assert dataclass_profile.movement_penalty == pydantic_profile.movement_penalty
        assert dataclass_profile.stealth_modifier == pydantic_profile.stealth_modifier
        assert dataclass_profile.sound_propagation == pydantic_profile.sound_propagation
        assert (
            dataclass_profile.creature_affinities
            == pydantic_profile.creature_affinities
        )

    def test_round_trip_conversion(self):
        """Test dataclass -> Pydantic -> dataclass round trip."""
        from studiorum.mcp.tools.encounter.themes import (
            EnvironmentalProfile as DataclassProfile,
        )

        # Create original dataclass
        original = DataclassProfile(
            environment=EnvironmentType.ARCTIC,
            climate="cold",
            weather="blizzard",
            visibility_range=15,
            creature_affinities={"elemental": 2.0, "giant": 1.8},
        )

        # Round trip: dataclass -> Pydantic -> dataclass
        pydantic_version = environmental_profile_to_pydantic(original)
        restored = environmental_profile_to_dataclass(pydantic_version)

        # Should be identical
        assert restored.environment == original.environment
        assert restored.climate == original.climate
        assert restored.weather == original.weather
        assert restored.visibility_range == original.visibility_range
        assert restored.creature_affinities == original.creature_affinities

    def test_conversion_with_defaults(self):
        """Test conversion with default values."""
        from studiorum.mcp.tools.encounter.themes import (
            EnvironmentalProfile as DataclassProfile,
        )

        # Create minimal dataclass profile
        original = DataclassProfile(environment=EnvironmentType.DESERT)

        # Convert to Pydantic and back
        pydantic_version = environmental_profile_to_pydantic(original)
        restored = environmental_profile_to_dataclass(pydantic_version)

        # Defaults should be preserved
        assert restored.climate == "temperate"
        assert restored.terrain_difficulty == "normal"
        assert restored.lighting == "normal"
        assert restored.weather == "clear"
        assert restored.visibility_range == 120

    def test_conversion_validation_errors(self):
        """Test that invalid dataclass data fails Pydantic validation."""
        from studiorum.mcp.tools.encounter.themes import (
            EnvironmentalProfile as DataclassProfile,
        )

        # Create dataclass with invalid data (bypassing dataclass validation)
        invalid_profile = DataclassProfile(environment=EnvironmentType.FOREST)
        invalid_profile.visibility_range = -50  # Invalid value

        # Should raise ValidationError when converting to Pydantic
        with pytest.raises(ValidationError) as exc_info:
            environmental_profile_to_pydantic(invalid_profile)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_none_input_handling(self):
        """Test handling of None inputs."""
        with pytest.raises(ValueError) as exc_info:
            environmental_profile_to_pydantic(None)
        assert "cannot be None" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            environmental_profile_to_dataclass(None)
        assert "cannot be None" in str(exc_info.value)


class TestThematicProfileConversions:
    """Test conversions between dataclass and Pydantic ThematicProfile."""

    def test_dataclass_to_pydantic_basic(self):
        """Test basic dataclass to Pydantic conversion."""
        from studiorum.mcp.tools.encounter.themes import (
            ThematicProfile as DataclassProfile,
        )

        # Create dataclass profile
        dataclass_profile = DataclassProfile(
            theme=EncounterTheme.UNDEAD_HORROR,
            intensity=1.5,
            allow_mixed=True,
            narrative_context={
                "location": "haunted_crypt",
                "threat_level": 8,
                "bonus_xp": 0.25,
                "is_boss_fight": False,
            },
        )

        # Convert to Pydantic
        pydantic_profile = thematic_profile_to_pydantic(dataclass_profile)

        # Verify all fields transferred correctly
        assert (
            pydantic_profile.theme == dataclass_profile.theme.value
        )  # Pydantic stores enum values
        assert pydantic_profile.intensity == dataclass_profile.intensity
        assert pydantic_profile.allow_mixed == dataclass_profile.allow_mixed
        assert pydantic_profile.narrative_context == dataclass_profile.narrative_context

    def test_pydantic_to_dataclass_basic(self):
        """Test basic Pydantic to dataclass conversion."""
        from studiorum.mcp.tools.encounter.themes_pydantic import (
            ThematicProfile as PydanticProfile,
        )

        # Create Pydantic profile
        pydantic_profile = PydanticProfile(
            theme=EncounterTheme.DRACONIC_POWER,
            intensity=2.0,
            allow_mixed=False,
            narrative_context={
                "dragon_color": "red",
                "age_category": 15,
                "hoard_value": 50000.0,
                "has_lair": True,
            },
        )

        # Convert to dataclass
        dataclass_profile = thematic_profile_to_dataclass(pydantic_profile)

        # Verify all fields transferred correctly
        assert (
            dataclass_profile.theme.value == pydantic_profile.theme
        )  # Dataclass has enum, Pydantic has string
        assert dataclass_profile.intensity == pydantic_profile.intensity
        assert dataclass_profile.allow_mixed == pydantic_profile.allow_mixed
        assert dataclass_profile.narrative_context == pydantic_profile.narrative_context

    def test_round_trip_conversion(self):
        """Test dataclass -> Pydantic -> dataclass round trip."""
        from studiorum.mcp.tools.encounter.themes import (
            ThematicProfile as DataclassProfile,
        )

        # Create original dataclass
        original = DataclassProfile(
            theme=EncounterTheme.FEY_MYSTERY,
            intensity=0.8,
            allow_mixed=True,
            narrative_context={"season": "autumn", "moon_phase": 3},
        )

        # Round trip: dataclass -> Pydantic -> dataclass
        pydantic_version = thematic_profile_to_pydantic(original)
        restored = thematic_profile_to_dataclass(pydantic_version)

        # Should be identical
        assert restored.theme == original.theme
        assert restored.intensity == original.intensity
        assert restored.allow_mixed == original.allow_mixed
        assert restored.narrative_context == original.narrative_context

    def test_conversion_with_invalid_narrative_context(self):
        """Test conversion fails with invalid narrative context."""
        from studiorum.mcp.tools.encounter.themes import (
            ThematicProfile as DataclassProfile,
        )

        # Create dataclass with invalid narrative context
        invalid_profile = DataclassProfile(
            theme=EncounterTheme.ELEMENTAL_CHAOS,
            narrative_context={
                "nested": {"invalid": "data"}
            },  # Nested dict not allowed
        )

        # Should raise ValidationError when converting to Pydantic
        with pytest.raises(ValidationError) as exc_info:
            thematic_profile_to_pydantic(invalid_profile)
        # Pydantic v2 tries each union member and reports all failures
        error_str = str(exc_info.value)
        assert (
            "Input should be a valid string" in error_str
            or "must be string, int, float, or bool" in error_str
        )


class TestBalanceMetricsConversions:
    """Test conversions between dataclass and Pydantic BalanceMetrics."""

    def test_dataclass_to_pydantic_basic(self):
        """Test basic dataclass to Pydantic conversion."""
        from studiorum.mcp.tools.encounter.balancer import (
            BalanceMetrics as DataclassMetrics,
        )

        # Create dataclass metrics
        dataclass_metrics = DataclassMetrics(
            xp_accuracy=0.85,
            tactical_balance=0.75,
            action_economy_score=0.90,
            environmental_fit=0.80,
            narrative_alignment=0.70,
            overall_balance=0.82,
            strengths=["Good XP balance", "Excellent action economy"],
            weaknesses=["Limited tactical variety"],
            optimization_suggestions=[
                "Add ranged attackers",
                "Increase creature diversity",
            ],
        )

        # Convert to Pydantic
        pydantic_metrics = balance_metrics_to_pydantic(dataclass_metrics)

        # Verify all fields transferred correctly
        assert pydantic_metrics.xp_accuracy == dataclass_metrics.xp_accuracy
        assert pydantic_metrics.tactical_balance == dataclass_metrics.tactical_balance
        assert (
            pydantic_metrics.action_economy_score
            == dataclass_metrics.action_economy_score
        )
        assert pydantic_metrics.environmental_fit == dataclass_metrics.environmental_fit
        assert (
            pydantic_metrics.narrative_alignment
            == dataclass_metrics.narrative_alignment
        )
        assert pydantic_metrics.overall_balance == dataclass_metrics.overall_balance
        assert pydantic_metrics.strengths == dataclass_metrics.strengths
        assert pydantic_metrics.weaknesses == dataclass_metrics.weaknesses
        assert (
            pydantic_metrics.optimization_suggestions
            == dataclass_metrics.optimization_suggestions
        )

    def test_pydantic_to_dataclass_basic(self):
        """Test basic Pydantic to dataclass conversion."""
        from studiorum.mcp.tools.encounter.balancer_pydantic import (
            BalanceMetrics as PydanticMetrics,
        )

        # Create Pydantic metrics
        pydantic_metrics = PydanticMetrics(
            xp_accuracy=0.95,
            tactical_balance=0.88,
            action_economy_score=0.77,
            environmental_fit=0.66,
            narrative_alignment=0.55,
            strengths=["Perfect XP match", "Great variety"],
            weaknesses=["Environmental mismatch"],
            optimization_suggestions=["Replace desert creatures with forest types"],
        )
        pydantic_metrics.calculate_overall_balance()

        # Convert to dataclass
        dataclass_metrics = balance_metrics_to_dataclass(pydantic_metrics)

        # Verify all fields transferred correctly
        assert dataclass_metrics.xp_accuracy == pydantic_metrics.xp_accuracy
        assert dataclass_metrics.tactical_balance == pydantic_metrics.tactical_balance
        assert (
            dataclass_metrics.action_economy_score
            == pydantic_metrics.action_economy_score
        )
        assert dataclass_metrics.environmental_fit == pydantic_metrics.environmental_fit
        assert (
            dataclass_metrics.narrative_alignment
            == pydantic_metrics.narrative_alignment
        )
        assert dataclass_metrics.overall_balance == pydantic_metrics.overall_balance
        assert dataclass_metrics.strengths == pydantic_metrics.strengths
        assert dataclass_metrics.weaknesses == pydantic_metrics.weaknesses
        assert (
            dataclass_metrics.optimization_suggestions
            == pydantic_metrics.optimization_suggestions
        )

    def test_round_trip_conversion(self):
        """Test dataclass -> Pydantic -> dataclass round trip."""
        from studiorum.mcp.tools.encounter.balancer import (
            BalanceMetrics as DataclassMetrics,
        )

        # Create original dataclass
        original = DataclassMetrics(
            xp_accuracy=0.72,
            tactical_balance=0.68,
            strengths=["Decent balance"],
            weaknesses=["Needs improvement", "Action economy off"],
            optimization_suggestions=["Add minions", "Reduce boss CR"],
        )

        # Round trip: dataclass -> Pydantic -> dataclass
        pydantic_version = balance_metrics_to_pydantic(original)
        restored = balance_metrics_to_dataclass(pydantic_version)

        # Should be identical
        assert restored.xp_accuracy == original.xp_accuracy
        assert restored.tactical_balance == original.tactical_balance
        assert restored.strengths == original.strengths
        assert restored.weaknesses == original.weaknesses
        assert restored.optimization_suggestions == original.optimization_suggestions


@pytest.fixture
def make_test_encounter_result():
    """Factory for creating test EncounterGenerationResult objects."""

    def _make_result(
        balance_score: float = 0.75, encounter_id: str = "test_encounter", **kwargs
    ):
        from studiorum.core.models.encounter_types import XP, EncounterId
        from studiorum.core.services.encounter_collector import (
            EncounterCreature,
        )

        # Create a simple test creature for the encounter
        test_creature = type(
            "TestCreature",
            (),
            {
                "name": "Goblin",
                "cr": "1/4",
                "type": {"type": "humanoid"},
                "source": {"abbreviation": "MM", "page": 166},
            },
        )()

        creatures = [
            EncounterCreature(
                creature=test_creature,
                quantity=2,
                tactical_role="combatant",
                xp_contribution=XP(200),
                environmental_suitability=0.8,
            )
        ]

        tactical_analysis = {
            "total_creatures": 2,
            "unique_creature_types": 1,
            "creature_roles": {"combatant": 2},
            "capabilities": {
                "has_ranged_attackers": False,
                "has_spellcasters": False,
                "has_tanks": True,
            },
            "action_economy": {"action_ratio": 1.0, "balance_assessment": "balanced"},
        }

        defaults = {
            "encounter_id": EncounterId(encounter_id),
            "creatures": creatures,
            "total_base_xp": XP(200),
            "total_adjusted_xp": XP(300),
            "difficulty_rating": "medium",
            "balance_score": balance_score,
            "tactical_analysis": tactical_analysis,
            "environmental_fit": 0.8,
            "rebalance_suggestions": ["Encounter is well balanced"],
            "generation_time_ms": 150.0,
        }

        return EncounterGenerationResult(**{**defaults, **kwargs})

    return _make_result


class TestBalanceAnalysisConversions:
    """Test conversions between dataclass and Pydantic BalanceAnalysis."""

    def test_dataclass_to_pydantic_basic(self):
        """Test basic dataclass to Pydantic conversion."""
        from studiorum.mcp.tools.encounter.balancer import (
            BalanceAnalysis as DataclassAnalysis,
            BalanceMetrics as DataclassMetrics,
        )

        # Create dataclass analysis
        metrics = DataclassMetrics(xp_accuracy=0.8, tactical_balance=0.7)
        dataclass_analysis = DataclassAnalysis(
            encounter_id="test_encounter_123",
            original_encounter=_create_simple_result(0.6),
            balanced_encounter=_create_simple_result(0.85),
            metrics=metrics,
            strategy_used=BalanceStrategy.PRECISE,
            optimization_goal=OptimizationGoal.TACTICAL_VARIETY,
            processing_time_ms=250.5,
            iterations_performed=4,
        )

        # Convert to Pydantic
        pydantic_analysis = balance_analysis_to_pydantic(dataclass_analysis)

        # Verify all fields transferred correctly
        assert pydantic_analysis.encounter_id == dataclass_analysis.encounter_id
        assert (
            pydantic_analysis.original_encounter
            == dataclass_analysis.original_encounter
        )
        assert (
            pydantic_analysis.balanced_encounter
            == dataclass_analysis.balanced_encounter
        )
        # Pydantic stores enum values as strings due to use_enum_values=True
        assert pydantic_analysis.strategy_used == dataclass_analysis.strategy_used.value
        assert (
            pydantic_analysis.optimization_goal
            == dataclass_analysis.optimization_goal.value
        )
        assert (
            pydantic_analysis.processing_time_ms
            == dataclass_analysis.processing_time_ms
        )
        assert (
            pydantic_analysis.iterations_performed
            == dataclass_analysis.iterations_performed
        )

        # Metrics should be converted too
        assert pydantic_analysis.metrics.xp_accuracy == metrics.xp_accuracy
        assert pydantic_analysis.metrics.tactical_balance == metrics.tactical_balance

    def test_pydantic_to_dataclass_basic(self):
        """Test basic Pydantic to dataclass conversion."""
        from studiorum.mcp.tools.encounter.balancer_pydantic import (
            BalanceAnalysis as PydanticAnalysis,
            BalanceMetrics as PydanticMetrics,
        )

        # Create Pydantic analysis
        metrics = PydanticMetrics(xp_accuracy=0.9, tactical_balance=0.8)
        pydantic_analysis = PydanticAnalysis(
            encounter_id="test_encounter_456",
            original_encounter=_create_simple_result(0.5),
            balanced_encounter=_create_simple_result(0.88),
            metrics=metrics,
            strategy_used=BalanceStrategy.AGGRESSIVE,
            optimization_goal=OptimizationGoal.ACTION_ECONOMY,
            processing_time_ms=180.0,
            iterations_performed=2,
        )

        # Convert to dataclass
        dataclass_analysis = balance_analysis_to_dataclass(pydantic_analysis)

        # Verify all fields transferred correctly
        assert dataclass_analysis.encounter_id == pydantic_analysis.encounter_id
        assert (
            dataclass_analysis.original_encounter
            == pydantic_analysis.original_encounter
        )
        assert (
            dataclass_analysis.balanced_encounter
            == pydantic_analysis.balanced_encounter
        )
        assert dataclass_analysis.strategy_used == pydantic_analysis.strategy_used
        assert (
            dataclass_analysis.optimization_goal == pydantic_analysis.optimization_goal
        )
        assert (
            dataclass_analysis.processing_time_ms
            == pydantic_analysis.processing_time_ms
        )
        assert (
            dataclass_analysis.iterations_performed
            == pydantic_analysis.iterations_performed
        )

        # Metrics should be converted too
        assert dataclass_analysis.metrics.xp_accuracy == metrics.xp_accuracy
        assert dataclass_analysis.metrics.tactical_balance == metrics.tactical_balance


class TestSerializationFunctions:
    """Test JSON serialization utility functions."""

    def test_environmental_profile_serialization(self):
        """Test environmental profile serialization and deserialization."""
        from studiorum.mcp.tools.encounter.themes import (
            EnvironmentalProfile as DataclassProfile,
        )

        # Create dataclass profile
        original = DataclassProfile(
            environment=EnvironmentType.UNDERWATER,
            climate="tropical",
            weather="storm",
            visibility_range=40,
            creature_affinities={"elemental": 2.5, "beast": 1.8},
        )

        # Serialize to dict
        data = serialize_environmental_profile(original)
        assert isinstance(data, dict)
        assert data["environment"] == "underwater"
        assert data["climate"] == "tropical"
        assert data["weather"] == "storm"
        assert data["visibility_range"] == 40
        assert "creature_affinities" in data

        # Deserialize back
        restored = deserialize_environmental_profile(data)

        # Should match original
        assert restored.environment == original.environment
        assert restored.climate == original.climate
        assert restored.weather == original.weather
        assert restored.visibility_range == original.visibility_range
        assert restored.creature_affinities == original.creature_affinities

    def test_thematic_profile_serialization(self):
        """Test thematic profile serialization and deserialization."""
        from studiorum.mcp.tools.encounter.themes import (
            ThematicProfile as DataclassProfile,
        )

        # Create dataclass profile
        original = DataclassProfile(
            theme=EncounterTheme.ABERRANT_MADNESS,
            intensity=1.8,
            allow_mixed=True,
            narrative_context={"sanity_loss": 2, "corruption_level": 0.7},
        )

        # Serialize to dict
        data = serialize_thematic_profile(original)
        assert isinstance(data, dict)
        assert data["theme"] == "aberrant_madness"
        assert data["intensity"] == 1.8
        assert data["allow_mixed"] is True
        assert "narrative_context" in data

        # Deserialize back
        restored = deserialize_thematic_profile(data)

        # Should match original
        assert restored.theme == original.theme
        assert restored.intensity == original.intensity
        assert restored.allow_mixed == original.allow_mixed
        assert restored.narrative_context == original.narrative_context

    def test_balance_metrics_serialization(self):
        """Test balance metrics serialization and deserialization."""
        from studiorum.mcp.tools.encounter.balancer import (
            BalanceMetrics as DataclassMetrics,
        )

        # Create dataclass metrics
        original = DataclassMetrics(
            xp_accuracy=0.91,
            tactical_balance=0.83,
            action_economy_score=0.76,
            strengths=["Great XP match", "Good variety"],
            weaknesses=["Action economy slightly off"],
            optimization_suggestions=["Fine-tune creature quantities"],
        )

        # Serialize to dict
        data = serialize_balance_metrics(original)
        assert isinstance(data, dict)
        assert data["xp_accuracy"] == 0.91
        assert data["tactical_balance"] == 0.83
        assert len(data["strengths"]) == 2
        assert len(data["weaknesses"]) == 1

        # Deserialize back
        restored = deserialize_balance_metrics(data)

        # Should match original
        assert restored.xp_accuracy == original.xp_accuracy
        assert restored.tactical_balance == original.tactical_balance
        assert restored.strengths == original.strengths
        assert restored.weaknesses == original.weaknesses

    def test_balance_analysis_serialization(self):
        """Test balance analysis serialization and deserialization."""
        from studiorum.mcp.tools.encounter.balancer import (
            BalanceAnalysis as DataclassAnalysis,
            BalanceMetrics as DataclassMetrics,
        )

        # Create dataclass analysis
        metrics = DataclassMetrics(xp_accuracy=0.85)
        original = DataclassAnalysis(
            encounter_id="serialization_test",
            original_encounter=_create_simple_result(0.62),
            balanced_encounter=_create_simple_result(0.87),
            metrics=metrics,
            strategy_used=BalanceStrategy.DYNAMIC,
            optimization_goal=OptimizationGoal.RESOURCE_DRAIN,
            processing_time_ms=320.8,
            iterations_performed=5,
        )

        # Serialize to dict
        data = serialize_balance_analysis(original)
        assert isinstance(data, dict)
        assert data["encounter_id"] == "serialization_test"
        assert data["strategy_used"] == "dynamic"
        assert data["optimization_goal"] == "resource_drain"
        assert data["processing_time_ms"] == 320.8
        assert data["iterations_performed"] == 5
        assert "metrics" in data

        # Deserialize back
        restored = deserialize_balance_analysis(data)

        # Should match original
        assert restored.encounter_id == original.encounter_id
        # Pydantic stores enum values as strings due to use_enum_values=True
        assert restored.strategy_used == original.strategy_used.value
        # Pydantic stores enum values as strings due to use_enum_values=True
        assert restored.optimization_goal == original.optimization_goal.value
        assert restored.processing_time_ms == original.processing_time_ms
        assert restored.iterations_performed == original.iterations_performed

    def test_serialization_error_handling(self):
        """Test error handling in serialization functions."""
        # Test None inputs
        with pytest.raises(ValueError) as exc_info:
            serialize_environmental_profile(None)
        assert "Cannot serialize None" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            deserialize_environmental_profile(None)
        assert "Cannot deserialize empty data" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            deserialize_thematic_profile({})
        assert "Cannot deserialize empty data" in str(exc_info.value)

    def test_serialization_with_invalid_data(self):
        """Test serialization fails with invalid data."""
        # Test deserialization with invalid data structure
        with pytest.raises(ValidationError):
            deserialize_environmental_profile(
                {"environment": "invalid_environment_type", "climate": "temperate"}
            )

        with pytest.raises(ValidationError):
            deserialize_thematic_profile(
                {"theme": "nonexistent_theme", "intensity": 1.0}
            )


def test_comprehensive_migration_workflow():
    """Test a complete migration workflow across all model types."""
    from studiorum.mcp.tools.encounter.balancer import (
        BalanceAnalysis as AnalysisDataclass,
        BalanceMetrics as MetricsDataclass,
    )
    from studiorum.mcp.tools.encounter.themes import (
        EnvironmentalProfile as EnvDataclass,
        ThematicProfile as ThemeDataclass,
    )

    # Step 1: Create original dataclass models
    env_profile = EnvDataclass(
        environment=EnvironmentType.UNDERDARK,
        lighting="dark",
        terrain_difficulty="extreme",
    )

    theme_profile = ThemeDataclass(
        theme=EncounterTheme.ABERRANT_MADNESS,
        intensity=1.6,
        narrative_context={"corruption": 8},
    )

    metrics = MetricsDataclass(
        xp_accuracy=0.88,
        tactical_balance=0.72,
        strengths=["Good challenge"],
        weaknesses=["Limited variety"],
    )

    analysis = AnalysisDataclass(
        encounter_id="comprehensive_test",
        original_encounter=_create_simple_result(0.68),
        balanced_encounter=_create_simple_result(0.85),
        metrics=metrics,
        strategy_used=BalanceStrategy.CONSERVATIVE,
        optimization_goal=OptimizationGoal.TACTICAL_VARIETY,
        processing_time_ms=150.0,
        iterations_performed=2,
    )

    # Step 2: Convert all to Pydantic (with validation)
    # These conversions validate the data and exercise the migration helpers
    environmental_profile_to_pydantic(env_profile)
    thematic_profile_to_pydantic(theme_profile)
    balance_metrics_to_pydantic(metrics)
    balance_analysis_to_pydantic(analysis)

    # Step 3: Serialize all to JSON-compatible dicts
    env_data = serialize_environmental_profile(env_profile)
    theme_data = serialize_thematic_profile(theme_profile)
    metrics_data = serialize_balance_metrics(metrics)
    analysis_data = serialize_balance_analysis(analysis)

    # Verify all data is JSON-serializable
    import json

    json_env = json.dumps(env_data)
    json_theme = json.dumps(theme_data)
    json_metrics = json.dumps(metrics_data)
    json_analysis = json.dumps(analysis_data)

    # Step 4: Deserialize back from JSON
    restored_env_data = json.loads(json_env)
    restored_theme_data = json.loads(json_theme)
    restored_metrics_data = json.loads(json_metrics)
    restored_analysis_data = json.loads(json_analysis)

    # Step 5: Convert back to dataclasses
    final_env = deserialize_environmental_profile(restored_env_data)
    final_theme = deserialize_thematic_profile(restored_theme_data)
    final_metrics = deserialize_balance_metrics(restored_metrics_data)
    final_analysis = deserialize_balance_analysis(restored_analysis_data)

    # Step 6: Verify everything survived the round trip
    assert final_env.environment == env_profile.environment
    assert final_env.lighting == env_profile.lighting
    assert final_env.terrain_difficulty == env_profile.terrain_difficulty

    assert final_theme.theme == theme_profile.theme
    assert final_theme.intensity == theme_profile.intensity
    assert final_theme.narrative_context == theme_profile.narrative_context

    assert final_metrics.xp_accuracy == metrics.xp_accuracy
    assert final_metrics.tactical_balance == metrics.tactical_balance
    assert final_metrics.strengths == metrics.strengths
    assert final_metrics.weaknesses == metrics.weaknesses

    assert final_analysis.encounter_id == analysis.encounter_id
    # Pydantic stores enum values as strings due to use_enum_values=True
    assert final_analysis.strategy_used == analysis.strategy_used.value
    assert final_analysis.processing_time_ms == analysis.processing_time_ms
    assert final_analysis.iterations_performed == analysis.iterations_performed
