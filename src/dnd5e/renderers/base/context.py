"""Rendering context management."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from dnd5e.core.loaders.omnidexer import Omnidexer

if TYPE_CHECKING:
    from dnd5e.core.config.latex_config import LaTeXConfig
    from dnd5e.core.indexer.tag_resolver import TagResolver
    from dnd5e.core.models.document_metadata import DocumentMetadata


class RenderContext(BaseModel):
    """Context object passed to renderers containing shared state and utilities.

    Provides access to the omnidexer for content lookups, tag resolver for
    cross-references, and various rendering options and metadata.
    """

    # Core services
    omnidexer: Any = Field(
        None, description="Content indexer for lookups"
    )  # TODO: Restore Omnidexer | None after test compatibility
    # TODO: Replace Any with proper types once TagResolver is migrated to Pydantic
    tag_resolver: Any = Field(None, description="Tag resolver for cross-references")

    # Document metadata (structured)
    # TODO: Replace Any with proper types once DocumentMetadata is migrated to Pydantic
    metadata: Any = Field(None, description="Structured document metadata")

    # LaTeX configuration
    # TODO: Replace Any with proper types once LaTeXConfig is migrated to Pydantic
    latex_config: Any = Field(None, description="LaTeX compilation configuration")

    # Document metadata (legacy)
    title: str | None = Field(None, description="Document title")
    subtitle: str | None = Field(None, description="Document subtitle")
    author: str | None = Field(None, description="Document author")
    date: str | None = Field(None, description="Document date")

    # Rendering options
    include_images: bool = Field(default=False, description="Whether to include images")
    include_toc: bool = Field(
        default=True, description="Whether to include table of contents"
    )
    include_index: bool = Field(default=False, description="Whether to include index")
    page_size: str = Field(default="letterpaper", description="Page size for output")
    font_size: str = Field(default="10pt", description="Base font size")

    # Content filtering
    include_items: bool = Field(default=True, description="Whether to include items")
    include_creatures: bool = Field(
        default=True, description="Whether to include creatures"
    )
    include_spells: bool = Field(default=True, description="Whether to include spells")
    content_filters: list[str] = Field(
        default_factory=list, description="Content type filters"
    )

    # Paths and resources
    output_dir: Path | None = Field(None, description="Output directory path")
    assets_dir: Path | None = Field(None, description="Assets directory path")
    images_dir: Path | None = Field(None, description="Images directory path")
    fonts_dir: Path | None = Field(None, description="Fonts directory path")

    # Custom data
    custom_data: dict[str, Any] = Field(
        default_factory=dict, description="Custom renderer data"
    )

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: str) -> str:
        """Validate LaTeX page size."""
        valid_sizes = {
            "letterpaper",
            "a4paper",
            "a5paper",
            "b5paper",
            "executivepaper",
            "legalpaper",
        }

        size_lower = v.lower().strip()
        if size_lower not in valid_sizes:
            raise ValueError(f"Invalid page size '{v}'. Must be one of {valid_sizes}")

        return size_lower

    @field_validator("font_size")
    @classmethod
    def validate_font_size(cls, v: str) -> str:
        """Validate LaTeX font size."""
        valid_sizes = {"10pt", "11pt", "12pt", "14pt", "17pt", "20pt"}

        size_lower = v.lower().strip()
        if size_lower not in valid_sizes:
            raise ValueError(f"Invalid font size '{v}'. Must be one of {valid_sizes}")

        return size_lower

    class Config:
        # Allow Path objects and other complex types
        arbitrary_types_allowed = True
        # Defer validation of forward references
        defer_build = True

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
        return self.model_copy(update=updates)
