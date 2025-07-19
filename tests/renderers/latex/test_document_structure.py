"""Tests for LaTeX document structure system."""

from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.content import BaseContent, Source
from dnd5e.core.models.document_metadata import (
    ContentSection,
    DocumentAuthor,
    DocumentMetadata,
    DocumentStructure,
    DocumentType,
    SectionLevel,
)
from dnd5e.renderers.base.context import RenderContext
from dnd5e.renderers.latex.document_structure import DocumentStructureBuilder


class MockContent(BaseContent):
    """Mock content for testing."""

    def __init__(self, name: str, content_type: str = "unknown"):
        super().__init__(name=name, source=Source(abbreviation="TEST"))
        self._content_type = content_type


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""

    def test_default_metadata(self):
        """Test default metadata creation."""
        metadata = DocumentMetadata(title="Test Document")

        assert metadata.title == "Test Document"
        assert metadata.subtitle is None
        assert metadata.document_type == DocumentType.BOOK
        assert metadata.include_toc is True
        assert metadata.include_index is False
        assert metadata.use_parts is False

    def test_metadata_with_authors(self):
        """Test metadata with author information."""
        authors = [
            DocumentAuthor(name="John Doe", email="john@example.com"),
            DocumentAuthor(name="Jane Smith"),
        ]

        metadata = DocumentMetadata(
            title="Test Document", authors=authors, subtitle="A Test"
        )

        assert len(metadata.authors) == 2
        assert metadata.get_author_list() == "John Doe and Jane Smith"

    def test_metadata_multiple_authors(self):
        """Test metadata with multiple authors."""
        authors = [
            DocumentAuthor(name="Alice"),
            DocumentAuthor(name="Bob"),
            DocumentAuthor(name="Charlie"),
        ]

        metadata = DocumentMetadata(title="Test", authors=authors)
        assert metadata.get_author_list() == "Alice, Bob, and Charlie"

    def test_document_class_for_type(self):
        """Test document class selection based on type."""
        book_metadata = DocumentMetadata(title="Book", document_type=DocumentType.BOOK)
        article_metadata = DocumentMetadata(
            title="Article", document_type=DocumentType.ARTICLE
        )

        assert book_metadata.get_document_class_for_type() == "dndbook"
        assert article_metadata.get_document_class_for_type() == "dndarticle"

    def test_frontmatter_usage(self):
        """Test frontmatter usage determination."""
        book_metadata = DocumentMetadata(
            title="Book",
            document_type=DocumentType.BOOK,
            structure=DocumentStructure.FRONTMATTER_MAINMATTER_BACKMATTER,
        )
        article_metadata = DocumentMetadata(
            title="Article", document_type=DocumentType.ARTICLE
        )

        assert book_metadata.should_use_frontmatter() is True
        assert article_metadata.should_use_frontmatter() is False

    def test_max_section_level(self):
        """Test maximum section level determination."""
        book_metadata = DocumentMetadata(title="Book", document_type=DocumentType.BOOK)
        article_metadata = DocumentMetadata(
            title="Article", document_type=DocumentType.ARTICLE
        )
        part_metadata = DocumentMetadata(title="Book", use_parts=True)

        assert book_metadata.get_max_section_level() == SectionLevel.CHAPTER
        assert article_metadata.get_max_section_level() == SectionLevel.SECTION
        assert part_metadata.get_max_section_level() == SectionLevel.PART


