"""Tests for Subclass content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestSubclassMigration:
    """Test Subclass content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_subclass_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Subclass automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "SUBCLASS")
        assert ContentType.SUBCLASS == "subclass"

    def test_subclass_content_factory_integration(self) -> None:
        """Test Subclass works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a wizard school
        subclass_data = {
            "name": "School of Abjuration",
            "shortName": "Abjuration",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "className": "Wizard",
            "classSource": "PHB",
            "subclassFeatures": [
                "Abjuration Savant|Wizard|PHB|Abjuration||2",
                "Arcane Ward|Wizard|PHB|Abjuration||2",
                "Projected Ward|Wizard|PHB|Abjuration||6",
                "Improved Abjuration|Wizard|PHB|Abjuration||10",
                "Spell Resistance|Wizard|PHB|Abjuration||14",
            ],
            "entries": [],
        }

        content = factory.create_content(subclass_data, ContentType.SUBCLASS)

        assert content.name == "School of Abjuration"
        assert content.short_name == "Abjuration"
        assert content.class_name == "Wizard"
        assert content.class_source == "PHB"
        assert len(content.subclass_features) == 5

    def test_subclass_cleric_domain_data(self) -> None:
        """Test Subclass with cleric domain data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a cleric domain with additional spells
        domain_data = {
            "name": "Life Domain",
            "shortName": "Life",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "className": "Cleric",
            "classSource": "PHB",
            "subclassFeatures": [
                "Domain Spells|Cleric|PHB|Life||1",
                "Bonus Proficiency|Cleric|PHB|Life||1",
                "Disciple of Life|Cleric|PHB|Life||1",
                "Channel Divinity: Preserve Life|Cleric|PHB|Life||2",
                "Blessed Healer|Cleric|PHB|Life||6",
                "Divine Strike|Cleric|PHB|Life||8",
                "Supreme Healing|Cleric|PHB|Life||17",
            ],
            "additionalSpells": [
                {
                    "prepared": {
                        "1": ["bless", "cure wounds"],
                        "3": ["lesser restoration", "spiritual weapon"],
                        "5": ["beacon of hope", "revivify"],
                        "7": ["death ward", "guardian of faith"],
                        "9": ["mass cure wounds", "raise dead"],
                    }
                }
            ],
            "entries": [],
        }

        content = factory.create_content(domain_data, ContentType.SUBCLASS)

        assert content.name == "Life Domain"
        assert content.short_name == "Life"
        assert content.additional_spells is not None
        assert len(content.additional_spells) == 1
        assert content.additional_spells[0].prepared is not None
        assert "cure wounds" in content.additional_spells[0].prepared["1"]

    def test_subclass_warlock_patron_data(self) -> None:
        """Test Subclass with warlock patron data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a warlock patron
        patron_data = {
            "name": "The Fiend",
            "shortName": "Fiend",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "className": "Warlock",
            "classSource": "PHB",
            "subclassFeatures": [
                "Expanded Spell List|Warlock|PHB|Fiend||1",
                "Dark One's Blessing|Warlock|PHB|Fiend||1",
                "Dark One's Own Luck|Warlock|PHB|Fiend||6",
                "Fiendish Resilience|Warlock|PHB|Fiend||10",
                "Hurl Through Hell|Warlock|PHB|Fiend||14",
            ],
            "additionalSpells": [
                {
                    "expanded": {
                        "1": ["burning hands", "command"],
                        "2": ["blindness/deafness", "scorching ray"],
                        "3": ["fireball", "stinking cloud"],
                        "4": ["fire shield", "wall of fire"],
                        "5": ["flame strike", "hallow"],
                    }
                }
            ],
            "entries": [],
        }

        content = factory.create_content(patron_data, ContentType.SUBCLASS)

        assert content.name == "The Fiend"
        assert content.short_name == "Fiend"
        assert content.additional_spells is not None
        assert content.additional_spells[0].expanded is not None
        assert "fireball" in content.additional_spells[0].expanded["3"]

    def test_subclass_validation_errors(self) -> None:
        """Test subclass validation errors."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty short name (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Test Subclass",
                "shortName": "",  # Empty short name should fail
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "className": "TestClass",
                "classSource": "TEST",
                "subclassFeatures": ["Feature|TestClass|TEST|Test||1"],
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.SUBCLASS)

        # Test with empty subclass features (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Test Subclass",
                "shortName": "Test",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "className": "TestClass",
                "classSource": "TEST",
                "subclassFeatures": [],  # Empty features should fail
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.SUBCLASS)

    def test_subclass_helper_methods(self) -> None:
        """Test subclass helper methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test helper methods
        subclass_data = {
            "name": "Circle of the Moon",
            "shortName": "Moon",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "className": "Druid",
            "classSource": "PHB",
            "subclassFeatures": [
                "Combat Wild Shape|Druid|PHB|Moon||2",
                "Circle Forms|Druid|PHB|Moon||2",
                "Primal Strike|Druid|PHB|Moon||6",
                "Elemental Wild Shape|Druid|PHB|Moon||10",
                "Thousand Forms|Druid|PHB|Moon||14",
            ],
            "entries": [],
        }

        content = factory.create_content(subclass_data, ContentType.SUBCLASS)

        # Test identifier methods
        class_id = content.get_class_identifier()
        assert class_id == "Druid|PHB"

        subclass_id = content.get_subclass_identifier()
        assert subclass_id == "Druid|PHB|Moon|PHB"

        # Test feature level mapping
        level_map = content.get_feature_level_map()
        assert 2 in level_map
        assert 6 in level_map
        assert 10 in level_map
        assert 14 in level_map
        assert "Combat Wild Shape" in level_map[2]

    def test_subclass_omnidexer_integration(self) -> None:
        """Test Subclass integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Subclass is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.SUBCLASS in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.SUBCLASS in json_types

    def test_subclass_file_patterns(self) -> None:
        """Test Subclass file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Subclass patterns are registered
        assert ContentType.SUBCLASS in content_patterns
        patterns = content_patterns[ContentType.SUBCLASS]
        assert "class" in patterns
        assert "classes" in patterns

    def test_subclass_registry_consistency(self) -> None:
        """Test that Subclass registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Subclass
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        subclass_registration = registrations.get("subclass")
        assert subclass_registration is not None
        assert subclass_registration.enum_value == "subclass"

        # Check ContentFactory has Subclass
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.SUBCLASS in supported_factory_types

        # Check Omnidexer has Subclass
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.SUBCLASS in supported_omnidexer_types
