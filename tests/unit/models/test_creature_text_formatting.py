"""Unit tests for creature text formatting and validation.

These tests focus on proper formatting of creature stat block text,
including alignment processing, size abbreviations, and complex text structures.
"""

import pytest

from studiorum.core.models.creatures import Creature, CreatureType
from tests.test_helpers import reset_test_environment


class TestCreatureSizeFormatting:
    """Test creature size abbreviation to full name conversion."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_size_abbreviation_conversion(self):
        """Test conversion of 5etools size abbreviations to full names."""
        test_cases = [
            (["T"], "Tiny"),
            (["S"], "Small"),
            (["M"], "Medium"),
            (["L"], "Large"),
            (["H"], "Huge"),
            (["G"], "Gargantuan"),
            (["V"], "Varies"),
        ]

        base_data = {
            "name": "Test Creature",
            "source": "TEST",
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

        for size_abv, expected_full in test_cases:
            creature_data = base_data.copy()
            creature_data["size"] = size_abv

            creature = Creature.model_validate(creature_data)
            size_text = creature._get_size_text()
            assert size_text == expected_full

    def test_multiple_sizes(self):
        """Test handling of creatures with multiple sizes."""
        creature_data = {
            "name": "Shapeshifter",
            "source": "TEST",
            "size": ["S", "M"],  # Small or Medium
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

        creature = Creature.model_validate(creature_data)
        size_text = creature._get_size_text()
        assert size_text == "Small, Medium"

    def test_unknown_size_abbreviation(self):
        """Test handling of unknown size abbreviations."""
        creature_data = {
            "name": "Unknown Size",
            "source": "TEST",
            "size": ["Z"],  # Unknown abbreviation
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

        creature = Creature.model_validate(creature_data)
        size_text = creature._get_size_text()
        assert size_text == "Z"  # Should pass through unknown values


class TestCreatureAlignmentFormatting:
    """Test creature alignment abbreviation processing and formatting."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_simple_alignment_abbreviations(self):
        """Test conversion of simple alignment abbreviations."""
        test_cases = [
            (["L", "G"], "lawful good"),
            (["N", "G"], "neutral good"),
            (["C", "G"], "chaotic good"),
            (["L", "N"], "lawful neutral"),
            (["N"], "neutral"),
            (["C", "N"], "chaotic neutral"),
            (["L", "E"], "lawful evil"),
            (["N", "E"], "neutral evil"),
            (["C", "E"], "chaotic evil"),
            (["U"], "unaligned"),
            (["A"], "any alignment"),
        ]

        base_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
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

        for alignment_abv, expected_text in test_cases:
            creature_data = base_data.copy()
            creature_data["alignment"] = alignment_abv

            creature = Creature.model_validate(creature_data)
            alignment_text = creature._get_alignment_text()
            assert alignment_text == expected_text

    def test_complex_alignment_patterns(self):
        """Test complex alignment patterns from 5etools."""
        # Test cases based on 5etools alignment processing logic
        test_cases = [
            # Neutral variations (3 items: NX, NY, N)
            (["NX", "NY", "N"], "any neutral alignment"),
            # Non-lawful (4 items without L and NX)
            (["C", "G", "N", "E"], "any chaotic alignment"),
            # Non-evil (4 items without E and NY)
            (["L", "G", "C", "N"], "any good alignment"),
            # Non-good (5 items without G)
            (["L", "N", "C", "E", "NY"], "any non-good alignment"),
            # Non-evil (5 items without E)
            (["L", "G", "N", "C", "NX"], "any non-evil alignment"),
        ]

        base_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
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

        for alignment_abv, expected_text in test_cases:
            creature_data = base_data.copy()
            creature_data["alignment"] = alignment_abv

            creature = Creature.model_validate(creature_data)
            alignment_text = creature._get_alignment_text()
            assert alignment_text == expected_text

    def test_special_alignment_format(self):
        """Test special alignment format with dict structure."""
        creature_data = {
            "name": "Special Alignment",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": [{"special": "neutral evil or chaotic evil"}],
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

        creature = Creature.model_validate(creature_data)
        alignment_text = creature._get_alignment_text()
        assert alignment_text == "neutral evil or chaotic evil"

    def test_choice_alignment_format(self):
        """Test choice alignment format with nested structures."""
        creature_data = {
            "name": "Choice Alignment",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": [{"choose": [["L", "G"], ["L", "N"]]}],
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

        creature = Creature.model_validate(creature_data)
        alignment_text = creature._get_alignment_text()
        # Should use the first choice option
        assert "lawful" in alignment_text and "good" in alignment_text


class TestCreatureTypeFormatting:
    """Test creature type formatting with subtypes and tags."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_simple_creature_type(self):
        """Test simple creature type without subtypes."""
        creature_type = CreatureType(type="humanoid")
        assert str(creature_type) == "humanoid"

    def test_creature_type_with_subtype(self):
        """Test creature type with subtype."""
        creature_type = CreatureType(type="humanoid", subtype="elf")
        assert str(creature_type) == "humanoid (elf)"

    def test_creature_type_with_tags(self):
        """Test creature type with tags."""
        creature_type = CreatureType(type="humanoid", tags=["elf", "noble"])
        assert str(creature_type) == "humanoid (elf, noble)"

    def test_creature_type_with_subtype_and_tags(self):
        """Test creature type with both subtype and tags."""
        creature_type = CreatureType(
            type="humanoid", subtype="elf", tags=["high elf", "wizard"]
        )
        result = str(creature_type)
        assert "humanoid" in result
        assert "elf" in result
        # Tags should be combined with subtype in parentheses
        assert "high elf" in result or "wizard" in result

    def test_complex_creature_type_tags(self):
        """Test creature type with complex tag structures."""
        creature_type = CreatureType(
            type="humanoid", tags=["elf", {"tag": "noble", "prefix": "High"}]
        )
        result = str(creature_type)
        assert "humanoid" in result
        assert "elf" in result
        assert "High noble" in result

    def test_choice_creature_type(self):
        """Test creature type with choice format."""
        creature_type = CreatureType(type={"choose": ["humanoid", "fey"]})
        result = str(creature_type)
        assert "humanoid or fey" in result


class TestCreatureStatBlockIntegration:
    """Test complete stat block text generation."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_complete_stat_block_header(self):
        """Test complete creature header line (size, type, alignment)."""
        creature_data = {
            "name": "Elven Ranger",
            "source": "TEST",
            "size": ["M"],
            "type": {"type": "humanoid", "subtype": "elf"},
            "alignment": ["C", "G"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 16,
            "con": 12,
            "int": 11,
            "wis": 15,
            "cha": 11,
            "cr": "2",
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_size_type_alignment()

        assert "Medium" in header
        assert "humanoid" in header
        assert "chaotic good" in header

        # Should be in format: "Medium humanoid (elf), chaotic good"
        expected_parts = ["Medium", "humanoid", "chaotic good"]
        for part in expected_parts:
            assert part in header

    def test_armor_class_text_generation(self):
        """Test AC text generation with various formats."""
        # Test simple AC
        creature_data = {
            "name": "Simple AC",
            "source": "TEST",
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [14],
            "hp": {"average": 30},
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
        assert creature.get_ac_text() == "14"

        # Test multiple AC values
        creature_data["ac"] = [14, 17]
        creature = Creature.model_validate(creature_data)
        ac_text = creature.get_ac_text()
        assert "14" in ac_text and "17" in ac_text

    def test_challenge_rating_text_variations(self):
        """Test various challenge rating formats."""
        base_data = {
            "name": "Test Creature",
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
        }

        test_cases = [
            ("0", "0 (10 XP)"),
            ("1/8", "1/8 (25 XP)"),
            ("1/4", "1/4 (50 XP)"),
            ("1/2", "1/2 (100 XP)"),
            ("1", "1 (200 XP)"),
            ("10", "10 (5,900 XP)"),
            ("20", "20 (25,000 XP)"),
            ("30", "30 (155,000 XP)"),
        ]

        for cr_value, expected_text in test_cases:
            creature_data = base_data.copy()
            creature_data["cr"] = cr_value

            creature = Creature.model_validate(creature_data)
            cr_text = creature.get_enhanced_cr_text()
            assert cr_text == expected_text

    def test_special_challenge_rating(self):
        """Test special challenge rating formats."""
        creature_data = {
            "name": "Special CR",
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
            "cr": {"special": "Varies by form"},
        }

        creature = Creature.model_validate(creature_data)
        cr_text = creature.get_enhanced_cr_text()
        assert cr_text == "Varies by form"


class TestCreatureTextValidation:
    """Test validation of creature text fields and formats."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_empty_fields_handling(self):
        """Test handling of empty or None text fields."""
        creature_data = {
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
            # Optional fields are None/missing
            "senses": None,
            "languages": None,
            "save": None,
            "skill": None,
        }

        creature = Creature.model_validate(creature_data)

        # These should return None for empty fields
        assert creature.get_formatted_senses() is None
        assert creature.get_formatted_languages() is None
        assert creature.get_formatted_saving_throws() is None
        assert creature.get_formatted_skills() is None

    def test_string_list_formatting(self):
        """Test formatting of various string list fields."""
        creature_data = {
            "name": "List Test",
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
            "senses": ["darkvision 60 ft.", "passive Perception 12"],
            "languages": ["Common", "Elvish", "telepathy 120 ft."],
            "resist": ["fire", "cold"],
            "immune": ["poison"],
            "conditionImmune": ["charmed", "frightened"],
        }

        creature = Creature.model_validate(creature_data)

        # Test comma-separated formatting
        senses = creature.get_formatted_senses()
        assert "darkvision 60 ft., passive Perception 12" == senses

        languages = creature.get_formatted_languages()
        assert "Common, Elvish, telepathy 120 ft." == languages

        resistances = creature.get_formatted_resistances()
        assert "fire; cold" == resistances

        immunities = creature.get_formatted_immunities()
        assert "poison" == immunities

        conditions = creature.get_formatted_condition_immunities()
        assert "charmed, frightened" == conditions

    def test_numeric_formatting_consistency(self):
        """Test consistent formatting of numeric values."""
        creature_data = {
            "name": "Numeric Test",
            "source": "TEST",
            "size": ["Large"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [18],
            "hp": {"average": 200, "formula": "16d12 + 96"},
            "speed": {"walk": 40, "fly": 80, "swim": 40},
            "str": 23,
            "dex": 10,
            "con": 23,
            "int": 14,
            "wis": 13,
            "cha": 17,
            "cr": "13",
            "save": {
                "str": "+12",
                "dex": "+5",
                "con": "+12",
                "wis": "+6",
                "cha": "+8",
            },  # Use string format
            "skill": {"perception": "+11", "stealth": "+5"},  # Use string format
        }

        creature = Creature.model_validate(creature_data)

        # Test numeric formatting with proper signs
        saves = creature.get_formatted_saving_throws()
        assert "+12" in saves  # Positive numbers get + sign
        assert "+5" in saves

        skills = creature.get_formatted_skills()
        assert "+11" in skills
        assert "+5" in skills

        # Test ability text formatting
        str_text = creature.get_ability_text(23)
        assert str_text == "23 (+6)"

        dex_text = creature.get_ability_text(10)
        assert dex_text == "10 (+0)"

    def test_case_sensitivity_handling(self):
        """Test proper case handling in text formatting."""
        creature_data = {
            "name": "Case Test",
            "source": "TEST",
            "size": ["M"],  # Use standard abbreviation
            "type": "humanoid",  # Use standard lowercase
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
            "skill": {
                "perception": "+3",  # Standard lowercase
                "animalHandling": "+2",  # Standard camelCase
            },
        }

        creature = Creature.model_validate(creature_data)

        # Size should be properly capitalized in output
        size_text = creature._get_size_text()
        assert "Medium" in size_text  # Should convert M to Medium

        # Skills should be properly formatted with proper capitalization
        skills = creature.get_formatted_skills()
        assert "Perception" in skills
        assert "Animal Handling" in skills
