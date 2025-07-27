"""Models for nested content within adventures and books."""

from typing import Any

from pydantic import BaseModel, Field

from .content import BaseContent, Source


class AdventureSection(BaseContent):
    """Represents a section within an adventure."""

    section_type: str = Field(default="section", description="Type of section")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Section ID")
    parent_name: str = Field(..., description="Parent adventure/chapter name")
    entries: list[Any] = Field(default_factory=list, description="Section content")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"adventuresection:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class AdventureTable(BaseContent):
    """Represents a table within an adventure."""

    caption: str | None = Field(None, description="Table caption")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Table ID")
    parent_name: str = Field(..., description="Parent adventure/section name")
    col_labels: list[str] = Field(default_factory=list, description="Column headers")
    rows: list[list[str]] = Field(default_factory=list, description="Table data")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return (
            f"adventuretable:{self.name}:{self.source.abbreviation}:{self.parent_name}"
        )


class AdventureInset(BaseContent):
    """Represents an inset/sidebar within an adventure."""

    inset_type: str = Field(default="inset", description="Type of inset")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Inset ID")
    parent_name: str = Field(..., description="Parent adventure/section name")
    entries: list[Any] = Field(default_factory=list, description="Inset content")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return (
            f"adventureinset:{self.name}:{self.source.abbreviation}:{self.parent_name}"
        )


class BookSection(BaseContent):
    """Represents a section within a book."""

    section_type: str = Field(default="section", description="Type of section")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Section ID")
    parent_name: str = Field(..., description="Parent book/chapter name")
    entries: list[Any] = Field(default_factory=list, description="Section content")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"booksection:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class VariantRule(BaseContent):
    """Represents a variant rule within a book."""

    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Rule ID")
    parent_name: str = Field(..., description="Parent book/section name")
    entries: list[Any] = Field(default_factory=list, description="Rule content")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"variantrule:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class BookTable(BaseContent):
    """Represents a table within a book."""

    caption: str | None = Field(None, description="Table caption")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Table ID")
    parent_name: str = Field(..., description="Parent book/section name")
    col_labels: list[str] = Field(default_factory=list, description="Column headers")
    rows: list[list[str]] = Field(default_factory=list, description="Table data")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"booktable:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class BookInset(BaseContent):
    """Represents an inset/sidebar within a book."""

    inset_type: str = Field(default="inset", description="Type of inset")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Inset ID")
    parent_name: str = Field(..., description="Parent book/section name")
    entries: list[Any] = Field(default_factory=list, description="Inset content")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"bookinset:{self.name}:{self.source.abbreviation}:{self.parent_name}"
