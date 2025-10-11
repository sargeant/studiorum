"""Adventure data models."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from ..registry import content_type
from .chapter import Chapter
from .content import BaseContent

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer


class AdventureMetadata(BaseModel):
    """Adventure metadata and publishing information."""

    id: str | None = Field(None, description="Adventure ID")
    published: str | None = Field(None, description="Publication date")
    storyline: str | None = Field(None, description="Storyline/campaign")
    level: dict[str, Any] | None = Field(None, description="Level range")
    group: str | None = Field(None, description="Adventure group")
    cover: dict[str, Any] | None = Field(None, description="Cover image")
    custom_fields: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )

    def get_level_range(self) -> str:
        """Get formatted level range text for display.

        Converts level range dictionary to human-readable format:
        - {"start": 1, "end": 5} → "Levels 1-5"
        - {"start": 3, "end": 3} → "Level 3"
        - None or missing level → ""
        - Non-dict values → string representation

        Returns:
            Formatted level range string

        Example:
            >>> metadata = AdventureMetadata(level={"start": 1, "end": 10})
            >>> metadata.get_level_range()
            "Levels 1-10"
        """
        if not self.level:
            return ""

        if isinstance(self.level, dict):
            start = self.level.get("start", 1)
            end = self.level.get("end", start)
            if start == end:
                return f"Level {start}"
            return f"Levels {start}-{end}"

        return str(self.level)


@content_type(
    enum_value="adventure",
    file_patterns=["adventure", "adventures"],
    statblock_tags=["adventure"],
    loader_type="json",
)
class Adventure(BaseContent):
    """Represents a 5e adventure with unified metadata and content structure.

    This model handles adventures from the 5etools dual-file architecture:
    - Metadata files (adventures.json) provide structure, names, and publishing info
    - Content files (adventure-\\*.json) provide actual entry data for chapters
    - ContentMerger combines these at resolution time into unified structures

    The Adventure model supports three input formats:
    1. **Unified structure** (from ContentMerger): Has both metadata fields and populated contents
    2. **Metadata-only structure**: Has metadata fields but empty/minimal contents
    3. **Content-only structure** (legacy): Has "data" field that gets transformed to contents

    Key Features:
    - Automatic metadata field validation with proper error messages
    - Content status methods to detect loaded vs metadata-only adventures
    - Backward compatibility with legacy 5etools formats
    - Rich metadata handling with AdventureMetadata objects

    Examples:
        >>> # Create from unified metadata+content structure (typical use)
        >>> adventure = Adventure.model_validate({
        ...     "name": "Curse of Strahd",
        ...     "id": "CoS",
        ...     "source": {"abbreviation": "CoS"},
        ...     "published": "2016-03-15",
        ...     "storyline": "Ravenloft",
        ...     "contents": [
        ...         {"name": "Chapter 1", "entries": ["Adventure content..."]}
        ...     ]
        ... })
        >>> adventure.has_content()  # True
        >>> adventure.get_content_file_path()  # "adventure-cos.json"

        >>> # Create from metadata-only structure
        >>> metadata_adventure = Adventure.model_validate({
        ...     "name": "Curse of Strahd",
        ...     "id": "CoS",
        ...     "source": {"abbreviation": "CoS"},
        ...     "contents": [{"name": "Chapter 1", "entries": []}]
        ... })
        >>> metadata_adventure.is_metadata_only()  # True
    """

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

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str | None) -> str | None:
        """Validate adventure ID format."""
        if v is not None and not isinstance(v, str):
            raise ValueError("Adventure ID must be a string")
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Adventure ID cannot be empty")
        return v.strip() if v else None

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate level range structure."""
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("Level must be a dictionary")

        # Validate level range values
        if "start" in v:
            start = v["start"]
            if not isinstance(start, int) or start < 1 or start > 20:
                raise ValueError("Level start must be an integer between 1 and 20")

        if "end" in v:
            end = v["end"]
            if not isinstance(end, int) or end < 1 or end > 20:
                raise ValueError("Level end must be an integer between 1 and 20")

        # Validate start <= end if both present
        if "start" in v and "end" in v and v["start"] > v["end"]:
            raise ValueError("Level start cannot be greater than level end")

        return v

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: Any = None,
        from_attributes: bool | None = None,
        context: Any = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "Adventure":
        """Custom validation to handle unified metadata+content structure.

        This validator handles multiple input formats from the 5etools architecture:

        1. **Unified structures** (from ContentMerger):
           - Have both metadata fields (id, source, published, etc.)
           - And populated contents arrays with actual entry data
           - No transformation needed, passed through directly

        2. **Legacy content-only files** (backward compatibility):
           - Have "data" field with section arrays
           - Get transformed to contents structure
           - Missing metadata fields get default values

        3. **Metadata-only structures**:
           - Have metadata fields but empty/stub contents
           - Used when content hasn't been loaded yet
           - Passed through with validation

        Args:
            obj: Input data (typically dict from JSON)
            strict: Enable strict validation mode
            from_attributes: Parse from object attributes
            context: Validation context
            by_alias: Use field aliases
            by_name: Use field names

        Returns:
            Validated Adventure instance

        Raises:
            ValidationError: If validation fails or required fields missing
        """
        if isinstance(obj, dict):
            # Make a copy to avoid modifying the original
            obj = dict(obj)

            # Handle legacy content-only files ("data" field without "contents")
            # This maintains backward compatibility for direct file loading
            if "data" in obj and not obj.get("contents"):
                data_sections = obj["data"]
                if isinstance(data_sections, list):
                    contents = []
                    for section in data_sections:
                        if (
                            isinstance(section, dict)
                            and section.get("type") == "section"
                        ):
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

                    obj["contents"] = contents
                    del obj["data"]

            # Ensure required fields are present
            if "name" not in obj:
                obj["name"] = "Unknown Adventure"
            if "source" not in obj or obj["source"] is None:
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

        # Validate metadata consistency if both individual fields and metadata exist
        if self.metadata:
            # Ensure individual fields are in sync with metadata
            if self.id is None and self.metadata.id:
                self.id = self.metadata.id
            if self.published is None and self.metadata.published:
                self.published = self.metadata.published

    @model_validator(mode="after")
    def validate_adventure_structure(self) -> "Adventure":
        """Validate overall adventure structure and metadata consistency."""
        from studiorum.core.logging import get_logger

        logger = get_logger(__name__)

        # Validate metadata consistency
        if self.metadata:
            # Check for conflicting ID values
            if self.id and self.metadata.id and self.id != self.metadata.id:
                logger.warning(
                    f"Adventure ID mismatch: field={self.id}, metadata={self.metadata.id}. Using field value."
                )

        # Validate that adventure has either content or proper metadata
        if not self.has_content() and not self._has_meaningful_metadata():
            logger.warning(
                f"Adventure '{self.name}' has no content and minimal metadata. "
                f"This may indicate incomplete data loading."
            )

        return self

    def _has_meaningful_metadata(self) -> bool:
        """Check if adventure has meaningful metadata beyond just name and source."""
        return bool(
            self.id
            or self.published
            or self.storyline
            or self.level
            or self.group
            or self.cover
            or (
                self.metadata
                and any(
                    [
                        self.metadata.id,
                        self.metadata.published,
                        self.metadata.storyline,
                        self.metadata.level,
                        self.metadata.group,
                        self.metadata.cover,
                    ]
                )
            )
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

    def has_content(self) -> bool:
        """Check if adventure has loaded content.

        Returns:
            True if adventure has chapters with actual entries, False otherwise
        """
        return any(chapter.entries for chapter in self.contents)

    def is_metadata_only(self) -> bool:
        """Check if adventure contains only metadata without content.

        Returns:
            True if adventure has no content entries, False otherwise
        """
        return not self.has_content()

    def get_content_file_path(self) -> str | None:
        """Get expected content file path for this adventure.

        Returns:
            Expected content file name (e.g., "adventure-cos.json") or None if no ID
        """
        if not self.id:
            return None

        # Normalize ID to filename pattern: "CoS" -> "adventure-cos.json"
        normalized_id = self.id.lower().replace("-", "")
        return f"adventure-{normalized_id}.json"

    def get_content_summary(self) -> dict[str, Any]:
        """Get summary of content loading status for debugging.

        Returns:
            Dictionary with content status information
        """
        total_chapters = len(self.contents)
        chapters_with_content = sum(1 for chapter in self.contents if chapter.entries)
        total_entries = sum(len(chapter.entries) for chapter in self.contents)

        return {
            "adventure_id": self.id,
            "adventure_name": self.name,
            "total_chapters": total_chapters,
            "chapters_with_content": chapters_with_content,
            "total_entries": total_entries,
            "has_content": self.has_content(),
            "is_metadata_only": self.is_metadata_only(),
            "expected_content_file": self.get_content_file_path(),
        }

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
                from studiorum.core.logging import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    f"Error parsing entries in {self.name} chapter '{chapter.name}': {e}"
                )
                continue

        return nested_content
