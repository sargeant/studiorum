"""Core image processing pipeline for LaTeX documents."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.renderers.core.interfaces import RenderingContext

logger = get_logger(__name__)

if TYPE_CHECKING:
    from .format_converter import FormatConverter
    from .image_optimizer import ImageOptimizer
    from .image_placer import ImagePlacer


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
    jpeg_quality: int = Field(
        default=85, ge=1, le=100, description="JPEG quality for optimization"
    )
    png_compression: int = Field(
        default=6, ge=0, le=9, description="PNG compression level (0-9)"
    )


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
        self._format_converter: FormatConverter | None = (
            None  # Will be initialized lazily
        )
        self._optimizer: ImageOptimizer | None = None  # Will be initialized lazily
        self._placer: ImagePlacer | None = None  # Will be initialized lazily
        self._image_manager: Any = None  # Will be initialized lazily

    def process_image_entry(
        self,
        image_entry: dict[str, Any],
        context: RenderingContext,
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
        include_images = context.metadata.get("include_images", True)
        if not include_images:
            title = image_entry.get("title", "")
            return f"% Image placeholder: {title}" if title else "% Image placeholder"

        href = image_entry.get("href", "")
        if not href:
            title = image_entry.get("title", "")
            logger.error(f"Image entry missing href: {title or 'untitled'}")
            return f"% Image placeholder: {title}" if title else "% Image placeholder"

        # Extract actual path from href structure
        image_path = self._extract_image_path(href)
        if not image_path:
            title = image_entry.get("title", "")
            logger.error(
                f"Invalid href structure for image: {title or 'untitled'}, href={href}"
            )
            return (
                f"% Image placeholder (invalid href): {title}"
                if title
                else "% Image placeholder (invalid href)"
            )

        title = image_entry.get("title", "")
        logger.info(f"Processing image: {title or 'untitled'} from path: {image_path}")

        try:
            # Process the image through the pipeline
            processed = self._process_image_pipeline(image_path, image_entry, context)
            logger.info(
                f"Successfully processed image: {title or 'untitled'} -> {processed.processed_path}"
            )
            return processed.latex_command

        except Exception as e:
            # Fallback to basic image handling
            title = image_entry.get("title", "")
            logger.error(
                f"Failed to process image '{title or 'untitled'}' from {image_path}: {e}",
                exc_info=True,
            )
            return (
                f"% Image processing failed ({e}): {title}"
                if title
                else f"% Image processing failed: {e}"
            )

    def _process_image_pipeline(
        self,
        image_path: str,
        image_entry: dict[str, Any],
        context: RenderingContext,
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
        logger.debug(f"Resolving image path: {image_path}")
        resolved_path = self._resolve_image_path(image_path, context)

        # Check if image was found
        if resolved_path is None:
            # Image not found, raise exception to trigger fallback
            logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Step 2: Convert format if needed (WebP -> PNG)
        converted_path = self._convert_format_if_needed(resolved_path)

        # Step 3: Optimize image (resize, compress)
        optimized_path = self._optimize_image(converted_path, context)

        # Step 4: Generate LaTeX with intelligent placement
        latex_command = self._generate_latex_command(
            optimized_path, image_entry, context
        )

        return ProcessedImage(
            original_path=Path(image_path),
            processed_path=optimized_path,
            latex_command=latex_command,
            width_specification=self._calculate_width_spec(image_entry, context),
            placement_hint=image_entry.get("placement"),
            caption=image_entry.get("title"),
        )

    def _resolve_image_path(
        self, image_path: str, context: RenderingContext
    ) -> Path | None:
        """Resolve image path, handling URLs and local paths.

        Args:
            image_path: Original image path or URL
            context: Rendering context

        Returns:
            Local path to the image file, or None if not found
        """
        # For now, implement basic local path resolution
        # TODO: Add URL downloading and 5etools-img integration

        if image_path.startswith(("http://", "https://")):
            # URL - would need to download
            # For now, return None to indicate we can't handle URLs yet
            return None

        # Try to resolve relative to configured image directory first
        from studiorum.core.config.unified_config import get_app_config

        app_config = get_app_config()

        if app_config.image.image_directory:
            image_file_path = app_config.image.image_directory / image_path
            logger.debug(f"Looking for image at: {image_file_path}")
            if image_file_path.exists():
                logger.debug(f"Found image at configured directory: {image_file_path}")
                return image_file_path
            else:
                logger.debug(f"Image not found at: {image_file_path}")

        # Fallback to assets directory from metadata
        assets_dir = context.metadata.get("assets_dir")
        if assets_dir:
            fallback_path = Path(assets_dir) / image_path
            logger.debug(f"Looking for image in assets dir: {fallback_path}")
            if fallback_path.exists():
                logger.debug(f"Found image at assets directory: {fallback_path}")
                return fallback_path

        # If we get here, the file doesn't exist in any of our search locations
        logger.warning(f"Image not found in any search location: {image_path}")
        return None

    def _convert_format_if_needed(self, image_path: Path) -> Path:
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
                result = self._format_converter.convert_to_compatible_format(image_path)
                if result is not None:
                    return result.converted_path
            return image_path

        except Exception:
            # If conversion fails, return original
            return image_path

    def _optimize_image(self, image_path: Path, context: RenderingContext) -> Path:
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
            result = self._optimizer.optimize_image(image_path)
            return result.optimized_path

        except Exception:
            # If optimization fails, return original
            return image_path

    def _generate_latex_command(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        context: RenderingContext,
    ) -> str:
        """Generate LaTeX command for the processed image.

        Args:
            image_path: Path to processed image
            image_entry: Original image entry data
            context: Rendering context

        Returns:
            LaTeX command string
        """
        # Final validation: ensure the image file actually exists
        if not image_path.exists():
            raise FileNotFoundError(f"Processed image file not found: {image_path}")

        # Check if we're in a gallery context
        in_gallery = context.metadata.get("in_gallery", False)

        if not self.config.enable_placement_optimization:
            # Use basic placement
            title = image_entry.get("title", "")
            width_spec = self._calculate_width_spec(image_entry, context)

            if in_gallery:
                # In gallery context, don't wrap in figure - just return the image
                return f"\\includegraphics[{width_spec}]{{{image_path}}}"
            elif title:
                return f"""\\begin{{figure}}[htbp]
    \\centering
    \\includegraphics[{width_spec}]{{{image_path}}}
    \\caption{{{title}}}
