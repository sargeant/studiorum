"""Rendering context management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from dnd5e.core.indexer.tag_resolver import TagResolver
from dnd5e.core.loaders.omnidexer import Omnidexer

if TYPE_CHECKING:
    from dnd5e.core.models.document_metadata import DocumentMetadata


@dataclass
class RenderContext:
    """Context object passed to renderers containing shared state and utilities.

    Provides access to the omnidexer for content lookups, tag resolver for
    cross-references, and various rendering options and metadata.
    """

    # Core services
    omnidexer: Optional[Omnidexer] = None
    tag_resolver: Optional[TagResolver] = None

    # Document metadata (structured)
    metadata: Optional["DocumentMetadata"] = None

    # Document metadata (legacy)
    title: Optional[str] = None
    subtitle: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None

    # Rendering options
    include_images: bool = False
    include_toc: bool = True
    include_index: bool = False
    page_size: str = "letterpaper"
    font_size: str = "10pt"

    # Content filtering
    include_items: bool = True
    include_creatures: bool = True
    include_spells: bool = True
    content_filters: List[str] = field(default_factory=list)

    # Paths and resources
    output_dir: Optional[Path] = None
    assets_dir: Optional[Path] = None
    images_dir: Optional[Path] = None
    fonts_dir: Optional[Path] = None

    # Custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def get_image_path(self, image_name: str) -> Optional[Path]:
        """Get full path to an image asset.

        Args:
            image_name: Name of image file

        Returns:
            Full path to image, or None if images_dir not set
        """
        if not self.images_dir or not image_name:
            return None
        return self.images_dir / image_name

    def get_font_path(self, font_name: str) -> Optional[Path]:
        """Get full path to a font asset.

        Args:
            font_name: Name of font file

        Returns:
            Full path to font, or None if fonts_dir not set
        """
        if not self.fonts_dir or not font_name:
            return None
        return self.fonts_dir / font_name

    def should_include_content_type(self, content_type: str) -> bool:
        """Check if a content type should be included based on filters.

        Args:
            content_type: Type of content to check

        Returns:
            True if content should be included
        """
        content_type = content_type.lower()

        # Check specific inclusion flags
        if content_type == "item" and not self.include_items:
            return False
        if content_type == "creature" and not self.include_creatures:
            return False
        if content_type == "spell" and not self.include_spells:
            return False

        # Check custom filters
        if self.content_filters:
            return content_type in self.content_filters

        return True

    def copy(self, **updates) -> "RenderContext":
        """Create a copy of this context with optional updates.

        Args:
            **updates: Fields to update in the copy

        Returns:
            New RenderContext with updates applied
        """
        from dataclasses import replace

        return replace(self, **updates)
