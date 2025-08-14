"""Unit tests for 5etools markup processing in creature context.

These tests focus on how creature abilities and descriptions handle
5etools markup tags like {@atk}, {@damage}, {@spell}, etc.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from dnd5e.core.models.creatures import Ability, ArmorClass, Creature
from tests.test_helpers import reset_test_environment


class TestCreatureMarkupProcessing:
    """Test 5etools markup processing in creature abilities and descriptions."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_ability_name_markup_processing(self):
        """Test processing of 5etools markup in ability names."""
        ability = Ability(
            name="Fire Breath {@recharge 5}",
            entries=["The dragon exhales fire in a 60-foot cone."],
        )

        # Mock the tag resolver to simulate markup processing
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.return_value = "Fire Breath (Recharge 5-6)"

        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = ["Fire Breath (Recharge 5-6)"]
            mock_processor_class.return_value = mock_processor

            processed_name = ability.get_processed_name()
            assert processed_name == "Fire Breath (Recharge 5-6)"

    def test_ability_description_markup_processing(self):
        """Test processing of 5etools markup in ability descriptions."""
        ability = Ability(
            name="Multiattack",
            entries=[
                "The creature makes two {@atk mw} attacks.",
                "Each attack deals {@damage 1d8+4} slashing damage.",
            ],
        )

        # Mock the entry processor to simulate complex markup processing
        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "The creature makes two melee weapon attacks.",
                "Each attack deals 1d8+4 slashing damage.",
            ]
            mock_processor_class.return_value = mock_processor

            description = ability.get_description_text()
            assert "melee weapon attacks" in description
            assert "1d8+4 slashing damage" in description

    def test_armor_class_markup_processing(self):
        """Test processing of 5etools markup in armor class descriptions."""
        ac = ArmorClass.model_validate(
            {
                "ac": 17,
                "from": ["natural armor", "{@item shield}"],
                "condition": "(19 with {@spell mage armor})",
            }
        )

        # Mock tag resolver for armor class processing
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.side_effect = lambda text: text.replace(
            "{@item shield}", "shield"
        ).replace("{@spell mage armor}", "mage armor")

        with patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver):
            processed_ac = ac.get_processed_ac_text()
            assert "17 (natural armor, shield) (19 with mage armor)" == processed_ac

    def test_senses_markup_processing(self):
        """Test processing of 5etools markup in creature senses."""
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
            "senses": [
                "darkvision 60 ft.",
                "{@sense blindsight} 30 ft.",
                "passive Perception 15",
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Mock the entry processor for senses
        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "darkvision 60 ft., blindsight 30 ft., passive Perception 15"
            ]
            mock_processor_class.return_value = mock_processor

            processed_senses = creature.get_processed_senses()
            assert "darkvision 60 ft." in processed_senses
            assert "blindsight 30 ft." in processed_senses
            assert "passive Perception 15" in processed_senses

    def test_markup_processing_fallback(self):
        """Test fallback behavior when markup processing fails."""
        ability = Ability(
            name="Spell Attack {@spell magic missile}",
            entries=[
                "The creature casts {@spell magic missile} at 3rd level.",
                "Each missile deals {@damage 1d4+1} force damage.",
            ],
        )

        # Test that fallback works when tag processing raises exceptions
        with patch(
            "dnd5e.cli.main.get_tag_resolver",
            side_effect=Exception("Tag resolver error"),
        ):
            # Should fall back to original name
            fallback_name = ability.get_processed_name()
            assert fallback_name == "Spell Attack {@spell magic missile}"

            # Should fall back to simple text extraction
            fallback_description = ability.get_description_text()
            assert "magic missile" in fallback_description
            assert "1d4+1" in fallback_description

    def test_complex_entry_markup_processing(self):
        """Test markup processing in complex nested entry structures."""
        complex_ability = Ability(
            name="Spellcasting",
            entries=[
                "The creature is an 18th-level spellcaster.",
                {
                    "type": "entries",
                    "name": "Cantrips (at will)",
                    "entries": [
                        "{@spell mage hand}",
                        "{@spell prestidigitation}",
                        "{@spell minor illusion}",
                    ],
                },
                {
                    "type": "entries",
                    "name": "1st level (4 slots)",
                    "entries": ["{@spell magic missile}", "{@spell shield}"],
                },
            ],
        )

        # Mock complex entry processing
        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "The creature is an 18th-level spellcaster.",
                "Cantrips (at will): mage hand, prestidigitation, minor illusion",
                "1st level (4 slots): magic missile, shield",
            ]
            mock_processor_class.return_value = mock_processor

            processed_text = complex_ability.get_description_text()
            assert "18th-level spellcaster" in processed_text
            assert "mage hand" in processed_text
            assert "magic missile" in processed_text

    def test_rendering_context_creation(self):
        """Test that proper rendering context is created for markup processing."""
        ability = Ability(
            name="Test Ability", entries=["Test entry with {@spell fireball}."]
        )

        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
            patch(
                "dnd5e.renderers.core.interfaces.RenderingContext"
            ) as mock_context_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = ["Test entry with fireball."]
            mock_processor_class.return_value = mock_processor

            mock_context = Mock()
            mock_context_class.return_value = mock_context

            ability.get_description_text()

            # Verify RenderingContext was created with correct parameters
            mock_context_class.assert_called_once()
            call_args = mock_context_class.call_args[1]
            assert call_args["output_format"] == "latex"
            assert call_args["debug_mode"] is False
            assert call_args["omnidexer"] == mock_omnidexer
            assert call_args["tag_resolver"] == mock_tag_resolver
            assert "content_type" in call_args["metadata"]
            assert call_args["metadata"]["content_type"] == "creature"

    def test_attack_markup_processing(self):
        """Test processing of attack-related markup tags."""
        ability = Ability(
            name="Longsword",
            entries=[
                "{@atk mw} {@hit 7} to hit, reach 5 ft., one target.",
                "Hit: {@damage 1d8 + 3} slashing damage, or {@damage 1d10 + 3} slashing damage if used with two hands.",
            ],
        )

        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "Melee Weapon Attack: +7 to hit, reach 5 ft., one target.",
                "Hit: 1d8 + 3 slashing damage, or 1d10 + 3 slashing damage if used with two hands.",
            ]
            mock_processor_class.return_value = mock_processor

            processed_text = ability.get_description_text()
            assert "Melee Weapon Attack" in processed_text
            assert "+7 to hit" in processed_text
            assert "1d8 + 3 slashing damage" in processed_text

    def test_spell_reference_markup(self):
        """Test processing of spell reference markup."""
        ability = Ability(
            name="Innate Spellcasting",
            entries=[
                "The creature's innate spellcasting ability is Charisma (spell save DC 15).",
                "It can innately cast the following spells, requiring no material components:",
                "At will: {@spell detect magic}, {@spell light}",
                "3/day each: {@spell dispel magic}, {@spell fireball}",
                "1/day: {@spell greater invisibility}",
            ],
        )

        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "The creature's innate spellcasting ability is Charisma (spell save DC 15).",
                "It can innately cast the following spells, requiring no material components:",
                "At will: detect magic, light",
                "3/day each: dispel magic, fireball",
                "1/day: greater invisibility",
            ]
            mock_processor_class.return_value = mock_processor

            processed_text = ability.get_description_text()
            assert "spell save DC 15" in processed_text
            assert "detect magic" in processed_text
            assert "fireball" in processed_text
            assert "greater invisibility" in processed_text

    def test_condition_markup_processing(self):
        """Test processing of condition-related markup."""
        ability = Ability(
            name="Frightful Presence",
            entries=[
                "Each creature of the dragon's choice that is within 120 feet of the dragon and aware of it must succeed on a DC 19 Wisdom saving throw or become {@condition frightened} for 1 minute.",
                "A creature can repeat the saving throw at the end of each of its turns, ending the effect on itself on a success.",
            ],
        )

        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "Each creature of the dragon's choice that is within 120 feet of the dragon and aware of it must succeed on a DC 19 Wisdom saving throw or become frightened for 1 minute.",
                "A creature can repeat the saving throw at the end of each of its turns, ending the effect on itself on a success.",
            ]
            mock_processor_class.return_value = mock_processor

            processed_text = ability.get_description_text()
            assert "DC 19 Wisdom saving throw" in processed_text
            assert "frightened for 1 minute" in processed_text

    def test_recharge_markup_processing(self):
        """Test processing of recharge-related markup."""
        ability = Ability(
            name="Breath Weapon {@recharge 5}",
            entries=[
                "The dragon exhales acid in a 60-foot line that is 5 feet wide.",
                "Each creature in that line must make a DC 18 Dexterity saving throw, taking {@damage 12d8} acid damage on a failed save, or half as much damage on a successful one.",
            ],
        )

        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "The dragon exhales acid in a 60-foot line that is 5 feet wide.",
                "Each creature in that line must make a DC 18 Dexterity saving throw, taking 12d8 acid damage on a failed save, or half as much damage on a successful one.",
            ]
            mock_processor_class.return_value = mock_processor

            # Test name processing
            mock_processor.process_entries.return_value = [
                "Breath Weapon (Recharge 5-6)"
            ]
            processed_name = ability.get_processed_name()
            assert "Recharge 5-6" in processed_name

            # Test description processing
            mock_processor.process_entries.return_value = [
                "The dragon exhales acid in a 60-foot line that is 5 feet wide.",
                "Each creature in that line must make a DC 18 Dexterity saving throw, taking 12d8 acid damage on a failed save, or half as much damage on a successful one.",
            ]
            processed_description = ability.get_description_text()
            assert "12d8 acid damage" in processed_description


