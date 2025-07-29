"""Adventure data models."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from .chapter import Chapter
from .content import BaseContent

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer


# Legacy alias for backward compatibility
AdventureChapter = Chapter


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
    contents: list[Chapter] = Field(
        default_factory=list, description="Adventure chapters"
    )
    metadata: AdventureMetadata | None = Field(None, description="Adventure metadata")

    # Adventure-specific fields
    published: str | None = Field(None, description="Publication date")
    storyline: str | None = Field(None, description="Storyline")
    level: dict[str, Any] | None = Field(None, description="Level range")
    group: str | None = Field(None, description="Adventure group")
    cover: dict[str, Any] | None = Field(None, description="Cover image")

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "Adventure":
        """Custom validation to handle 5etools data format."""
        # If this is a dict with "data" field, transform it
        if isinstance(obj, dict) and "data" in obj and not obj.get("contents"):
            data_sections = obj["data"]
            if isinstance(data_sections, list):
                contents = []
                for section in data_sections:
                    if isinstance(section, dict) and section.get("type") == "section":
                        entries = section.get("entries", [])

                        chapter = {
                            "name": section.get("name", "Unnamed Chapter"),
                            "entries": entries,
                        }
                        if "id" in section:
                            chapter["ordinal"] = {
                                "type": "section",
                                "identifier": section["id"],
                            }
                        contents.append(chapter)

                # Replace data with contents
                obj = dict(obj)  # Make a copy
                obj["contents"] = contents
                del obj["data"]  # Remove the data field

                # Add required fields if missing
                if "name" not in obj:
                    obj["name"] = "Unknown Adventure"
                if "source" not in obj:
                    obj["source"] = {"abbreviation": "UNK", "name": "Unknown Source"}

        return super().model_validate(
            obj, strict=strict, from_attributes=from_attributes, context=context
        )

    def model_post_init(self, __context: Any) -> None:
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
            return AdventureMetadata(
                id=None,
                published=None,
                storyline=None,
                level=self.level,
                group=None,
                cover=None,
            ).get_level_range()
        return ""

    def get_storyline_text(self) -> str:
        """Get storyline text."""
        if self.metadata and self.metadata.storyline:
            return self.metadata.storyline
        return self.storyline or ""

    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Return nested content for deep indexing.

        Extracts indexable content from adventure chapters including:
        - Sections
        - Tables
        - Insets/sidebars
        - Named locations
        - NPCs

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
                for content_item in parser.parse_entries(chapter.entries, "adventure"):
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
