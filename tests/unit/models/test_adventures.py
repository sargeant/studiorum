"""Tests for Adventure model."""

import pytest
from pydantic import ValidationError

from dnd5e.core.models.adventures import Adventure, AdventureMetadata
from dnd5e.core.models.chapter import Chapter
from dnd5e.core.models.content import Source


class TestAdventureMetadata:
    """Tests for AdventureMetadata model."""

    def test_metadata_creation(self) -> None:
        """Test basic metadata creation."""
        metadata = AdventureMetadata(
            id="CoS",
            published="2016-03-15",
            storyline="Ravenloft",
            level={"start": 1, "end": 10},
            group="curse-of-strahd",
            cover={"type": "image", "href": "cos-cover.jpg"},
        )

        assert metadata.id == "CoS"
        assert metadata.published == "2016-03-15"
        assert metadata.storyline == "Ravenloft"
        assert metadata.level == {"start": 1, "end": 10}
        assert metadata.group == "curse-of-strahd"
        assert metadata.cover == {"type": "image", "href": "cos-cover.jpg"}

    def test_get_level_range_with_start_end(self) -> None:
        """Test level range formatting with start and end."""
        metadata = AdventureMetadata(level={"start": 3, "end": 7})
        assert metadata.get_level_range() == "Levels 3-7"

    def test_get_level_range_single_level(self) -> None:
        """Test level range formatting with same start and end."""
        metadata = AdventureMetadata(level={"start": 5, "end": 5})
        assert metadata.get_level_range() == "Level 5"

    def test_get_level_range_no_level(self) -> None:
        """Test level range formatting with no level data."""
        metadata = AdventureMetadata()
        assert metadata.get_level_range() == ""

    def test_get_level_range_non_dict(self) -> None:
        """Test level range formatting with non-dict level."""
        # AdventureMetadata expects dict for level, but Adventure allows non-dict
        # This test is more relevant for Adventure.get_level_range()
        pass  # Skip this test as AdventureMetadata enforces dict type


