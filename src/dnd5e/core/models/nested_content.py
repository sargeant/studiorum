"""Models for nested content within adventures and books."""

from typing import Any

from pydantic import Field, field_validator

from .content import BaseContent


def roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer."""
    roman_map = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
        "IV": 4,
        "IX": 9,
        "XL": 40,
        "XC": 90,
        "CD": 400,
        "CM": 900,
    }

    roman = roman.upper()
    result = 0
    i = 0

    # Process two-character combinations first
    while i < len(roman):
        if i + 1 < len(roman) and roman[i : i + 2] in roman_map:
            result += roman_map[roman[i : i + 2]]
            i += 2
        elif roman[i] in roman_map:
            result += roman_map[roman[i]]
            i += 1
        else:
            # Invalid Roman numeral, return 0
            return 0

    return result


class Section(BaseContent):
    """Represents a section within a book or adventure."""

    section_type: str = Field(default="section", description="Type of section")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Section ID")
    parent_name: str = Field(..., description="Parent document/chapter name")
    entries: list[Any] = Field(default_factory=list, description="Section content")
    document_type: str = Field(..., description="Document type")

    @field_validator("page", mode="before")
    @classmethod
    def parse_page(cls, v: Any) -> int | None:
        """Parse page numbers, including Roman numerals."""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Try to convert Roman numeral to integer
            try:
                return roman_to_int(v)
            except Exception:
                # If Roman numeral conversion fails, try direct int conversion
                try:
                    return int(v)
                except ValueError:
                    # If all fails, return None
                    return None
        return None

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"{self.document_type}section:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class Table(BaseContent):
    """Represents a table within a book or adventure."""

    caption: str | None = Field(None, description="Table caption")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Table ID")
    parent_name: str = Field(..., description="Parent document/section name")
    col_labels: list[str] = Field(default_factory=list, description="Column headers")
    rows: list[list[str]] = Field(default_factory=list, description="Table data")
    document_type: str = Field(..., description="Document type")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"{self.document_type}table:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class Inset(BaseContent):
    """Represents an inset/sidebar within a book or adventure."""

    inset_type: str = Field(default="inset", description="Type of inset")
    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Inset ID")
    parent_name: str = Field(..., description="Parent document/section name")
    entries: list[Any] = Field(default_factory=list, description="Inset content")
    document_type: str = Field(..., description="Document type")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"{self.document_type}inset:{self.name}:{self.source.abbreviation}:{self.parent_name}"


class VariantRule(BaseContent):
    """Represents a variant rule within a book."""

    page: int | None = Field(None, description="Page number")
    id: str | None = Field(None, description="Rule ID")
    parent_name: str | None = Field(None, description="Parent book/section name")
    entries: list[Any] = Field(default_factory=list, description="Rule content")

    def get_hash_key(self) -> str:
        """Generate a unique hash key for indexing."""
        return f"variantrule:{self.name}:{self.source.abbreviation}:{self.parent_name}"
