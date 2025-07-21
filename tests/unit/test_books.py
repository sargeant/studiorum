"""Tests for book models."""

from typing import Any

import pytest
from pydantic import ValidationError

from dnd5e.core.models.books import Book, BookChapter, BookMetadata  # type: ignore
from dnd5e.core.models.content import Source  # type: ignore


class TestBookChapter:
    """Tests for BookChapter model."""

    def test_book_chapter_creation_minimal(self) -> None:
        """Test basic BookChapter creation with minimal data."""
        data = {"name": "Introduction"}
        chapter = BookChapter.model_validate(data)

        assert chapter.name == "Introduction"
        assert chapter.ordinal is None
        assert chapter.headers is None
        assert chapter.entries == []

    def test_book_chapter_creation_full(self) -> None:
        """Test BookChapter creation with all fields."""
        data = {
            "name": "Getting Started",
            "ordinal": {"type": "chapter", "identifier": 1},
            "headers": ["Overview", "Prerequisites"],
            "entries": ["Some content", {"type": "table", "data": []}],
        }
        chapter = BookChapter.model_validate(data)

        assert chapter.name == "Getting Started"
        assert chapter.ordinal == {"type": "chapter", "identifier": 1}
        assert chapter.headers == ["Overview", "Prerequisites"]
        assert len(chapter.entries) == 2

    def test_book_chapter_get_chapter_number_chapter(self) -> None:
        """Test get_chapter_number for chapter type."""
        chapter: Any = BookChapter(
            name="Test Chapter", ordinal={"type": "chapter", "identifier": 5}
        )

        result = chapter.get_chapter_number()
        assert result == "Chapter 5"

    def test_book_chapter_get_chapter_number_part(self) -> None:
        """Test get_chapter_number for part type."""
        chapter: Any = BookChapter(
            name="Test Part", ordinal={"type": "part", "identifier": 2}
        )

        result = chapter.get_chapter_number()
        assert result == "Part 2"

    def test_book_chapter_get_chapter_number_appendix(self) -> None:
        """Test get_chapter_number for appendix type."""
        chapter: Any = BookChapter(
            name="Test Appendix", ordinal={"type": "appendix", "identifier": 3}
        )

        result = chapter.get_chapter_number()
        assert result == "Appendix 3"

    def test_book_chapter_get_chapter_number_unknown_type(self) -> None:
        """Test get_chapter_number for unknown type."""
        chapter: Any = BookChapter(
            name="Test Section", ordinal={"type": "section", "identifier": 7}
        )

        result = chapter.get_chapter_number()
        assert result == "7"

    def test_book_chapter_get_chapter_number_no_ordinal(self) -> None:
        """Test get_chapter_number with no ordinal data."""
        chapter: Any = BookChapter(name="Test Chapter")

        result = chapter.get_chapter_number()
        assert result == ""

    def test_book_chapter_get_chapter_number_missing_fields(self) -> None:
        """Test get_chapter_number with incomplete ordinal data."""
        # Missing identifier - falls back to str(ordinal)
        chapter: Any = BookChapter(name="Test Chapter", ordinal={"type": "chapter"})
        result = chapter.get_chapter_number()
        assert result == "{'type': 'chapter'}"

        # Missing type - uses default "chapter" but has identifier
        chapter2: Any = BookChapter(name="Test Chapter", ordinal={"identifier": 1})
        result = chapter2.get_chapter_number()
        assert result == "Chapter 1"

    def test_book_chapter_get_chapter_number_various_identifiers(self) -> None:
        """Test get_chapter_number with various identifier types."""
        test_cases = [
            ("chapter", 1, "Chapter 1"),
            ("chapter", 10, "Chapter 10"),
            ("part", 1, "Part 1"),
            ("part", 5, "Part 5"),
            ("appendix", 1, "Appendix 1"),
            ("appendix", "A", "Appendix A"),
            ("section", 3, "3"),
            ("unknown", 42, "42"),
        ]

        for ordinal_type, identifier, expected in test_cases:
            chapter: Any = BookChapter(
                name=f"Test {ordinal_type}",
                ordinal={"type": ordinal_type, "identifier": identifier},
            )
            result = chapter.get_chapter_number()
            assert result == expected

    def test_book_chapter_get_formatted_headers_strings(self) -> None:
        """Test get_formatted_headers with string headers."""
        chapter: Any = BookChapter(
            name="Test Chapter", headers=["Introduction", "Overview", "Getting Started"]
        )

        result = chapter.get_formatted_headers()
        assert result == ["Introduction", "Overview", "Getting Started"]

    def test_book_chapter_get_formatted_headers_dicts(self) -> None:
        """Test get_formatted_headers with dict headers."""
        chapter: Any = BookChapter(
            name="Test Chapter",
            headers=[
                {"type": "section", "header": "Overview"},
                {"type": "subsection", "header": "Details", "entries": []},
                {"header": "Summary"},
            ],
        )

        result = chapter.get_formatted_headers()
        assert result == ["Overview", "Details", "Summary"]

    def test_book_chapter_get_formatted_headers_mixed(self) -> None:
        """Test get_formatted_headers with mixed string/dict headers."""
        chapter: Any = BookChapter(
            name="Test Chapter",
            headers=[
                "Introduction",
                {"header": "Overview"},
                "Conclusion",
                {"type": "section", "header": "Details"},
            ],
        )

        result = chapter.get_formatted_headers()
        assert result == ["Introduction", "Overview", "Conclusion", "Details"]

    def test_book_chapter_get_formatted_headers_no_headers(self) -> None:
        """Test get_formatted_headers with no headers."""
        chapter: Any = BookChapter(name="Test Chapter")

        result = chapter.get_formatted_headers()
        assert result == []

    def test_book_chapter_get_formatted_headers_empty_headers(self) -> None:
        """Test get_formatted_headers with empty headers list."""
        chapter: Any = BookChapter(name="Test Chapter", headers=[])

        result = chapter.get_formatted_headers()
        assert result == []

    def test_book_chapter_get_formatted_headers_dict_without_header(self) -> None:
        """Test get_formatted_headers with dict headers missing header field."""
        chapter: Any = BookChapter(
            name="Test Chapter",
            headers=[
                {"type": "section", "entries": []},
                {"header": "Valid Header"},
                {"other_field": "value"},
            ],
        )

        result = chapter.get_formatted_headers()
        # Should convert dict without "header" to string representation
        expected = [
            "{'type': 'section', 'entries': []}",
            "Valid Header",
            "{'other_field': 'value'}",
        ]
        assert result == expected

    def test_book_chapter_parse_headers_validator_with_dict_extraction(self) -> None:
        """Test parse_headers validator extracts header fields from dicts."""
        data = {
            "name": "Test Chapter",
            "headers": [
                {"header": "Header 1"},
                {"header": "Header 2", "other": "data"},
                {"no_header": "value"},
            ],
        }
        chapter = BookChapter.model_validate(data)

        # Validator should extract "header" fields and convert others to string
        assert chapter.headers == ["Header 1", "Header 2", "{'no_header': 'value'}"]

    def test_book_chapter_parse_headers_validator_list(self) -> None:
        """Test parse_headers validator with list input."""
        data = {"name": "Test Chapter", "headers": ["Header 1", "Header 2"]}
        chapter = BookChapter.model_validate(data)

        assert chapter.headers == ["Header 1", "Header 2"]

    def test_book_chapter_validation_name_required(self) -> None:
        """Test that name field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BookChapter.model_validate({})

        assert "name" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)


class TestBookMetadata:
    """Tests for BookMetadata model."""

    def test_book_metadata_creation_empty(self) -> None:
        """Test BookMetadata creation with no fields."""
        metadata = BookMetadata.model_validate({})

        assert metadata.id is None
        assert metadata.published is None
        assert metadata.author is None
        assert metadata.contents is None
        assert metadata.cover is None

    def test_book_metadata_creation_full(self) -> None:
        """Test BookMetadata creation with all fields."""
        data = {
            "id": "phb-2024",
            "published": "2024-01-01",
            "author": ["Mike Mearls", "Jeremy Crawford"],
            "contents": [{"name": "Chapter 1", "page": 1}],
            "cover": {"url": "cover.jpg", "width": 400, "height": 600},
        }
        metadata = BookMetadata.model_validate(data)

        assert metadata.id == "phb-2024"
        assert metadata.published == "2024-01-01"
        assert metadata.author == ["Mike Mearls", "Jeremy Crawford"]
        assert metadata.contents == [{"name": "Chapter 1", "page": 1}]
        assert metadata.cover == {"url": "cover.jpg", "width": 400, "height": 600}

    def test_book_metadata_get_authors_text_single_author(self) -> None:
        """Test get_authors_text with single author."""
        metadata: Any = BookMetadata(author=["John Smith"])

        result = metadata.get_authors_text()
        assert result == "John Smith"

    def test_book_metadata_get_authors_text_two_authors(self) -> None:
        """Test get_authors_text with two authors."""
        metadata: Any = BookMetadata(author=["John Smith", "Jane Doe"])

        result = metadata.get_authors_text()
        assert result == "John Smith and Jane Doe"

    def test_book_metadata_get_authors_text_three_authors(self) -> None:
        """Test get_authors_text with three authors."""
        metadata: Any = BookMetadata(author=["John Smith", "Jane Doe", "Bob Johnson"])

        result = metadata.get_authors_text()
        assert result == "John Smith, Jane Doe, and Bob Johnson"

    def test_book_metadata_get_authors_text_four_authors(self) -> None:
        """Test get_authors_text with four authors."""
        metadata: Any = BookMetadata(
            author=["John Smith", "Jane Doe", "Bob Johnson", "Alice Brown"]
        )

        result = metadata.get_authors_text()
        assert result == "John Smith, Jane Doe, Bob Johnson, and Alice Brown"

    def test_book_metadata_get_authors_text_no_authors(self) -> None:
        """Test get_authors_text with no authors."""
        metadata: Any = BookMetadata()

        result = metadata.get_authors_text()
        assert result == ""

    def test_book_metadata_get_authors_text_empty_list(self) -> None:
        """Test get_authors_text with empty author list."""
        metadata: Any = BookMetadata(author=[])

        result = metadata.get_authors_text()
        assert result == ""

    def test_book_metadata_parse_author_string_input(self) -> None:
        """Test parse_author validator with string input."""
        data = {"author": "Single Author"}
        metadata = BookMetadata.model_validate(data)

        assert metadata.author == ["Single Author"]

    def test_book_metadata_parse_author_list_input(self) -> None:
        """Test parse_author validator with list input."""
        data = {"author": ["Author 1", "Author 2"]}
        metadata = BookMetadata.model_validate(data)

        assert metadata.author == ["Author 1", "Author 2"]

    def test_book_metadata_parse_author_none_input(self) -> None:
        """Test parse_author validator with None input."""
        data = {"author": None}
        metadata = BookMetadata.model_validate(data)

        assert metadata.author is None


class TestBook:
    """Tests for Book model."""

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook")

    @pytest.fixture
    def sample_chapter_data(self) -> Any:
        """Sample chapter data for testing."""
        return {
            "name": "Introduction",
            "ordinal": {"type": "chapter", "identifier": 1},
            "headers": ["Overview", "Getting Started"],
            "entries": ["Welcome to D&D!"],
        }

    @pytest.fixture
    def sample_metadata_data(self) -> Any:
        """Sample metadata for testing."""
        return {
            "id": "phb-2024",
            "published": "2024-01-01",
            "author": ["Mike Mearls", "Jeremy Crawford"],
            "cover": {"url": "cover.jpg"},
        }

    def test_book_creation_minimal(self, sample_source: Any) -> None:
        """Test Book creation with minimal required data."""
        data = {"name": "Player's Handbook", "source": sample_source}
        book = Book.model_validate(data)

        assert book.name == "Player's Handbook"
        assert book.source == sample_source
        assert book.id is None
        assert book.contents == []
        assert book.metadata is None
        assert book.published is None
        assert book.author is None
        assert book.cover is None

    def test_book_creation_with_chapters(
        self, sample_source: Any, sample_chapter_data: Any
    ) -> None:
        """Test Book creation with chapters."""
        data = {
            "name": "Player's Handbook",
            "source": sample_source,
            "contents": [sample_chapter_data],
        }
        book = Book.model_validate(data)

        assert book.name == "Player's Handbook"
        assert len(book.contents) == 1
        assert isinstance(book.contents[0], BookChapter)
        assert book.contents[0].name == "Introduction"

    def test_book_creation_with_metadata(
        self, sample_source: Any, sample_metadata_data: Any
    ) -> None:
        """Test Book creation with metadata."""
        data = {
            "name": "Player's Handbook",
            "source": sample_source,
            "metadata": sample_metadata_data,
        }
        book = Book.model_validate(data)

        assert book.name == "Player's Handbook"
        assert isinstance(book.metadata, BookMetadata)
        assert book.metadata.id == "phb-2024"
        assert book.metadata.author == ["Mike Mearls", "Jeremy Crawford"]

    def test_book_creation_with_individual_metadata_fields(
        self, sample_source: Any
    ) -> None:
        """Test Book creation with individual metadata fields."""
        data = {
            "name": "Player's Handbook",
            "source": sample_source,
            "id": "phb-2024",
            "published": "2024-01-01",
            "author": ["Mike Mearls", "Jeremy Crawford"],
            "cover": {"url": "cover.jpg"},
        }
        book = Book.model_validate(data)

        assert book.name == "Player's Handbook"
        assert book.id == "phb-2024"
        assert book.published == "2024-01-01"
        assert book.author == ["Mike Mearls", "Jeremy Crawford"]
        assert book.cover == {"url": "cover.jpg"}

        # Should auto-create metadata in post_init
        assert book.metadata is not None
        assert isinstance(book.metadata, BookMetadata)
        assert book.metadata.id == "phb-2024"
        assert book.metadata.published == "2024-01-01"
        assert book.metadata.author == ["Mike Mearls", "Jeremy Crawford"]
        assert book.metadata.cover == {"url": "cover.jpg"}

    def test_book_model_post_init_no_metadata_creation(
        self, sample_source: Any, sample_metadata_data: Any
    ) -> None:
        """Test that model_post_init doesn't create metadata when it already exists."""
        data = {
            "name": "Player's Handbook",
            "source": sample_source,
            "metadata": sample_metadata_data,
            "id": "different-id",  # Should be ignored since metadata exists
            "author": ["Different Author"],
        }
        book = Book.model_validate(data)

        # Should keep original metadata, not create new one
        assert book.metadata.id == "phb-2024"
        assert book.metadata.author == ["Mike Mearls", "Jeremy Crawford"]
        assert book.id == "different-id"  # Individual field should still be set
        assert book.author == ["Different Author"]

    def test_book_model_post_init_partial_metadata_creation(
        self, sample_source: Any
    ) -> None:
        """Test model_post_init creates metadata from partial fields."""
        data = {
            "name": "Player's Handbook",
            "source": sample_source,
            "published": "2024-01-01",
            "author": ["Mike Mearls"],
            # No id or cover
        }
        book = Book.model_validate(data)

        assert book.metadata is not None
        assert book.metadata.published == "2024-01-01"
        assert book.metadata.author == ["Mike Mearls"]
        assert book.metadata.id is None
        assert book.metadata.cover is None

    def test_book_get_chapter_count_zero(self, sample_source: Any) -> None:
        """Test get_chapter_count with no chapters."""
        book: Any = Book(name="Empty Book", source=sample_source)

        result = book.get_chapter_count()
        assert result == 0

    def test_book_get_chapter_count_multiple(self, sample_source: Any) -> None:
        """Test get_chapter_count with multiple chapters."""
        chapters = [
            BookChapter(name="Chapter 1"),
            BookChapter(name="Chapter 2"),
            BookChapter(name="Chapter 3"),
        ]
        book: Any = Book(
            name="Multi-Chapter Book", source=sample_source, contents=chapters
        )

        result = book.get_chapter_count()
        assert result == 3

    def test_book_get_authors_text_from_metadata(self, sample_source: Any) -> None:
        """Test get_authors_text when metadata exists."""
        metadata: Any = BookMetadata(author=["John Smith", "Jane Doe"])
        book: Any = Book(name="Test Book", source=sample_source, metadata=metadata)

        result = book.get_authors_text()
        assert result == "John Smith and Jane Doe"

    def test_book_get_authors_text_fallback_to_individual(
        self, sample_source: Any
    ) -> None:
        """Test get_authors_text fallback when no metadata."""
        book: Any = Book(
            name="Test Book", source=sample_source, author=["Individual Author"]
        )

        result = book.get_authors_text()
        assert result == "Individual Author"

    def test_book_get_authors_text_no_authors(self, sample_source: Any) -> None:
        """Test get_authors_text with no authors anywhere."""
        book: Any = Book(name="Test Book", source=sample_source)

        result = book.get_authors_text()
        assert result == ""

    def test_book_get_authors_text_metadata_takes_precedence(
        self, sample_source: Any
    ) -> None:
        """Test that metadata authors take precedence over individual field."""
        metadata: Any = BookMetadata(author=["Metadata Author"])
        book: Any = Book(
            name="Test Book",
            source=sample_source,
            metadata=metadata,
            author=["Individual Author"],  # Should be ignored
        )

        result = book.get_authors_text()
        assert result == "Metadata Author"

    def test_book_parse_author_string_input(self, sample_source: Any) -> None:
        """Test parse_author validator with string input."""
        data = {"name": "Test Book", "source": sample_source, "author": "Single Author"}
        book = Book.model_validate(data)

        assert book.author == ["Single Author"]

    def test_book_parse_author_list_input(self, sample_source: Any) -> None:
        """Test parse_author validator with list input."""
        data = {
            "name": "Test Book",
            "source": sample_source,
            "author": ["Author 1", "Author 2"],
        }
        book = Book.model_validate(data)

        assert book.author == ["Author 1", "Author 2"]

    def test_book_inheritance_from_base_content(self, sample_source: Any) -> None:
        """Test that Book properly inherits from BaseContent."""
        book: Any = Book(name="Test Book", source=sample_source)

        # Should have BaseContent properties
        assert hasattr(book, "name")
        assert hasattr(book, "source")
        assert book.name == "Test Book"
        assert book.source == sample_source

    def test_book_validation_name_required(self, sample_source: Any) -> None:
        """Test that name field is required (inherited from BaseContent)."""
        with pytest.raises(ValidationError) as exc_info:
            Book.model_validate({"source": sample_source})

        assert "name" in str(exc_info.value)

    def test_book_validation_source_required(self) -> None:
        """Test that source field is required (inherited from BaseContent)."""
        with pytest.raises(ValidationError) as exc_info:
            Book.model_validate({"name": "Test Book"})

        assert "source" in str(exc_info.value)


