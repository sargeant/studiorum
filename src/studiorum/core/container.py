"""Dependency injection container for managing application services.

This module provides a centralized service container that manages the lifecycle
of core application components, replacing global singletons with proper
dependency injection.

This is now a minimal compatibility layer that delegates to the modern service container.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.services.container import ServiceContainer

from studiorum.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ServiceError,
)
from studiorum.core.result import Error, Result, Success

logger = get_logger(__name__)


# Global container instance
_global_container: ServiceContainer | None = None


def get_global_container() -> ServiceContainer:
    """Get the global service container instance.

    This provides a global container for CLI usage while still allowing
    dependency injection in tests and other contexts.

    Returns:
        The global service container instance
    """
    global _global_container
    if _global_container is None:
        from studiorum.core.services.container import ServiceContainer

        _global_container = ServiceContainer()

        # Try to register services automatically when possible
        _try_register_services(_global_container)

    return _global_container


def _try_register_services(container: ServiceContainer) -> None:
    """Try to register services automatically if possible."""
    try:
        import asyncio

        from studiorum.core.services.registration import register_modern_services

        # Only register if no services are registered yet
        if len(container.get_registered_services()) > 0:
            return

        try:
            # Try without an event loop first
            asyncio.get_running_loop()
            logger.debug(
                "Event loop running, services must be registered manually with ensure_services_registered()"
            )
        except RuntimeError:
            # No running loop - try sync registration first
            try:
                _register_services_sync(container)
                logger.debug("Global container services registered synchronously")
            except Exception as sync_error:
                logger.warning(
                    f"Sync registration failed: {sync_error}, falling back to async"
                )
                # Fallback to async registration
                asyncio.run(register_modern_services(container))
                logger.debug(
                    "Global container services registered successfully (async fallback)"
                )
    except Exception as e:
        logger.warning(f"Failed to register services in global container: {e}")


def _register_services_sync(container: ServiceContainer) -> None:
    """Register services synchronously for CLI contexts.

    This provides a sync alternative to avoid event loop creation during
    container initialization for CLI usage.
    """
    from studiorum.core.services.factories import (
        create_cache_service,
        create_configuration_service_sync,
        create_content_attribution_service,
        create_content_factory_service,
        create_content_type_registry_service,
        create_data_source_manager_service,
        create_display_manager_service,
        create_entry_registry_service,
        create_omnidexer_service_sync,
        create_reference_manager_service,
        create_tag_resolver_service,
    )
    from studiorum.core.services.lifecycle import CleanupPriority, ServiceLifecycle
    from studiorum.core.services.protocols import (
        CacheProtocol,
        ConfigurationProtocol,
        ContentAttributionProtocol,
        ContentFactoryProtocol,
        ContentTypeRegistryProtocol,
        DisplayManagerProtocol,
        EntryTypeRegistryProtocol,
        OmnidexerProtocol,
        ReferenceManagerProtocol,
        SourceManagerProtocol,
        TagResolverProtocol,
    )

    # Register services without creating instances
    # Service registration is synchronous - only service creation can be async

    # Configuration (hot-reloadable singleton)
    container.register_service(
        ConfigurationProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_configuration_service_sync,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.CONFIGURATION,
    )

    # Source management services
    container.register_service(
        SourceManagerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_data_source_manager_service,
        lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
        dependencies=(ConfigurationProtocol,),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    container.register_service(
        ContentAttributionProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_attribution_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    # Core data service (omnidexer with sync initialization for CLI)
    container.register_service(
        OmnidexerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_omnidexer_service_sync,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(ConfigurationProtocol,),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.CORE_RESOURCES,
    )

    # Registry and factory services (lightweight singletons)
    container.register_service(
        ContentTypeRegistryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_type_registry_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    container.register_service(
        ContentFactoryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_content_factory_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    container.register_service(
        EntryTypeRegistryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_entry_registry_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    # Request-scoped services with hot-reload support
    container.register_service(
        TagResolverProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_tag_resolver_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(OmnidexerProtocol, ConfigurationProtocol),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )

    # Display and output services (cleaned up last)
    container.register_service(
        DisplayManagerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_display_manager_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.DISPLAY_OUTPUT,
    )

    container.register_service(
        ReferenceManagerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_reference_manager_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )

    # Infrastructure services
    container.register_service(
        CacheProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_cache_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    logger.debug("Services registered synchronously (descriptors only)")


async def ensure_services_registered() -> None:
    """Ensure services are registered in the global container.

    This should be called in async contexts to ensure services are available.
    """
    global _global_container
    if _global_container is None:
        _global_container = get_global_container()

    # Register services if not already registered
    if len(_global_container.get_registered_services()) == 0:
        from studiorum.core.services.registration import register_modern_services

        await register_modern_services(_global_container)
        logger.debug("Services registered in async context")


def reset_global_container() -> None:
    """Reset the global service container for testing.

    This properly closes the existing container and creates a new one,
    ensuring complete cleanup of all cached services and their resources.
    Used primarily for test isolation.
    """
    global _global_container
    if _global_container is not None:
        try:
            # Always run cleanup synchronously to avoid threading issues
            # Fire-and-forget tasks during teardown can cause infinite loops
            asyncio.run(_global_container.cleanup())
        except Exception as e:
            logger.warning(f"Error during container cleanup: {e}")
    _global_container = None


def reset_all_services() -> None:
    """Reset all services managed by the container and other global state.

    This is a comprehensive reset function for tests that ensures complete
    isolation by resetting both container services and other global singletons.
    """
    reset_global_container()

    # Reset other global state that may not be in the container yet
    # Note: PathConfig was removed in P4, no path-specific reset needed

    try:
        from studiorum.core.config.unified_config import reset_app_config

        reset_app_config()
    except ImportError:
        pass

    # Reset any other global state
    try:
        from studiorum.core.cache import CacheManager

        # Reset the cache manager completely
        CacheManager.reset()
    except (ImportError, AttributeError):
        # Cache system may not exist in all configurations
        pass


async def create_mcp_request_container(
    base_config: Any, request_overrides: dict | None = None
) -> Any:
    """Create MCP request container with configuration overrides.

    Args:
        base_config: Base application configuration
        request_overrides: Request-specific configuration overrides

    Returns:
        Request-scoped container with configuration overrides
    """
    from studiorum.core.services.container import (
        create_mcp_request_container as _create_mcp_container,
    )

    return await _create_mcp_container(base_config, request_overrides)


def reload_global_configuration() -> None:
    """Reload global configuration and recreate container."""
    reset_global_container()


def cleanup_global_container() -> None:
    """Clean up the global container."""
    reset_global_container()


@contextmanager
def service_container_for_testing() -> Iterator[ServiceContainer]:
    """Context manager that provides a fresh container for testing.

    This ensures test isolation by creating a new container instance
    and properly cleaning up afterward.

    Yields:
        A fresh service container instance
    """
    # Store current container
    global _global_container
    original_container = _global_container

    # Create fresh container
    from studiorum.core.services.container import ServiceContainer

    _global_container = ServiceContainer()

    try:
        yield _global_container
    finally:
        # Clean up test container
        if _global_container is not None:
            try:
                asyncio.run(_global_container.cleanup())
            except Exception as e:
                logger.warning(f"Error during test container cleanup: {e}")

        # Restore original container
        _global_container = original_container
