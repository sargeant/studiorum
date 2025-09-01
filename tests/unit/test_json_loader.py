"""Tests for JsonDataLoader."""

from pathlib import Path
from typing import Any

import pytest

from studiorum.core.loaders.json_loader import JsonDataLoader
from studiorum.core.models.content import ContentType, Source
from tests.test_helpers import reset_test_environment


class TestJsonDataLoaderBook:
    """Tests for JsonDataLoader book data extraction."""

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

    def _get_content_type(self, type_name: str) -> ContentType:
        """Get ContentType safely, falling back to static enum members."""
        try:
            return ContentType(type_name)
        except ValueError:
            # Fall back to known static enum members
            fallback_map = {
                "spell": ContentType.SPELL,
                "creature": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "adventure": ContentType.ADVENTURE,
                "book": ContentType.BOOK,
                "class": ContentType.CREATURE,  # Fall back to CREATURE for class tests
                "feat": ContentType.CREATURE,  # Fall back to CREATURE for feat tests
            }
            return fallback_map.get(type_name, ContentType.SPELL)  # Default fallback

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook")

    @pytest.fixture
    def sample_path(self) -> Path:
        """Sample path for testing."""
        return Path("/fake/path/book-phb.json")

    def test_extract_content_book_data_format(self, sample_path: Path) -> None:
        """Test _extract_content with 'bookData' key format."""
        data = {"bookData": [{"name": "Chapter 1", "entries": ["Some content"]}]}

        loader = JsonDataLoader(self._get_content_type("book"))
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

        loader = JsonDataLoader(self._get_content_type("book"))
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

        loader = JsonDataLoader(self._get_content_type("book"))
        result = loader._extract_content(data, sample_path)

        # Should still return the structure even if data array is empty
        assert result == []

    def test_extract_content_book_non_list_data(self, sample_path: Path) -> None:
        """Test _extract_content with non-list 'data' value."""
        data = {"data": {"not": "a list"}}

        loader = JsonDataLoader(self._get_content_type("book"))
        result = loader._extract_content(data, sample_path)

        assert result == []

    def test_extract_content_book_no_recognized_keys(self, sample_path: Path) -> None:
        """Test _extract_content with no recognized book keys."""
        data = {"other": "data", "not_book": "related"}

        loader = JsonDataLoader(self._get_content_type("book"))
        result = loader._extract_content(data, sample_path)

        assert result == []

    def test_extract_content_book_priority_order(self, sample_path: Path) -> None:
        """Test that 'book' key takes precedence over other formats."""
        data = {
            "book": [{"name": "Book format"}],
            "bookData": [{"name": "BookData format"}],
            "data": [{"name": "Data format"}],
        }

        loader = JsonDataLoader(self._get_content_type("book"))
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

        loader = JsonDataLoader(self._get_content_type("book"))
        result = loader._extract_content(data, sample_path)

        assert len(result) == 1
        assert result[0]["name"] == "BookData format"


class TestJsonDataLoaderBookIntegration:
    """Integration tests for JsonDataLoader with Book model validation."""

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

    def _get_content_type(self, type_name: str) -> ContentType:
        """Get ContentType safely, falling back to static enum members."""
        try:
            return ContentType(type_name)
        except ValueError:
            # Fall back to known static enum members
            fallback_map = {
                "spell": ContentType.SPELL,
                "creature": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "adventure": ContentType.ADVENTURE,
                "book": ContentType.BOOK,
                "class": ContentType.CREATURE,  # Fall back to CREATURE for class tests
                "feat": ContentType.CREATURE,  # Fall back to CREATURE for feat tests
            }
            return fallback_map.get(type_name, ContentType.SPELL)  # Default fallback

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook")

    def test_5etools_book_format_full_validation(self, sample_source: Any) -> None:
        """Test complete validation of 5etools book format through JsonDataLoader."""
        # Create realistic 5etools book data that conforms to Pydantic Book model
        raw_data = {
            "name": "Test Book",  # Required by Pydantic Book model
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
            ],
        }

        # Create loader and process data
        loader = JsonDataLoader(self._get_content_type("book"))

        # Mock the path for testing
        mock_path = Path("/fake/book-phb.json")

        # Add source info and required fields (simulating the full loader process)
        extracted = loader._extract_content(raw_data, mock_path)
        assert len(extracted) == 1

        book_item = extracted[0]
        book_item = loader._ensure_source_info(book_item, mock_path)
        # Removed deprecated _add_missing_required_fields() call - now handled by Pydantic validation

        # Verify the book data has the structure we expect
        # Note: After Pydantic migration, 'name' field is not automatically added
        # The book data should have source info and the original data structure
        assert "source" in book_item
        assert "data" in book_item

        # The data should contain the nested sections we provided
        assert len(book_item["data"]) == 2
        assert book_item["data"][0]["name"] == "Introduction"
        assert book_item["data"][1]["name"] == "Character Creation"

        # Create the actual Book object
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()
        book = factory.create_content(book_item, self._get_content_type("book"))

        # Verify the book structure
        assert book.name == "Test Book"  # From our test data
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

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

    def _get_content_type(self, type_name: str) -> ContentType:
        """Get ContentType safely, falling back to static enum members."""
        try:
            return ContentType(type_name)
        except ValueError:
            # Fall back to known static enum members
            fallback_map = {
                "spell": ContentType.SPELL,
                "creature": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "adventure": ContentType.ADVENTURE,
                "book": ContentType.BOOK,
                "class": ContentType.CREATURE,  # Fall back to CREATURE for class tests
                "feat": ContentType.CREATURE,  # Fall back to CREATURE for feat tests
            }
            return fallback_map.get(type_name, ContentType.SPELL)  # Default fallback

    @pytest.fixture
    def sample_path(self) -> Path:
        """Sample path for testing."""
        return Path("/fake/path/spells.json")

    # Removed deprecated test: test_add_missing_required_fields_spell_missing_components
    # This tested legacy _add_missing_required_fields() method which is replaced by Pydantic validation

    # Removed deprecated test: test_add_missing_required_fields_spell_all_missing
    # This tested legacy _add_missing_required_fields() method which is replaced by Pydantic validation

    # Removed deprecated test: test_add_missing_required_fields_spell_preserves_existing
    # This tested legacy _add_missing_required_fields() method which is replaced by Pydantic validation

    # Removed deprecated test: test_add_missing_required_fields_spell_with_existing_components
    # This tested legacy _add_missing_required_fields() method which is replaced by Pydantic validation


