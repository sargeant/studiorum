"""Base content models for all D&D content types."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentType(str, Enum):
    """Enumeration of supported D&D content types.

    This enum contains core static types and is dynamically extended by the
    registry system. Additional content types are registered via @content_type
    decorators and added to this enum at runtime.
    """

    # Core content types needed for bootstrapping
    ADVENTURE = "adventure"
    BOOK = "book"
    SPELL = "spell"
    CREATURE = "creature"
    ITEM = "item"

    @classmethod
    def from_content(cls, content: BaseContent) -> ContentType:
        """Determine content type from content object.

        Args:
            content: Content object to analyze

        Returns:
            ContentType corresponding to the content

        Raises:
            ValueError: If content type cannot be determined
        """
        # Use the registry directly to avoid circular imports
        from ..interfaces import get_content_type_registry

        registry = get_content_type_registry()
        return registry.get_type(content)


class Source(BaseModel):
    """Represents a D&D source book reference."""

    abbreviation: str = Field(
        ..., description="Source book abbreviation (e.g., 'PHB', 'MM')"
    )
    name: str | None = Field(None, description="Full source book name")
    page: int | None = Field(None, description="Page number reference")
    url: str | None = Field(None, description="URL reference")

    def model_post_init(self, __context: dict | None) -> None:
        """Set name to abbreviation if not provided."""
        if self.name is None:
            self.name = self.abbreviation

    def __str__(self) -> str:
        if self.page:
            return f"{self.abbreviation}, p. {self.page}"
        return self.abbreviation


class BaseContent(BaseModel):
    """Base class for all D&D content."""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for flexibility with 5etools data
        use_enum_values=True,  # Use enum values for serialization
    )

    name: str = Field(..., description="Content name")
    source: Source = Field(..., description="Source book reference")

    @field_validator("source", mode="before")
    @classmethod
    def parse_source(cls, v: str | dict[str, str] | Source) -> dict[str, str] | Source:
        """Handle both string and dict source formats for liberal parsing."""
        if isinstance(v, str):
            return {"abbreviation": v, "name": v}
        elif isinstance(v, dict):
            return v
        elif hasattr(v, "abbreviation") and hasattr(v, "name"):
            # If it's already a Source object, return it as-is
            return v
        # Fallback - convert to string and create dict
        return {"abbreviation": str(v), "name": str(v)}

    def __str__(self) -> str:
        return f"{self.name} ({self.source.abbreviation})"

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return (
            f"{self.__class__.__name__.lower()}:{self.name}:{self.source.abbreviation}"
        )
