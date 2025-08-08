"""Tests for Trap content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestTrapMigration:
    """Test Trap content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_trap_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Trap automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "TRAP")
        assert ContentType.TRAP == "trap"

    def test_trap_content_factory_integration(self) -> None:
        """Test Trap works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a complex mechanical trap
        falling_net_data = {
            "name": "Falling Net",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "page": 122,
            "trapHazType": "MECH",
            "entries": ["A net falls on creatures that trigger this trap."],
            "trigger": ["A creature walks into the area"],
            "effect": [
                "The net falls, and creatures in the area must make a DC 10 Dexterity saving throw.",
                "On a failure, the creature is restrained by the net.",
            ],
            "countermeasures": [
                "A DC 15 Perception check reveals the trap.",
                "A DC 15 Thieves' Tools check disables the trap.",
            ],
            "rating": [{"tier": 1, "threat": "setback"}],
            "skillCheck": [
                {"skill": "Perception", "dc": 15},
                {"skill": "Thieves' Tools", "dc": 15},
            ],
        }

        content = factory.create_content(falling_net_data, ContentType.TRAP)

        assert content.name == "Falling Net"
        assert content.source.abbreviation == "DMG"
        assert content.is_mechanical() is True
        assert content.is_magical() is False
        assert content.has_triggers() is True
        assert content.has_effects() is True
        assert content.has_countermeasures() is True
        assert content.can_be_detected() is True
        assert content.can_be_disabled() is True
        assert content.get_detection_difficulty() == 15
        assert content.get_disarm_difficulty() == 15

    def test_trap_hazard_types(self) -> None:
        """Test Trap hazard type classification."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.trap import TrapHazardType

        factory = ContentFactory()

        # Test magical trap
        magical_data = {
            "name": "Glyph of Warding",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "MAG",
            "entries": ["A magical glyph explodes when triggered."],
            "effect": ["3d8 thunder damage to creatures within 20 feet."],
        }

        magical_trap = factory.create_content(magical_data, ContentType.TRAP)
        assert magical_trap.get_trap_hazard_type() == TrapHazardType.MAGICAL
        assert magical_trap.is_magical() is True
        assert magical_trap.get_trap_type_description() == "Magical Trap"

        # Test environmental hazard
        env_data = {
            "name": "Lava Pool",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "ENV",
            "entries": ["A pool of molten lava blocks the path."],
            "effect": ["6d10 fire damage to creatures that enter the lava."],
        }

        env_hazard = factory.create_content(env_data, ContentType.TRAP)
        assert env_hazard.get_trap_hazard_type() == TrapHazardType.ENVIRONMENTAL
        assert env_hazard.is_environmental_hazard() is True
        assert env_hazard.get_trap_type_description() == "Environmental Hazard"

    def test_trap_threat_ratings(self) -> None:
        """Test Trap threat rating system."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.trap import ThreatLevel

        factory = ContentFactory()

        # Test trap with multiple threat ratings
        scaling_trap_data = {
            "name": "Poison Dart Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "MECH",
            "entries": ["Darts shoot from hidden holes in the wall."],
            "rating": [
                {"tier": 1, "threat": "dangerous"},
                {"tier": 2, "threat": "setback"},
                {"tier": 3, "threat": "setback"},
                {"tier": 4, "threat": "setback"},
            ],
            "effect": ["1d4 piercing damage plus poison"],
        }

        content = factory.create_content(scaling_trap_data, ContentType.TRAP)

        assert content.has_rating() is True
        assert content.get_threat_level_for_tier(1) == ThreatLevel.DANGEROUS
        assert content.get_threat_level_for_tier(2) == ThreatLevel.SETBACK
        assert content.is_dangerous_for_tier(1) is True
        assert content.is_deadly_for_tier(1) is False
        assert content.get_threat_level_description(1) == "Dangerous"
        assert content.get_threat_level_description(2) == "Setback"

        # Test all threat levels
        all_levels = content.get_all_threat_levels()
        assert len(all_levels) == 4
        assert all_levels[1] == ThreatLevel.DANGEROUS
        assert all_levels[2] == ThreatLevel.SETBACK

    def test_trap_defenses_and_properties(self) -> None:
        """Test Trap defenses and special properties."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test trap with full defensive stats
        armored_trap_data = {
            "name": "Animated Armor Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "MAG",
            "entries": ["A suit of armor animates and attacks."],
            "ac": 18,
            "hp": 33,
            "initiative": 0,
            "initiativeNote": "Acts on initiative count 0",
            "immune": ["poison", "psychic"],
            "conditionImmune": ["charmed", "exhaustion", "frightened"],
            "senses": ["blindsight 60 ft.", "darkvision 120 ft."],
            "effect": [
                "The armor makes two slam attacks: +4 to hit, 1d6+2 bludgeoning damage."
            ],
        }

        content = factory.create_content(armored_trap_data, ContentType.TRAP)

        assert content.has_defenses() is True
        assert content.ac == 18
        assert content.hp == 33
        assert content.has_initiative() is True
        assert content.initiative == 0
        assert content.has_immunities() is True
        assert len(content.get_damage_immunities_list()) == 2
        assert len(content.get_condition_immunities_list()) == 3
        assert "poison" in content.get_damage_immunities_list()
        assert "charmed" in content.get_condition_immunities_list()
        assert len(content.get_senses_list()) == 2

    def test_trap_skill_checks_and_saves(self) -> None:
        """Test Trap skill checks and saving throws."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test trap with complex interaction requirements
        complex_trap_data = {
            "name": "Puzzle Lock Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "CPLX",
            "entries": ["A complex puzzle must be solved to avoid the trap."],
            "skillCheck": [
                {"skill": "Investigation", "dc": 18},
                {"skill": "Thieves' Tools", "dc": 20},
                {"skill": "Arcana", "dc": 15},
            ],
            "savingThrow": [
                {"ability": "Dexterity", "dc": 16},
                {"ability": "Intelligence", "dc": 14},
            ],
            "trigger": ["Opening the chest without solving the puzzle"],
            "effect": ["Lightning bolt fills the room"],
        }

        content = factory.create_content(complex_trap_data, ContentType.TRAP)

        assert content.requires_skill_checks() is True
        assert content.requires_saving_throws() is True
        assert len(content.get_skill_checks_list()) == 3
        assert len(content.get_saving_throws_list()) == 2
        assert content.get_detection_difficulty() == 18  # Investigation check
        assert content.get_disarm_difficulty() == 20  # Thieves' Tools check

    def test_trap_complexity_rating(self) -> None:
        """Test Trap complexity rating system."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test simple trap
        simple_data = {
            "name": "Pit Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "SMPL",
            "entries": ["A covered pit opens beneath creatures."],
            "trigger": ["A creature steps on the cover"],
            "effect": ["1d6 bludgeoning damage from the fall"],
        }

        simple_trap = factory.create_content(simple_data, ContentType.TRAP)
        assert simple_trap.get_complexity_rating() == "Simple"

        # Test complex trap
        complex_data = {
            "name": "Master Thief's Vault",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "CPLX",
            "entries": ["An elaborate trap protecting a valuable vault."],
            "trigger": [
                "Opening the vault without the proper key",
                "Touching the vault with metal objects",
                "Casting spells near the vault",
            ],
            "effect": [
                "Poisonous gas fills the room",
                "Lightning arcs between metal surfaces",
                "Magical alarms sound throughout the building",
                "The vault seals permanently for 24 hours",
            ],
            "countermeasures": [
                "Dispel magic on the vault",
                "Thieves' tools to pick the lock",
                "Arcane knowledge to identify safe approach",
            ],
            "ac": 20,
            "hp": 50,
            "immune": ["all damage until disarmed"],
            "conditionImmune": ["all conditions"],
            "initiative": 10,
        }

        complex_trap = factory.create_content(complex_data, ContentType.TRAP)
        assert complex_trap.get_complexity_rating() == "Complex"

    def test_trap_counting_methods(self) -> None:
        """Test Trap counting methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test trap with multiple components
        multi_data = {
            "name": "Multi-Component Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "CPLX",
            "entries": ["A trap with multiple triggers and effects."],
            "trigger": ["Pressure plate", "Motion sensor", "Sound trigger"],
            "effect": ["Dart volley", "Alarm bell", "Gas release"],
            "countermeasures": ["Disable pressure plate", "Jam motion sensor"],
        }

        content = factory.create_content(multi_data, ContentType.TRAP)

        assert content.get_trigger_count() == 3
        assert content.get_effect_count() == 3
        assert content.get_countermeasure_count() == 2

    def test_trap_summary_functionality(self) -> None:
        """Test Trap summary generation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive trap summary
        summary_data = {
            "name": "Death Ray Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "MAG",
            "entries": ["A beam of deadly energy sweeps the room."],
            "rating": [
                {"tier": 1, "threat": "deadly"},
                {"tier": 2, "threat": "dangerous"},
            ],
            "trigger": ["Opening the door", "Entering the room"],
            "skillCheck": [
                {"skill": "Perception", "dc": 20},
                {"skill": "Arcana", "dc": 18},
            ],
            "countermeasures": ["Dispel the magical energy source"],
        }

        content = factory.create_content(summary_data, ContentType.TRAP)

        summary = content.get_trap_summary()
        assert "Magical Trap" in summary
        assert "T1: deadly" in summary
        assert "T2: dangerous" in summary
        assert "2 triggers" in summary
        assert "detect DC 20" in summary
        assert "moderate complexity" in summary

    def test_trap_minimal_data(self) -> None:
        """Test Trap with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Simple Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "entries": ["A basic trap."],
        }

        content = factory.create_content(minimal_data, ContentType.TRAP)

        assert content.name == "Simple Trap"
        assert content.get_trap_type_description() == "Unknown Trap Type"
        assert content.has_rating() is False
        assert content.has_triggers() is False
        assert content.has_effects() is False
        assert content.has_countermeasures() is False
        assert content.has_defenses() is False
        assert content.has_immunities() is False
        assert content.can_be_detected() is False
        assert content.can_be_disabled() is False

    def test_trap_validation_errors(self) -> None:
        """Test Trap validation errors."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty name
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "",  # Empty name should fail
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "entries": ["Test entry."],
            }
            factory.create_content(invalid_data, ContentType.TRAP)

        # Test with invalid AC
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Test Trap",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "entries": ["Test entry."],
                "ac": -5,  # Invalid AC should fail
            }
            factory.create_content(invalid_data, ContentType.TRAP)

        # Test with invalid HP
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Test Trap",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "entries": ["Test entry."],
                "hp": 0,  # Invalid HP should fail
            }
            factory.create_content(invalid_data, ContentType.TRAP)

    def test_trap_field_normalization(self) -> None:
        """Test Trap field normalization and validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.trap import TrapHazardType

        factory = ContentFactory()

        # Test string to list conversion
        string_data = {
            "name": "String Fields Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "trapHazType": "mech",  # Should convert to MECHANICAL
            "entries": ["Test trap."],
            "trigger": "Single trigger",  # Should convert to list
            "effect": "Single effect",  # Should convert to list
            "countermeasures": "Single countermeasure",  # Should convert to list
        }

        content = factory.create_content(string_data, ContentType.TRAP)
        assert content.get_trap_hazard_type() == TrapHazardType.MECHANICAL
        assert isinstance(content.trigger, list)
        assert len(content.trigger) == 1
        assert content.trigger[0] == "Single trigger"
        assert isinstance(content.effect, list)
        assert isinstance(content.countermeasures, list)

    def test_trap_omnidexer_integration(self) -> None:
        """Test Trap integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Trap is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.TRAP in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.TRAP in json_types

    def test_trap_file_patterns(self) -> None:
        """Test Trap file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Trap patterns are registered
        assert ContentType.TRAP in content_patterns
        patterns = content_patterns[ContentType.TRAP]
        assert "trap" in patterns
        assert "traps" in patterns
        assert "trapshazards" in patterns

    def test_trap_registry_consistency(self) -> None:
        """Test that Trap registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Trap
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        trap_registration = registrations.get("trap")
        assert trap_registration is not None
        assert trap_registration.enum_value == "trap"

        # Check ContentFactory has Trap
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.TRAP in supported_factory_types

        # Check Omnidexer has Trap
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.TRAP in supported_omnidexer_types

    def test_trap_edge_cases(self) -> None:
        """Test Trap edge cases and boundary conditions."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test trap with no threat ratings for specific tier
        no_rating_data = {
            "name": "No Rating Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "entries": ["A trap without threat ratings."],
            "rating": [{"tier": 1, "threat": "setback"}],
        }

        content = factory.create_content(no_rating_data, ContentType.TRAP)

        # Should return empty list for non-existent tier
        assert len(content.get_ratings_by_tier(3)) == 0
        assert content.get_threat_level_for_tier(3).value == "unknown"

        # Test detection/disarm with no relevant skill checks
        no_detection_data = {
            "name": "No Detection Trap",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "entries": ["A trap that can't be detected normally."],
            "skillCheck": [{"skill": "Athletics", "dc": 15}],  # Not detection skill
        }

        content = factory.create_content(no_detection_data, ContentType.TRAP)
        assert (
            content.get_detection_difficulty() == 15
        )  # Falls back to first skill check
        assert content.get_disarm_difficulty() is None  # No thieves' tools check
