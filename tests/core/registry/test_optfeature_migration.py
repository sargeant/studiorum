"""Tests for OptionalFeature content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestOptionalFeatureMigration:
    """Test OptionalFeature content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_optfeature_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers OptionalFeature automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "OPTFEATURE")
        assert ContentType.OPTFEATURE == "optfeature"

    def test_optfeature_content_factory_integration(self) -> None:
        """Test OptionalFeature works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an Agonizing Blast eldritch invocation
        agonizing_blast_data = {
            "name": "Agonizing Blast",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "page": 110,
            "featureType": ["EI"],
            "prerequisite": [{"spell": ["eldritch blast#c"]}],
            "entries": [
                "When you cast eldritch blast, add your Charisma modifier to the damage it deals on a hit."
            ],
        }

        content = factory.create_content(agonizing_blast_data, ContentType.OPTFEATURE)

        assert content.name == "Agonizing Blast"
        assert content.source.abbreviation == "PHB"
        assert content.is_eldritch_invocation() is True
        assert content.has_prerequisite() is True
        assert content.get_primary_feature_type() == "EI"
        prerequisite_summary = content.get_prerequisite_summary()
        assert "eldritch blast" in prerequisite_summary

    def test_optfeature_fighting_style_data(self) -> None:
        """Test OptionalFeature with fighting style data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Fighting Style
        archery_data = {
            "name": "Archery",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["FS:F"],
            "entries": [
                "You gain a +2 bonus to attack rolls you make with ranged weapons."
            ],
        }

        content = factory.create_content(archery_data, ContentType.OPTFEATURE)

        assert content.name == "Archery"
        assert content.is_fighting_style() is True
        assert content.is_eldritch_invocation() is False
        assert content.has_prerequisite() is False
        assert content.get_feature_types() == ["FS:F"]

    def test_optfeature_maneuver_data(self) -> None:
        """Test OptionalFeature with Battle Master maneuver data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Battle Master maneuver
        ambush_data = {
            "name": "Ambush",
            "source": {"abbreviation": "XPHB", "full": "Player's Handbook (2024)"},
            "featureType": ["MV:B"],
            "consumes": {"name": "Superiority Die"},
            "entries": [
                "When you make a Dexterity (Stealth) check or an Initiative roll, you can expend one Superiority Die and add the die to the roll, unless you have the Incapacitated condition."
            ],
        }

        content = factory.create_content(ambush_data, ContentType.OPTFEATURE)

        assert content.name == "Ambush"
        assert content.is_maneuver() is True
        assert content.consumes_resources() is True
        assert content.get_consumed_resource() == "Superiority Die"

    def test_optfeature_metamagic_data(self) -> None:
        """Test OptionalFeature with metamagic option data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Metamagic option
        quickened_data = {
            "name": "Quickened Spell",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["MM"],
            "entries": [
                "When you cast a spell that has a casting time of 1 action, you can spend 2 sorcery points to change the casting time to 1 bonus action for this casting."
            ],
        }

        content = factory.create_content(quickened_data, ContentType.OPTFEATURE)

        assert content.name == "Quickened Spell"
        assert content.is_metamagic() is True
        assert content.is_fighting_style() is False
        assert content.is_maneuver() is False

    def test_optfeature_artificer_infusion_data(self) -> None:
        """Test OptionalFeature with Artificer Infusion data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an Artificer Infusion
        enhanced_weapon_data = {
            "name": "Enhanced Weapon",
            "source": {"abbreviation": "TCE", "full": "Tasha's Cauldron of Everything"},
            "featureType": ["AI"],
            "level": 2,
            "entries": [
                "Item: A simple or martial weapon",
                "This magic weapon grants a +1 bonus to attack and damage rolls made with it.",
            ],
        }

        content = factory.create_content(enhanced_weapon_data, ContentType.OPTFEATURE)

        assert content.name == "Enhanced Weapon"
        assert content.is_artificer_infusion() is True
        assert content.has_level_requirement() is True
        assert content.get_minimum_level() == 2

    def test_optfeature_complex_prerequisite_data(self) -> None:
        """Test OptionalFeature with complex prerequisite structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test complex prerequisite structure
        complex_prereq_data = {
            "name": "Advanced Invocation",
            "source": {"abbreviation": "XPHB", "full": "Player's Handbook (2024)"},
            "featureType": ["EI"],
            "prerequisite": [
                {
                    "spell": [
                        {
                            "choose": "level=0|class=Warlock",
                            "entry": "a Warlock Cantrip That Deals Damage",
                            "entrySummary": "Warlock Cantrip That Deals Damage",
                        }
                    ],
                    "level": {
                        "level": 2,
                        "class": {"name": "Warlock", "source": "XPHB"},
                    },
                }
            ],
            "entries": [
                "Choose one of your known Warlock cantrips that deals damage. You can add your Charisma modifier to that spell's damage rolls."
            ],
        }

        content = factory.create_content(complex_prereq_data, ContentType.OPTFEATURE)

        assert content.name == "Advanced Invocation"
        assert content.has_prerequisite() is True
        prerequisite_summary = content.get_prerequisite_summary()
        assert "Level 2 Warlock" in prerequisite_summary
        assert "Warlock Cantrip That Deals Damage" in prerequisite_summary

    def test_optfeature_class_variant_data(self) -> None:
        """Test OptionalFeature with class feature variant data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test class feature variant
        variant_data = {
            "name": "Enhanced Maneuver",
            "source": {"abbreviation": "TCE", "full": "Tasha's Cauldron of Everything"},
            "featureType": ["MV:B"],
            "isClassFeatureVariant": True,
            "entries": ["This is an enhanced version of the standard maneuver."],
        }

        content = factory.create_content(variant_data, ContentType.OPTFEATURE)

        assert content.name == "Enhanced Maneuver"
        assert content.is_class_variant() is True
        assert content.is_maneuver() is True

    def test_optfeature_feature_category_enum(self) -> None:
        """Test OptionalFeature feature category enum functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test known feature type enum matching
        enum_test_data = {
            "name": "Test Feature",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "featureType": ["EI"],
            "entries": ["Test entry"],
        }

        content = factory.create_content(enum_test_data, ContentType.OPTFEATURE)

        category = content.get_feature_category()
        assert category is not None
        assert category.value == "EI"

    def test_optfeature_minimal_data(self) -> None:
        """Test OptionalFeature with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Feature",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "featureType": ["OTH"],
        }

        content = factory.create_content(minimal_data, ContentType.OPTFEATURE)

        assert content.name == "Minimal Feature"
        assert content.get_feature_types() == ["OTH"]
        assert content.has_prerequisite() is False
        assert content.has_level_requirement() is False
        assert content.get_minimum_level() == 1  # Default
        assert content.consumes_resources() is False
        assert content.grants_additional_spells() is False

    def test_optfeature_validation_errors(self) -> None:
        """Test OptionalFeature validation errors."""
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
                "featureType": ["EI"],
            }
            factory.create_content(invalid_data, ContentType.OPTFEATURE)

        # Test with missing required featureType field
        with pytest.raises(ValidationError):
            missing_type_data = {
                "name": "Test Feature",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                # Missing required 'featureType' field
            }
            factory.create_content(missing_type_data, ContentType.OPTFEATURE)

    def test_optfeature_omnidexer_integration(self) -> None:
        """Test OptionalFeature integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify OptionalFeature is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.OPTFEATURE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.OPTFEATURE in json_types

    def test_optfeature_file_patterns(self) -> None:
        """Test OptionalFeature file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify OptionalFeature patterns are registered
        assert ContentType.OPTFEATURE in content_patterns
        patterns = content_patterns[ContentType.OPTFEATURE]
        assert "optfeature" in patterns
        assert "optfeatures" in patterns
        assert "optionalfeature" in patterns
        assert "optionalfeatures" in patterns

    def test_optfeature_registry_consistency(self) -> None:
        """Test that OptionalFeature registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has OptionalFeature
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        optfeature_registration = registrations.get("optfeature")
        assert optfeature_registration is not None
        assert optfeature_registration.enum_value == "optfeature"

        # Check ContentFactory has OptionalFeature
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.OPTFEATURE in supported_factory_types

        # Check Omnidexer has OptionalFeature
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.OPTFEATURE in supported_omnidexer_types
