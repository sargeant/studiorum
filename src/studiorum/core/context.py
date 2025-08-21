"""Modern async request context with protocol-based service isolation.

This module provides request context patterns that leverage P3's enhanced service
container architecture to provide protocol-based service isolation, async resource
management, and clean request boundaries for MCP server operations while maintaining
backward compatibility with the existing CLI workflow.

Key Features:
- AsyncRequestContext with protocol-validated service access
- RequestContext sync wrapper for CLI compatibility
- Modern async context managers for MCP request execution
- Performance monitoring and hot-reload support
- Comprehensive async resource management and cleanup
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)
from uuid import UUID, uuid4
from weakref import WeakSet

from pydantic import BaseModel, ConfigDict, Field

from studiorum.core.logging import get_logger

from .error_types import (
    ContentNotFoundError,
    MCPError,
    ProcessingError,
)
from .exceptions import DnD5eError
from .services.container import ModernServiceContainer
from .services.lifecycle import ServiceLifecycle
from .services.protocols import (
    AsyncResourceProtocol,
    ConfigurationProtocol,
    ContentFactoryProtocol,
    DisplayManagerProtocol,
    OmnidexerProtocol,
    ReferenceManagerProtocol,
    ServiceProtocol,
    TagResolverProtocol,
)

if TYPE_CHECKING:
    from .config.unified_config import ApplicationConfig
    from .models.adventures import Adventure
    from .models.base import Content
else:
    # Import ApplicationConfig at runtime for Pydantic model
    try:
        from .config.unified_config import ApplicationConfig
    except ImportError:
        # Forward declare ApplicationConfig when not available
        ApplicationConfig = type("ApplicationConfig", (), {})  # type: ignore[misc,assignment]
    Adventure = Any
    Content = Any

T = TypeVar("T", bound=ServiceProtocol)

logger = get_logger(__name__)


class RequestMetrics(BaseModel):
    """Performance metrics for request context."""

    service_access_count: dict[str, int] = Field(default_factory=dict)
    async_operations_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_peak_mb: float | None = None


@runtime_checkable
class RequestContextProtocol(Protocol):
    """Protocol for request context - enables testing and extensibility."""

    request_id: UUID
    started_at: datetime
    is_closed: bool

    async def get_service(self, protocol: type[T]) -> T:
        """Get service with protocol validation."""
        ...

    async def close(self) -> None:
        """Close context and clean up resources."""
        ...

    def add_error(self, error: MCPError) -> None:
        """Add error to request context."""
        ...


class AsyncRequestContext(BaseModel):
    """Modern async request context with protocol-based service access.

    This context provides:
    - Protocol-validated service access with runtime verification
    - Async resource management with proper cleanup
    - Performance metrics collection and monitoring hooks
    - Hot-reload configuration support
    - Request-scoped error collection and propagation
    - Service caching for performance optimization

    Examples:
        Basic usage:
        >>> async with AsyncRequestContext() as ctx:
        ...     omnidexer = await ctx.get_service(OmnidexerProtocol)
        ...     results = await omnidexer.search("fireball")

        With configuration override:
        >>> context = AsyncRequestContext(user_config=custom_config)
        >>> async with context as ctx:
        ...     config = await ctx.get_service(ConfigurationProtocol)
    """

    # Request identification and lifecycle
    request_id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None

    # Request configuration
    user_config: ApplicationConfig | None = None
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Performance and monitoring
    metrics: RequestMetrics = Field(default_factory=RequestMetrics)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Private attributes for internal state
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._container: ModernServiceContainer | None = None
        self._closed: bool = False
        self._async_resources: WeakSet = WeakSet()
        self._cleanup_tasks: list[asyncio.Task] = []
        self._errors: list[MCPError] = []
        self._service_cache: dict[type, ServiceProtocol] = {}

    async def __aenter__(self) -> AsyncRequestContext:
        """Async context manager entry with proper resource initialization."""
        if self._container is None:
            self._container = await self._create_request_container()
            await self._initialize_async_resources()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit with comprehensive cleanup."""
        await self.close()
        if exc_type:
            logger.error(
                f"Request {self.request_id} failed: {exc_type.__name__}: {exc_val}"
            )

    async def _create_request_container(self) -> ModernServiceContainer:
        """Create and configure request-scoped service container."""
        container = ModernServiceContainer()

        # Import factory functions from P3
        from .services.factories import (
            create_configuration_service,
            create_content_factory_service,
            create_display_manager_service,
            create_omnidexer_service,
            create_reference_manager_service,
            create_tag_resolver_service,
        )

        # Register configuration service (per-request override support)
        if self.user_config:
            # Create a simple wrapper for the config instance
            def config_factory() -> ApplicationConfig:
                return self.user_config  # type: ignore[return-value]

            container.register_service(
                ConfigurationProtocol,  # type: ignore[type-abstract]
                config_factory,
                lifecycle=ServiceLifecycle.SINGLETON,
                dependencies=(),
                hot_reloadable=True,
            )
        else:
            container.register_service(
                ConfigurationProtocol,  # type: ignore[type-abstract]
                create_configuration_service,
                lifecycle=ServiceLifecycle.SINGLETON,
                dependencies=(),
                hot_reloadable=True,
            )

        # Register omnidexer with async resource lifecycle
        container.register_service(
            OmnidexerProtocol,  # type: ignore[type-abstract]
            self._omnidexer_factory,
            lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
            dependencies=(ConfigurationProtocol,),
        )

        # Register tag resolver with scoped lifecycle
        container.register_service(
            TagResolverProtocol,  # type: ignore[type-abstract]
            create_tag_resolver_service,
            lifecycle=ServiceLifecycle.SCOPED,
            dependencies=(OmnidexerProtocol, ConfigurationProtocol),
            hot_reloadable=True,
        )

        # Register display manager as scoped
        container.register_service(
            DisplayManagerProtocol,  # type: ignore[type-abstract]
            create_display_manager_service,
            lifecycle=ServiceLifecycle.SCOPED,
            dependencies=(ConfigurationProtocol,),
            hot_reloadable=True,
        )

        # Register reference manager as scoped
        container.register_service(
            ReferenceManagerProtocol,  # type: ignore[type-abstract]
            create_reference_manager_service,
            lifecycle=ServiceLifecycle.SCOPED,
            dependencies=(OmnidexerProtocol,),
        )

        # Register content factory as async resource
        container.register_service(
            ContentFactoryProtocol,  # type: ignore[type-abstract]
            create_content_factory_service,
            lifecycle=ServiceLifecycle.SINGLETON,
            dependencies=(),
        )

        return container

    async def _initialize_async_resources(self) -> None:
        """Initialize all async resources in the container."""
        # Get all async resources from container for tracking
        # This would be implemented based on the container's API
        pass

    async def get_service(self, protocol: type[T]) -> T:
        """Get service with protocol validation and caching.

        Args:
            protocol: Service protocol type to get

        Returns:
            Service instance implementing the protocol

        Raises:
            RuntimeError: If context is closed
            ServiceNotRegisteredError: If service not registered
            TypeError: If service doesn't implement protocol
        """
        self._check_not_closed()

        # Check cache first
        if protocol in self._service_cache:
            self.metrics.cache_hits += 1
            service = self._service_cache[protocol]
            # Verify protocol compliance at runtime
            if not isinstance(service, protocol):
                raise RuntimeError(
                    f"Cached service {service} doesn't implement {protocol}"
                )
            return service

        # Get from container with async support
        if self._container is None:
            raise RuntimeError("Container not initialized")
        service = await self._container.get_service(protocol)

        # Runtime protocol validation
        if not isinstance(service, protocol):
            raise RuntimeError(
                f"Service {service} doesn't implement protocol {protocol}"
            )

        # Cache for performance
        self._service_cache[protocol] = service
        self.metrics.cache_misses += 1
        self.metrics.service_access_count[protocol.__name__] = (
            self.metrics.service_access_count.get(protocol.__name__, 0) + 1
        )

        return service

    async def close(self) -> None:
        """Comprehensive async cleanup with proper resource management."""
        if self._closed:
            return

        logger.info(f"Closing request context {self.request_id}")

        try:
            # Cancel any running cleanup tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()

            if self._cleanup_tasks:
                await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)

            # Clean up async resources in reverse dependency order
            async_resources = list(self._async_resources)
            for resource in reversed(async_resources):
                if isinstance(resource, AsyncResourceProtocol):
                    try:
                        await resource.cleanup()
                    except Exception as e:
                        logger.error(
                            f"Error cleaning up async resource {resource}: {e}"
                        )

            # Clean up service container
            if self._container:
                await self._container.cleanup()

            self.finished_at = datetime.now()
            self._closed = True

            # Log performance metrics
            if self.duration_ms:
                logger.info(
                    f"Request {self.request_id} completed in {self.duration_ms:.2f}ms"
                )
                logger.debug(f"Request metrics: {self.metrics}")

        except Exception as e:
            logger.error(f"Error during request cleanup: {e}")
            raise

    @property
    def is_closed(self) -> bool:
        """Check if context is closed."""
        return self._closed

    @property
    def duration_ms(self) -> float | None:
        """Get request duration in milliseconds."""
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return None

    # Modern protocol-based service access with async support
    async def omnidexer(self) -> OmnidexerProtocol:
        """Get request-scoped omnidexer with protocol validation."""
        return await self.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]

    async def tag_resolver(self) -> TagResolverProtocol:
        """Get request-scoped tag resolver with protocol validation."""
        return await self.get_service(TagResolverProtocol)  # type: ignore[type-abstract]

    async def content_factory(self) -> ContentFactoryProtocol:
        """Get request-scoped content factory with async initialization."""
        return await self.get_service(ContentFactoryProtocol)  # type: ignore[type-abstract]

    async def config(self) -> ApplicationConfig:
        """Get effective configuration for this request."""
        config_service = await self.get_service(ConfigurationProtocol)  # type: ignore[type-abstract]
        return config_service.get_config()

    # Hot-reload support from P3
    async def reload_configuration(self, new_config: ApplicationConfig) -> None:
        """Hot-reload configuration during request execution."""
        self.user_config = new_config
        if self._container:
            # Update configuration service
            await self._container.register_instance(ConfigurationProtocol, new_config)  # type: ignore[arg-type]
            # Trigger hot-reload for configurable services
            hot_reloadable_services = (
                await self._container.get_hot_reloadable_services()
            )
            for service in hot_reloadable_services:
                if hasattr(service, "reload_config"):
                    await service.reload_config(new_config)
        logger.info(f"Configuration reloaded for request {self.request_id}")

    # Error handling integration with P2 (enhanced)
    def add_error(self, error: MCPError) -> None:
        """Add error to request context with async error propagation."""
        self._errors.append(error)
        logger.warning(f"Request {self.request_id} error: {error.message}")

    async def add_async_error(self, error: MCPError) -> None:
        """Add error with async error handling capabilities."""
        self.add_error(error)
        # Could trigger async error reporting/telemetry here

    def has_errors(self) -> bool:
        """Check if request has any errors."""
        return len(self._errors) > 0

    def get_errors(self) -> list[MCPError]:
        """Get all errors for this request."""
        return self._errors.copy()

    def clear_errors(self) -> None:
        """Clear all errors."""
        self._errors.clear()

    # Performance monitoring hooks for P5
    def record_cache_hit(self) -> None:
        """Record cache hit for performance monitoring."""
        self.metrics.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record cache miss for performance monitoring."""
        self.metrics.cache_misses += 1

    def record_async_operation(self) -> None:
        """Record async operation for performance tracking."""
        self.metrics.async_operations_count += 1

    def _check_not_closed(self) -> None:
        """Ensure context is not closed."""
        if self._closed:
            raise RuntimeError(f"AsyncRequestContext {self.request_id} is closed")

    # Service factory functions (using P3 patterns)
    async def _omnidexer_factory(
        self, config_service: ConfigurationProtocol
    ) -> OmnidexerProtocol:
        """Factory for request-scoped omnidexer using proper service wrapper."""
        from .services.factories import create_omnidexer_service

        # Use the proper factory that returns AsyncOmnidexerService
        # We need to pass the container, not the config service
        if self._container is None:
            raise RuntimeError("Container not initialized")
        return await create_omnidexer_service(self._container)


# Legacy sync wrapper for CLI backward compatibility
class RequestContext:
    """Synchronous wrapper around AsyncRequestContext for CLI compatibility.

    This wrapper provides a synchronous interface to AsyncRequestContext,
    enabling CLI commands to use request contexts without async/await syntax.

    Examples:
        CLI usage:
        >>> with RequestContext() as ctx:
        ...     omnidexer = ctx.omnidexer
        ...     results = omnidexer.search("fireball")
    """

    def __init__(self, async_context: AsyncRequestContext) -> None:
        """Initialize sync wrapper around async context."""
        self._async_context = async_context
        self._loop: asyncio.AbstractEventLoop | None = None

    def __enter__(self) -> RequestContext:
        """Sync context manager entry."""
        import asyncio

        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._loop.run_until_complete(self._async_context.__aenter__())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Sync context manager exit."""
        if self._loop is None:
            raise RuntimeError("Event loop not initialized")
        self._loop.run_until_complete(
            self._async_context.__aexit__(exc_type, exc_val, exc_tb)
        )

    @property
    def request_id(self) -> UUID:
        """Get request ID."""
        return self._async_context.request_id

    @property
    def is_closed(self) -> bool:
        """Check if context is closed."""
        return self._async_context.is_closed

    # Sync property access (blocks until async completes)
    @property
    def omnidexer(self) -> OmnidexerProtocol:
        """Get omnidexer synchronously."""
        if self._loop is None:
            raise RuntimeError("RequestContext must be used as a context manager")
        return self._loop.run_until_complete(self._async_context.omnidexer())

    @property
    def tag_resolver(self) -> TagResolverProtocol:
        """Get tag resolver synchronously."""
        if self._loop is None:
            raise RuntimeError("RequestContext must be used as a context manager")
        return self._loop.run_until_complete(self._async_context.tag_resolver())

    @property
    def config(self) -> ApplicationConfig:
        """Get config synchronously."""
        if self._loop is None:
            raise RuntimeError("RequestContext must be used as a context manager")
        return self._loop.run_until_complete(self._async_context.config())

    def add_error(self, error: MCPError) -> None:
        """Add error (delegated)."""
        self._async_context.add_error(error)

    def has_errors(self) -> bool:
        """Check for errors (delegated)."""
        return self._async_context.has_errors()

    def get_errors(self) -> list[MCPError]:
        """Get errors (delegated)."""
        return self._async_context.get_errors()


