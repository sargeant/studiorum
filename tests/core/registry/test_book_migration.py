"""Tests for Book content type migration to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestBookMigration:
    """Test that Book content type works with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_book_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Book correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.books import Book
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="book",
                file_patterns=["book", "books"],
                statblock_tags=["book"],
                loader_type="json",
            )
            class TestBook(Book):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "book"
        assert metadata.model_class == TestBook
        assert metadata.file_patterns == ["book", "books"]
        assert metadata.statblock_tags == ["book"]
        assert metadata.loader_type == "json"

    def test_book_enum_created_dynamically(self):
        """Test that BOOK enum is created dynamically during finalization."""
        # Import books to register via decorator
        from dnd5e.core.models import books

        # Initially BOOK should already exist (it's in ContentType enum)
        assert hasattr(ContentType, "BOOK")
        assert ContentType.BOOK == "book"

        # Initialize should still work and not conflict
        initialize_content_types()

        # Verify enum still exists and works
        assert hasattr(ContentType, "BOOK")
        assert ContentType.BOOK == "book"

    def test_book_content_creation(self):
        """Test that Book content can be created and validated."""
        from dnd5e.core.models.books import Book, BookMetadata
        from dnd5e.core.models.chapter import Chapter

        # Create a simple book instance
        book = Book(
            name="Player's Handbook",
            source="PHB",
            id="phb",
            published="2014",
            author=["Wizards of the Coast"],
            contents=[
                Chapter(
                    name="Chapter 1: Step-by-Step Characters",
                    entries=["Character creation steps..."],
                ),
                Chapter(
                    name="Chapter 2: Races",
                    entries=["Race descriptions..."],
                ),
            ],
        )

        assert book.name == "Player's Handbook"
        assert book.source.abbreviation == "PHB"
        assert book.id == "phb"
        assert book.published == "2014"
        assert book.author == ["Wizards of the Coast"]
        assert len(book.contents) == 2
        assert book.get_chapter_count() == 2

    def test_book_with_metadata(self):
        """Test that Book works with BookMetadata nested model."""
        from dnd5e.core.models.books import Book, BookMetadata

        metadata = BookMetadata(
            id="dmg",
            published="2014",
            author=["Mike Mearls", "Jeremy Crawford"],
            cover={"type": "internal", "path": "cover.jpg"},
        )

        book = Book(
            name="Dungeon Master's Guide", source="DMG", metadata=metadata, contents=[]
        )

        assert book.name == "Dungeon Master's Guide"
        assert book.metadata is not None
        assert book.metadata.id == "dmg"
        assert book.metadata.author == ["Mike Mearls", "Jeremy Crawford"]
        assert book.get_authors_text() == "Mike Mearls and Jeremy Crawford"

    def test_book_5etools_format_transformation(self):
        """Test that Book correctly transforms 5etools format."""
        from dnd5e.core.models.books import Book

        # Simulate 5etools book format with "data" array
        raw_data = {
            "name": "Test Book",
            "source": "TEST",
            "id": "test",
            "data": [
                {
                    "name": "Introduction",
                    "type": "section",
                    "entries": ["Welcome to the test book..."],
                },
                {
                    "name": "Chapter 1",
                    "type": "chapter",
                    "entries": ["This is chapter 1 content..."],
                },
            ],
        }

        book = Book.model_validate(raw_data)

        assert book.name == "Test Book"
        assert book.id == "test"
        assert len(book.contents) == 2
        assert book.contents[0].name == "Introduction"
        assert book.contents[1].name == "Chapter 1"
        assert book.has_content()
        assert not book.is_metadata_only()

    def test_book_author_field_validation(self):
        """Test that Book handles author field in different formats."""
        from dnd5e.core.models.books import Book

        # Test single author as string
        book1 = Book(name="Test Book 1", source="TEST", author="Single Author")
        assert book1.author == ["Single Author"]
        assert book1.get_authors_text() == "Single Author"

        # Test multiple authors as list
        book2 = Book(
            name="Test Book 2",
            source="TEST",
            author=["Author One", "Author Two", "Author Three"],
        )
        assert book2.author == ["Author One", "Author Two", "Author Three"]
        assert book2.get_authors_text() == "Author One, Author Two, and Author Three"

    def test_book_content_analysis_methods(self):
        """Test book content analysis methods."""
        from dnd5e.core.models.books import Book
        from dnd5e.core.models.chapter import Chapter

        # Book with content
        book_with_content = Book(
            name="Content Book",
            source="TEST",
            id="content-book",
            contents=[
                Chapter(name="Chapter 1", entries=["Some content"]),
                Chapter(name="Chapter 2", entries=["More content"]),
            ],
        )

        assert book_with_content.has_content()
        assert not book_with_content.is_metadata_only()
        assert book_with_content.get_content_file_path() == "book-content-book.json"

        # Book without content (metadata only)
        book_metadata_only = Book(
            name="Metadata Book",
            source="TEST",
            id="metadata-book",
            contents=[
                Chapter(name="Chapter 1", entries=[]),
                Chapter(name="Chapter 2", entries=[]),
            ],
        )

        assert not book_metadata_only.has_content()
        assert book_metadata_only.is_metadata_only()

        # Test content summary
        summary = book_with_content.get_content_summary()
        assert summary["book_id"] == "content-book"
        assert summary["book_name"] == "Content Book"
        assert summary["total_chapters"] == 2
        assert summary["chapters_with_content"] == 2
        assert summary["total_entries"] == 2
        assert summary["has_content"] is True
        assert summary["is_metadata_only"] is False

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
