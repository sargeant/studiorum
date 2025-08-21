"""MCP tools for encounter building and balancing.

This module provides the MCP tool interface for encounter building capabilities,
including encounter budget calculation, creature search, encounter generation,
and rebalancing functionality.

All tools maintain <500ms performance targets and provide comprehensive
error handling with meaningful suggestions.
"""

import logging
from typing import Any, cast

from dnd5e.core.error_types import (
    ContentNotFoundError,
    ErrorCategory,
    ErrorSeverity,
    MCPError,
    MCPErrorCode,
    MCPException,
)
from dnd5e.core.models.encounter_types import (
    XP,
    EncounterConstraints,
    EnvironmentalModifiers,
    PartyComposition,
)
from dnd5e.core.result import Error, Result, Success
from dnd5e.mcp.tools.encounter.balancer import rebalance_encounter
from dnd5e.mcp.tools.encounter.budget import calculate_encounter_budget
from dnd5e.mcp.tools.encounter.themes import (
    create_environmental_profile,
    create_thematic_profile,
)

logger = logging.getLogger(__name__)


async def calculate_encounter_budget_mcp(
    party_size: int,
    party_level: int,
    difficulty: str = "medium",
    individual_levels: list[int] | None = None,
) -> dict[str, Any]:
    """Calculate encounter XP budget for given party composition.

    MCP Tool: calculate_encounter_budget

    Calculates DMG-accurate encounter budgets with party size adjustments
    and mixed-level party support. Provides complete difficulty analysis
    with tactical recommendations.

    Args:
        party_size: Number of characters in the party (1-8)
        party_level: Average party level (1-20)
        difficulty: Target encounter difficulty (easy/medium/hard/deadly)
        individual_levels: Individual character levels for mixed-level parties

    Returns:
        Dictionary with encounter budget details and recommendations

    Performance Target: <50ms for budget calculations

    Examples:
        Standard party:
        >>> budget = await calculate_encounter_budget_mcp(4, 5, "hard")
        >>> print(f"Target XP: {budget['adjusted_xp_budget']}")

        Mixed-level party:
        >>> budget = await calculate_encounter_budget_mcp(
        ...     4, 5, "medium", individual_levels=[4, 5, 5, 6]
        ... )

    Raises:
        ValidationError: If parameters are invalid
        ContentNotFoundError: If calculation fails
    """
    try:
        logger.info(
            f"Calculating encounter budget: {party_size} level-{party_level} party, {difficulty}"
        )

        # Validate parameters
        if party_size < 1 or party_size > 8:
            raise MCPException(
                MCPError(
                    message="Party size must be between 1 and 8",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="calculate_encounter_budget_mcp",
                    suggestions=[
                        "Use party sizes between 1-8 characters",
                        "Split large parties into smaller groups",
                        "Adjust encounter multipliers for very large parties",
                    ],
                    data={
                        "party_size": party_size,
                        "valid_range": "1-8",
                        "operation": "encounter_budget_calculation",
                    },
                )
            )

        if party_level < 1 or party_level > 20:
            raise MCPException(
                MCPError(
                    message="Party level must be between 1 and 20",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="calculate_encounter_budget_mcp",
                    suggestions=[
                        "Use character levels between 1-20",
                        "For epic level campaigns, use level 20 as maximum",
                        "Adjust encounter calculations manually for epic levels",
                    ],
                    data={
                        "party_level": party_level,
                        "valid_range": "1-20",
                        "operation": "encounter_budget_calculation",
                    },
                )
            )

        if difficulty not in ["easy", "medium", "hard", "deadly"]:
            raise MCPException(
                MCPError(
                    message=f"Invalid difficulty: {difficulty}",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="calculate_encounter_budget_mcp",
                    suggestions=[
                        "Use difficulty levels: easy, medium, hard, or deadly",
                        "Check spelling and capitalization",
                        "Refer to DMG p. 82 for difficulty guidelines",
                    ],
                    data={
                        "difficulty": difficulty,
                        "valid_options": ["easy", "medium", "hard", "deadly"],
                        "operation": "encounter_budget_calculation",
                    },
                )
            )

        # Calculate budget using existing function
        budget_result = calculate_encounter_budget(
            party_size, party_level, difficulty, individual_levels
        )

        # Enhance with additional encounter building guidance
        budget_result["mcp_metadata"] = {
            "tool": "calculate_encounter_budget",
            "performance_target": "< 50ms",
            "dmg_compliance": True,
            "party_analysis": {
                "size_category": (
                    "small"
                    if party_size <= 3
                    else "large"
                    if party_size >= 6
                    else "standard"
                ),
                "level_tier": (
                    "low"
                    if party_level <= 4
                    else "mid"
                    if party_level <= 10
                    else "high"
                    if party_level <= 16
                    else "epic"
                ),
            },
        }

        # Add tactical encounter building advice
        if difficulty == "deadly":
            budget_result["encounter_advice"] = [
                "Deadly encounters can cause character deaths",
                "Ensure party has full resources (hit points, spell slots)",
                "Consider environmental escape routes",
                "Use legendary actions for single creature encounters",
            ]
        elif difficulty == "hard":
            budget_result["encounter_advice"] = [
                "Hard encounters should be challenging but fair",
                "Good for climactic moments or boss fights",
                "Consider terrain advantages for dynamic combat",
            ]
        elif difficulty == "easy":
            budget_result["encounter_advice"] = [
                "Easy encounters for resource conservation",
                "Good for introducing new creature types",
                "Can be used to drain resources over multiple encounters",
            ]

        logger.debug(
            f"Encounter budget calculated: {budget_result['adjusted_xp_budget']} XP"
        )
        return budget_result

    except (MCPException, ValueError) as e:
        logger.error(f"Encounter budget calculation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in encounter budget calculation: {e}")
        raise MCPException(
            MCPError(
                message=f"Encounter budget calculation failed: {e}",
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.ERROR,
                source="calculate_encounter_budget_mcp",
                suggestions=[
                    "Check input parameters for validity",
                    "Verify DMG encounter building rules",
                    "Try with different parameter combinations",
                ],
                data={
                    "party_size": party_size,
                    "party_level": party_level,
                    "difficulty": difficulty,
                    "operation": "encounter_budget_calculation",
                },
            )
        )


