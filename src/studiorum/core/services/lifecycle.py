"""Service lifecycle management for modern dependency injection.

This module provides the infrastructure for managing service lifecycles,
dependencies, and async resource management. Supports 5 lifecycle patterns
optimized for different service characteristics and MCP requirements.

Key components:
- ServiceLifecycle: Enum defining 5 lifecycle patterns
- ServiceDescriptor: Complete service metadata with dependencies
- AsyncServiceFactory: Protocol for async service creation
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

if TYPE_CHECKING:
    from .container import ServiceContainer

T = TypeVar("T")


class ServiceLifecycle(Enum):
    """Advanced service lifecycle management patterns.

    These lifecycle patterns provide fine-grained control over service
    creation, sharing, and cleanup to optimize performance and resource
    usage while supporting MCP request isolation requirements.
    """

    SINGLETON = "singleton"
    """Shared across all scopes and requests.

    Best for: Expensive-to-create services that are stateless or
    have shared state (e.g., ContentTypeRegistry, ContentFactory).
    Memory: Single instance for entire application lifetime.
    Thread safety: Must be thread-safe for concurrent access.
    """

    SCOPED = "scoped"
    """Per-request instance for isolation.

    Best for: Services that need request-specific state or configuration
    (e.g., TagResolver with rendering context, DisplayManager with
    request-specific formatting).
    Memory: One instance per request scope.
    Thread safety: No sharing between requests, so thread safety not required.
    """

    TRANSIENT = "transient"
    """New instance every time requested.

    Best for: Lightweight, stateless services where instance creation
    is cheap and sharing provides no benefit.
    Memory: New instance for each get_service() call.
    Thread safety: No sharing, so thread safety not required.
    """

    ASYNC_RESOURCE = "async_resource"
    """Requires async initialization and cleanup.

    Best for: Services that need async setup like network connections,
    file handles, or GitHub repository cloning (e.g., Omnidexer).
    Memory: Managed lifecycle with proper async cleanup.
    Thread safety: Depends on implementation, usually singleton pattern.
    """

    HOT_RELOADABLE = "hot_reloadable"
    """Supports configuration hot-reload without restart.

    Best for: Services that can update their configuration at runtime
    (e.g., ConfigurationService, TagResolver with rendering config).
    Memory: Usually singleton or scoped with reload capabilities.
    Thread safety: Must handle concurrent access during reload.
    """


@dataclass(frozen=True)
class ServiceDescriptor[T]:
    """Complete service descriptor with modern DI metadata.

    Provides all information needed for the container to properly
    manage a service's lifecycle, dependencies, and cleanup.
    """

    protocol: type[T]
    """Protocol interface that the service implements."""

    factory: (
        Callable[[], T]
        | Callable[[], Awaitable[T]]
        | Callable[[ServiceContainer], T]
        | Callable[[ServiceContainer], Awaitable[T]]
        | AsyncServiceFactory[T]
    )
    """Factory function or class for creating service instances.

    Can be:
    - Simple callable: () -> T
    - Async callable: async () -> T
    - Container-aware: (container) -> T
    - Async container-aware: async (container) -> T
    - Full async factory: AsyncServiceFactory[T]
    """

    lifecycle: ServiceLifecycle
    """Lifecycle pattern for this service."""

    dependencies: tuple[type[Any], ...] = ()
    """Protocol types that this service depends on.

    Dependencies will be resolved and injected before service creation.
    Circular dependencies are detected and reported as errors.
    """

    hot_reloadable: bool = False
    """Whether service supports configuration hot-reload.

    If True, service must implement ConfigurableServiceProtocol.
    """

    cleanup_priority: int = 100
    """Priority for cleanup ordering (lower numbers cleaned up first).

    Allows control over cleanup order to ensure dependencies
    are cleaned up in the correct sequence:
    - 10-19: Configuration and core infrastructure
    - 20-29: Core data services (omnidexer)
    - 30-49: Registry and factory services
    - 50-79: Request-scoped services
    - 80-99: Display and output services
    - 100+: Default priority
    """

    def is_async_factory(self) -> bool:
        """Check if factory function is async.

        Returns:
            True if the factory requires async execution
        """
        if hasattr(self.factory, "create"):
            # AsyncServiceFactory protocol
            return True

        return asyncio.iscoroutinefunction(self.factory)

    def requires_container(self) -> bool:
        """Check if factory requires container parameter.

        Returns:
            True if factory expects container as first parameter
        """
        if hasattr(self.factory, "create"):
            # AsyncServiceFactory always gets container
            return True

        # Check function signature for container parameter
        import inspect
        from collections.abc import Callable
        from typing import cast

        # For union types, we need to cast to callable for signature inspection
        # At this point we know it's not AsyncServiceFactory, so it must be a callable
        callable_factory = cast(Callable[..., Any], self.factory)
        sig = inspect.signature(callable_factory)

        # Only return True if there's a parameter named 'container'
        # or if the factory is one of the specific ones that needs the container
        for param_name, param in sig.parameters.items():
            if param_name == "container":
                return True

        # Special case for display manager and reference manager factories that need container
        factory_name = getattr(callable_factory, "__name__", "")
        container_requiring_factories = [
            "create_display_manager_service",
            "create_reference_manager_service",
        ]

        return factory_name in container_requiring_factories

    def validate_lifecycle_compatibility(self) -> list[str]:
        """Validate that lifecycle and other settings are compatible.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Hot-reloadable services should generally be singleton or scoped
        if self.hot_reloadable and self.lifecycle == ServiceLifecycle.TRANSIENT:
            errors.append(
                f"Hot-reloadable service {self.protocol.__name__} "
                f"should not use TRANSIENT lifecycle"
            )

        # Async resources need special lifecycle handling
        if (
            self.lifecycle == ServiceLifecycle.ASYNC_RESOURCE
            and not self.is_async_factory()
        ):
            errors.append(
                f"ASYNC_RESOURCE service {self.protocol.__name__} "
                f"must have async factory"
            )

        # Dependencies should be protocol types
        for dep in self.dependencies:
            if not hasattr(dep, "__protocol__") and not hasattr(dep, "_is_protocol"):
                errors.append(
                    f"Dependency {dep} for {self.protocol.__name__} "
                    f"should be a Protocol type"
                )

        return errors


