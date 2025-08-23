"""
Service integration module for image processing observability.

This module provides service registration and factory functions for integrating
the observability system with the existing image processing services through
the ModernServiceContainer.

Created: 2025-01-23
Status: Phase 4 - Observability Integration
"""

from __future__ import annotations

import logging
from typing import Any

from studiorum.core.logging.image_observability import (
    AsyncResourceMonitor,
    ImageProcessingObserver,
    get_image_observer,
    get_resource_monitor,
)
from studiorum.core.services.lifecycle import CleanupPriority, ServiceLifecycle
from studiorum.core.services.protocols import Protocol

logger = logging.getLogger(__name__)


class ImageObservabilityProtocol(Protocol):
    """Protocol for image processing observability service."""

    def start_operation(
        self,
        stage: str,
        content_type: str,
        *,
        operation_id: str | None = None,
        content_id: str | None = None,
        source_name: str | None = None,
        image_count: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start tracking an image processing operation."""
        ...

    def complete_operation(
        self,
        operation_id: str,
        result: str,
        *,
        confidence_score: float | None = None,
        fallback_used: bool = False,
        memory_usage_mb: float | None = None,
        cpu_usage_percent: float | None = None,
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Complete tracking of an image processing operation."""
        ...

    def record_cache_operation(
        self,
        cache_name: str,
        operation: str,
        key: str,
        *,
        lookup_duration_ms: float | None = None,
        size_bytes: int | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a cache operation."""
        ...

    def get_statistics(self) -> dict[str, Any]:
        """Get current processing statistics."""
        ...

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        ...


class AsyncResourceMonitorProtocol(Protocol):
    """Protocol for async resource monitoring service."""

    async def start_monitoring(self, operation_id: str) -> None:
        """Start monitoring resources for an operation."""
        ...

    async def stop_monitoring(self, operation_id: str) -> dict[str, float]:
        """Stop monitoring and return resource usage metrics."""
        ...


# Service factory functions


def create_image_observability_service() -> ImageProcessingObserver:
    """Create image processing observability service.

    Returns:
        ImageProcessingObserver instance
    """
    logger.debug("Creating image observability service")
    return get_image_observer()


def create_resource_monitor_service() -> AsyncResourceMonitor:
    """Create async resource monitor service.

    Returns:
        AsyncResourceMonitor instance
    """
    logger.debug("Creating async resource monitor service")
    return get_resource_monitor()


def register_observability_services(container: Any) -> None:  # ModernServiceContainer
    """Register observability services with the service container.

    Args:
        container: Modern service container for registration

    This function registers observability services that provide comprehensive
    monitoring and performance tracking for image processing operations.
    These services are designed to work with both CLI and MCP contexts.

    Service Architecture:
    - ImageObservabilityProtocol: SINGLETON (global observer, shared state)
    - AsyncResourceMonitorProtocol: SINGLETON (system resource monitoring)

    Integration Points:
    - Automatic instrumentation through decorators
    - Context managers for operation tracking
    - Performance reporting and dashboard data
    - Logfire integration for structured logging
    """
    logger.info("Registering image observability services")

    # Image Processing Observer - Central observability service
    container.register_service(
        ImageObservabilityProtocol,  # type: ignore[type-abstract]
        create_image_observability_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),  # No dependencies, uses global state
        hot_reloadable=False,  # Observer state should persist
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered ImageObservabilityProtocol as singleton")

    # Async Resource Monitor - System resource tracking
    container.register_service(
        AsyncResourceMonitorProtocol,  # type: ignore[type-abstract]
        create_resource_monitor_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),  # System-level monitoring
        hot_reloadable=False,  # Monitor state should persist
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered AsyncResourceMonitorProtocol as singleton")

    logger.info("Observability services registered successfully")


def get_observability_service_summary() -> dict[str, Any]:
    """Get summary of observability service registrations for diagnostics.

    Returns:
        Dictionary with service lifecycle and integration information
    """
    return {
        "singletons": {
            "ImageObservabilityProtocol": {
                "dependencies": [],
                "hot_reloadable": False,
                "description": "Central image processing observability with Logfire integration",
                "features": [
                    "Operation tracking and timing",
                    "Performance metrics collection",
                    "Cache hit/miss monitoring",
                    "Error tracking and context",
                    "Batch processing insights",
                    "Resource usage monitoring",
                ],
            },
            "AsyncResourceMonitorProtocol": {
                "dependencies": [],
                "hot_reloadable": False,
                "description": "System resource monitoring for async operations",
                "features": [
                    "Memory usage tracking",
                    "CPU utilization monitoring",
                    "Operation duration measurement",
                    "Resource leak detection",
                ],
            },
        },
        "scoped": {},
        "total_services": 2,
        "phase": "Phase 4 - Observability Integration",
        "status": "Production Ready",
        "integration_points": {
            "decorators": [
                "@observe_image_processing",
                "@observe_cache_operation",
            ],
            "context_managers": [
                "track_image_operation",
                "track_async_image_operation",
            ],
            "reporting": [
                "generate_performance_report",
                "log_performance_summary",
                "ProgressReporter",
            ],
            "logfire_integration": [
                "Structured operation logging",
                "Performance metrics tracking",
                "Error context preservation",
                "Dashboard data generation",
            ],
        },
    }


# Enhanced service wrapper with observability integration


class ObservableImageService:
    """Wrapper that adds observability to any image service.

    This wrapper can be used to add comprehensive observability to existing
    image processing services without modifying their core implementation.
    """

    def __init__(self, wrapped_service: Any, observer: ImageProcessingObserver) -> None:
        """Initialize observable service wrapper.

        Args:
            wrapped_service: The service to wrap with observability
            observer: Observability service instance
        """
        self._wrapped = wrapped_service
        self._observer = observer

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to wrapped service with observability."""
        attr = getattr(self._wrapped, name)

        # If it's a callable method, wrap it with observability
        if callable(attr):
            return self._create_observable_method(name, attr)

        return attr

    def _create_observable_method(self, method_name: str, method: Any) -> Any:
        """Create observable version of a method."""
        import asyncio
        import functools

        from studiorum.core.logging.image_observability import (
            ImageProcessingStage,
            track_async_image_operation,
            track_image_operation,
        )
        from studiorum.latex_engine.core.images.placement_models import ContentType

        # Map method names to processing stages
        stage_mapping = {
            "discover_images": ImageProcessingStage.DISCOVERY,
            "place_images": ImageProcessingStage.PLACEMENT,
            "optimize_images": ImageProcessingStage.OPTIMIZATION,
            "render_images": ImageProcessingStage.RENDERING,
            "create_gallery": ImageProcessingStage.GALLERY_CREATION,
            "sync_sources": ImageProcessingStage.SOURCE_SYNC,
        }

        stage = stage_mapping.get(method_name, ImageProcessingStage.DISCOVERY)

        if asyncio.iscoroutinefunction(method):

            @functools.wraps(method)
            async def async_observable_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with track_async_image_operation(
                    stage=stage,
                    content_type=ContentType.UNKNOWN,  # Could be extracted from args
                    metadata={
                        "method": method_name,
                        "service": type(self._wrapped).__name__,
                    },
                ) as tracking:
                    result = await method(*args, **kwargs)

                    # Extract metadata from result if available
                    if hasattr(result, "__len__"):
                        tracking["add_metadata"]("result_count", len(result))

                    return result

            return async_observable_wrapper
        else:

            @functools.wraps(method)
            def sync_observable_wrapper(*args: Any, **kwargs: Any) -> Any:
                with track_image_operation(
                    stage=stage,
                    content_type=ContentType.UNKNOWN,  # Could be extracted from args
                    metadata={
                        "method": method_name,
                        "service": type(self._wrapped).__name__,
                    },
                ) as tracking:
                    result = method(*args, **kwargs)

                    # Extract metadata from result if available
                    if hasattr(result, "__len__"):
                        tracking["add_metadata"]("result_count", len(result))

                    return result

            return sync_observable_wrapper


# Service factory for creating observable service wrappers


def create_observable_service_wrapper(
    service_protocol: type,
    service_factory: Any,
    observer: ImageProcessingObserver | None = None,
) -> Any:
    """Create an observable wrapper for any service.

    Args:
        service_protocol: Service protocol type
        service_factory: Factory function for creating the service
        observer: Optional observer instance (uses global if None)

    Returns:
        Factory function that creates observable service
    """

    def wrapper_factory(*args: Any, **kwargs: Any) -> ObservableImageService:
        service_instance = service_factory(*args, **kwargs)
        observer_instance = observer or get_image_observer()
        return ObservableImageService(service_instance, observer_instance)

    return wrapper_factory


# Utility functions for integrating observability with existing services


def enhance_service_with_observability(service_instance: Any) -> ObservableImageService:
    """Enhance an existing service instance with observability.

    Args:
        service_instance: Existing service to enhance

    Returns:
        Observable wrapper around the service
    """
    observer = get_image_observer()
    return ObservableImageService(service_instance, observer)


def register_enhanced_image_services(container: Any) -> None:
    """Register enhanced versions of image services with observability.

    This function can be used instead of the standard service registration
    to automatically add observability to all image processing services.

    Args:
        container: Modern service container for registration
    """
    from studiorum.core.services.image_services import register_image_services
    from studiorum.core.services.protocols import (
        EnhancedImagePlacerProtocol,
        GalleryProcessorProtocol,
        ImageSourceRegistryProtocol,
    )

    # First register observability services
    register_observability_services(container)

    # Then register enhanced image services with observability wrappers
    logger.info("Registering enhanced image services with observability")

    # Get the original factories
    from studiorum.core.services.image_factories.image_factory import (
        create_enhanced_image_placer_service,
        create_gallery_processor_service,
        create_image_source_registry_service,
    )

    # Register enhanced versions
    observer = get_image_observer()

    container.register_service(
        ImageSourceRegistryProtocol,  # type: ignore[type-abstract]
        create_observable_service_wrapper(
            ImageSourceRegistryProtocol,
            create_image_source_registry_service,
            observer,
        ),
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(ImageObservabilityProtocol,),
        hot_reloadable=True,
        cleanup_priority=CleanupPriority.CORE_RESOURCES,
    )

    container.register_service(
        EnhancedImagePlacerProtocol,  # type: ignore[type-abstract]
        create_observable_service_wrapper(
            EnhancedImagePlacerProtocol,
            create_enhanced_image_placer_service,
            observer,
        ),
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(ImageSourceRegistryProtocol, ImageObservabilityProtocol),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )

    container.register_service(
        GalleryProcessorProtocol,  # type: ignore[type-abstract]
        create_observable_service_wrapper(
            GalleryProcessorProtocol,
            create_gallery_processor_service,
            observer,
        ),
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(EnhancedImagePlacerProtocol, ImageObservabilityProtocol),
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )

    logger.info("Enhanced image services with observability registered successfully")