class TestCreatureMarkupEdgeCases:
    """Test edge cases and error handling in markup processing."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_empty_entry_processing(self):
        """Test processing of empty or None entries."""
        ability = Ability(name="Empty Test", entries=[])

        # Should handle empty entries gracefully
        with patch(
            "dnd5e.cli.main.get_tag_resolver", side_effect=Exception("No resolver")
        ):
            description = ability.get_description_text()
            assert description == ""

    def test_mixed_entry_types_processing(self):
        """Test processing of mixed entry types in fallback mode."""
        ability = Ability(
            name="Mixed Entries",
            entries=[
                "String entry",
                {"type": "entries", "name": "Subsection", "entries": ["Nested string"]},
                {"text": "Direct text field"},
                {"name": "Named entry", "text": "Named text"},
            ],
        )

        # Test fallback text extraction without tag processing
        with patch(
            "dnd5e.cli.main.get_tag_resolver", side_effect=Exception("No resolver")
        ):
            description = ability.get_description_text()
            assert "String entry" in description
            assert "Subsection" in description
            assert "Nested string" in description
            assert "Direct text field" in description
            assert "Named entry" in description
            assert "Named text" in description

    def test_malformed_entry_handling(self):
        """Test handling of malformed or unexpected entry structures."""
        # Create an ability with some malformed entries - filter out None values since Pydantic won't accept them
        entries = [
            "Valid string",
            {"incomplete": "dict"},  # Missing expected fields
            # Skip None as Pydantic validation will reject it
            "123",  # String representation of number
        ]

        ability = Ability(name="Malformed Test", entries=entries)

        # Should handle malformed entries without crashing
        with patch(
            "dnd5e.cli.main.get_tag_resolver", side_effect=Exception("No resolver")
        ):
            description = ability.get_description_text()
            assert "Valid string" in description
            # Other entries should be converted to strings or handled gracefully

    def test_entry_processor_construction_failure(self):
        """Test handling when entry processor construction fails."""
        ability = Ability(name="Test Ability", entries=["Test entry"])

        # Mock components that might fail during construction
        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor",
                side_effect=Exception("Construction failed"),
            ),
        ):
            # Should fall back to simple text extraction
            description = ability.get_description_text()
            assert "Test entry" in description

    def test_context_creation_failure(self):
        """Test handling when rendering context creation fails."""
        ability = Ability(name="Test Ability", entries=["Test entry"])

        mock_tag_resolver = Mock()
        mock_omnidexer = Mock()

        with (
            patch("dnd5e.cli.main.get_tag_resolver", return_value=mock_tag_resolver),
            patch("dnd5e.cli.main.get_omnidexer", return_value=mock_omnidexer),
            patch(
                "dnd5e.renderers.core.interfaces.RenderingContext",
                side_effect=Exception("Context creation failed"),
            ),
        ):
            # Should fall back to simple text extraction
            description = ability.get_description_text()
            assert "Test entry" in description
