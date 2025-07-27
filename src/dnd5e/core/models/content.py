"""Base content models for all D&D content types."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentType(str, Enum):
    """Enumeration of supported D&D content types."""

    ADVENTURE = "adventure"
    BOOK = "book"
    SPELL = "spell"
    CREATURE = "creature"
    ITEM = "item"
    CLASS = "class"
    CLASS_FEATURE = "classFeature"
    SUBCLASS_FEATURE = "subclassFeature"
    BACKGROUND = "background"
    FEAT = "feat"
    RACE = "race"
    SUPPLEMENT = "supplement"
    SPELL_FLUFF = "spellFluff"
    CREATURE_FLUFF = "creatureFluff"
    ITEM_FLUFF = "itemFluff"

    # Adventure nested content types
    ADVENTURE_SECTION = "adventureSection"
    ADVENTURE_TABLE = "adventureTable"
    ADVENTURE_NPC = "adventureNpc"
    ADVENTURE_LOCATION = "adventureLocation"
    ADVENTURE_INSET = "adventureInset"

    # Book nested content types
    BOOK_SECTION = "bookSection"
    VARIANT_RULE = "variantRule"
    BOOK_TABLE = "bookTable"
    BOOK_INSET = "bookInset"

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
        # Use the registry-based resolver to avoid circular imports
        from ..content_type_resolver import get_content_type_resolver

        resolver = get_content_type_resolver()
        return resolver.resolve_type(content)


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
