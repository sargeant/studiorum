"""Comprehensive tests for encounter building MCP tools.

This module provides complete test coverage for the encounter building system,
including budget calculation, creature search, encounter generation, and
rebalancing functionality.

Tests maintain the required reset_test_environment() pattern for parallel execution
and include both unit tests and integration scenarios.
"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from studiorum.core.error_types import ContentNotFoundError, MCPException
from studiorum.core.models.encounter_types import (
    XP,
    EncounterConstraints,
    EnvironmentalModifiers,
    PartyComposition,
)
from studiorum.mcp.tools.encounter.budget import calculate_encounter_budget
from studiorum.mcp.tools.encounter.tools import (
    build_balanced_encounter_mcp,
    calculate_encounter_budget_mcp,
    get_encounter_tool_definitions,
    rebalance_encounter_mcp,
    search_creatures_for_encounter_mcp,
)


class TestEncounterBudgetCalculation:
    """Test encounter budget calculation functionality."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_basic_budget_calculation(self) -> None:
        """Test basic encounter budget calculation."""
        result = calculate_encounter_budget(
            party_size=4, party_level=5, difficulty="medium"
        )

        assert "base_xp_budget" in result
        assert "adjusted_xp_budget" in result
        assert "thresholds" in result
        assert result["party_size"] == 4
        assert result["party_level"] == 5
        assert result["target_difficulty"] == "medium"

        # Check that we get reasonable XP values for level 5 party
        assert 1000 <= result["base_xp_budget"] <= 3000
        assert isinstance(result["thresholds"], dict)
        assert all(
            threshold in result["thresholds"]
            for threshold in ["easy", "medium", "hard", "deadly"]
        )

    def test_party_size_adjustments(self) -> None:
        """Test party size adjustments affect encounter budget."""
        small_party = calculate_encounter_budget(2, 5, "medium")
        standard_party = calculate_encounter_budget(4, 5, "medium")
        large_party = calculate_encounter_budget(6, 5, "medium")

        # Small parties should have higher effective budgets (encounters are harder)
        assert (
            small_party["composition_modifier"] > standard_party["composition_modifier"]
        )

        # Large parties should have lower effective budgets (encounters are easier)
        assert (
            large_party["composition_modifier"] < standard_party["composition_modifier"]
        )

    def test_mixed_level_parties(self) -> None:
        """Test mixed-level party calculations."""
        result = calculate_encounter_budget(
            party_size=4,
            party_level=5,  # This should be ignored when individual_levels provided
            difficulty="hard",
            individual_levels=[4, 5, 5, 6],
        )

        assert result["party_size"] == 4
        # Should use effective level from individual levels (5)
        assert result["party_level"] == 5
        assert result["target_difficulty"] == "hard"

    def test_all_difficulty_levels(self) -> None:
        """Test all difficulty levels produce valid budgets."""
        party_size, party_level = 4, 8

        results = {}
        for difficulty in ["easy", "medium", "hard", "deadly"]:
            result = calculate_encounter_budget(party_size, party_level, difficulty)
            results[difficulty] = result["base_xp_budget"]

        # Budget should increase with difficulty
        assert results["easy"] < results["medium"]
        assert results["medium"] < results["hard"]
        assert results["hard"] < results["deadly"]

    def test_level_scaling(self) -> None:
        """Test encounter budgets scale with party level."""
        low_level = calculate_encounter_budget(4, 3, "medium")
        mid_level = calculate_encounter_budget(4, 10, "medium")
        high_level = calculate_encounter_budget(4, 17, "medium")

        assert low_level["base_xp_budget"] < mid_level["base_xp_budget"]
        assert mid_level["base_xp_budget"] < high_level["base_xp_budget"]

    def test_invalid_parameters(self) -> None:
        """Test validation of invalid parameters."""
        # Invalid party size
        with pytest.raises(ValueError, match="Party size must be between 1 and 8"):
            calculate_encounter_budget(0, 5, "medium")

        with pytest.raises(ValueError, match="Party size must be between 1 and 8"):
            calculate_encounter_budget(10, 5, "medium")

        # Invalid party level
        with pytest.raises(ValueError, match="Party level must be between 1 and 20"):
            calculate_encounter_budget(4, 0, "medium")

        with pytest.raises(ValueError, match="Party level must be between 1 and 20"):
            calculate_encounter_budget(4, 25, "medium")

        # Invalid difficulty
        with pytest.raises(ValueError, match="Invalid difficulty"):
            calculate_encounter_budget(4, 5, "impossible")

    @pytest.mark.asyncio
    async def test_mcp_budget_calculation(self) -> None:
        """Test MCP interface for budget calculation."""
        result = await calculate_encounter_budget_mcp(
            party_size=4, party_level=7, difficulty="hard"
        )

        assert "base_xp_budget" in result
        assert "adjusted_xp_budget" in result
        assert "mcp_metadata" in result
        assert "encounter_advice" in result
        assert result["mcp_metadata"]["tool"] == "calculate_encounter_budget"
        assert result["mcp_metadata"]["dmg_compliance"] is True

    @pytest.mark.asyncio
    async def test_mcp_validation_errors(self) -> None:
        """Test MCP validation error handling."""
        with pytest.raises(MCPException):
            await calculate_encounter_budget_mcp(
                party_size=0, party_level=5, difficulty="medium"
            )

        with pytest.raises(MCPException):
            await calculate_encounter_budget_mcp(
                party_size=4, party_level=25, difficulty="medium"
            )

        with pytest.raises(MCPException):
            await calculate_encounter_budget_mcp(
                party_size=4, party_level=5, difficulty="legendary"
            )


