"""Tests for JsonDataLoader."""

from pathlib import Path
from typing import Any

import pytest

from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.models.content import ContentType, Source


class TestJsonDataLoaderBook:
    """Tests for JsonDataLoader book data extraction."""

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook")

    @pytest.fixture
    def sample_path(self) -> Path:
        """Sample path for testing."""
        return Path("/fake/path/book-phb.json")

    def test_extract_content_book_legacy_format(self, sample_path: Path) -> None:
        """Test _extract_content with legacy 'book' key format."""
        data = {"book": [{"name": "Chapter 1", "entries": ["Some content"]}]}

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        assert len(result) == 1
        assert result[0]["name"] == "Chapter 1"
        assert result[0]["entries"] == ["Some content"]

    def test_extract_content_book_data_format(self, sample_path: Path) -> None:
        """Test _extract_content with 'bookData' key format."""
        data = {"bookData": [{"name": "Chapter 1", "entries": ["Some content"]}]}

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        assert len(result) == 1
        assert result[0]["name"] == "Chapter 1"
        assert result[0]["entries"] == ["Some content"]

    def test_extract_content_book_5etools_data_format(self, sample_path: Path) -> None:
        """Test _extract_content with 5etools 'data' array format."""
        data = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "page": 5,
                    "entries": [
                        "The Dungeons & Dragons roleplaying game is about storytelling in worlds of swords and sorcery.",
                        {
                            "type": "insetReadaloud",
                            "entries": ["Sample read-aloud text."],
                        },
                    ],
                },
                {
                    "type": "section",
                    "name": "Character Creation",
                    "page": 10,
                    "entries": [
                        "Your first step in playing an adventurer is to create a character."
                    ],
                },
            ]
        }

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        # Should return single book structure with data array intact
        assert len(result) == 1
        book_data = result[0]
        assert "data" in book_data
        assert len(book_data["data"]) == 2

        # First section in data array
        first_section = book_data["data"][0]
        assert first_section["type"] == "section"
        assert first_section["name"] == "Introduction"
        assert first_section["page"] == 5
        assert len(first_section["entries"]) == 2
        assert "storytelling" in first_section["entries"][0]

        # Second section in data array
        second_section = book_data["data"][1]
        assert second_section["type"] == "section"
        assert second_section["name"] == "Character Creation"
        assert second_section["page"] == 10
        assert len(second_section["entries"]) == 1
        assert "adventurer" in second_section["entries"][0]

    def test_extract_content_book_empty_data_array(self, sample_path: Path) -> None:
        """Test _extract_content with empty 'data' array."""
        data = {"data": []}

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        # Should still return the structure even if data array is empty
        assert result == []

    def test_extract_content_book_non_list_data(self, sample_path: Path) -> None:
        """Test _extract_content with non-list 'data' value."""
        data = {"data": {"not": "a list"}}

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        assert result == []

    def test_extract_content_book_no_recognized_keys(self, sample_path: Path) -> None:
        """Test _extract_content with no recognized book keys."""
        data = {"other": "data", "not_book": "related"}

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        assert result == []

    def test_extract_content_book_priority_order(self, sample_path: Path) -> None:
        """Test that 'book' key takes precedence over other formats."""
        data = {
            "book": [{"name": "Book format"}],
            "bookData": [{"name": "BookData format"}],
            "data": [{"name": "Data format"}],
        }

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        assert len(result) == 1
        assert result[0]["name"] == "Book format"

    def test_extract_content_book_data_precedence_over_book_data(
        self, sample_path: Path
    ) -> None:
        """Test that 'bookData' takes precedence over 'data' format."""
        data = {
            "bookData": [{"name": "BookData format"}],
            "data": [{"name": "Data format"}],
        }

        loader = JsonDataLoader(ContentType.BOOK)
        result = loader._extract_content(data, sample_path)

        assert len(result) == 1
        assert result[0]["name"] == "BookData format"


