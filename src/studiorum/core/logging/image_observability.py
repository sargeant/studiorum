"""
Comprehensive observability for Phase 4 image processing system using Logfire.

This module provides structured observability, performance tracking, and operational
intelligence for all image processing operations in the Studiorum application.
It integrates with the existing Logfire infrastructure to provide real-time
monitoring, debugging, and dashboard visualization.

Created: 2025-01-23
Status: Phase 4 - Observability Integration
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

import logfire
from pydantic import BaseModel, Field

from studiorum.core.logging.logger import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    ImageMetadata,
    PlacementDecision,
    ProcessedImage,
)

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ImageProcessingStage(str, Enum):
    """Stages of image processing pipeline for tracking."""

    DISCOVERY = "discovery"
    RESOLUTION = "resolution"
    PLACEMENT = "placement"
    OPTIMIZATION = "optimization"
    RENDERING = "rendering"
    GALLERY_CREATION = "gallery_creation"
    SOURCE_SYNC = "source_sync"
    CACHE_OPERATION = "cache_operation"
    BATCH_PROCESSING = "batch_processing"


class ImageProcessingResult(str, Enum):
    """Results of image processing operations."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    SKIPPED = "skipped"
    CACHED = "cached"
    FALLBACK = "fallback"


class CacheOperation(str, Enum):
    """Cache operation types for tracking."""

    HIT = "hit"
    MISS = "miss"
    STORE = "store"
    EVICT = "evict"
    INVALIDATE = "invalidate"


class ImageProcessingMetrics(BaseModel):
    """Structured metrics for image processing operations."""

    operation_id: str = Field(description="Unique operation identifier")
    stage: ImageProcessingStage = Field(description="Processing stage")
    content_type: ContentType = Field(description="Type of content being processed")
    result: ImageProcessingResult = Field(description="Operation result")

    # Performance metrics
    start_time: float = Field(description="Operation start timestamp")
    end_time: float | None = Field(None, description="Operation end timestamp")
    duration_ms: float | None = Field(
        None, description="Operation duration in milliseconds"
    )

    # Resource metrics
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")

    # Context information
    image_count: int = Field(default=1, description="Number of images processed")
    source_name: str | None = Field(None, description="Image source name")
    content_id: str | None = Field(None, description="Content identifier")

    # Quality metrics
    confidence_score: float | None = Field(
        None, description="Placement confidence score"
    )
    fallback_used: bool = Field(default=False, description="Whether fallback was used")

    # Error information
    error_type: str | None = Field(None, description="Error type if operation failed")
    error_message: str | None = Field(None, description="Error message")
    error_context: dict[str, Any] = Field(
        default_factory=dict, description="Error context"
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional operation metadata"
    )


class CacheMetrics(BaseModel):
    """Cache performance and effectiveness metrics."""

    cache_name: str = Field(description="Name of the cache")
    operation: CacheOperation = Field(description="Cache operation type")
    key: str = Field(description="Cache key")
    timestamp: float = Field(description="Operation timestamp")

    # Performance metrics
    lookup_duration_ms: float | None = Field(None, description="Cache lookup duration")
    size_bytes: int | None = Field(None, description="Size of cached data")

    # Context
    content_type: ContentType | None = Field(None, description="Content type")
    hit_ratio: float | None = Field(None, description="Current hit ratio")

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


@dataclass
class ProcessingStatistics:
    """Aggregated processing statistics."""

    operation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0

    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0

    memory_peak_mb: float = 0.0
    cpu_peak_percent: float = 0.0

    content_type_counts: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    stage_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def update_from_metrics(self, metrics: ImageProcessingMetrics) -> None:
        """Update statistics from new metrics."""
        self.operation_count += 1

        if metrics.result == ImageProcessingResult.SUCCESS:
            self.success_count += 1
        else:
            self.failure_count += 1

        if metrics.duration_ms:
            self.total_duration_ms += metrics.duration_ms
            self.avg_duration_ms = self.total_duration_ms / self.operation_count
            self.min_duration_ms = min(self.min_duration_ms, metrics.duration_ms)
            self.max_duration_ms = max(self.max_duration_ms, metrics.duration_ms)

        if metrics.memory_usage_mb:
            self.memory_peak_mb = max(self.memory_peak_mb, metrics.memory_usage_mb)

        if metrics.cpu_usage_percent:
            self.cpu_peak_percent = max(
                self.cpu_peak_percent, metrics.cpu_usage_percent
            )

        self.content_type_counts[metrics.content_type.value] += 1
        self.stage_counts[metrics.stage.value] += 1

        if metrics.error_type:
            self.error_counts[metrics.error_type] += 1

    def update_cache_stats(self, cache_metrics: CacheMetrics) -> None:
        """Update cache statistics."""
        if cache_metrics.operation == CacheOperation.HIT:
            self.cache_hits += 1
        elif cache_metrics.operation == CacheOperation.MISS:
            self.cache_misses += 1

        total_ops = self.cache_hits + self.cache_misses
        if total_ops > 0:
            self.cache_hit_ratio = self.cache_hits / total_ops


