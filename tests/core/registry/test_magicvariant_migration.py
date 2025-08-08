"""Tests for MagicVariant content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestMagicVariantMigration:
    """Test MagicVariant content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_magicvariant_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers MagicVariant automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "MAGICVARIANT")
        assert ContentType.MAGICVARIANT == "magicvariant"

    def test_magicvariant_content_factory_integration(self) -> None:
        """Test MagicVariant works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a +1 Ammunition magic variant
        ammunition_data = {
            "name": "+1 Ammunition",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "edition": "classic",
            "type": "GV|DMG",
            "requires": [{"type": "A"}, {"type": "AF|DMG"}],
            "ammo": True,
            "inherits": {
                "namePrefix": "+1 ",
                "source": "DMG",
                "page": 150,
                "tier": "minor",
                "rarity": "uncommon",
                "bonusWeapon": "+1",
                "entries": [
                    "You have a +1 bonus to attack and damage rolls made with this piece of magic ammunition. Once it hits a target, the ammunition is no longer magical."
                ],
            },
        }

        content = factory.create_content(ammunition_data, ContentType.MAGICVARIANT)

        assert content.name == "+1 Ammunition"
        assert content.source.abbreviation == "DMG"
        assert content.applies_to_ammunition() is True
        assert content.is_generic_variant() is True
        assert content.get_edition() == "classic"
        assert content.get_bonus_value() == "+1"
        assert content.get_name_prefix() == "+1 "
        assert content.get_rarity() == "uncommon"

    def test_magicvariant_armor_variant_data(self) -> None:
        """Test MagicVariant with armor variant data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a +1 Armor magic variant
        armor_data = {
            "name": "+1 Armor",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "type": "GV|DMG",
            "requires": [{"armor": True}],
            "inherits": {
                "namePrefix": "+1 ",
                "source": "DMG",
                "page": 152,
                "tier": "major",
                "rarity": "rare",
                "bonusAc": "+1",
                "entries": ["You have a +1 bonus to AC while wearing this armor."],
            },
        }

        content = factory.create_content(armor_data, ContentType.MAGICVARIANT)

        assert content.name == "+1 Armor"
        assert content.applies_to_armor() is False  # Not explicitly set
        assert content.get_bonus_value() == "+1"
        assert content.get_rarity() == "rare"
        assert content.has_requirements() is True
        assert content.get_requirement_count() == 1

    def test_magicvariant_weapon_variant_data(self) -> None:
        """Test MagicVariant with weapon variant data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a weapon magic variant
        weapon_data = {
            "name": "Flame Tongue",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "type": "GV|DMG",
            "weapon": True,
            "requires": [{"type": "MS"}, {"type": "MW"}],
            "inherits": {
                "rarity": "rare",
                "reqAttune": True,
                "entries": [
                    "You can use a bonus action to speak this magic sword's command word, causing flames to erupt from the blade."
                ],
            },
        }

        content = factory.create_content(weapon_data, ContentType.MAGICVARIANT)

        assert content.name == "Flame Tongue"
        assert content.applies_to_weapons() is True
        assert content.has_requirements() is True
        assert content.get_requirement_count() == 2
        assert content.matches_item_type("MS") is True
        assert content.matches_item_type("MW") is True

    def test_magicvariant_item_type_matching(self) -> None:
        """Test magic variant item type matching functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test item type matching
        variant_data = {
            "name": "Test Variant",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "GV|TEST",
            "requires": [{"type": "A|XPHB"}, {"type": "AF|XDMG"}],
        }

        content = factory.create_content(variant_data, ContentType.MAGICVARIANT)

        assert content.matches_item_type("A|XPHB") is True
        assert content.matches_item_type("AF|XDMG") is True
        assert content.matches_item_type("XPHB") is True
        assert content.matches_item_type("A") is True
        assert content.matches_item_type("SWORD") is False

    def test_magicvariant_inherited_properties(self) -> None:
        """Test magic variant inherited properties functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test inherited properties
        properties_data = {
            "name": "Property Test Variant",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "GV|TEST",
            "inherits": {
                "namePrefix": "Magical ",
                "rarity": "legendary",
                "bonusWeapon": "+3",
                "bonusAc": "+2",
                "customProperty": "test value",
            },
        }

        content = factory.create_content(properties_data, ContentType.MAGICVARIANT)

        assert content.has_inherited_properties() is True
        inherited = content.get_inherited_properties()
        assert inherited["namePrefix"] == "Magical "
        assert inherited["rarity"] == "legendary"
        assert inherited["customProperty"] == "test value"
        assert content.get_bonus_value() == "+3"  # First bonus field found
        assert content.get_name_prefix() == "Magical "
        assert content.get_rarity() == "legendary"

    def test_magicvariant_minimal_data(self) -> None:
        """Test MagicVariant with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Variant",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "GV|TEST",
        }

        content = factory.create_content(minimal_data, ContentType.MAGICVARIANT)

        assert content.name == "Minimal Variant"
        assert content.get_variant_type() == "GV|TEST"
        assert content.has_requirements() is False
        assert content.has_inherited_properties() is False
        assert content.get_edition() == "current"  # Default
        assert content.get_bonus_value() is None
        assert content.get_name_prefix() is None
        assert content.get_rarity() is None

    def test_magicvariant_validation_errors(self) -> None:
        """Test MagicVariant validation errors."""
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
                "type": "GV|TEST",
            }
            factory.create_content(invalid_data, ContentType.MAGICVARIANT)

        # Test with missing required type field
        with pytest.raises(ValidationError):
            missing_type_data = {
                "name": "Test Variant",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                # Missing required 'type' field
            }
            factory.create_content(missing_type_data, ContentType.MAGICVARIANT)

    def test_magicvariant_helper_methods(self) -> None:
        """Test MagicVariant helper methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test helper methods with comprehensive data
        helper_data = {
            "name": "Helper Test Variant",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "GV|TEST",
            "edition": "2024",
            "ammo": True,
            "armor": False,
            "weapon": True,
        }

        content = factory.create_content(helper_data, ContentType.MAGICVARIANT)

        # Test type checks
        assert content.applies_to_ammunition() is True
        assert content.applies_to_armor() is False
        assert content.applies_to_weapons() is True
        assert content.is_generic_variant() is True
        assert content.get_edition() == "2024"

    def test_magicvariant_omnidexer_integration(self) -> None:
        """Test MagicVariant integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify MagicVariant is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.MAGICVARIANT in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.MAGICVARIANT in json_types

    def test_magicvariant_file_patterns(self) -> None:
        """Test MagicVariant file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify MagicVariant patterns are registered
        assert ContentType.MAGICVARIANT in content_patterns
        patterns = content_patterns[ContentType.MAGICVARIANT]
        assert "magicvariant" in patterns
        assert "magicvariants" in patterns

    def test_magicvariant_registry_consistency(self) -> None:
        """Test that MagicVariant registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has MagicVariant
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        magicvariant_registration = registrations.get("magicvariant")
        assert magicvariant_registration is not None
        assert magicvariant_registration.enum_value == "magicvariant"

        # Check ContentFactory has MagicVariant
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.MAGICVARIANT in supported_factory_types

        # Check Omnidexer has MagicVariant
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.MAGICVARIANT in supported_omnidexer_types
