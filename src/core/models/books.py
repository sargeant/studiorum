"""Book data models."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .content import BaseContent


class BookChapter(BaseModel):
    """Represents a chapter within a book."""

    name: str = Field(..., description="Chapter name")
    ordinal: Optional[Dict[str, Any]] = Field(None, description="Chapter numbering")
    headers: Optional[List[Union[str, Dict[str, Any]]]] = Field(None, description="Section headers")
    entries: List[Any] = Field(default_factory=list, description="Chapter content")

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

    def get_formatted_headers(self) -> List[str]:
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


class BookMetadata(BaseModel):
    """Book metadata and publishing information."""

    id: Optional[str] = Field(None, description="Book ID")
    published: Optional[str] = Field(None, description="Publication date")
    author: Optional[List[str]] = Field(None, description="Book authors")
    contents: Optional[List[Dict[str, Any]]] = Field(
        None, description="Table of contents"
    )
    cover: Optional[Dict[str, Any]] = Field(None, description="Cover image")

    @field_validator("author", mode="before")
    @classmethod
    def parse_author(cls, v):
        """Handle both string and list formats for author field."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]  # Convert string to single-item list
        if isinstance(v, list):
            return v
        return [str(v)]  # Convert other types to string then list

    def get_authors_text(self) -> str:
        """Get formatted authors text."""
        if not self.author:
            return ""

        if len(self.author) == 1:
            return self.author[0]
        elif len(self.author) == 2:
            return f"{self.author[0]} and {self.author[1]}"
        else:
            return f"{', '.join(self.author[:-1])}, and {self.author[-1]}"


class Book(BaseContent):
    """Represents a D&D rulebook or supplement."""

    id: Optional[str] = Field(None, description="Book identifier")
    contents: List[BookChapter] = Field(
        default_factory=list, description="Book chapters"
    )
    metadata: Optional[BookMetadata] = Field(None, description="Book metadata")

    # Book-specific fields
    published: Optional[str] = Field(None, description="Publication date")
    author: Optional[List[str]] = Field(None, description="Authors")
    cover: Optional[Dict[str, Any]] = Field(None, description="Cover image")

    @field_validator("author", mode="before")
    @classmethod
    def parse_author(cls, v):
        """Handle both string and list formats for author field."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]  # Convert string to single-item list
        if isinstance(v, list):
            return v
        return [str(v)]  # Convert other types to string then list

    def model_post_init(self, __context) -> None:
        """Post-process parsed data."""
        # Create metadata from individual fields if not present
        if not self.metadata and any(
            [self.id, self.published, self.author, self.cover]
        ):
            self.metadata = BookMetadata(
                id=self.id,
                published=self.published,
                author=self.author,
                cover=self.cover,
            )

    def get_chapter_count(self) -> int:
        """Get number of chapters."""
        return len(self.contents)

    def get_authors_text(self) -> str:
        """Get formatted authors text."""
        if self.metadata:
            return self.metadata.get_authors_text()
        elif self.author:
            return BookMetadata(author=self.author).get_authors_text()
        return ""