class TestEncounterConstraints:
    """Test encounter constraint validation and processing."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_basic_constraints(self) -> None:
        """Test basic encounter constraint creation."""
        constraints = EncounterConstraints(
            min_cr=2.0,
            max_cr=5.0,
            creature_types=["dragon", "beast"],
            no_legendary=True,
            max_creatures=6,
        )

        assert constraints.min_cr == 2.0
        assert constraints.max_cr == 5.0
        assert constraints.creature_types == ["dragon", "beast"]
        assert constraints.no_legendary is True
        assert constraints.max_creatures == 6

    def test_constraint_validation(self) -> None:
        """Test constraint validation logic."""
        # Valid constraints should not raise
        constraints = EncounterConstraints(min_cr=1.0, max_cr=5.0, max_creatures=4)
        constraints.validate_for_encounter()

        # Invalid constraint combinations should raise
        with pytest.raises(
            ValueError, match="Cannot require boss and prefer multiple weaker creatures"
        ):
            invalid = EncounterConstraints(
                require_boss=True, prefer_multiple_weaker=True
            )
            invalid.validate_for_encounter()

        with pytest.raises(ValidationError):
            EncounterConstraints(max_creatures=0)

    def test_xp_constraints(self) -> None:
        """Test XP-based constraints."""
        constraints = EncounterConstraints(
            min_xp_per_creature=XP(100),
            max_xp_per_creature=XP(1000),
            allow_single_powerful=True,
        )

        assert constraints.min_xp_per_creature == 100
        assert constraints.max_xp_per_creature == 1000
        assert constraints.allow_single_powerful is True

        # Invalid XP range should raise
        with pytest.raises(
            ValueError, match="min_xp_per_creature cannot exceed max_xp_per_creature"
        ):
            invalid = EncounterConstraints(
                min_xp_per_creature=XP(1000), max_xp_per_creature=XP(100)
            )
            invalid.validate_for_encounter()


class TestEnvironmentalProfiles:
    """Test environmental profile functionality."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_environmental_profile_creation(self) -> None:
        """Test creating environmental profiles."""
        from studiorum.mcp.tools.encounter.themes import create_environmental_profile

        profile = create_environmental_profile(
            "forest", climate="temperate", lighting="dim", weather="rain"
        )

        assert profile.environment.value == "forest"
        assert profile.climate == "temperate"
        assert profile.lighting == "dim"
        assert profile.weather == "rain"
        assert isinstance(profile.creature_affinities, dict)

    def test_creature_suitability_calculation(self) -> None:
        """Test creature suitability scoring."""
        from studiorum.core.models.creatures import Creature
        from studiorum.mcp.tools.encounter.themes import create_environmental_profile

        forest_profile = create_environmental_profile("forest")

        # Create mock creature with forest-appropriate type
        forest_creature = Mock(spec=Creature)
        forest_creature.type = {"type": "beast"}
        forest_creature.senses = "darkvision 60 ft."
        forest_creature.speed = {"walk": 30}

        suitability = forest_profile.calculate_creature_suitability(forest_creature)

        # Should be higher than baseline (1.0) for forest creatures
        assert suitability > 1.0
        assert suitability <= 2.0  # Max cap

    def test_invalid_environment_type(self) -> None:
        """Test handling of invalid environment types."""
        from studiorum.mcp.tools.encounter.themes import create_environmental_profile

        with pytest.raises(ValueError, match="Invalid environment type"):
            create_environmental_profile("atlantis")