# Context factory functions
def create_async_request_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncRequestContext:
    """Factory function for creating async request contexts."""
    return AsyncRequestContext(
        user_config=config_override, sources=sources or [], metadata=metadata or {}
    )


def create_sync_request_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RequestContext:
    """Factory function for creating sync request contexts (CLI compatibility)."""
    async_context = create_async_request_context(config_override, sources, metadata)
    return RequestContext(async_context)


@asynccontextmanager
async def async_request_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncIterator[AsyncRequestContext]:
    """Modern async context manager for MCP request execution."""
    context = create_async_request_context(config_override, sources, metadata)
    async with context:
        yield context


@contextmanager
def request_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[RequestContext]:
    """Sync context manager for CLI backward compatibility."""
    context = create_sync_request_context(config_override, sources, metadata)
    with context:
        yield context


# Advanced factory with performance and hot-reload capabilities
@asynccontextmanager
async def performance_monitored_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    enable_hot_reload: bool = False,
    performance_tracking: bool = True,
) -> AsyncIterator[AsyncRequestContext]:
    """Context manager with advanced performance monitoring and hot-reload support."""

    context = create_async_request_context(config_override, sources, metadata)

    # Enable performance tracking hooks
    if performance_tracking:
        context.metadata["performance_tracking"] = True

    # Setup hot-reload monitoring if enabled
    if enable_hot_reload and config_override:
        context.metadata["hot_reload_enabled"] = True

    async with context:
        try:
            yield context
        finally:
            # Log performance metrics
            if performance_tracking and context.metrics:
                logger.info(
                    f"Request {context.request_id} performance metrics: {context.metrics}"
                )


# Protocol validation factory for testing
def create_mock_request_context(
    mock_services: dict[type, ServiceProtocol] | None = None,
) -> AsyncRequestContext:
    """Factory for creating mock request contexts for testing."""
    context = create_async_request_context()

    if mock_services:
        # Pre-populate service cache with mocks
        context._service_cache.update(mock_services)

    return context
