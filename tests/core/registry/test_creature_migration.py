"""Tests for Creature content type migration to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestCreatureMigration:
    """Test that Creature content type works with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_creature_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Creature correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.creatures import Creature
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="creature",
                file_patterns=["bestiary", "monster", "creatures"],
                statblock_tags=["creature"],
                loader_type="json",
            )
            class TestCreature(Creature):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "creature"
        assert metadata.model_class == TestCreature
        assert metadata.file_patterns == ["bestiary", "monster", "creatures"]
        assert metadata.statblock_tags == ["creature"]
        assert metadata.loader_type == "json"

    def test_creature_enum_created_dynamically(self):
        """Test that CREATURE enum is created dynamically during finalization."""
        # Import creatures to register via decorator
        from dnd5e.core.models import creatures

        # Initially CREATURE should already exist (it's in ContentType enum)
        assert hasattr(ContentType, "CREATURE")
        assert ContentType.CREATURE == "creature"

        # Initialize should still work and not conflict
        initialize_content_types()

        # Verify enum still exists and works
        assert hasattr(ContentType, "CREATURE")
        assert ContentType.CREATURE == "creature"

    def test_creature_content_creation(self):
        """Test that Creature content can be created and validated."""
        from dnd5e.core.models.creatures import (
            ArmorClass,
            Creature,
            CreatureType,
            HitPoints,
            Speed,
        )

        # Create a simple creature instance
        creature = Creature(
            name="Test Goblin",
            source="MM",
            size=["Small"],
            type="humanoid",
            alignment=["chaotic evil"],
            ac=[ArmorClass(ac=15)],
            hp=HitPoints(average=7, formula="2d6"),
            speed=Speed(walk=30),
            str=8,  # Using alias
            dex=14,
            con=10,
            int=10,
            wis=8,
            cha=8,
        )

        assert creature.name == "Test Goblin"
        assert creature.source.abbreviation == "MM"
        assert creature.size == ["Small"]
        assert isinstance(creature.type, CreatureType)
        assert creature.alignment == ["chaotic evil"]
        assert creature.strength == 8
        assert creature.dexterity == 14

    def test_creature_with_complex_abilities(self):
        """Test that Creature works with complex ability structures."""
        from dnd5e.core.models.creatures import (
            Ability,
            ArmorClass,
            Creature,
            HitPoints,
            Speed,
        )

        creature = Creature(
            name="Test Dragon",
            source="MM",
            size=["Large"],
            type="dragon",
            alignment=["lawful evil"],
            ac=[ArmorClass(ac=18)],
            hp=HitPoints(average=200, formula="16d12+112"),
            speed=Speed(walk=40, fly=80),
            str=23,
            dex=10,
            con=25,
            int=16,
            wis=13,
            cha=21,
            trait=[
                Ability(
                    name="Legendary Resistance",
                    entries=[
                        "If the dragon fails a saving throw, it can choose to succeed instead (3/Day)."
                    ],
                )
            ],
            action=[
                Ability(
                    name="Multiattack",
                    entries=[
                        "The dragon can use its Frightful Presence. It then makes three attacks."
                    ],
                )
            ],
        )

        assert creature.name == "Test Dragon"
        assert len(creature.trait) == 1
        assert creature.trait[0].name == "Legendary Resistance"
        assert len(creature.action) == 1
        assert creature.action[0].name == "Multiattack"

    def test_creature_formatting_methods(self):
        """Test creature formatting methods work correctly."""
        from dnd5e.core.models.creatures import ArmorClass, Creature, HitPoints, Speed

        creature = Creature(
            name="Test Beast",
            source="MM",
            size=["Medium"],
            type="beast",
            alignment=["unaligned"],
            ac=[ArmorClass(ac=12)],
            hp=HitPoints(average=26, formula="4d8+8"),
            speed=Speed(walk=40, climb=30),
            str=16,
            dex=14,
            con=15,
            int=2,
            wis=12,
            cha=6,
            cr="1/2",
        )

        # Test various formatting methods
        assert "Medium beast, unaligned" in creature.get_size_type_alignment()
        assert "12" in creature.get_ac_text()
        assert "26 (4d8+8)" in creature.get_hp_text()
        assert "40 ft., climb 30 ft." in creature.get_speed_text()
        assert "1/2" in creature.get_cr_text()

    def test_initialization_flow_works(self):
        """Test that initialization flow works without errors."""
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
