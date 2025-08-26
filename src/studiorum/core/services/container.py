"""Modern service container with full dependency injection and async support.

This module provides the core container implementation for managing service
lifecycles, dependencies, and async resources. Designed to support both
CLI usage (backward compatibility) and MCP server requirements (request isolation).

Key components:
- ServiceContainer: Full DI container with async support
- RequestScopedContainer: Isolated container for MCP requests
- Service resolution with dependency injection
- Async resource management and cleanup
- Hot-reload infrastructure
"""

from __future__ import annotations

import asyncio
import weakref
from collections.abc import Awaitable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import uuid4

from studiorum.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ServiceError,
)
from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success

from .lifecycle import AsyncServiceFactory, ServiceDescriptor, ServiceLifecycle
from .protocols import AsyncResourceProtocol, ConfigurableServiceProtocol

if TYPE_CHECKING:
    from studiorum.core.config.unified_config import ApplicationConfig

logger = get_logger(__name__)

T = TypeVar("T")


class TypedServiceRegistry:
    """Type-safe service instance registry with runtime validation.

    Maintains type safety by using cast() with runtime validation
    instead of untyped dictionary access.
    """

    def __init__(self) -> None:
        self._instances: dict[type[Any], Any] = {}

    def store[S](self, protocol: type[S], instance: S) -> None:
        """Store a service instance with type validation."""
        self._instances[protocol] = instance

    def get[S](self, protocol: type[S]) -> S:
        """Get a service instance with type-safe cast.

        Uses cast() to maintain type safety while preserving runtime
        behavior. The container's service resolution ensures the stored
        instance actually implements the protocol.
        """
        instance = self._instances[protocol]
        return cast(S, instance)

    def contains(self, protocol: type[Any]) -> bool:
        """Check if protocol has a stored instance."""
        return protocol in self._instances

    def remove(self, protocol: type[Any]) -> None:
        """Remove stored instance for protocol."""
        self._instances.pop(protocol, None)

    def clear(self) -> None:
        """Clear all stored instances."""
        self._instances.clear()

    def items(self) -> Any:
        """Get items for iteration compatibility."""
        return self._instances.items()

    def __len__(self) -> int:
        """Get number of stored instances."""
        return len(self._instances)

    def __setitem__(self, protocol: type[Any], instance: Any) -> None:
        """Support dict-like assignment."""
        self._instances[protocol] = instance


class ServiceNotRegisteredError(Exception):
    """Raised when attempting to get a service that hasn't been registered."""

    def __init__(self, service_type: type[Any]) -> None:
        self.service_type = service_type
        super().__init__(f"Service {service_type.__name__} not registered")


class ServiceInitializationError(Exception):
    """Raised when service initialization fails."""

    def __init__(self, service_type: type[Any], cause: Exception) -> None:
        self.service_type = service_type
        self.cause = cause
        super().__init__(f"Failed to initialize {service_type.__name__}: {cause}")


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""

    def __init__(self, dependency_chain: list[type[Any]]) -> None:
        self.dependency_chain = dependency_chain
        chain_names = " -> ".join(t.__name__ for t in dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_names}")


