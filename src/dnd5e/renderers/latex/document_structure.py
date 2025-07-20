"""Document structure builder for LaTeX document assembly."""

from typing import Any

from ...core.models.content import BaseContent, ContentType
from ...core.models.document_metadata import (
    ContentSection,
    DocumentMetadata,
    DocumentType,
    SectionLevel,
)
from ..base.context import RenderContext


class DocumentStructureBuilder:
    """Builds structured LaTeX documents with proper hierarchy and organization."""

    def __init__(self, metadata: DocumentMetadata):
        """Initialize document structure builder.

        Args:
            metadata: Document metadata configuration
        """
        self.metadata = metadata
        self._section_counter = 0

    def build_document_structure(
        self, content_items: list[BaseContent], context: RenderContext
    ) -> tuple[list[ContentSection], dict[str, Any]]:
        """Build complete document structure from content items.

        Args:
            content_items: List of content to organize
            context: Rendering context

        Returns:
            Tuple of (sections, document_context)
        """
        # Organize content by type and source
        organized_content = self._organize_content_by_type(content_items)

        # Build section hierarchy based on document type
        sections = self._build_section_hierarchy(organized_content, context)

        # Create document context for templates
        document_context = self._create_document_context(sections, context)

        return sections, document_context

    def _organize_content_by_type(
        self, content_items: list[BaseContent]
    ) -> dict[str, list[BaseContent]]:
        """Organize content items by their content type.

        Args:
            content_items: List of content to organize

        Returns:
            Dictionary mapping content types to lists of content
        """
        organized: dict[str, list[BaseContent]] = {}

        for item in content_items:
            try:
                content_type = ContentType.from_content(item)
                type_key = content_type.value
            except ValueError:
                # Fallback for unknown content types
                type_key = "unknown"

            if type_key not in organized:
                organized[type_key] = []
            organized[type_key].append(item)

        return organized

    def _build_section_hierarchy(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build section hierarchy based on document type and content.

        Args:
            organized_content: Content organized by type
            context: Rendering context

        Returns:
            List of top-level sections
        """
        sections = []

        if self.metadata.document_type == DocumentType.ADVENTURE:
            sections = self._build_adventure_structure(organized_content, context)
        elif self.metadata.document_type == DocumentType.BOOK:
            sections = self._build_book_structure(organized_content, context)
        elif self.metadata.document_type == DocumentType.SUPPLEMENT:
            sections = self._build_supplement_structure(organized_content, context)
        elif self.metadata.document_type == DocumentType.REFERENCE:
            sections = self._build_reference_structure(organized_content, context)
        elif self.metadata.document_type == DocumentType.ARTICLE:
            sections = self._build_article_structure(organized_content, context)
        else:
            # Fallback to generic structure
            sections = self._build_generic_structure(organized_content, context)

        return sections

    def _build_adventure_structure(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build structure for adventure documents.

        Adventures typically use:
        - Parts for major story arcs (optional)
        - Chapters for adventure sections
        - Sections for encounters/locations
        """
        sections = []

        # Handle adventure content specifically
        if ContentType.ADVENTURE.value in organized_content:
            for adventure in organized_content[ContentType.ADVENTURE.value]:
                if hasattr(adventure, "contents") and adventure.contents:
                    # Process adventure chapters
                    for i, chapter in enumerate(adventure.contents):
                        chapter_section = self._create_chapter_section(
                            chapter, i + 1, context
                        )
                        sections.append(chapter_section)

        # Add other content types as separate chapters
        content_chapters = self._create_content_type_chapters(
            organized_content, context
        )
        sections.extend(content_chapters)

        return sections

    def _build_book_structure(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build structure for book documents.

        Books typically use:
        - Parts for major sections (optional)
        - Chapters for content organization
        - Sections for detailed content
        """
        sections = []

        # Handle book content specifically
        if ContentType.BOOK.value in organized_content:
            for book in organized_content[ContentType.BOOK.value]:
                if hasattr(book, "contents") and book.contents:
                    # Process book chapters
                    for i, chapter in enumerate(book.contents):
                        chapter_section = self._create_chapter_section(
                            chapter, i + 1, context
                        )
                        sections.append(chapter_section)

        # Add other content types as separate chapters
        content_chapters = self._create_content_type_chapters(
            organized_content, context
        )
        sections.extend(content_chapters)

        return sections

    def _build_supplement_structure(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build structure for supplement documents.

        Supplements typically organize by content type:
        - Chapter per content type (Spells, Creatures, Items, etc.)
        - Sections for individual items
        """
        sections = []

        # Content type priority for organization
        content_type_order = [
            ContentType.CLASS.value,
            ContentType.RACE.value,
            ContentType.BACKGROUND.value,
            ContentType.FEAT.value,
            ContentType.SPELL.value,
            ContentType.CREATURE.value,
            ContentType.ITEM.value,
        ]

        # Add chapters in preferred order
        for content_type in content_type_order:
            if content_type in organized_content:
                chapter = self._create_content_type_chapter(
                    content_type, organized_content[content_type], context
                )
                sections.append(chapter)

        # Add any remaining content types
        for content_type, items in organized_content.items():
            if content_type not in content_type_order:
                chapter = self._create_content_type_chapter(
                    content_type, items, context
                )
                sections.append(chapter)

        return sections

    def _build_reference_structure(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build structure for reference documents.

        References typically use:
        - Sections for major content groups
        - Alphabetical or type-based organization
        """
        sections = []

        # Create sections for each content type
        for content_type, items in organized_content.items():
            section = self._create_content_type_section(content_type, items, context)
            sections.append(section)

        return sections

    def _build_article_structure(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build structure for article documents.

        Articles typically use:
        - Simple section-based organization
        - Minimal hierarchy
        """
        sections = []

        # For articles, create simple sections
        for content_type, items in organized_content.items():
            section = self._create_content_type_section(content_type, items, context)
            sections.append(section)

        return sections

    def _build_generic_structure(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Build generic structure as fallback.

        Args:
            organized_content: Content organized by type
            context: Rendering context

        Returns:
            List of sections with basic organization
        """
        sections = []

        for content_type, items in organized_content.items():
            if self.metadata.get_max_section_level() == SectionLevel.CHAPTER:
                section = self._create_content_type_chapter(
                    content_type, items, context
                )
            else:
                section = self._create_content_type_section(
                    content_type, items, context
                )
            sections.append(section)

        return sections

    def _create_chapter_section(
        self, chapter_data: Any, chapter_num: int, context: RenderContext
    ) -> ContentSection:
        """Create a ContentSection from adventure/book chapter data.

        Args:
            chapter_data: Chapter data from adventure/book
            chapter_num: Chapter number
            context: Rendering context

        Returns:
            ContentSection for the chapter
        """
        # Extract chapter name
        if hasattr(chapter_data, "name"):
            title = chapter_data.name
        else:
            title = f"Chapter {chapter_num}"

        # Create chapter section
        section = ContentSection(
            title=title,
            level=SectionLevel.CHAPTER,
            numbered=True,
            label=f"ch:{self._generate_label(title)}",
            page_break_before=False,
            page_break_after=False,
            two_column=None,
        )

        # Add chapter content
        if hasattr(chapter_data, "entries"):
            section.content_items = chapter_data.entries

        # Add chapter headers as subsections
        if hasattr(chapter_data, "headers") and chapter_data.headers:
            for header in chapter_data.headers:
                if isinstance(header, str):
                    subsection = ContentSection(
                        title=header,
                        level=SectionLevel.SECTION,
                        numbered=True,
                        label=f"sec:{self._generate_label(header)}",
                        page_break_before=False,
                        page_break_after=False,
                        two_column=None,
                    )
                    section.subsections.append(subsection)

        return section

    def _create_content_type_chapters(
        self, organized_content: dict[str, list[BaseContent]], context: RenderContext
    ) -> list[ContentSection]:
        """Create chapters for content types (excluding adventures/books).

        Args:
            organized_content: Content organized by type
            context: Rendering context

        Returns:
            List of content type chapters
        """
        chapters = []

        # Skip adventure and book content as they're handled separately
        skip_types = {ContentType.ADVENTURE.value, ContentType.BOOK.value}

        for content_type, items in organized_content.items():
            if content_type not in skip_types:
                chapter = self._create_content_type_chapter(
                    content_type, items, context
                )
                chapters.append(chapter)

        return chapters

    def _create_content_type_chapter(
        self, content_type: str, items: list[BaseContent], context: RenderContext
    ) -> ContentSection:
        """Create a chapter for a specific content type.

        Args:
            content_type: Type of content
            items: Content items of this type
            context: Rendering context

        Returns:
            ContentSection for the content type
        """
        # Format title
        title = self._format_content_type_title(content_type)

        section = ContentSection(
            title=title,
            level=SectionLevel.CHAPTER,
            numbered=True,
            label=f"ch:{self._generate_label(content_type)}",
            content_items=items,
            page_break_before=False,
            page_break_after=False,
            two_column=None,
        )

        return section

    def _create_content_type_section(
        self, content_type: str, items: list[BaseContent], context: RenderContext
    ) -> ContentSection:
        """Create a section for a specific content type.

        Args:
            content_type: Type of content
            items: Content items of this type
            context: Rendering context

        Returns:
            ContentSection for the content type
        """
        # Format title
        title = self._format_content_type_title(content_type)

        section = ContentSection(
            title=title,
            level=SectionLevel.SECTION,
            numbered=True,
            label=f"sec:{self._generate_label(content_type)}",
            content_items=items,
            page_break_before=False,
            page_break_after=False,
            two_column=None,
        )

        return section

    def _format_content_type_title(self, content_type: str) -> str:
        """Format content type as a human-readable title.

        Args:
            content_type: Content type string

        Returns:
            Formatted title
        """
        # Handle special cases
        special_cases = {
            "spell": "Spells",
            "creature": "Creatures and NPCs",
            "item": "Magic Items and Equipment",
            "class": "Classes",
            "race": "Races",
            "background": "Backgrounds",
            "feat": "Feats",
            "adventure": "Adventures",
            "book": "Books",
            "supplement": "Supplemental Material",
            "unknown": "Additional Content",
        }

        if content_type in special_cases:
            return special_cases[content_type]

        # Default formatting: capitalize and pluralize
        return content_type.replace("_", " ").title() + "s"

    def _generate_label(self, text: str) -> str:
        """Generate a LaTeX-safe label from text.

        Args:
            text: Text to convert to label

        Returns:
            LaTeX-safe label
        """
        self._section_counter += 1

        # Create safe label from text
        safe_text = (
            text.lower()
            .replace(" ", "-")
            .replace("'", "")
            .replace('"', "")
            .replace("&", "and")
            .replace("/", "-")
        )

        # Remove non-alphanumeric characters except hyphens
        safe_text = "".join(c for c in safe_text if c.isalnum() or c == "-")

        return f"{safe_text}-{self._section_counter}"

    def _create_document_context(
        self, sections: list[ContentSection], context: RenderContext
    ) -> dict[str, Any]:
        """Create document context for template rendering.

        Args:
            sections: Document sections
            context: Rendering context

        Returns:
            Document context dictionary
        """
        return {
            "metadata": self.metadata,
            "sections": sections,
            "document_class": self.metadata.get_document_class_for_type(),
            "use_frontmatter": self.metadata.should_use_frontmatter(),
            "use_parts": self.metadata.use_parts,
            "max_section_depth": self.metadata.max_section_depth,
            "numbering_depth": self.metadata.numbering_depth,
            "total_sections": len(sections),
            "total_content_items": sum(
                len(section.get_all_content_items()) for section in sections
            ),
        }

    def generate_latex_structure(self, sections: list[ContentSection]) -> list[str]:
        """Generate LaTeX commands for document structure.

        Args:
            sections: Document sections to convert

        Returns:
            List of LaTeX structure commands
        """
        commands = []

        # Add frontmatter if needed
        if self.metadata.should_use_frontmatter():
            commands.append("\\frontmatter")

            # Add title page
            commands.append("\\maketitle")

            # Add table of contents
            if self.metadata.include_toc:
                commands.append("\\tableofcontents")
                commands.append("\\clearpage")

            commands.append("\\mainmatter")

        # Generate section commands
        for section in sections:
            commands.extend(self._generate_section_commands(section))

        # Add backmatter if needed
        if self.metadata.should_use_frontmatter():
            if self.metadata.include_index:
                commands.append("\\backmatter")
                commands.append("\\printindex")

        return commands

    def _generate_section_commands(self, section: ContentSection) -> list[str]:
        """Generate LaTeX commands for a section and its subsections.

        Args:
            section: Section to generate commands for

        Returns:
            List of LaTeX commands
        """
        commands = []

        # Add page break if requested
        if section.page_break_before:
            commands.append("\\clearpage")

        # Add section command
        section_cmd = f"\\{section.get_latex_command()}{{{section.title}}}"
        if section.label:
            section_cmd += f"\\label{{{section.label}}}"
        commands.append(section_cmd)

        # Add content placeholder (will be filled by content renderers)
        if section.content_items:
            commands.append(f"% Content for {section.title}")

        # Add subsections
        for subsection in section.subsections:
            commands.extend(self._generate_section_commands(subsection))

        # Add page break if requested
        if section.page_break_after:
            commands.append("\\clearpage")

        return commands