\\end{{figure}}"""
            else:
                return f"\\includegraphics[{width_spec}]{{{image_path}}}"

        # Initialize placer lazily - use enhanced placer with ContentAwarePlacementStrategy
        if self._placer is None:
            try:
                from .enhanced_image_placer import EnhancedImagePlacer

                self._placer = EnhancedImagePlacer()
            except ImportError:
                # Fallback to basic placer if enhanced version not available
                from .image_placer import ImagePlacer

                self._placer = ImagePlacer()

        try:
            # Use intelligent placement with enhanced context
            # Extract context information for better placement decisions
            placement_context = self._build_placement_context(image_entry, context)

            if hasattr(self._placer, "place_image_with_context"):
                result = self._placer.place_image_with_context(
                    image_path, image_entry, placement_context
                )
            else:
                # Fallback for basic placer
                result = self._placer.place_image(image_path, image_entry)

            # Check if we're in a gallery context and need to unwrap figure
            if in_gallery and result.latex_command:
                latex_cmd = result.latex_command
                # Extract just the includegraphics command from figure environment
                if "\\includegraphics" in latex_cmd:
                    import re

                    # Find the includegraphics line (handle multiline with re.DOTALL)
                    match = re.search(
                        r"\\includegraphics\[.*?\]\{.*?\}", latex_cmd, re.DOTALL
                    )
                    if match:
                        return match.group(0)

            return result.latex_command

        except Exception:
            # Fallback to basic placement
            title = image_entry.get("title", "")
            width_spec = self._calculate_width_spec(image_entry, context)

            if in_gallery:
                # In gallery context, don't wrap in figure - just return the image
                return f"\\includegraphics[{width_spec}]{{{image_path}}}"
            elif title:
                return f"""\\begin{{figure}}[htbp]
    \\centering
    \\includegraphics[{width_spec}]{{{image_path}}}
    \\caption{{{title}}}
