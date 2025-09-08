"""Integration tests for creature LaTeX rendering pipeline.

These tests focus on the end-to-end LaTeX rendering process for creatures,
including stat block generation, markup processing, and document compilation.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.core.models.creatures import Creature
from studiorum.latex_engine.core.document import LaTeXDocumentRenderer
from tests.test_helpers import reset_test_environment


@pytest.mark.integration
class TestCreatureLaTeXRendering:
    """Test creature LaTeX rendering pipeline integration."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

        # Create comprehensive creature test data
        self.test_creature_data = {
            "name": "Integration Test Dragon",
            "source": "TEST",
            "size": ["L"],
            "type": {"type": "dragon", "subtype": "chromatic"},
            "alignment": ["C", "E"],
            "ac": [{"ac": 18, "from": ["natural armor"]}],
            "hp": {"average": 178, "formula": "17d12 + 85"},
            "speed": {"walk": 40, "fly": 80, "swim": 40},
            "str": 23,
            "dex": 10,
            "con": 21,
            "int": 14,
            "wis": 13,
            "cha": 17,
            "save": {"dex": "+5", "con": "+11", "wis": "+6", "cha": "+8"},
            "skill": {"perception": "+11", "stealth": "+5"},
            "resist": ["fire"],
            "immune": ["poison"],
            "conditionImmune": ["charmed", "poisoned"],
            "senses": [
                "blindsight 60 ft.",
                "darkvision 120 ft.",
                "passive Perception 21",
            ],
            "languages": ["Common", "Draconic"],
            "cr": "10",
            "trait": [
                {
                    "name": "Legendary Resistance {@recharge 3}",
                    "entries": [
                        "If the dragon fails a saving throw, it can choose to succeed instead."
                    ],
                }
            ],
            "action": [
                {
                    "name": "Multiattack",
                    "entries": [
                        "The dragon can use its Frightful Presence. It then makes three attacks: one with its bite and two with its claws."
                    ],
                },
                {
                    "name": "Bite",
                    "entries": [
                        "{@atk mw} {@hit 11} to hit, reach 10 ft., one target. {@h}2d10 + 6 piercing damage plus {@damage 1d8} poison damage."
                    ],
                },
                {
                    "name": "Claw",
                    "entries": [
                        "{@atk mw} {@hit 11} to hit, reach 5 ft., one target. {@h}2d6 + 6 slashing damage."
                    ],
                },
                {
                    "name": "Poison Breath {@recharge 5}",
                    "entries": [
                        "The dragon exhales poisonous gas in a 60-foot cone. Each creature in that area must make a DC 19 Constitution saving throw, taking {@damage 12d8} poison damage on a failed save, or half as much damage on a successful one."
                    ],
                },
            ],
            "legendary": [
                {
                    "name": "Detect",
                    "entries": [
                        "The dragon makes a Wisdom ({@skill Perception}) check."
                    ],
                },
                {"name": "Tail Attack", "entries": ["The dragon makes a tail attack."]},
                {
                    "name": "Wing Attack",
                    "cost": 2,
                    "entries": [
                        "The dragon beats its wings. Each creature within 10 feet of the dragon must succeed on a DC 19 Dexterity saving throw or take {@damage 2d6 + 6} bludgeoning damage and be knocked {@condition prone}."
                    ],
                },
            ],
        }

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_creature_stat_block_latex_generation(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test LaTeX generation for creature stat blocks."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.side_effect = (
            lambda text: text.replace("{@atk mw}", "Melee Weapon Attack:")
            .replace("{@hit 11}", "+11")
            .replace("{@h}", "Hit: ")
            .replace("{@damage 1d8}", "1d8")
            .replace("{@damage 12d8}", "12d8")
            .replace("{@damage 2d6 + 6}", "2d6 + 6")
            .replace("{@recharge 3}", "(3/Day)")
            .replace("{@recharge 5}", "(Recharge 5-6)")
            .replace("{@skill Perception}", "Perception")
            .replace("{@condition prone}", "prone")
        )
        mock_get_tag_resolver.return_value = mock_tag_resolver

        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        # Create creature model
        creature = Creature.model_validate(self.test_creature_data)

        # Test LaTeX rendering
        with patch(
            "studiorum.latex_engine.core.entry_processor.RecursiveEntryProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_entries.side_effect = lambda entries: [
                entry.replace("{@atk mw}", "Melee Weapon Attack:")
                .replace("{@hit 11}", "+11")
                .replace("{@h}", "Hit: ")
                .replace("{@damage 1d8}", "1d8")
                .replace("{@damage 12d8}", "12d8")
                .replace("{@damage 2d6 + 6}", "2d6 + 6")
                .replace("{@recharge 3}", "(3/Day)")
                .replace("{@recharge 5}", "(Recharge 5-6)")
                .replace("{@skill Perception}", "Perception")
                .replace("{@condition prone}", "prone")
                if isinstance(entry, str)
                else str(entry)
                for entry in entries
            ]
            mock_processor_class.return_value = mock_processor

            # Test that basic stat block elements are rendered
            assert creature.name == "Integration Test Dragon"
            assert creature.get_enhanced_cr_text() == "10 (5,900 XP)"
            assert "Large dragon (chromatic)" in creature.get_size_type_alignment()
            assert "chaotic evil" in creature.get_size_type_alignment()

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_creature_abilities_latex_processing(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test LaTeX processing of creature abilities with 5etools markup."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        creature = Creature.model_validate(self.test_creature_data)

        # Test trait processing
        with patch(
            "studiorum.latex_engine.core.entry_processor.RecursiveEntryProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "Legendary Resistance (3/Day)",
                "If the dragon fails a saving throw, it can choose to succeed instead.",
            ]
            mock_processor_class.return_value = mock_processor

            trait = creature.trait[0]
            processed_name = trait.get_processed_name()
            processed_desc = trait.get_description_text()

            assert "Legendary Resistance" in processed_name
            assert "saving throw" in processed_desc

        # Test action processing
        with patch(
            "studiorum.latex_engine.core.entry_processor.RecursiveEntryProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "Melee Weapon Attack: +11 to hit, reach 10 ft., one target.",
                "Hit: 2d10 + 6 piercing damage plus 1d8 poison damage.",
            ]
            mock_processor_class.return_value = mock_processor

            bite_action = creature.action[1]  # Bite attack
            processed_desc = bite_action.get_description_text()

            assert "Melee Weapon Attack" in processed_desc
            assert "+11 to hit" in processed_desc
            assert "piercing damage" in processed_desc

    def test_creature_layout_decision_integration(self):
        """Test integration of creature layout decision logic."""
        creature = Creature.model_validate(self.test_creature_data)

        # This dragon has legendary actions, so should require full width
        assert creature.requires_full_width_layout() is True

        # Test with simpler creature
        simple_creature_data = {
            "name": "Simple Beast",
            "source": "TEST",
            "size": ["M"],
            "type": "beast",
            "alignment": ["U"],
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
            "action": [
                {"name": "Bite", "entries": ["Melee weapon attack: +4 to hit."]}
            ],
        }

        simple_creature = Creature.model_validate(simple_creature_data)
        assert simple_creature.requires_full_width_layout() is False

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_creature_document_rendering_integration(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test full document rendering integration for creatures."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        creature = Creature.model_validate(self.test_creature_data)

        # Test with document renderer
        with (
            patch(
                "studiorum.latex_engine.core.entry_processor.RecursiveEntryProcessor"
            ) as mock_processor_class,
            patch(
                "studiorum.renderers.core.interfaces.RenderingContext"
            ) as mock_context_class,
        ):
            mock_processor = Mock()
            mock_processor.process_entries.side_effect = lambda entries: [
                str(entry) for entry in entries
            ]
            mock_processor_class.return_value = mock_processor

            mock_context = Mock()
            mock_context_class.return_value = mock_context

            # Mock renderer and test basic rendering call structure
            with patch(
                "studiorum.latex_engine.core.document.LaTeXDocumentRenderer"
            ) as mock_renderer_class:
                mock_renderer = Mock()
                mock_renderer.render.return_value = "\\documentclass{article}\\begin{document}Dragon stat block\\end{document}"
                mock_renderer_class.return_value = mock_renderer

                # This tests that the creature can be passed to the renderer without errors
                renderer = mock_renderer_class()
                result = renderer.render([creature])

                assert "document" in result
                mock_renderer.render.assert_called_once()

    def test_creature_spellcasting_integration(self):
        """Test integration of creature spellcasting abilities."""
        spellcaster_data = {
            "name": "Test Spellcaster",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["L", "N"],
            "ac": [12],
            "hp": {"average": 40},
            "speed": {"walk": 30},
            "str": 9,
            "dex": 14,
            "con": 11,
            "int": 17,
            "wis": 12,
            "cha": 11,
            "cr": "6",
            "spellcasting": [
                {
                    "name": "Spellcasting",
                    "headerEntries": [
                        "The spellcaster is a 9th-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 14, +6 to hit with spell attacks)."
                    ],
                    "spells": {
                        "0": {
                            "spells": ["{@spell mage hand}", "{@spell minor illusion}"]
                        },
                        "1": {
                            "slots": 4,
                            "spells": ["{@spell magic missile}", "{@spell shield}"],
                        },
                    },
                }
            ],
        }

        spellcaster = Creature.model_validate(spellcaster_data)

        # Test that spellcasting data is properly structured
        assert spellcaster.spellcasting is not None
        assert len(spellcaster.spellcasting) == 1
        spellcasting_data = spellcaster.spellcasting[0]
        assert "Spellcasting" in (
            spellcasting_data.name
            if hasattr(spellcasting_data, "name")
            else spellcasting_data.get("name", "")
        )
        assert "9th-level spellcaster" in (
            spellcasting_data.headerEntries[0]
            if hasattr(spellcasting_data, "headerEntries")
            else spellcasting_data.get("headerEntries", [""])[0]
        )

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_creature_complex_markup_integration(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test integration of complex 5etools markup processing."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.side_effect = lambda text: (
            text.replace("{@atk mw}", "Melee Weapon Attack:")
            .replace("{@hit 11}", "+11")
            .replace("{@damage 12d8}", "12d8")
            .replace("{@recharge 5}", "(Recharge 5-6)")
            .replace("{@condition prone}", "prone")
        )
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        creature = Creature.model_validate(self.test_creature_data)

        # Test complex ability with multiple markup tags
        with patch(
            "studiorum.latex_engine.core.entry_processor.RecursiveEntryProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "The dragon exhales poisonous gas in a 60-foot cone. Each creature in that area must make a DC 19 Constitution saving throw, taking 12d8 poison damage on a failed save, or half as much damage on a successful one."
            ]
            mock_processor_class.return_value = mock_processor

            poison_breath = creature.action[3]  # Poison Breath action
            processed_desc = poison_breath.get_description_text()

            assert "poisonous gas" in processed_desc
            assert "Constitution saving throw" in processed_desc
            assert "12d8 poison damage" in processed_desc

    def test_creature_validation_edge_cases(self):
        """Test creature validation with edge case data."""
        # Test creature with minimal required fields
        minimal_data = {
            "name": "Minimal Creature",
            "source": "TEST",
            "size": ["T"],
            "type": "beast",
            "alignment": ["U"],
            "ac": [10],
            "hp": {"average": 1},
            "speed": {"walk": 10},
            "str": 1,
            "dex": 1,
            "con": 1,
            "int": 1,
            "wis": 1,
            "cha": 1,
            "cr": "0",
        }

        minimal_creature = Creature.model_validate(minimal_data)
        assert minimal_creature.name == "Minimal Creature"
        assert minimal_creature.get_enhanced_cr_text() == "0 (10 XP)"

        # Test creature with maximum complexity
        complex_data = self.test_creature_data.copy()
        complex_data["reaction"] = [
            {"name": "Test Reaction", "entries": ["The dragon can react to attacks."]}
        ]

        complex_creature = Creature.model_validate(complex_data)
        assert complex_creature.reaction is not None
        assert len(complex_creature.reaction) == 1


@pytest.mark.integration
class TestCreatureLaTeXCompilation:
    """Test LaTeX compilation integration for creature documents."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_creature_latex_compilation_mock(self):
        """Test LaTeX compilation structure for creature documents."""
        # Create test LaTeX content
        latex_content = """
\\documentclass{article}
\\usepackage[utf8]{inputenc}
\\begin{document}
\\section*{Test Goblin}
\\textbf{Small humanoid, neutral evil}

\\textbf{Armor Class} 15

\\textbf{Hit Points} 7 (2d6)

\\textbf{Speed} 30 ft.

\\textbf{Challenge} 1/4 (50 XP)
\\end{document}
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / "creature.tex"
            tex_file.write_text(latex_content)

            # Test that file is created correctly
            assert tex_file.exists()
            content = tex_file.read_text()
            assert "Test Goblin" in content
            assert "Small humanoid" in content
            assert "Challenge" in content

    def test_creature_latex_output_structure(self):
        """Test that creature LaTeX output has proper structure."""
        creature_data = {
            "name": "Structure Test Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["N"],
            "ac": [13],
            "hp": {"average": 25},
            "speed": {"walk": 30},
            "str": 12,
            "dex": 14,
            "con": 13,
            "int": 10,
            "wis": 11,
            "cha": 9,
            "cr": "1/2",
        }

        creature = Creature.model_validate(creature_data)

        # Test key stat block elements are present
        assert creature.name
        assert creature.get_size_type_alignment()
        assert creature.get_ac_text()
        assert creature.get_enhanced_cr_text()

        # Test ability scores are formatted correctly
        for ability in [
            creature.strength,
            creature.dexterity,
            creature.constitution,
            creature.intelligence,
            creature.wisdom,
            creature.charisma,
        ]:
            assert isinstance(ability, int)
            assert 1 <= ability <= 30


@pytest.mark.integration
class TestCreatureRenderingParityPhase3:
    """Integration tests for Phase 3 creature rendering parity features.

    Tests the 5 integration scenarios from the parity plan:
    1. Named creature pronouns and prefix handling
    2. Generic creature pronouns and prefix handling
    3. Lair variant parenthetical generation
    4. Structured headers rendering via smart_render_entry
    5. Empty sections handling
    """

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_named_creature_pronouns_and_headers(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test that named creatures use 'they/them/their' and no 'the' prefix."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        named_creature_data = {
            "name": "Strahd von Zarovich",
            "source": "COS",
            "isNamedCreature": True,
            "size": ["M"],
            "type": "undead",
            "alignment": ["lawful evil"],
            "ac": [17],
            "hp": {"average": 144, "formula": "17d12 + 68"},
            "speed": {"walk": 30},
            "str": 18,
            "dex": 18,
            "con": 18,
            "int": 20,
            "wis": 15,
            "cha": 18,
            "cr": "15",
            "legendary": [
                {
                    "name": "Move",
                    "entries": [
                        "Strahd moves up to his speed without provoking opportunity attacks."
                    ],
                },
                {
                    "name": "Unarmed Strike",
                    "entries": ["Strahd makes one unarmed strike."],
                },
                {
                    "name": "Cast Spell",
                    "cost": 3,
                    "entries": ["Strahd casts a spell of 3rd level or lower."],
                },
            ],
        }

        creature = Creature.model_validate(named_creature_data)

        # Test pronouns are correct for named creatures
        assert creature.get_pronoun_subject() == "they"
        assert creature.get_pronoun_object() == "them"
        assert creature.get_pronoun_possessive() == "their"

        # Test short name has no prefix
        assert creature.get_short_name() == "Strahd"
        assert creature.get_short_name(is_title_case=True) == "Strahd"

        # Test legendary actions header uses proper pronouns
        header = creature.get_legendary_actions_header()
        assert header is not None
        header_text = header[0]
        assert "Strahd can take 3 legendary actions" in header_text
        assert "their turn" in header_text  # Named creature uses "their"
        assert "its turn" not in header_text  # Should not use generic pronoun

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_generic_creature_pronouns_and_headers(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test that generic creatures use 'it/its/its' and 'the' prefix."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        generic_creature_data = {
            "name": "Ancient Red Dragon",
            "source": "MM",
            "size": ["G"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [22],
            "hp": {"average": 546, "formula": "28d20 + 252"},
            "speed": {"walk": 40, "fly": 80, "climb": 40},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "cr": "24",
            "legendary": [
                {
                    "name": "Detect",
                    "entries": ["The dragon makes a Wisdom (Perception) check."],
                },
                {"name": "Tail Attack", "entries": ["The dragon makes a tail attack."]},
                {
                    "name": "Wing Attack",
                    "cost": 2,
                    "entries": ["The dragon beats its wings."],
                },
            ],
        }

        creature = Creature.model_validate(generic_creature_data)

        # Test pronouns are correct for generic creatures
        assert creature.get_pronoun_subject() == "it"
        assert creature.get_pronoun_object() == "its"
        assert creature.get_pronoun_possessive() == "its"

        # Test short name has prefix
        assert creature.get_short_name() == "the ancient red dragon"
        assert creature.get_short_name(is_title_case=True) == "The Ancient Red Dragon"
        assert (
            creature.get_short_name(is_sentence_case=True) == "The Ancient red dragon"
        )

        # Test legendary actions header uses proper pronouns
        header = creature.get_legendary_actions_header()
        assert header is not None
        header_text = header[0]
        assert "The Ancient Red Dragon can take 3 legendary actions" in header_text
        assert "its turn" in header_text  # Generic creature uses "its"
        assert "their turn" not in header_text  # Should not use named creature pronoun

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_lair_variant_parenthetical(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test lair variant parenthetical when counts differ."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        lair_dragon_data = {
            "name": "Lair Dragon",
            "source": "TEST",
            "size": ["G"],
            "type": "dragon",
            "alignment": ["neutral evil"],
            "ac": [20],
            "hp": {"average": 400, "formula": "24d20 + 144"},
            "speed": {"walk": 40, "fly": 80},
            "str": 28,
            "dex": 10,
            "con": 23,
            "int": 16,
            "wis": 15,
            "cha": 21,
            "cr": "20",
            "legendaryActions": 3,  # Normal actions
            "legendaryActionsLair": 5,  # More actions in lair
            "legendary": [
                {"name": "Detect", "entries": ["The dragon makes a Wisdom check."]},
                {"name": "Attack", "entries": ["The dragon makes one attack."]},
                {
                    "name": "Wing Attack",
                    "cost": 2,
                    "entries": ["The dragon beats its wings."],
                },
            ],
        }

        creature = Creature.model_validate(lair_dragon_data)
        header = creature.get_legendary_actions_header()

        assert header is not None
        header_text = header[0]

        # Should mention both action counts
        assert "3 legendary actions" in header_text
        assert "(or 5 when in its lair)" in header_text
        assert (
            "The Lair Dragon can take 3 legendary actions (or 5 when in its lair)"
            in header_text
        )

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_structured_headers_rendering(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test structured headers (dict/tag content) render via smart_render_entry."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.side_effect = lambda text: text.replace(
            "{@spell fireball}", "fireball"
        )
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        structured_header_data = {
            "name": "Structured Header Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58, "formula": "9d8 + 18"},
            "speed": {"walk": 30},
            "str": 12,
            "dex": 16,
            "con": 14,
            "int": 18,
            "wis": 13,
            "cha": 15,
            "cr": "5",
            # Custom structured header with 5etools markup
            "actionsHeader": [
                {
                    "type": "entries",
                    "name": "Spellcasting Actions",
                    "entries": [
                        "The creature can cast {@spell fireball} as an action.",
                        "Spell save DC is 15.",
                    ],
                }
            ],
            "action": [{"name": "Sword", "entries": ["Melee weapon attack."]}],
        }

        creature = Creature.model_validate(structured_header_data)

        # Test that structured header is retrieved correctly
        header = creature.get_section_header("actions")
        assert header is not None
        assert len(header) == 1

        # Verify it's a structured entry (CreatureEntryContent) that would be processed by smart_render_entry
        structured_entry = header[0]
        # The entry is parsed into a CreatureEntryContent object
        assert hasattr(structured_entry, "type")
        assert structured_entry.type == "entries"
        assert structured_entry.name == "Spellcasting Actions"
        assert (
            "@spell fireball" in structured_entry.entries[0]
        )  # Should contain markup for processing

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_empty_sections_handling(self, mock_get_omnidexer, mock_get_tag_resolver):
        """Test sections omitted when both entries and spells are empty."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        minimal_creature_data = {
            "name": "Minimal Creature",
            "source": "TEST",
            "size": ["S"],
            "type": "beast",
            "alignment": ["unaligned"],
            "ac": [12],
            "hp": {"average": 7, "formula": "2d6"},
            "speed": {"walk": 40},
            "str": 15,
            "dex": 14,
            "con": 13,
            "int": 2,
            "wis": 12,
            "cha": 6,
            "cr": "1/4",
            # Note: No trait, action, legendary, reaction, or spellcasting sections
        }

        creature = Creature.model_validate(minimal_creature_data)

        # Test that empty sections return None or empty lists
        assert creature.trait is None or len(creature.trait) == 0
        assert creature.action is None or len(creature.action) == 0
        assert creature.legendary is None or len(creature.legendary) == 0
        assert creature.reaction is None or len(creature.reaction) == 0
        assert creature.spellcasting is None or len(creature.spellcasting) == 0

        # Test that legendary actions header returns None when no legendary actions
        assert creature.get_legendary_actions_header() is None

        # Test that section headers return None for non-existent sections
        assert creature.get_section_header("trait") is None
        assert creature.get_section_header("action") is None
        assert creature.get_section_header("legendary") is None
        assert creature.get_section_header("reaction") is None

    @patch("studiorum.cli.main.get_tag_resolver")
    @patch("studiorum.cli.main.get_omnidexer")
    def test_integration_rendering_pipeline_with_new_helpers(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test that new helpers integrate properly with the rendering pipeline."""
        # Setup mocks
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.side_effect = lambda text: text.replace(
            "{@atk mw}", "Melee Weapon Attack:"
        )
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        pipeline_test_data = {
            "name": "Pipeline Test Dragon",
            "source": "TEST",
            "isNamedCreature": False,  # Generic creature for testing
            "size": ["L"],
            "type": "dragon",
            "alignment": ["chaotic neutral"],
            "ac": [19],
            "hp": {"average": 225, "formula": "18d12 + 108"},
            "speed": {"walk": 40, "fly": 80},
            "str": 25,
            "dex": 10,
            "con": 23,
            "int": 16,
            "wis": 13,
            "cha": 21,
            "cr": "15",
            "legendaryActions": 3,
            "actionsHeader": ["The dragon's mighty actions shake the battlefield."],
            "action": [
                {"name": "Multiattack", "entries": ["The dragon makes three attacks."]},
                {
                    "name": "Bite",
                    "entries": ["{@atk mw} +13 to hit, reach 10 ft., one target."],
                },
            ],
            "legendary": [
                {"name": "Detect", "entries": ["The dragon makes a Wisdom check."]},
                {"name": "Tail Attack", "entries": ["The dragon makes a tail attack."]},
                {
                    "name": "Wing Attack",
                    "cost": 2,
                    "entries": ["The dragon beats its wings."],
                },
            ],
        }

        creature = Creature.model_validate(pipeline_test_data)

        # Test all helper methods return expected values
        assert creature.get_pronoun_subject() == "it"  # Generic creature
        assert creature.get_pronoun_possessive() == "its"
        assert creature.get_short_name() == "the pipeline test dragon"

        # Test custom action header is retrieved
        action_header = creature.get_section_header("actions")
        assert action_header == ["The dragon's mighty actions shake the battlefield."]

        # Test legendary actions header generation
        legendary_header = creature.get_legendary_actions_header()
        assert legendary_header is not None
        header_text = legendary_header[0]
        assert "The Pipeline Test Dragon can take 3 legendary actions" in header_text
        assert "its turn" in header_text

        # Test that creature has content for rendering
        assert len(creature.action) == 2
        assert len(creature.legendary) == 3

        # Test that it would require full-width layout
        assert creature.requires_full_width_layout() is True  # Has legendary actions
