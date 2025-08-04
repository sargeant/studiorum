"""Image format conversion utilities for LaTeX compatibility."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ConversionResult(BaseModel):
    """Result of image format conversion."""

    original_path: Path
    converted_path: Path
    original_format: str
    target_format: str
    file_size_before: int
    file_size_after: int


class FormatConverter:
    """Handles image format conversion for LaTeX compatibility.

    Primarily converts WebP images to PNG since LaTeX doesn't support WebP.
    Also handles other format conversions as needed.
    """

    def __init__(self) -> None:
        """Initialize the format converter."""
        if not PIL_AVAILABLE:
            raise ImportError(
                "Pillow is required for image format conversion. "
                "Install with: pip install Pillow"
            )

    async def convert_webp_to_png(
        self, webp_path: Path, output_dir: Path | None = None
    ) -> ConversionResult:
        """Convert WebP image to PNG format.

        Args:
            webp_path: Path to WebP image file
            output_dir: Directory for output file (defaults to same directory)

        Returns:
            Conversion result with paths and metadata

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file is not a valid WebP image
        """
        if not webp_path.exists():
            raise FileNotFoundError(f"WebP file not found: {webp_path}")

        # Determine output path
        if output_dir is None:
            output_dir = webp_path.parent
        output_path = output_dir / f"{webp_path.stem}.png"

        # Get file sizes
        original_size = webp_path.stat().st_size

        # Run conversion in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, self._convert_webp_sync, webp_path, output_path
        )

        converted_size = output_path.stat().st_size

        return ConversionResult(
            original_path=webp_path,
            converted_path=output_path,
            original_format="WebP",
            target_format="PNG",
            file_size_before=original_size,
            file_size_after=converted_size,
        )

    def _convert_webp_sync(self, webp_path: Path, png_path: Path) -> None:
        """Synchronous WebP to PNG conversion.

        Args:
            webp_path: Input WebP file
            png_path: Output PNG file
        """
        try:
            with Image.open(webp_path) as img:
                # Convert to RGB if necessary (WebP can have transparency)
                if img.mode in ("RGBA", "LA"):
                    # Create white background for transparency
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(
                            img, mask=img.split()[-1]
                        )  # Use alpha channel as mask
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Save as PNG
                img.save(png_path, "PNG", optimize=True)

        except Exception as e:
            raise ValueError(f"Failed to convert WebP to PNG: {e}") from e

    async def convert_to_compatible_format(
        self, image_path: Path, output_dir: Path | None = None
    ) -> ConversionResult | None:
        """Convert image to LaTeX-compatible format if needed.

        Args:
            image_path: Path to image file
            output_dir: Directory for output file

        Returns:
            Conversion result if conversion was needed, None if already compatible
        """
        # Check if conversion is needed
        suffix = image_path.suffix.lower()

        if suffix == ".webp":
            return await self.convert_webp_to_png(image_path, output_dir)
        elif suffix in {".png", ".jpg", ".jpeg", ".pdf"}:
            # Already LaTeX compatible
            return None
        else:
            # Unknown format - try to convert to PNG
            return await self._convert_unknown_format(image_path, output_dir)

    async def _convert_unknown_format(
        self, image_path: Path, output_dir: Path | None = None
    ) -> ConversionResult:
        """Convert unknown image format to PNG.

        Args:
            image_path: Path to image file
            output_dir: Directory for output file

        Returns:
            Conversion result
        """
        if output_dir is None:
            output_dir = image_path.parent
        output_path = output_dir / f"{image_path.stem}.png"

        original_size = image_path.stat().st_size

        await asyncio.get_event_loop().run_in_executor(
            None, self._convert_to_png_sync, image_path, output_path
        )

        converted_size = output_path.stat().st_size

        return ConversionResult(
            original_path=image_path,
            converted_path=output_path,
            original_format=image_path.suffix.upper().lstrip("."),
            target_format="PNG",
            file_size_before=original_size,
            file_size_after=converted_size,
        )

    def _convert_to_png_sync(self, input_path: Path, output_path: Path) -> None:
        """Synchronous conversion to PNG.

        Args:
            input_path: Input image file
            output_path: Output PNG file
        """
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "LA"):
                    # Create white background for transparency
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Save as PNG
                img.save(output_path, "PNG", optimize=True)

        except Exception as e:
            raise ValueError(
                f"Failed to convert {input_path.suffix} to PNG: {e}"
            ) from e

    def is_conversion_needed(self, image_path: Path) -> bool:
        """Check if image format conversion is needed for LaTeX.

        Args:
            image_path: Path to image file

        Returns:
            True if conversion is needed
        """
        latex_compatible_formats = {".png", ".jpg", ".jpeg", ".pdf", ".eps"}
        return image_path.suffix.lower() not in latex_compatible_formats