class TestThematicProfiles:
    """Test thematic profile functionality."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_thematic_profile_creation(self) -> None:
        """Test creating thematic profiles."""
        from studiorum.mcp.tools.encounter.themes import create_thematic_profile

        profile = create_thematic_profile(
            "undead_horror", intensity=1.5, allow_mixed=True
        )

        assert profile.theme.value == "undead_horror"
        assert profile.intensity == 1.5
        assert profile.allow_mixed is True

    def test_thematic_fit_calculation(self) -> None:
        """Test thematic fit scoring."""
        from studiorum.core.models.creatures import Creature
        from studiorum.mcp.tools.encounter.themes import create_thematic_profile

        undead_profile = create_thematic_profile("undead_horror", intensity=1.0)

        # Create mock undead creature
        undead_creature = Mock(spec=Creature)
        undead_creature.type = {"type": "undead"}

        fit = undead_profile.calculate_thematic_fit(undead_creature)

        # Should be high fit for matching theme
        assert fit > 1.5
        assert fit <= 2.0

    def test_invalid_theme_type(self) -> None:
        """Test handling of invalid theme types."""
        from studiorum.mcp.tools.encounter.themes import create_thematic_profile

        with pytest.raises(ValueError, match="Invalid theme"):
            create_thematic_profile("rainbow_unicorns")


class TestMCPToolIntegration:
    """Test MCP tool interface integration."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    @pytest.mark.asyncio
    async def test_creature_search_placeholder(self) -> None:
        """Test creature search MCP tool (placeholder implementation)."""
        result = await search_creatures_for_encounter_mcp(
            constraints={"min_cr": 2, "max_cr": 5},
            environment="forest",
            theme="beast_wilderness",
        )

        # Should return placeholder response with metadata
        assert result["status"] == "search_not_implemented"
        assert "mcp_metadata" in result
        assert result["mcp_metadata"]["tool"] == "search_creatures_for_encounter"
        assert result["constraints"]["min_cr"] == 2
        assert result["environment"] == "forest"
        assert result["theme"] == "beast_wilderness"

    @pytest.mark.asyncio
    async def test_encounter_building_placeholder(self) -> None:
        """Test encounter building MCP tool (placeholder implementation)."""
        result = await build_balanced_encounter_mcp(
            party_size=4,
            party_level=6,
            difficulty="hard",
            environment="dungeon",
            theme="undead_horror",
        )

        # Should return structured placeholder with budget
        assert "encounter_id" in result
        assert "party_composition" in result
        assert "encounter_budget" in result
        assert "mcp_metadata" in result
        assert result["target_difficulty"] == "hard"
        assert result["environmental_profile"]["type"] == "dungeon"
        assert result["thematic_profile"]["theme"] == "undead_horror"

    @pytest.mark.asyncio
    async def test_encounter_rebalancing_placeholder(self) -> None:
        """Test encounter rebalancing MCP tool."""
        encounter_data = {"creatures": [], "difficulty": "medium"}

        result = await rebalance_encounter_mcp(
            encounter_data=encounter_data,
            target_difficulty="hard",
            party_size=4,
            party_level=8,
            strategy="conservative",
            max_iterations=3,
        )

        # Should return rebalancing analysis
        assert result["status"] == "rebalancing_not_implemented"
        assert result["target_difficulty"] == "hard"
        assert result["strategy"] == "conservative"
        assert "mcp_metadata" in result
        assert result["mcp_metadata"]["strategy_used"] == "conservative"

    @pytest.mark.asyncio
    async def test_invalid_rebalancing_strategy(self) -> None:
        """Test validation of rebalancing strategy."""
        with pytest.raises(MCPException, match="Invalid rebalancing strategy"):
            await rebalance_encounter_mcp(
                encounter_data={},
                target_difficulty="hard",
                party_size=4,
                party_level=8,
                strategy="godmode",
            )

    def test_tool_definitions(self) -> None:
        """Test MCP tool definition generation."""
        definitions = get_encounter_tool_definitions()

        assert len(definitions) == 4
        tool_names = [tool["name"] for tool in definitions]

        assert "calculate_encounter_budget" in tool_names
        assert "search_creatures_for_encounter" in tool_names
        assert "build_balanced_encounter" in tool_names
        assert "rebalance_encounter" in tool_names

        # Check that each tool has required structure
        for tool in definitions:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]
            assert "required" in tool["inputSchema"]


