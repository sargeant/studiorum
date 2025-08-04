"""Rendering context management."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from dnd5e.core.base_context import ServiceContext
from dnd5e.core.loaders.omnidexer import Omnidexer

if TYPE_CHECKING:
    from dnd5e.core.config.latex_config import LaTeXConfig
    from dnd5e.core.indexer.tag_resolver import TagResolver
    from dnd5e.core.models.document_metadata import DocumentMetadata


class RenderContext(ServiceContext):
    """Context object passed to renderers containing shared state and utilities.

    Provides access to the omnidexer for content lookups, tag resolver for
    cross-references, and various rendering options and metadata.

    Inherits from ServiceContext to provide standardized service access patterns
    while maintaining full backward compatibility with existing renderer code.
    """

    # Document metadata (structured)
    metadata: DocumentMetadata | None = Field(
        None, description="Structured document metadata"
    )

    # LaTeX configuration
    latex_config: LaTeXConfig | None = Field(
        None, description="LaTeX compilation configuration"
    )

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

    def __init__(self, **data: Any) -> None:
        """Initialize RenderContext with proper service mapping."""
        # Extract services that should go to the base ServiceContext
        services = {}
        for service_name in ["omnidexer", "tag_resolver", "config"]:
            if service_name in data:
                services[service_name] = data.pop(service_name)

        # Handle latex_config mapping - keep both latex_config and config populated
        if "latex_config" in data:
            latex_config = data["latex_config"]  # Keep for the latex_config field
            if "config" not in services:
                services["config"] = latex_config  # Also use as base config

        # Initialize the base ServiceContext
        super().__init__(**services, **data)

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


# Rebuild the model to resolve forward references after all imports are available
def _rebuild_model() -> None:
    """Rebuild RenderContext model to resolve forward references."""
    try:
        from dnd5e.core.config.latex_config import LaTeXConfig  # noqa: F401
        from dnd5e.core.indexer.tag_resolver import TagResolver  # noqa: F401
        from dnd5e.core.models.document_metadata import DocumentMetadata  # noqa: F401

        RenderContext.model_rebuild()
    except ImportError:
        # Forward references will be resolved when modules are imported
        pass


_rebuild_model()
