"""Service registration and configuration for modern dependency injection.

This module handles the registration of all core services with their
appropriate lifecycles, dependencies, and priorities. Provides the
centralized configuration for the entire service container system.

Registration includes:
- Protocol mappings to factory functions
- Lifecycle assignments optimized for each service
- Dependency relationships and injection order
- Hot-reload and cleanup priority configuration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from studiorum.core.logging import get_logger

from .container import ModernServiceContainer
from .factories import (
    create_cache_service,
    create_configuration_service,
    create_content_factory_service,
    create_content_type_registry_service,
    create_display_manager_service,
    create_entry_registry_service,
    create_omnidexer_service,
    create_reference_manager_service,
    create_tag_resolver_service,
)
from .lifecycle import CleanupPriority, ServiceLifecycle
from .protocols import (
    CacheProtocol,
    ConfigurationProtocol,
    ContentFactoryProtocol,
    ContentTypeRegistryProtocol,
    DisplayManagerProtocol,
    EntryTypeRegistryProtocol,
    OmnidexerProtocol,
    ReferenceManagerProtocol,
    TagResolverProtocol,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


async def register_modern_services(container: ModernServiceContainer) -> None:
    """Register all services with modern lifecycle management.

    This function configures the complete service dependency graph with
    optimized lifecycles for both CLI usage and MCP server requirements.

    Service Lifecycle Strategy:
    - Configuration: SINGLETON + HOT_RELOADABLE (shared config with runtime updates)
    - Omnidexer: ASYNC_RESOURCE (expensive async initialization, singleton for performance)
    - TagResolver: SCOPED + HOT_RELOADABLE (per-request rendering context, config updates)
    - DisplayManager: SCOPED + HOT_RELOADABLE (per-request formatting, preference updates)
    - ReferenceManager: SCOPED (per-request reference tracking)
    - ContentTypeRegistry: SINGLETON (static registry, shared optimal)
    - ContentFactory: SINGLETON (stateless factory, shared optimal)
    - EntryRegistry: SINGLETON (static registry, shared optimal)

    Args:
        container: Service container to register services with
    """
    logger.info("Registering modern services with lifecycle management")

    # Configuration (hot-reloadable singleton)
    # Highest priority cleanup to ensure other services can access config during shutdown
    container.register_service(
        ConfigurationProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_configuration_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.CONFIGURATION,
    )
    logger.debug("Registered ConfigurationProtocol as hot-reloadable singleton")

    # Core async resources (singleton for performance, async lifecycle)
    # High priority cleanup after configuration
    container.register_service(
        OmnidexerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_omnidexer_service,
        lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
        dependencies=(ConfigurationProtocol,),
        hot_reloadable=False,  # Could be added in future for source reloading
        cleanup_priority=CleanupPriority.CORE_RESOURCES,
    )
    logger.debug(
        "Registered OmnidexerProtocol as async resource with config dependency"
    )

    # Infrastructure services (singleton for shared state)
    # Medium priority cleanup
    container.register_service(
        ContentTypeRegistryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_type_registry_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered ContentTypeRegistryProtocol as singleton")

    container.register_service(
        ContentFactoryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_factory_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),  # Could depend on ContentTypeRegistryProtocol in future
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered ContentFactoryProtocol as singleton")

    container.register_service(
        EntryTypeRegistryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_entry_registry_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered EntryTypeRegistryProtocol as singleton")

    container.register_service(
        CacheProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_cache_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered CacheProtocol as singleton")

    # Request-scoped services (MCP isolation required)
    # Later cleanup priority to ensure dependencies are available
    container.register_service(
        TagResolverProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_tag_resolver_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(OmnidexerProtocol, ConfigurationProtocol),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered TagResolverProtocol as scoped with hot-reload")

    container.register_service(
        DisplayManagerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_display_manager_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(ConfigurationProtocol,),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.DISPLAY_OUTPUT,
    )
    logger.debug("Registered DisplayManagerProtocol as scoped with hot-reload")

    container.register_service(
        ReferenceManagerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_reference_manager_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(OmnidexerProtocol,),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered ReferenceManagerProtocol as scoped")

    # Encounter building services (Package 2.3)
    # Register after core services are available
    from .encounter_services import register_encounter_services

    register_encounter_services(container)

    # Image processing services (Phase 4 - Service Integration)
    # Register after core services are available
    from .image_services import register_image_services

    register_image_services(container)

    logger.info("Modern service registration completed successfully")


def get_service_lifecycle_summary() -> dict[str, dict]:
    """Get summary of service lifecycle assignments and rationale.

    Returns:
        Dictionary mapping service names to lifecycle information

    Useful for debugging, documentation, and configuration validation.
    """
    from .encounter_services import get_encounter_service_lifecycle_summary

    # Base services
    base_services = {
        "ConfigurationProtocol": {
            "lifecycle": "SINGLETON",
            "hot_reloadable": True,
            "cleanup_priority": CleanupPriority.CONFIGURATION,
            "rationale": "Shared configuration with runtime hot-reload capability",
            "dependencies": [],
        },
        "OmnidexerProtocol": {
            "lifecycle": "ASYNC_RESOURCE",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.CORE_RESOURCES,
            "rationale": "Expensive async initialization (GitHub sources), singleton for performance",
            "dependencies": ["ConfigurationProtocol"],
        },
        "TagResolverProtocol": {
            "lifecycle": "SCOPED",
            "hot_reloadable": True,
            "cleanup_priority": CleanupPriority.REQUEST_SCOPED,
            "rationale": "Per-request rendering context, supports rendering config updates",
            "dependencies": ["OmnidexerProtocol", "ConfigurationProtocol"],
        },
        "DisplayManagerProtocol": {
            "lifecycle": "SCOPED",
            "hot_reloadable": True,
            "cleanup_priority": CleanupPriority.DISPLAY_OUTPUT,
            "rationale": "Per-request output formatting, supports display preference updates",
            "dependencies": ["ConfigurationProtocol"],
        },
        "ReferenceManagerProtocol": {
            "lifecycle": "SCOPED",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.REQUEST_SCOPED,
            "rationale": "Per-request reference tracking and cross-reference resolution",
            "dependencies": ["OmnidexerProtocol"],
        },
        "ContentTypeRegistryProtocol": {
            "lifecycle": "SINGLETON",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.INFRASTRUCTURE,
            "rationale": "Static content type registry, sharing is optimal",
            "dependencies": [],
        },
        "ContentFactoryProtocol": {
            "lifecycle": "SINGLETON",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.INFRASTRUCTURE,
            "rationale": "Stateless content factory, sharing is optimal",
            "dependencies": [],
        },
        "EntryTypeRegistryProtocol": {
            "lifecycle": "SINGLETON",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.INFRASTRUCTURE,
            "rationale": "Static entry type registry, sharing is optimal",
            "dependencies": [],
        },
        "CacheProtocol": {
            "lifecycle": "SINGLETON",
            "hot_reloadable": False,
            "cleanup_priority": CleanupPriority.INFRASTRUCTURE,
            "rationale": "Shared cache for performance optimization, singleton for efficiency",
            "dependencies": [],
        },
    }

    # Combine base services with encounter services
    encounter_services = get_encounter_service_lifecycle_summary()
    return {**base_services, **encounter_services}


def validate_service_registration() -> list[str]:
    """Validate service registration configuration for consistency.

    Returns:
        List of validation warnings/errors (empty if all valid)
    """
    from .encounter_services import validate_encounter_service_registration

    issues = []
    summary = get_service_lifecycle_summary()

    # Add encounter service validation
    encounter_issues = validate_encounter_service_registration()
    issues.extend(encounter_issues)

    # Check dependency order vs cleanup priority
    for service_name, info in summary.items():
        service_priority = info["cleanup_priority"]

        for dep_name in info["dependencies"]:
            if dep_name in summary:
                dep_priority = summary[dep_name]["cleanup_priority"]

                # Dependencies should be cleaned up after dependents
                if dep_priority > service_priority:
                    issues.append(
                        f"{service_name} (priority {service_priority}) depends on "
                        f"{dep_name} (priority {dep_priority}) - dependency will be "
                        f"cleaned up before dependent"
                    )

    # Check hot-reload compatibility
    hot_reloadable_services = [
        name for name, info in summary.items() if info["hot_reloadable"]
    ]

    if hot_reloadable_services:
        logger.debug(f"Hot-reloadable services: {hot_reloadable_services}")

    # Check scoped service dependencies
    scoped_services = [
        name for name, info in summary.items() if info["lifecycle"] == "SCOPED"
    ]

    for service_name in scoped_services:
        info = summary[service_name]
        for dep_name in info["dependencies"]:
            if dep_name in summary:
                dep_info = summary[dep_name]
                if dep_info["lifecycle"] == "SCOPED":
                    issues.append(
                        f"Scoped service {service_name} depends on another "
                        f"scoped service {dep_name} - this may cause issues "
                        f"with request isolation"
                    )

    return issues


# Service factory validation


def validate_all_factories() -> list[str]:
    """Validate that all service factories are properly configured.

    Returns:
        List of validation issues (empty if all valid)
    """
    issues = []

    # Check that all protocols have corresponding factories
    protocol_classes = [
        ConfigurationProtocol,
        OmnidexerProtocol,
        TagResolverProtocol,
        DisplayManagerProtocol,
        ReferenceManagerProtocol,
        ContentTypeRegistryProtocol,
        ContentFactoryProtocol,
        EntryTypeRegistryProtocol,
        CacheProtocol,
    ]

    factory_functions = [
        create_configuration_service,
        create_omnidexer_service,
        create_tag_resolver_service,
        create_display_manager_service,
        create_reference_manager_service,
        create_content_type_registry_service,
        create_content_factory_service,
        create_entry_registry_service,
        create_cache_service,
    ]

    if len(protocol_classes) != len(factory_functions):
        issues.append(
            f"Mismatch between protocols ({len(protocol_classes)}) "
            f"and factories ({len(factory_functions)})"
        )

    # Validate factory function signatures
    import inspect

    for factory in factory_functions:
        from collections.abc import Callable
        from typing import cast

        sig = inspect.signature(cast(Callable, factory))

        # Check if factory is async
        if not inspect.iscoroutinefunction(factory):
            issues.append(f"Factory {factory.__name__} should be async")

        # Check parameter count for container dependency
        param_count = len(sig.parameters)
        if param_count > 1:
            issues.append(
                f"Factory {factory.__name__} has {param_count} parameters, "
                f"expected 0 or 1 (container)"
            )

    return issues
