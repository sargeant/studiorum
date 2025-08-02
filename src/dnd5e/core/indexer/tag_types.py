"""Intermediate representation types for tag resolution."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..models.content import BaseContent, ContentType


class FormatType(str, Enum):
    """Types of formatting that can be applied to text."""

    BOLD = "bold"
    ITALIC = "italic"
    MONOSPACE = "monospace"
    EMPHASIS = "emphasis"


class ContentReference(BaseModel):
    """Represents a resolved reference to game content.

    This is the result of semantic resolution - finding what a tag references
    without any formatting applied. The resolved_content is None if the
    reference couldn't be found.

    Examples:
        {@creature Strahd} -> ContentReference(
            content_type=ContentType.CREATURE,
            name="Strahd",
            source=None,
            resolved_content=<Creature object if found>
        )
    """

    content_type: ContentType = Field(description="Type of content being referenced")
    name: str = Field(min_length=1, description="Name of the content")
    source: str | None = Field(None, description="Source abbreviation for the content")
    display_text: str | None = Field(None, description="Custom display text override")
    page: str | None = Field(None, description="Page reference if available")
    resolved_content: Any = Field(
        None, description="The actual resolved content object"
    )  # TODO: Replace with BaseContent | None once migrated

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize content name."""
        return v.strip()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str | None) -> str | None:
        """Validate source abbreviation format."""
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned if cleaned else None

    @field_validator("display_text")
    @classmethod
    def validate_display_text(cls, v: str | None) -> str | None:
        """Validate display text override."""
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned if cleaned else None

    @property
    def is_resolved(self) -> bool:
        """True if the content reference was successfully resolved."""
        return self.resolved_content is not None

    @property
    def effective_name(self) -> str:
        """The name to display - uses display_text if provided, otherwise name."""
        return self.display_text or self.name

    def __str__(self) -> str:
        if self.resolved_content:
            return (
                f"{self.effective_name} ({self.resolved_content.source.abbreviation})"
            )
        return self.effective_name

    class Config:
        # Allow content objects (they should be Pydantic models too)
        arbitrary_types_allowed = True
        # Make instances immutable like the original frozen dataclass
        frozen = True


class FormattingNode(BaseModel):
    """Represents text with formatting instructions.

    This is used for pure formatting tags like {@b text} or {@i text}
    that don't reference game content.

    Examples:
        {@b strong text} -> FormattingNode(
            format_type=FormatType.BOLD,
            content="strong text"
        )
    """

    format_type: FormatType = Field(description="Type of formatting to apply")
    content: str = Field(min_length=1, description="Text content to format")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and normalize content text."""
        return v.strip()

    def __str__(self) -> str:
        return f"{self.format_type.value}({self.content})"

    class Config:
        # Make instances immutable like the original frozen dataclass
        frozen = True


class SpecialTag(BaseModel):
    """Represents special tags that need custom handling.

    This covers tags like {@dice 1d6}, {@hit +5}, {@dc 15}, etc.
    that have specific semantic meaning but aren't content references
    or simple formatting.

    Examples:
        {@dice 1d6} -> SpecialTag(
            tag_type="dice",
            value="1d6"
        )
        {@hit +5} -> SpecialTag(
            tag_type="hit",
            value="+5"
        )
    """

    tag_type: str = Field(min_length=1, description="Type of special tag")
    value: str = Field(min_length=1, description="Value/content of the tag")
    display_text: str | None = Field(None, description="Custom display text override")
    metadata: dict[str, Any] | None = Field(
        None, description="Additional metadata for the tag"
    )

    @field_validator("tag_type")
    @classmethod
    def validate_tag_type(cls, v: str) -> str:
        """Validate and normalize tag type."""
        normalized = v.strip().lower()
        if not normalized:
            raise ValueError("Tag type cannot be empty")
        return normalized

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Validate tag value."""
        return v.strip()

    @field_validator("display_text")
    @classmethod
    def validate_display_text(cls, v: str | None) -> str | None:
        """Validate display text override."""
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned if cleaned else None

    @property
    def effective_value(self) -> str:
        """The value to display - uses display_text if provided, otherwise value."""
        return self.display_text or self.value

    def __str__(self) -> str:
        return f"{self.tag_type}({self.effective_value})"

    class Config:
        # Make instances immutable like the original frozen dataclass
        frozen = True


# Union type for all possible tag resolution results
TagResolutionResult = ContentReference | FormattingNode | SpecialTag | str


class TagContext(BaseModel):
    """Context information available during tag resolution.

    This provides access to the omnidexer and other contextual information
    that tag handlers might need.
    """

    omnidexer: Any = Field(
        description="Content indexer for tag resolution"
    )  # TODO: Replace with Omnidexer once it's migrated to Pydantic

    def find_content(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> BaseContent | None:
        """Find content using the omnidexer."""
        # Type: ignore the Any return from omnidexer since we know it returns BaseContent | None
        return self.omnidexer.find(content_type, name, source)  # type: ignore[no-any-return]

    class Config:
        # Allow complex types to avoid circular imports
        arbitrary_types_allowed = True
        # Make instances immutable like the original frozen dataclass
        frozen = True
