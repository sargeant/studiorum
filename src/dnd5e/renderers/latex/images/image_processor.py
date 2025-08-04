"""Core image processing pipeline for LaTeX documents."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dnd5e.renderers.base.context import RenderContext


class ImageProcessingConfig(BaseModel):
    """Configuration for image processing pipeline."""

    enable_webp_conversion: bool = Field(
        default=True, description="Convert WebP images to PNG"
    )
    enable_optimization: bool = Field(
        default=True, description="Optimize image sizes and quality"
    )
    enable_placement_optimization: bool = Field(
        default=True, description="Optimize image placement"
    )
    cache_processed_images: bool = Field(
        default=True, description="Cache processed images"
    )
    max_image_width: int = Field(
        default=1200, description="Maximum image width in pixels"
    )
    jpeg_quality: int = Field(default=85, description="JPEG quality for optimization")
    png_compression: int = Field(default=6, description="PNG compression level (0-9)")


class ProcessedImage(BaseModel):
    """Result of image processing pipeline."""

    original_path: Path
    processed_path: Path
    latex_command: str
    width_specification: str
    placement_hint: str | None = None
    caption: str | None = None


class ImageProcessor:
    """Core image processing pipeline for LaTeX documents.

    Coordinates image conversion, optimization, and LaTeX generation
    while integrating with the existing rendering system.
    """

    def __init__(self, config: ImageProcessingConfig | None = None) -> None:
        """Initialize the image processor.

        Args:
            config: Image processing configuration
        """
        self.config = config or ImageProcessingConfig()
        self._format_converter: Any = None  # Will be initialized lazily
        self._optimizer: Any = None  # Will be initialized lazily
        self._placer: Any = None  # Will be initialized lazily
        self._image_manager: Any = None  # Will be initialized lazily

    async def process_image_entry(
        self,
        image_entry: dict[str, Any],
        context: RenderContext,
    ) -> str:
        """Process an image entry and return LaTeX code.

        This method integrates with the existing RecursiveEntryProcessor
        to provide enhanced image processing capabilities.

        Args:
            image_entry: Image entry dictionary with href, title, etc.
            context: Current rendering context

        Returns:
            LaTeX code for the processed image
        """
        # If images are disabled, return placeholder
        if not context.include_images:
            title = image_entry.get("title", "")
            return f"% Image placeholder: {title}" if title else "% Image placeholder"

        href = image_entry.get("href", "")
        if not href:
            title = image_entry.get("title", "")
            return f"% Image placeholder: {title}" if title else "% Image placeholder"

        try:
            # Process the image through the pipeline
            processed = await self._process_image_pipeline(href, image_entry, context)
            return processed.latex_command

        except Exception as e:
            # Fallback to basic image handling
            title = image_entry.get("title", "")
            return (
                f"% Image processing failed ({e}): {title}"
                if title
                else f"% Image processing failed: {e}"
            )

    async def _process_image_pipeline(
        self,
        image_path: str,
        image_entry: dict[str, Any],
        context: RenderContext,
    ) -> ProcessedImage:
        """Run the complete image processing pipeline.

        Args:
            image_path: Original image path/URL
            image_entry: Complete image entry data
            context: Rendering context

        Returns:
            Processed image with LaTeX command
        """
        # Step 1: Resolve and download image if needed
        resolved_path = await self._resolve_image_path(image_path, context)

        # Step 2: Convert format if needed (WebP -> PNG)
        converted_path = await self._convert_format_if_needed(resolved_path)

        # Step 3: Optimize image (resize, compress)
        optimized_path = await self._optimize_image(converted_path, context)

        # Step 4: Generate LaTeX with intelligent placement
        latex_command = await self._generate_latex_command(
            optimized_path, image_entry, context
        )

        return ProcessedImage(
            original_path=Path(image_path),
            processed_path=optimized_path,
            latex_command=latex_command,
            width_specification=self._calculate_width_spec(image_entry),
            placement_hint=image_entry.get("placement"),
            caption=image_entry.get("title"),
        )

    async def _resolve_image_path(
        self, image_path: str, context: RenderContext
    ) -> Path:
        """Resolve image path, handling URLs and local paths.

        Args:
            image_path: Original image path or URL
            context: Rendering context

        Returns:
            Local path to the image file
        """
        # For now, implement basic local path resolution
        # TODO: Add URL downloading and 5etools-img integration

        if image_path.startswith(("http://", "https://")):
            # URL - would need to download
            # For now, return a placeholder path
            return Path("placeholder.png")

        # Local path - resolve relative to assets directory
        if context.assets_dir:
            return context.assets_dir / image_path
        else:
            return Path(image_path)

    async def _convert_format_if_needed(self, image_path: Path) -> Path:
        """Convert image format if needed (e.g., WebP to PNG).

        Args:
            image_path: Path to original image

        Returns:
            Path to converted image (or original if no conversion needed)
        """
        if not self.config.enable_webp_conversion:
            return image_path

        # Initialize format converter lazily
        if self._format_converter is None:
            try:
                from .format_converter import FormatConverter

                self._format_converter = FormatConverter()
            except ImportError:
                # PIL not available, skip conversion
                return image_path

        try:
            # Check if conversion is needed
            if self._format_converter.is_conversion_needed(image_path):
                result = await self._format_converter.convert_to_compatible_format(
                    image_path
                )
                if result:
                    return result.converted_path
            return image_path

        except Exception:
            # If conversion fails, return original
            return image_path

    async def _optimize_image(self, image_path: Path, context: RenderContext) -> Path:
        """Optimize image size and quality.

        Args:
            image_path: Path to image to optimize
            context: Rendering context

        Returns:
            Path to optimized image
        """
        if not self.config.enable_optimization:
            return image_path

        # Initialize optimizer lazily
        if self._optimizer is None:
            try:
                from .image_optimizer import ImageOptimizer, OptimizationConfig

                opt_config = OptimizationConfig(
                    max_width=self.config.max_image_width,
                    jpeg_quality=self.config.jpeg_quality,
                    png_compression=self.config.png_compression,
                )
                self._optimizer = ImageOptimizer(opt_config)
            except ImportError:
                # PIL not available, skip optimization
                return image_path

        try:
            # TODO: Extract context hint from image entry
            result = await self._optimizer.optimize_image(image_path)
            return result.optimized_path

        except Exception:
            # If optimization fails, return original
            return image_path

    async def _generate_latex_command(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        context: RenderContext,
    ) -> str:
        """Generate LaTeX command for the processed image.

        Args:
            image_path: Path to processed image
            image_entry: Original image entry data
            context: Rendering context

        Returns:
            LaTeX command string
        """
        if not self.config.enable_placement_optimization:
            # Use basic placement
            title = image_entry.get("title", "")
            width_spec = self._calculate_width_spec(image_entry)

            if title:
                return f"""\\begin{{figure}}[htbp]
    \\centering
    \\includegraphics[width={width_spec}]{{{image_path}}}
    \\caption{{{title}}}
\\end{{figure}}"""
            else:
                return f"\\includegraphics[width={width_spec}]{{{image_path}}}"

        # Initialize placer lazily
        if self._placer is None:
            from .image_placer import ImagePlacer

            self._placer = ImagePlacer()

        try:
            # Use intelligent placement
            # TODO: Extract context hint from image entry or content
            result = self._placer.place_image(image_path, image_entry)
            return result.latex_command

        except Exception:
            # Fallback to basic placement
            title = image_entry.get("title", "")
            width_spec = self._calculate_width_spec(image_entry)

            if title:
                return f"""\\begin{{figure}}[htbp]
    \\centering
    \\includegraphics[width={width_spec}]{{{image_path}}}
    \\caption{{{title}}}
\\end{{figure}}"""
            else:
                return f"\\includegraphics[width={width_spec}]{{{image_path}}}"

    def _calculate_width_spec(self, image_entry: dict[str, Any]) -> str:
        """Calculate LaTeX width specification for image.

        Args:
            image_entry: Image entry data

        Returns:
            LaTeX width specification (e.g., "0.8\\textwidth")
        """
        # TODO: Add intelligent sizing based on image type and content
        # For now, use simple default
        return "0.8\\textwidth"
