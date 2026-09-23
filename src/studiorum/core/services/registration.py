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

from .container import ServiceContainer
from .factories import (
    create_cache_service,
    create_configuration_service,
    create_content_attribution_service,
    create_content_factory_service,
    create_content_list_writer_service,
    create_content_type_registry_service,
    create_data_source_manager_service,
    create_display_manager_service,
    create_entry_registry_service,
    create_fluff_deduplicator_service,
    create_omnidexer_service,
    create_reference_manager_service,
    create_tag_resolver_service,
)
from .lifecycle import CleanupPriority, ServiceLifecycle
from .protocols import (
    CacheProtocol,
    ConfigurationProtocol,
    ContentAttributionProtocol,
    ContentFactoryProtocol,
    ContentListWriterProtocol,
    ContentTypeRegistryProtocol,
    DisplayManagerProtocol,
    EntryTypeRegistryProtocol,
    FluffDeduplicatorProtocol,
    OmnidexerProtocol,
    ReferenceManagerProtocol,
    SourceManagerProtocol,
    TagResolverProtocol,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


async def register_modern_services(container: ServiceContainer) -> None:
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

    # Source management services (infrastructure for content loading)
    # Register before omnidexer as it depends on these services
    container.register_service(
        SourceManagerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_data_source_manager_service,
        lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
        dependencies=(ConfigurationProtocol,),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered SourceManagerProtocol as async resource")

    container.register_service(
        ContentAttributionProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_attribution_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered ContentAttributionProtocol as singleton")

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

    # Fluff services (Phase 4 - Fluff Deduplication)
    # Register after core services are available
    container.register_service(
        FluffDeduplicatorProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_fluff_deduplicator_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(),  # Can be enhanced later to depend on ContentTracker
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered FluffDeduplicatorProtocol as scoped")

    # Content list writer service (utility service)
    # Register as singleton since it's stateless
    container.register_service(
        ContentListWriterProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_list_writer_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered ContentListWriterProtocol as singleton")

    # Encounter building services (Package 2.3)
    # Register after core services are available
    from .encounter_services import register_encounter_services

    register_encounter_services(container)

    logger.info("Modern service registration completed successfully")