async def search_creatures_for_encounter_mcp(
    constraints: dict[str, Any],
    xp_budget: int | None = None,
    environment: str | None = None,
    theme: str | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Search for creatures suitable for encounter building.

    MCP Tool: search_creatures_for_encounter

    Advanced creature search with encounter-specific constraints including
    environmental suitability, thematic coherence, and XP budget filtering.

    Args:
        constraints: Creature filtering constraints dictionary
        xp_budget: Optional XP budget limit for pre-filtering
        environment: Environment type for suitability scoring
        theme: Encounter theme for thematic filtering
        sources: Source books to search (defaults to configured sources)

    Returns:
        Dictionary with matching creatures and metadata

    Performance Target: <200ms for creature search

    Examples:
        Basic search:
        >>> creatures = await search_creatures_for_encounter_mcp({
        ...     "min_cr": 2, "max_cr": 5, "creature_types": ["dragon"]
        ... })

        Environmental search:
        >>> creatures = await search_creatures_for_encounter_mcp(
        ...     {"min_cr": 1, "max_cr": 3},
        ...     environment="forest", theme="beast_wilderness"
        ... )

    Raises:
        ValidationError: If constraints are invalid
        ContentNotFoundError: If no creatures found
    """
    try:
        logger.info(
            f"Searching creatures for encounter with constraints: {constraints}"
        )

        # This would be implemented when service container integration is complete
        # For now, return placeholder response
        return {
            "status": "search_not_implemented",
            "message": "Creature search for encounters is not yet fully implemented",
            "constraints": constraints,
            "xp_budget": xp_budget,
            "environment": environment,
            "theme": theme,
            "sources": sources,
            "mcp_metadata": {
                "tool": "search_creatures_for_encounter",
                "performance_target": "< 200ms",
                "implementation_status": "pending_service_container_integration",
            },
        }

    except Exception as e:
        logger.error(f"Creature search failed: {e}")
        raise MCPException(
            MCPError(
                message=f"Creature search failed: {e}",
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.ERROR,
                source="search_creatures_for_encounter_mcp",
                suggestions=[
                    "Check search constraint parameters",
                    "Verify data sources are available",
                    "Try with broader search criteria",
                ],
                data={
                    "constraints": constraints,
                    "xp_budget": xp_budget,
                    "environment": environment,
                    "operation": "creature_search",
                },
            )
        )


async def build_balanced_encounter_mcp(
    party_size: int,
    party_level: int,
    difficulty: str,
    constraints: dict[str, Any] | None = None,
    environment: str | None = None,
    theme: str | None = None,
    individual_levels: list[int] | None = None,
) -> dict[str, Any]:
    """Build a balanced encounter for the given party and constraints.

    MCP Tool: build_balanced_encounter

    Complete encounter generation with DMG-accurate balancing, environmental
    considerations, and tactical analysis. Provides ready-to-run encounters.

    Args:
        party_size: Number of characters in party
        party_level: Average party level
        difficulty: Target difficulty (easy/medium/hard/deadly)
        constraints: Optional creature filtering constraints
        environment: Optional environment type for creature selection
        theme: Optional encounter theme
        individual_levels: Individual character levels for mixed parties

    Returns:
        Dictionary with complete encounter details and analysis

    Performance Target: <500ms for encounter generation

    Examples:
        Standard encounter:
        >>> encounter = await build_balanced_encounter_mcp(
        ...     4, 5, "hard"
        ... )

        Themed encounter:
        >>> encounter = await build_balanced_encounter_mcp(
        ...     4, 8, "deadly",
        ...     environment="dungeon", theme="undead_horror"
        ... )

    Raises:
        ValidationError: If parameters are invalid
        ContentNotFoundError: If encounter generation fails
    """
    try:
        logger.info(
            f"Building balanced encounter: {party_size} level-{party_level} party, {difficulty}"
        )

        # Validate core parameters (reuse validation from budget calculation)
        if party_size < 1 or party_size > 8:
            raise MCPException(
                MCPError(
                    message="Party size must be between 1 and 8",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="build_balanced_encounter_mcp",
                )
            )

        if party_level < 1 or party_level > 20:
            raise MCPException(
                MCPError(
                    message="Party level must be between 1 and 20",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="build_balanced_encounter_mcp",
                )
            )

        if difficulty not in ["easy", "medium", "hard", "deadly"]:
            raise MCPException(
                MCPError(
                    message=f"Invalid difficulty: {difficulty}",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="build_balanced_encounter_mcp",
                )
            )

        # Calculate base encounter budget
        budget_result = calculate_encounter_budget(
            party_size, party_level, difficulty, individual_levels
        )

        # This would use the full encounter generation pipeline when implemented
        # For now, return structured placeholder with budget information
        encounter_result = {
            "encounter_id": "placeholder_encounter_001",
            "party_composition": {
                "size": party_size,
                "level": party_level,
                "individual_levels": individual_levels,
            },
            "target_difficulty": difficulty,
            "encounter_budget": budget_result,
            "creatures": [],  # Would be populated by encounter generation
            "tactical_analysis": {
                "note": "Tactical analysis not yet implemented",
                "total_creatures": 0,
                "action_economy": {"party_actions": party_size, "enemy_actions": 0},
            },
            "environmental_profile": None
            if not environment
            else {
                "type": environment,
                "note": "Environmental profiles not yet fully implemented",
            },
            "thematic_profile": None
            if not theme
            else {
                "theme": theme,
                "note": "Thematic profiles not yet fully implemented",
            },
            "balance_score": 0.0,
            "recommendations": [
                "Encounter generation is not yet fully implemented",
                "Use the encounter budget to manually select creatures",
                f"Target adjusted XP: {budget_result['adjusted_xp_budget']}",
            ],
            "mcp_metadata": {
                "tool": "build_balanced_encounter",
                "performance_target": "< 500ms",
                "implementation_status": "partial_implementation",
                "budget_calculation": "complete",
                "creature_generation": "pending",
                "balance_analysis": "pending",
            },
        }

        logger.info("Balanced encounter structure created (implementation pending)")
        return encounter_result

    except (MCPException, ValueError) as e:
        logger.error(f"Encounter building failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in encounter building: {e}")
        raise MCPException(
            MCPError(
                message=f"Encounter building failed: {e}",
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.ERROR,
                source="build_balanced_encounter_mcp",
                suggestions=[
                    "Check party composition parameters",
                    "Verify encounter constraints",
                    "Try with standard difficulty levels",
                ],
                data={
                    "party_size": party_size,
                    "party_level": party_level,
                    "difficulty": difficulty,
                    "operation": "encounter_building",
                },
            )
        )


async def rebalance_encounter_mcp(
    encounter_data: dict[str, Any],
    target_difficulty: str,
    party_size: int,
    party_level: int,
    strategy: str = "precise",
    max_iterations: int = 5,
) -> dict[str, Any]:
    """Rebalance an existing encounter to match target difficulty.

    MCP Tool: rebalance_encounter

    Advanced encounter rebalancing with iterative optimization, multiple
    balancing strategies, and comprehensive analysis of changes made.

    Args:
        encounter_data: Current encounter data to rebalance
        target_difficulty: Desired difficulty level
        party_size: Number of party members
        party_level: Average party level
        strategy: Balancing strategy (conservative/aggressive/precise/dynamic)
        max_iterations: Maximum optimization iterations

    Returns:
        Dictionary with rebalanced encounter and analysis

    Performance Target: <300ms for encounter rebalancing

    Examples:
        Basic rebalancing:
        >>> rebalanced = await rebalance_encounter_mcp(
        ...     current_encounter, "hard", 4, 8
        ... )

        Conservative rebalancing:
        >>> rebalanced = await rebalance_encounter_mcp(
        ...     current_encounter, "deadly", 6, 12, strategy="conservative"
        ... )

    Raises:
        ValidationError: If parameters are invalid
        ContentNotFoundError: If rebalancing fails
    """
    try:
        logger.info(
            f"Rebalancing encounter to {target_difficulty} for {party_size} level-{party_level} party"
        )

        # Validate rebalancing parameters
        if target_difficulty not in ["easy", "medium", "hard", "deadly"]:
            raise MCPException(
                MCPError(
                    message=f"Invalid target difficulty: {target_difficulty}",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="rebalance_encounter_mcp",
                )
            )

        if strategy not in ["conservative", "aggressive", "precise", "dynamic"]:
            raise MCPException(
                MCPError(
                    message=f"Invalid rebalancing strategy: {strategy}",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="rebalance_encounter_mcp",
                    suggestions=[
                        "Use strategy: conservative, aggressive, precise, or dynamic",
                        "Conservative: Slightly easier than target",
                        "Aggressive: Slightly harder than target",
                        "Precise: Exact target difficulty",
                        "Dynamic: Adapts based on encounter characteristics",
                    ],
                )
            )

        if max_iterations < 1 or max_iterations > 10:
            raise MCPException(
                MCPError(
                    message="Max iterations must be between 1 and 10",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source="rebalance_encounter_mcp",
                )
            )

        # Use the existing rebalance function (which currently returns placeholder)
        rebalance_result = rebalance_encounter(
            encounter_data,
            party_size,
            party_level,
            target_difficulty,
            strategy,
            None,
            max_iterations,
        )

        # Enhance with MCP metadata
        rebalance_result["mcp_metadata"] = {
            "tool": "rebalance_encounter",
            "performance_target": "< 300ms",
            "strategy_used": strategy,
            "max_iterations": max_iterations,
            "implementation_status": "partial_implementation",
        }

        logger.info("Encounter rebalancing analysis completed (implementation pending)")
        return rebalance_result

    except (MCPException, ValueError) as e:
        logger.error(f"Encounter rebalancing failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in encounter rebalancing: {e}")
        raise MCPException(
            MCPError(
                message=f"Encounter rebalancing failed: {e}",
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.ERROR,
                source="rebalance_encounter_mcp",
                suggestions=[
                    "Check encounter data format",
                    "Verify rebalancing parameters",
                    "Try with different balancing strategy",
                ],
                data={
                    "target_difficulty": target_difficulty,
                    "party_size": party_size,
                    "party_level": party_level,
                    "strategy": strategy,
                    "operation": "encounter_rebalancing",
                },
            )
        )


# Utility functions for MCP tool registration and validation


def get_encounter_tool_definitions() -> list[dict[str, Any]]:
    """Get MCP tool definitions for encounter building tools.

    Returns:
        List of tool definition dictionaries for MCP registration
    """
    return [
        {
            "name": "calculate_encounter_budget",
            "description": (
                "Calculate DMG-accurate encounter XP budgets for party composition. "
                "Provides complete difficulty analysis with tactical recommendations."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "party_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Number of characters in the party",
                    },
                    "party_level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Average party level",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard", "deadly"],
                        "default": "medium",
                        "description": "Target encounter difficulty",
                    },
                    "individual_levels": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1, "maximum": 20},
                        "description": "Individual character levels for mixed-level parties",
                    },
                },
                "required": ["party_size", "party_level"],
            },
        },
        {
            "name": "search_creatures_for_encounter",
            "description": (
                "Search for creatures suitable for encounter building with "
                "environmental and thematic constraints."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "constraints": {
                        "type": "object",
                        "description": "Creature filtering constraints",
                    },
                    "xp_budget": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Optional XP budget limit for filtering",
                    },
                    "environment": {
                        "type": "string",
                        "description": "Environment type for suitability scoring",
                    },
                    "theme": {
                        "type": "string",
                        "description": "Encounter theme for thematic filtering",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Source books to search",
                    },
                },
                "required": ["constraints"],
            },
        },
        {
            "name": "build_balanced_encounter",
            "description": (
                "Build a complete balanced encounter with DMG-accurate balancing, "
                "environmental considerations, and tactical analysis."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "party_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Number of characters in party",
                    },
                    "party_level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Average party level",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard", "deadly"],
                        "description": "Target difficulty",
                    },
                    "constraints": {
                        "type": "object",
                        "description": "Optional creature filtering constraints",
                    },
                    "environment": {
                        "type": "string",
                        "description": "Optional environment type",
                    },
                    "theme": {
                        "type": "string",
                        "description": "Optional encounter theme",
                    },
                    "individual_levels": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1, "maximum": 20},
                        "description": "Individual character levels for mixed parties",
                    },
                },
                "required": ["party_size", "party_level", "difficulty"],
            },
        },
        {
            "name": "rebalance_encounter",
            "description": (
                "Rebalance an existing encounter to match target difficulty with "
                "iterative optimization and comprehensive analysis."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "encounter_data": {
                        "type": "object",
                        "description": "Current encounter data to rebalance",
                    },
                    "target_difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard", "deadly"],
                        "description": "Desired difficulty level",
                    },
                    "party_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Number of party members",
                    },
                    "party_level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Average party level",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["conservative", "aggressive", "precise", "dynamic"],
                        "default": "precise",
                        "description": "Balancing strategy to use",
                    },
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": "Maximum optimization iterations",
                    },
                },
                "required": [
                    "encounter_data",
                    "target_difficulty",
                    "party_size",
                    "party_level",
                ],
            },
        },
    ]
