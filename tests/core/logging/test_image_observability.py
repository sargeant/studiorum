"""
Tests for image processing observability module.

This module tests the comprehensive observability features including
Logfire integration, performance tracking, and operational intelligence.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from studiorum.core.logging.image_observability import (
    AsyncResourceMonitor,
    CacheMetrics,
    CacheOperation,
    ImageProcessingMetrics,
    ImageProcessingObserver,
    ImageProcessingResult,
    ImageProcessingStage,
    ProgressReporter,
    generate_performance_report,
    get_image_observer,
    get_resource_monitor,
    log_performance_summary,
    observe_cache_operation,
    observe_image_processing,
    reset_image_observer,
    track_async_image_operation,
    track_image_operation,
)
from studiorum.latex_engine.core.images.placement_models import ContentType


class TestImageProcessingObserver:
    """Test image processing observer functionality."""

    def setup_method(self) -> None:
        """Reset observer before each test."""
        reset_image_observer()

    def test_observer_initialization(self) -> None:
        """Test observer initializes correctly."""
        observer = get_image_observer()

        assert observer is not None
        assert observer.stats.operation_count == 0
        assert len(observer.active_operations) == 0
        assert observer._session_id is not None

    def test_start_operation(self) -> None:
        """Test starting an operation."""
        observer = get_image_observer()

        op_id = observer.start_operation(
            stage=ImageProcessingStage.PLACEMENT,
            content_type=ContentType.BESTIARY,
            content_id="ancient-red-dragon",
            source_name="dnd-beyond",
            image_count=2,
            metadata={"test": "data"},
        )

        assert op_id is not None
        assert op_id in observer.active_operations

        metrics = observer.active_operations[op_id]
        assert metrics.stage == ImageProcessingStage.PLACEMENT
        assert metrics.content_type == ContentType.BESTIARY
        assert metrics.content_id == "ancient-red-dragon"
        assert metrics.source_name == "dnd-beyond"
        assert metrics.image_count == 2
        assert metrics.metadata["test"] == "data"

    def test_complete_operation_success(self) -> None:
        """Test completing a successful operation."""
        observer = get_image_observer()

        op_id = observer.start_operation(
            stage=ImageProcessingStage.PLACEMENT,
            content_type=ContentType.BESTIARY,
        )

        # Wait a bit for duration
        time.sleep(0.01)

        observer.complete_operation(
            op_id,
            ImageProcessingResult.SUCCESS,
            confidence_score=0.95,
            fallback_used=False,
            memory_usage_mb=50.0,
            cpu_usage_percent=25.0,
            metadata={"extra": "info"},
        )

        # Check operation was removed from active
        assert op_id not in observer.active_operations

        # Check statistics were updated
        assert observer.stats.operation_count == 1
        assert observer.stats.success_count == 1
        assert observer.stats.failure_count == 0
        assert observer.stats.avg_duration_ms > 0
        assert observer.stats.memory_peak_mb == 50.0
        assert observer.stats.cpu_peak_percent == 25.0

    def test_complete_operation_failure(self) -> None:
        """Test completing a failed operation."""
        observer = get_image_observer()

        op_id = observer.start_operation(
            stage=ImageProcessingStage.OPTIMIZATION,
            content_type=ContentType.ADVENTURE,
        )

        error = ValueError("Test error")

        observer.complete_operation(
            op_id,
            ImageProcessingResult.FAILURE,
            error=error,
        )

        # Check statistics
        assert observer.stats.operation_count == 1
        assert observer.stats.success_count == 0
        assert observer.stats.failure_count == 1
        assert observer.stats.error_counts["ValueError"] == 1

    def test_record_cache_operation(self) -> None:
        """Test recording cache operations."""
        observer = get_image_observer()

        # Record cache hit
        observer.record_cache_operation(
            cache_name="placement_cache",
            operation=CacheOperation.HIT,
            key="bestiary:dragon",
            lookup_duration_ms=5.0,
            size_bytes=1024,
            content_type=ContentType.BESTIARY,
        )

        # Record cache miss
        observer.record_cache_operation(
            cache_name="placement_cache",
            operation=CacheOperation.MISS,
            key="bestiary:unicorn",
            lookup_duration_ms=2.0,
        )

        # Check cache statistics
        assert observer.stats.cache_hits == 1
        assert observer.stats.cache_misses == 1
        assert observer.stats.cache_hit_ratio == 0.5

    def test_record_batch_operation(self) -> None:
        """Test recording batch operations."""
        observer = get_image_observer()

        with patch(
            "studiorum.core.logging.image_observability.logfire"
        ) as mock_logfire:
            observer.record_batch_operation(
                operation_type="adventure_processing",
                items_processed=100,
                duration_ms=5000.0,
                success_count=95,
                failure_count=5,
                content_type=ContentType.ADVENTURE,
                metadata={"batch_id": "test-batch"},
            )

            # Check logfire was called
            mock_logfire.info.assert_called_once()
            call_args = mock_logfire.info.call_args
            assert call_args[0][0] == "Batch operation completed"
            assert call_args[1]["items_processed"] == 100
            assert (
                call_args[1]["throughput_per_second"] == 20.0
            )  # 100 items / 5 seconds
            assert call_args[1]["success_rate"] == 0.95

    def test_get_statistics(self) -> None:
        """Test getting statistics."""
        observer = get_image_observer()

        # Add some operations
        for i in range(5):
            op_id = observer.start_operation(
                stage=ImageProcessingStage.DISCOVERY,
                content_type=ContentType.BESTIARY,
            )
            observer.complete_operation(
                op_id,
                ImageProcessingResult.SUCCESS
                if i < 4
                else ImageProcessingResult.FAILURE,
                confidence_score=0.8 + (i * 0.05),
            )

        stats = observer.get_statistics()

        assert stats["operation_count"] == 5
        assert stats["success_count"] == 4
        assert stats["failure_count"] == 1
        assert stats["success_rate"] == 0.8
        assert stats["content_type_distribution"]["bestiary"] == 5
        assert stats["stage_distribution"]["discovery"] == 5


class TestContextManagers:
    """Test context managers for operation tracking."""

    def setup_method(self) -> None:
        """Reset observer before each test."""
        reset_image_observer()

    def test_track_image_operation_success(self) -> None:
        """Test sync context manager for successful operation."""
        with track_image_operation(
            stage=ImageProcessingStage.PLACEMENT,
            content_type=ContentType.BESTIARY,
            content_id="dragon",
        ) as tracking:
            tracking["set_confidence"](0.9)
            tracking["set_fallback"](False)
            tracking["add_metadata"]("test_key", "test_value")

        observer = get_image_observer()
        stats = observer.get_statistics()

        assert stats["operation_count"] == 1
        assert stats["success_count"] == 1

    def test_track_image_operation_failure(self) -> None:
        """Test sync context manager for failed operation."""
        with pytest.raises(ValueError):
            with track_image_operation(
                stage=ImageProcessingStage.OPTIMIZATION,
                content_type=ContentType.ADVENTURE,
            ) as tracking:
                tracking["set_confidence"](0.5)
                raise ValueError("Test error")

        observer = get_image_observer()
        stats = observer.get_statistics()

        assert stats["operation_count"] == 1
        assert stats["failure_count"] == 1
        assert stats["error_distribution"]["ValueError"] == 1

    @pytest.mark.asyncio
    async def test_track_async_image_operation_success(self) -> None:
        """Test async context manager for successful operation."""
        async with track_async_image_operation(
            stage=ImageProcessingStage.RENDERING,
            content_type=ContentType.ITEM_COLLECTION,
            image_count=3,
        ) as tracking:
            tracking["set_confidence"](0.85)
            tracking["set_resource_usage"](memory_mb=30.0, cpu_percent=15.0)
            await asyncio.sleep(0.01)  # Simulate async work

        observer = get_image_observer()
        stats = observer.get_statistics()

        assert stats["operation_count"] == 1
        assert stats["success_count"] == 1

    @pytest.mark.asyncio
    async def test_track_async_image_operation_failure(self) -> None:
        """Test async context manager for failed operation."""
        with pytest.raises(RuntimeError):
            async with track_async_image_operation(
                stage=ImageProcessingStage.GALLERY_CREATION,
                content_type=ContentType.ADVENTURE,
            ) as tracking:
                tracking["set_fallback"](True)
                await asyncio.sleep(0.01)
                raise RuntimeError("Async error")

        observer = get_image_observer()
        stats = observer.get_statistics()

        assert stats["operation_count"] == 1
        assert stats["failure_count"] == 1
        assert stats["error_distribution"]["RuntimeError"] == 1


class TestDecorators:
    """Test automatic instrumentation decorators."""

    def setup_method(self) -> None:
        """Reset observer before each test."""
        reset_image_observer()

    def test_observe_image_processing_sync(self) -> None:
        """Test image processing decorator on sync function."""

        @observe_image_processing(
            stage=ImageProcessingStage.PLACEMENT,
            content_type=ContentType.BESTIARY,
        )
        def place_image(image_data: dict) -> dict:
            return {"placement": "top", "confidence": 0.9}

        result = place_image({"name": "dragon"})

        assert result["placement"] == "top"

        observer = get_image_observer()
        stats = observer.get_statistics()
        assert stats["operation_count"] == 1
        assert stats["success_count"] == 1

    def test_observe_image_processing_with_extractors(self) -> None:
        """Test decorator with content extraction functions."""

        def extract_content_type(args) -> ContentType:
            return (
                ContentType.ADVENTURE
                if args[0]["type"] == "adventure"
                else ContentType.BESTIARY
            )

        def extract_content_id(args) -> str:
            return args[0]["id"]

        @observe_image_processing(
            stage=ImageProcessingStage.DISCOVERY,
            extract_content_type=extract_content_type,
            extract_content_id=extract_content_id,
        )
        def discover_images(content: dict) -> list[str]:
            return ["image1.jpg", "image2.jpg"]

        result = discover_images({"type": "adventure", "id": "storm-kings-thunder"})

        assert len(result) == 2

        observer = get_image_observer()
        stats = observer.get_statistics()
        assert stats["operation_count"] == 1
        assert stats["content_type_distribution"]["adventure"] == 1

    @pytest.mark.asyncio
    async def test_observe_image_processing_async(self) -> None:
        """Test decorator on async function."""

        @observe_image_processing(
            stage=ImageProcessingStage.OPTIMIZATION,
            content_type=ContentType.ITEM_COLLECTION,
        )
        async def optimize_images(images: list) -> list:
            await asyncio.sleep(0.01)
            return [{"optimized": True} for _ in images]

        result = await optimize_images(["img1", "img2"])

        assert len(result) == 2
        assert all(img["optimized"] for img in result)

        observer = get_image_observer()
        stats = observer.get_statistics()
        assert stats["operation_count"] == 1
        assert stats["success_count"] == 1

    def test_observe_cache_operation(self) -> None:
        """Test cache operation decorator."""

        @observe_cache_operation("test_cache")
        def get_cached_data(self, key: str) -> str | None:
            # Simulate cache logic
            if key == "hit":
                return "cached_value"
            return None

        # Test cache hit
        result = get_cached_data(None, "hit")
        assert result == "cached_value"

        # Test cache miss
        result = get_cached_data(None, "miss")
        assert result is None

        observer = get_image_observer()
        assert observer.stats.cache_hits == 1
        assert observer.stats.cache_misses == 1
        assert observer.stats.cache_hit_ratio == 0.5


class TestPerformanceReporting:
    """Test performance reporting and dashboard utilities."""

    def setup_method(self) -> None:
        """Reset observer before each test."""
        reset_image_observer()

    def test_generate_performance_report(self) -> None:
        """Test performance report generation."""
        observer = get_image_observer()

        # Add some successful operations
        for i in range(10):
            op_id = observer.start_operation(
                stage=ImageProcessingStage.PLACEMENT,
                content_type=ContentType.BESTIARY,
            )
            observer.complete_operation(
                op_id,
                ImageProcessingResult.SUCCESS,
                confidence_score=0.9,
            )

        # Add cache operations with good hit ratio (>=70%)
        for i in range(7):  # 7 hits
            observer.record_cache_operation(
                "test_cache",
                CacheOperation.HIT,
                f"key{i}",
            )
        for i in range(3):  # 3 misses
            observer.record_cache_operation(
                "test_cache",
                CacheOperation.MISS,
                f"miss_key{i}",
            )

        report = generate_performance_report()

        assert report["performance_grade"] == "A"
        assert len(report["recommendations"]) == 0
        assert report["health_indicators"]["success_rate_healthy"] is True
        assert report["health_indicators"]["cache_effective"] is True  # 70% >= 70%
        assert report["statistics"]["operation_count"] == 10
        assert report["statistics"]["success_rate"] == 1.0

    def test_generate_performance_report_poor_performance(self) -> None:
        """Test performance report with poor metrics."""
        observer = get_image_observer()

        # Add failed operations
        for i in range(10):
            op_id = observer.start_operation(
                stage=ImageProcessingStage.PLACEMENT,
                content_type=ContentType.BESTIARY,
            )
            result = (
                ImageProcessingResult.SUCCESS
                if i < 9
                else ImageProcessingResult.FAILURE
            )
            observer.complete_operation(op_id, result)

        report = generate_performance_report()

        assert report["performance_grade"] == "C"  # Success rate < 95%
        assert any("Success rate below 95%" in rec for rec in report["recommendations"])
        assert report["health_indicators"]["success_rate_healthy"] is False

    def test_log_performance_summary(self) -> None:
        """Test logging performance summary."""
        observer = get_image_observer()

        # Add some operations
        op_id = observer.start_operation(
            stage=ImageProcessingStage.DISCOVERY,
            content_type=ContentType.ADVENTURE,
        )
        observer.complete_operation(op_id, ImageProcessingResult.SUCCESS)

        with patch(
            "studiorum.core.logging.image_observability.logfire"
        ) as mock_logfire:
            log_performance_summary()

            mock_logfire.info.assert_called_once()
            call_args = mock_logfire.info.call_args
            assert call_args[0][0] == "Image processing performance summary"


class TestProgressReporter:
    """Test CLI-friendly progress reporting."""

    def test_progress_reporter_quiet(self) -> None:
        """Test progress reporter in quiet mode."""
        reporter = ProgressReporter(quiet=True)

        # Should not raise any exceptions
        reporter.report_progress(5, 10, "Testing")
        reporter.report_completion("Testing", 10, 9)

    def test_progress_reporter_verbose(self, capsys) -> None:
        """Test progress reporter verbose output."""
        reporter = ProgressReporter(quiet=False)

        reporter.report_progress(5, 10, "Testing", force=True)
        captured = capsys.readouterr()
        assert "Testing: 5/10 (50.0%)" in captured.out

        reporter.report_completion("Testing", 10, 9)
        captured = capsys.readouterr()
        assert "Testing completed: 9/10 (90.0%)" in captured.out


class TestAsyncResourceMonitor:
    """Test async resource monitoring."""

    @pytest.mark.asyncio
    async def test_resource_monitoring(self) -> None:
        """Test basic resource monitoring."""
        monitor = get_resource_monitor()

        op_id = "test_operation"
        await monitor.start_monitoring(op_id)

        # Simulate some work
        await asyncio.sleep(0.01)

        metrics = await monitor.stop_monitoring(op_id)

        assert "duration_ms" in metrics
        assert metrics["duration_ms"] > 0
        # Memory metrics depend on system, just check they exist
        assert "memory_usage_mb" in metrics
        assert "peak_memory_mb" in metrics

    @pytest.mark.asyncio
    async def test_resource_monitoring_missing_operation(self) -> None:
        """Test monitoring non-existent operation."""
        monitor = get_resource_monitor()

        metrics = await monitor.stop_monitoring("nonexistent")

        assert metrics == {}


class TestImageProcessingMetrics:
    """Test metrics model functionality."""

    def test_image_processing_metrics_creation(self) -> None:
        """Test creating image processing metrics."""
        metrics = ImageProcessingMetrics(
            operation_id="test_op",
            stage=ImageProcessingStage.PLACEMENT,
            content_type=ContentType.BESTIARY,
            result=ImageProcessingResult.SUCCESS,
            start_time=time.time(),
            image_count=2,
            confidence_score=0.85,
        )

        assert metrics.operation_id == "test_op"
        assert metrics.stage == ImageProcessingStage.PLACEMENT
        assert metrics.content_type == ContentType.BESTIARY
        assert metrics.image_count == 2
        assert metrics.confidence_score == 0.85

    def test_cache_metrics_creation(self) -> None:
        """Test creating cache metrics."""
        metrics = CacheMetrics(
            cache_name="test_cache",
            operation=CacheOperation.HIT,
            key="test_key",
            timestamp=time.time(),
            lookup_duration_ms=5.0,
            size_bytes=1024,
        )

        assert metrics.cache_name == "test_cache"
        assert metrics.operation == CacheOperation.HIT
        assert metrics.key == "test_key"
        assert metrics.lookup_duration_ms == 5.0
        assert metrics.size_bytes == 1024
