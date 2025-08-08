"""Tests for LegendaryGroup content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestLegendaryGroupMigration:
    """Test LegendaryGroup content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_legendarygroup_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers LegendaryGroup automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "LEGENDARYGROUP")
        assert ContentType.LEGENDARYGROUP == "legendarygroup"

    def test_legendarygroup_content_factory_integration(self) -> None:
        """Test LegendaryGroup works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an Aboleth legendary group
        aboleth_data = {
            "name": "Aboleth",
            "source": {"abbreviation": "MM", "full": "Monster Manual"},
            "page": 13,
            "lairActions": [
                "When fighting inside its lair, an aboleth can invoke the ambient magic to take lair actions. On initiative count 20 (losing initiative ties), the aboleth takes a lair action to cause one of the following effects:",
                {
                    "type": "list",
                    "items": [
                        "The aboleth casts phantasmal force (no components required) on any number of creatures it can see within 60 feet of it.",
                        "Pools of water within 90 feet of the aboleth surge outward in a grasping tide.",
                        "Water in the aboleth's lair magically becomes a conduit for the creature's rage.",
                    ],
                },
            ],
            "regionalEffects": [
                "The region containing an aboleth's lair is warped by the creature's presence, which creates one or more of the following effects:",
                {
                    "type": "list",
                    "items": [
                        "Underground surfaces within 1 mile of the aboleth's lair are slimy and wet and are difficult terrain.",
                        "Water sources within 1 mile of the lair are supernaturally fouled.",
                        "As an action, the aboleth can create an illusory image of itself within 1 mile of the lair.",
                    ],
                },
                "If the aboleth dies, the first two effects fade over the course of 3d10 days.",
            ],
        }

        content = factory.create_content(aboleth_data, ContentType.LEGENDARYGROUP)

        assert content.name == "Aboleth"
        assert content.source.abbreviation == "MM"
        assert content.has_lair_actions() is True
        assert content.has_regional_effects() is True
        assert content.get_lair_action_count() == 2
        assert content.get_regional_effect_count() == 3
        assert content.is_regional_based() is True

    def test_legendarygroup_lair_only_data(self) -> None:
        """Test LegendaryGroup with only lair actions."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a lair-only legendary group
        lair_only_data = {
            "name": "Dragon Lair",
            "source": {"abbreviation": "MM", "full": "Monster Manual"},
            "lairActions": [
                "On initiative count 20 (losing initiative ties), the dragon takes a lair action to cause one of the following effects:",
                {
                    "type": "list",
                    "items": [
                        "Magma erupts from a point on the ground the dragon can see within 120 feet of it.",
                        "The dragon creates an earthquake. Each creature must succeed on a DC 15 Dexterity saving throw or be knocked prone.",
                        "Volcanic gases form a cloud in a 20-foot-radius sphere centered on a point the dragon can see within 120 feet of it.",
                    ],
                },
            ],
        }

        content = factory.create_content(lair_only_data, ContentType.LEGENDARYGROUP)

        assert content.name == "Dragon Lair"
        assert content.has_lair_actions() is True
        assert content.has_regional_effects() is False
        assert content.is_lair_based() is True
        assert content.is_regional_based() is False
        assert content.get_lair_action_count() == 2

    def test_legendarygroup_mythic_encounter_data(self) -> None:
        """Test LegendaryGroup with mythic encounter mechanics."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a legendary group with mythic encounter
        mythic_data = {
            "name": "Ancient Dragon Mythic",
            "source": {"abbreviation": "MOT", "full": "Mythic Odysseys of Theros"},
            "mythicEncounter": [
                "This legendary creature has a mythic encounter phase that begins when it drops to half its hit points.",
                {
                    "type": "list",
                    "items": [
                        "The creature regains all expended legendary actions.",
                        "The creature's legendary actions are enhanced with additional effects.",
                        "New lair actions become available during the mythic phase.",
                    ],
                },
            ],
            "lairActions": [
                "During the mythic phase, additional lair actions become available."
            ],
        }

        content = factory.create_content(mythic_data, ContentType.LEGENDARYGROUP)

        assert content.name == "Ancient Dragon Mythic"
        assert content.has_mythic_encounter() is True
        assert content.get_mythic_encounter_count() == 2
        assert content.has_lair_actions() is True

    def test_legendarygroup_summary_functionality(self) -> None:
        """Test legendary group summary generation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive legendary group
        full_data = {
            "name": "Complete Legendary Group",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "lairActions": ["Action 1", "Action 2"],
            "regionalEffects": ["Effect 1", "Effect 2", "Effect 3"],
            "mythicEncounter": ["Mythic 1"],
        }

        content = factory.create_content(full_data, ContentType.LEGENDARYGROUP)

        summary = content.get_summary()
        assert "2 lair actions" in summary
        assert "3 regional effects" in summary
        assert "1 mythic encounter mechanics" in summary

    def test_legendarygroup_minimal_data(self) -> None:
        """Test LegendaryGroup with minimal data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Legendary Group",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
        }

        content = factory.create_content(minimal_data, ContentType.LEGENDARYGROUP)

        assert content.name == "Minimal Legendary Group"
        assert content.has_lair_actions() is False
        assert content.has_regional_effects() is False
        assert content.has_mythic_encounter() is False
        assert content.get_summary() == "No special mechanics"

    def test_legendarygroup_validation_errors(self) -> None:
        """Test LegendaryGroup validation errors."""
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
            }
            factory.create_content(invalid_data, ContentType.LEGENDARYGROUP)

    def test_legendarygroup_omnidexer_integration(self) -> None:
        """Test LegendaryGroup integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify LegendaryGroup is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.LEGENDARYGROUP in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.LEGENDARYGROUP in json_types

    def test_legendarygroup_file_patterns(self) -> None:
        """Test LegendaryGroup file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify LegendaryGroup patterns are registered
        assert ContentType.LEGENDARYGROUP in content_patterns
        patterns = content_patterns[ContentType.LEGENDARYGROUP]
        assert "legendarygroup" in patterns
        assert "legendarygroups" in patterns

    def test_legendarygroup_registry_consistency(self) -> None:
        """Test that LegendaryGroup registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has LegendaryGroup
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        legendarygroup_registration = registrations.get("legendarygroup")
        assert legendarygroup_registration is not None
        assert legendarygroup_registration.enum_value == "legendarygroup"

        # Check ContentFactory has LegendaryGroup
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.LEGENDARYGROUP in supported_factory_types

        # Check Omnidexer has LegendaryGroup
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.LEGENDARYGROUP in supported_omnidexer_types
