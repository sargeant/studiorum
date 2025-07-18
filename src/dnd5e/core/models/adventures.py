"""Adventure data models."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent


class AdventureChapter(BaseModel):
    """Represents a chapter within an adventure."""

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
                elif ordinal_type == "appendix" and identifier:
                    return f"Appendix {identifier}"
                elif identifier:
                    return str(identifier)
            return str(self.ordinal)
        return ""

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v):
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


class AdventureMetadata(BaseModel):
    """Adventure metadata and publishing information."""

    id: str | None = Field(None, description="Adventure ID")
    published: str | None = Field(None, description="Publication date")
    storyline: str | None = Field(None, description="Storyline/campaign")
    level: dict[str, Any] | None = Field(None, description="Level range")
    group: str | None = Field(None, description="Adventure group")
    cover: dict[str, Any] | None = Field(None, description="Cover image")

    def get_level_range(self) -> str:
        """Get formatted level range."""
        if not self.level:
            return ""

        if isinstance(self.level, dict):
            start = self.level.get("start", 1)
            end = self.level.get("end", start)
            if start == end:
                return f"Level {start}"
            return f"Levels {start}-{end}"

        return str(self.level)


class Adventure(BaseContent):
    """Represents a D&D adventure."""

    id: str | None = Field(None, description="Adventure identifier")
    contents: list[AdventureChapter] = Field(
        default_factory=list, description="Adventure chapters"
    )
    metadata: AdventureMetadata | None = Field(None, description="Adventure metadata")

    # Adventure-specific fields
    published: str | None = Field(None, description="Publication date")
    storyline: str | None = Field(None, description="Storyline")
    level: dict[str, Any] | None = Field(None, description="Level range")
    group: str | None = Field(None, description="Adventure group")
    cover: dict[str, Any] | None = Field(None, description="Cover image")

    def model_post_init(self, __context) -> None:
        """Post-process parsed data."""
        # Create metadata from individual fields if not present
        if not self.metadata and any(
            [
                self.id,
                self.published,
                self.storyline,
                self.level,
                self.group,
                self.cover,
            ]
        ):
            self.metadata = AdventureMetadata(
                id=self.id,
                published=self.published,
                storyline=self.storyline,
                level=self.level,
                group=self.group,
                cover=self.cover,
            )

    def get_chapter_count(self) -> int:
        """Get number of chapters."""
        return len(self.contents)

    def get_level_range(self) -> str:
        """Get formatted level range."""
        if self.metadata:
            return self.metadata.get_level_range()
        elif self.level:
            return AdventureMetadata(level=self.level).get_level_range()
        return ""

    def get_storyline_text(self) -> str:
        """Get storyline text."""
        if self.metadata and self.metadata.storyline:
            return self.metadata.storyline
        return self.storyline or ""
