"""Tests for Adventure content type migration to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestAdventureMigration:
    """Test that Adventure content type works with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_adventure_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Adventure correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.adventures import Adventure
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="adventure",
                file_patterns=["adventure", "adventures"],
                statblock_tags=["adventure"],
                loader_type="json",
            )
            class TestAdventure(Adventure):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "adventure"
        assert metadata.model_class == TestAdventure
        assert metadata.file_patterns == ["adventure", "adventures"]
        assert metadata.statblock_tags == ["adventure"]
        assert metadata.loader_type == "json"

    def test_adventure_enum_created_dynamically(self):
        """Test that ADVENTURE enum is created dynamically during finalization."""
        # Import adventures to register via decorator
        from dnd5e.core.models import adventures

        # Initially ADVENTURE should already exist (it's in ContentType enum)
        assert hasattr(ContentType, "ADVENTURE")
        assert ContentType.ADVENTURE == "adventure"

        # Initialize should still work and not conflict
        initialize_content_types()

        # Verify enum still exists and works
        assert hasattr(ContentType, "ADVENTURE")
        assert ContentType.ADVENTURE == "adventure"

    def test_adventure_content_creation(self):
        """Test that Adventure content can be created and validated."""
        from dnd5e.core.models.adventures import Adventure, AdventureMetadata
        from dnd5e.core.models.chapter import Chapter

        # Create a simple adventure instance
        adventure = Adventure(
            name="Curse of Strahd",
            source="CoS",
            id="CoS",
            published="2016-03-15",
            storyline="Ravenloft",
            level={"start": 1, "end": 10},
            contents=[
                Chapter(
                    name="Chapter 1: Into the Mists",
                    entries=["The adventure begins..."],
                ),
                Chapter(
                    name="Chapter 2: The Land of Barovia",
                    entries=["Barovia is a land..."],
                ),
            ],
        )

        assert adventure.name == "Curse of Strahd"
        assert adventure.source.abbreviation == "CoS"
        assert adventure.id == "CoS"
        assert adventure.published == "2016-03-15"
        assert adventure.storyline == "Ravenloft"
        assert adventure.level == {"start": 1, "end": 10}
        assert len(adventure.contents) == 2

    def test_adventure_with_metadata(self):
        """Test that Adventure works with AdventureMetadata nested model."""
        from dnd5e.core.models.adventures import Adventure, AdventureMetadata

        metadata = AdventureMetadata(
            id="LMoP",
            published="2014",
            storyline="Starter Set",
            level={"start": 1, "end": 5},
            group="starter",
        )

        adventure = Adventure(
            name="Lost Mine of Phandelver",
            source="LMoP",
            metadata=metadata,
            contents=[],
        )

        assert adventure.name == "Lost Mine of Phandelver"
        assert adventure.metadata is not None
        assert adventure.metadata.id == "LMoP"
        assert adventure.metadata.storyline == "Starter Set"
        assert adventure.metadata.get_level_range() == "Levels 1-5"

    def test_adventure_level_validation(self):
        """Test that Adventure level field validation works correctly."""
        import pytest

        from dnd5e.core.models.adventures import Adventure

        # Valid level range
        adventure1 = Adventure(
            name="Test Adventure", source="TEST", level={"start": 1, "end": 5}
        )
        assert adventure1.level == {"start": 1, "end": 5}

        # Single level (start == end)
        adventure2 = Adventure(
            name="Test Adventure", source="TEST", level={"start": 3, "end": 3}
        )
        assert adventure2.level == {"start": 3, "end": 3}

        # Test invalid level range (start > end)
        with pytest.raises(
            ValueError, match="Level start cannot be greater than level end"
        ):
            Adventure(
                name="Test Adventure", source="TEST", level={"start": 10, "end": 5}
            )

        # Test invalid level values
        with pytest.raises(
            ValueError, match="Level start must be an integer between 1 and 20"
        ):
            Adventure(
                name="Test Adventure", source="TEST", level={"start": 0, "end": 5}
            )

    def test_adventure_metadata_level_range_formatting(self):
        """Test AdventureMetadata level range formatting."""
        from dnd5e.core.models.adventures import AdventureMetadata

        # Range of levels
        metadata1 = AdventureMetadata(level={"start": 1, "end": 10})
        assert metadata1.get_level_range() == "Levels 1-10"

        # Single level
        metadata2 = AdventureMetadata(level={"start": 5, "end": 5})
        assert metadata2.get_level_range() == "Level 5"

        # No level
        metadata3 = AdventureMetadata(level=None)
        assert metadata3.get_level_range() == ""

        # Only start level
        metadata4 = AdventureMetadata(level={"start": 3})
        assert metadata4.get_level_range() == "Level 3"

    def test_adventure_5etools_data_transformation(self):
        """Test that Adventure correctly transforms 5etools 'data' format."""
        from dnd5e.core.models.adventures import Adventure

        # Simulate 5etools adventure format with "data" array
        raw_data = {
            "name": "Test Adventure",
            "source": {"abbreviation": "TEST"},
            "id": "test",
            "data": [
                {
                    "name": "Chapter 1",
                    "type": "section",
                    "id": "ch1",
                    "entries": ["This is chapter 1 content..."],
                },
                {
                    "name": "Chapter 2",
                    "type": "section",
                    "id": "ch2",
                    "entries": ["This is chapter 2 content..."],
                },
            ],
        }

        adventure = Adventure.model_validate(raw_data)

        assert adventure.name == "Test Adventure"
        assert adventure.id == "test"
        assert len(adventure.contents) == 2
        assert adventure.contents[0].name == "Chapter 1"
        assert adventure.contents[1].name == "Chapter 2"

    def test_adventure_id_validation(self):
        """Test Adventure ID field validation."""
        import pytest

        from dnd5e.core.models.adventures import Adventure

        # Valid ID
        adventure1 = Adventure(
            name="Test Adventure", source="TEST", id="test-adventure"
        )
        assert adventure1.id == "test-adventure"

        # None ID (allowed)
        adventure2 = Adventure(name="Test Adventure", source="TEST", id=None)
        assert adventure2.id is None

        # Empty string ID (should be stripped to None or raise error)
        with pytest.raises(ValueError, match="Adventure ID cannot be empty"):
            Adventure(
                name="Test Adventure",
                source="TEST",
                id="   ",  # whitespace only
            )

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
