"""Encounter building services registration and factories.

This module provides service container integration for the encounter building
system, including protocol definitions, factory functions, and lifecycle
management following the existing service patterns.

Integrates encounter services with the modern service container while maintaining
performance targets and proper dependency management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.models.encounter_types import (
        EncounterConstraints,
        EnvironmentalModifiers,
        PartyComposition,
    )
    from studiorum.core.services.encounter_collector import (
        EncounterCollector,
        EncounterGenerationResult,
    )
    from studiorum.mcp.tools.encounter.balancer import (
        BalanceAnalysis,
        BalanceStrategy,
        EncounterBalancer,
        OptimizationGoal,
    )
    from studiorum.mcp.tools.encounter.themes import (
        EnvironmentalProfile,
        ThematicEncounterGenerator,
        ThematicProfile,
    )

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.services.encounter_collector import EncounterCollector
from studiorum.core.services.protocols import OmnidexerProtocol
from studiorum.mcp.tools.encounter.balancer import EncounterBalancer
from studiorum.mcp.tools.encounter.themes import ThematicEncounterGenerator

logger = get_logger(__name__)


@runtime_checkable
class EncounterCollectorProtocol(Protocol):
    """Protocol for encounter collection services.

    Defines the interface for creature collection and encounter generation
    services with proper typing and performance guarantees.
    """

    def search_creatures_for_encounter(
        self,
        constraints: EncounterConstraints,
        xp_budget: int | None = None,
        environmental_mods: EnvironmentalModifiers | None = None,
    ) -> Any:  # CreatureCollectionResult
        """Search creatures optimized for encounter building."""
        ...

    def generate_balanced_encounter(
        self,
        party: PartyComposition,
        target_difficulty: str,
        constraints: EncounterConstraints,
        environmental_mods: EnvironmentalModifiers | None = None,
    ) -> EncounterGenerationResult:
        """Generate a balanced encounter for given party and constraints."""
        ...

    def rebalance_encounter(
        self,
        current_creatures: list[Any],  # list[EncounterCreature]
        target_difficulty: str,
        party: PartyComposition,
        constraints: EncounterConstraints | None = None,
    ) -> EncounterGenerationResult:
        """Rebalance existing encounter to match target difficulty."""
        ...


@runtime_checkable
class EncounterBalancerProtocol(Protocol):
    """Protocol for encounter balancing services.

    Defines the interface for sophisticated encounter analysis and
    optimization capabilities.
    """

    def analyze_encounter_balance(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        target_difficulty: str,
        environmental_context: EnvironmentalModifiers | None = None,
        narrative_context: dict[str, Any] | None = None,
    ) -> Any:  # BalanceMetrics
        """Perform comprehensive encounter balance analysis."""
        ...

    def rebalance_encounter_optimized(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        target_difficulty: str,
        strategy: BalanceStrategy = ...,  # Default strategy
        optimization_goal: OptimizationGoal | None = None,
        constraints: EncounterConstraints | None = None,
        max_iterations: int = 5,
    ) -> BalanceAnalysis:
        """Perform optimized encounter rebalancing with iterative improvement."""
        ...

    def optimize_for_goal(
        self,
        encounter: EncounterGenerationResult,
        party: PartyComposition,
        optimization_goal: OptimizationGoal,
        constraints: EncounterConstraints | None = None,
    ) -> EncounterGenerationResult | None:
        """Optimize encounter for specific goal while maintaining balance."""
        ...


@runtime_checkable
class ThematicEncounterGeneratorProtocol(Protocol):
    """Protocol for thematic encounter generation services.

    Defines the interface for environment-based and theme-based
    encounter generation with narrative coherence.
    """

    def generate_environmental_encounter(
        self,
        environmental_profile: EnvironmentalProfile,
        encounter_constraints: EncounterConstraints,
        min_suitability: float = 0.7,
    ) -> list[Any]:  # list[EncounterCreature]
        """Generate encounter optimized for specific environment."""
        ...

    def generate_thematic_encounter(
        self,
        thematic_profile: ThematicProfile,
        encounter_constraints: EncounterConstraints,
        min_fit: float = 0.8,
    ) -> list[Any]:  # list[EncounterCreature]
        """Generate encounter matching specific theme."""
        ...

    def generate_themed_environmental_encounter(
        self,
        environmental_profile: EnvironmentalProfile,
        thematic_profile: ThematicProfile,
        encounter_constraints: EncounterConstraints,
        balance_weight: float = 0.5,
    ) -> list[Any]:  # list[EncounterCreature]
        """Generate encounter balancing environmental and thematic considerations."""
        ...


# Service Factory Functions


async def create_encounter_collector_service(
    omnidexer_protocol: OmnidexerProtocol,
) -> EncounterCollector:
    """Create encounter collector service with omnidexer dependency.

    Args:
        omnidexer_protocol: Omnidexer service for content lookup

    Returns:
        Configured encounter collector service
    """
    logger.debug("Creating encounter collector service")

    # Cast protocol to concrete type for service creation
    # The service container ensures the protocol is satisfied
    # Cast the protocol to the concrete type for constructor compatibility
    omnidexer = cast(Omnidexer, omnidexer_protocol)

    encounter_collector = EncounterCollector(omnidexer)

    logger.debug("Encounter collector service created successfully")
    return encounter_collector


async def create_encounter_balancer_service(
    encounter_collector_protocol: EncounterCollectorProtocol,
) -> EncounterBalancer:
    """Create encounter balancer service with encounter collector dependency.

    Args:
        encounter_collector_protocol: Encounter collector service

    Returns:
        Configured encounter balancer service
    """
    logger.debug("Creating encounter balancer service")

    # Cast protocol to concrete type for constructor compatibility
    encounter_collector = cast(EncounterCollector, encounter_collector_protocol)

    encounter_balancer = EncounterBalancer(encounter_collector)

    logger.debug("Encounter balancer service created successfully")
    return encounter_balancer


async def create_thematic_encounter_generator_service(
    encounter_collector_protocol: EncounterCollectorProtocol,
) -> ThematicEncounterGenerator:
    """Create thematic encounter generator service.

    Args:
        encounter_collector_protocol: Encounter collector service

    Returns:
        Configured thematic encounter generator service
    """
    logger.debug("Creating thematic encounter generator service")

    # Cast protocol to concrete type for constructor compatibility
    encounter_collector = cast(EncounterCollector, encounter_collector_protocol)

    thematic_generator = ThematicEncounterGenerator(encounter_collector)

    logger.debug("Thematic encounter generator service created successfully")
    return thematic_generator


# Integration with existing service registration


def register_encounter_services(container: Any) -> None:  # ServiceContainer
    """Register encounter building services with the service container.

    Args:
        container: Modern service container for registration

    This function extends the existing service registration to include
    encounter building capabilities while following established patterns.
    """
    from studiorum.core.services.lifecycle import CleanupPriority, ServiceLifecycle

    logger.info("Registering encounter building services")

    # Encounter Collector - Scoped for request isolation
    # Depends on omnidexer for creature access
    container.register_service(
        EncounterCollectorProtocol,  # type: ignore[type-abstract]
        create_encounter_collector_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(OmnidexerProtocol,),
        hot_reloadable=False,  # No configuration dependencies
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered EncounterCollectorProtocol as scoped service")

    # Encounter Balancer - Scoped for request isolation
    # Depends on encounter collector for balancing operations
    container.register_service(
        EncounterBalancerProtocol,  # type: ignore[type-abstract]
        create_encounter_balancer_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(EncounterCollectorProtocol,),
        hot_reloadable=False,  # No direct configuration dependencies
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered EncounterBalancerProtocol as scoped service")

    # Thematic Encounter Generator - Scoped for request isolation
    # Depends on encounter collector for thematic creature selection
    container.register_service(
        ThematicEncounterGeneratorProtocol,  # type: ignore[type-abstract]
        create_thematic_encounter_generator_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(EncounterCollectorProtocol,),
        hot_reloadable=False,  # No direct configuration dependencies
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered ThematicEncounterGeneratorProtocol as scoped service")

    logger.info("Encounter building services registered successfully")


def get_encounter_service_lifecycle_summary() -> dict[str, dict]:
    """Get lifecycle summary for encounter services.

    Returns:
        Dictionary mapping service names to lifecycle information
    """
    from studiorum.core.services.lifecycle import CleanupPriority

    return {
        "EncounterCollectorProtocol": {
            "lifecycle": "SCOPED",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.REQUEST_SCOPED,
            "rationale": "Per-request encounter generation with creature data access",
            "dependencies": ["OmnidexerProtocol"],
        },
        "EncounterBalancerProtocol": {
            "lifecycle": "SCOPED",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.REQUEST_SCOPED,
            "rationale": "Per-request encounter analysis and optimization",
            "dependencies": ["EncounterCollectorProtocol"],
        },
        "ThematicEncounterGeneratorProtocol": {
            "lifecycle": "SCOPED",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.REQUEST_SCOPED,
            "rationale": "Per-request thematic and environmental encounter generation",
            "dependencies": ["EncounterCollectorProtocol"],
        },
    }


def validate_encounter_service_registration() -> list[str]:
    """Validate encounter service registration for consistency.

    Returns:
        List of validation issues (empty if all valid)
    """
    issues = []
    summary = get_encounter_service_lifecycle_summary()

    # Check that all encounter services are scoped (for MCP request isolation)
    for service_name, info in summary.items():
        if info["lifecycle"] != "SCOPED":
            issues.append(
                f"Encounter service {service_name} should be SCOPED for MCP request isolation, "
                f"but is {info['lifecycle']}"
            )

    # Check dependency chain consistency

    # Validate that balancer depends on collector
    balancer_deps = summary["EncounterBalancerProtocol"]["dependencies"]
    if "EncounterCollectorProtocol" not in balancer_deps:
        issues.append(
            "EncounterBalancerProtocol should depend on EncounterCollectorProtocol"
        )

    # Validate that thematic generator depends on collector
    thematic_deps = summary["ThematicEncounterGeneratorProtocol"]["dependencies"]
    if "EncounterCollectorProtocol" not in thematic_deps:
        issues.append(
            "ThematicEncounterGeneratorProtocol should depend on EncounterCollectorProtocol"
        )

    return issues


# Convenience function for testing and CLI integration


def get_encounter_collector_from_container(container: Any) -> EncounterCollector:
    """Get encounter collector service from container (for testing/CLI).

    Args:
        container: Service container instance

    Returns:
        Encounter collector service instance

    Raises:
        RuntimeError: If service retrieval fails
    """
    try:
        # This would use the actual container API when available
        # For now, create directly for testing
        from studiorum.core.services.encounter_collector import EncounterCollector

        # Get omnidexer from container
        omnidexer_result = container.get_omnidexer()
        if not omnidexer_result.is_success():
            raise RuntimeError(f"Failed to get omnidexer: {omnidexer_result.error}")

        omnidexer = omnidexer_result.unwrap()
        return EncounterCollector(omnidexer)

    except Exception as e:
        logger.error(f"Failed to get encounter collector from container: {e}")
        raise RuntimeError(f"Encounter collector retrieval failed: {e}")
