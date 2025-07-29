"""Intermediate representation types for tag resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..models.content import BaseContent, ContentType


class FormatType(str, Enum):
    """Types of formatting that can be applied to text."""

    BOLD = "bold"
    ITALIC = "italic"
    MONOSPACE = "monospace"
    EMPHASIS = "emphasis"


@dataclass(frozen=True)
class ContentReference:
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

    content_type: ContentType
    name: str
    source: str | None = None
    display_text: str | None = None
    page: str | None = None
    resolved_content: BaseContent | None = None

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


@dataclass(frozen=True)
class FormattingNode:
    """Represents text with formatting instructions.

    This is used for pure formatting tags like {@b text} or {@i text}
    that don't reference game content.

    Examples:
        {@b strong text} -> FormattingNode(
            format_type=FormatType.BOLD,
            content="strong text"
        )
    """

    format_type: FormatType
    content: str

    def __str__(self) -> str:
        return f"{self.format_type.value}({self.content})"


@dataclass(frozen=True)
class SpecialTag:
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

    tag_type: str
    value: str
    display_text: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def effective_value(self) -> str:
        """The value to display - uses display_text if provided, otherwise value."""
        return self.display_text or self.value

    def __str__(self) -> str:
        return f"{self.tag_type}({self.effective_value})"


# Union type for all possible tag resolution results
TagResolutionResult = ContentReference | FormattingNode | SpecialTag | str


@dataclass(frozen=True)
class TagContext:
    """Context information available during tag resolution.

    This provides access to the omnidexer and other contextual information
    that tag handlers might need.
    """

    omnidexer: Any  # Avoid circular import - will be Omnidexer at runtime

    def find_content(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> BaseContent | None:
        """Find content using the omnidexer."""
        # Type: ignore the Any return from omnidexer since we know it returns BaseContent | None
        return self.omnidexer.find(content_type, name, source)  # type: ignore[no-any-return]
