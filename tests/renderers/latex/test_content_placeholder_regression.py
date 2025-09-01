"""Regression tests for content placeholder replacement bug.

This module contains tests to ensure that the duplicate content bug
where string placeholders were globally replaced does not recur.
"""

import pytest

from studiorum.core.models.books import Book, Chapter
from studiorum.core.models.content import Source
from studiorum.core.models.document_metadata import DocumentMetadata, DocumentType
from studiorum.latex_engine.core.document import LaTeXDocumentRenderer
from studiorum.latex_engine.core.document_structure import (
    ContentSection,
    DocumentStructureBuilder,
    SectionLevel,
)
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


@pytest.mark.rendering
class TestContentPlaceholderRegression:
    """Test that content placeholder replacement doesn't cause duplication."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.renderer = LaTeXDocumentRenderer()
        metadata = DocumentMetadata(
            title="Test Book",
            document_type=DocumentType.BOOK,
        )
        self.context = RenderingContext(
            output_format="latex", metadata={"document_metadata": metadata}
        )

    def test_string_placeholder_replacement_is_limited(self) -> None:
        """Test that string placeholders are replaced only once, not globally."""
        # Create two sections with string content
        section1 = ContentSection(
            title="Chapter 1",
            level=SectionLevel.CHAPTER,
            content_items=[
                "First chapter content",
                "More content for chapter 1",
            ],
        )

        section2 = ContentSection(
            title="Chapter 2",
            level=SectionLevel.CHAPTER,
            content_items=[
                "Second chapter content",
                "More content for chapter 2",
            ],
        )

        # Create a mock document with placeholders
        document = """
\\chapter{Chapter 1}
% Content: String Entry (str)
% Content: String Entry (str)

\\chapter{Chapter 2}
% Content: String Entry (str)
% Content: String Entry (str)
"""

        # Process the sections
        result = self.renderer._render_content_in_sections(
            document, [section1, section2], self.context
        )

        # Verify each chapter has its own content, not duplicated
        assert "First chapter content" in result
        assert "More content for chapter 1" in result
        assert "Second chapter content" in result
        assert "More content for chapter 2" in result

        # Count occurrences - each should appear exactly once
        assert result.count("First chapter content") == 1
        assert result.count("Second chapter content") == 1
        assert result.count("More content for chapter 1") == 1
        assert result.count("More content for chapter 2") == 1

    def test_mixed_content_placeholder_replacement(self) -> None:
        """Test placeholder replacement with mixed content types."""
        # Create sections with mixed string and dict content
        section1 = ContentSection(
            title="Introduction",
            level=SectionLevel.CHAPTER,
            content_items=[
                "Introduction paragraph",
                {"type": "section", "name": "Welcome", "entries": ["Welcome text"]},
            ],
        )

        section2 = ContentSection(
            title="Rules",
            level=SectionLevel.CHAPTER,
            content_items=[
                "Rules paragraph",
                {
                    "type": "section",
                    "name": "Basic Rules",
                    "entries": ["Basic rules text"],
                },
            ],
        )

        document = """
\\chapter{Introduction}
% Content: String Entry (str)
% Content: Welcome (dict)

