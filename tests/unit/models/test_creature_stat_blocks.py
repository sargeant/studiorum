"""Unit tests for creature stat block generation and rendering.

These tests focus on the core functionality of creature models for generating
properly formatted stat blocks with ability scores, modifiers, and complex text formatting.
"""

from unittest.mock import Mock, patch

import pytest

from studiorum.cli.services import get_cli_template_service
from studiorum.core.models.creatures import (
    Ability,
    ArmorClass,
    Creature,
    CreatureType,
    HitPoints,
    SkillBonus,
    Speed,
)
from studiorum.core.references.content_tracker import ContentTracker
from tests.test_helpers import reset_test_environment


class TestCreatureStatBlockRendering:
    """Test creature stat block rendering functionality."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_ability_score_modifier_calculation(self):
        """Test calculation of ability score modifiers."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 16,  # +3
            "dex": 14,  # +2
            "con": 15,  # +2
            "int": 10,  # +0
            "wis": 13,  # +1
            "cha": 8,  # -1
            "cr": "2",
            "senses": ["passive Perception 11"],
            "languages": ["Common"],
        }

        creature = Creature.model_validate(creature_data)

        # Test modifier calculations
        assert creature.get_ability_modifier(16) == 3
        assert creature.get_ability_modifier(14) == 2
        assert creature.get_ability_modifier(15) == 2
        assert creature.get_ability_modifier(10) == 0
        assert creature.get_ability_modifier(13) == 1
        assert creature.get_ability_modifier(8) == -1

        # Test edge cases
        assert creature.get_ability_modifier(1) == -5
        assert creature.get_ability_modifier(30) == 10

    def test_ability_text_formatting(self):
        """Test formatted ability score text with modifiers."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 18,
            "dex": 12,
            "con": 16,
            "int": 8,
            "wis": 14,
            "cha": 6,
            "cr": "2",
        }

        creature = Creature.model_validate(creature_data)

        # Test positive modifiers
        assert creature.get_ability_text(18) == "18 (+4)"
        assert creature.get_ability_text(16) == "16 (+3)"
        assert creature.get_ability_text(14) == "14 (+2)"
        assert creature.get_ability_text(12) == "12 (+1)"

        # Test zero modifier
        assert creature.get_ability_text(10) == "10 (+0)"

        # Test negative modifiers
        assert creature.get_ability_text(8) == "8 (-1)"
        assert creature.get_ability_text(6) == "6 (-2)"

    def test_armor_class_processing(self):
        """Test complex AC calculations and formatting."""
        # Simple AC
        simple_ac = ArmorClass(ac=15)
        assert str(simple_ac) == "15"

        # AC with sources - need to use model_validate for the from_ field
        ac_with_sources = ArmorClass.model_validate(
            {"ac": 17, "from": ["Natural Armor", "Shield"]}
        )
        assert str(ac_with_sources) == "17 (Natural Armor, Shield)"

        # AC with condition
        conditional_ac = ArmorClass(ac=13, condition="(16 with mage armor)")
        assert str(conditional_ac) == "13 (16 with mage armor)"

        # Special AC description
        special_ac = ArmorClass(special="17 (natural armor, shield)")
        assert str(special_ac) == "17 (natural armor, shield)"

    def test_hit_points_formatting(self):
        """Test hit points formatting with formulas."""
        # Simple HP
        simple_hp = HitPoints(average=58)
        assert str(simple_hp) == "58"

        # HP with formula
        hp_with_formula = HitPoints(average=58, formula="9d8 + 18")
        assert str(hp_with_formula) == "58 (9d8 + 18)"

        # Special HP description
        special_hp = HitPoints(special="58 hit points (9d8 + 18)")
        assert str(special_hp) == "58 hit points (9d8 + 18)"

        # Formula only
        formula_only = HitPoints(formula="9d8 + 18")
        assert str(formula_only) == "9d8 + 18"

    def test_speed_text_formatting(self):
        """Test speed formatting for various movement types."""
        # Walking only
        walk_only = Speed(walk=30)
        assert str(walk_only) == "30 ft."

        # Multiple speeds
        multi_speed = Speed(walk=30, fly=60, swim=30)
        assert str(multi_speed) == "30 ft., fly 60 ft., swim 30 ft."

        # Speed with conditions
        conditional_speed = Speed(walk=30, fly={"number": 60, "condition": "hover"})
        result = str(conditional_speed)
        assert "30 ft." in result
        assert "fly 60 ft. (hover)" in result

        # All movement types
        all_speeds = Speed(walk=25, fly=50, swim=25, climb=15, burrow=10)
        result = str(all_speeds)
        assert "25 ft." in result
        assert "fly 50 ft." in result
        assert "swim 25 ft." in result
        assert "climb 15 ft." in result
        assert "burrow 10 ft." in result

    def test_creature_type_formatting(self):
        """Test creature type and subtype formatting."""
        # Simple type
        simple_type = CreatureType(type="humanoid")
        assert str(simple_type) == "humanoid"

        # Type with subtype
        type_with_subtype = CreatureType(type="humanoid", subtype="elf")
        assert str(type_with_subtype) == "humanoid (elf)"

        # Type with tags
        type_with_tags = CreatureType(type="humanoid", tags=["elf", "noble"])
        assert str(type_with_tags) == "humanoid (elf, noble)"

        # Type with both subtype and tags
        complex_type = CreatureType(
            type="humanoid", subtype="elf", tags=["high elf", "spellcaster"]
        )
        result = str(complex_type)
        assert "humanoid" in result
        assert "elf" in result

    def test_size_type_alignment_formatting(self):
        """Test complete size, type, and alignment formatting."""
        creature_data = {
            "name": "Test Elf",
            "source": "TEST",
            "size": ["M"],  # Medium abbreviation
            "type": "humanoid",
            "alignment": ["L", "G"],  # Lawful Good abbreviations
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "1",
        }

        creature = Creature.model_validate(creature_data)
        result = creature.get_size_type_alignment()

        assert "Medium humanoid" in result
        assert "lawful good" in result

    def test_challenge_rating_with_xp(self):
        """Test enhanced challenge rating formatting with XP."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
        }

        creature = Creature.model_validate(creature_data)

        # Test standard CRs
        creature.cr = "2"
        assert creature.get_enhanced_cr_text() == "2 (450 XP)"

        creature.cr = "1/2"
        assert creature.get_enhanced_cr_text() == "1/2 (100 XP)"

        creature.cr = "0"
        assert creature.get_enhanced_cr_text() == "0 (10 XP)"

        # Test high CR
        creature.cr = "20"
        assert creature.get_enhanced_cr_text() == "20 (25,000 XP)"

    def test_saving_throws_formatting(self):
        """Test saving throw bonus formatting."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            "save": {"str": "+5", "dex": "+7", "wis": "+3"},
        }

        creature = Creature.model_validate(creature_data)
        result = creature.get_formatted_saving_throws()

        assert "Str +5" in result
        assert "Dex +7" in result
        assert "Wis +3" in result

    def test_skills_formatting(self):
        """Test skills formatting with proper capitalization."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            "skill": {
                "perception": "+5",
                "stealth": "+7",
                "animalHandling": "+3",
                "sleightOfHand": "+4",
            },
        }

        creature = Creature.model_validate(creature_data)
        result = creature.get_formatted_skills()

        assert "Perception +5" in result
        assert "Stealth +7" in result
        assert "Animal Handling +3" in result
        assert "Sleight Of Hand +4" in result

    def test_senses_processing(self):
        """Test senses formatting."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            "senses": ["darkvision 60 ft.", "passive Perception 15"],
        }

        creature = Creature.model_validate(creature_data)
        result = creature.get_formatted_senses()

        assert "darkvision 60 ft." in result
        assert "passive Perception 15" in result

    def test_damage_resistances_formatting(self):
        """Test damage resistance, immunity, and vulnerability formatting."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            "resist": ["fire", "cold"],
            "immune": ["poison"],
            "vulnerable": ["thunder"],
            "conditionImmune": ["charmed", "frightened"],
        }

        creature = Creature.model_validate(creature_data)

        # Test resistances
        resistances = creature.get_formatted_resistances()
        assert "fire" in resistances
        assert "cold" in resistances

        # Test immunities
        immunities = creature.get_formatted_immunities()
        assert "poison" in immunities

        # Test vulnerabilities
        vulnerabilities = creature.get_formatted_vulnerabilities()
        assert "thunder" in vulnerabilities

        # Test condition immunities
        conditions = creature.get_formatted_condition_immunities()
        assert "charmed" in conditions
        assert "frightened" in conditions


