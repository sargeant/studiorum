"""Shared chapter model for books and adventures."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class Chapter(BaseModel):
    """Represents a chapter within a book or adventure."""

    name: str = Field(..., description="Chapter name")
    ordinal: dict[str, Any] | None = Field(None, description="Chapter numbering")
    headers: list[str | dict[str, Any]] | None = Field(
        None, description="Section headers"
    )
    entries: list[Any] = Field(default_factory=list, description="Chapter content")

    def get_chapter_number(self) -> str:
        """Get formatted chapter number."""
        if self.ordinal:
            if isinstance(self.ordinal, dict):
                ordinal_type = self.ordinal.get("type", "chapter")
                identifier = self.ordinal.get("identifier", "")
                if ordinal_type == "chapter" and identifier:
                    return f"Chapter {identifier}"
                elif ordinal_type == "part" and identifier:
                    return f"Part {identifier}"
                elif ordinal_type == "appendix" and identifier:
                    return f"Appendix {identifier}"
                elif identifier:
                    return str(identifier)
            return str(self.ordinal)
        return ""

    def get_clean_title(self, strip_manual_numbering: bool = False) -> str:
        """Get chapter title, optionally stripped of manual numbering.

        Args:
            strip_manual_numbering: If True, remove "Chapter X:" prefixes

        Returns:
            Clean chapter title for LaTeX native numbering
        """
        title = self.name

        if strip_manual_numbering:
            # Remove common manual numbering patterns
            import re

            # Match "Chapter X:" or "Part X:" at the start
            title = re.sub(r"^(Chapter|Part)\s+\d+:\s*", "", title)
            # Match "Appendix X:" at the start
            title = re.sub(r"^Appendix\s+[A-Z]:\s*", "", title)

        return title

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

    def get_formatted_headers(self) -> list[str]:
        """Get formatted header texts."""
        if not self.headers:
            return []

        result = []
        for header in self.headers:
            if isinstance(header, str):
                result.append(header)
            elif isinstance(header, dict):
                if "header" in header:
                    result.append(header["header"])
                else:
                    result.append(str(header))
            else:
                result.append(str(header))
        return result