\\chapter{Rules}
% Content: String Entry (str)
% Content: Basic Rules (dict)
"""

        # Mock render_content_item to return predictable content
        def mock_render_content_item(item, context):
            if isinstance(item, str):
                return item
            elif isinstance(item, dict):
                return f"[Rendered: {item.get('name', 'Unknown')}]"
            return ""

        self.renderer.render_content_item = mock_render_content_item

        result = self.renderer._render_content_in_sections(
            document, [section1, section2], self.context
        )

        # Verify correct content in correct places
        assert "Introduction paragraph" in result
        assert "Rules paragraph" in result
        assert "[Rendered: Welcome]" in result
        assert "[Rendered: Basic Rules]" in result

        # Ensure no duplication
        assert result.count("Introduction paragraph") == 1
        assert result.count("Rules paragraph") == 1

    def test_book_rendering_no_cross_chapter_duplication(self) -> None:
        """Test full book rendering doesn't duplicate content across chapters."""
        # Create a book with multiple chapters
        book = Book(
            name="Test Book",
            source=Source(abbreviation="TST"),
            contents=[
                Chapter(
                    name="Introduction",
                    entries=[
                        "The introduction content that should only appear once.",
                        {"type": "insetReadaloud", "entries": ["Read aloud text"]},
                    ],
                ),
                Chapter(
                    name="Spellcasting",
                    entries=[
                        "Magic permeates the world.",
                        {
                            "type": "section",
                            "name": "What is a Spell?",
                            "entries": ["Spell description"],
                        },
                    ],
                ),
            ],
        )

        # Build document structure
        builder = DocumentStructureBuilder(self.context.metadata["document_metadata"])
        sections, _ = builder.build_document_structure([book], self.context)

        # Create a simple template-like document
        document = ""
        for section in sections:
            document += f"\\chapter{{{section.title}}}\\label{{{section.label}}}\n"
            for i, item in enumerate(section.content_items or []):
                if isinstance(item, str):
                    document += "% Content: String Entry (str)\n"
                elif isinstance(item, dict):
                    name = item.get("name", "Unknown")
                    escaped_name = self.renderer._escape_latex(name)
                    document += f"% Content: {escaped_name} (dict)\n"

        # Mock render_content_item to return the actual content
        def mock_render_content_item(item, context):
            if isinstance(item, str):
                return item
            elif isinstance(item, dict):
                if item.get("type") == "insetReadaloud":
                    return (
                        "\\begin{DndReadAloud}\n"
                        + str(item.get("entries", [])[0])
                        + "\n\\end{DndReadAloud}"
                    )
                elif item.get("type") == "section":
                    return f"\\section{{{item.get('name', 'Unknown')}}}\n{item.get('entries', [''])[0]}"
            return ""

        self.renderer.render_content_item = mock_render_content_item

        # Render content in sections
        result = self.renderer._render_content_in_sections(
            document, sections, self.context
        )

        # Verify Introduction content appears only in Introduction chapter
        intro_content = "The introduction content that should only appear once."
        assert intro_content in result
        assert result.count(intro_content) == 1

        # Find where the introduction content appears
        intro_pos = result.find(intro_content)
        intro_chapter_start = result.rfind("\\chapter{Introduction}", 0, intro_pos)
        spell_chapter_start = result.find("\\chapter{Spellcasting}")

        # Ensure introduction content is before Spellcasting chapter
        assert intro_chapter_start < intro_pos < spell_chapter_start

        # Verify Spellcasting has its own content
        assert "Magic permeates the world." in result
        magic_pos = result.find("Magic permeates the world.")
        assert (
            magic_pos > spell_chapter_start
        )  # Magic text is after Spellcasting chapter starts

    def test_placeholder_pattern_edge_cases(self) -> None:
        """Test edge cases in placeholder pattern matching."""
        section = ContentSection(
            title="Test",
            level=SectionLevel.CHAPTER,
            content_items=[
                "Normal content",
                "",  # Empty string
                "Content with % special characters",
                "% Content: This looks like a placeholder but isn't",
            ],
        )

        document = """
\\chapter{Test}
% Content: String Entry (str)
% Content: String Entry (str)
% Content: String Entry (str)
% Content: String Entry (str)
"""

        result = self.renderer._render_content_in_sections(
            document, [section], self.context
        )

        # All content should be present
        assert "Normal content" in result
        # LaTeX escaping is applied, so % becomes \%
        assert "Content with \\% special characters" in result
        assert "\\% Content: This looks like a placeholder but isn't" in result

        # Original placeholders should be replaced (one remains because empty string produces no output)
        assert (
            result.count("% Content: String Entry (str)") == 1
        )  # Empty string leaves its placeholder

    @pytest.mark.parametrize("num_chapters", [2, 5, 10])
    def test_multiple_chapters_with_identical_first_entries(
        self, num_chapters: int
    ) -> None:
        """Test that chapters with identical first entries don't interfere."""
        # Create chapters that all start with string entries
        sections = []
        for i in range(num_chapters):
            section = ContentSection(
                title=f"Chapter {i + 1}",
                level=SectionLevel.CHAPTER,
                content_items=[
                    f"Chapter {i + 1} first paragraph",
                    f"Chapter {i + 1} second paragraph",
                ],
            )
            sections.append(section)

        # Build document with placeholders
        document = ""
        for section in sections:
            document += f"\\chapter{{{section.title}}}\n"
            document += "% Content: String Entry (str)\n"
            document += "% Content: String Entry (str)\n\n"

        result = self.renderer._render_content_in_sections(
            document, sections, self.context
        )

        # Verify each chapter has its unique content
        for i in range(num_chapters):
            first_para = f"Chapter {i + 1} first paragraph"
            second_para = f"Chapter {i + 1} second paragraph"

            assert first_para in result
            assert second_para in result
            assert result.count(first_para) == 1
            assert result.count(second_para) == 1

        # No placeholders should remain
        assert "% Content: String Entry (str)" not in result