class TestJsonDataLoaderContentTypeValidation:
    """Tests for JsonDataLoader content type validation to prevent cross-contamination.

    This test class addresses issue #54 where class definitions were being validated
    against the Spell schema instead of the Class schema due to permissive fallback logic.
    """

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

    def _get_content_type(self, type_name: str) -> ContentType:
        """Get ContentType safely, falling back to static enum members."""
        try:
            return ContentType(type_name)
        except ValueError:
            # Fall back to known static enum members
            fallback_map = {
                "spell": ContentType.SPELL,
                "creature": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "adventure": ContentType.ADVENTURE,
                "book": ContentType.BOOK,
                "class": ContentType.CREATURE,  # Fall back to CREATURE for class tests
                "feat": ContentType.CREATURE,  # Fall back to CREATURE for feat tests
            }
            return fallback_map.get(type_name, ContentType.SPELL)  # Default fallback

    @pytest.fixture
    def sample_class_data(self) -> dict[str, Any]:
        """Sample class data from a real 5e.tools file."""
        return {
            "_meta": {
                "sources": [
                    {
                        "json": "TestClass",
                        "abbreviation": "TC",
                        "full": "Test Class",
                        "authors": ["Test Author"],
                        "version": "1.0",
                    }
                ]
            },
            "class": [
                {
                    "name": "Spellblade",
                    "source": "TestClass",
                    "hd": {"number": 1, "faces": 8},
                    "proficiency": ["dex", "int"],
                    "classFeatures": ["Spellblade|TC|1|0", "Fighting Style|TC|2|0"],
                    "hasFluff": True,
                }
            ],
        }

    @pytest.fixture
    def sample_spell_data(self) -> dict[str, Any]:
        """Sample spell data from a real 5e.tools file."""
        return {
            "_meta": {
                "sources": [
                    {
                        "json": "TestSpells",
                        "abbreviation": "TS",
                        "full": "Test Spells",
                        "authors": ["Test Author"],
                        "version": "1.0",
                    }
                ]
            },
            "spell": [
                {
                    "name": "Test Spell",
                    "source": "TestSpells",
                    "level": 1,
                    "school": "A",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {"type": "point", "distance": {"type": "self"}},
                    "components": {"v": True, "s": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["A test spell."],
                }
            ],
        }

    def test_spell_loader_with_spell_data_succeeds(
        self, sample_spell_data: dict[str, Any]
    ) -> None:
        """Test that SPELL loader successfully processes spell data."""
        loader = JsonDataLoader(self._get_content_type("spell"))
        mock_path = Path("/fake/spell-test.json")

        # Extract content
        extracted = loader._extract_content(sample_spell_data, mock_path)
        assert len(extracted) == 1

        # Verify it extracted spell data
        spell_item = extracted[0]
        assert spell_item["name"] == "Test Spell"
        assert "level" in spell_item
        assert "school" in spell_item
        assert "components" in spell_item

    def test_spell_loader_with_class_data_should_fail(
        self, sample_class_data: dict[str, Any]
    ) -> None:
        """Test that SPELL loader should NOT successfully process class data.

        This is the core issue from #54 - spell loaders should not be able to
        process class data through fallback logic and field injection.
        """
        loader = JsonDataLoader(self._get_content_type("spell"))
        mock_path = Path("/fake/class-test.json")

        # This should not find any content since there's no "spell" key
        extracted = loader._extract_content(sample_class_data, mock_path)

        # The spell loader should not extract anything from class data
        # If it does extract content, that's the bug we're fixing
        if extracted:
            # If content is extracted, it should not be valid spell data
            # without the problematic field injection
            class_item = extracted[0]

            # This item should NOT have spell-specific fields unless they were incorrectly added
            assert "level" not in class_item or class_item.get("level") is None
            assert "school" not in class_item or class_item.get("school") is None
            assert (
                "components" not in class_item or class_item.get("components") is None
            )

            # It should still have class-specific fields
            assert "hd" in class_item
            assert "proficiency" in class_item
        else:
            # This is the preferred behavior - no extraction should occur
            assert extracted == []

    # Removed deprecated test: test_spell_loader_does_not_add_fields_to_class_data
    # This tested legacy _add_missing_required_fields() method which is replaced by Pydantic validation

    # Removed deprecated test: test_content_type_specific_field_injection
    # This tested legacy _add_missing_required_fields() method which is replaced by Pydantic validation
