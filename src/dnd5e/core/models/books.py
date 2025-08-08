"""Book data models."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from ..registry import content_type
from .chapter import Chapter
from .content import BaseContent

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer


class BookMetadata(BaseModel):
    """Book metadata and publishing information."""

    id: str | None = Field(None, description="Book ID")
    published: str | None = Field(None, description="Publication date")
    author: list[str] | None = Field(None, description="Book authors")
    contents: list[dict[str, Any]] | None = Field(None, description="Table of contents")
    cover: dict[str, Any] | None = Field(None, description="Cover image")

    @field_validator("author", mode="before")
    @classmethod
    def parse_author(cls, v: Any) -> list[str] | None:
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

    def get_formatted_date(self) -> str:
        """Get formatted publication date."""
        if not self.published:
            return ""
        return self.published


@content_type(
    enum_value="book",
    file_patterns=["book", "books"],
    statblock_tags=["book"],
    loader_type="json",
)
class Book(BaseContent):
    """Represents a D&D rulebook or supplement."""

    id: str | None = Field(None, description="Book identifier")
    contents: list[Chapter] = Field(default_factory=list, description="Book chapters")
    metadata: BookMetadata | None = Field(None, description="Book metadata")

    # Book-specific fields
    published: str | None = Field(None, description="Publication date")
    author: list[str] | None = Field(None, description="Authors")
    cover: dict[str, Any] | None = Field(None, description="Cover image")

    @field_validator("author", mode="before")
    @classmethod
    def parse_author(cls, v: Any) -> list[str] | None:
        """Handle both string and list formats for author field."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]  # Convert string to single-item list
        if isinstance(v, list):
            return v
        return [str(v)]  # Convert other types to string then list

    @model_validator(mode="before")
    @classmethod
    def transform_5etools_format(cls, data: Any) -> Any:
        """Transform 5etools book format to standard Book format."""
        if isinstance(data, dict) and "data" in data and "contents" not in data:
            # Transform 5etools format: move "data" array to "contents" field
            data_array = data.get("data", [])
            if isinstance(data_array, list):
                # Create a copy of the data and transform it
                transformed = dict(data)

                # Process each item in data_array to ensure required fields
                processed_contents = []
                for i, item in enumerate(data_array):
                    if isinstance(item, dict):
                        # Ensure each chapter/section has a name field
                        if "name" not in item:
                            item = dict(item)  # Make a copy
                            # Generate a default name based on type or position
                            if item.get("type") == "section":
                                item["name"] = f"Section {i + 1}"
                            else:
                                item["name"] = f"Chapter {i + 1}"
                        processed_contents.append(item)
                    else:
                        # Non-dict items need to be wrapped
                        processed_contents.append(
                            {
                                "name": f"Chapter {i + 1}",
                                "type": "chapter",
                                "entries": [item] if item else [],
                            }
                        )

                transformed["contents"] = processed_contents
                # Keep the original data field for reference if needed
                return transformed
        return data

    def model_post_init(self, __context: Any) -> None:
        """Post-process parsed data."""
        # Create metadata from individual fields if not present
        if not self.metadata and any(
            [self.id, self.published, self.author, self.cover]
        ):
            self.metadata = BookMetadata(
                id=self.id,
                published=self.published,
                author=self.author,
                contents=None,
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
            return BookMetadata(
                id=None,
                published=None,
                author=self.author,
                contents=None,
                cover=None,
            ).get_authors_text()
        return ""

    def has_content(self) -> bool:
        """Check if book has loaded content vs metadata stub.

        Returns:
            True if book has actual content entries, False if metadata-only
        """
        return any(len(chapter.entries) > 0 for chapter in self.contents)

    def is_metadata_only(self) -> bool:
        """Check if book is a metadata-only stub without content.

        Returns:
            True if book appears to be metadata-only, False if has content
        """
        return not self.has_content()

    def get_content_file_path(self) -> str | None:
        """Get expected content file path for this book.

        Returns:
            Expected content file name or None if ID missing
        """
        if not self.id:
            return None
        return f"book-{self.id.lower()}.json"

    def get_content_summary(self) -> dict[str, Any]:
        """Get summary of content loading status for debugging.

        Returns:
            Dictionary with content status information
        """
        total_chapters = len(self.contents)
        chapters_with_content = sum(1 for chapter in self.contents if chapter.entries)
        total_entries = sum(len(chapter.entries) for chapter in self.contents)

        return {
            "book_id": self.id,
            "book_name": self.name,
            "total_chapters": total_chapters,
            "chapters_with_content": chapters_with_content,
            "total_entries": total_entries,
            "has_content": self.has_content(),
            "is_metadata_only": self.is_metadata_only(),
            "expected_content_file": self.get_content_file_path(),
        }

    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Return nested content for deep indexing.

        Extracts indexable content from book chapters including:
        - Sections
        - Variant rules
        - Tables
        - Insets/sidebars

        Args:
            omnidexer: The omnidexer instance doing the indexing

        Returns:
            List of nested content objects for indexing
        """
        from ..parsers.entry_parser import EntryParser

        nested_content = []

        # Process each chapter
        for chapter in self.contents:
            if not chapter.entries:
                continue

            # Create parser for this chapter
            chapter_name = chapter.name
            if chapter.get_chapter_number():
                chapter_name = f"{chapter.get_chapter_number()}: {chapter.name}"

            parser = EntryParser(
                source=self.source, parent_name=f"{self.name} > {chapter_name}"
            )

            # Parse chapter entries
            try:
                for content_item in parser.parse_entries(chapter.entries, "book"):
                    nested_content.append(content_item)
            except Exception as e:
                # Log error but continue processing other chapters
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Error parsing entries in {self.name} chapter '{chapter.name}': {e}"
                )
                continue

        return nested_content
