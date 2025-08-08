"""Tests for CharacterOption content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestCharacterOptionMigration:
    """Test CharacterOption content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_charoption_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers CharacterOption automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "CHAROPTION")
        assert ContentType.CHAROPTION == "charoption"

    def test_charoption_content_factory_integration(self) -> None:
        """Test CharacterOption works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an Alagondar Scion character option
        charoption_data = {
            "name": "Alagondar Scion",
            "source": {
                "abbreviation": "IDRotF",
                "full": "Icewind Dale: Rime of the Frostmaiden",
            },
            "page": 264,
            "prerequisite": [
                {
                    "race": [
                        {"name": "human"},
                        {"name": "half-elf"},
                        {"name": "half-orc"},
                    ],
                    "note": "If you don't meet this prerequisite, draw a different card.",
                }
            ],
            "optionType": ["CS"],
            "entries": [
                "I'm a scion of the Alagondar bloodline and the only known heir to the crown of Neverwinter. If Dagult Neverember, the city's lord-regent, learns that I'm alive, he'll send assassins to kill me."
            ],
        }

        content = factory.create_content(charoption_data, ContentType.CHAROPTION)

        assert content.name == "Alagondar Scion"
        assert content.source.abbreviation == "IDRotF"
        assert content.has_prerequisite() is True
        assert content.matches_option_type("CS") is True
        assert len(content.get_option_types()) == 1
        assert "CS" in content.get_option_types()

    def test_charoption_dark_gift_data(self) -> None:
        """Test CharacterOption with dark gift data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a dark gift character option
        dark_gift_data = {
            "name": "Echoing Soul",
            "source": {
                "abbreviation": "VRGtR",
                "full": "Van Richten's Guide to Ravenloft",
            },
            "optionType": ["DG"],
            "entries": [
                "Your soul echoes with the voices of the dead. You gain the following benefits:",
                {
                    "type": "list",
                    "items": [
                        "You can speak, read, and write one additional language of your choice.",
                        "You have resistance to necrotic damage.",
                        "As a bonus action, you can channel the voices in your soul to gain advantage on your next Wisdom (Insight) or Charisma (Intimidation) check. Once you use this feature, you can't use it again until you finish a short or long rest.",
                    ],
                },
            ],
        }

        content = factory.create_content(dark_gift_data, ContentType.CHAROPTION)

        assert content.name == "Echoing Soul"
        assert content.matches_option_type("DG") is True
        assert content.has_prerequisite() is False
        assert len(content.entries) == 2

    def test_charoption_supernatural_gift_data(self) -> None:
        """Test CharacterOption with supernatural gift data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a supernatural gift
        supernatural_gift_data = {
            "name": "Anvilwrought",
            "source": {"abbreviation": "MOT", "full": "Mythic Odysseys of Theros"},
            "optionType": ["SG"],
            "entries": [
                "Your soul was forged in the first days of Theros by the god Purphoros. You are a living construct built to honor the gods.",
                "You have the following racial traits:",
                {
                    "type": "entries",
                    "name": "Creature Type",
                    "entries": ["You are a construct."],
                },
                {
                    "type": "entries",
                    "name": "Armor Integration",
                    "entries": [
                        "You can don only armor with which you have proficiency. To don armor other than a shield, you must incorporate it into your body over the course of 1 hour, during which you remain conscious. To doff armor, you must spend 1 hour removing it. You can rest while donning or doffing armor in this way."
                    ],
                },
            ],
        }

        content = factory.create_content(supernatural_gift_data, ContentType.CHAROPTION)

        assert content.name == "Anvilwrought"
        assert content.matches_option_type("SG") is True
        assert content.source.abbreviation == "MOT"
        assert len(content.entries) == 4

    def test_charoption_multiple_option_types(self) -> None:
        """Test CharacterOption with multiple option types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating option with multiple types
        multi_type_data = {
            "name": "Multi-Type Option",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "optionType": ["CS", "DG"],
            "entries": ["This is a test option with multiple types."],
        }

        content = factory.create_content(multi_type_data, ContentType.CHAROPTION)

        assert content.name == "Multi-Type Option"
        assert len(content.get_option_types()) == 2
        assert content.matches_option_type("CS") is True
        assert content.matches_option_type("DG") is True
        assert content.matches_option_type("SG") is False

    def test_charoption_prerequisite_summary(self) -> None:
        """Test prerequisite summary functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test complex prerequisite structure
        prereq_data = {
            "name": "Complex Prereq Option",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "prerequisite": [
                {
                    "race": [{"name": "elf"}, {"name": "half-elf"}],
                    "background": "noble",
                    "note": "Must have noble connections",
                }
            ],
            "optionType": ["RF:B"],
            "entries": ["Test option with complex prerequisites."],
        }

        content = factory.create_content(prereq_data, ContentType.CHAROPTION)

        summary = content.get_prerequisite_summary()
        assert "Race: elf, half-elf" in summary
        assert "Background: noble" in summary
        assert "Note: Must have noble connections" in summary

    def test_charoption_validation_errors(self) -> None:
        """Test CharacterOption validation errors."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with invalid data structure
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "",  # Empty name should fail
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "optionType": ["CS"],
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.CHAROPTION)

    def test_charoption_helper_methods(self) -> None:
        """Test CharacterOption helper methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test helper methods with minimal data
        simple_data = {
            "name": "Simple Option",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "entries": ["A simple character option."],
        }

        content = factory.create_content(simple_data, ContentType.CHAROPTION)

        # Test no prerequisites
        assert content.has_prerequisite() is False
        assert content.get_prerequisite_summary() == "No prerequisites"

        # Test no option types
        assert len(content.get_option_types()) == 0
        assert content.matches_option_type("CS") is False

    def test_charoption_omnidexer_integration(self) -> None:
        """Test CharacterOption integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify CharacterOption is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.CHAROPTION in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.CHAROPTION in json_types

    def test_charoption_file_patterns(self) -> None:
        """Test CharacterOption file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify CharacterOption patterns are registered
        assert ContentType.CHAROPTION in content_patterns
        patterns = content_patterns[ContentType.CHAROPTION]
        assert "charoption" in patterns
        assert "charcreationoptions" in patterns

    def test_charoption_registry_consistency(self) -> None:
        """Test that CharacterOption registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has CharacterOption
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        charoption_registration = registrations.get("charoption")
        assert charoption_registration is not None
        assert charoption_registration.enum_value == "charoption"

        # Check ContentFactory has CharacterOption
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.CHAROPTION in supported_factory_types

        # Check Omnidexer has CharacterOption
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.CHAROPTION in supported_omnidexer_types
