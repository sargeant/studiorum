"""FluffImageExtractor service for extracting and processing images from fluff content.

This service is designed to work with the future image system and provides
image extraction capabilities for Phase 5 fluff features.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..logging import get_logger
from ..models.fluff import BaseFluff

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer

logger = get_logger(__name__)


class FluffImageInfo:
    """Information about an image extracted from fluff content."""

    def __init__(
        self,
        path: str,
        credit: str | None = None,
        image_type: str = "image",
        source_fluff: str | None = None,
        source_abbreviation: str | None = None,
        alt_text: str | None = None,
        caption: str | None = None,
        **metadata: Any,
    ) -> None:
        self.path = path
        self.credit = credit
        self.image_type = image_type
        self.source_fluff = source_fluff
        self.source_abbreviation = source_abbreviation
        self.alt_text = alt_text
        self.caption = caption
        self.metadata = metadata

    @property
    def filename(self) -> str:
        """Get the filename from the path."""
        return Path(self.path).name if self.path else ""

    @property
    def extension(self) -> str:
        """Get the file extension."""
        return Path(self.path).suffix.lower() if self.path else ""

    def is_supported_format(self) -> bool:
        """Check if the image format is supported."""
        supported_formats = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        return self.extension in supported_formats

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "credit": self.credit,
            "image_type": self.image_type,
            "source_fluff": self.source_fluff,
            "source_abbreviation": self.source_abbreviation,
            "alt_text": self.alt_text,
            "caption": self.caption,
            "filename": self.filename,
            "extension": self.extension,
            "supported": self.is_supported_format(),
            **self.metadata,
        }


class FluffImageExtractor:
    """Service for extracting images from fluff content.

    This service is designed to be future-ready for when the image system
    becomes fully operational. It provides comprehensive image extraction
    and metadata generation capabilities.
    """

    def __init__(self, omnidexer: "Omnidexer | None" = None) -> None:
        """Initialize the FluffImageExtractor.

        Args:
            omnidexer: Optional omnidexer for content lookup
        """
        self.omnidexer = omnidexer

    def extract_images_from_fluff(self, fluff: BaseFluff) -> list[FluffImageInfo]:
        """Extract all images from a fluff entry.

        Args:
            fluff: The fluff entry to extract images from

        Returns:
            List of FluffImageInfo objects with image details
        """
        images = []

        # Extract from dedicated images field
        for img in fluff.images:
            image_path = img.get_path()
            if image_path:
                image_info = FluffImageInfo(
                    path=image_path,
                    credit=img.credit,
                    image_type=img.type,
                    source_fluff=fluff.name,
                    source_abbreviation=fluff.source.abbreviation,
                    alt_text=self._generate_alt_text(fluff.name, img.credit),
                )
                images.append(image_info)

        # Extract from entries that might contain image references
        for entry in fluff.entries:
            entry_images = self._extract_images_from_entry(entry, fluff)
            images.extend(entry_images)

        return images

    def _extract_images_from_entry(
        self, entry: Any, fluff: BaseFluff
    ) -> list[FluffImageInfo]:
        """Extract images from a single fluff entry.

        Args:
            entry: The fluff entry to check
            fluff: The parent fluff object for context

        Returns:
            List of FluffImageInfo objects found in the entry
        """
        images = []

        # Check if the entry itself is an image type
        if hasattr(entry, "type") and entry.type == "image":
            # Handle image entries with href field
            if hasattr(entry, "href") and entry.href:
                if isinstance(entry.href, dict) and "path" in entry.href:
                    image_info = FluffImageInfo(
                        path=entry.href["path"],
                        credit=getattr(entry, "credit", None),
                        image_type="image",
                        source_fluff=fluff.name,
                        source_abbreviation=fluff.source.abbreviation,
                        alt_text=self._generate_alt_text(
                            fluff.name, getattr(entry, "credit", None)
                        ),
                    )
                    images.append(image_info)

        # Check entry content for embedded image references
        if hasattr(entry, "content") and entry.content:
            content_str = str(entry.content)
            embedded_images = self._extract_image_references_from_text(
                content_str, fluff
            )
            images.extend(embedded_images)

        return images

    def _extract_image_references_from_text(
        self, text: str, fluff: BaseFluff
    ) -> list[FluffImageInfo]:
        """Extract image references from text content.

        Args:
            text: The text content to search
            fluff: The parent fluff object for context

        Returns:
            List of FluffImageInfo objects found in the text
        """
        images = []

        # Pattern to match 5etools image references like {@img path/to/image.png}
        image_pattern = r"\{@img\s+([^}]+)\}"
        matches = re.finditer(image_pattern, text, re.IGNORECASE)

        for match in matches:
            image_path = match.group(1).strip()
            # Clean up the path (remove quotes, extra spaces)
            image_path = image_path.strip("\"'")

            if image_path:
                image_info = FluffImageInfo(
                    path=image_path,
                    image_type="embedded",
                    source_fluff=fluff.name,
                    source_abbreviation=fluff.source.abbreviation,
                    alt_text=self._generate_alt_text(fluff.name),
                    caption=self._extract_caption_near_image(text, match.start()),
                )
                images.append(image_info)

        # Pattern to match other common image patterns
        # This can be expanded based on actual 5etools data formats
        url_pattern = r"https?://[^\s]+\.(png|jpg|jpeg|gif|webp|bmp)"
        url_matches = re.finditer(url_pattern, text, re.IGNORECASE)

        for match in url_matches:
            image_url = match.group(0)
            image_info = FluffImageInfo(
                path=image_url,
                image_type="url",
                source_fluff=fluff.name,
                source_abbreviation=fluff.source.abbreviation,
                alt_text=self._generate_alt_text(fluff.name),
                is_external_url=True,
            )
            images.append(image_info)

        return images

    def _generate_alt_text(self, fluff_name: str, credit: str | None = None) -> str:
        """Generate alt text for accessibility.

        Args:
            fluff_name: Name of the fluff content
            credit: Optional image credit

        Returns:
            Generated alt text
        """
        base_alt = f"Illustration for {fluff_name}"
        if credit:
            base_alt += f" (Credit: {credit})"
        return base_alt

    def _extract_caption_near_image(
        self, text: str, image_position: int, context_chars: int = 100
    ) -> str | None:
        """Extract potential caption text near an image reference.

        Args:
            text: The full text content
            image_position: Position of the image reference in the text
            context_chars: Number of characters to look around the image

        Returns:
            Potential caption text or None
        """
        # Look for text immediately after the image reference
        start = max(0, image_position - context_chars)
        end = min(len(text), image_position + context_chars)
        context = text[start:end]

        # Look for common caption patterns
        caption_patterns = [
            r"\{@img[^}]+\}\s*([^{@]+?)(?:\{@|$)",  # Text after image tag
            r"\bcaption[:\s]*([^\n\.]+)",  # Explicit caption
            r"\billustration[:\s]*([^\n\.]+)",  # Illustration description
        ]

        for pattern in caption_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                caption = match.group(1).strip()
                if len(caption) > 5 and len(caption) < 200:  # Reasonable caption length
                    return caption

        return None

    def filter_images_by_type(
        self, images: list[FluffImageInfo], image_types: list[str]
    ) -> list[FluffImageInfo]:
        """Filter images by their type.

        Args:
            images: List of image info objects
            image_types: List of image types to include

        Returns:
            Filtered list of images
        """
        return [img for img in images if img.image_type in image_types]

    def filter_images_by_format(
        self, images: list[FluffImageInfo], supported_only: bool = True
    ) -> list[FluffImageInfo]:
        """Filter images by format support.

        Args:
            images: List of image info objects
            supported_only: Whether to include only supported formats

        Returns:
            Filtered list of images
        """
        if supported_only:
            return [img for img in images if img.is_supported_format()]
        return images

    def get_image_statistics(self, images: list[FluffImageInfo]) -> dict[str, Any]:
        """Get statistics about extracted images.

        Args:
            images: List of image info objects

        Returns:
            Dictionary with image statistics
        """
        stats: dict[str, Any] = {
            "total_images": len(images),
            "by_type": {},
            "by_format": {},
            "by_source": {},
            "supported_formats": 0,
            "external_urls": 0,
            "has_credits": 0,
            "has_captions": 0,
        }

        by_type = stats["by_type"]  # type: dict[str, int]
        by_format = stats["by_format"]  # type: dict[str, int]
        by_source = stats["by_source"]  # type: dict[str, int]

        for img in images:
            # Count by type
            by_type[img.image_type] = by_type.get(img.image_type, 0) + 1

            # Count by format
            if img.extension:
                by_format[img.extension] = by_format.get(img.extension, 0) + 1

            # Count by source
            if img.source_abbreviation:
                by_source[img.source_abbreviation] = (
                    by_source.get(img.source_abbreviation, 0) + 1
                )

            # Count various attributes
            if img.is_supported_format():
                stats["supported_formats"] += 1

            if img.metadata.get("is_external_url"):
                stats["external_urls"] += 1

            if img.credit:
                stats["has_credits"] += 1

            if img.caption:
                stats["has_captions"] += 1

        return stats

    def create_image_manifest(self, images: list[FluffImageInfo]) -> dict[str, Any]:
        """Create a manifest of all extracted images for future processing.

        Args:
            images: List of image info objects

        Returns:
            Image manifest dictionary suitable for JSON serialization
        """
        return {
            "version": "1.0.0",
            "generated_by": "FluffImageExtractor",
            "statistics": self.get_image_statistics(images),
            "images": [img.to_dict() for img in images],
        }
