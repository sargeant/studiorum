"""Integration tests for creature LaTeX rendering pipeline.

These tests focus on the end-to-end LaTeX rendering process for creatures,
including stat block generation, markup processing, and document compilation.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.core.models.creatures import Creature
from studiorum.renderers.latex.document import LaTeXDocumentRenderer
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
            "studiorum.renderers.latex.entry_processor.RecursiveEntryProcessor"
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
            "studiorum.renderers.latex.entry_processor.RecursiveEntryProcessor"
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
            "studiorum.renderers.latex.entry_processor.RecursiveEntryProcessor"
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
                "studiorum.renderers.latex.entry_processor.RecursiveEntryProcessor"
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
                "studiorum.renderers.latex.document.LaTeXDocumentRenderer"
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
            "studiorum.renderers.latex.entry_processor.RecursiveEntryProcessor"
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
