"""Tests for AdventureImageRegistry and batch processing functionality.

This module tests the image registry system including cataloging,
batch processing, and statistics generation.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from studiorum.core.result import Error, Success
from studiorum.latex_engine.core.images.placement_models import (
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
)
from studiorum.latex_engine.core.images.registry.adventure_registry import (
    AdventureImageRegistry,
    BatchProcessingJob,
    BatchResult,
    ImageCatalog,
    ImageCatalogEntry,
    RegistryStats,
)
from tests.test_helpers import reset_test_environment


class TestImageCatalogEntry:
    """Test ImageCatalogEntry model."""

    def setup_method(self):
        reset_test_environment()

    def test_basic_catalog_entry(self):
        """Test basic catalog entry creation."""
        test_metadata = ImageMetadata(
            path="test_image.jpg",
            local_path=Path("/test/image.jpg"),
            characteristics=[ImageCharacteristic.ARTISTIC],
            dimensions=ImageDimensions.from_dimensions(1920, 1080),
            file_size_bytes=2048000,
        )

        entry = ImageCatalogEntry(
            image_id="test_123",
            filename="test_image.jpg",
            file_path=Path("/test/image.jpg"),
            image_type="opener",
            content_context="Chapter 1 Opening",
            metadata=test_metadata,
        )

        assert entry.image_id == "test_123"
        assert entry.filename == "test_image.jpg"
        assert entry.image_type == "opener"
        assert entry.content_context == "Chapter 1 Opening"
        assert entry.preprocessing_status == "pending"  # Default
        assert entry.preprocessing_timestamp is None

    def test_processed_catalog_entry(self):
        """Test processed catalog entry with optimization data."""
        test_metadata = ImageMetadata(
            path="processed_image.jpg",
            local_path=Path("/test/processed.jpg"),
            characteristics=[ImageCharacteristic.TECHNICAL],
            dimensions=ImageDimensions.from_dimensions(1600, 1200),
            file_size_bytes=1536000,
        )

        optimization_data = {
            "original_size": 2048000,
            "optimized_size": 1536000,
            "compression_ratio": 0.75,
            "formats_generated": ["webp", "png"],
        }

        entry = ImageCatalogEntry(
            image_id="processed_456",
            filename="processed_image.jpg",
            file_path=Path("/test/processed.jpg"),
            image_type="map",
            content_context="Location Map",
            metadata=test_metadata,
            preprocessing_status="processed",
            preprocessing_timestamp=datetime.now(UTC),
            optimization_data=optimization_data,
            tags=["map", "location", "optimized"],
        )

        assert entry.preprocessing_status == "processed"
        assert entry.preprocessing_timestamp is not None
        assert entry.optimization_data["compression_ratio"] == 0.75
        assert "optimized" in entry.tags


class TestImageCatalog:
    """Test ImageCatalog model."""

    def setup_method(self):
        reset_test_environment()

    def test_empty_catalog_creation(self):
        """Test creating an empty catalog."""
        catalog = ImageCatalog(
            adventure_id="test_adventure",
            adventure_name="Test Adventure",
        )

        assert catalog.adventure_id == "test_adventure"
        assert catalog.adventure_name == "Test Adventure"
        assert catalog.total_images == 0
        assert len(catalog.chapter_openers) == 0
        assert len(catalog.location_maps) == 0
        assert len(catalog.npc_portraits) == 0
        assert len(catalog.atmospheric_scenes) == 0
        assert catalog.preprocessing_completed is False

    def test_populated_catalog(self):
        """Test catalog with various image types."""
        # Create sample entries
        opener_entry = ImageCatalogEntry(
            image_id="opener_1",
            filename="chapter_opener.jpg",
            file_path=Path("/test/opener.jpg"),
            image_type="opener",
            content_context="Chapter 1",
            metadata=ImageMetadata(
                path="chapter_opener.jpg",
                local_path=Path("/test/opener.jpg"),
                characteristics=[],
                dimensions=ImageDimensions.from_dimensions(1920, 1080),
                file_size_bytes=2048000,
            ),
        )

        map_entry = ImageCatalogEntry(
            image_id="map_1",
            filename="location_map.jpg",
            file_path=Path("/test/map.jpg"),
            image_type="map",
            content_context="Barovia",
            metadata=ImageMetadata(
                path="location_map.jpg",
                local_path=Path("/test/map.jpg"),
                characteristics=[],
                dimensions=ImageDimensions.from_dimensions(1600, 1200),
                file_size_bytes=1536000,
            ),
        )

        catalog = ImageCatalog(
            adventure_id="curse_of_strahd",
            adventure_name="Curse of Strahd",
            total_images=2,
            chapter_openers=[opener_entry],
            location_maps=[map_entry],
            preprocessing_completed=True,
        )

        assert catalog.total_images == 2
        assert len(catalog.chapter_openers) == 1
        assert len(catalog.location_maps) == 1
        assert catalog.preprocessing_completed is True


class TestBatchProcessingJob:
    """Test BatchProcessingJob model."""

    def setup_method(self):
        reset_test_environment()

    def test_pending_job(self):
        """Test pending batch processing job."""
        job = BatchProcessingJob(
            job_id="batch_123",
            adventure_id="test_adventure",
        )

        assert job.job_id == "batch_123"
        assert job.adventure_id == "test_adventure"
        assert job.status == "pending"
        assert job.started_at is None
        assert job.completed_at is None
        assert job.images_processed == 0

    def test_completed_job(self):
        """Test completed batch processing job."""
        now = datetime.now(UTC)

        job = BatchProcessingJob(
            job_id="batch_456",
            adventure_id="test_adventure",
            status="completed",
            started_at=now,
            completed_at=now,
            images_processed=10,
            images_failed=1,
            error_messages=["One image failed to process"],
        )

        assert job.status == "completed"
        assert job.images_processed == 10
        assert job.images_failed == 1
        assert len(job.error_messages) == 1


class TestBatchResult:
    """Test BatchResult model."""

    def setup_method(self):
        reset_test_environment()

    def test_successful_batch_result(self):
        """Test successful batch processing result."""
        result = BatchResult(
            job_id="batch_success",
            adventure_id="test_adventure",
            success=True,
            processing_time_seconds=45.5,
            images_processed=15,
            images_optimized=12,
            images_failed=0,
            catalog_updated=True,
        )

        assert result.success is True
        assert result.processing_time_seconds == 45.5
        assert result.images_processed == 15
        assert result.images_optimized == 12
        assert result.images_failed == 0
        assert result.catalog_updated is True

    def test_failed_batch_result(self):
        """Test failed batch processing result."""
        result = BatchResult(
            job_id="batch_failure",
            adventure_id="test_adventure",
            success=False,
            processing_time_seconds=120.0,
            images_processed=5,
            images_optimized=3,
            images_failed=2,
            error_summary=["Network timeout", "Invalid image format"],
        )

        assert result.success is False
        assert result.images_failed == 2
        assert len(result.error_summary) == 2


class TestRegistryStats:
    """Test RegistryStats model."""

    def setup_method(self):
        reset_test_environment()

    def test_registry_statistics(self):
        """Test registry statistics."""
        stats = RegistryStats(
            total_adventures=5,
            total_images_cataloged=150,
            images_by_type={
                "chapter_openers": 25,
                "location_maps": 30,
                "npc_portraits": 45,
                "atmospheric_scenes": 35,
                "gallery_images": 15,
            },
            preprocessing_completion_rate=0.85,
            average_images_per_adventure=30.0,
            storage_usage_mb=2048.5,
        )

        assert stats.total_adventures == 5
        assert stats.total_images_cataloged == 150
        assert stats.images_by_type["npc_portraits"] == 45
        assert stats.preprocessing_completion_rate == 0.85
        assert stats.average_images_per_adventure == 30.0
        assert stats.storage_usage_mb == 2048.5


class TestAdventureImageRegistry:
    """Test AdventureImageRegistry class."""

    def setup_method(self):
        reset_test_environment()

        # Create mock dependencies
        self.mock_processor = Mock()
        self.mock_manager = Mock()
        self.mock_source_registry = Mock()
        self.test_storage_path = Path("/tmp/test_registry")

        # Create registry instance
        self.registry = AdventureImageRegistry(
            image_processor=self.mock_processor,
            image_manager=self.mock_manager,
            source_registry=self.mock_source_registry,
            registry_storage_path=self.test_storage_path,
        )

    def test_initialization(self):
        """Test proper initialization."""
        assert self.registry._image_processor is self.mock_processor
        assert self.registry._image_manager is self.mock_manager
        assert self.registry._source_registry is self.mock_source_registry
        assert self.registry._storage_path == self.test_storage_path

    @pytest.mark.asyncio
    async def test_catalog_adventure_images_success(self):
        """Test successful adventure image cataloging."""
        adventure_id = "curse_of_strahd"
        adventure_content = {
            "name": "Curse of Strahd",
            "data": {"chapter": []},
        }

        # Mock source registry to return available sources
        mock_source_info = Mock()
        mock_source_info.source_id = "test_source"
        self.mock_source_registry.get_available_sources.return_value = Success(
            [mock_source_info]
        )

        with patch.object(self.registry, "_discover_adventure_images") as mock_discover:
            # Mock image discovery
            sample_images = [
                ImageMetadata(
                    path="test_image.jpg",
                    local_path=Path("/test/image.jpg"),
                    characteristics=[ImageCharacteristic.ARTISTIC],
                    dimensions=ImageDimensions.from_dimensions(1920, 1080),
                    file_size_bytes=2048000,
                )
            ]
            mock_discover.return_value = Success(sample_images)

            with patch.object(self.registry, "_persist_catalog") as mock_persist:
                mock_persist.return_value = None

                # Execute cataloging
                result = await self.registry.catalog_adventure_images(
                    adventure_id, adventure_content
                )

                # Verify success
                assert isinstance(result, Success)
                catalog = result.value
                assert isinstance(catalog, ImageCatalog)
                assert catalog.adventure_id == adventure_id
                assert catalog.adventure_name == "Curse of Strahd"

    @pytest.mark.asyncio
    async def test_catalog_adventure_images_discovery_failure(self):
        """Test handling of image discovery failure."""
        adventure_id = "test_adventure"

        # Mock source registry to return available sources
        mock_source_info = Mock()
        mock_source_info.source_id = "test_source"
        self.mock_source_registry.get_available_sources.return_value = Success(
            [mock_source_info]
        )

        with patch.object(self.registry, "_discover_adventure_images") as mock_discover:
            mock_discover.return_value = Error("Discovery failed")

            result = await self.registry.catalog_adventure_images(adventure_id)

            assert isinstance(result, Error)
            assert "Discovery failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_batch_preprocess_adventure_success(self):
        """Test successful batch preprocessing."""
        adventure_id = "test_adventure"

        # Create a test catalog
        test_catalog = ImageCatalog(
            adventure_id=adventure_id,
            adventure_name="Test Adventure",
            total_images=3,
        )

        with (
            patch.object(self.registry, "catalog_adventure_images") as mock_catalog,
            patch.object(
                self.registry, "_batch_process_image_category"
            ) as mock_process,
        ):
            mock_catalog.return_value = Success(test_catalog)

            # Mock batch processing results
            mock_process.return_value = {
                "category": "test_category",
                "processed": 5,
                "optimized": 4,
                "failed": 1,
                "total": 6,
            }

            result = await self.registry.batch_preprocess_adventure(adventure_id)

            assert isinstance(result, Success)
            batch_result = result.value
            assert isinstance(batch_result, BatchResult)
            assert batch_result.adventure_id == adventure_id

    @pytest.mark.asyncio
    async def test_batch_preprocess_adventure_catalog_failure(self):
        """Test batch preprocessing with catalog failure."""
        adventure_id = "test_adventure"

        with patch.object(self.registry, "catalog_adventure_images") as mock_catalog:
            mock_catalog.return_value = Error("Catalog creation failed")

            result = await self.registry.batch_preprocess_adventure(adventure_id)

            assert isinstance(result, Error)
            assert "Catalog creation failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_get_adventure_image_statistics_success(self):
        """Test successful statistics generation."""
        adventure_id = "test_adventure"

        # Create test catalog with statistics
        test_entries = [
            ImageCatalogEntry(
                image_id="test_1",
                filename="test1.jpg",
                file_path=Path("/test/1.jpg"),
                image_type="opener",
                content_context="Chapter 1",
                metadata=ImageMetadata(
                    path="test1.jpg",
                    local_path=Path("/test/1.jpg"),
                    characteristics=[],
                    dimensions=ImageDimensions.from_dimensions(1920, 1080),
                    file_size_bytes=2048000,
                ),
                preprocessing_status="processed",
            ),
            ImageCatalogEntry(
                image_id="test_2",
                filename="test2.jpg",
                file_path=Path("/test/2.jpg"),
                image_type="map",
                content_context="Location",
                metadata=ImageMetadata(
                    path="test2.jpg",
                    local_path=Path("/test/2.jpg"),
                    characteristics=[],
                    dimensions=ImageDimensions.from_dimensions(1600, 1200),
                    file_size_bytes=1536000,
                ),
                preprocessing_status="pending",
            ),
        ]

        test_catalog = ImageCatalog(
            adventure_id=adventure_id,
            adventure_name="Test Adventure",
            total_images=2,
            chapter_openers=[test_entries[0]],
            location_maps=[test_entries[1]],
        )

        with patch.object(self.registry, "catalog_adventure_images") as mock_catalog:
            mock_catalog.return_value = Success(test_catalog)

            result = await self.registry.get_adventure_image_statistics(adventure_id)

            assert isinstance(result, Success)
            stats = result.value
            assert isinstance(stats, RegistryStats)
            assert stats.total_images_cataloged == 2
            assert stats.images_by_type["chapter_openers"] == 1
            assert stats.images_by_type["location_maps"] == 1
            assert stats.preprocessing_completion_rate == 0.5  # 1 of 2 processed

    @pytest.mark.asyncio
    async def test_get_registry_overview(self):
        """Test registry overview generation."""
        # Add some test catalogs
        test_catalog = ImageCatalog(
            adventure_id="test_adventure",
            adventure_name="Test Adventure",
            total_images=5,
        )
        self.registry._catalogs["test_adventure"] = test_catalog

        # Add a test job
        test_job = BatchProcessingJob(
            job_id="test_job",
            adventure_id="test_adventure",
            status="running",
        )
        self.registry._processing_jobs["test_job"] = test_job

        result = await self.registry.get_registry_overview()

        assert isinstance(result, Success)
        overview = result.value
        assert overview["total_adventures"] == 1
        assert overview["total_processing_jobs"] == 1
        assert "test_adventure" in overview["adventures"]
        assert len(overview["active_jobs"]) == 1

    def test_analyze_image_context(self):
        """Test image context analysis."""
        test_metadata = ImageMetadata(
            path="chapter_opener_strahd.jpg",
            local_path=Path("/test/opener.jpg"),
            characteristics=[ImageCharacteristic.ARTISTIC],
            dimensions=ImageDimensions.from_dimensions(1920, 1080),
            file_size_bytes=2048000,
        )

        image_type, content_context, tags = self.registry._analyze_image_context(
            test_metadata, {"adventure_name": "Curse of Strahd"}
        )

        assert image_type == "opener"
        assert content_context == "Chapter Opening"
        assert "chapter" in tags
        assert "opener" in tags

    def test_analyze_image_context_map(self):
        """Test map image context analysis."""
        test_metadata = ImageMetadata(
            path="barovia_location_map.jpg",
            local_path=Path("/test/map.jpg"),
            characteristics=[ImageCharacteristic.INFORMATIONAL],
            dimensions=ImageDimensions.from_dimensions(1600, 1200),
            file_size_bytes=1536000,
        )

        image_type, content_context, tags = self.registry._analyze_image_context(
            test_metadata
        )

        assert image_type == "map"
        assert content_context == "Location Map"
        assert "map" in tags
        assert "location" in tags

    @pytest.mark.asyncio
    async def test_process_single_image(self):
        """Test single image processing."""
        test_entry = ImageCatalogEntry(
            image_id="test_single",
            filename="test.jpg",
            file_path=Path("/test/test.jpg"),
            image_type="scene",
            content_context="Atmospheric Scene",
            metadata=ImageMetadata(
                path="test.jpg",
                local_path=Path("/test/test.jpg"),
                characteristics=[],
                dimensions=ImageDimensions.from_dimensions(800, 600),
                file_size_bytes=1024000,
            ),
        )

        result = await self.registry._process_single_image(test_entry)

        # Should return optimization data (placeholder implementation)
        assert isinstance(result, dict)
        assert "optimized" in result
        assert "processing_time_ms" in result

    @pytest.mark.asyncio
    async def test_batch_process_image_category(self):
        """Test batch processing of image category."""
        test_entries = [
            ImageCatalogEntry(
                image_id=f"test_{i}",
                filename=f"test_{i}.jpg",
                file_path=Path(f"/test/test_{i}.jpg"),
                image_type="scene",
                content_context="Test Scene",
                metadata=ImageMetadata(
                    path=f"test_{i}.jpg",
                    local_path=Path(f"/test/test_{i}.jpg"),
                    characteristics=[],
                    dimensions=ImageDimensions.from_dimensions(800, 600),
                    file_size_bytes=1024000,
                ),
            )
            for i in range(3)
        ]

        result = await self.registry._batch_process_image_category(
            test_entries, "test_category"
        )

        assert result["category"] == "test_category"
        assert result["total"] == 3
        assert result["processed"] >= 0
        assert result["failed"] >= 0

    @pytest.mark.asyncio
    async def test_create_sample_discovery_images(self):
        """Test sample image discovery creation."""
        sample_images = await self.registry._create_sample_discovery_images(
            "test_adventure", "test_source"
        )

        assert isinstance(sample_images, list)
        assert len(sample_images) == 2  # Based on implementation

        for image in sample_images:
            assert isinstance(image, ImageMetadata)
            assert "test_adventure" in image.path

    @pytest.mark.asyncio
    async def test_persist_catalog(self):
        """Test catalog persistence."""
        test_catalog = ImageCatalog(
            adventure_id="test_persist",
            adventure_name="Test Persistence",
        )

        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await self.registry._persist_catalog(test_catalog)

            # Verify file operations
            mock_open.assert_called_once()
            mock_file.write.assert_called_once()


class TestAdventureImageRegistryAsync:
    """Test async functionality and concurrency."""

    def setup_method(self):
        reset_test_environment()

        self.registry = AdventureImageRegistry(
            image_processor=Mock(),
            image_manager=Mock(),
            source_registry=Mock(),
        )

    @pytest.mark.asyncio
    async def test_concurrent_cataloging(self):
        """Test concurrent cataloging of multiple adventures."""
        adventure_ids = ["adventure_1", "adventure_2", "adventure_3"]

        # Mock all dependencies
        with (
            patch.object(self.registry, "_discover_adventure_images") as mock_discover,
            patch.object(self.registry, "_persist_catalog") as mock_persist,
        ):
            mock_discover.return_value = Success([])
            mock_persist.return_value = None

            # Setup source registry mock
            self.registry._source_registry.get_available_sources.return_value = Success(
                []
            )

            # Catalog multiple adventures concurrently
            tasks = [
                self.registry.catalog_adventure_images(adventure_id)
                for adventure_id in adventure_ids
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(isinstance(result, Success) for result in results)
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_registry_locking(self):
        """Test registry locking for thread safety."""
        adventure_id = "test_locking"

        # Mock dependencies
        with (
            patch.object(self.registry, "_discover_adventure_images") as mock_discover,
            patch.object(self.registry, "_persist_catalog") as mock_persist,
        ):
            mock_discover.return_value = Success([])
            mock_persist.return_value = None
            self.registry._source_registry.get_available_sources.return_value = Success(
                []
            )

            # Start multiple cataloging operations
            task1 = asyncio.create_task(
                self.registry.catalog_adventure_images(adventure_id)
            )
            task2 = asyncio.create_task(
                self.registry.catalog_adventure_images(adventure_id, force_refresh=True)
            )

            results = await asyncio.gather(task1, task2)

            # Both should complete successfully due to locking
            assert all(isinstance(result, Success) for result in results)


@pytest.mark.requires_data
class TestAdventureImageRegistryIntegration:
    """Integration tests with realistic data (slower, marked for optional execution)."""

    def setup_method(self):
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_real_adventure_cataloging(self):
        """Test with realistic adventure data."""
        pytest.skip("Requires real adventure data")

    @pytest.mark.asyncio
    async def test_large_batch_processing(self):
        """Test batch processing with large image collections."""
        pytest.skip("Requires large test dataset")
