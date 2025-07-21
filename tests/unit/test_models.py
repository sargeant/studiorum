"""Tests for data models."""

from typing import Any

import pytest
from pydantic import ValidationError

from dnd5e.core.models.content import Source  # type: ignore
from dnd5e.core.models.creatures import (  # type: ignore
    Ability,
    ArmorClass,
    Creature,
    CreatureType,
    HitPoints,
    Speed,
)
from dnd5e.core.models.spells import Spell, SpellComponent  # type: ignore


class TestSource:
    """Tests for Source model."""

    def test_source_creation(self) -> None:
        """Test basic source creation."""
        source: Any = Source(abbreviation="PHB", name="Player's Handbook", page=123)
        assert source.abbreviation == "PHB"
        assert source.name == "Player's Handbook"
        assert source.page == 123

    def test_source_str(self) -> None:
        """Test source string representation."""
        source: Any = Source(abbreviation="PHB", name="Player's Handbook", page=123)
        assert str(source) == "PHB, p. 123"

        source_no_page: Any = Source(abbreviation="PHB", name="Player's Handbook")
        assert str(source_no_page) == "PHB"


class TestSpell:
    """Tests for Spell model."""

    def test_spell_creation(self, sample_spell_data: Any) -> None:
        """Test basic spell creation."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.name == "Fireball"
        assert spell.level == 3
        assert spell.school == "Evocation"  # Should be expanded from "V"

    def test_spell_validation_error(self) -> None:
        """Test spell validation with invalid data."""
        with pytest.raises(ValidationError):
            Spell.model_validate(
                {"name": "Test Spell", "level": 10, "school": "V"}  # Invalid level > 9
            )

    def test_spell_level_text(self, sample_spell: Any) -> None:
        """Test spell level text formatting."""
        assert sample_spell.get_level_text() == "3rd-level evocation"

        cantrip_spell = Spell.model_validate(
            {
                "name": "Test Cantrip",
                "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
                "level": 0,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point"},
                "components": {"v": True},
                "duration": [{"type": "instant"}],
                "entries": ["Test"],
            }
        )
        assert cantrip_spell.get_level_text() == "Evocation cantrip"

    def test_spell_components_text(self, sample_spell: Any) -> None:
        """Test spell components text formatting."""
        components_text = sample_spell.get_components_text()
        assert "V" in components_text
        assert "S" in components_text
        assert "M" in components_text
        assert "bat guano" in components_text


class TestCreature:
    """Tests for Creature model."""

    def test_creature_creation(self, sample_creature_data: Any) -> None:
        """Test basic creature creation."""
        creature = Creature.model_validate(sample_creature_data)
        assert creature.name == "Ancient Red Dragon"
        assert creature.strength == 30
        assert creature.get_ability_modifier(30) == 10

    def test_ability_modifier_calculation(self, sample_creature: Any) -> None:
        """Test ability modifier calculation."""
        assert sample_creature.get_ability_modifier(10) == 0
        assert sample_creature.get_ability_modifier(8) == -1
        assert sample_creature.get_ability_modifier(18) == 4
        assert sample_creature.get_ability_modifier(30) == 10

    def test_ability_text_formatting(self, sample_creature: Any) -> None:
        """Test ability score text formatting."""
        assert sample_creature.get_ability_text(18) == "18 (+4)"
        assert sample_creature.get_ability_text(8) == "8 (-1)"
        assert sample_creature.get_ability_text(10) == "10 (+0)"

    def test_size_type_alignment(self, sample_creature: Any) -> None:
        """Test size/type/alignment formatting."""
        size_type_alignment = sample_creature.get_size_type_alignment()
        assert "Gargantuan" in size_type_alignment or "G" in size_type_alignment
        assert "dragon" in size_type_alignment

    def test_armor_class_parsing(self, sample_creature_data: Any) -> None:
        """Test AC parsing from various formats."""
        creature = Creature.model_validate(sample_creature_data)
        ac_text = creature.get_ac_text()
        assert "22" in ac_text

    def test_creature_type_field_validation(self) -> None:
        """Test creature type field validator."""
        # String type
        data1 = {
            "name": "Test",
            "source": {"abbreviation": "TST"},
            "size": ["M"],
            "type": "beast",
            "alignment": ["N"],
            "ac": [15],
            "hp": {"average": 10},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }
        creature1 = Creature.model_validate(data1)
        assert isinstance(creature1.type, CreatureType)
        assert str(creature1.type) == "beast"

        # Dict type with type key
        data2 = data1.copy()
        data2["type"] = {"type": "humanoid", "subtype": "elf"}
        creature2 = Creature.model_validate(data2)
        assert isinstance(creature2.type, CreatureType)
        assert "humanoid" in str(creature2.type)

    def test_creature_ac_field_validation(self) -> None:
        """Test AC field validator."""
        base_data = {
            "name": "Test",
            "source": {"abbreviation": "TST"},
            "size": ["M"],
            "type": "beast",
            "alignment": ["N"],
            "hp": {"average": 10},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }

        # Integer AC
        data1 = base_data.copy()
        data1["ac"] = 15
        creature1 = Creature.model_validate(data1)
        assert len(creature1.ac) == 1
        assert isinstance(creature1.ac[0], ArmorClass)

        # List of dicts
        data2 = base_data.copy()
        data2["ac"] = [{"ac": 16, "from": ["natural armor"]}]
        creature2 = Creature.model_validate(data2)
        assert len(creature2.ac) == 1
        assert isinstance(creature2.ac[0], ArmorClass)

    def test_creature_hp_speed_validation(self) -> None:
        """Test HP and speed field validators."""
        base_data = {
            "name": "Test",
            "source": {"abbreviation": "TST"},
            "size": ["M"],
            "type": "beast",
            "alignment": ["N"],
            "ac": [15],
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }

        # HP dict
        data1 = base_data.copy()
        data1["hp"] = {"average": 25, "formula": "4d6 + 8"}
        creature1 = Creature.model_validate(data1)
        assert isinstance(creature1.hp, HitPoints)

        # Speed dict
        data2 = base_data.copy()
        data2["hp"] = {"average": 10}
        data2["speed"] = {"walk": 30, "fly": 60}
        creature2 = Creature.model_validate(data2)
        assert isinstance(creature2.speed, Speed)

    def test_creature_ability_parsing(self) -> None:
        """Test ability list parsing."""
        base_data = {
            "name": "Test",
            "source": {"abbreviation": "TST"},
            "size": ["M"],
            "type": "beast",
            "alignment": ["N"],
            "ac": [15],
            "hp": {"average": 10},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }

        # Trait parsing
        data = base_data.copy()
        data["trait"] = [
            {
                "name": "Keen Sight",
                "entries": ["The eagle has advantage on perception checks."],
            }
        ]
        creature = Creature.model_validate(data)
        assert creature.trait is not None
        assert len(creature.trait) == 1
        assert isinstance(creature.trait[0], Ability)
        assert creature.trait[0].name == "Keen Sight"

    def test_creature_alignment_text_formatting(self) -> None:
        """Test alignment text formatting."""
        base_data = {
            "name": "Test",
            "source": {"abbreviation": "TST"},
            "size": ["M"],
            "type": "beast",
            "hp": {"average": 10},
            "speed": {"walk": 30},
            "ac": [15],
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }

        # Simple alignment
        data1 = base_data.copy()
        data1["alignment"] = ["L", "G"]
        creature1 = Creature.model_validate(data1)
        alignment_text = creature1._get_alignment_text()
        assert "L G" in alignment_text

        # Complex alignment with dict
        data2 = base_data.copy()
        data2["alignment"] = [{"alignment": ["N", "E"]}]
        creature2 = Creature.model_validate(data2)
        alignment_text2 = creature2._get_alignment_text()
        assert "N E" in alignment_text2

        # Empty alignment
        data3 = base_data.copy()
        data3["alignment"] = []
        creature3 = Creature.model_validate(data3)
        assert creature3._get_alignment_text() == "unaligned"

    def test_creature_cr_text_formatting(self) -> None:
        """Test challenge rating text formatting."""
        base_data = {
            "name": "Test",
            "source": {"abbreviation": "TST"},
            "size": ["M"],
            "type": "beast",
            "alignment": ["N"],
            "ac": [15],
            "hp": {"average": 10},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }

        # String CR
        data1 = base_data.copy()
        data1["cr"] = "5"
        creature1 = Creature.model_validate(data1)
        assert creature1.get_cr_text() == "5"

        # Dict CR with special
        data2 = base_data.copy()
        data2["cr"] = {"special": "Variable (see description)"}
        creature2 = Creature.model_validate(data2)
        assert creature2.get_cr_text() == "Variable (see description)"

        # Dict CR with cr key
        data3 = base_data.copy()
        data3["cr"] = {"cr": "10"}
        creature3 = Creature.model_validate(data3)
        assert creature3.get_cr_text() == "10"

        # No CR
        creature4 = Creature.model_validate(base_data)
        assert creature4.get_cr_text() == "Unknown"

    def test_creature_text_methods(self) -> None:
        """Test creature text formatting methods."""
        base_data = {
            "name": "Test Dragon",
            "source": {"abbreviation": "TST"},
            "size": ["L"],
            "type": "dragon",
            "alignment": ["C", "E"],
            "ac": [{"ac": 18, "from": ["natural armor"]}],
            "hp": {"average": 100, "formula": "10d10 + 50"},
            "speed": {"walk": 40, "fly": 80},
            "str": 20,
            "dex": 14,
            "con": 20,
            "int": 16,
            "wis": 13,
            "cha": 16,
        }
        creature = Creature.model_validate(base_data)

        # Test AC text
        assert "18" in creature.get_ac_text()
        assert "natural armor" in creature.get_ac_text()

        # Test HP text
        assert "100" in creature.get_hp_text()
        assert "10d10 + 50" in creature.get_hp_text()

        # Test speed text
        assert "40 ft." in creature.get_speed_text()
        assert "fly 80 ft." in creature.get_speed_text()

        # Test size/type/alignment
        size_type_alignment = creature.get_size_type_alignment()
        assert "L" in size_type_alignment or "Large" in size_type_alignment
        assert "dragon" in size_type_alignment
        assert "C E" in size_type_alignment


class TestSpellComponent:
    """Tests for SpellComponent model."""

    def test_material_component_parsing(self) -> None:
        """Test parsing of material components."""
        # Boolean material component
        comp1 = SpellComponent.model_validate({"v": True, "s": False, "m": True})
        assert comp1.material is True

        # String material component
        comp2 = SpellComponent.model_validate(
            {"v": True, "s": True, "m": "a diamond worth 1,000 gp"}
        )
        assert comp2.material == "a diamond worth 1,000 gp"

        # Dict material component (legacy format)
        comp3 = SpellComponent.model_validate(
            {"v": True, "s": True, "m": {"text": "bat guano"}}
        )
        assert comp3.material == "bat guano"


class TestArmorClass:
    """Tests for ArmorClass model."""

    def test_armor_class_creation(self) -> None:
        """Test AC creation and string representation."""
        ac = ArmorClass.model_validate(
            {"ac": 15, "from": ["leather armor", "+1 shield"]}
        )
        assert ac.ac == 15
        assert str(ac) == "15 (leather armor, +1 shield)"

        simple_ac: Any = ArmorClass(ac=12)
        assert str(simple_ac) == "12"

    def test_armor_class_special(self) -> None:
        """Test AC with special description."""
        special_ac: Any = ArmorClass(special="Variable (see description)")
        assert str(special_ac) == "Variable (see description)"

        # Special takes priority over other fields
        mixed_ac: Any = ArmorClass(ac=15, special="Variable AC")
        assert str(mixed_ac) == "Variable AC"

    def test_armor_class_conditional(self) -> None:
        """Test AC with conditions."""
        conditional_ac: Any = ArmorClass(ac=13, condition="(16 with mage armor)")
        assert str(conditional_ac) == "13 (16 with mage armor)"

        # With both from and condition using model_validate
        complex_ac = ArmorClass.model_validate(
            {"ac": 14, "from": ["natural armor"], "condition": "(17 with shield)"}
        )
        assert str(complex_ac) == "14 (natural armor) (17 with shield)"

    def test_armor_class_edge_cases(self) -> None:
        """Test AC edge cases."""
        # No AC value
        empty_ac: Any = ArmorClass()
        assert str(empty_ac) == "Unknown"

        # AC with empty from list using model_validate
        ac_empty_from = ArmorClass.model_validate({"ac": 10, "from": []})
        assert str(ac_empty_from) == "10"

        # AC with single from source using model_validate
        ac_single_from = ArmorClass.model_validate({"ac": 12, "from": ["padded armor"]})
        assert str(ac_single_from) == "12 (padded armor)"


class TestHitPoints:
    """Tests for HitPoints model."""

    def test_hit_points_creation(self) -> None:
        """Test HP creation and string representation."""
        hp: Any = HitPoints(average=58, formula="9d8 + 18")
        assert hp.average == 58
        assert hp.formula == "9d8 + 18"
        assert str(hp) == "58 (9d8 + 18)"

    def test_hit_points_special(self) -> None:
        """Test HP with special description."""
        special_hp: Any = HitPoints(special="Variable (see description)")
        assert str(special_hp) == "Variable (see description)"

        # Special takes priority over other fields
        mixed_hp: Any = HitPoints(average=100, special="Immortal")
        assert str(mixed_hp) == "Immortal"

    def test_hit_points_average_only(self) -> None:
        """Test HP with only average."""
        avg_only_hp: Any = HitPoints(average=25)
        assert str(avg_only_hp) == "25"

    def test_hit_points_formula_only(self) -> None:
        """Test HP with only formula."""
        formula_only_hp: Any = HitPoints(formula="4d6 + 8")
        assert str(formula_only_hp) == "4d6 + 8"

    def test_hit_points_edge_cases(self) -> None:
        """Test HP edge cases."""
        # No values
        empty_hp: Any = HitPoints()
        assert str(empty_hp) == "Unknown"

        # Zero average
        zero_hp: Any = HitPoints(average=0, formula="1d4")
        assert str(zero_hp) == "0 (1d4)"


class TestSpeed:
    """Tests for Speed model."""

    def test_speed_walk_only(self) -> None:
        """Test basic walking speed."""
        speed: Any = Speed(walk=30)
        assert str(speed) == "30 ft."

    def test_speed_multiple_types(self) -> None:
        """Test multiple speed types."""
        speed: Any = Speed(walk=40, fly=80, swim=20)
        result: Any = str(speed)
        assert "40 ft." in result
        assert "fly 80 ft." in result
        assert "swim 20 ft." in result

    def test_speed_dict_format(self) -> None:
        """Test speed with dictionary format."""
        speed: Any = Speed(
            walk={"number": 30}, fly={"number": 60, "condition": "hover"}
        )
        result: Any = str(speed)
        assert "30 ft." in result
        assert "fly 60 ft. (hover)" in result

    def test_speed_all_types(self) -> None:
        """Test all speed types."""
        speed: Any = Speed(walk=30, fly=60, swim=25, climb=20, burrow=15)
        result: Any = str(speed)
        assert "30 ft." in result
        assert "fly 60 ft." in result
        assert "swim 25 ft." in result
        assert "climb 20 ft." in result
        assert "burrow 15 ft." in result

    def test_speed_with_conditions(self) -> None:
        """Test speeds with conditions."""
        speed: Any = Speed(walk=30, fly={"number": 60, "condition": "hover, magical"})
        result: Any = str(speed)
        assert "30 ft." in result
        assert "fly 60 ft. (hover, magical)" in result

    def test_speed_edge_cases(self) -> None:
        """Test speed edge cases."""
        # No speeds
        empty_speed: Any = Speed()
        assert str(empty_speed) == "0 ft."

        # Zero walk speed
        zero_speed: Any = Speed(walk=0)
        assert str(zero_speed) == "0 ft."

        # Dict with missing number defaults to expected values
        speed_missing_number: Any = Speed(fly={"condition": "hover"})
        result: Any = str(speed_missing_number)
        assert "fly 0 ft. (hover)" in result


class TestCreatureType:
    """Tests for CreatureType model."""

    def test_creature_type_string(self) -> None:
        """Test basic string type."""
        ctype = CreatureType.model_validate("dragon")
        assert str(ctype) == "dragon"

        # Direct creation from string
        ctype2: Any = CreatureType(type="humanoid")
        assert str(ctype2) == "humanoid"

    def test_creature_type_with_subtype(self) -> None:
        """Test type with subtype."""
        ctype: Any = CreatureType(type="humanoid", subtype="elf")
        assert str(ctype) == "humanoid (elf)"

    def test_creature_type_choice_format(self) -> None:
        """Test choice format handling."""
        choice_data = {"choose": ["undead", "humanoid"]}
        ctype = CreatureType.model_validate(choice_data)
        result: Any = str(ctype)
        assert "undead or humanoid" in result

    def test_creature_type_dict_special(self) -> None:
        """Test special dict format without 'type' key."""
        special_dict = {"special": "Variable (see description)"}
        ctype = CreatureType.model_validate(special_dict)
        # The dict gets wrapped as the type
        assert "special" in str(ctype)

    def test_creature_type_with_tags(self) -> None:
        """Test type with tags."""
        ctype: Any = CreatureType(type="humanoid", subtype="elf", tags=["noble"])
        assert str(ctype) == "humanoid (elf, noble)"

        # Tags without subtype
        ctype2: Any = CreatureType(type="humanoid", tags=["elf", "noble"])
        assert str(ctype2) == "humanoid (elf, noble)"

    def test_creature_type_complex_tags(self) -> None:
        """Test complex tag formats."""
        ctype: Any = CreatureType(
            type="humanoid", tags=[{"tag": "elf", "prefix": "High"}, "noble"]
        )
        result: Any = str(ctype)
        assert "humanoid" in result
        assert "High elf" in result
        assert "noble" in result

    def test_creature_type_model_validate_edge_cases(self) -> None:
        """Test model_validate with various inputs."""
        # String input
        ctype1 = CreatureType.model_validate("beast")
        assert str(ctype1) == "beast"

        # Dict with type key
        ctype2 = CreatureType.model_validate({"type": "fiend", "subtype": "demon"})
        assert str(ctype2) == "fiend (demon)"

        # Dict without type but with choose
        ctype3 = CreatureType.model_validate({"choose": ["celestial", "fiend"]})
        result: Any = str(ctype3)
        assert "celestial or fiend" in result


class TestAbility:
    """Tests for Ability model."""

    def test_ability_basic(self) -> None:
        """Test basic ability creation."""
        ability: Any = Ability(
            name="Multiattack", entries=["The dragon makes three attacks."]
        )
        assert str(ability) == "Multiattack"
        assert ability.get_description_text() == "The dragon makes three attacks."

    def test_ability_complex_entries(self) -> None:
        """Test ability with complex entry structures."""
        entries = [
            "The dragon breathes fire in a cone.",
            {
                "type": "entries",
                "name": "Fire Breath",
                "entries": ["Each creature in the area must make a saving throw."],
            },
        ]
        ability: Any = Ability(name="Breath Weapon", entries=entries)
        result = ability.get_description_text()
        assert "The dragon breathes fire in a cone." in result
        assert "**Fire Breath**" in result
        assert "Each creature in the area must make a saving throw." in result

    def test_ability_with_text_entries(self) -> None:
        """Test ability with text-type entries."""
        entries = [
            {"text": "This is a text entry."},
            {"name": "Special Action", "text": "This has both name and text."},
        ]
        ability: Any = Ability(name="Complex Ability", entries=entries)
        result = ability.get_description_text()
        assert "This is a text entry." in result
        assert "**Special Action**" in result
        assert "This has both name and text." in result

    def test_ability_with_items(self) -> None:
        """Test ability with item lists."""
        entries = [
            {
                "type": "list",
                "items": [
                    "Simple string item",
                    {"name": "Named Item", "text": "Item with description"},
                    {"text": "Item with just text"},
                ],
            }
        ]
        ability: Any = Ability(name="List Ability", entries=entries)
        result = ability.get_description_text()
        assert "• Simple string item" in result
        assert "• **Named Item** Item with description" in result
        assert "• Item with just text" in result

    def test_ability_nested_entries(self) -> None:
        """Test deeply nested entry structures."""
        entries = [
            {
                "entries": [
                    {"entries": [{"text": "Deeply nested text"}]},
                    {"name": "Nested Section", "entries": ["Nested content"]},
                ]
            }
        ]
        ability: Any = Ability(name="Nested Ability", entries=entries)
        result = ability.get_description_text()
        assert "Deeply nested text" in result
        assert "**Nested Section**" in result
        assert "Nested content" in result

    def test_ability_edge_cases(self) -> None:
        """Test ability edge cases."""
        # Empty entries
        ability1: Any = Ability(name="Empty", entries=[])
        assert ability1.get_description_text() == ""

        # None/empty dict entries
        ability2: Any = Ability(name="Minimal", entries=[{}])
        assert ability2.get_description_text() == ""

        # Mixed empty and valid entries
        ability3: Any = Ability(name="Mixed", entries=["Valid text", {}, ""])
        result = ability3.get_description_text()
        assert "Valid text" in result
