"""Tests for remaining content type migrations (Vehicle, Class, Rule Types, Fluff) to registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestRemainingTypesMigration:
    """Test that remaining content types work with registry system."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure clean state
        reset_test_environment()

    def test_vehicle_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Vehicle correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.vehicles import Vehicle
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="vehicle",
                file_patterns=["vehicle", "vehicles"],
                statblock_tags=["vehicle"],
                loader_type="json",
            )
            class TestVehicle(Vehicle):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "vehicle"
        assert metadata.model_class == TestVehicle
        assert metadata.file_patterns == ["vehicle", "vehicles"]
        assert metadata.statblock_tags == ["vehicle"]
        assert metadata.loader_type == "json"

    def test_class_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers Class correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.classes import Class
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="class",
                file_patterns=["class", "classes"],
                statblock_tags=["class"],
                loader_type="json",
            )
            class TestClass(Class):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "class"
        assert metadata.model_class == TestClass
        assert metadata.file_patterns == ["class", "classes"]
        assert metadata.statblock_tags == ["class"]
        assert metadata.loader_type == "json"

    def test_class_feature_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers ClassFeature correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.classes import ClassFeature
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="classFeature",
                file_patterns=["classFeature", "classfeature"],
                statblock_tags=["classFeature"],
                loader_type="json",
            )
            class TestClassFeature(ClassFeature):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "classFeature"
        assert metadata.model_class == TestClassFeature
        assert metadata.file_patterns == ["classFeature", "classfeature"]
        assert metadata.statblock_tags == ["classFeature"]
        assert metadata.loader_type == "json"

    def test_subclass_feature_decorator_registers_automatically(self):
        """Test that the @content_type decorator registers SubclassFeature correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.classes import SubclassFeature
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="subclassFeature",
                file_patterns=["subclassFeature", "subclassfeature"],
                statblock_tags=["subclassFeature"],
                loader_type="json",
            )
            class TestSubclassFeature(SubclassFeature):
                pass

        # Verify that the mock registry's register method was called
        assert mock_registry.register.called
        call_args = mock_registry.register.call_args[0]
        metadata = call_args[0]

        assert isinstance(metadata, ContentTypeMetadata)
        assert metadata.enum_value == "subclassFeature"
        assert metadata.model_class == TestSubclassFeature
        assert metadata.file_patterns == ["subclassFeature", "subclassfeature"]
        assert metadata.statblock_tags == ["subclassFeature"]
        assert metadata.loader_type == "json"

    def test_rule_types_decorators_register_automatically(self):
        """Test that rule type decorators register correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.rule_types import (
            Action,
            Condition,
            Hazard,
            Sense,
            Status,
        )
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="action",
                file_patterns=["action", "actions", "conditionsdiseases"],
                statblock_tags=["action"],
                loader_type="json",
            )
            class TestAction(Action):
                pass

            @content_type(
                enum_value="condition",
                file_patterns=["condition", "conditions", "conditionsdiseases"],
                statblock_tags=["condition"],
                loader_type="json",
            )
            class TestCondition(Condition):
                pass

            @content_type(
                enum_value="sense",
                file_patterns=["sense", "senses", "conditionsdiseases"],
                statblock_tags=["sense"],
                loader_type="json",
            )
            class TestSense(Sense):
                pass

            @content_type(
                enum_value="hazard",
                file_patterns=["hazard", "hazards", "conditionsdiseases"],
                statblock_tags=["hazard"],
                loader_type="json",
            )
            class TestHazard(Hazard):
                pass

            @content_type(
                enum_value="status",
                file_patterns=["status", "statuses", "conditionsdiseases"],
                statblock_tags=["status"],
                loader_type="json",
            )
            class TestStatus(Status):
                pass

        # Verify that the mock registry's register method was called 5 times
        assert mock_registry.register.call_count == 5

        # Check specific calls were made with correct metadata
        call_args_list = mock_registry.register.call_args_list

        # Verify action metadata
        action_metadata = call_args_list[0][0][0]
        assert isinstance(action_metadata, ContentTypeMetadata)
        assert action_metadata.enum_value == "action"
        assert action_metadata.model_class == TestAction
        assert "conditionsdiseases" in action_metadata.file_patterns

        # Verify condition metadata
        condition_metadata = call_args_list[1][0][0]
        assert isinstance(condition_metadata, ContentTypeMetadata)
        assert condition_metadata.enum_value == "condition"
        assert condition_metadata.model_class == TestCondition

        # Verify sense metadata
        sense_metadata = call_args_list[2][0][0]
        assert isinstance(sense_metadata, ContentTypeMetadata)
        assert sense_metadata.enum_value == "sense"
        assert sense_metadata.model_class == TestSense

        # Verify hazard metadata
        hazard_metadata = call_args_list[3][0][0]
        assert isinstance(hazard_metadata, ContentTypeMetadata)
        assert hazard_metadata.enum_value == "hazard"
        assert hazard_metadata.model_class == TestHazard

        # Verify status metadata
        status_metadata = call_args_list[4][0][0]
        assert isinstance(status_metadata, ContentTypeMetadata)
        assert status_metadata.enum_value == "status"
        assert status_metadata.model_class == TestStatus

    def test_fluff_decorators_register_automatically(self):
        """Test that fluff type decorators register correctly."""
        from unittest.mock import Mock, patch

        from dnd5e.core.models.fluff import CreatureFluff, ItemFluff, SpellFluff
        from dnd5e.core.registry import content_type
        from dnd5e.core.registry.content_type_registry import ContentTypeMetadata

        # Mock the registry to test decorator behavior
        mock_registry = Mock()

        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry",
            return_value=mock_registry,
        ):

            @content_type(
                enum_value="spellFluff",
                file_patterns=["spellFluff", "spell-fluff", "spells"],
                statblock_tags=["spellFluff"],
                loader_type="fluff",
            )
            class TestSpellFluff(SpellFluff):
                pass

            @content_type(
                enum_value="creatureFluff",
                file_patterns=["creatureFluff", "creature-fluff", "bestiary"],
                statblock_tags=["creatureFluff"],
                loader_type="fluff",
            )
            class TestCreatureFluff(CreatureFluff):
                pass

            @content_type(
                enum_value="itemFluff",
                file_patterns=["itemFluff", "item-fluff", "items"],
                statblock_tags=["itemFluff"],
                loader_type="fluff",
            )
            class TestItemFluff(ItemFluff):
                pass

        # Verify that the mock registry's register method was called 3 times
        assert mock_registry.register.call_count == 3

        # Check specific calls were made with correct metadata
        call_args_list = mock_registry.register.call_args_list

        # Verify spell fluff metadata
        spell_fluff_metadata = call_args_list[0][0][0]
        assert isinstance(spell_fluff_metadata, ContentTypeMetadata)
        assert spell_fluff_metadata.enum_value == "spellFluff"
        assert spell_fluff_metadata.model_class == TestSpellFluff
        assert spell_fluff_metadata.loader_type == "fluff"

        # Verify creature fluff metadata
        creature_fluff_metadata = call_args_list[1][0][0]
        assert isinstance(creature_fluff_metadata, ContentTypeMetadata)
        assert creature_fluff_metadata.enum_value == "creatureFluff"
        assert creature_fluff_metadata.model_class == TestCreatureFluff
        assert creature_fluff_metadata.loader_type == "fluff"

        # Verify item fluff metadata
        item_fluff_metadata = call_args_list[2][0][0]
        assert isinstance(item_fluff_metadata, ContentTypeMetadata)
        assert item_fluff_metadata.enum_value == "itemFluff"
        assert item_fluff_metadata.model_class == TestItemFluff
        assert item_fluff_metadata.loader_type == "fluff"

    def test_remaining_enums_exist_in_content_type(self):
        """Test that remaining type enums exist in ContentType enum."""
        # Import remaining types to register via decorator (if they're already decorated in the source)
        from dnd5e.core.models import classes, fluff, rule_types, vehicles

        # Verify these enums exist in the ContentType enum
        assert hasattr(ContentType, "VEHICLE")
        assert ContentType.VEHICLE == "vehicle"
        assert hasattr(ContentType, "CLASS")
        assert ContentType.CLASS == "class"
        assert hasattr(ContentType, "CLASS_FEATURE")
        assert ContentType.CLASS_FEATURE == "classFeature"
        assert hasattr(ContentType, "SUBCLASS_FEATURE")
        assert ContentType.SUBCLASS_FEATURE == "subclassFeature"

        # Rule types
        assert hasattr(ContentType, "ACTION")
        assert ContentType.ACTION == "action"
        assert hasattr(ContentType, "CONDITION")
        assert ContentType.CONDITION == "condition"
        assert hasattr(ContentType, "SENSE")
        assert ContentType.SENSE == "sense"
        assert hasattr(ContentType, "HAZARD")
        assert ContentType.HAZARD == "hazard"
        assert hasattr(ContentType, "STATUS")
        assert ContentType.STATUS == "status"

        # Fluff types
        assert hasattr(ContentType, "SPELL_FLUFF")
        assert ContentType.SPELL_FLUFF == "spellFluff"
        assert hasattr(ContentType, "CREATURE_FLUFF")
        assert ContentType.CREATURE_FLUFF == "creatureFluff"
        assert hasattr(ContentType, "ITEM_FLUFF")
        assert ContentType.ITEM_FLUFF == "itemFluff"

    def test_vehicle_content_creation(self):
        """Test that Vehicle content can be created and validated."""
        from dnd5e.core.models.vehicles import (
            Vehicle,
            VehicleArmor,
            VehicleHitPoints,
            VehicleSpeed,
        )

        # Create a simple vehicle instance
        vehicle = Vehicle(
            name="Galley",
            source="DMG",
            vehicleType="watercraft",
            size=["Gargantuan"],
            dimensions=["130 ft. by 20 ft."],
            cost=30000,
            speed=40,
            ac=[15],
            hp=500,
            crew=20,
            passenger=150,
            entries=["A galley is a large oared vessel..."],
        )

        assert vehicle.name == "Galley"
        assert vehicle.source.abbreviation == "DMG"
        assert vehicle.vehicle_type == "watercraft"  # This accesses the aliased field
        assert vehicle.size == ["Gargantuan"]
        assert vehicle.cost == 30000
        assert vehicle.entries == ["A galley is a large oared vessel..."]

    def test_class_content_creation(self):
        """Test that Class content can be created and validated."""
        from dnd5e.core.models.classes import Class, StartingProficiencies

        # Create a sidekick class instance (bypasses required field validation)
        char_class = Class(
            name="Warrior Sidekick",
            source="PHB",
            isSidekick=True,
            startingProficiencies=StartingProficiencies(
                armor=["light armor", "medium armor"], weapons=["simple weapons"]
            ),
        )

        assert char_class.name == "Warrior Sidekick"
        assert char_class.source.abbreviation == "PHB"
        assert char_class.is_sidekick is True
        assert char_class.starting_proficiencies.armor is not None

    def test_rule_types_content_creation(self):
        """Test that rule type content can be created and validated."""
        from dnd5e.core.models.rule_types import Action, Condition

        # Create an action instance
        action = Action(
            name="Attack",
            source="PHB",
            page=192,
            entries=[
                "The most common action to take in combat is the Attack action..."
            ],
            time=[{"number": 1, "unit": "action"}],
        )

        assert action.name == "Attack"
        assert action.source.abbreviation == "PHB"
        assert action.page == 192
        assert len(action.entries) == 1
        assert len(action.time) == 1

        # Create a condition instance
        condition = Condition(
            name="Blinded",
            source="PHB",
            page=290,
            entries=[
                "A blinded creature can't see and automatically fails any ability check..."
            ],
        )

        assert condition.name == "Blinded"
        assert condition.source.abbreviation == "PHB"
        assert condition.page == 290
        assert len(condition.entries) == 1

    def test_fluff_content_creation(self):
        """Test that fluff content can be created and validated."""
        from dnd5e.core.models.fluff import FluffEntry, SpellFluff

        # Create a spell fluff instance
        spell_fluff = SpellFluff(
            name="Fireball",
            source="PHB",
            entries=[
                FluffEntry(content="The orange glow of flames dances in the air...")
            ],
        )

        assert spell_fluff.name == "Fireball"
        assert spell_fluff.source.abbreviation == "PHB"
        assert len(spell_fluff.entries) == 1
        assert "orange glow" in spell_fluff.entries[0].content

    def test_initialization_flow_works_with_all_types(self):
        """Test that initialization flow works without errors with all migrated types."""
        try:
            initialize_content_types()
            # If we get here, initialization completed successfully
            assert True
        except Exception as e:
            pytest.fail(f"Initialization failed: {e}")