class TestContentSection:
    """Tests for ContentSection model."""

    def test_basic_section(self):
        """Test basic section creation."""
        section = ContentSection(
            title="Test Chapter",
            level=SectionLevel.CHAPTER,
            numbered=True,
            label="ch:test",
        )

        assert section.title == "Test Chapter"
        assert section.level == SectionLevel.CHAPTER
        assert section.numbered is True
        assert section.label == "ch:test"
        assert section.get_latex_command() == "chapter"

    def test_unnumbered_section(self):
        """Test unnumbered section."""
        section = ContentSection(
            title="Appendix", level=SectionLevel.SECTION, numbered=False
        )

        assert section.get_latex_command() == "section*"

    def test_section_depth(self):
        """Test section depth calculation."""
        part = ContentSection(title="Part", level=SectionLevel.PART)
        chapter = ContentSection(title="Chapter", level=SectionLevel.CHAPTER)
        section = ContentSection(title="Section", level=SectionLevel.SECTION)
        subsection = ContentSection(title="Subsection", level=SectionLevel.SUBSECTION)

        assert part.get_depth() == -1
        assert chapter.get_depth() == 0
        assert section.get_depth() == 1
        assert subsection.get_depth() == 2

    def test_add_subsection(self):
        """Test adding subsections with proper hierarchy."""
        chapter = ContentSection(title="Chapter", level=SectionLevel.CHAPTER)
        section = ContentSection(title="Section", level=SectionLevel.SECTION)
        subsection = ContentSection(title="Subsection", level=SectionLevel.SUBSECTION)

        chapter.add_subsection(section)
        section.add_subsection(subsection)

        assert len(chapter.subsections) == 1
        assert len(section.subsections) == 1
        assert chapter.subsections[0] == section
        assert section.subsections[0] == subsection

    def test_invalid_subsection_hierarchy(self):
        """Test that invalid subsection hierarchy raises error."""
        section = ContentSection(title="Section", level=SectionLevel.SECTION)
        chapter = ContentSection(title="Chapter", level=SectionLevel.CHAPTER)

        with pytest.raises(ValueError, match="must be deeper than parent level"):
            section.add_subsection(chapter)

    def test_get_all_content_items(self):
        """Test getting all content items including subsections."""
        item1 = MockContent("Item 1")
        item2 = MockContent("Item 2")
        item3 = MockContent("Item 3")

        chapter = ContentSection(
            title="Chapter", level=SectionLevel.CHAPTER, content_items=[item1]
        )
        section = ContentSection(
            title="Section", level=SectionLevel.SECTION, content_items=[item2, item3]
        )

        chapter.add_subsection(section)

        all_items = chapter.get_all_content_items()
        assert len(all_items) == 3
        assert item1 in all_items
        assert item2 in all_items
        assert item3 in all_items


