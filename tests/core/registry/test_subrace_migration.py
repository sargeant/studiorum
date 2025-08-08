"""Tests for Subrace content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestSubraceMigration:
    """Test Subrace content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_subrace_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Subrace automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "SUBRACE")
        assert ContentType.SUBRACE == "subrace"

    def test_subrace_content_factory_integration(self) -> None:
        """Test Subrace works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a hill dwarf subrace
        subrace_data = {
            "name": "Hill Dwarf",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "raceName": "Dwarf",
            "raceSource": "PHB",
            "ability": [{"wis": 1}],
            "entries": [
                {
                    "type": "entries",
                    "name": "Dwarven Toughness",
                    "entries": [
                        "Your hit point maximum increases by 1, and it increases by 1 every time you gain a level."
                    ],
                }
            ],
        }

        content = factory.create_content(subrace_data, ContentType.SUBRACE)

        assert content.name == "Hill Dwarf"
        assert content.race_name == "Dwarf"
        assert content.race_source == "PHB"
        assert len(content.ability) == 1
        assert content.ability[0]["wis"] == 1

    def test_subrace_high_elf_data(self) -> None:
        """Test Subrace with high elf data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a high elf with weapon and skill proficiencies
        high_elf_data = {
            "name": "High Elf",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "raceName": "Elf",
            "raceSource": "PHB",
            "ability": [{"int": 1}],
            "weaponProficiencies": [
                {
                    "longsword": True,
                    "shortsword": True,
                    "shortbow": True,
                    "longbow": True,
                }
            ],
            "additionalSpells": [
                {"innate": {"1": {"spells": {"choose": "from|wizard|0"}}}}
            ],
            "entries": [
                {
                    "type": "entries",
                    "name": "Elf Weapon Training",
                    "entries": [
                        "You have proficiency with longswords, shortswords, shortbows, and longbows."
                    ],
                },
                {
                    "type": "entries",
                    "name": "Cantrip",
                    "entries": [
                        "You know one cantrip of your choice from the wizard spell list."
                    ],
                },
            ],
        }

        content = factory.create_content(high_elf_data, ContentType.SUBRACE)

        assert content.name == "High Elf"
        assert content.ability[0]["int"] == 1
        assert content.weapon_proficiencies is not None
        assert len(content.weapon_proficiencies) == 1
        assert content.weapon_proficiencies[0]["longsword"] is True
        assert content.additional_spells is not None

    def test_subrace_tiefling_variant_data(self) -> None:
        """Test Subrace with tiefling variant data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a tiefling variant with resistances
        tiefling_data = {
            "name": "Asmodeus Tiefling",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "raceName": "Tiefling",
            "raceSource": "PHB",
            "ability": [{"cha": 2, "int": 1}],
            "resist": ["fire"],
            "spellcastingAbility": "cha",
            "additionalSpells": [
                {
                    "innate": {
                        "1": {"spells": {"thaumaturgy": {}}},
                        "3": {"spells": {"hellish rebuke": {"ability": "cha"}}},
                        "5": {"spells": {"darkness": {}}},
                    }
                }
            ],
            "entries": [
                {
                    "type": "entries",
                    "name": "Infernal Legacy",
                    "entries": [
                        "You know the {@spell thaumaturgy} cantrip. When you reach 3rd level, you can cast the {@spell hellish rebuke} spell as a 2nd-level spell once with this trait and regain the ability to do so when you finish a long rest."
                    ],
                }
            ],
        }

        content = factory.create_content(tiefling_data, ContentType.SUBRACE)

        assert content.name == "Asmodeus Tiefling"
        assert content.ability[0]["cha"] == 2
        assert content.ability[0]["int"] == 1
        assert content.resist == ["fire"]
        assert content.spellcasting_ability == "cha"

    def test_subrace_ability_validation(self) -> None:
        """Test ability score validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty race name (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Invalid Subrace",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "raceName": "",  # Empty race name should fail
                "raceSource": "TEST",
                "ability": [{"str": 2}],
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.SUBRACE)

    def test_subrace_darkvision_validation(self) -> None:
        """Test darkvision range validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with extreme darkvision (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Invalid Subrace",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "raceName": "TestRace",
                "raceSource": "TEST",
                "darkvision": 500,  # Too high, should fail
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.SUBRACE)

    def test_subrace_helper_methods(self) -> None:
        """Test subrace helper methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test helper methods
        subrace_data = {
            "name": "Mountain Dwarf",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "raceName": "Dwarf",
            "raceSource": "PHB",
            "ability": [{"str": 2, "con": 2}],
            "skillProficiencies": [{"perception": True, "stealth": True}],
            "entries": [],
        }

        content = factory.create_content(subrace_data, ContentType.SUBRACE)

        # Test identifier methods
        race_id = content.get_race_identifier()
        assert race_id == "Dwarf|PHB"

        subrace_id = content.get_subrace_identifier()
        assert subrace_id == "Dwarf|PHB|Mountain Dwarf|PHB"

        # Test actual implemented functionality
        assert content.ability is not None
        assert len(content.ability) == 1
        assert "str" in content.ability[0]
        assert "con" in content.ability[0]

    def test_subrace_omnidexer_integration(self) -> None:
        """Test Subrace integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Subrace is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.SUBRACE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.SUBRACE in json_types

    def test_subrace_file_patterns(self) -> None:
        """Test Subrace file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Subrace patterns are registered
        assert ContentType.SUBRACE in content_patterns
        patterns = content_patterns[ContentType.SUBRACE]
        assert "race" in patterns
        assert "races" in patterns

    def test_subrace_registry_consistency(self) -> None:
        """Test that Subrace registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Subrace
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        subrace_registration = registrations.get("subrace")
        assert subrace_registration is not None
        assert subrace_registration.enum_value == "subrace"

        # Check ContentFactory has Subrace
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.SUBRACE in supported_factory_types

        # Check Omnidexer has Subrace
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.SUBRACE in supported_omnidexer_types