@runtime_checkable
class AsyncServiceFactory(Protocol[T]):
    """Protocol for async service factories with full lifecycle management.

    Provides complete control over async service creation and cleanup,
    suitable for complex services that need container access or
    sophisticated initialization logic.
    """

    async def create(self, container: ServiceContainer) -> T:
        """Create service instance with full container access.

        Args:
            container: Service container for dependency resolution

        Returns:
            Fully initialized service instance

        Raises:
            ServiceInitializationError: If creation fails
        """
        ...

    async def cleanup(self, instance: T) -> None:
        """Clean up service instance.

        Args:
            instance: Service instance to clean up

        Should be idempotent - safe to call multiple times.
        """
        ...


def validate_service_descriptor(descriptor: ServiceDescriptor[Any]) -> None:
    """Validate a service descriptor for correctness.

    Args:
        descriptor: Service descriptor to validate

    Raises:
        ValueError: If descriptor has validation errors
    """
    errors = descriptor.validate_lifecycle_compatibility()

    if errors:
        error_msg = f"Service descriptor validation failed for {descriptor.protocol.__name__}:\n"
        error_msg += "\n".join(f"  - {error}" for error in errors)
        raise ValueError(error_msg)


# Service lifecycle optimization helpers


def optimize_lifecycle_for_service(
    service_type: type[Any],
    is_stateless: bool = True,
    is_expensive_to_create: bool = False,
    needs_request_isolation: bool = False,
    supports_hot_reload: bool = False,
    requires_async_init: bool = False,
) -> ServiceLifecycle:
    """Recommend optimal lifecycle for a service based on characteristics.

    Args:
        service_type: Service class or protocol
        is_stateless: Whether service maintains no mutable state
        is_expensive_to_create: Whether creation is computationally expensive
        needs_request_isolation: Whether service needs per-request instances
        supports_hot_reload: Whether service supports config reload
        requires_async_init: Whether service needs async initialization

    Returns:
        Recommended lifecycle pattern

    Examples:
        >>> optimize_lifecycle_for_service(
        ...     ContentTypeRegistry,
        ...     is_stateless=True,
        ...     is_expensive_to_create=False
        ... )
        ServiceLifecycle.SINGLETON

        >>> optimize_lifecycle_for_service(
        ...     TagResolver,
        ...     is_stateless=False,
        ...     needs_request_isolation=True,
        ...     supports_hot_reload=True
        ... )
        ServiceLifecycle.SCOPED
    """
    # Async initialization takes precedence
    if requires_async_init:
        return ServiceLifecycle.ASYNC_RESOURCE

    # Request isolation needs scoped lifecycle
    if needs_request_isolation:
        return ServiceLifecycle.SCOPED

    # Expensive-to-create stateless services should be singleton
    if is_expensive_to_create and is_stateless:
        return ServiceLifecycle.SINGLETON

    # Cheap-to-create services can be transient unless they support hot-reload
    if not is_expensive_to_create:
        if supports_hot_reload:
            return ServiceLifecycle.SINGLETON  # Need persistent instance for reload
        else:
            return ServiceLifecycle.TRANSIENT

    # Default to singleton for other cases
    return ServiceLifecycle.SINGLETON


# Cleanup priority constants for common service types


class CleanupPriority:
    """Standard cleanup priorities for different service categories."""

    CONFIGURATION = 10
    """Configuration services - cleaned up first."""

    CORE_RESOURCES = 20
    """Core resources like omnidexer - cleaned up early."""

    INFRASTRUCTURE = 30
    """Infrastructure services like registries."""

    BUSINESS_LOGIC = 50
    """Business logic services - middle priority."""

    REQUEST_SCOPED = 70
    """Request-scoped services - cleaned up late."""

    DISPLAY_OUTPUT = 90
    """Display and output services - cleaned up last."""

    DEFAULT = 100
    """Default priority for unspecified services."""