class TestDocumentStructureBuilder:
    """Tests for DocumentStructureBuilder class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.metadata = DocumentMetadata(
            title="Test Adventure",
            document_type=DocumentType.ADVENTURE,
            authors=[DocumentAuthor(name="Test Author")],
        )
        self.builder = DocumentStructureBuilder(self.metadata)
        self.context = RenderContext()

    def test_builder_initialization(self):
        """Test builder initialization."""
        assert self.builder.metadata == self.metadata
        assert self.builder._section_counter == 0

    def test_organize_content_by_type(self):
        """Test content organization by type."""
        content_items = [
            MockContent("Spell 1", "spell"),
            MockContent("Creature 1", "creature"),
            MockContent("Spell 2", "spell"),
            MockContent("Item 1", "item"),
        ]

        # Mock the ContentType.from_content method
        from unittest.mock import patch

        with patch(
            "dnd5e.core.models.content.ContentType.from_content"
        ) as mock_from_content:

            def side_effect(content):
                if content._content_type == "spell":
                    from dnd5e.core.models.content import ContentType

                    return ContentType.SPELL
                elif content._content_type == "creature":
                    from dnd5e.core.models.content import ContentType

                    return ContentType.CREATURE
                elif content._content_type == "item":
                    from dnd5e.core.models.content import ContentType

                    return ContentType.ITEM
                else:
                    raise ValueError("Unknown type")

            mock_from_content.side_effect = side_effect

            organized = self.builder._organize_content_by_type(content_items)

            assert "spell" in organized
            assert "creature" in organized
            assert "item" in organized
            assert len(organized["spell"]) == 2
            assert len(organized["creature"]) == 1
            assert len(organized["item"]) == 1

    def test_build_adventure_structure(self):
        """Test building adventure document structure."""
        # Create mock adventure content with proper attributes
        chapter1 = Mock()
        chapter1.name = "Chapter 1"
        chapter1.headers = ["Introduction", "Background"]
        chapter1.entries = []

        chapter2 = Mock()
        chapter2.name = "Chapter 2"
        chapter2.headers = ["The Quest Begins"]
        chapter2.entries = []

        adventure = Mock()
        adventure.name = "Test Adventure"
        adventure.contents = [chapter1, chapter2]

        organized_content = {"adventure": [adventure]}

        sections = self.builder._build_adventure_structure(
            organized_content, self.context
        )

        assert len(sections) >= 2  # At least the adventure chapters
        assert sections[0].title == "Chapter 1"
        assert sections[0].level == SectionLevel.CHAPTER

    def test_build_supplement_structure(self):
        """Test building supplement document structure."""
        content_items = [
            MockContent("Spell 1", "spell"),
            MockContent("Creature 1", "creature"),
            MockContent("Item 1", "item"),
        ]

        # Mock the ContentType.from_content method
        from unittest.mock import patch

        with patch(
            "dnd5e.core.models.content.ContentType.from_content"
        ) as mock_from_content:

            def side_effect(content):
                if content._content_type == "spell":
                    from dnd5e.core.models.content import ContentType

                    return ContentType.SPELL
                elif content._content_type == "creature":
                    from dnd5e.core.models.content import ContentType

                    return ContentType.CREATURE
                elif content._content_type == "item":
                    from dnd5e.core.models.content import ContentType

                    return ContentType.ITEM
                else:
                    raise ValueError("Unknown type")

            mock_from_content.side_effect = side_effect

            organized_content = self.builder._organize_content_by_type(content_items)

            # Change to supplement document type
            self.metadata.document_type = DocumentType.SUPPLEMENT
            sections = self.builder._build_supplement_structure(
                organized_content, self.context
            )

            # Should have chapters for spells, creatures, and items
            chapter_titles = [section.title for section in sections]
            assert "Spells" in chapter_titles
            assert "Creatures and NPCs" in chapter_titles
            assert "Magic Items and Equipment" in chapter_titles

    def test_build_article_structure(self):
        """Test building article document structure."""
        # Use pre-organized content to avoid ContentType resolution
        organized_content = {"unknown": [MockContent("Content 1")]}
        sections = self.builder._build_article_structure(
            organized_content, self.context
        )

        # Article should use sections, not chapters
        assert len(sections) >= 1
        assert sections[0].level == SectionLevel.SECTION

    def test_generate_latex_structure(self):
        """Test LaTeX structure command generation."""
        section = ContentSection(
            title="Test Chapter",
            level=SectionLevel.CHAPTER,
            numbered=True,
            label="ch:test",
            page_break_before=True,
        )

        commands = self.builder.generate_latex_structure([section])

        # Should include frontmatter commands for adventure
        assert "\\frontmatter" in commands
        assert "\\maketitle" in commands
        assert "\\tableofcontents" in commands
        assert "\\mainmatter" in commands

        # Should include the section command
        chapter_commands = self.builder._generate_section_commands(section)
        assert "\\clearpage" in chapter_commands  # page break before
        assert "\\chapter{Test Chapter}\\label{ch:test}" in chapter_commands

    def test_create_document_context(self):
        """Test document context creation."""
        sections = [
            ContentSection(title="Chapter 1", level=SectionLevel.CHAPTER),
            ContentSection(title="Chapter 2", level=SectionLevel.CHAPTER),
        ]

        context = self.builder._create_document_context(sections, self.context)

        assert context["metadata"] == self.metadata
        assert context["sections"] == sections
        assert context["document_class"] == "dndbook"
        assert context["use_frontmatter"] is True
        assert context["total_sections"] == 2

    def test_format_content_type_title(self):
        """Test content type title formatting."""
        assert self.builder._format_content_type_title("spell") == "Spells"
        assert (
            self.builder._format_content_type_title("creature") == "Creatures and NPCs"
        )
        assert (
            self.builder._format_content_type_title("item")
            == "Magic Items and Equipment"
        )
        assert (
            self.builder._format_content_type_title("unknown") == "Additional Content"
        )

    def test_generate_label(self):
        """Test LaTeX label generation."""
        label1 = self.builder._generate_label("Test Chapter")
        label2 = self.builder._generate_label("Another Section")

        assert "test-chapter" in label1
        assert "another-section" in label2
        assert label1 != label2  # Should be unique due to counter

    def test_build_document_structure_integration(self):
        """Test complete document structure building."""
        content_items = [
            MockContent("Content 1", "unknown"),
            MockContent("Content 2", "unknown"),
        ]

        # Use a simple patch to bypass ContentType resolution
        with patch.object(self.builder, "_organize_content_by_type") as mock_organize:
            mock_organize.return_value = {"unknown": content_items}

            sections, document_context = self.builder.build_document_structure(
                content_items, self.context
            )

            assert len(sections) >= 1  # Should have at least one section
            assert document_context["metadata"] == self.metadata
            assert document_context["total_content_items"] == 2


class TestDocumentStructureIntegration:
    """Integration tests for document structure system."""

    def test_book_document_structure(self):
        """Test complete book document structure."""
        metadata = DocumentMetadata(
            title="Player's Handbook",
            subtitle="Core Rules",
            document_type=DocumentType.BOOK,
            authors=[DocumentAuthor(name="Wizards of the Coast")],
            include_toc=True,
            include_index=True,
        )

        builder = DocumentStructureBuilder(metadata)
        content_items = [
            MockContent("Fireball", "unknown"),
            MockContent("Dragon", "unknown"),
            MockContent("Magic Sword", "unknown"),
        ]

        context = RenderContext()

        # Use a simple patch to bypass ContentType resolution
        with patch.object(builder, "_organize_content_by_type") as mock_organize:
            mock_organize.return_value = {"unknown": content_items}

            sections, document_context = builder.build_document_structure(
                content_items, context
            )

            # Verify structure
            assert len(sections) >= 1  # At least one section
            assert document_context["use_frontmatter"] is True
            assert document_context["document_class"] == "dndbook"

            # Generate LaTeX commands
            latex_commands = builder.generate_latex_structure(sections)
            assert "\\frontmatter" in latex_commands
            assert "\\mainmatter" in latex_commands

    def test_article_document_structure(self):
        """Test complete article document structure."""
        metadata = DocumentMetadata(
            title="Spell Compendium",
            document_type=DocumentType.ARTICLE,
            include_toc=False,
        )

        builder = DocumentStructureBuilder(metadata)
        content_items = [MockContent("Magic Missile", "unknown")]
        context = RenderContext()

        # Use a simple patch to bypass ContentType resolution
        with patch.object(builder, "_organize_content_by_type") as mock_organize:
            mock_organize.return_value = {"unknown": content_items}

            sections, document_context = builder.build_document_structure(
                content_items, context
            )

            # Verify structure
            assert document_context["use_frontmatter"] is False
            assert document_context["document_class"] == "dndarticle"

            # Should use sections instead of chapters for articles
            for section in sections:
                assert section.level == SectionLevel.SECTION

    def test_supplement_document_organization(self):
        """Test supplement document with multiple content types."""
        metadata = DocumentMetadata(
            title="Homebrew Compendium", document_type=DocumentType.SUPPLEMENT
        )

        builder = DocumentStructureBuilder(metadata)
        content_items = [
            MockContent("Custom Spell", "unknown"),
            MockContent("Homebrew Race", "unknown"),
            MockContent("Custom Class", "unknown"),
            MockContent("Magic Item", "unknown"),
        ]

        context = RenderContext()

        # Use a simple patch to simulate organized content
        organized_content = {
            "spell": [content_items[0]],
            "race": [content_items[1]],
            "class": [content_items[2]],
            "item": [content_items[3]],
        }

        with patch.object(builder, "_organize_content_by_type") as mock_organize:
            mock_organize.return_value = organized_content

            sections, document_context = builder.build_document_structure(
                content_items, context
            )

            # Should organize by content type with preferred order
            chapter_titles = [section.title for section in sections]

            # Check that chapters are created for each content type
            assert len(sections) >= 4
            assert any("Races" in title for title in chapter_titles)
            assert any("Classes" in title for title in chapter_titles)
            assert any("Spells" in title for title in chapter_titles)
            assert any("Magic Items" in title for title in chapter_titles)
