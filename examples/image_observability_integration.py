#!/usr/bin/env python3
"""
Comprehensive example of image processing observability integration.

This example demonstrates how to integrate the image observability module
with existing image processing services for comprehensive monitoring,
performance tracking, and operational intelligence.

Usage:
    python examples/image_observability_integration.py
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from studiorum.core.logging.image_observability import (
    CacheOperation,
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
from studiorum.core.logging.logger import setup_logging
from studiorum.latex_engine.core.images.placement_models import ContentType


class MockImageService:
    """Mock image service for demonstration purposes."""

    def __init__(self) -> None:
        """Initialize mock service."""
        self._cache: dict[str, Any] = {}

    @observe_image_processing(
        stage=ImageProcessingStage.DISCOVERY,
        content_type=ContentType.BESTIARY,  # Default content type for simplicity
    )
    def discover_images(self, content_id: str, content_type: ContentType) -> list[str]:
        """Discover images for content (mock implementation)."""
        # Simulate discovery work
        time.sleep(0.1)

        if content_type == ContentType.BESTIARY:
            return [f"{content_id}_portrait.jpg", f"{content_id}_action.jpg"]
        elif content_type == ContentType.ADVENTURE:
            return [f"{content_id}_chapter_{i}.jpg" for i in range(1, 4)]
        else:
            return [f"{content_id}_default.jpg"]

    @observe_image_processing(
        stage=ImageProcessingStage.PLACEMENT,
        content_type=ContentType.ADVENTURE,  # Default content type for simplicity
    )
    async def place_images(
        self, images: list[str], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Place images with intelligent positioning (mock implementation)."""
        await asyncio.sleep(0.05)  # Simulate async work

        placements = []
        for i, image in enumerate(images):
            confidence = 0.9 - (i * 0.1)  # Decreasing confidence
            placements.append(
                {
                    "image": image,
                    "placement": "top" if i == 0 else "inline",
                    "confidence": max(confidence, 0.5),
                    "size": "medium",
                }
            )

        return placements

    @observe_cache_operation("image_placement_cache")
    def get_cached_placement(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached placement decision."""
        return self._cache.get(cache_key)

    def store_cached_placement(self, cache_key: str, placement: dict[str, Any]) -> None:
        """Store placement in cache."""
        observer = get_image_observer()
        observer.record_cache_operation(
            cache_name="image_placement_cache",
            operation=CacheOperation.STORE,
            key=cache_key,
            size_bytes=len(str(placement)),
        )
        self._cache[cache_key] = placement

    async def batch_process_adventure(
        self, adventure_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Process entire adventure with comprehensive observability."""
        adventure_id = adventure_data.get("id", "unknown")
        chapter_count = len(adventure_data.get("chapters", []))

        # Use async context manager for batch operation tracking
        async with track_async_image_operation(
            stage=ImageProcessingStage.BATCH_PROCESSING,
            content_type=ContentType.ADVENTURE,
            content_id=adventure_id,
            image_count=chapter_count,
            metadata={"batch_type": "adventure_processing"},
        ) as tracking:
            # Start resource monitoring
            resource_monitor = get_resource_monitor()
            await resource_monitor.start_monitoring(tracking["operation_id"])

            results = {
                "adventure_id": adventure_id,
                "chapters": [],
                "total_images": 0,
                "successful_placements": 0,
            }

            # Process each chapter
            for i, chapter in enumerate(adventure_data.get("chapters", [])):
                chapter_id = f"{adventure_id}_chapter_{i + 1}"

                # Discover images
                images = self.discover_images(chapter_id, ContentType.ADVENTURE)

                # Check cache first
                cache_key = f"adventure:{chapter_id}"
                cached_placement = self.get_cached_placement(cache_key)

                if cached_placement:
                    placements = cached_placement
                    tracking["add_metadata"]("cache_hits", tracking["operation_id"])
                else:
                    # Generate new placements
                    context = {
                        "content_type": ContentType.ADVENTURE,
                        "chapter": chapter,
                        "adventure_id": adventure_id,
                    }
                    placements = await self.place_images(images, context)
                    self.store_cached_placement(cache_key, placements)

                results["chapters"].append(
                    {
                        "chapter_id": chapter_id,
                        "image_count": len(images),
                        "placements": placements,
                    }
                )

                results["total_images"] += len(images)
                results["successful_placements"] += sum(
                    1 for p in placements if p["confidence"] > 0.7
                )

            # Calculate overall confidence
            if results["total_images"] > 0:
                overall_confidence = (
                    results["successful_placements"] / results["total_images"]
                )
                tracking["set_confidence"](overall_confidence)

                # Set fallback usage based on low confidence placements
                fallback_used = any(
                    p["confidence"] < 0.6
                    for chapter in results["chapters"]
                    for p in chapter["placements"]
                )
                tracking["set_fallback"](fallback_used)

            # Get resource usage
            resource_metrics = await resource_monitor.stop_monitoring(
                tracking["operation_id"]
            )
            if resource_metrics:
                tracking["set_resource_usage"](
                    memory_mb=resource_metrics.get("memory_usage_mb"),
                    cpu_percent=None,  # Not available in mock
                )

            tracking["add_metadata"]("chapters_processed", len(results["chapters"]))
            tracking["add_metadata"]("total_images", results["total_images"])

            return results


async def demonstrate_cli_workflow():
    """Demonstrate CLI-style workflow with progress reporting."""
    print("\n=== CLI Workflow Demonstration ===")

    service = MockImageService()
    reporter = ProgressReporter(quiet=False)

    # Simulate processing multiple creatures
    creatures = [
        {"id": "ancient-red-dragon", "type": ContentType.BESTIARY},
        {"id": "adult-blue-dragon", "type": ContentType.BESTIARY},
        {"id": "young-green-dragon", "type": ContentType.BESTIARY},
        {"id": "dragon-turtle", "type": ContentType.BESTIARY},
        {"id": "kobold", "type": ContentType.BESTIARY},
    ]

    total_creatures = len(creatures)
    successful = 0

    for i, creature in enumerate(creatures):
        reporter.report_progress(i, total_creatures, "Processing creatures")

        try:
            with track_image_operation(
                stage=ImageProcessingStage.DISCOVERY,
                content_type=creature["type"],
                content_id=creature["id"],
            ) as tracking:
                images = service.discover_images(creature["id"], creature["type"])
                tracking["set_confidence"](0.9)
                tracking["add_metadata"]("image_count", len(images))
                successful += 1
        except Exception as e:
            print(f"Error processing {creature['id']}: {e}")

        # Small delay to show progress
        await asyncio.sleep(0.1)

    reporter.report_progress(
        total_creatures, total_creatures, "Processing creatures", force=True
    )
    reporter.report_completion("Creature processing", total_creatures, successful)


async def demonstrate_mcp_workflow():
    """Demonstrate MCP-style async workflow."""
    print("\n=== MCP Workflow Demonstration ===")

    service = MockImageService()

    # Simulate multiple concurrent requests
    adventure_data = {
        "id": "storm-kings-thunder",
        "chapters": [
            {"title": "A Great Upheaval", "content": "..."},
            {"title": "Rumblings", "content": "..."},
            {"title": "The Savage Frontier", "content": "..."},
        ],
    }

    # Process adventure with full observability
    result = await service.batch_process_adventure(adventure_data)

    print(f"Processed adventure: {result['adventure_id']}")
    print(f"Total chapters: {len(result['chapters'])}")
    print(f"Total images: {result['total_images']}")
    print(f"Successful placements: {result['successful_placements']}")

    # Simulate concurrent operations
    print("\nProcessing concurrent requests...")

    tasks = []
    for i in range(3):
        concurrent_adventure = {
            "id": f"concurrent-adventure-{i + 1}",
            "chapters": [
                {"title": f"Chapter {j + 1}", "content": "..."} for j in range(2)
            ],
        }
        tasks.append(service.batch_process_adventure(concurrent_adventure))

    concurrent_results = await asyncio.gather(*tasks)

    print(f"Completed {len(concurrent_results)} concurrent operations")


def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring and reporting."""
    print("\n=== Performance Monitoring Demonstration ===")

    # Generate performance report
    report = generate_performance_report()

    print(f"Session ID: {report['session_id']}")
    print(f"Performance Grade: {report['performance_grade']}")
    print(f"Total Operations: {report['statistics']['operation_count']}")
    print(f"Success Rate: {report['statistics']['success_rate']:.1%}")
    print(f"Average Duration: {report['statistics']['avg_duration_ms']:.1f}ms")
    print(f"Cache Hit Ratio: {report['statistics']['cache_hit_ratio']:.1%}")

    if report["recommendations"]:
        print("\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")

    print("\nContent Type Distribution:")
    for content_type, count in report["statistics"][
        "content_type_distribution"
    ].items():
        print(f"  {content_type}: {count}")

    print("\nStage Distribution:")
    for stage, count in report["statistics"]["stage_distribution"].items():
        print(f"  {stage}: {count}")

    # Log summary to Logfire
    print("\nLogging performance summary to Logfire...")
    log_performance_summary()


async def main():
    """Main demonstration function."""
    print("Image Processing Observability Integration Demo")
    print("=" * 50)

    # Initialize logging
    setup_logging(
        debug=True,
        environment="demo",
        enable_telemetry=False,  # Disable for demo
        console_min_level="info",
    )

    # Reset observer for clean demo
    reset_image_observer()

    try:
        # Run CLI workflow demo
        await demonstrate_cli_workflow()

        # Run MCP workflow demo
        await demonstrate_mcp_workflow()

        # Show performance monitoring
        demonstrate_performance_monitoring()

        print("\n=== Integration Test Summary ===")
        observer = get_image_observer()
        final_stats = observer.get_statistics()

        print(f"Total operations tracked: {final_stats['operation_count']}")
        print(f"Success rate: {final_stats['success_rate']:.1%}")
        print(f"Cache efficiency: {final_stats['cache_hit_ratio']:.1%}")
        print(f"Average processing time: {final_stats['avg_duration_ms']:.1f}ms")

        # Show health indicators
        report = generate_performance_report()
        health = report["health_indicators"]
        print("\nHealth Status:")
        print(
            f"  Success Rate Healthy: {'✓' if health['success_rate_healthy'] else '✗'}"
        )
        print(f"  Cache Effective: {'✓' if health['cache_effective'] else '✗'}")
        print(
            f"  Performance Acceptable: {'✓' if health['performance_acceptable'] else '✗'}"
        )

    except Exception as e:
        print(f"\nDemo error: {e}")
        import traceback

        traceback.print_exc()

    print("\nDemo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