class TestPartyComposition:
    """Test party composition calculations."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_basic_party_composition(self) -> None:
        """Test basic party composition creation."""
        party = PartyComposition(size=4, level=5)

        assert party.size == 4
        assert party.level == 5
        assert party.get_effective_level() == 5
        assert party.get_size_multiplier() == 1.0  # Standard size

    def test_mixed_level_party(self) -> None:
        """Test mixed-level party calculations."""
        party = PartyComposition(
            size=4,
            level=5,  # This should be overridden
            individual_levels=[3, 5, 5, 7],
        )

        assert party.get_effective_level() == 5  # Average of individual levels

    def test_party_size_multipliers(self) -> None:
        """Test party size multiplier calculations."""
        small_party = PartyComposition(size=2, level=5)
        standard_party = PartyComposition(size=4, level=5)
        large_party = PartyComposition(size=6, level=5)
        very_large_party = PartyComposition(size=8, level=5)

        assert small_party.get_size_multiplier() == 1.5  # Harder for small parties
        assert standard_party.get_size_multiplier() == 1.0  # Standard
        assert large_party.get_size_multiplier() == 0.75  # Easier for large parties
        assert very_large_party.get_size_multiplier() == 0.5  # Much easier


@pytest.mark.integration
class TestEncounterServiceIntegration:
    """Integration tests for encounter services (requires service container)."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def test_service_registration(self) -> None:
        """Test encounter service registration in container."""
        from studiorum.core.services.encounter_services import (
            get_encounter_service_lifecycle_summary,
            validate_encounter_service_registration,
        )

        # Validate service registration
        issues = validate_encounter_service_registration()
        assert len(issues) == 0, f"Service registration issues: {issues}"

        # Check service lifecycle summary
        summary = get_encounter_service_lifecycle_summary()

        expected_services = [
            "EncounterCollectorProtocol",
            "EncounterBalancerProtocol",
            "ThematicEncounterGeneratorProtocol",
        ]

        for service in expected_services:
            assert service in summary
            assert summary[service]["lifecycle"] == "SCOPED"

    @patch("studiorum.core.services.encounter_services.EncounterCollector")
    def test_encounter_collector_service_creation(self, mock_collector) -> None:
        """Test encounter collector service creation."""
        from studiorum.core.services.encounter_services import (
            create_encounter_collector_service,
        )

        # Mock omnidexer
        mock_omnidexer = Mock()

        # This would be called by the service container
        # For testing, we just verify the factory works
        result = create_encounter_collector_service(mock_omnidexer)

        # Should return the collector instance
        assert result is not None

    def test_container_integration(self) -> None:
        """Test integration with service container."""
        from studiorum.core.services.encounter_services import (
            get_encounter_collector_from_container,
        )

        # Mock container and omnidexer result
        mock_container_instance = Mock()
        mock_omnidexer_result = Mock()
        mock_omnidexer_result.is_success.return_value = True
        mock_omnidexer_result.unwrap.return_value = Mock()
        mock_container_instance.get_omnidexer.return_value = mock_omnidexer_result

        # Should successfully create encounter collector
        with patch(
            "studiorum.core.services.encounter_collector.EncounterCollector"
        ) as mock_ec:
            # Make the mock return itself when called (so result is not None)
            mock_ec.return_value = mock_ec
            result = get_encounter_collector_from_container(mock_container_instance)
            assert result is not None
            mock_ec.assert_called_once()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