class TestJsonDataLoaderBookIntegration:
    """Integration tests for JsonDataLoader with Book model validation."""

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook")

    def test_5etools_book_format_full_validation(self, sample_source: Any) -> None:
        """Test complete validation of 5etools book format through JsonDataLoader."""
        # Create realistic 5etools book data
        raw_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "page": 5,
                    "entries": [
                        "Welcome to D&D!",
                        {
                            "type": "insetReadaloud",
                            "entries": ["Sample read-aloud text"],
                        },
                    ],
                },
                {
                    "type": "section",
                    "name": "Character Creation",
                    "page": 10,
                    "ordinal": {"type": "chapter", "identifier": 1},
                    "headers": ["Step 1", "Step 2"],
                    "entries": ["Create your character..."],
                },
            ]
        }

        # Create loader and process data
        loader = JsonDataLoader(ContentType.BOOK)

        # Mock the path for testing
        mock_path = Path("/fake/book-phb.json")

        # Add source info and required fields (simulating the full loader process)
        extracted = loader._extract_content(raw_data, mock_path)
        assert len(extracted) == 1

        book_item = extracted[0]
        book_item = loader._ensure_source_info(book_item, mock_path)
        book_item = loader._add_missing_required_fields(book_item)

        # Verify the book data has required fields
        assert "name" in book_item
        assert "source" in book_item
        assert "data" in book_item

        # Create the actual Book object
        from dnd5e.core.loaders.content_factory import get_content_factory

        factory = get_content_factory()
        book = factory.create_content(book_item, ContentType.BOOK)

        # Verify the book structure
        assert book.name == "Player's Handbook"  # From name mapping
        assert book.source.abbreviation == "PHB"
        assert len(book.contents) == 2  # Two chapters from data array

        # Check first chapter
        intro_chapter = book.contents[0]
        assert intro_chapter.name == "Introduction"
        assert len(intro_chapter.entries) == 2  # This should now work!
        assert intro_chapter.entries[0] == "Welcome to D&D!"
        assert isinstance(intro_chapter.entries[1], dict)

        # Check second chapter
        creation_chapter = book.contents[1]
        assert creation_chapter.name == "Character Creation"
        assert len(creation_chapter.entries) == 1
        assert creation_chapter.entries[0] == "Create your character..."
        assert creation_chapter.ordinal == {"type": "chapter", "identifier": 1}
        assert creation_chapter.headers == ["Step 1", "Step 2"]


class TestJsonDataLoaderSpell:
    """Tests for JsonDataLoader spell handling with missing required fields."""

    @pytest.fixture
    def sample_path(self) -> Path:
        """Sample path for testing."""
        return Path("/fake/path/spells.json")

    def test_add_missing_required_fields_spell_missing_components(self) -> None:
        """Test that missing components field gets default empty SpellComponent."""
        spell_data = {
            "name": "Test Spell",
            "level": 1,
            "school": "A",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "self"}},
            "duration": [{"type": "instant"}],
            "entries": ["A test spell."],
            "source": "TST",
            # Missing components field
        }

        loader = JsonDataLoader(ContentType.SPELL)
        result = loader._add_missing_required_fields(spell_data)

        assert "components" in result
        assert (
            result["components"] == {}
        )  # Should be empty dict for SpellComponent defaults

    def test_add_missing_required_fields_spell_all_missing(self) -> None:
        """Test that spell with only name gets all required fields with defaults."""
        spell_data = {
            "name": "Incomplete Spell",
            "source": "TST",
        }

        loader = JsonDataLoader(ContentType.SPELL)
        result = loader._add_missing_required_fields(spell_data)

        # Check all required fields have defaults
        assert result["components"] == {}
        assert result["level"] == 0  # Cantrip
        assert result["school"] == "T"  # Transmutation
        assert result["time"] == [{"number": 1, "unit": "action"}]
        assert result["range"] == {"type": "point", "distance": {"type": "self"}}
        assert result["duration"] == [{"type": "instant"}]
        assert result["entries"] == ["Incomplete spell data."]

    def test_add_missing_required_fields_spell_preserves_existing(self) -> None:
        """Test that existing spell fields are preserved when adding defaults."""
        spell_data = {
            "name": "Partial Spell",
            "level": 3,
            "school": "E",
            "source": "TST",
            # Missing: components, time, range, duration, entries
        }

        loader = JsonDataLoader(ContentType.SPELL)
        result = loader._add_missing_required_fields(spell_data)

        # Existing fields should be preserved
        assert result["name"] == "Partial Spell"
        assert result["level"] == 3
        assert result["school"] == "E"
        assert result["source"] == "TST"

        # Missing fields should have defaults
        assert result["components"] == {}
        assert result["time"] == [{"number": 1, "unit": "action"}]
        assert result["range"] == {"type": "point", "distance": {"type": "self"}}
        assert result["duration"] == [{"type": "instant"}]
        assert result["entries"] == ["Incomplete spell data."]

    def test_add_missing_required_fields_spell_with_existing_components(self) -> None:
        """Test that existing components field is not overridden."""
        spell_data = {
            "name": "Complete Spell",
            "level": 2,
            "school": "C",
            "components": {"v": True, "s": True, "m": "a piece of string"},
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "touch"}},
            "duration": [
                {"type": "timed", "duration": {"type": "minute", "amount": 10}}
            ],
            "entries": ["A complete spell description."],
            "source": "TST",
        }

        loader = JsonDataLoader(ContentType.SPELL)
        result = loader._add_missing_required_fields(spell_data)

        # All original data should be preserved
        assert result == spell_data
        assert result["components"] == {"v": True, "s": True, "m": "a piece of string"}
