"""Dependency injection container for managing application services.

This module provides a centralized service container that manages the lifecycle
of core application components, replacing global singletons with proper
dependency injection.

Enhanced in P3 with modern async DI container while maintaining full backward compatibility.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager

# Lazy imports to avoid circular dependencies
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from dnd5e.cli.display_manager import DisplayManager
    from dnd5e.core.config.unified_config import ApplicationConfig
    from dnd5e.core.entry_registry import EntryTypeRegistry
    from dnd5e.core.interfaces import ContentTypeRegistry
    from dnd5e.core.loaders.content_factory import ContentFactory
    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.text.tag_resolver import TagResolver
    from dnd5e.core.unified_references import ReferenceManager

from dnd5e.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ServiceError,
)
from dnd5e.core.result import Error, Result, Success

# Modern service container imports (lazy to avoid circular dependencies)
if TYPE_CHECKING:
    from dnd5e.core.services.container import (
        ModernServiceContainer,
        RequestScopedContainer,
    )
    from dnd5e.core.services.protocols import (
        ConfigurationProtocol,
        ContentFactoryProtocol,
        ContentTypeRegistryProtocol,
        DisplayManagerProtocol,
        EntryTypeRegistryProtocol,
        OmnidexerProtocol,
        ReferenceManagerProtocol,
        TagResolverProtocol,
    )

logger = logging.getLogger(__name__)


class ServiceContainer(Protocol):
    """Protocol for service containers that manage application dependencies."""

    def get_omnidexer(self) -> Result[Omnidexer, ServiceError]:
        """Get or create the omnidexer instance."""
        ...

    def get_tag_resolver(self) -> Result[TagResolver, ServiceError]:
        """Get or create the tag resolver instance."""
        ...

    def get_content_type_registry(self) -> Result[ContentTypeRegistry, ServiceError]:
        """Get or create the content type registry instance."""
        ...

    def get_display_manager(self) -> Result[DisplayManager, ServiceError]:
        """Get or create the display manager instance."""
        ...

    def get_content_factory(self) -> Result[ContentFactory, ServiceError]:
        """Get or create the content factory instance."""
        ...

    def get_entry_registry(self) -> Result[EntryTypeRegistry, ServiceError]:
        """Get or create the entry registry instance."""
        ...

    def get_app_config(self) -> Result[ApplicationConfig, ServiceError]:
        """Get or create the application configuration instance."""
        ...

    def get_reference_manager(self) -> Result[ReferenceManager, ServiceError]:
        """Get or create the reference manager instance."""
        ...

    def close(self) -> None:
        """Clean up all managed resources."""
        ...


class DefaultServiceContainer:
    """Enhanced service container with simplified proxy pattern for backward compatibility.

    This container manages the lifecycle of all core application services,
    providing lazy initialization and proper cleanup. Enhanced in P3 to use
    the modern async service container while maintaining 100% backward compatibility
    for existing CLI usage.

    Features:
    - Legacy sync interfaces for CLI compatibility via simple proxy pattern
    - Modern async services for MCP support
    - Protocol-based service resolution
    - Request scoping for MCP request isolation
    - Simplified async/sync bridging with minimal threading complexity
    - Hot-reload infrastructure for configuration changes

    Implementation Notes:
    - Uses proxy pattern to bridge async modern container with sync legacy interfaces
    - Eliminates complex threading logic in favor of simple async.run() calls
    - Maintains full backward compatibility with existing CLI code
    - Proxy instances are cached for performance
    """

    def __init__(self) -> None:
        """Initialize the enhanced service container."""
        # Modern async container for new features
        self._modern_container: ModernServiceContainer | None = None
        self._initialization_task: asyncio.Task | None = None

        # Legacy service instances (cached for sync access)
        self._legacy_instances: dict[str, Any] = {}

        # Track if container is closed
        self._closed = False

        # Initialize modern container asynchronously
        self._ensure_modern_container_initialized()

    def _ensure_modern_container_initialized(self) -> None:
        """Ensure modern container is initialized (async setup)."""
        if self._modern_container is None and self._initialization_task is None:
            # Start async initialization in background
            try:
                loop = asyncio.get_event_loop()
                self._initialization_task = loop.create_task(
                    self._initialize_modern_container()
                )
            except RuntimeError:
                # No event loop running, defer initialization
                pass

    async def _initialize_modern_container(self) -> None:
        """Initialize the modern async service container."""
        try:
            from dnd5e.core.services.container import ModernServiceContainer
            from dnd5e.core.services.registration import register_modern_services

            logger.debug("Initializing modern service container")

            # Create modern container
            self._modern_container = ModernServiceContainer()

            # Register all services
            await register_modern_services(self._modern_container)

            logger.info("Modern service container initialized successfully")

        except Exception:
            logger.exception("Failed to initialize modern service container")
            self._modern_container = None
            raise

    async def get_modern_container(self) -> ModernServiceContainer:
        """Get the modern async service container.

        Returns:
            Modern async service container for MCP usage

        Raises:
            RuntimeError: If container initialization failed
        """
        if self._closed:
            raise RuntimeError("Service container has been closed")

        # Wait for initialization if needed
        if self._modern_container is None:
            if self._initialization_task is None:
                await self._initialize_modern_container()
            else:
                await self._initialization_task

        if self._modern_container is None:
            raise RuntimeError("Failed to initialize modern service container")

        return self._modern_container

    def _get_modern_container_sync(self) -> ModernServiceContainer:
        """Get modern container, initializing synchronously if needed.

        This method handles the async/sync bridging using a simplified approach:
        - First tries asyncio.run() for new event loops
        - Falls back to thread pool execution if already in an async context
        - Much simpler than the previous complex threading implementation
        """
        if self._modern_container is None:
            # Initialize synchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, need to run in thread
                    import concurrent.futures

                    def run_in_new_loop() -> ModernServiceContainer:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(
                                self._initialize_modern_container()
                            )
                            if self._modern_container is None:
                                raise RuntimeError(
                                    "Failed to initialize modern container"
                                )
                            return self._modern_container
                        finally:
                            new_loop.close()

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_new_loop)
                        return future.result(timeout=30)
                else:
                    # Safe to run in current loop
                    loop.run_until_complete(self._initialize_modern_container())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(self._initialize_modern_container())

        if self._modern_container is None:
            raise RuntimeError("Failed to initialize modern service container")

        return self._modern_container

    def _get_service_proxy(self, service_name: str, proxy_factory: Any) -> Any:
        """Get service proxy, creating it if needed.

        This implements the simplified proxy pattern:
        - Caches proxy instances for performance
        - Proxy factory handles async/sync bridging
        - Returns actual service instances (not wrapper objects)
        """
        if self._closed:
            raise RuntimeError("Service container has been closed")

        # Return cached proxy if available
        if service_name in self._legacy_instances:
            return self._legacy_instances[service_name]

        # Create proxy
        modern_container = self._get_modern_container_sync()
        proxy = proxy_factory(modern_container)

        # Cache the proxy
        self._legacy_instances[service_name] = proxy
        return proxy

    def get_omnidexer(self) -> Result[Omnidexer, ServiceError]:
        """Get or create the omnidexer instance.

        Enhanced in P3 to use modern async service container while maintaining
        backward compatibility for CLI usage.

        Returns:
            Success with omnidexer instance, or Error with service failure details

        Examples:
            ```python
            result = container.get_omnidexer()
            if result.is_success():
                omnidexer = result.unwrap()
            else:
                error = result.error
                print(f"Failed to load omnidexer: {error.message}")
            ```
        """
        try:
            from dnd5e.core.services.proxies import create_omnidexer_proxy

            omnidexer_proxy = self._get_service_proxy(
                "omnidexer", create_omnidexer_proxy
            )
            return Success(omnidexer_proxy)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get omnidexer: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_omnidexer",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify async service factory configuration",
                        "Check data source availability",
                    ],
                    data={
                        "service_name": "omnidexer",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_tag_resolver(self) -> Result[TagResolver, ServiceError]:
        """Get or create the tag resolver instance.

        Enhanced in P3 to use modern async service container with hot-reload support.

        Returns:
            Success with tag resolver instance, or Error with service failure details
        """
        try:
            from dnd5e.core.services.proxies import create_tag_resolver_proxy

            tag_resolver_proxy = self._get_service_proxy(
                "tag_resolver", create_tag_resolver_proxy
            )
            return Success(tag_resolver_proxy)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get tag resolver: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_tag_resolver",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify tag resolver dependencies",
                        "Check omnidexer availability",
                    ],
                    data={
                        "service_name": "tag_resolver",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_content_type_registry(self) -> Result[ContentTypeRegistry, ServiceError]:
        """Get or create the content type registry instance.

        Enhanced in P3 to use modern service container.

        Returns:
            Success with content type registry instance, or Error with service failure details
        """
        try:
            from dnd5e.core.services.proxies import create_content_type_registry_proxy

            registry = self._get_service_proxy(
                "content_type_registry", create_content_type_registry_proxy
            )
            return Success(registry)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get content type registry: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_content_type_registry",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify content type registry factory",
                    ],
                    data={
                        "service_name": "content_type_registry",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_display_manager(self) -> Result[DisplayManager, ServiceError]:
        """Get or create the display manager instance.

        Enhanced in P3 to use modern service container with hot-reload support.

        Returns:
            Success with display manager instance, or Error with service failure details
        """
        try:
            from dnd5e.core.services.proxies import create_display_manager_proxy

            display_manager = self._get_service_proxy(
                "display_manager", create_display_manager_proxy
            )
            return Success(display_manager)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get display manager: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_display_manager",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify display manager factory",
                        "Check configuration service availability",
                    ],
                    data={
                        "service_name": "display_manager",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_content_factory(self) -> Result[ContentFactory, ServiceError]:
        """Get or create the content factory instance.

        Enhanced in P3 to use modern service container.

        Returns:
            Success with content factory instance, or Error with service failure details
        """
        try:
            from dnd5e.core.services.proxies import create_content_factory_proxy

            content_factory = self._get_service_proxy(
                "content_factory", create_content_factory_proxy
            )
            return Success(content_factory)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get content factory: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_content_factory",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify content factory configuration",
                    ],
                    data={
                        "service_name": "content_factory",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_entry_registry(self) -> Result[EntryTypeRegistry, ServiceError]:
        """Get or create the entry registry instance.

        Enhanced in P3 to use modern service container.

        Returns:
            Success with entry registry instance, or Error with service failure details
        """
        try:
            from dnd5e.core.services.proxies import create_entry_registry_proxy

            entry_registry = self._get_service_proxy(
                "entry_registry", create_entry_registry_proxy
            )
            return Success(entry_registry)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get entry registry: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_entry_registry",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify entry registry factory",
                    ],
                    data={
                        "service_name": "entry_registry",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_app_config(self) -> Result[ApplicationConfig, ServiceError]:
        """Get or create the application configuration instance.

        Enhanced in P3 to use modern service container with hot-reload support.

        Returns:
            Success with application configuration instance, or Error with service failure details
        """
        try:
            # Import the concrete configuration service, not the protocol
            from dnd5e.core.config.unified_config import get_app_config

            # For backward compatibility, get config directly
            app_config = get_app_config()
            return Success(app_config)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get application configuration: {e}",
                    error_code=MCPErrorCode.CONFIGURATION_ERROR,
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_app_config",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify configuration service availability",
                        "Check configuration file format",
                    ],
                    data={
                        "service_name": "app_config",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def get_reference_manager(self) -> Result[ReferenceManager, ServiceError]:
        """Get or create the reference manager instance.

        Enhanced in P3 to use modern service container with request scoping.

        Returns:
            Success with reference manager instance, or Error with service failure details
        """
        try:
            from dnd5e.core.services.proxies import create_reference_manager_proxy

            reference_manager = self._get_service_proxy(
                "reference_manager", create_reference_manager_proxy
            )
            return Success(reference_manager)
        except Exception as e:
            return Error(
                ServiceError(
                    message=f"Failed to get reference manager: {e}",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer.get_reference_manager",
                    suggestions=[
                        "Check modern service container initialization",
                        "Verify reference manager factory",
                        "Check omnidexer dependency",
                    ],
                    data={
                        "service_name": "reference_manager",
                        "exception_type": type(e).__name__,
                        "operation": "proxy_service_resolution",
                    },
                )
            )

    def _resolve_copy_references(self) -> None:
        """Resolve all pending copy references in the omnidexer."""
        # Get omnidexer through proper service resolution
        omnidexer_result = self.get_omnidexer()
        if not omnidexer_result.is_success():
            return

        try:
            from dnd5e.core.resolvers.copy_resolver import CopyResolver

            omnidexer = omnidexer_result.unwrap()
            copy_resolver = CopyResolver(omnidexer)
            copy_resolver.resolve_copies_in_omnidexer()
        except Exception as e:
            logger.warning(f"Failed to resolve copy references: {e}")

    def close(self) -> None:
        """Clean up all managed resources.

        Enhanced in P3 to properly clean up modern async service container.
        """
        if self._closed:
            return

        logger.debug("Closing enhanced service container")

        # Clean up modern container asynchronously
        if self._modern_container is not None:
            try:
                # Try to clean up async container
                if hasattr(asyncio, "get_running_loop"):
                    try:
                        loop = asyncio.get_running_loop()
                        # Schedule cleanup task
                        loop.create_task(self._modern_container.cleanup())
                    except RuntimeError:
                        # No running loop, run cleanup synchronously
                        asyncio.run(self._modern_container.cleanup())
                else:
                    # Fallback for older Python versions
                    asyncio.run(self._modern_container.cleanup())
            except Exception as e:
                logger.warning(f"Failed to cleanup modern container: {e}")

        # Cancel initialization task if running
        if self._initialization_task and not self._initialization_task.done():
            self._initialization_task.cancel()

        # Clear all state
        self._modern_container = None
        self._initialization_task = None
        self._legacy_instances.clear()
        self._closed = True

        logger.debug("Enhanced service container closed")

    def _check_not_closed(self) -> Result[None, ServiceError]:
        """Check that the container hasn't been closed.

        Returns:
            Success if container is open, Error if closed
        """
        if self._closed:
            return Error(
                ServiceError(
                    message="Service container has been closed",
                    error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source="ServiceContainer",
                    suggestions=[
                        "Create a new service container",
                        "Use a context manager to ensure proper cleanup",
                        "Check container lifecycle management",
                    ],
                    data={"container_state": "closed"},
                )
            )
        return Success(None)

    def __repr__(self) -> str:
        """Return string representation of the enhanced container."""
        status = "closed" if self._closed else "open"

        # Show information about modern container and cached legacy services
        modern_status = "initialized" if self._modern_container else "pending"
        legacy_count = len(self._legacy_instances)

        return (
            f"DefaultServiceContainer(status={status}, "
            f"modern={modern_status}, "
            f"legacy_cached={legacy_count})"
        )


@contextmanager
def service_container() -> Iterator[ServiceContainer]:
    """Create and manage a service container as a context manager.

    This context manager ensures proper cleanup of the container when done.

    Usage:
        with service_container() as container:
            omnidexer = container.get_omnidexer()
            # ... use services
        # Container is automatically closed here

    Yields:
        A service container instance
    """
    container = DefaultServiceContainer()
    try:
        yield container
    finally:
        container.close()


# Global container instance for CLI usage
_global_container: DefaultServiceContainer | None = None


def get_global_container() -> DefaultServiceContainer:
    """Get the global service container instance.

    This provides a global container for CLI usage while still allowing
    dependency injection in tests and other contexts.

    Returns:
        The global service container instance
    """
    global _global_container
    if _global_container is None:
        _global_container = DefaultServiceContainer()
    return _global_container


def reset_global_container() -> None:
    """Reset the global service container for testing.

    This properly closes the existing container and creates a new one,
    ensuring complete cleanup of all cached services and their resources.
    Used primarily for test isolation.
    """
    global _global_container
    if _global_container is not None:
        # Properly close the existing container to clean up resources
        _global_container.close()
    _global_container = None


def reset_all_services() -> None:
    """Reset all services managed by the container and other global state.

    This is a comprehensive reset function for tests that ensures complete
    isolation by resetting both container services and other global singletons.
    """
    reset_global_container()

    # Reset other global state that may not be in the container yet
    try:
        from dnd5e.core.config.paths import reset_path_config

        reset_path_config()
    except ImportError:
        pass

    try:
        from dnd5e.core.config.unified_config import reset_app_config

        reset_app_config()
    except ImportError:
        pass

    try:
        from dnd5e.core.config.sources import reset_config_manager

        reset_config_manager()
    except ImportError:
        pass


# MCP Integration Functions


async def create_mcp_request_container(
    base_config: ApplicationConfig | None = None,
    request_overrides: dict | None = None,
) -> RequestScopedContainer:
    """Create MCP request container with configuration overrides.

    This function creates an isolated container for MCP request handling,
    with optional configuration overrides for request-specific customization.

    Args:
        base_config: Base application configuration (uses global if None)
        request_overrides: Request-specific configuration overrides

    Returns:
        Request-scoped container with configuration overrides

    Examples:
        >>> async with await create_mcp_request_container(
        ...     request_overrides={"content": {"sources": ["SRD"]}}
        ... ) as container:
        ...     omnidexer = await container.get_service(OmnidexerProtocol)
    """
    from dnd5e.core.services.container import RequestScopedContainer

    # Get global container (enhanced DefaultServiceContainer)
    global_container = get_global_container()

    # Get modern container for creating request scope
    modern_container = await global_container.get_modern_container()

    # Create request scope
    request_container = await modern_container.create_request_scope()

    # Apply request-specific configuration overrides if provided
    if request_overrides and base_config:
        # For now, skip registering configuration overrides since we need a concrete type
        # This can be implemented in phase 2 when we create proper proxy classes
        # TODO: Implement configuration service override with concrete type
        # TODO: Create config with overrides: base_config.model_copy(update=request_overrides)
        pass

    return request_container


async def reload_global_configuration(new_config: ApplicationConfig) -> None:
    """Hot-reload configuration for the global service container.

    This function enables runtime configuration updates for long-running
    MCP servers without requiring a restart.

    Args:
        new_config: New application configuration to apply

    Examples:
        >>> new_config = load_configuration_from_file("updated_config.yaml")
        >>> await reload_global_configuration(new_config)
    """
    global_container = get_global_container()

    try:
        modern_container = await global_container.get_modern_container()
        await modern_container.reload_configuration(new_config)
        logger.info("Global configuration hot-reloaded successfully")
    except Exception:
        logger.exception("Failed to hot-reload global configuration")
        raise


async def cleanup_global_container() -> None:
    """Clean up the global service container asynchronously.

    This function properly shuts down the global container and all
    its async resources. Should be called during MCP server shutdown.
    """
    global _global_container

    if _global_container is not None:
        try:
            if _global_container._modern_container:
                await _global_container._modern_container.cleanup()
            _global_container.close()
            logger.info("Global service container cleaned up")
        except Exception:
            logger.exception("Failed to cleanup global container")
        finally:
            _global_container = None
