"""Tests for CharacterOptionType content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestCharacterOptionTypeMigration:
    """Test CharacterOptionType content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_charoptiontype_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers CharacterOptionType automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "CHAROPTIONTYPE")
        assert ContentType.CHAROPTIONTYPE == "charoptiontype"

    def test_charoptiontype_content_factory_integration(self) -> None:
        """Test CharacterOptionType works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Supernatural Gift option type
        charoptiontype_data = {
            "name": "Supernatural Gift",
            "source": {"abbreviation": "CORE", "full": "Core Rules"},
            "abbreviation": "SG",
            "full_name": "Supernatural Gift",
            "description": "Supernatural gifts represent boons granted by powerful entities or cosmic forces.",
            "entries": [
                "Supernatural gifts are special traits that characters can gain through extraordinary circumstances.",
                {
                    "type": "entries",
                    "name": "Gaining Supernatural Gifts",
                    "entries": [
                        "Characters typically gain supernatural gifts as rewards for great deeds or through exposure to powerful magic."
                    ],
                },
            ],
        }

        content = factory.create_content(
            charoptiontype_data, ContentType.CHAROPTIONTYPE
        )

        assert content.name == "Supernatural Gift"
        assert content.abbreviation == "SG"
        assert content.full_name == "Supernatural Gift"
        assert content.is_supernatural_gift() is True
        assert content.is_known_category() is True
        assert len(content.entries) == 2

    def test_charoptiontype_dark_gift_category(self) -> None:
        """Test CharacterOptionType with Dark Gift category."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Dark Gift option type
        dark_gift_data = {
            "name": "Dark Gift",
            "source": {
                "abbreviation": "VRGtR",
                "full": "Van Richten's Guide to Ravenloft",
            },
            "abbreviation": "DG",
            "full_name": "Dark Gift",
            "description": "Dark gifts are supernatural abilities that come with a price or curse.",
            "rules_source": "VRGtR",
            "entries": [
                "Dark gifts manifest as supernatural abilities paired with flaws or drawbacks.",
                "Each dark gift reflects the corrupting influence of the domains of dread.",
            ],
        }

        content = factory.create_content(dark_gift_data, ContentType.CHAROPTIONTYPE)

        assert content.name == "Dark Gift"
        assert content.abbreviation == "DG"
        assert content.is_dark_gift() is True
        assert content.is_known_category() is True
        assert content.rules_source == "VRGtR"

    def test_charoptiontype_replacement_feature_category(self) -> None:
        """Test CharacterOptionType with Replacement Feature category."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Replacement Feature option type
        replacement_data = {
            "name": "Replacement Feature - Background",
            "source": {"abbreviation": "CORE", "full": "Core Rules"},
            "abbreviation": "RF:B",
            "full_name": "Replacement Feature: Background",
            "description": "Alternative features that replace standard background features.",
            "entries": [
                "Replacement features allow customization of existing character elements.",
                "These features are designed to better fit specific campaign themes or character concepts.",
            ],
        }

        content = factory.create_content(replacement_data, ContentType.CHAROPTIONTYPE)

        assert content.name == "Replacement Feature - Background"
        assert content.abbreviation == "RF:B"
        assert content.is_replacement_feature() is True
        assert content.get_replacement_type() == "B"
        assert content.is_known_category() is True

    def test_charoptiontype_character_secret_category(self) -> None:
        """Test CharacterOptionType with Character Secret category."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Character Secret option type
        character_secret_data = {
            "name": "Character Secret",
            "source": {
                "abbreviation": "IDRotF",
                "full": "Icewind Dale: Rime of the Frostmaiden",
            },
            "abbreviation": "CS",
            "full_name": "Character Secret",
            "description": "Character secrets are background elements specific to certain campaigns.",
            "rules_source": "IDRotF",
            "entries": [
                "Character secrets provide personal motivations and plot hooks tied to specific adventures.",
                "Each secret gives the character a unique connection to the campaign world.",
            ],
        }

        content = factory.create_content(
            character_secret_data, ContentType.CHAROPTIONTYPE
        )

        assert content.name == "Character Secret"
        assert content.abbreviation == "CS"
        assert content.is_character_secret() is True
        assert content.is_known_category() is True

    def test_charoptiontype_custom_category(self) -> None:
        """Test CharacterOptionType with custom/unknown category."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a custom option type
        custom_data = {
            "name": "Custom Option Type",
            "source": {"abbreviation": "HOMEBREW", "full": "Homebrew Content"},
            "abbreviation": "CUSTOM",
            "full_name": "Custom Option Type",
            "description": "A homebrew character option category.",
            "entries": ["This is a custom option type for homebrew content."],
        }

        content = factory.create_content(custom_data, ContentType.CHAROPTIONTYPE)

        assert content.name == "Custom Option Type"
        assert content.abbreviation == "CUSTOM"
        assert content.is_known_category() is False
        assert content.get_category() is None

    def test_charoptiontype_create_standard_types(self) -> None:
        """Test creating standard character option types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.models.charoptiontype import CharacterOptionType

        standard_types = CharacterOptionType.create_standard_types()

        assert len(standard_types) == 5

        # Check that all standard types are present
        abbreviations = {opt.abbreviation for opt in standard_types}
        assert "SG" in abbreviations
        assert "DG" in abbreviations
        assert "CS" in abbreviations
        assert "RF:B" in abbreviations
        assert "OF" in abbreviations

        # Check specific properties
        sg_type = next(opt for opt in standard_types if opt.abbreviation == "SG")
        assert sg_type.is_supernatural_gift() is True
        assert sg_type.full_name == "Supernatural Gift"

        dg_type = next(opt for opt in standard_types if opt.abbreviation == "DG")
        assert dg_type.is_dark_gift() is True
        assert dg_type.full_name == "Dark Gift"

    def test_charoptiontype_validation_errors(self) -> None:
        """Test CharacterOptionType validation errors."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty abbreviation
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Invalid Type",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "abbreviation": "",  # Empty abbreviation should fail
                "full_name": "Invalid Type",
            }
            factory.create_content(invalid_data, ContentType.CHAROPTIONTYPE)

        # Test with empty full name
        with pytest.raises(ValidationError):
            invalid_data2 = {
                "name": "Invalid Type",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "abbreviation": "IV",
                "full_name": "",  # Empty full name should fail
            }
            factory.create_content(invalid_data2, ContentType.CHAROPTIONTYPE)

    def test_charoptiontype_helper_methods(self) -> None:
        """Test CharacterOptionType helper methods with various types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test replacement feature with different suffix
        replacement_class_data = {
            "name": "Replacement Feature - Class",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "abbreviation": "RF:C",
            "full_name": "Replacement Feature: Class",
        }

        content = factory.create_content(
            replacement_class_data, ContentType.CHAROPTIONTYPE
        )

        assert content.is_replacement_feature() is True
        assert content.get_replacement_type() == "C"
        assert content.is_known_category() is False  # RF:C is not a standard type

    def test_charoptiontype_omnidexer_integration(self) -> None:
        """Test CharacterOptionType integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify CharacterOptionType is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.CHAROPTIONTYPE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.CHAROPTIONTYPE in json_types

    def test_charoptiontype_file_patterns(self) -> None:
        """Test CharacterOptionType file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify CharacterOptionType patterns are registered
        assert ContentType.CHAROPTIONTYPE in content_patterns
        patterns = content_patterns[ContentType.CHAROPTIONTYPE]
        assert "charoptiontype" in patterns
        assert "charoptiontypes" in patterns

    def test_charoptiontype_registry_consistency(self) -> None:
        """Test that CharacterOptionType registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has CharacterOptionType
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        charoptiontype_registration = registrations.get("charoptiontype")
        assert charoptiontype_registration is not None
        assert charoptiontype_registration.enum_value == "charoptiontype"

        # Check ContentFactory has CharacterOptionType
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.CHAROPTIONTYPE in supported_factory_types

        # Check Omnidexer has CharacterOptionType
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.CHAROPTIONTYPE in supported_omnidexer_types
