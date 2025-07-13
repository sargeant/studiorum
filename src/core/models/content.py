"""Base content models for all D&D content types."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentType(str, Enum):
    """Enumeration of supported D&D content types."""

    ADVENTURE = "adventure"
    BOOK = "book"
    SPELL = "spell"
    CREATURE = "creature"
    ITEM = "item"
    CLASS = "class"
    BACKGROUND = "background"
    FEAT = "feat"
    RACE = "race"
    SUPPLEMENT = "supplement"
    SPELL_FLUFF = "spellFluff"
    CREATURE_FLUFF = "creatureFluff"
    ITEM_FLUFF = "itemFluff"

    @classmethod
    def from_content(cls, content: "BaseContent") -> "ContentType":
        """Determine content type from content object.

        Args:
            content: Content object to analyze

        Returns:
            ContentType corresponding to the content

        Raises:
            ValueError: If content type cannot be determined
        """
        from ..models.adventures import Adventure
        from ..models.backgrounds import Background
        from ..models.books import Book
        from ..models.classes import Class
        from ..models.creatures import Creature
        from ..models.feats import Feat
        from ..models.items import Item
        from ..models.races import Race
        from ..models.spells import Spell

        if isinstance(content, Spell):
            return cls.SPELL
        elif isinstance(content, Creature):
            return cls.CREATURE
        elif isinstance(content, Item):
            return cls.ITEM
        elif isinstance(content, Adventure):
            return cls.ADVENTURE
        elif isinstance(content, Book):
            return cls.BOOK
        elif isinstance(content, Feat):
            return cls.FEAT
        elif isinstance(content, Race):
            return cls.RACE
        elif isinstance(content, Background):
            return cls.BACKGROUND
        elif isinstance(content, Class):
            return cls.CLASS
        else:
            # Try to infer from class name
            class_name = content.__class__.__name__.lower()
            for content_type in cls:
                if content_type.value in class_name:
                    return content_type

            # If it's the base BaseContent class, return a default
            if content.__class__.__name__ == "BaseContent":
                return cls.SUPPLEMENT  # Default fallback for unknown content

            raise ValueError(
                f"Cannot determine content type for {content.__class__.__name__}"
            )


class Source(BaseModel):
    """Represents a D&D source book reference."""

    abbreviation: str = Field(
        ..., description="Source book abbreviation (e.g., 'PHB', 'MM')"
    )
    name: Optional[str] = Field(None, description="Full source book name")
    page: Optional[int] = Field(None, description="Page number reference")
    url: Optional[str] = Field(None, description="URL reference")

    def model_post_init(self, __context):
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
    def parse_source(cls, v):
        """Handle both string and dict source formats for liberal parsing."""
        if isinstance(v, str):
            return {"abbreviation": v, "name": v}
        elif isinstance(v, dict):
            return v
        return v

    def __str__(self) -> str:
        return f"{self.name} ({self.source.abbreviation})"

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return (
            f"{self.__class__.__name__.lower()}:{self.name}:{self.source.abbreviation}"
        )