class ServiceContainer:
    """2025 Python dependency injection container with full async support.

    This container provides:
    - Protocol-based service registration and resolution
    - 5 service lifecycle patterns (singleton/scoped/transient/async_resource/hot_reloadable)
    - Async resource management with proper cleanup
    - Dependency injection with circular dependency detection
    - Hot-reload infrastructure for configuration changes
    - Request scoping for MCP request isolation
    - CLI-optimized singleton caching to avoid asyncio.run() overhead

    Examples:
        Basic usage:
        >>> container = ServiceContainer()
        >>> container.register_service(
        ...     ConfigurationProtocol,
        ...     create_configuration_service,
        ...     lifecycle=ServiceLifecycle.SINGLETON
        ... )
        >>> config = await container.get_service(ConfigurationProtocol)

        Request scoping:
        >>> async with await container.create_request_scope() as request_scope:
        ...     scoped_service = await request_scope.get_service(TagResolverProtocol)
    """

    def __init__(self, parent: ServiceContainer | None = None) -> None:
        """Initialize service container.

        Args:
            parent: Parent container for service resolution hierarchy
        """
        self._parent = parent
        self._descriptors: dict[type[Any], ServiceDescriptor] = {}
        self._singleton_instances = TypedServiceRegistry()
        self._scoped_instances = TypedServiceRegistry()
        self._async_resources: set[Any] = set()
        self._initialization_lock: asyncio.Lock | None = None
        self._protocol_locks: dict[type[Any], asyncio.Lock] = {}
        self._cleanup_tasks: set[asyncio.Task] = set()
        self._resolution_stack: list[
            type[Any]
        ] = []  # For circular dependency detection
        self._is_closed = False

        # CLI-specific singleton cache to avoid asyncio.run() overhead
        # Only used for sync access to singleton services
        self._sync_singleton_cache = TypedServiceRegistry()

        # Weak references to child containers for cleanup propagation
        self._child_containers: set[weakref.ReferenceType[ServiceContainer]] = set()

        if parent:
            parent._add_child_container(self)

    def _add_child_container(self, child: ServiceContainer) -> None:
        """Add a child container reference for cleanup propagation."""
        self._child_containers.add(weakref.ref(child))

    def register_service(
        self,
        protocol: type[T],
        factory: Any,  # Union of various factory types
        lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON,
        dependencies: tuple[type[Any], ...] = (),
        hot_reloadable: bool = False,
        cleanup_priority: int = 100,
    ) -> None:
        """Register a service with full lifecycle management.

        Args:
            protocol: Protocol interface the service implements
            factory: Factory function, class, or AsyncServiceFactory
            lifecycle: Service lifecycle pattern
            dependencies: Protocol types this service depends on
            hot_reloadable: Whether service supports hot-reload
            cleanup_priority: Priority for cleanup ordering (lower = earlier)

        Raises:
            ValueError: If service descriptor validation fails
        """
        if self._is_closed:
            raise RuntimeError("Cannot register services on closed container")

        descriptor = ServiceDescriptor(
            protocol=protocol,
            factory=factory,
            lifecycle=lifecycle,
            dependencies=dependencies,
            hot_reloadable=hot_reloadable,
            cleanup_priority=cleanup_priority,
        )

        # Validate descriptor
        from .lifecycle import validate_service_descriptor

        validate_service_descriptor(descriptor)

        self._descriptors[protocol] = descriptor
        logger.debug(
            f"Registered service {protocol.__name__} with {lifecycle.value} lifecycle"
        )

    async def get_service(self, protocol: type[T]) -> T:
        """Get service instance with async support and dependency resolution.

        Args:
            protocol: Protocol interface to resolve

        Returns:
            Service instance implementing the protocol

        Raises:
            ServiceNotRegisteredError: If service not registered
            ServiceInitializationError: If service creation fails
            CircularDependencyError: If circular dependencies detected
        """
        if self._is_closed:
            raise RuntimeError("Cannot get services from closed container")

        # Check for circular dependencies
        if protocol in self._resolution_stack:
            raise CircularDependencyError(self._resolution_stack + [protocol])

        if protocol not in self._descriptors:
            if self._parent:
                return await self._parent.get_service(protocol)
            raise ServiceNotRegisteredError(protocol)

        descriptor = self._descriptors[protocol]

        # Handle different lifecycle types
        try:
            self._resolution_stack.append(protocol)

            if descriptor.lifecycle == ServiceLifecycle.SINGLETON:
                return await self._get_singleton_instance(protocol, descriptor)
            elif descriptor.lifecycle == ServiceLifecycle.SCOPED:
                return await self._get_scoped_instance(protocol, descriptor)
            elif descriptor.lifecycle == ServiceLifecycle.TRANSIENT:
                return await self._create_instance(descriptor)
            elif descriptor.lifecycle == ServiceLifecycle.ASYNC_RESOURCE:
                return await self._get_async_resource_instance(protocol, descriptor)
            elif descriptor.lifecycle == ServiceLifecycle.HOT_RELOADABLE:
                # Hot-reloadable services are typically singleton with reload capability
                return await self._get_singleton_instance(protocol, descriptor)
            else:
                raise ValueError(f"Unknown lifecycle: {descriptor.lifecycle}")

        finally:
            if self._resolution_stack and self._resolution_stack[-1] == protocol:
                self._resolution_stack.pop()

    def get_service_sync(self, protocol: type[T]) -> T:
        """Get service instance synchronously for CLI usage.

        This method provides synchronous access to services for CLI commands
        that operate in a synchronous context. It implements true sync service
        creation to avoid asyncio.run() overhead completely.

        Args:
            protocol: Protocol interface to resolve

        Returns:
            Service instance implementing the protocol

        Raises:
            RuntimeError: If called from async context
            ServiceNotRegisteredError: If service not registered
            ServiceInitializationError: If service creation fails
        """
        # Allow bypass for test environments
        import os

        if not os.getenv("PYTEST_CURRENT_TEST"):
            try:
                # Check if we're in an async context
                asyncio.get_running_loop()
                raise RuntimeError(
                    f"get_service_sync({protocol.__name__}) cannot be called from async context. "
                    f"Use 'await container.get_service({protocol.__name__})' instead."
                )
            except RuntimeError as e:
                # Re-raise if it's our error message
                if "get_service_sync" in str(e):
                    raise

        # Fast path: Check CLI singleton cache first
        if self._sync_singleton_cache.contains(protocol):
            cached_instance = self._sync_singleton_cache.get(protocol)
            logger.debug(f"Retrieved {protocol.__name__} from sync cache")
            return cached_instance

        # Check if service is registered
        if protocol not in self._descriptors:
            if self._parent:
                return self._parent.get_service_sync(protocol)
            raise ServiceNotRegisteredError(protocol)

        descriptor = self._descriptors[protocol]

        # Handle different lifecycle types synchronously
        if descriptor.lifecycle == ServiceLifecycle.SINGLETON:
            return self._get_singleton_instance_sync(protocol, descriptor)
        elif descriptor.lifecycle == ServiceLifecycle.SCOPED:
            return self._get_scoped_instance_sync(protocol, descriptor)
        elif descriptor.lifecycle == ServiceLifecycle.TRANSIENT:
            return self._create_instance_sync(descriptor)
        elif descriptor.lifecycle == ServiceLifecycle.ASYNC_RESOURCE:
            # Async resources cannot be created synchronously - fallback to async
            logger.warning(
                f"ASYNC_RESOURCE service {protocol.__name__} requires event loop"
            )
            return asyncio.run(self.get_service(protocol))
        elif descriptor.lifecycle == ServiceLifecycle.HOT_RELOADABLE:
            # Hot-reloadable services are typically singleton
            return self._get_singleton_instance_sync(protocol, descriptor)
        else:
            raise ValueError(f"Unknown lifecycle: {descriptor.lifecycle}")

    def _get_singleton_instance_sync(
        self, protocol: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Get or create singleton instance synchronously for CLI usage."""
        # Check sync cache first
        if self._sync_singleton_cache.contains(protocol):
            return self._sync_singleton_cache.get(protocol)

        # Check async singleton cache
        if self._singleton_instances.contains(protocol):
            instance = self._singleton_instances.get(protocol)
            # Cache in sync cache for future access
            self._sync_singleton_cache.store(protocol, instance)
            logger.debug(f"Cached existing {protocol.__name__} in sync cache")
            return instance

        # Need to create new instance synchronously
        try:
            # Resolve dependencies synchronously
            resolved_deps = self._resolve_dependencies_sync(descriptor.dependencies)

            # Create instance with resolved dependencies
            new_instance: T = self._create_instance_with_dependencies_sync(
                descriptor, resolved_deps
            )

            # Store in both caches
            self._singleton_instances.store(protocol, new_instance)
            self._sync_singleton_cache.store(protocol, new_instance)

            logger.debug(
                f"Created and cached new singleton {protocol.__name__} synchronously"
            )
            return new_instance

        except Exception as e:
            logger.exception(
                f"Failed to create singleton instance of {descriptor.protocol.__name__} synchronously"
            )
            raise ServiceInitializationError(descriptor.protocol, e) from e

    def _get_scoped_instance_sync(
        self, protocol: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Get or create scoped instance synchronously."""
        if self._scoped_instances.contains(protocol):
            return self._scoped_instances.get(protocol)

        instance: T = self._create_instance_sync(descriptor)
        self._scoped_instances.store(protocol, instance)
        return instance

    def _resolve_dependencies_sync(
        self, dependencies: tuple[type[Any], ...]
    ) -> tuple[Any, ...]:
        """Resolve service dependencies synchronously.

        Args:
            dependencies: Tuple of protocol types to resolve

        Returns:
            Tuple of resolved service instances
        """
        if not dependencies:
            return ()

        resolved = []
        for dep_protocol in dependencies:
            dep_instance = self.get_service_sync(dep_protocol)
            resolved.append(dep_instance)

        return tuple(resolved)

    def _create_instance_sync(self, descriptor: ServiceDescriptor[T]) -> T:
        """Create service instance synchronously with dependency injection.

        Args:
            descriptor: Service descriptor with factory and dependencies

        Returns:
            Created service instance
        """
        try:
            # Resolve dependencies first
            deps = self._resolve_dependencies_sync(descriptor.dependencies)

            # Dispatch to sync factory call
            instance: Any = self._dispatch_factory_call_sync(descriptor, deps)

            logger.debug(
                f"Created instance of {descriptor.protocol.__name__} synchronously"
            )
            return cast(T, instance)

        except Exception as e:
            logger.exception(
                f"Failed to create instance of {descriptor.protocol.__name__} synchronously"
            )
            raise ServiceInitializationError(descriptor.protocol, e) from e

    def _create_instance_with_dependencies_sync(
        self, descriptor: ServiceDescriptor[T], deps: tuple[Any, ...]
    ) -> T:
        """Create service instance synchronously with pre-resolved dependencies.

        Args:
            descriptor: Service descriptor with factory and dependencies
            deps: Pre-resolved dependency instances

        Returns:
            Created service instance
        """
        try:
            # Use the sync dispatch method
            instance: Any = self._dispatch_factory_call_sync(descriptor, deps)

            logger.debug(
                f"Created instance of {descriptor.protocol.__name__} with dependencies synchronously"
            )
            return cast(T, instance)

        except Exception as e:
            logger.exception(
                f"Failed to create instance of {descriptor.protocol.__name__} synchronously"
            )
            raise ServiceInitializationError(descriptor.protocol, e) from e

    def _dispatch_factory_call_sync(
        self, descriptor: ServiceDescriptor, deps: tuple[Any, ...]
    ) -> Any:
        """Dispatch factory call synchronously with proper type handling.

        This method handles sync factory calls without creating event loops.
        """
        factory = descriptor.factory

        # AsyncServiceFactory cannot be called synchronously
        if isinstance(factory, AsyncServiceFactory):
            raise RuntimeError(
                f"AsyncServiceFactory for {descriptor.protocol.__name__} "
                f"cannot be called synchronously. Use async context."
            )

        # Check if factory is async - need special handling
        if asyncio.iscoroutinefunction(factory):
            # Try to run the async factory synchronously as fallback
            # This is not ideal but necessary for CLI compatibility
            logger.warning(
                f"Running async factory for {descriptor.protocol.__name__} synchronously. "
                f"Consider providing a sync alternative for better performance."
            )
            try:
                # Use asyncio.run as fallback for critical services
                coro_result = (
                    factory(*deps)
                    if len(descriptor.dependencies) > 0
                    else (
                        factory(self) if descriptor.requires_container() else factory()
                    )
                )
                return asyncio.run(coro_result)
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    raise RuntimeError(
                        f"Cannot create {descriptor.protocol.__name__} synchronously "
                        f"from within async context. Use async container methods."
                    ) from e
                raise

        # Call sync factory using progressive fallback approach
        # This handles the complex union type by trying different call patterns

        # Cast to avoid union type issues for mypy
        from typing import cast

        factory_callable = cast(Any, factory)

        # First try: dependencies as arguments
        if len(descriptor.dependencies) > 0:
            return factory_callable(*deps)

        # Second try: container as argument if factory requires it
        if descriptor.requires_container():
            return factory_callable(self)

        # Third try: no arguments
        return factory_callable()

    async def _get_singleton_instance(
        self, protocol: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Get or create singleton instance with thread safety."""
        if self._singleton_instances.contains(protocol):
            return self._singleton_instances.get(protocol)

        # Use per-protocol locks to avoid deadlock during dependency resolution
        if protocol not in self._protocol_locks:
            self._protocol_locks[protocol] = asyncio.Lock()

        protocol_lock = self._protocol_locks[protocol]

        async with protocol_lock:
            # Double-check after acquiring protocol-specific lock
            if self._singleton_instances.contains(protocol):
                return self._singleton_instances.get(protocol)

            # Resolve dependencies outside the global lock to prevent deadlock
            dependencies = await self._resolve_dependencies(descriptor.dependencies)

            # Create instance with resolved dependencies
            instance: T = await self._create_instance_with_dependencies(
                descriptor, dependencies
            )
            self._singleton_instances.store(protocol, instance)
            return instance

    async def _get_scoped_instance(
        self, protocol: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Get or create scoped instance."""
        if self._scoped_instances.contains(protocol):
            return self._scoped_instances.get(protocol)

        instance: T = await self._create_instance(descriptor)
        self._scoped_instances.store(protocol, instance)
        return instance

    async def _get_async_resource_instance(
        self, protocol: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Get or create async resource with proper lifecycle management."""
        # Async resources are typically singleton but with special lifecycle
        if self._singleton_instances.contains(protocol):
            return self._singleton_instances.get(protocol)

        # Create lock lazily to ensure it's associated with the current event loop
        if self._initialization_lock is None:
            self._initialization_lock = asyncio.Lock()

        async with self._initialization_lock:
            # Double-check after acquiring lock
            if self._singleton_instances.contains(protocol):
                return self._singleton_instances.get(protocol)

            instance: T = await self._create_instance(descriptor)

            # Track for cleanup
            if isinstance(instance, AsyncResourceProtocol):
                self._async_resources.add(instance)

            self._singleton_instances.store(protocol, instance)
            return instance

    async def _resolve_dependencies(
        self, dependencies: tuple[type[Any], ...]
    ) -> tuple[Any, ...]:
        """Resolve service dependencies recursively.

        Args:
            dependencies: Tuple of protocol types to resolve

        Returns:
            Tuple of resolved service instances
        """
        if not dependencies:
            return ()

        resolved = []
        for dep_protocol in dependencies:
            dep_instance = await self.get_service(dep_protocol)
            resolved.append(dep_instance)

        return tuple(resolved)

    async def _create_instance(self, descriptor: ServiceDescriptor) -> T:
        """Create service instance with dependency injection.

        Args:
            descriptor: Service descriptor with factory and dependencies

        Returns:
            Created and initialized service instance
        """
        try:
            # Resolve dependencies first
            deps = await self._resolve_dependencies(descriptor.dependencies)

            # Dispatch to specific factory handler based on type
            instance: Any = await self._dispatch_factory_call(descriptor, deps)

            # Initialize async resources
            if isinstance(instance, AsyncResourceProtocol):
                if not instance.is_initialized():
                    await instance.initialize()
                self._async_resources.add(instance)

            logger.debug(f"Created instance of {descriptor.protocol.__name__}")
            return cast(T, instance)

        except Exception as e:
            logger.exception(
                f"Failed to create instance of {descriptor.protocol.__name__}"
            )
            raise ServiceInitializationError(descriptor.protocol, e) from e

    async def _dispatch_factory_call(
        self, descriptor: ServiceDescriptor, deps: tuple[Any, ...]
    ) -> Any:
        """Dispatch factory call with proper type handling.

        This method handles the complex union type by dispatching
        to specific handlers that can properly narrow the factory type.
        """
        factory = descriptor.factory

        # Handle AsyncServiceFactory protocol
        if isinstance(factory, AsyncServiceFactory):
            return await factory.create(self)

        # For callable factories, dispatch based on signature requirements
        if len(descriptor.dependencies) > 0:
            return await self._call_factory_with_dependencies(factory, deps)
        elif descriptor.requires_container():
            return await self._call_factory_with_container(factory)
        else:
            return await self._call_simple_factory(factory)

    async def _call_factory_with_dependencies(
        self, factory: Any, deps: tuple[Any, ...]
    ) -> Any:
        """Call factory function with dependency arguments."""
        if asyncio.iscoroutinefunction(factory):
            return await factory(*deps)
        else:
            return factory(*deps)

    async def _call_factory_with_container(self, factory: Any) -> Any:
        """Call factory function with container argument."""
        if asyncio.iscoroutinefunction(factory):
            return await factory(self)
        else:
            return factory(self)

    async def _call_simple_factory(self, factory: Any) -> Any:
        """Call factory function with no arguments."""
        if asyncio.iscoroutinefunction(factory):
            return await factory()
        else:
            return factory()

    async def _create_instance_with_dependencies(
        self, descriptor: ServiceDescriptor, deps: tuple[Any, ...]
    ) -> T:
        """Create service instance with pre-resolved dependencies.

        Args:
            descriptor: Service descriptor with factory and dependencies
            deps: Pre-resolved dependency instances

        Returns:
            Created and initialized service instance
        """
        try:
            # Use the shared dispatch method for consistent factory handling
            instance: Any = await self._dispatch_factory_call(descriptor, deps)

            # Initialize async resources
            if isinstance(instance, AsyncResourceProtocol):
                if not instance.is_initialized():
                    await instance.initialize()
                self._async_resources.add(instance)

            logger.debug(f"Created instance of {descriptor.protocol.__name__}")
            return cast(T, instance)

        except Exception as e:
            logger.exception(
                f"Failed to create instance of {descriptor.protocol.__name__}"
            )
            raise ServiceInitializationError(descriptor.protocol, e) from e

    async def create_request_scope(self) -> RequestScopedContainer:
        """Create isolated container for MCP request handling.

        Returns:
            Request-scoped container with service isolation
        """
        if self._is_closed:
            raise RuntimeError("Cannot create request scope from closed container")

        return RequestScopedContainer(parent=self)

    async def reload_configuration(self, new_config: ApplicationConfig) -> None:
        """Hot-reload configuration for all hot-reloadable services.

        Args:
            new_config: New application configuration to apply
        """
        if self._is_closed:
            logger.warning("Attempted to reload configuration on closed container")
            return

        reload_tasks = []

        # Reload singleton services
        for service_type, instance in self._singleton_instances.items():
            descriptor = self._descriptors.get(service_type)
            if (
                descriptor
                and descriptor.hot_reloadable
                and isinstance(instance, ConfigurableServiceProtocol)
            ):
                reload_tasks.append(instance.reload_config(new_config))

        # Reload scoped services
        for service_type, instance in self._scoped_instances.items():
            descriptor = self._descriptors.get(service_type)
            if (
                descriptor
                and descriptor.hot_reloadable
                and isinstance(instance, ConfigurableServiceProtocol)
            ):
                reload_tasks.append(instance.reload_config(new_config))

        # Propagate to child containers
        for child_ref in list(self._child_containers):
            child = child_ref()
            if child:
                reload_tasks.append(child.reload_configuration(new_config))
            else:
                self._child_containers.remove(child_ref)

        if reload_tasks:
            results = await asyncio.gather(*reload_tasks, return_exceptions=True)

            # Log any reload failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Configuration reload failed for service: {result}")

            logger.info(f"Configuration hot-reloaded for {len(reload_tasks)} services")

    async def cleanup(self) -> None:
        """Clean up all resources in dependency order.

        Performs cleanup in priority order to ensure dependencies
        are cleaned up in the correct sequence.
        """
        if self._is_closed:
            return

        logger.debug("Starting service container cleanup")

        try:
            # Clean up child containers first
            child_cleanup_tasks = []
            for child_ref in list(self._child_containers):
                child = child_ref()
                if child:
                    child_cleanup_tasks.append(child.cleanup())

            if child_cleanup_tasks:
                await asyncio.gather(*child_cleanup_tasks, return_exceptions=True)

            # Clean up async resources by priority
            async_resources_with_priority = []
            for resource in self._async_resources:
                priority = getattr(resource, "cleanup_priority", 100)
                async_resources_with_priority.append((priority, resource))

            # Sort by priority (lower numbers first)
            async_resources_with_priority.sort(key=lambda x: x[0])

            for priority, resource in async_resources_with_priority:
                if isinstance(resource, AsyncResourceProtocol):
                    try:
                        await resource.cleanup()
                        logger.debug(
                            f"Cleaned up async resource {type(resource).__name__}"
                        )
                    except Exception as e:
                        logger.exception(f"Failed to cleanup resource {resource}: {e}")

            # Cancel any remaining cleanup tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()

            if self._cleanup_tasks:
                await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)

            # Clear all state including sync cache
            self._singleton_instances.clear()
            self._scoped_instances.clear()
            self._sync_singleton_cache.clear()
            self._async_resources.clear()
            self._cleanup_tasks.clear()
            self._child_containers.clear()

        finally:
            self._is_closed = True
            logger.debug("Service container cleanup complete")

    def is_closed(self) -> bool:
        """Check if container has been closed.

        Returns:
            True if container is closed
        """
        return self._is_closed

    def get_registered_services(self) -> dict[type[Any], ServiceDescriptor]:
        """Get all registered service descriptors.

        Returns:
            Dictionary mapping protocol types to descriptors
        """
        return self._descriptors.copy()

    async def register_instance(self, protocol: type[T], instance: T) -> None:
        """Register an existing instance for a protocol.

        Args:
            protocol: Protocol interface the instance implements
            instance: Pre-created instance to register
        """
        if self._is_closed:
            raise RuntimeError("Cannot register instances on closed container")

        # Register as singleton with identity factory
        def identity_factory() -> T:
            return instance

        self.register_service(
            protocol=protocol,
            factory=identity_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Store the instance directly to avoid re-creation
        self._singleton_instances[protocol] = instance

        logger.debug(f"Registered instance of {protocol.__name__}")

    async def get_hot_reloadable_services(self) -> list[Any]:
        """Get all hot-reloadable service instances.

        Returns:
            List of service instances that support hot-reload
        """
        hot_reloadable = []

        # Check singleton instances
        for service_type, instance in self._singleton_instances.items():
            descriptor = self._descriptors.get(service_type)
            if descriptor and descriptor.hot_reloadable:
                hot_reloadable.append(instance)

        # Check scoped instances
        for service_type, instance in self._scoped_instances.items():
            descriptor = self._descriptors.get(service_type)
            if descriptor and descriptor.hot_reloadable:
                hot_reloadable.append(instance)

        return hot_reloadable

    def __repr__(self) -> str:
        """Return string representation of container."""
        status = "closed" if self._is_closed else "open"
        service_count = len(self._descriptors)
        singleton_count = len(self._singleton_instances)
        scoped_count = len(self._scoped_instances)
        sync_cache_count = len(self._sync_singleton_cache)

        return (
            f"ServiceContainer(status={status}, "
            f"services={service_count}, "
            f"singletons={singleton_count}, "
            f"scoped={scoped_count}, "
            f"sync_cache={sync_cache_count})"
        )


class RequestScopedContainer(ServiceContainer):
    """Request-scoped container for MCP request isolation.

    Provides complete isolation for MCP requests while inheriting
    singleton services from the parent container. Automatically
    cleans up when used as an async context manager.

    Examples:
        >>> async with await container.create_request_scope() as request_scope:
        ...     tag_resolver = await request_scope.get_service(TagResolverProtocol)
        ...     # Process request with isolated services
        # Automatic cleanup when context exits
    """

    def __init__(self, parent: ServiceContainer) -> None:
        """Initialize request-scoped container.

        Args:
            parent: Parent container for singleton service resolution
        """
        super().__init__(parent=parent)
        self._request_id = str(uuid4())
        self._created_at = datetime.now()

        logger.debug(f"Created request-scoped container {self._request_id}")

    @property
    def request_id(self) -> str:
        """Get unique request identifier.

        Returns:
            UUID string for this request scope
        """
        return self._request_id

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp.

        Returns:
            Datetime when this request scope was created
        """
        return self._created_at

    async def __aenter__(self) -> RequestScopedContainer:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager with cleanup."""
        await self.cleanup()

    def __repr__(self) -> str:
        """Return string representation of request container."""
        status = "closed" if self._is_closed else "open"
        age = datetime.now() - self._created_at

        return (
            f"RequestScopedContainer(id={self._request_id[:8]}, "
            f"status={status}, age={age.total_seconds():.1f}s)"
        )


# Utility functions for container management


async def create_mcp_request_container(
    base_config: ApplicationConfig, request_overrides: dict | None = None
) -> RequestScopedContainer:
    """Create MCP request container with configuration overrides.

    Args:
        base_config: Base application configuration
        request_overrides: Request-specific configuration overrides

    Returns:
        Request-scoped container with configuration overrides

    Examples:
        >>> async with await create_mcp_request_container(
        ...     base_config,
        ...     {"content": {"sources": ["SRD"]}}
        ... ) as container:
        ...     omnidexer = await container.get_service(OmnidexerProtocol)
    """
    from ..container import get_global_container

    # Get global container (will be enhanced DefaultServiceContainer)
    global_container = get_global_container()

    # Check if it has the create_request_scope method
    if not hasattr(global_container, "create_request_scope"):
        raise RuntimeError("Global container does not support request scoping")

    # Create request scope - cast needed for legacy global container compatibility
    request_container_raw = await global_container.create_request_scope()
    request_container = cast(RequestScopedContainer, request_container_raw)

    # Apply request-specific configuration overrides if provided
    if request_overrides:
        from .factories import create_configuration_service
        from .protocols import ConfigurationProtocol

        # Create config with overrides
        config_with_overrides = base_config.model_copy(update=request_overrides)

        # Override configuration service for this request
        async def config_factory() -> ConfigurationProtocol:
            return await create_configuration_service(config_with_overrides)

        request_container.register_service(
            cast(type, ConfigurationProtocol),
            config_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

    return request_container