class TestCreatureAbilities:
    """Test creature abilities (traits, actions, etc.) processing."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_ability_text_extraction(self):
        """Test text extraction from complex ability structures."""
        # Simple string entry
        simple_ability = Ability(
            name="Keen Senses",
            entries=["The creature has advantage on Wisdom (Perception) checks."],
        )

        # Test fallback text extraction (without tag processing)
        with patch(
            "studiorum.cli.main.get_tag_resolver", side_effect=Exception("No resolver")
        ):
            # Use template service for text extraction
            template_service = get_cli_template_service()
            content_tracker = ContentTracker()
            bound = template_service.bind_context(content_tracker)
            text = bound.render_entry(simple_ability.entries)
            assert "advantage on Wisdom (Perception)" in text

    def test_ability_name_processing(self):
        """Test ability name processing with fallback."""
        ability = Ability(
            name="Multiattack", entries=["The creature makes two weapon attacks."]
        )

        # Test fallback name processing (without tag processing)
        with patch(
            "studiorum.cli.main.get_tag_resolver", side_effect=Exception("No resolver")
        ):
            name = ability.get_processed_name()
            assert name == "Multiattack"

    def test_complex_entry_structure(self):
        """Test handling of complex entry structures."""
        complex_ability = Ability(
            name="Spellcasting",
            entries=[
                "The creature is an 18th-level spellcaster.",
                {
                    "type": "entries",
                    "name": "Cantrips (at will)",
                    "entries": ["mage hand", "prestidigitation", "minor illusion"],
                },
                {
                    "type": "entries",
                    "name": "1st level (4 slots)",
                    "entries": ["magic missile", "shield"],
                },
            ],
        )

        # Test fallback text extraction
        with patch(
            "studiorum.cli.main.get_tag_resolver", side_effect=Exception("No resolver")
        ):
            # Use template service for text extraction
            template_service = get_cli_template_service()
            content_tracker = ContentTracker()
            bound = template_service.bind_context(content_tracker)
            text = bound.render_entry(complex_ability.entries)
            assert "18th-level spellcaster" in text
            assert "Cantrips" in text
            assert "magic missile" in text


class TestCreatureLayoutDecisions:
    """Test creature layout decision logic."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_full_width_layout_legendary_actions(self):
        """Test that creatures with legendary actions require full width."""
        creature_data = {
            "name": "Ancient Dragon",
            "source": "TEST",
            "size": ["Gargantuan"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [22],
            "hp": {"average": 546},
            "speed": {"walk": 40, "fly": 80},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "cr": "24",
            "legendary": [
                Ability(name="Detect", entries=["The dragon makes a Wisdom check."]),
                Ability(
                    name="Tail Attack", entries=["The dragon makes a tail attack."]
                ),
                Ability(name="Wing Attack", entries=["The dragon beats its wings."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        assert creature.requires_full_width_layout() is True

    def test_full_width_layout_many_traits(self):
        """Test that creatures with many traits require full width."""
        traits = []
        for i in range(8):
            traits.append(
                Ability(name=f"Trait {i}", entries=[f"This is trait number {i}."])
            )

        creature_data = {
            "name": "Complex Creature",
            "source": "TEST",
            "size": ["Large"],
            "type": "monstrosity",
            "alignment": ["neutral"],
            "ac": [18],
            "hp": {"average": 200},
            "speed": {"walk": 30},
            "str": 20,
            "dex": 14,
            "con": 18,
            "int": 10,
            "wis": 12,
            "cha": 8,
            "cr": "10",
            "trait": traits,
        }

        creature = Creature.model_validate(creature_data)
        assert creature.requires_full_width_layout() is True

    def test_compact_layout_simple_creature(self):
        """Test that simple creatures can use compact layout."""
        creature_data = {
            "name": "Simple Beast",
            "source": "TEST",
            "size": ["Medium"],
            "type": "beast",
            "alignment": ["unaligned"],
            "ac": [12],
            "hp": {"average": 22},
            "speed": {"walk": 40},
            "str": 15,
            "dex": 14,
            "con": 13,
            "int": 2,
            "wis": 12,
            "cha": 6,
            "cr": "1/4",
            "trait": [
                Ability(name="Keen Smell", entries=["Advantage on smell-based checks."])
            ],
            "action": [
                Ability(name="Bite", entries=["Melee weapon attack: +4 to hit."])
            ],
        }

        creature = Creature.model_validate(creature_data)
        assert creature.requires_full_width_layout() is False


class TestCreatureValidation:
    """Test creature data validation and edge cases."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_minimal_creature_validation(self):
        """Test validation of minimal creature data."""
        minimal_data = {
            "name": "Minimal Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [10],
            "hp": {"average": 4},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "0",
        }

        creature = Creature.model_validate(minimal_data)
        assert creature.name == "Minimal Creature"
        assert creature.get_enhanced_cr_text() == "0 (10 XP)"

    def test_ability_score_bounds(self):
        """Test ability score validation bounds."""
        valid_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [10],
            "hp": {"average": 4},
            "speed": {"walk": 30},
            "str": 1,  # Minimum
            "dex": 30,  # Maximum
            "con": 15,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "0",
        }

        creature = Creature.model_validate(valid_data)
        assert creature.strength == 1
        assert creature.dexterity == 30

        # Test invalid bounds should raise validation error
        with pytest.raises(ValueError):  # Pydantic validation error
            invalid_data = valid_data.copy()
            invalid_data["str"] = 0  # Below minimum
            Creature.model_validate(invalid_data)

        with pytest.raises(ValueError):  # Pydantic validation error
            invalid_data = valid_data.copy()
            invalid_data["dex"] = 31  # Above maximum
            Creature.model_validate(invalid_data)

    def test_skill_bonus_parsing(self):
        """Test structured skill bonus parsing."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            "skill": {
                "perception": {
                    "value": "+5",
                    "proficiency": "proficient",
                    "expertise": False,
                },
                "stealth": "+7",  # Simple string format
                "insight": {"value": "+3", "expertise": True},
            },
        }

        creature = Creature.model_validate(creature_data)

        # Check that structured skills are parsed correctly
        assert isinstance(creature.skill["perception"], SkillBonus)
        assert creature.skill["perception"].value == "+5"
        assert creature.skill["perception"].proficiency == "proficient"
        assert creature.skill["perception"].expertise is False

        # Check that simple strings are preserved
        assert creature.skill["stealth"] == "+7"

        # Check expertise handling
        assert isinstance(creature.skill["insight"], SkillBonus)
        assert creature.skill["insight"].expertise is True
