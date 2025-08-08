"""Tests for OptionalFeature content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestOptionalFeatureMigration:
    """Test OptionalFeature content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_optionalfeature_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers OptionalFeature automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "OPTIONALFEATURE")
        assert ContentType.OPTIONALFEATURE == "optionalfeature"

    def test_optionalfeature_content_factory_integration(self) -> None:
        """Test OptionalFeature works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a fighting style
        fighting_style_data = {
            "name": "Archery",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["FS:F", "FS:R"],
            "entries": [
                "You gain a +2 bonus to attack rolls you make with ranged weapons."
            ],
        }

        content = factory.create_content(
            fighting_style_data, ContentType.OPTIONALFEATURE
        )

        assert content.name == "Archery"
        assert content.feature_type == ["FS:F", "FS:R"]
        assert len(content.entries) == 1
        assert content.source.abbreviation == "PHB"

    def test_optionalfeature_eldritch_invocation_data(self) -> None:
        """Test OptionalFeature with eldritch invocation data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an eldritch invocation with prerequisites
        invocation_data = {
            "name": "Agonizing Blast",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["EI"],
            "prerequisite": [{"spell": ["eldritch blast#c"]}],
            "entries": [
                "When you cast {@spell eldritch blast}, add your Charisma modifier to the damage it deals on a hit."
            ],
        }

        content = factory.create_content(invocation_data, ContentType.OPTIONALFEATURE)

        assert content.name == "Agonizing Blast"
        assert content.feature_type == ["EI"]
        assert content.prerequisite is not None
        assert len(content.prerequisite) == 1
        assert content.prerequisite[0].spell == ["eldritch blast#c"]

    def test_optionalfeature_metamagic_data(self) -> None:
        """Test OptionalFeature with metamagic data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating metamagic option
        metamagic_data = {
            "name": "Quickened Spell",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["MM"],
            "entries": [
                "When you cast a spell that has a casting time of 1 action, you can spend 2 sorcery points to change the casting time to 1 bonus action for this casting."
            ],
        }

        content = factory.create_content(metamagic_data, ContentType.OPTIONALFEATURE)

        assert content.name == "Quickened Spell"
        assert content.feature_type == ["MM"]
        assert "sorcery points" in content.entries[0]

    def test_optionalfeature_maneuver_with_consumption(self) -> None:
        """Test OptionalFeature with resource consumption (maneuver)."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a battlemaster maneuver
        maneuver_data = {
            "name": "Trip Attack",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["MV:B"],
            "consumes": {"name": "Superiority Die"},
            "entries": [
                "When you hit a creature with a weapon attack, you can expend one superiority die to attempt to knock the target down."
            ],
        }

        content = factory.create_content(maneuver_data, ContentType.OPTIONALFEATURE)

        assert content.name == "Trip Attack"
        assert content.feature_type == ["MV:B"]
        assert content.consumes is not None
        assert content.consumes.name == "Superiority Die"

    def test_optionalfeature_additional_spells(self) -> None:
        """Test OptionalFeature with additional spells."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an optional feature that grants spells
        spell_granting_data = {
            "name": "Magic Initiate",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["OF"],
            "additionalSpells": [{"known": {"1": ["cure wounds", "detect magic"]}}],
            "entries": [
                "You learn two cantrips of your choice from the cleric spell list."
            ],
        }

        content = factory.create_content(
            spell_granting_data, ContentType.OPTIONALFEATURE
        )

        assert content.name == "Magic Initiate"
        assert content.additional_spells is not None
        assert len(content.additional_spells) == 1
        assert content.additional_spells[0].known is not None

    def test_optionalfeature_feature_type_validation(self) -> None:
        """Test feature type validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty feature type (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Invalid Feature",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "featureType": [],  # Empty list should fail
                "entries": ["Test entry"],
            }
            factory.create_content(invalid_data, ContentType.OPTIONALFEATURE)

    def test_optionalfeature_display_methods(self) -> None:
        """Test display helper methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test display formatting
        multi_type_data = {
            "name": "Dual Wielder",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "featureType": ["FS:F", "FS:R", "EI"],
            "entries": ["Test entry"],
        }

        content = factory.create_content(multi_type_data, ContentType.OPTIONALFEATURE)

        display_types = content.get_feature_types_display()
        assert "Fighting Style (F)" in display_types
        assert "Fighting Style (R)" in display_types
        assert "Eldritch Invocation" in display_types

    def test_optionalfeature_omnidexer_integration(self) -> None:
        """Test OptionalFeature integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify OptionalFeature is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.OPTIONALFEATURE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.OPTIONALFEATURE in json_types

    def test_optionalfeature_configurable_source_manager_integration(self) -> None:
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
        assert ContentType.OPTIONALFEATURE in content_patterns
        patterns = content_patterns[ContentType.OPTIONALFEATURE]
        assert "optionalfeature" in patterns
        assert "optionalfeatures" in patterns

    def test_optionalfeature_registry_consistency(self) -> None:
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
        optionalfeature_registration = registrations.get("optionalfeature")
        assert optionalfeature_registration is not None
        assert optionalfeature_registration.enum_value == "optionalfeature"

        # Check ContentFactory has OptionalFeature
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.OPTIONALFEATURE in supported_factory_types

        # Check Omnidexer has OptionalFeature
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.OPTIONALFEATURE in supported_omnidexer_types
