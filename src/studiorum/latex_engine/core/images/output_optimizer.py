"""Output optimization system for digital vs print image processing.

This module provides sophisticated image optimization tailored for different
output formats, including digital display, print production, and hybrid
approaches that work well for both mediums.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.placement_models import (
    HybridImage,
    ImageDimensions,
    ImageMetadata,
    OptimizationConfig,
    OptimizationTarget,
    ProcessedImage,
)

logger = get_logger(__name__)


class OptimizationProfile(BaseModel):
    """Predefined optimization profile for specific use cases."""

    name: str = Field(description="Profile name")
    target: OptimizationTarget = Field(description="Primary optimization target")
    config: OptimizationConfig = Field(description="Optimization configuration")
    description: str = Field(description="Description of the profile")
    use_cases: list[str] = Field(description="Recommended use cases")


class ProcessingMetrics(BaseModel):
    """Metrics collected during image processing."""

    original_size_bytes: int = Field(description="Original file size")
    processed_size_bytes: int = Field(description="Processed file size")
    compression_ratio: float = Field(description="Size reduction ratio")
    processing_time_seconds: float = Field(description="Time taken to process")
    quality_loss_estimate: float = Field(
        ge=0.0, le=1.0, description="Estimated quality loss (0=none, 1=total)"
    )
    format_conversion: bool = Field(
        description="Whether format was converted during processing"
    )
    resolution_changed: bool = Field(description="Whether resolution was modified")


class OptimizationResult(BaseModel):
    """Result of image optimization process."""

    success: bool = Field(description="Whether optimization succeeded")
    processed_image: ProcessedImage | None = Field(
        default=None, description="Processed image if successful"
    )
    metrics: ProcessingMetrics | None = Field(
        default=None, description="Processing metrics"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal warnings during processing"
    )
    error_message: str | None = Field(
        default=None, description="Error message if optimization failed"
    )


class OutputOptimizer:
    """Advanced image optimization system for different output formats.

    Provides format-specific optimization with intelligent trade-offs between
    file size, quality, and compatibility for digital display, print output,
    and hybrid usage scenarios.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the output optimizer.

        Args:
            cache_dir: Directory for caching optimized images
        """
        self.cache_dir = (
            cache_dir or Path.home() / ".studiorum" / "image_optimization_cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize optimization profiles
        self.profiles = self._create_optimization_profiles()

        logger.debug(f"Initialized OutputOptimizer with cache dir: {self.cache_dir}")

    def optimize_for_digital(
        self, image: ImageMetadata, config: OptimizationConfig | None = None
    ) -> Result[ProcessedImage, str]:
        """Optimize image for digital display (screens, web, e-readers).

        Digital optimization priorities:
        - Smaller file sizes for faster loading
        - sRGB colour space for consistent display
        - Moderate resolution (96-150 DPI)
        - Format optimization (WebP, PNG with alpha)

        Args:
            image: Image metadata to optimize
            config: Optional custom optimization configuration

        Returns:
            Optimized image or error message
        """
        if not config:
            config = OptimizationConfig(
                target=OptimizationTarget.DIGITAL,
                quality_priority=0.6,
                target_dpi=96,
                max_file_size_mb=2.0,
                colour_profile="sRGB",
                compression_level=0.7,
            )

        logger.debug(f"Optimizing {image.path} for digital display")

        return self._process_image(image, config, "digital")

    def optimize_for_print(
        self, image: ImageMetadata, config: OptimizationConfig | None = None
    ) -> Result[ProcessedImage, str]:
        """Optimize image for print production.

        Print optimization priorities:
        - Higher resolution (300+ DPI) for quality output
        - CMYK colour space when possible
        - Minimal compression to preserve detail
        - Format suited for print workflows

        Args:
            image: Image metadata to optimize
            config: Optional custom optimization configuration

        Returns:
            Optimized image or error message
        """
        if not config:
            config = OptimizationConfig(
                target=OptimizationTarget.PRINT,
                quality_priority=0.9,
                target_dpi=300,
                max_file_size_mb=10.0,
                colour_profile="Adobe RGB",
                compression_level=0.9,
            )

        logger.debug(f"Optimizing {image.path} for print production")

        return self._process_image(image, config, "print")

    def create_hybrid_optimization(
        self,
        image: ImageMetadata,
        digital_config: OptimizationConfig | None = None,
        print_config: OptimizationConfig | None = None,
    ) -> Result[HybridImage, str]:
        """Create optimized versions for both digital and print usage.

        Generates two versions of the same image optimized for different
        output mediums, with recommendations for when to use each version.

        Args:
            image: Image metadata to optimize
            digital_config: Optional digital optimization configuration
            print_config: Optional print optimization configuration

        Returns:
            Hybrid image with both versions or error message
        """
        logger.info(f"Creating hybrid optimization for {image.path}")

        # Optimize for digital
        digital_result = self.optimize_for_digital(image, digital_config)
        if isinstance(digital_result, Error):
            return Error(digital_result.error)

        # Optimize for print
        print_result = self.optimize_for_print(image, print_config)
        if isinstance(print_result, Error):
            return Error(print_result.error)

        # Create usage recommendations
        recommendations = {
            "digital": "Use for web viewing, e-books, and screen display",
            "print": "Use for PDF generation, physical printing, and high-quality output",
            "auto_select": "Digital version recommended for file sizes < 1MB, print version for quality-critical applications",
        }

        digital_image = digital_result.unwrap()
        print_image = print_result.unwrap()

        hybrid_image = HybridImage(
            digital_version=digital_image,
            print_version=print_image,
            shared_metadata=image,
            usage_recommendations=recommendations,
        )

        logger.info(
            f"Created hybrid image: digital={digital_image.final_file_size_bytes} bytes, "
            f"print={print_image.final_file_size_bytes} bytes"
        )

        return Success(hybrid_image)

    def get_optimization_profiles(self) -> list[OptimizationProfile]:
        """Get available optimization profiles.

        Returns:
            List of predefined optimization profiles
        """
        return list(self.profiles.values())

    def optimize_with_profile(
        self, image: ImageMetadata, profile_name: str
    ) -> Result[ProcessedImage, str]:
        """Optimize image using a predefined profile.

        Args:
            image: Image metadata to optimize
            profile_name: Name of the optimization profile to use

        Returns:
            Optimized image or error message
        """
        if profile_name not in self.profiles:
            available = ", ".join(self.profiles.keys())
            return Error(f"Unknown profile '{profile_name}'. Available: {available}")

        profile = self.profiles[profile_name]

        logger.debug(f"Using optimization profile '{profile_name}' for {image.path}")

        return self._process_image(image, profile.config, profile_name)

    def _process_image(
        self, image: ImageMetadata, config: OptimizationConfig, optimization_type: str
    ) -> Result[ProcessedImage, str]:
        """Process an image with the specified optimization configuration."""
        try:
            start_time = time.time()

            # Check cache first
            cache_key = self._generate_cache_key(image, config)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Using cached optimization for {image.path}")
                return Success(cached_result)

            # Validate input image
            if not image.local_path or not image.local_path.exists():
                return Error(f"Image file not found: {image.path}")

            # Create output path
            output_path = (
                self.cache_dir / f"{cache_key}.{self._get_target_format(config)}"
            )

            # Simulate image processing (in a real implementation, this would use PIL, OpenCV, etc.)
            processed_image = self._simulate_image_processing(
                image, config, output_path, start_time
            )

            # Cache the result
            self._cache_result(cache_key, processed_image)

            logger.info(
                f"Optimized {image.path} for {optimization_type} "
                f"({image.file_size_bytes} → {processed_image.final_file_size_bytes} bytes, "
                f"{processed_image.processing_time_seconds:.2f}s)"
            )

            return Success(processed_image)

        except Exception as e:
            logger.error(f"Image processing failed for {image.path}: {str(e)}")
            return Error(f"Image processing failed: {str(e)}")

    def _simulate_image_processing(
        self,
        image: ImageMetadata,
        config: OptimizationConfig,
        output_path: Path,
        start_time: float,
    ) -> ProcessedImage:
        """Simulate image processing (placeholder for actual implementation)."""
        # In a real implementation, this would use image processing libraries

        # Simulate processing based on configuration
        original_size = image.file_size_bytes or 1000000  # Default 1MB

        # Calculate size reduction based on compression
        size_reduction = 1.0 - config.compression_level
        final_size = int(original_size * (1.0 - size_reduction))

        # Simulate resolution changes
        final_dimensions = image.dimensions
        if image.dimensions and config.target_dpi != 150:  # Assuming 150 DPI original
            scale_factor = config.target_dpi / 150.0
            final_dimensions = ImageDimensions.from_dimensions(
                int(image.dimensions.width * scale_factor),
                int(image.dimensions.height * scale_factor),
            )

        # Simulate quality assessment
        quality_loss = max(0.0, 1.0 - config.quality_priority)

        # Create processing metrics
        processing_time = time.time() - start_time

        # Determine final format
        final_format = self._get_target_format(config)

        # Generate quality metrics (simulated)
        quality_metrics = {
            "sharpness_score": max(0.1, 1.0 - quality_loss),
            "colour_accuracy": config.quality_priority,
            "compression_efficiency": config.compression_level,
            "format_compatibility": 0.9 if final_format in ["png", "jpg"] else 0.7,
        }

        # Generate optimization notes
        optimization_notes = []
        if config.target == OptimizationTarget.DIGITAL:
            optimization_notes.extend(
                [
                    "Optimized for screen display",
                    f"Target DPI: {config.target_dpi}",
                    "sRGB colour space applied",
                ]
            )
        elif config.target == OptimizationTarget.PRINT:
            optimization_notes.extend(
                [
                    "Optimized for print production",
                    f"High resolution: {config.target_dpi} DPI",
                    "Minimal compression for quality retention",
                ]
            )

        if final_format != image.path.split(".")[-1].lower():
            optimization_notes.append(f"Format converted to {final_format}")

        return ProcessedImage(
            original_metadata=image,
            processed_path=output_path,
            optimization_config=config,
            final_dimensions=final_dimensions
            or ImageDimensions.from_dimensions(800, 600),
            final_file_size_bytes=final_size,
            format=final_format,
            processing_time_seconds=processing_time,
            quality_metrics=quality_metrics,
            optimization_notes=optimization_notes,
        )

    def _get_target_format(self, config: OptimizationConfig) -> str:
        """Determine the optimal output format based on configuration."""
        if config.target == OptimizationTarget.DIGITAL:
            if config.preserve_transparency:
                return "png"
            elif config.quality_priority < 0.7:
                return "webp"  # Better compression for web
            else:
                return "jpg"
        elif config.target == OptimizationTarget.PRINT:
            if config.preserve_transparency:
                return "png"
            else:
                return "jpg"  # Good for print, widely supported
        else:
            return config.fallback_format

    def _generate_cache_key(
        self, image: ImageMetadata, config: OptimizationConfig
    ) -> str:
        """Generate a cache key for the optimization configuration."""
        # Create hash from image path and optimization parameters
        key_content = (
            f"{image.path}:{image.file_size_bytes}:"
            f"{config.target.value}:{config.quality_priority}:"
            f"{config.target_dpi}:{config.compression_level}:"
            f"{config.colour_profile}"
        )

        return hashlib.sha256(key_content.encode()).hexdigest()[:16]

    def _get_cached_result(self, cache_key: str) -> ProcessedImage | None:
        """Retrieve cached optimization result if available."""
        # In a real implementation, this would check the cache directory
        # and load cached optimization results
        return None

    def _cache_result(self, cache_key: str, processed_image: ProcessedImage) -> None:
        """Cache the optimization result for future use."""
        # In a real implementation, this would save the processed image
        # and its metadata to the cache directory
        pass

    def _create_optimization_profiles(self) -> dict[str, OptimizationProfile]:
        """Create predefined optimization profiles."""
        profiles = {}

        # Web/Digital profiles
        profiles["web_optimized"] = OptimizationProfile(
            name="web_optimized",
            target=OptimizationTarget.DIGITAL,
            config=OptimizationConfig(
                target=OptimizationTarget.DIGITAL,
                quality_priority=0.6,
                target_dpi=96,
                max_file_size_mb=1.0,
                compression_level=0.6,
            ),
            description="Optimized for web display with small file sizes",
            use_cases=["Websites", "E-books", "Digital documents"],
        )

        profiles["high_quality_digital"] = OptimizationProfile(
            name="high_quality_digital",
            target=OptimizationTarget.DIGITAL,
            config=OptimizationConfig(
                target=OptimizationTarget.DIGITAL,
                quality_priority=0.8,
                target_dpi=150,
                max_file_size_mb=3.0,
                compression_level=0.8,
            ),
            description="High-quality digital display with balanced file sizes",
            use_cases=["High-resolution screens", "Digital art", "Presentations"],
        )

        # Print profiles
        profiles["print_draft"] = OptimizationProfile(
            name="print_draft",
            target=OptimizationTarget.PRINT,
            config=OptimizationConfig(
                target=OptimizationTarget.PRINT,
                quality_priority=0.7,
                target_dpi=200,
                max_file_size_mb=5.0,
                compression_level=0.8,
            ),
            description="Draft quality print with moderate file sizes",
            use_cases=["Draft printing", "Internal documents", "Proofs"],
        )

        profiles["print_production"] = OptimizationProfile(
            name="print_production",
            target=OptimizationTarget.PRINT,
            config=OptimizationConfig(
                target=OptimizationTarget.PRINT,
                quality_priority=0.95,
                target_dpi=300,
                max_file_size_mb=20.0,
                compression_level=0.95,
            ),
            description="Production-quality print with maximum image fidelity",
            use_cases=["Professional printing", "Books", "Marketing materials"],
        )

        # Hybrid profiles
        profiles["balanced_hybrid"] = OptimizationProfile(
            name="balanced_hybrid",
            target=OptimizationTarget.HYBRID,
            config=OptimizationConfig(
                target=OptimizationTarget.HYBRID,
                quality_priority=0.75,
                target_dpi=150,
                max_file_size_mb=4.0,
                compression_level=0.8,
            ),
            description="Balanced optimization suitable for both digital and print",
            use_cases=["PDF documents", "Multi-format publishing", "General use"],
        )

        # Specialized profiles
        profiles["accessibility"] = OptimizationProfile(
            name="accessibility",
            target=OptimizationTarget.ACCESSIBILITY,
            config=OptimizationConfig(
                target=OptimizationTarget.ACCESSIBILITY,
                quality_priority=0.8,
                target_dpi=150,
                max_file_size_mb=3.0,
                compression_level=0.8,
                preserve_transparency=True,
            ),
            description="Optimized for accessibility with high contrast preservation",
            use_cases=[
                "Accessible documents",
                "Screen readers",
                "High contrast displays",
                "Accessibility compliance",
            ],
        )

        profiles["bandwidth_optimized"] = OptimizationProfile(
            name="bandwidth_optimized",
            target=OptimizationTarget.BANDWIDTH,
            config=OptimizationConfig(
                target=OptimizationTarget.BANDWIDTH,
                quality_priority=0.4,
                target_dpi=96,
                max_file_size_mb=0.5,
                compression_level=0.4,
            ),
            description="Minimal file sizes for bandwidth-constrained environments",
            use_cases=["Mobile devices", "Slow connections", "Email attachments"],
        )

        return profiles

    def clear_cache(self, older_than_days: int = 30) -> Result[dict[str, int], str]:
        """Clear optimization cache of old files.

        Args:
            older_than_days: Remove files older than this many days

        Returns:
            Statistics about cache cleanup or error message
        """
        try:
            if not self.cache_dir.exists():
                return Success({"files_removed": 0, "space_freed_bytes": 0})

            cutoff_time = time.time() - (older_than_days * 24 * 3600)

            files_removed = 0
            space_freed = 0

            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file() and cache_file.stat().st_mtime < cutoff_time:
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    files_removed += 1
                    space_freed += file_size

            logger.info(
                f"Cache cleanup: removed {files_removed} files, "
                f"freed {space_freed / (1024 * 1024):.1f} MB"
            )

            return Success(
                {
                    "files_removed": files_removed,
                    "space_freed_bytes": space_freed,
                }
            )

        except Exception as e:
            logger.error(f"Cache cleanup failed: {str(e)}")
            return Error(f"Cache cleanup failed: {str(e)}")

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get statistics about the optimization cache.

        Returns:
            Dictionary with cache statistics
        """
        try:
            if not self.cache_dir.exists():
                return {
                    "cache_directory": str(self.cache_dir),
                    "total_files": 0,
                    "total_size_bytes": 0,
                    "total_size_mb": 0.0,
                }

            total_files = 0
            total_size = 0

            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    total_files += 1
                    total_size += cache_file.stat().st_size

            return {
                "cache_directory": str(self.cache_dir),
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
            }

        except Exception as e:
            logger.error(f"Failed to get cache statistics: {str(e)}")
            return {
                "cache_directory": str(self.cache_dir),
                "error": str(e),
            }