class TestAdventure:
    """Tests for Adventure model."""

    @pytest.fixture
    def sample_source(self) -> Source:
        """Create a sample source."""
        return Source(abbreviation="CoS", name="Curse of Strahd")

    @pytest.fixture
    def sample_chapter(self) -> Chapter:
        """Create a sample chapter."""
        return Chapter(
            name="Chapter 1: Into the Mists",
            entries=[
                "The characters are drawn into Barovia.",
                {
                    "type": "section",
                    "name": "Village of Barovia",
                    "entries": ["A small village..."],
                },
            ],
        )

    @pytest.fixture
    def sample_metadata(self) -> AdventureMetadata:
        """Create sample adventure metadata."""
        return AdventureMetadata(
            id="CoS",
            published="2016-03-15",
            storyline="Ravenloft",
            level={"start": 1, "end": 10},
            group="curse-of-strahd",
        )

    def test_adventure_creation_minimal(self, sample_source: Source) -> None:
        """Test minimal adventure creation."""
        adventure = Adventure(name="Test Adventure", source=sample_source)

        assert adventure.name == "Test Adventure"
        assert adventure.source.abbreviation == "CoS"
        assert adventure.id is None
        assert len(adventure.contents) == 0
        assert adventure.metadata is None

    def test_adventure_creation_full(
        self,
        sample_source: Source,
        sample_chapter: Chapter,
        sample_metadata: AdventureMetadata,
    ) -> None:
        """Test full adventure creation."""
        adventure = Adventure(
            name="Curse of Strahd",
            source=sample_source,
            id="CoS",
            contents=[sample_chapter],
            metadata=sample_metadata,
            published="2016-03-15",
            storyline="Ravenloft",
            level={"start": 1, "end": 10},
        )

        assert adventure.name == "Curse of Strahd"
        assert adventure.id == "CoS"
        assert len(adventure.contents) == 1
        assert adventure.metadata is not None
        assert adventure.published == "2016-03-15"

    def test_adventure_from_metadata_content_structure(self) -> None:
        """Test adventure creation from merged metadata+content structure."""
        data = {
            "name": "Curse of Strahd",
            "id": "CoS",
            "source": {"abbreviation": "CoS", "name": "Curse of Strahd"},
            "published": "2016-03-15",
            "storyline": "Ravenloft",
            "level": {"start": 1, "end": 10},
            "contents": [
                {
                    "name": "Chapter 1: Into the Mists",
                    "entries": [
                        "The characters are drawn into Barovia.",
                        "The mists surround them.",
                    ],
                },
                {
                    "name": "Chapter 2: The Lands of Barovia",
                    "entries": ["Barovia is a realm of terror."],
                },
            ],
        }

        adventure = Adventure.model_validate(data)

        assert adventure.name == "Curse of Strahd"
        assert adventure.id == "CoS"
        assert adventure.storyline == "Ravenloft"
        assert len(adventure.contents) == 2
        assert adventure.contents[0].name == "Chapter 1: Into the Mists"
        assert len(adventure.contents[0].entries) == 2
        assert adventure.has_content()
        assert not adventure.is_metadata_only()

    def test_adventure_from_content_only_structure(self) -> None:
        """Test adventure creation from content-only structure (current 5etools format)."""
        data = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1: The Beginning",
                    "id": "ch1",
                    "entries": [
                        "This is the first chapter.",
                        "It contains important information.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Chapter 2: The Middle",
                    "id": "ch2",
                    "entries": ["This is the second chapter."],
                },
            ]
        }

        adventure = Adventure.model_validate(data)

        assert adventure.name == "Unknown Adventure"  # Default name
        assert adventure.source.abbreviation == "UNK"  # Default source
        assert len(adventure.contents) == 2
        assert adventure.contents[0].name == "Chapter 1: The Beginning"
        assert adventure.contents[0].ordinal is not None
        assert adventure.contents[0].ordinal["identifier"] == "ch1"
        assert len(adventure.contents[0].entries) == 2

    def test_adventure_from_metadata_only_structure(self) -> None:
        """Test adventure creation from metadata-only structure."""
        data = {
            "name": "Curse of Strahd",
            "id": "CoS",
            "source": {"abbreviation": "CoS", "name": "Curse of Strahd"},
            "published": "2016-03-15",
            "contents": [
                {
                    "name": "Chapter 1: Into the Mists",
                    "headers": ["Village of Barovia", "Tser Pool Encampment"],
                },
                {
                    "name": "Chapter 2: The Lands of Barovia",
                    "headers": ["Areas of Barovia", "Random Encounters"],
                },
            ],
        }

        adventure = Adventure.model_validate(data)

        assert adventure.name == "Curse of Strahd"
        assert adventure.id == "CoS"
        assert len(adventure.contents) == 2
        assert adventure.contents[0].name == "Chapter 1: Into the Mists"
        assert len(adventure.contents[0].entries) == 0  # No actual content
        assert not adventure.has_content()
        assert adventure.is_metadata_only()

    def test_id_validation(self) -> None:
        """Test adventure ID validation."""
        # Valid ID
        adventure = Adventure(name="Test", source=Source(abbreviation="TST"), id="CoS")
        assert adventure.id == "CoS"

        # Empty ID should raise validation error
        with pytest.raises(ValidationError, match="Adventure ID cannot be empty"):
            Adventure(name="Test", source=Source(abbreviation="TST"), id="   ")

        # Invalid ID type should raise error
        with pytest.raises(ValidationError, match="Input should be a valid string"):
            Adventure.model_validate(
                {"name": "Test", "source": {"abbreviation": "TST"}, "id": 123}
            )

    def test_level_validation(self) -> None:
        """Test level range validation."""
        # Valid level range
        adventure = Adventure(
            name="Test", source=Source(abbreviation="TST"), level={"start": 1, "end": 5}
        )
        assert adventure.level == {"start": 1, "end": 5}

        # Invalid start level
        with pytest.raises(
            ValidationError, match="Level start must be an integer between 1 and 20"
        ):
            Adventure.model_validate(
                {
                    "name": "Test",
                    "source": {"abbreviation": "TST"},
                    "level": {"start": 0, "end": 5},
                }
            )

        # Invalid end level
        with pytest.raises(
            ValidationError, match="Level end must be an integer between 1 and 20"
        ):
            Adventure.model_validate(
                {
                    "name": "Test",
                    "source": {"abbreviation": "TST"},
                    "level": {"start": 1, "end": 25},
                }
            )

        # Start > end
        with pytest.raises(
            ValidationError, match="Level start cannot be greater than level end"
        ):
            Adventure.model_validate(
                {
                    "name": "Test",
                    "source": {"abbreviation": "TST"},
                    "level": {"start": 10, "end": 5},
                }
            )

    def test_has_content_method(self, sample_source: Source) -> None:
        """Test has_content method."""
        # Adventure with content
        adventure_with_content = Adventure(
            name="Test",
            source=sample_source,
            contents=[Chapter(name="Ch1", entries=["Some content"])],
        )
        assert adventure_with_content.has_content() is True

        # Adventure without content
        adventure_no_content = Adventure(
            name="Test",
            source=sample_source,
            contents=[Chapter(name="Ch1", entries=[])],
        )
        assert adventure_no_content.has_content() is False

        # Adventure with empty contents
        adventure_empty = Adventure(name="Test", source=sample_source, contents=[])
        assert adventure_empty.has_content() is False

    def test_is_metadata_only_method(self, sample_source: Source) -> None:
        """Test is_metadata_only method."""
        # Adventure with content
        adventure_with_content = Adventure(
            name="Test",
            source=sample_source,
            contents=[Chapter(name="Ch1", entries=["Some content"])],
        )
        assert adventure_with_content.is_metadata_only() is False

        # Adventure without content
        adventure_metadata_only = Adventure(
            name="Test",
            source=sample_source,
            contents=[Chapter(name="Ch1", entries=[])],
        )
        assert adventure_metadata_only.is_metadata_only() is True

    def test_get_content_file_path_method(self, sample_source: Source) -> None:
        """Test get_content_file_path method."""
        # Adventure with ID
        adventure_with_id = Adventure(
            name="Curse of Strahd", source=sample_source, id="CoS"
        )
        assert adventure_with_id.get_content_file_path() == "adventure-cos.json"

        # Adventure with complex ID
        adventure_complex_id = Adventure(
            name="Test", source=sample_source, id="DrDe-ACfaS"
        )
        assert (
            adventure_complex_id.get_content_file_path() == "adventure-drdeacfas.json"
        )

        # Adventure without ID
        adventure_no_id = Adventure(name="Test", source=sample_source)
        assert adventure_no_id.get_content_file_path() is None

    def test_get_content_summary_method(self, sample_source: Source) -> None:
        """Test get_content_summary method."""
        adventure = Adventure(
            name="Test Adventure",
            source=sample_source,
            id="TST",
            contents=[
                Chapter(name="Ch1", entries=["content1", "content2"]),
                Chapter(name="Ch2", entries=[]),
                Chapter(name="Ch3", entries=["content3"]),
            ],
        )

        summary = adventure.get_content_summary()

        assert summary["adventure_id"] == "TST"
        assert summary["adventure_name"] == "Test Adventure"
        assert summary["total_chapters"] == 3
        assert summary["chapters_with_content"] == 2
        assert summary["total_entries"] == 3
        assert summary["has_content"] is True
        assert summary["is_metadata_only"] is False
        assert summary["expected_content_file"] == "adventure-tst.json"

    def test_metadata_post_init_creation(self, sample_source: Source) -> None:
        """Test automatic metadata creation in post_init."""
        adventure = Adventure(
            name="Test",
            source=sample_source,
            id="TST",
            published="2023-01-01",
            storyline="Test Campaign",
            level={"start": 1, "end": 5},
        )

        # Metadata should be created automatically
        assert adventure.metadata is not None
        assert adventure.metadata.id == "TST"
        assert adventure.metadata.published == "2023-01-01"
        assert adventure.metadata.storyline == "Test Campaign"
        assert adventure.metadata.level == {"start": 1, "end": 5}

    def test_metadata_field_sync(
        self, sample_source: Source, sample_metadata: AdventureMetadata
    ) -> None:
        """Test metadata field synchronization."""
        adventure = Adventure(
            name="Test", source=sample_source, metadata=sample_metadata
        )

        # Fields should be synced from metadata
        assert adventure.id == "CoS"
        assert adventure.published == "2016-03-15"

    def test_get_level_range_method(self, sample_source: Source) -> None:
        """Test get_level_range method."""
        # With metadata
        adventure_with_metadata = Adventure(
            name="Test",
            source=sample_source,
            metadata=AdventureMetadata(level={"start": 3, "end": 7}),
        )
        assert adventure_with_metadata.get_level_range() == "Levels 3-7"

        # Without metadata but with level field
        adventure_with_level = Adventure(
            name="Test", source=sample_source, level={"start": 5, "end": 5}
        )
        assert adventure_with_level.get_level_range() == "Level 5"

        # No level data
        adventure_no_level = Adventure(name="Test", source=sample_source)
        assert adventure_no_level.get_level_range() == ""

    def test_get_storyline_text_method(self, sample_source: Source) -> None:
        """Test get_storyline_text method."""
        # With metadata
        adventure_with_metadata = Adventure(
            name="Test",
            source=sample_source,
            metadata=AdventureMetadata(storyline="Test Campaign"),
        )
        assert adventure_with_metadata.get_storyline_text() == "Test Campaign"

        # Without metadata but with storyline field
        adventure_with_storyline = Adventure(
            name="Test", source=sample_source, storyline="Direct Storyline"
        )
        assert adventure_with_storyline.get_storyline_text() == "Direct Storyline"

        # No storyline data
        adventure_no_storyline = Adventure(name="Test", source=sample_source)
        assert adventure_no_storyline.get_storyline_text() == ""

    def test_get_chapter_count_method(self, sample_source: Source) -> None:
        """Test get_chapter_count method."""
        adventure = Adventure(
            name="Test",
            source=sample_source,
            contents=[
                Chapter(name="Ch1", entries=[]),
                Chapter(name="Ch2", entries=[]),
                Chapter(name="Ch3", entries=[]),
            ],
        )

        assert adventure.get_chapter_count() == 3

    def test_model_validation_warnings(self, sample_source: Source, caplog) -> None:
        """Test that model validation produces appropriate warnings."""
        import logging

        # Create adventure with conflicting IDs
        adventure = Adventure(
            name="Test",
            source=sample_source,
            id="TST1",
            metadata=AdventureMetadata(id="TST2"),
        )

        # Should log warning about ID mismatch
        with caplog.at_level(logging.WARNING):
            adventure.validate_adventure_structure()

        assert "Adventure ID mismatch" in caplog.text

    def test_has_meaningful_metadata_method(self, sample_source: Source) -> None:
        """Test _has_meaningful_metadata helper method."""
        # Adventure with meaningful metadata
        adventure_meaningful = Adventure(
            name="Test", source=sample_source, id="TST", storyline="Test Campaign"
        )
        assert adventure_meaningful._has_meaningful_metadata() is True

        # Adventure with minimal metadata
        adventure_minimal = Adventure(name="Test", source=sample_source)
        assert adventure_minimal._has_meaningful_metadata() is False

    def test_edge_cases(self, sample_source: Source) -> None:
        """Test edge cases and error conditions."""
        # None source will be replaced with default source by model_validate
        adventure_none_source = Adventure.model_validate(
            {"name": "Test", "source": None}
        )
        assert adventure_none_source.source.abbreviation == "UNK"

        # Valid contents format with missing entries (should default to empty list)
        adventure = Adventure.model_validate(
            {
                "name": "Test",
                "source": {"abbreviation": "TST"},
                "contents": [{"name": "Ch1"}],  # Missing entries
            }
        )
        assert len(adventure.contents) == 1
        assert len(adventure.contents[0].entries) == 0

        # Test that empty name works (BaseContent allows it)
        adventure_empty_name = Adventure(name="", source=sample_source)
        assert adventure_empty_name.name == ""
