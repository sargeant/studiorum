"""Document metadata models for LaTeX document generation."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    """Document type enumeration for different 5e content organizations."""

    BOOK = "book"
    ARTICLE = "article"
    SUPPLEMENT = "supplement"
    REFERENCE = "reference"
    ADVENTURE = "adventure"
    HOMEBREW = "homebrew"


class DocumentStructure(str, Enum):
    """Document structure enumeration for LaTeX organization."""

    FRONTMATTER_MAINMATTER_BACKMATTER = "frontmatter_mainmatter_backmatter"
    SIMPLE = "simple"
    PARTS_CHAPTERS = "parts_chapters"
    CHAPTERS_ONLY = "chapters_only"
    SECTIONS_ONLY = "sections_only"


class SectionLevel(str, Enum):
    """LaTeX sectioning command levels."""

    PART = "part"
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"
    SUBSUBSECTION = "subsubsection"
    PARAGRAPH = "paragraph"
    SUBPARAGRAPH = "subparagraph"


class DocumentAuthor(BaseModel):
    """Author information for documents."""

    name: str = Field(..., description="Author name")
    email: str | None = Field(None, description="Author email")
    affiliation: str | None = Field(None, description="Author affiliation")

    def __str__(self) -> str:
        return self.name


class DocumentCover(BaseModel):
    """Cover image information for documents."""

    image_path: Path | None = Field(None, description="Path to cover image")
    title_overlay: bool = Field(True, description="Show title overlay on cover")
    subtitle_overlay: bool = Field(True, description="Show subtitle overlay on cover")
    author_overlay: bool = Field(True, description="Show author overlay on cover")

    @field_validator("image_path", mode="before")
    @classmethod
    def parse_image_path(cls, v: str | Path | None) -> Path | None:
        """Parse image path from string or Path."""
        if isinstance(v, str):
            return Path(v)
        return v


class DocumentMetadata(BaseModel):
    """Comprehensive document metadata for LaTeX document generation."""

    # Basic document information
    title: str = Field(..., description="Document title")
    subtitle: str | None = Field(None, description="Document subtitle")
    short_title: str | None = Field(None, description="Short title for headers")

    # Author information
    authors: list[DocumentAuthor] = Field(
        default_factory=list, description="Document authors"
    )
    editor: str | None = Field(None, description="Document editor")

    # Publication information
    date: str | datetime | None = Field(None, description="Publication date")
    version: str | None = Field(None, description="Document version")
    edition: str | None = Field(None, description="Document edition")
    publisher: str | None = Field(None, description="Publisher name")

    # Document structure
    document_type: DocumentType = Field(
        default=DocumentType.BOOK, description="Type of document"
    )
    structure: DocumentStructure = Field(
        default=DocumentStructure.FRONTMATTER_MAINMATTER_BACKMATTER,
        description="Document structure organization",
    )

    # Content options
    include_toc: bool = Field(True, description="Include table of contents")
    include_index: bool = Field(False, description="Include document index")
    include_bibliography: bool = Field(False, description="Include bibliography")
    include_glossary: bool = Field(False, description="Include glossary")

    # Visual options
    cover: DocumentCover | None = Field(None, description="Cover information")
    logo_path: Path | None = Field(None, description="Path to logo image")

    # Custom metadata
    keywords: list[str] = Field(default_factory=list, description="Document keywords")
    subject: str | None = Field(None, description="Document subject")
    description: str | None = Field(None, description="Document description")
    language: str = Field(default="en", description="Document language")

    # LaTeX-specific options
    use_parts: bool = Field(False, description="Use \\part sectioning")
    max_section_depth: int = Field(default=3, description="Maximum sectioning depth")
    numbering_depth: int = Field(default=-1, description="Section numbering depth")

    # Custom fields
    custom_fields: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v: str | datetime | None) -> datetime | None:
        """Parse date from various formats."""
        if isinstance(v, str):
            # Try to parse common date formats
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%B %d, %Y", "%Y"]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            # If parsing fails, raise an error
            raise ValueError(f"Unable to parse date: {v}")
        return v

    @field_validator("logo_path", mode="before")
    @classmethod
    def parse_logo_path(cls, v: str | Path | None) -> Path | None:
        """Parse logo path from string or Path."""
        if isinstance(v, str):
            return Path(v)
        return v

    def get_author_list(self) -> str:
        """Get formatted author list for LaTeX."""
        if not self.authors:
            return ""

        if len(self.authors) == 1:
            return str(self.authors[0])
        elif len(self.authors) == 2:
            return f"{self.authors[0]} and {self.authors[1]}"
        else:
            author_names = [str(author) for author in self.authors[:-1]]
            return f"{', '.join(author_names)}, and {self.authors[-1]}"

    def get_formatted_date(self) -> str:
        """Get formatted date for LaTeX."""
        if not self.date:
            return r"\today"

        if isinstance(self.date, datetime):
            return self.date.strftime("%B %d, %Y")

        return str(self.date)

    def get_short_title(self) -> str:
        """Get short title for headers, falling back to main title."""
        return self.short_title or self.title

    def should_use_frontmatter(self) -> bool:
        """Check if document should use frontmatter/mainmatter structure."""
        return (
            self.structure == DocumentStructure.FRONTMATTER_MAINMATTER_BACKMATTER
            and self.document_type in [DocumentType.BOOK, DocumentType.ADVENTURE]
        )

    def get_document_class_for_type(self) -> str:
        """Get appropriate LaTeX document class for document type."""
        if self.document_type == DocumentType.ARTICLE:
            return "dndarticle"
        else:
            return "dndbook"

    def get_recommended_structure(self) -> DocumentStructure:
        """Get recommended structure for document type."""
        structure_mapping = {
            DocumentType.BOOK: DocumentStructure.FRONTMATTER_MAINMATTER_BACKMATTER,
            DocumentType.ADVENTURE: DocumentStructure.FRONTMATTER_MAINMATTER_BACKMATTER,
            DocumentType.SUPPLEMENT: DocumentStructure.CHAPTERS_ONLY,
            DocumentType.REFERENCE: DocumentStructure.SECTIONS_ONLY,
            DocumentType.ARTICLE: DocumentStructure.SIMPLE,
            DocumentType.HOMEBREW: DocumentStructure.CHAPTERS_ONLY,
        }
        return structure_mapping.get(self.document_type, DocumentStructure.SIMPLE)

    def get_max_section_level(self) -> SectionLevel:
        """Get maximum section level for document type."""
        if self.document_type == DocumentType.ARTICLE:
            return SectionLevel.SECTION
        elif self.use_parts:
            return SectionLevel.PART
        else:
            return SectionLevel.CHAPTER


class ContentSection(BaseModel):
    """Represents a section of content in a structured document."""

    title: str = Field(..., description="Section title")
    level: SectionLevel = Field(..., description="Section level")
    numbered: bool = Field(True, description="Include section in numbering")
    label: str | None = Field(None, description="LaTeX label for cross-references")

    # Content organization
    content_items: list[Any] = Field(
        default_factory=list, description="Content items in section"
    )
    subsections: list["ContentSection"] = Field(
        default_factory=list, description="Subsections"
    )

    # Rendering options
    page_break_before: bool = Field(
        False, description="Insert page break before section"
    )
    page_break_after: bool = Field(False, description="Insert page break after section")
    two_column: bool | None = Field(
        None, description="Override column layout for section"
    )

    def get_latex_command(self) -> str:
        """Get LaTeX sectioning command for this section."""
        command_map = {
            SectionLevel.PART: "part",
            SectionLevel.CHAPTER: "chapter",
            SectionLevel.SECTION: "section",
            SectionLevel.SUBSECTION: "subsection",
            SectionLevel.SUBSUBSECTION: "subsubsection",
            SectionLevel.PARAGRAPH: "paragraph",
            SectionLevel.SUBPARAGRAPH: "subparagraph",
        }

        command = command_map[self.level]
        if not self.numbered:
            command += "*"

        return command

    def get_depth(self) -> int:
        """Get numerical depth of this section level."""
        depth_map = {
            SectionLevel.PART: -1,
            SectionLevel.CHAPTER: 0,
            SectionLevel.SECTION: 1,
            SectionLevel.SUBSECTION: 2,
            SectionLevel.SUBSUBSECTION: 3,
            SectionLevel.PARAGRAPH: 4,
            SectionLevel.SUBPARAGRAPH: 5,
        }
        return depth_map[self.level]

    def add_subsection(self, subsection: "ContentSection") -> None:
        """Add a subsection, ensuring proper level hierarchy."""
        if subsection.get_depth() <= self.get_depth():
            raise ValueError(
                f"Subsection level {subsection.level} must be deeper than parent level {self.level}"
            )
        self.subsections.append(subsection)

    def get_all_content_items(self) -> list[Any]:
        """Get all content items including those in subsections."""
        items = list(self.content_items)
        for subsection in self.subsections:
            items.extend(subsection.get_all_content_items())
        return items

    def get_clean_title(self, strip_manual_numbering: bool = False) -> str:
        """Get section title, optionally stripped of manual numbering.

        Args:
            strip_manual_numbering: If True, remove "Chapter X:" prefixes

        Returns:
            Clean section title for LaTeX native numbering
        """
        title = self.title

        if strip_manual_numbering:
            # Remove common manual numbering patterns
            import re

            # Match "Chapter X:" or "Part X:" at the start
            title = re.sub(r"^(Chapter|Part)\s+\d+:\s*", "", title)
            # Match "Appendix X:" at the start
            title = re.sub(r"^Appendix\s+[A-Z]:\s*", "", title)

        return title


# Allow forward references
ContentSection.model_rebuild()
