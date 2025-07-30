"""Rendering context management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dnd5e.core.loaders.omnidexer import Omnidexer

if TYPE_CHECKING:
    from dnd5e.core.config.latex_config import LaTeXConfig
    from dnd5e.core.indexer.tag_resolver import TagResolver
    from dnd5e.core.models.document_metadata import DocumentMetadata


@dataclass
class RenderContext:
    """Context object passed to renderers containing shared state and utilities.

    Provides access to the omnidexer for content lookups, tag resolver for
    cross-references, and various rendering options and metadata.
    """

    # Core services
    omnidexer: Omnidexer | None = None
    tag_resolver: TagResolver | None = (
        None  #: :class:`dnd5e.core.indexer.tag_resolver.TagResolver` for cross-references
    )

    # Document metadata (structured)
    metadata: DocumentMetadata | None = None

    # LaTeX configuration
    latex_config: LaTeXConfig | None = None

    # Document metadata (legacy)
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None

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
    content_filters: list[str] = field(default_factory=list)

    # Paths and resources
    output_dir: Path | None = None
    assets_dir: Path | None = None
    images_dir: Path | None = None
    fonts_dir: Path | None = None

    # Custom data
    custom_data: dict[str, Any] = field(default_factory=dict)

    def get_image_path(self, image_name: str) -> Path | None:
        """Get full path to an image asset.

        Args:
            image_name: Name of image file

        Returns:
            Full path to image, or None if images_dir not set
        """
        if not self.images_dir or not image_name:
            return None
        return self.images_dir / image_name

    def get_font_path(self, font_name: str) -> Path | None:
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

    def copy(self, **updates: Any) -> RenderContext:
        """Create a copy of this context with optional updates.

        Args:
            **updates: Fields to update in the copy

        Returns:
            New RenderContext with updates applied
        """
        from dataclasses import replace

        return replace(self, **updates)
