"""Adventure Image Registry for comprehensive batch processing and cataloging.

This module provides intelligent batch processing capabilities for complete
adventures and books, with image cataloging, metadata tracking, and performance
optimization through preprocessing.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.placement_models import (
    ImageDimensions,
    ImageMetadata,
)

if TYPE_CHECKING:
    from studiorum.core.assets.image_manager import ImageManager
    from studiorum.core.assets.image_sources import ImageSourceRegistry

    from ..image_processor import ImageProcessor

logger = get_logger(__name__)


class ImageCatalogEntry(BaseModel):
    """Individual entry in an image catalog."""

    image_id: str
    filename: str
    file_path: Path
    image_type: str  # opener, map, portrait, scene, gallery
    content_context: str  # chapter name, location, NPC name, etc.
    metadata: ImageMetadata
    preprocessing_status: str = Field(default="pending")  # pending, processed, failed
    preprocessing_timestamp: datetime | None = None
    optimization_data: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)


class ImageCatalog(BaseModel):
    """Complete catalog of images for an adventure or book."""

    adventure_id: str
    adventure_name: str
    catalog_created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    catalog_version: str = Field(default="1.0")
    total_images: int = Field(default=0)

    # Categorized image entries
    chapter_openers: list[ImageCatalogEntry] = Field(default_factory=list)
    location_maps: list[ImageCatalogEntry] = Field(default_factory=list)
    npc_portraits: list[ImageCatalogEntry] = Field(default_factory=list)
    atmospheric_scenes: list[ImageCatalogEntry] = Field(default_factory=list)
    gallery_images: list[ImageCatalogEntry] = Field(default_factory=list)
    miscellaneous: list[ImageCatalogEntry] = Field(default_factory=list)

    # Processing metadata
    processing_stats: dict[str, Any] = Field(default_factory=dict)
    source_directories: list[str] = Field(default_factory=list)
    preprocessing_completed: bool = Field(default=False)


class BatchProcessingJob(BaseModel):
    """Individual batch processing job."""

    job_id: str
    adventure_id: str
    status: str = Field(default="pending")  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    images_processed: int = Field(default=0)
    images_failed: int = Field(default=0)
    error_messages: list[str] = Field(default_factory=list)
    optimization_results: dict[str, Any] = Field(default_factory=dict)


class BatchResult(BaseModel):
    """Result of batch processing operation."""

    job_id: str
    adventure_id: str
    success: bool
    processing_time_seconds: float
    images_processed: int
    images_optimized: int
    images_failed: int
    optimization_summary: dict[str, Any] = Field(default_factory=dict)
    error_summary: list[str] = Field(default_factory=list)
    catalog_updated: bool = Field(default=False)


class RegistryStats(BaseModel):
    """Statistics for image registry operations."""

    total_adventures: int
    total_images_cataloged: int
    images_by_type: dict[str, int] = Field(default_factory=dict)
    preprocessing_completion_rate: float = Field(default=0.0)
    average_images_per_adventure: float = Field(default=0.0)
    storage_usage_mb: float = Field(default=0.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdventureImageRegistry:
    """Comprehensive image registry for adventure content with batch processing.

    This class provides intelligent cataloging, batch preprocessing, and
    optimization capabilities for complete adventures and book collections,
    integrating with Phase 1 ImageSourceRegistry for source management.
    """

    def __init__(
        self,
        image_processor: ImageProcessor,
        image_manager: ImageManager,
        source_registry: ImageSourceRegistry,
        registry_storage_path: Path | None = None,
    ) -> None:
        """Initialize adventure image registry.

        Args:
            image_processor: Core image processing component
            image_manager: Image asset management component
            source_registry: Image source registry for discovery
            registry_storage_path: Path for registry data storage

        """
        self._image_processor = image_processor
        self._image_manager = image_manager
        self._source_registry = source_registry
        self._storage_path = (
            registry_storage_path or Path.home() / ".studiorum" / "registry"
        )
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory registries
        self._catalogs: dict[str, ImageCatalog] = {}
        self._processing_jobs: dict[str, BatchProcessingJob] = {}
        self._registry_lock = asyncio.Lock()

    async def catalog_adventure_images(
        self,
        adventure_id: str,
        adventure_content: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> Result[ImageCatalog, str]:
        """Catalog all images for a specific adventure or book.

        Args:
            adventure_id: Unique identifier for the adventure
            adventure_content: Optional adventure content for context
            force_refresh: Force refresh of existing catalog

        Returns:
            Result containing complete image catalog or error

        """
        async with self._registry_lock:
            try:
                logger.info(f"Starting image cataloging for adventure: {adventure_id}")

                # Check for existing catalog
                if not force_refresh and adventure_id in self._catalogs:
                    logger.debug(f"Returning existing catalog for {adventure_id}")
                    return Success(self._catalogs[adventure_id])

                # Create new catalog
                catalog = ImageCatalog(
                    adventure_id=adventure_id,
                    adventure_name=adventure_content.get("name", adventure_id)
                    if adventure_content
                    else adventure_id,
                )

                # Discover images from all configured sources
                discovery_result = await self._discover_adventure_images(
                    adventure_id, adventure_content
                )
                if isinstance(discovery_result, Error):
                    return discovery_result.with_context(
                        "Failed to discover images for adventure catalog",
                        operation="catalog_creation",
                        adventure_id=adventure_id,
                    )

                discovered_images = discovery_result.unwrap()

                # Process and categorize discovered images
                for image_metadata in discovered_images:
                    catalog_entry = await self._create_catalog_entry(
                        image_metadata, adventure_content
                    )
                    if isinstance(catalog_entry, Success):
                        self._add_to_catalog(catalog, catalog_entry.value)

                # Update catalog statistics
                catalog.total_images = self._count_catalog_images(catalog)
                catalog.processing_stats = {
                    "discovery_timestamp": datetime.now(UTC).isoformat(),
                    "images_discovered": len(discovered_images),
                    "images_cataloged": catalog.total_images,
                    "sources_used": len(catalog.source_directories),
                }

                # Store catalog
                self._catalogs[adventure_id] = catalog
                await self._persist_catalog(catalog)

                logger.info(
                    f"Cataloging completed for {adventure_id}",
                    extra={
                        "total_images": catalog.total_images,
                        "chapter_openers": len(catalog.chapter_openers),
                        "location_maps": len(catalog.location_maps),
                        "npc_portraits": len(catalog.npc_portraits),
                        "atmospheric_scenes": len(catalog.atmospheric_scenes),
                    },
                )

                return Success(catalog)

            except Exception as e:
                error_msg = f"Image cataloging failed for {adventure_id}: {e}"
                logger.error(error_msg, exc_info=True)
                return Error(error_msg)

    async def batch_preprocess_adventure(
        self, adventure_id: str, optimization_config: dict[str, Any] | None = None
    ) -> Result[BatchResult, str]:
        """Batch preprocess all images for an adventure with optimization.

        Args:
            adventure_id: Adventure identifier for batch processing
            optimization_config: Configuration for image optimization

        Returns:
            Result containing batch processing results or error

        """
        try:
            logger.info(f"Starting batch preprocessing for adventure: {adventure_id}")

            # Get or create catalog
            catalog_result = await self.catalog_adventure_images(adventure_id)
            if isinstance(catalog_result, Error):
                return catalog_result.with_context(
                    "Failed to get catalog for batch preprocessing",
                    operation="batch_preprocessing",
                    adventure_id=adventure_id,
                )

            catalog = catalog_result.unwrap()

            # Create processing job
            job_id = f"batch_{adventure_id}_{int(datetime.now(UTC).timestamp())}"
            job = BatchProcessingJob(
                job_id=job_id,
                adventure_id=adventure_id,
                status="running",
                started_at=datetime.now(UTC),
            )
            self._processing_jobs[job_id] = job

            start_time = datetime.now(UTC)

            try:
                # Process all image categories in parallel
                processing_tasks = [
                    self._batch_process_image_category(
                        catalog.chapter_openers, "chapter_openers", optimization_config
                    ),
                    self._batch_process_image_category(
                        catalog.location_maps, "location_maps", optimization_config
                    ),
                    self._batch_process_image_category(
                        catalog.npc_portraits, "npc_portraits", optimization_config
                    ),
                    self._batch_process_image_category(
                        catalog.atmospheric_scenes,
                        "atmospheric_scenes",
                        optimization_config,
                    ),
                    self._batch_process_image_category(
                        catalog.gallery_images, "gallery_images", optimization_config
                    ),
                ]

                category_results = await asyncio.gather(
                    *processing_tasks, return_exceptions=True
                )

                # Aggregate results
                total_processed = 0
                total_optimized = 0
                total_failed = 0
                optimization_summary: dict[str, Any] = {}
                error_summary: list[str] = []

                for i, result in enumerate(category_results):
                    if isinstance(result, Exception):
                        error_summary.append(f"Category processing failed: {result}")
                        total_failed += 1
                    elif isinstance(result, dict):
                        total_processed += result.get("processed", 0)
                        total_optimized += result.get("optimized", 0)
                        total_failed += result.get("failed", 0)
                        category_name = [
                            "chapter_openers",
                            "location_maps",
                            "npc_portraits",
                            "atmospheric_scenes",
                            "gallery_images",
                        ][i]
                        optimization_summary[category_name] = result

                # Update job status
                end_time = datetime.now(UTC)
                processing_time = (end_time - start_time).total_seconds()

                job.status = "completed" if total_failed == 0 else "partial_failure"
                job.completed_at = end_time
                job.images_processed = total_processed
                job.images_failed = total_failed
                job.error_messages = error_summary

                # Update catalog preprocessing status
                catalog.preprocessing_completed = total_failed == 0
                catalog.processing_stats.update(
                    {
                        "last_preprocessing": end_time.isoformat(),
                        "preprocessing_job_id": job_id,
                    }
                )
                await self._persist_catalog(catalog)

                # Create batch result
                batch_result = BatchResult(
                    job_id=job_id,
                    adventure_id=adventure_id,
                    success=total_failed == 0,
                    processing_time_seconds=processing_time,
                    images_processed=total_processed,
                    images_optimized=total_optimized,
                    images_failed=total_failed,
                    optimization_summary=optimization_summary,
                    error_summary=error_summary,
                    catalog_updated=True,
                )

                logger.info(
                    f"Batch preprocessing completed for {adventure_id}",
                    extra={
                        "processing_time": processing_time,
                        "images_processed": total_processed,
                        "images_failed": total_failed,
                    },
                )

                return Success(batch_result)

            except Exception as processing_error:
                # Update job with failure status
                job.status = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_messages = [str(processing_error)]
                raise processing_error

        except Exception as e:
            error_msg = f"Batch preprocessing failed for {adventure_id}: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    async def get_adventure_image_statistics(
        self, adventure_id: str
    ) -> Result[RegistryStats, str]:
        """Get comprehensive statistics for adventure image registry.

        Args:
            adventure_id: Adventure identifier for statistics

        Returns:
            Result containing registry statistics or error

        """
        try:
            catalog_result = await self.catalog_adventure_images(adventure_id)
            if isinstance(catalog_result, Error):
                return catalog_result.with_context(
                    "Failed to get catalog for statistics",
                    operation="registry_statistics",
                    adventure_id=adventure_id,
                )

            catalog = catalog_result.unwrap()

            # Calculate statistics
            images_by_type = {
                "chapter_openers": len(catalog.chapter_openers),
                "location_maps": len(catalog.location_maps),
                "npc_portraits": len(catalog.npc_portraits),
                "atmospheric_scenes": len(catalog.atmospheric_scenes),
                "gallery_images": len(catalog.gallery_images),
                "miscellaneous": len(catalog.miscellaneous),
            }

            # Calculate preprocessing completion rate
            total_images = catalog.total_images
            processed_images = sum(
                1
                for entry in self._get_all_catalog_entries(catalog)
                if entry.preprocessing_status == "processed"
            )
            completion_rate = (
                (processed_images / total_images) if total_images > 0 else 0.0
            )

            # Calculate storage usage (placeholder - would need actual file size calculation)
            storage_usage = sum(
                entry.metadata.file_size_bytes or 0
                for entry in self._get_all_catalog_entries(catalog)
            ) / (1024 * 1024)  # Convert to MB

            stats = RegistryStats(
                total_adventures=1,  # Single adventure statistics
                total_images_cataloged=total_images,
                images_by_type=images_by_type,
                preprocessing_completion_rate=completion_rate,
                average_images_per_adventure=float(total_images),
                storage_usage_mb=storage_usage,
            )

            return Success(stats)

        except Exception as e:
            error_msg = f"Statistics generation failed for {adventure_id}: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    async def get_registry_overview(self) -> Result[dict[str, Any], str]:
        """Get overview of all registered adventures and processing status.

        Returns:
            Result containing registry overview or error

        """
        try:
            overview: dict[str, Any] = {
                "total_adventures": len(self._catalogs),
                "total_processing_jobs": len(self._processing_jobs),
                "adventures": {},
                "active_jobs": [],
            }

            # Adventure summaries
            for adventure_id, catalog in self._catalogs.items():
                overview["adventures"][adventure_id] = {
                    "adventure_name": catalog.adventure_name,
                    "total_images": catalog.total_images,
                    "preprocessing_completed": catalog.preprocessing_completed,
                    "last_updated": catalog.catalog_created.isoformat(),
                }

            # Active processing jobs
            for job_id, job in self._processing_jobs.items():
                if job.status in ["pending", "running"]:
                    overview["active_jobs"].append(
                        {
                            "job_id": job_id,
                            "adventure_id": job.adventure_id,
                            "status": job.status,
                            "created_at": job.created_at.isoformat(),
                            "images_processed": job.images_processed,
                        }
                    )

            return Success(overview)

        except Exception as e:
            error_msg = f"Registry overview generation failed: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    async def _discover_adventure_images(
        self, adventure_id: str, adventure_content: dict[str, Any] | None = None
    ) -> Result[list[ImageMetadata], str]:
        """Discover all available images for an adventure using source registry.

        Args:
            adventure_id: Adventure identifier for discovery
            adventure_content: Optional adventure content for context

        Returns:
            Result containing list of discovered images or error

        """
        try:
            discovered_images: list[ImageMetadata] = []

            # Get available image sources from registry
            sources = self._source_registry.list_sources()

            # Discovery patterns based on adventure metadata
            base_patterns = [
                f"{adventure_id.lower().replace(' ', '_')}_*",
                f"*_{adventure_id.lower().replace(' ', '_')}",
                f"{adventure_id.lower().replace(' ', '_')}/",
            ]

            # Add content-specific patterns if available
            if adventure_content:
                adventure_name = (
                    adventure_content.get("name", "").lower().replace(" ", "_")
                )
                base_patterns.extend(
                    [
                        f"{adventure_name}_*",
                        f"*_{adventure_name}",
                        f"{adventure_name}/",
                    ]
                )

            # Search each source for relevant images
            for source_info in sources:
                try:
                    # This would use the actual image source discovery
                    # For now, create sample images for testing
                    source_images = await self._create_sample_discovery_images(
                        adventure_id, source_info.config.name
                    )
                    discovered_images.extend(source_images)

                except Exception as source_error:
                    logger.debug(
                        f"Discovery failed for source {source_info.config.name}: {source_error}"
                    )

            logger.debug(
                f"Discovered {len(discovered_images)} images for {adventure_id}"
            )
            return Success(discovered_images)

        except Exception as e:
            error_msg = f"Image discovery failed for {adventure_id}: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    async def _create_catalog_entry(
        self,
        image_metadata: ImageMetadata,
        adventure_content: dict[str, Any] | None = None,
    ) -> Result[ImageCatalogEntry, str]:
        """Create a catalog entry from image metadata.

        Args:
            image_metadata: Base image metadata
            adventure_content: Optional adventure content for context

        Returns:
            Result containing catalog entry or error

        """
        try:
            # Determine image type and context from metadata
            image_type, content_context, tags = self._analyze_image_context(
                image_metadata, adventure_content
            )

            entry = ImageCatalogEntry(
                image_id=f"{image_metadata.path}_{int(datetime.now(UTC).timestamp())}",
                filename=image_metadata.path,
                file_path=image_metadata.local_path or Path(image_metadata.path),
                image_type=image_type,
                content_context=content_context,
                metadata=image_metadata,
                tags=tags,
                confidence_score=0.7,  # Default confidence score
            )

            return Success(entry)

        except Exception as e:
            error_msg = f"Catalog entry creation failed: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    def _analyze_image_context(
        self,
        image_metadata: ImageMetadata,
        adventure_content: dict[str, Any] | None = None,
    ) -> tuple[str, str, list[str]]:
        """Analyze image metadata to determine type, context, and tags.

        Args:
            image_metadata: Image metadata to analyze
            adventure_content: Optional adventure content for context

        Returns:
            Tuple of (image_type, content_context, tags)

        """
        filename = image_metadata.path.lower()
        tags = []

        # Determine image type based on filename patterns
        if any(keyword in filename for keyword in ["opener", "chapter", "title"]):
            image_type = "opener"
            content_context = "Chapter Opening"
            tags = ["chapter", "opener", "title"]
        elif any(keyword in filename for keyword in ["map", "location", "region"]):
            image_type = "map"
            content_context = "Location Map"
            tags = ["map", "location", "geography"]
        elif any(keyword in filename for keyword in ["portrait", "npc", "character"]):
            image_type = "portrait"
            content_context = "Character Portrait"
            tags = ["portrait", "character", "npc"]
        elif any(
            keyword in filename for keyword in ["scene", "atmosphere", "landscape"]
        ):
            image_type = "scene"
            content_context = "Atmospheric Scene"
            tags = ["scene", "atmosphere", "landscape"]
        elif any(
            keyword in filename for keyword in ["gallery", "collection", "showcase"]
        ):
            image_type = "gallery"
            content_context = "Gallery Collection"
            tags = ["gallery", "collection", "showcase"]
        else:
            image_type = "miscellaneous"
            content_context = "General Illustration"
            tags = ["illustration", "general"]

        # Add quality-based tags
        if hasattr(image_metadata, "characteristics"):
            for char in image_metadata.characteristics:
                tags.append(char.name.lower())

        return image_type, content_context, tags

    def _add_to_catalog(self, catalog: ImageCatalog, entry: ImageCatalogEntry) -> None:
        """Add a catalog entry to the appropriate category.

        Args:
            catalog: Image catalog to update
            entry: Catalog entry to add

        """
        if entry.image_type == "opener":
            catalog.chapter_openers.append(entry)
        elif entry.image_type == "map":
            catalog.location_maps.append(entry)
        elif entry.image_type == "portrait":
            catalog.npc_portraits.append(entry)
        elif entry.image_type == "scene":
            catalog.atmospheric_scenes.append(entry)
        elif entry.image_type == "gallery":
            catalog.gallery_images.append(entry)
        else:
            catalog.miscellaneous.append(entry)

    def _count_catalog_images(self, catalog: ImageCatalog) -> int:
        """Count total images in catalog across all categories.

        Args:
            catalog: Image catalog to count

        Returns:
            Total number of images in catalog

        """
        return (
            len(catalog.chapter_openers)
            + len(catalog.location_maps)
            + len(catalog.npc_portraits)
            + len(catalog.atmospheric_scenes)
            + len(catalog.gallery_images)
            + len(catalog.miscellaneous)
        )

    def _get_all_catalog_entries(
        self, catalog: ImageCatalog
    ) -> list[ImageCatalogEntry]:
        """Get all catalog entries across all categories.

        Args:
            catalog: Image catalog to process

        Returns:
            List of all catalog entries

        """
        return (
            catalog.chapter_openers
            + catalog.location_maps
            + catalog.npc_portraits
            + catalog.atmospheric_scenes
            + catalog.gallery_images
            + catalog.miscellaneous
        )

    async def _batch_process_image_category(
        self,
        entries: list[ImageCatalogEntry],
        category_name: str,
        optimization_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Batch process images in a specific category.

        Args:
            entries: List of catalog entries to process
            category_name: Name of the image category
            optimization_config: Configuration for image optimization

        Returns:
            Dictionary containing processing results

        """
        try:
            processed = 0
            optimized = 0
            failed = 0

            # Process entries in parallel batches
            batch_size = 5  # Process 5 images at once
            for i in range(0, len(entries), batch_size):
                batch = entries[i : i + batch_size]

                batch_tasks = [
                    self._process_single_image(entry, optimization_config)
                    for entry in batch
                ]

                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                for entry, result in zip(batch, batch_results, strict=False):
                    if isinstance(result, Exception):
                        entry.preprocessing_status = "failed"
                        failed += 1
                    else:
                        # result is dict[str, Any] here (not Exception)
                        optimization_result = cast(dict[str, Any], result)
                        entry.preprocessing_status = "processed"
                        entry.preprocessing_timestamp = datetime.now(UTC)
                        entry.optimization_data = optimization_result
                        processed += 1
                        if optimization_result.get("optimized", False):
                            optimized += 1

            return {
                "category": category_name,
                "processed": processed,
                "optimized": optimized,
                "failed": failed,
                "total": len(entries),
            }

        except Exception as e:
            logger.error(f"Batch processing failed for category {category_name}: {e}")
            return {
                "category": category_name,
                "processed": 0,
                "optimized": 0,
                "failed": len(entries),
                "total": len(entries),
                "error": str(e),
            }

    async def _process_single_image(
        self,
        entry: ImageCatalogEntry,
        optimization_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a single image for optimization and preprocessing.

        Args:
            entry: Catalog entry to process
            optimization_config: Configuration for image optimization

        Returns:
            Dictionary containing processing results

        """
        try:
            # This would use the actual image processor for optimization
            # For now, return a placeholder result
            await asyncio.sleep(0.1)  # Simulate processing time

            return {
                "optimized": True,
                "original_size": entry.metadata.file_size_bytes,
                "optimized_size": int(
                    (entry.metadata.file_size_bytes or 1000000) * 0.8
                ),
                "format_conversions": ["webp", "png"],
                "processing_time_ms": 100,
            }

        except Exception as e:
            logger.error(f"Single image processing failed for {entry.filename}: {e}")
            raise e

    async def _persist_catalog(self, catalog: ImageCatalog) -> None:
        """Persist image catalog to storage.

        Args:
            catalog: Image catalog to persist

        """
        try:
            catalog_file = self._storage_path / f"{catalog.adventure_id}_catalog.json"
            catalog_data = catalog.model_dump_json(indent=2)

            with open(catalog_file, "w", encoding="utf-8") as f:
                f.write(catalog_data)

            logger.debug(f"Persisted catalog for {catalog.adventure_id}")

        except Exception as e:
            logger.error(f"Catalog persistence failed for {catalog.adventure_id}: {e}")

    async def _create_sample_discovery_images(
        self, adventure_id: str, source_id: str
    ) -> list[ImageMetadata]:
        """Create sample discovery images for development/testing.

        Args:
            adventure_id: Adventure identifier
            source_id: Source identifier

        Returns:
            List of sample image metadata

        """
        # This is a placeholder implementation for testing
        # In production, this would interface with actual image sources
        sample_images = [
            ImageMetadata(
                path=f"{adventure_id}_chapter_opener_1",
                local_path=Path(f"/sample/{source_id}/chapter_opener_1.jpg"),
                characteristics=[],
                dimensions=ImageDimensions.from_dimensions(1920, 1080),
                file_size_bytes=2048000,
            ),
            ImageMetadata(
                path=f"{adventure_id}_location_map_1",
                local_path=Path(f"/sample/{source_id}/location_map_1.jpg"),
                characteristics=[],
                dimensions=ImageDimensions.from_dimensions(1600, 1200),
                file_size_bytes=1536000,
            ),
        ]

        return sample_images
