"""Shared chapter model for books and adventures."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# 5etools' ordinal types (Parser.bookOrdinalToAbv)
OrdinalType = Literal["part", "chapter", "episode", "appendix", "level", "section"]

NUMBERED_KINDS: tuple[OrdinalType, ...] = ("chapter", "part", "episode", "level")


class ChapterType(str, Enum):
    """How the document assembly opens a chapter."""

    INTRODUCTION = "introduction"  # Unnumbered, in the table of contents
    CHAPTER = "chapter"
    APPENDIX = "appendix"
    PART = "part"


class Ordinal(BaseModel):
    """A chapter's place in the book: Chapter 3, Appendix B, Part 1."""

    type: OrdinalType
    identifier: int | str | None = None


class Chapter(BaseModel):
    """A top-level section of a book or adventure.

    ``name`` is the short name from the book's table of contents, ``ordinal``
    5etools' numbering (None for introductions and credits) and ``id`` the
    section's id in its text.
    """

    name: str = Field(..., description="Chapter name")
    id: str | None = Field(None, description="The section's 5etools id")
    ordinal: Ordinal | None = Field(None, description="Chapter numbering")
    headers: list[str | dict[str, Any]] | None = Field(
        None, description="Section headers"
    )
    entries: list[Any] = Field(default_factory=list, description="Chapter content")

    @property
    def label(self) -> str:
        """5etools' label for the chapter, such as "Chapter 3" or "Appendix"."""
        if self.ordinal is None:
            return ""
        word = self.ordinal.type.title()
        if self.ordinal.identifier is None:
            return word
        return f"{word} {self.ordinal.identifier}"

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> Any:
        """Parse headers from various formats."""
        if not v:
            return v

        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # Extract header text from dict format
                    if "header" in item:
                        result.append(item["header"])
                    else:
                        result.append(str(item))
                else:
                    result.append(str(item))
            return result
        return v