class TestBookIntegration:
    """Integration tests for book models working together."""

    @pytest.fixture
    def complex_book_data(self) -> Any:
        """Complex book data for integration testing."""
        return {
            "name": "Player's Handbook",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
            "id": "phb-2024",
            "published": "2024-01-01",
            "author": ["Mike Mearls", "Jeremy Crawford", "Chris Perkins"],
            "cover": {"url": "phb_cover.jpg", "width": 400, "height": 600},
            "contents": [
                {
                    "name": "Introduction",
                    "ordinal": {"type": "chapter", "identifier": 1},
                    "headers": ["What Is D&D?", "How to Play", "The Three Pillars"],
                    "entries": [
                        "Welcome to Dungeons & Dragons!",
                        {"type": "section", "name": "Getting Started", "entries": []},
                    ],
                },
                {
                    "name": "Races",
                    "ordinal": {"type": "chapter", "identifier": 2},
                    "headers": ["Choosing a Race", "Human", "Elf", "Dwarf"],
                    "entries": ["Character races provide variety..."],
                },
                {
                    "name": "Spells",
                    "ordinal": {"type": "appendix", "identifier": 1},
                    "headers": ["Spell Lists", "Spell Descriptions"],
                    "entries": ["This appendix contains spells..."],
                },
            ],
            "metadata": {
                "id": "phb-meta-2024",  # Different from book id
                "published": "2024-01-15",  # Different from book published
                "author": ["Meta Author"],  # Different from book author
                "contents": [
                    {"name": "Chapter 1: Introduction", "page": 5},
                    {"name": "Chapter 2: Races", "page": 15},
                    {"name": "Appendix A: Spells", "page": 200},
                ],
                "cover": {"url": "meta_cover.jpg"},
            },
        }

    def test_complex_book_creation(self, complex_book_data: Any) -> None:
        """Test creation of complex book with all features."""
        book = Book.model_validate(complex_book_data)

        # Basic book properties
        assert book.name == "Player's Handbook"
        assert book.source.abbreviation == "PHB"
        assert book.id == "phb-2024"
        assert len(book.author) == 3

        # Chapters
        assert len(book.contents) == 3
        assert all(isinstance(chapter, BookChapter) for chapter in book.contents)

        # First chapter
        intro = book.contents[0]
        assert intro.name == "Introduction"
        assert intro.get_chapter_number() == "Chapter 1"
        assert len(intro.get_formatted_headers()) == 3

        # Appendix chapter
        spells = book.contents[2]
        assert spells.name == "Spells"
        assert spells.get_chapter_number() == "Appendix 1"

        # Metadata (should use provided metadata, not auto-created)
        assert book.metadata is not None
        assert book.metadata.id == "phb-meta-2024"  # From metadata, not book
        assert book.metadata.author == ["Meta Author"]  # From metadata
        assert len(book.metadata.contents) == 3

    def test_book_chapter_count_complex(self, complex_book_data: Any) -> None:
        """Test chapter count with complex book."""
        book = Book.model_validate(complex_book_data)

        assert book.get_chapter_count() == 3

    def test_book_authors_text_with_metadata_precedence(
        self, complex_book_data: Any
    ) -> None:
        """Test that metadata authors take precedence."""
        book = Book.model_validate(complex_book_data)

        # Should use metadata author, not book author
        result = book.get_authors_text()
        assert result == "Meta Author"

    def test_round_trip_serialization(self, complex_book_data: Any) -> None:
        """Test that book can be serialized and deserialized."""
        # Create book from data
        original_book = Book.model_validate(complex_book_data)

        # Serialize to dict
        serialized = original_book.model_dump()

        # Deserialize back to book
        recreated_book = Book.model_validate(serialized)

        # Verify key properties are preserved
        assert recreated_book.name == original_book.name
        assert recreated_book.source.abbreviation == original_book.source.abbreviation
        assert len(recreated_book.contents) == len(original_book.contents)
        assert recreated_book.get_chapter_count() == original_book.get_chapter_count()
        assert recreated_book.get_authors_text() == original_book.get_authors_text()

        # Verify chapter details
        for i, (orig_ch, new_ch) in enumerate(
            zip(original_book.contents, recreated_book.contents, strict=False)
        ):
            assert new_ch.name == orig_ch.name
            assert new_ch.get_chapter_number() == orig_ch.get_chapter_number()
            assert new_ch.get_formatted_headers() == orig_ch.get_formatted_headers()

    def test_book_without_metadata_auto_creation(self) -> None:
        """Test book with individual fields creates metadata automatically."""
        data = {
            "name": "Simple Book",
            "source": {"abbreviation": "SB", "name": "Simple Book"},
            "published": "2024-01-01",
            "author": "Solo Author",
            "contents": [{"name": "Only Chapter", "entries": ["Some content"]}],
        }
        book = Book.model_validate(data)

        # Should auto-create metadata
        assert book.metadata is not None
        assert book.metadata.published == "2024-01-01"
        assert book.metadata.author == ["Solo Author"]  # Converted to list

        # Book fields should also be set
        assert book.published == "2024-01-01"
        assert book.author == ["Solo Author"]

        # Authors text should work via metadata
        assert book.get_authors_text() == "Solo Author"