class ImageProcessingObserver:
    """Central observer for image processing operations with Logfire integration."""

    def __init__(self) -> None:
        """Initialize the observer."""
        self.stats = ProcessingStatistics()
        self.active_operations: dict[str, ImageProcessingMetrics] = {}
        self._session_id = str(uuid4())[:8]

        # Initialize Logfire instrumentation
        logfire.info(
            "Image processing observer initialized",
            session_id=self._session_id,
            observer_version="1.0.0",
        )

    def start_operation(
        self,
        stage: ImageProcessingStage,
        content_type: ContentType,
        *,
        operation_id: str | None = None,
        content_id: str | None = None,
        source_name: str | None = None,
        image_count: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start tracking an image processing operation.

        Args:
            stage: Processing stage
            content_type: Type of content being processed
            operation_id: Optional operation ID (auto-generated if None)
            content_id: Content identifier
            source_name: Image source name
            image_count: Number of images being processed
            metadata: Additional metadata

        Returns:
            Operation ID for tracking
        """
        if operation_id is None:
            operation_id = str(uuid4())

        metrics = ImageProcessingMetrics(
            operation_id=operation_id,
            stage=stage,
            content_type=content_type,
            result=ImageProcessingResult.SUCCESS,  # Will be updated on completion
            start_time=time.time(),
            content_id=content_id,
            source_name=source_name,
            image_count=image_count,
            metadata=metadata or {},
        )

        self.active_operations[operation_id] = metrics

        # Log operation start to Logfire
        logfire.info(
            "Image processing operation started",
            operation_id=operation_id,
            stage=stage.value,
            content_type=content_type.value,
            content_id=content_id,
            source_name=source_name,
            image_count=image_count,
            session_id=self._session_id,
            **metrics.metadata,
        )

        return operation_id

    def complete_operation(
        self,
        operation_id: str,
        result: ImageProcessingResult,
        *,
        confidence_score: float | None = None,
        fallback_used: bool = False,
        memory_usage_mb: float | None = None,
        cpu_usage_percent: float | None = None,
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Complete tracking of an image processing operation.

        Args:
            operation_id: Operation identifier
            result: Operation result
            confidence_score: Placement confidence score
            fallback_used: Whether fallback was used
            memory_usage_mb: Memory usage in MB
            cpu_usage_percent: CPU usage percentage
            error: Exception if operation failed
            metadata: Additional metadata
        """
        if operation_id not in self.active_operations:
            logger.warning(f"Operation {operation_id} not found in active operations")
            return

        metrics = self.active_operations[operation_id]
        end_time = time.time()

        # Update metrics
        metrics.end_time = end_time
        metrics.duration_ms = (end_time - metrics.start_time) * 1000
        metrics.result = result
        metrics.confidence_score = confidence_score
        metrics.fallback_used = fallback_used
        metrics.memory_usage_mb = memory_usage_mb
        metrics.cpu_usage_percent = cpu_usage_percent

        if error:
            metrics.error_type = type(error).__name__
            metrics.error_message = str(error)
            if hasattr(error, "__dict__"):
                metrics.error_context = dict(error.__dict__)

        if metadata:
            metrics.metadata.update(metadata)

        # Update statistics
        self.stats.update_from_metrics(metrics)

        # Log completion to Logfire
        log_data = {
            "operation_id": operation_id,
            "stage": metrics.stage.value,
            "content_type": metrics.content_type.value,
            "result": result.value,
            "duration_ms": metrics.duration_ms,
            "confidence_score": confidence_score,
            "fallback_used": fallback_used,
            "memory_usage_mb": memory_usage_mb,
            "cpu_usage_percent": cpu_usage_percent,
            "image_count": metrics.image_count,
            "session_id": self._session_id,
        }

        if error:
            log_data.update(
                {
                    "error_type": metrics.error_type,
                    "error_message": metrics.error_message,
                }
            )
            # Log error with key information
            logfire.error(
                "Image processing operation failed",
                operation_id=operation_id,
                stage=metrics.stage.value,
                content_type=metrics.content_type.value,
                duration_ms=metrics.duration_ms,
                error_type=metrics.error_type,
                error_message=metrics.error_message,
            )
        else:
            # Log success with key information
            logfire.info(
                "Image processing operation completed",
                operation_id=operation_id,
                stage=metrics.stage.value,
                content_type=metrics.content_type.value,
                result=result.value,
                duration_ms=metrics.duration_ms,
                image_count=metrics.image_count,
            )

        # Clean up
        del self.active_operations[operation_id]

    def record_cache_operation(
        self,
        cache_name: str,
        operation: CacheOperation,
        key: str,
        *,
        lookup_duration_ms: float | None = None,
        size_bytes: int | None = None,
        content_type: ContentType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a cache operation.

        Args:
            cache_name: Name of the cache
            operation: Cache operation type
            key: Cache key
            lookup_duration_ms: Duration of cache lookup
            size_bytes: Size of cached data
            content_type: Content type
            metadata: Additional metadata
        """
        cache_metrics = CacheMetrics(
            cache_name=cache_name,
            operation=operation,
            key=key,
            timestamp=time.time(),
            lookup_duration_ms=lookup_duration_ms,
            size_bytes=size_bytes,
            content_type=content_type,
            metadata=metadata or {},
        )

        # Update cache statistics
        self.stats.update_cache_stats(cache_metrics)
        cache_metrics.hit_ratio = self.stats.cache_hit_ratio

        # Log to Logfire
        logfire.info(
            "Cache operation recorded",
            cache_name=cache_name,
            operation=operation.value,
            key=key,
            lookup_duration_ms=lookup_duration_ms,
            size_bytes=size_bytes,
            content_type=content_type.value if content_type else None,
            hit_ratio=cache_metrics.hit_ratio,
            session_id=self._session_id,
            **cache_metrics.metadata,
        )

    def record_batch_operation(
        self,
        operation_type: str,
        items_processed: int,
        duration_ms: float,
        success_count: int,
        failure_count: int,
        *,
        content_type: ContentType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a batch processing operation.

        Args:
            operation_type: Type of batch operation
            items_processed: Number of items processed
            duration_ms: Total duration
            success_count: Number of successful operations
            failure_count: Number of failed operations
            content_type: Content type
            metadata: Additional metadata
        """
        throughput = items_processed / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = success_count / items_processed if items_processed > 0 else 0

        logfire.info(
            "Batch operation completed",
            operation_type=operation_type,
            items_processed=items_processed,
            duration_ms=duration_ms,
            success_count=success_count,
            failure_count=failure_count,
            throughput_per_second=throughput,
            success_rate=success_rate,
            content_type=content_type.value if content_type else None,
            session_id=self._session_id,
            **(metadata or {}),
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get current processing statistics.

        Returns:
            Dictionary with current statistics
        """
        return {
            "session_id": self._session_id,
            "operation_count": self.stats.operation_count,
            "success_count": self.stats.success_count,
            "failure_count": self.stats.failure_count,
            "success_rate": (
                self.stats.success_count / self.stats.operation_count
                if self.stats.operation_count > 0
                else 0.0
            ),
            "avg_duration_ms": self.stats.avg_duration_ms,
            "min_duration_ms": (
                self.stats.min_duration_ms
                if self.stats.min_duration_ms != float("inf")
                else 0.0
            ),
            "max_duration_ms": self.stats.max_duration_ms,
            "cache_hit_ratio": self.stats.cache_hit_ratio,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "memory_peak_mb": self.stats.memory_peak_mb,
            "cpu_peak_percent": self.stats.cpu_peak_percent,
            "content_type_distribution": dict(self.stats.content_type_counts),
            "stage_distribution": dict(self.stats.stage_counts),
            "error_distribution": dict(self.stats.error_counts),
            "active_operations": len(self.active_operations),
        }

    def reset_statistics(self) -> None:
        """Reset all statistics (useful for testing)."""
        self.stats = ProcessingStatistics()
        self.active_operations.clear()

        logfire.info(
            "Image processing statistics reset",
            session_id=self._session_id,
        )


# Global observer instance
_observer: ImageProcessingObserver | None = None


def get_image_observer() -> ImageProcessingObserver:
    """Get the global image processing observer."""
    global _observer
    if _observer is None:
        _observer = ImageProcessingObserver()
    return _observer


def reset_image_observer() -> None:
    """Reset the global observer (for testing)."""
    global _observer
    _observer = None


# Context managers for operation tracking


@contextmanager
def track_image_operation(
    stage: ImageProcessingStage,
    content_type: ContentType,
    *,
    operation_id: str | None = None,
    content_id: str | None = None,
    source_name: str | None = None,
    image_count: int = 1,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Context manager for tracking image processing operations.

    Args:
        stage: Processing stage
        content_type: Type of content being processed
        operation_id: Optional operation ID
        content_id: Content identifier
        source_name: Image source name
        image_count: Number of images
        metadata: Additional metadata

    Yields:
        Dictionary with operation tracking functions

    Example:
        >>> with track_image_operation(
        ...     ImageProcessingStage.PLACEMENT,
        ...     ContentType.BESTIARY,
        ...     content_id="ancient-red-dragon"
        ... ) as tracking:
        ...     # Your image processing code here
        ...     tracking["set_confidence"](0.95)
        ...     tracking["set_fallback"](False)
    """
    observer = get_image_observer()
    op_id = observer.start_operation(
        stage=stage,
        content_type=content_type,
        operation_id=operation_id,
        content_id=content_id,
        source_name=source_name,
        image_count=image_count,
        metadata=metadata,
    )

    # Tracking state
    tracking_state: dict[str, Any] = {
        "confidence_score": None,
        "fallback_used": False,
        "memory_usage_mb": None,
        "cpu_usage_percent": None,
        "metadata": {},
    }

    # Helper functions
    def set_confidence(score: float) -> None:
        tracking_state["confidence_score"] = score

    def set_fallback(used: bool) -> None:
        tracking_state["fallback_used"] = used

    def set_resource_usage(
        memory_mb: float | None = None, cpu_percent: float | None = None
    ) -> None:
        if memory_mb is not None:
            tracking_state["memory_usage_mb"] = memory_mb
        if cpu_percent is not None:
            tracking_state["cpu_usage_percent"] = cpu_percent

    def add_metadata(key: str, value: Any) -> None:
        tracking_state["metadata"][key] = value

    tracking_interface = {
        "operation_id": op_id,
        "set_confidence": set_confidence,
        "set_fallback": set_fallback,
        "set_resource_usage": set_resource_usage,
        "add_metadata": add_metadata,
    }

    try:
        yield tracking_interface
        # Success case
        observer.complete_operation(
            op_id,
            ImageProcessingResult.SUCCESS,
            **tracking_state,
        )
    except Exception as e:
        # Error case
        observer.complete_operation(
            op_id,
            ImageProcessingResult.FAILURE,
            error=e,
            **tracking_state,
        )
        raise


@asynccontextmanager
async def track_async_image_operation(
    stage: ImageProcessingStage,
    content_type: ContentType,
    *,
    operation_id: str | None = None,
    content_id: str | None = None,
    source_name: str | None = None,
    image_count: int = 1,
    metadata: dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Async context manager for tracking image processing operations.

    Similar to track_image_operation but for async operations.
    """
    observer = get_image_observer()
    op_id = observer.start_operation(
        stage=stage,
        content_type=content_type,
        operation_id=operation_id,
        content_id=content_id,
        source_name=source_name,
        image_count=image_count,
        metadata=metadata,
    )

    # Tracking state (same as sync version)
    tracking_state: dict[str, Any] = {
        "confidence_score": None,
        "fallback_used": False,
        "memory_usage_mb": None,
        "cpu_usage_percent": None,
        "metadata": {},
    }

    # Helper functions (same as sync version)
    def set_confidence(score: float) -> None:
        tracking_state["confidence_score"] = score

    def set_fallback(used: bool) -> None:
        tracking_state["fallback_used"] = used

    def set_resource_usage(
        memory_mb: float | None = None, cpu_percent: float | None = None
    ) -> None:
        if memory_mb is not None:
            tracking_state["memory_usage_mb"] = memory_mb
        if cpu_percent is not None:
            tracking_state["cpu_usage_percent"] = cpu_percent

    def add_metadata(key: str, value: Any) -> None:
        tracking_state["metadata"][key] = value

    tracking_interface = {
        "operation_id": op_id,
        "set_confidence": set_confidence,
        "set_fallback": set_fallback,
        "set_resource_usage": set_resource_usage,
        "add_metadata": add_metadata,
    }

    try:
        yield tracking_interface
        # Success case
        observer.complete_operation(
            op_id,
            ImageProcessingResult.SUCCESS,
            **tracking_state,
        )
    except Exception as e:
        # Error case
        observer.complete_operation(
            op_id,
            ImageProcessingResult.FAILURE,
            error=e,
            **tracking_state,
        )
        raise


# Decorators for automatic instrumentation


def observe_image_processing(
    stage: ImageProcessingStage,
    content_type: ContentType | None = None,
    *,
    extract_content_type: Callable[[Any], ContentType] | None = None,
    extract_content_id: Callable[[Any], str | None] | None = None,
    extract_metadata: Callable[[Any], dict[str, Any]] | None = None,
) -> Callable[[F], F]:
    """Decorator for automatically instrumenting image processing functions.

    Args:
        stage: Processing stage
        content_type: Content type (if static)
        extract_content_type: Function to extract content type from args
        extract_content_id: Function to extract content ID from args
        extract_metadata: Function to extract metadata from args

    Example:
        >>> @observe_image_processing(
        ...     ImageProcessingStage.PLACEMENT,
        ...     extract_content_type=lambda args: args[1].content_type,
        ...     extract_content_id=lambda args: args[1].content_id,
        ... )
        ... def place_image(image_metadata, context):
        ...     # Your placement logic here
        ...     return placement_decision
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract context information
                resolved_content_type = (
                    content_type
                    or (extract_content_type and extract_content_type(args))
                    or ContentType.UNKNOWN
                )
                resolved_content_id = extract_content_id and extract_content_id(args)
                resolved_metadata = extract_metadata and extract_metadata(args)

                async with track_async_image_operation(
                    stage=stage,
                    content_type=resolved_content_type,
                    content_id=resolved_content_id,
                    metadata=resolved_metadata,
                ) as tracking:
                    result = await func(*args, **kwargs)

                    # Extract confidence if available
                    if hasattr(result, "confidence"):
                        tracking["set_confidence"](result.confidence)

                    return result

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract context information
                resolved_content_type = (
                    content_type
                    or (extract_content_type and extract_content_type(args))
                    or ContentType.UNKNOWN
                )
                resolved_content_id = extract_content_id and extract_content_id(args)
                resolved_metadata = extract_metadata and extract_metadata(args)

                with track_image_operation(
                    stage=stage,
                    content_type=resolved_content_type,
                    content_id=resolved_content_id,
                    metadata=resolved_metadata,
                ) as tracking:
                    result = func(*args, **kwargs)

                    # Extract confidence if available
                    if hasattr(result, "confidence"):
                        tracking["set_confidence"](result.confidence)

                    return result

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def observe_cache_operation(cache_name: str) -> Callable[[F], F]:
    """Decorator for automatically instrumenting cache operations.

    Args:
        cache_name: Name of the cache

    Example:
        >>> @observe_cache_operation("image_placement_cache")
        ... def get_cached_placement(self, key):
        ...     # Your cache logic here
        ...     return cached_value
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = str(args[1]) if len(args) > 1 else "unknown"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000

                operation = (
                    CacheOperation.HIT if result is not None else CacheOperation.MISS
                )

                get_image_observer().record_cache_operation(
                    cache_name=cache_name,
                    operation=operation,
                    key=cache_key,
                    lookup_duration_ms=duration,
                )

                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000

                get_image_observer().record_cache_operation(
                    cache_name=cache_name,
                    operation=CacheOperation.MISS,
                    key=cache_key,
                    lookup_duration_ms=duration,
                    metadata={"error": str(e)},
                )

                raise

        return wrapper  # type: ignore[return-value]

    return decorator


# Dashboard and reporting utilities


def generate_performance_report() -> dict[str, Any]:
    """Generate a comprehensive performance report.

    Returns:
        Dictionary with performance insights and recommendations
    """
    observer = get_image_observer()
    stats = observer.get_statistics()

    # Performance analysis
    performance_issues = []
    recommendations = []

    if stats["success_rate"] < 0.95:
        performance_issues.append("success_rate")
        recommendations.append("Success rate below 95% - investigate error patterns")

    if stats["cache_hit_ratio"] < 0.7:
        performance_issues.append("cache_hit_ratio")
        recommendations.append("Cache hit ratio below 70% - review caching strategy")

    if stats["avg_duration_ms"] > 5000:  # 5 seconds
        performance_issues.append("avg_duration")
        recommendations.append(
            "Average operation time above 5s - optimize processing pipeline"
        )

    # Determine grade based on number and severity of issues
    if not performance_issues:
        performance_grade = "A"
    elif "success_rate" in performance_issues:
        performance_grade = "C"  # Success rate issues are most critical
    elif len(performance_issues) >= 2:
        performance_grade = "C"  # Multiple issues
    else:
        performance_grade = "B"  # Single non-critical issue

    return {
        "timestamp": datetime.now().isoformat(),
        "session_id": stats["session_id"],
        "performance_grade": performance_grade,
        "recommendations": recommendations,
        "statistics": stats,
        "health_indicators": {
            "success_rate_healthy": stats["success_rate"] >= 0.95,
            "cache_effective": stats["cache_hit_ratio"] >= 0.7,
            "performance_acceptable": stats["avg_duration_ms"] <= 5000,
            "memory_usage_reasonable": stats["memory_peak_mb"] <= 1000,  # 1GB
        },
    }


def log_performance_summary() -> None:
    """Log a performance summary to Logfire."""
    report = generate_performance_report()

    logfire.info(
        "Image processing performance summary",
        **report["statistics"],
        performance_grade=report["performance_grade"],
        recommendations=report["recommendations"],
        health_indicators=report["health_indicators"],
    )


# CLI-friendly progress reporting


class ProgressReporter:
    """CLI-friendly progress reporting for image operations."""

    def __init__(self, quiet: bool = False) -> None:
        """Initialize progress reporter.

        Args:
            quiet: Whether to suppress console output
        """
        self.quiet = quiet
        self.start_time = time.time()
        self.last_update = 0.0

    def report_progress(
        self,
        current: int,
        total: int,
        operation: str = "Processing",
        *,
        force: bool = False,
    ) -> None:
        """Report progress to console.

        Args:
            current: Current progress
            total: Total items
            operation: Operation description
            force: Force update even if too soon
        """
        if self.quiet:
            return

        now = time.time()
        if not force and now - self.last_update < 0.5:  # Throttle updates
            return

        self.last_update = now

        percentage = (current / total) * 100 if total > 0 else 0
        elapsed = now - self.start_time

        if current > 0:
            eta = (elapsed / current) * (total - current)
            eta_str = f"ETA: {eta:.1f}s"
        else:
            eta_str = "ETA: --"

        print(
            f"\r{operation}: {current}/{total} ({percentage:.1f}%) {eta_str}",
            end="",
            flush=True,
        )

        if current >= total:
            print()  # New line when complete

    def report_completion(self, operation: str, count: int, success_count: int) -> None:
        """Report operation completion.

        Args:
            operation: Operation description
            count: Total items processed
            success_count: Number of successful operations
        """
        if self.quiet:
            return

        elapsed = time.time() - self.start_time
        rate = count / elapsed if elapsed > 0 else 0
        success_rate = (success_count / count * 100) if count > 0 else 0

        print(
            f"{operation} completed: {success_count}/{count} ({success_rate:.1f}%) "
            f"in {elapsed:.1f}s ({rate:.1f} ops/s)"
        )


# MCP-friendly async resource monitoring


class AsyncResourceMonitor:
    """Monitor resource usage for async operations."""

    def __init__(self) -> None:
        """Initialize resource monitor."""
        self.monitors: dict[str, dict[str, Any]] = {}

    async def start_monitoring(self, operation_id: str) -> None:
        """Start monitoring resources for an operation.

        Args:
            operation_id: Operation identifier
        """
        import psutil

        process = psutil.Process()
        self.monitors[operation_id] = {
            "start_memory": process.memory_info().rss / 1024 / 1024,  # MB
            "start_cpu": process.cpu_percent(),
            "start_time": time.time(),
        }

    async def stop_monitoring(self, operation_id: str) -> dict[str, float]:
        """Stop monitoring and return resource usage.

        Args:
            operation_id: Operation identifier

        Returns:
            Dictionary with resource usage metrics
        """
        if operation_id not in self.monitors:
            return {}

        import psutil

        monitor_data = self.monitors.pop(operation_id)
        process = psutil.Process()

        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        current_time = time.time()

        return {
            "memory_usage_mb": current_memory - monitor_data["start_memory"],
            "peak_memory_mb": current_memory,
            "duration_ms": (current_time - monitor_data["start_time"]) * 1000,
        }


# Global resource monitor instance
_resource_monitor: AsyncResourceMonitor | None = None


def get_resource_monitor() -> AsyncResourceMonitor:
    """Get the global resource monitor."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = AsyncResourceMonitor()
    return _resource_monitor