\\end{{figure}}"""
            else:
                return f"\\includegraphics[{width_spec}]{{{image_path}}}"

    def _calculate_width_spec(
        self, image_entry: dict[str, Any], context: RenderingContext | None = None
    ) -> str:
        """Calculate LaTeX width specification for image.

        Args:
            image_entry: Image entry data
            context: Rendering context for layout awareness

        Returns:
            LaTeX width specification with both width and height constraints
        """
        # Check if we're in a gallery context (different sizing rules)
        if context and context.metadata.get("in_gallery", False):
            # Gallery images should fill subfigure but respect aspect ratio
            return "width=\\textwidth,height=0.25\\textheight,keepaspectratio"

        # Check if we're in a two-column layout (most 5e content)
        layout_mode = (
            context.metadata.get("layout_mode", "twocolumn") if context else "twocolumn"
        )

        # For item compendiums and similar content, use column-aware sizing
        if layout_mode == "twocolumn":
            # In two-column layout, textwidth spans both columns
            # We want images to fit within a single column
            content_type = context.metadata.get("content_type") if context else None

            if content_type == "item":
                # Item images should be smaller and not dominate the layout
                # Constrain both width and height to prevent page overflow
                return "width=0.6\\columnwidth,height=0.2\\textheight,keepaspectratio"
            elif content_type == "spell":
                # Spell images also conservative sizing
                return "width=0.7\\columnwidth,height=0.25\\textheight,keepaspectratio"
            elif content_type == "creature":
                # Creature images can be larger but still within column
                return "width=0.9\\columnwidth,height=0.3\\textheight,keepaspectratio"
            else:
                # General content in two-column layout
                return "width=0.8\\columnwidth,height=0.3\\textheight,keepaspectratio"

        # Single column or full-width layouts
        return "width=0.8\\textwidth,height=0.4\\textheight,keepaspectratio"

    def _build_placement_context(
        self, image_entry: dict[str, Any], context: RenderingContext
    ) -> dict[str, Any]:
        """Build placement context for ContentAwarePlacementStrategy.

        Args:
            image_entry: Image entry data
            context: Rendering context

        Returns:
            Dictionary with context information for placement decisions
        """
        placement_context = {
            "content_type": context.metadata.get("content_type", "unknown"),
            "layout_mode": context.metadata.get("layout_mode", "twocolumn"),
            "image_context": context.metadata.get("image_context", "illustration"),
            "placement_hint": image_entry.get("placement_hint", "auto"),
            "content_name": context.metadata.get("item_name")
            or image_entry.get("title", ""),
            "in_gallery": context.metadata.get("in_gallery", False),
            "current_section": context.metadata.get("current_section", ""),
            # Add sizing preferences based on content type
            "preferred_size": self._get_preferred_size_for_content(
                context.metadata.get("content_type")
            ),
        }
        return placement_context

    def _get_preferred_size_for_content(self, content_type: str | None) -> str:
        """Get preferred size category based on content type.

        Args:
            content_type: Type of content being processed

        Returns:
            Size preference string
        """
        size_preferences = {
            "item": "small",
            "spell": "small",
            "creature": "medium",
            "adventure": "large",
            "chapter": "large",
        }
        return size_preferences.get(content_type or "unknown", "medium")

    def _extract_image_path(self, href: str | dict[str, Any]) -> str:
        """Extract the actual image path from href structure.

        Args:
            href: Either a string path or a dictionary with 'type' and 'path' keys

        Returns:
            String path to the image, or empty string if extraction fails
        """
        if isinstance(href, str):
            return href
        elif isinstance(href, dict):
            # Handle 5etools href structure: {"type": "internal", "path": "..."}
            if href.get("type") == "internal" and "path" in href:
                return href["path"]
            # Handle other possible href structures
            elif "path" in href:
                return href["path"]
            elif "href" in href:
                return href["href"]
            elif "url" in href:
                return href["url"]

        # If we can't extract a path, return empty string
        return ""
