"""Image optimization for LaTeX documents."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
else:
    PILImage = None

# Check for PIL availability
try:
    from PIL import Image

    _pil_available = True
except ImportError:
    Image = None  # type: ignore[misc,assignment]
    _pil_available = False

# Constant that Pyright can understand is never None
PIL_AVAILABLE: bool = _pil_available


class OptimizationConfig(BaseModel):
    """Configuration for image optimization."""

    max_width: int = Field(default=1200, description="Maximum image width in pixels")
    max_height: int = Field(default=1600, description="Maximum image height in pixels")
    jpeg_quality: int = Field(default=85, description="JPEG quality (1-100)")
    png_compression: int = Field(default=6, description="PNG compression level (0-9)")
    optimize_png: bool = Field(default=True, description="Enable PNG optimization")
    preserve_aspect_ratio: bool = Field(
        default=True, description="Preserve aspect ratio when resizing"
    )


class OptimizationResult(BaseModel):
    """Result of image optimization."""

    original_path: Path
    optimized_path: Path
    original_size: tuple[int, int]  # (width, height)
    optimized_size: tuple[int, int]  # (width, height)
    file_size_before: int
    file_size_after: int
    compression_ratio: float
    was_resized: bool
    was_compressed: bool


class ImageOptimizer:
    """Optimizes images for LaTeX documents.

    Handles resizing, compression, and quality optimization while
    maintaining visual quality appropriate for print and digital use.
    """

    def __init__(self, config: OptimizationConfig | None = None) -> None:
        """Initialize the image optimizer.

        Args:
            config: Optimization configuration
        """
        if not PIL_AVAILABLE:
            raise ImportError(
                "Pillow is required for image optimization. "
                "Install with: pip install Pillow"
            )
        self.config = config or OptimizationConfig()

    def optimize_image(
        self,
        image_path: Path,
        output_dir: Path | None = None,
        context_hint: str | None = None,
    ) -> OptimizationResult:
        """Optimize an image for LaTeX document inclusion.

        Args:
            image_path: Path to source image
            output_dir: Directory for optimized image (defaults to same directory)
            context_hint: Hint about image usage context (e.g., "creature", "item", "chapter-art")

        Returns:
            Optimization result with metadata
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Determine output path
        if output_dir is None:
            output_dir = image_path.parent

        # Add optimization suffix to filename
        output_path = output_dir / f"{image_path.stem}_optimized{image_path.suffix}"

        # Get original file info
        original_file_size = image_path.stat().st_size

        # Run optimization synchronously
        result = self._optimize_sync(image_path, output_path, context_hint)

        # Get optimized file size
        optimized_file_size = output_path.stat().st_size

        return OptimizationResult(
            original_path=image_path,
            optimized_path=output_path,
            original_size=result["original_size"],
            optimized_size=result["optimized_size"],
            file_size_before=original_file_size,
            file_size_after=optimized_file_size,
            compression_ratio=original_file_size / optimized_file_size
            if optimized_file_size > 0
            else 1.0,
            was_resized=result["was_resized"],
            was_compressed=result["was_compressed"],
        )

    def _optimize_sync(
        self, input_path: Path, output_path: Path, context_hint: str | None = None
    ) -> dict[str, Any]:
        """Synchronous image optimization.

        Args:
            input_path: Source image path
            output_path: Output image path
            context_hint: Context hint for optimization strategy

        Returns:
            Dictionary with optimization metadata
        """
        try:
            if Image is None:
                raise ImportError("PIL Image not available")
            with Image.open(input_path) as img_file:
                img: PILImage = img_file
                original_size = img.size
                was_resized = False
                was_compressed = False

                # Determine optimization strategy based on context
                target_config = self._get_context_config(context_hint)

                # Resize if needed
                if self._needs_resize(img, target_config):
                    img = self._resize_image(img, target_config)
                    was_resized = True

                # Save with optimization
                save_kwargs = self._get_save_kwargs(output_path, target_config)
                img.save(output_path, **save_kwargs)
                was_compressed = True

                return {
                    "original_size": original_size,
                    "optimized_size": img.size,
                    "was_resized": was_resized,
                    "was_compressed": was_compressed,
                }

        except Exception as e:
            raise ValueError(f"Failed to optimize image: {e}") from e

    def _get_context_config(self, context_hint: str | None) -> OptimizationConfig:
        """Get optimization configuration based on context hint.

        Args:
            context_hint: Context hint (creature, item, chapter-art, etc.)

        Returns:
            Optimization configuration for the context
        """
        if context_hint == "creature":
            # Creature images can be larger for detail
            return OptimizationConfig(
                max_width=800,
                max_height=1000,
                jpeg_quality=90,
            )
        elif context_hint == "item":
            # Item images are typically smaller
            return OptimizationConfig(
                max_width=400,
                max_height=400,
                jpeg_quality=85,
            )
        elif context_hint == "chapter-art":
            # Chapter art can be full resolution
            return OptimizationConfig(
                max_width=1600,
                max_height=2000,
                jpeg_quality=95,
            )
        else:
            # Use default configuration
            return self.config

    def _needs_resize(self, img: PILImage, config: OptimizationConfig) -> bool:
        """Check if image needs resizing.

        Args:
            img: PIL Image object
            config: Optimization configuration

        Returns:
            True if resizing is needed
        """
        width, height = img.size
        return width > config.max_width or height > config.max_height

    def _resize_image(self, img: PILImage, config: OptimizationConfig) -> PILImage:
        """Resize image while preserving aspect ratio.

        Args:
            img: PIL Image object
            config: Optimization configuration

        Returns:
            Resized image
        """
        if not config.preserve_aspect_ratio:
            if Image is None:
                raise ImportError("PIL Image not available")
            return img.resize(
                (config.max_width, config.max_height), Image.Resampling.LANCZOS
            )

        # Calculate new size preserving aspect ratio
        width, height = img.size
        ratio = min(config.max_width / width, config.max_height / height)

        if ratio >= 1:
            # No resize needed
            return img

        new_width = int(width * ratio)
        new_height = int(height * ratio)

        if Image is None:
            raise ImportError("PIL Image not available")
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _get_save_kwargs(
        self, output_path: Path, config: OptimizationConfig
    ) -> dict[str, Any]:
        """Get save keyword arguments based on file format.

        Args:
            output_path: Output file path
            config: Optimization configuration

        Returns:
            Dictionary of save keyword arguments
        """
        format_ext = output_path.suffix.lower()

        if format_ext in {".jpg", ".jpeg"}:
            return {
                "format": "JPEG",
                "quality": config.jpeg_quality,
                "optimize": True,
                "progressive": True,
            }
        elif format_ext == ".png":
            return {
                "format": "PNG",
                "compress_level": config.png_compression,
                "optimize": config.optimize_png,
            }
        else:
            # Default save options
            return {"optimize": True}

    def calculate_optimal_dimensions(
        self, original_size: tuple[int, int], context_hint: str | None = None
    ) -> tuple[int, int]:
        """Calculate optimal dimensions for an image.

        Args:
            original_size: Original image dimensions (width, height)
            context_hint: Context hint for sizing strategy

        Returns:
            Optimal dimensions (width, height)
        """
        config = self._get_context_config(context_hint)
        width, height = original_size

        if not self._needs_resize_dimensions(original_size, config):
            return original_size

        # Calculate new size preserving aspect ratio
        ratio = min(config.max_width / width, config.max_height / height)

        return (int(width * ratio), int(height * ratio))

    def _needs_resize_dimensions(
        self, size: tuple[int, int], config: OptimizationConfig
    ) -> bool:
        """Check if dimensions need resizing.

        Args:
            size: Image dimensions (width, height)
            config: Optimization configuration

        Returns:
            True if resizing is needed
        """
        width, height = size
        return width > config.max_width or height > config.max_height
