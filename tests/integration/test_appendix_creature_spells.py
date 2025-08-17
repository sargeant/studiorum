"""Integration tests for creature spell references in appendix generation."""

from unittest.mock import MagicMock

import pytest

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.spells import Spell
from dnd5e.core.references.content_tracker import ContentTracker
from dnd5e.core.services.appendix_generator import AppendixFlags, AppendixGenerator
from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine


@pytest.mark.integration
class TestAppendixCreatureSpells:
    """Test that creature spell references are captured in appendix generation."""

    def setup_method(self) -> None:
        """Reset test environment."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

    def test_creature_appendix_captures_spell_references(self):
        """Test that rendering creatures for appendix captures {@spell} references."""
        # Create mock spells
        mock_fireball = Spell.model_validate(
            {
                "name": "Fireball",
                "source": {"abbreviation": "PHB"},
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
                "components": {
                    "v": True,
                    "s": True,
                    "m": "a tiny ball of bat guano and sulfur",
                },
                "duration": [{"type": "instant"}],
                "entries": ["A bright streak flashes from your pointing finger..."],
            }
        )

        mock_shield = Spell.model_validate(
            {
                "name": "Shield",
                "source": {"abbreviation": "PHB"},
                "level": 1,
                "school": "A",
                "time": [{"number": 1, "unit": "reaction"}],
                "range": {"type": "point", "distance": {"type": "self"}},
                "components": {"v": True, "s": True},
                "duration": [
                    {"type": "timed", "duration": {"type": "round", "amount": 1}}
                ],
                "entries": ["An invisible barrier of magical force appears..."],
            }
        )

        # Create mock omnidexer
        mock_omnidexer = MagicMock(spec=Omnidexer)
        mock_omnidexer.find.side_effect = lambda content_type, name, source=None: {
            ("spell", "fireball"): mock_fireball,
            ("spell", "shield"): mock_shield,
        }.get((content_type.type_name, name.lower()))

        # Create mock template engine
        mock_template_engine = MagicMock(spec=LaTeXTemplateEngine)

        # Create creature with spell references
        creature_data = {
            "name": "Test Wizard",
            "source": {"abbreviation": "TEST"},
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [12],
            "hp": {"average": 20},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 16,
            "wis": 12,
            "cha": 10,
            "action": [
                {
                    "name": "Spellcasting",
                    "entries": [
                        "The wizard casts {@spell fireball|phb} at 3rd level.",
                        "As a reaction, the wizard can cast {@spell shield|phb}.",
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Create ContentTracker and add the creature
        content_tracker = ContentTracker()
        content_tracker.add_content("creature", "Test Wizard", "TEST", page="1")

        # Create AppendixGenerator and mock the creature collector
        appendix_generator = AppendixGenerator(mock_omnidexer, mock_template_engine)

        # Mock the creature collector to return our test creature
        appendix_generator.creature_collector.collect_by_names = MagicMock()
        mock_result = MagicMock()
        mock_result.creatures = [creature]
        appendix_generator.creature_collector.collect_by_names.return_value = (
            mock_result
        )

        # Mock the entry renderer registry to return simple LaTeX
        mock_creature_renderer = MagicMock()
        mock_creature_renderer.render.return_value = (
            "\\section{Test Wizard} Mock creature content with spells"
        )
        appendix_generator.entry_registry.get_renderer = MagicMock(
            return_value=mock_creature_renderer
        )

        # Generate creature appendix with spell tracking
        flags = AppendixFlags(creatures=True, spells=False, items=False)

        # This should render the creature and capture spell references
        appendices = appendix_generator.generate_appendices(content_tracker, flags)

        # Verify creature appendix was generated
        assert len(appendices) == 1
        creature_appendix = appendices[0]
        assert creature_appendix.title == "Appendix C: Creatures"
        assert creature_appendix.content_type == "creature"
        assert creature_appendix.item_count == 1

        # Verify that the creature renderer was called with ContentTracker in context
        mock_creature_renderer.render.assert_called_once()
        call_args = mock_creature_renderer.render.call_args
        rendered_creature = call_args[0][0]
        rendering_context = call_args[0][1]

        assert rendered_creature == creature
        assert rendering_context.output_format == "latex"
        assert rendering_context.omnidexer == mock_omnidexer
        assert rendering_context.content_tracker == content_tracker

    def test_spells_appendix_includes_creature_referenced_spells(self):
        """Test complete flow: creature appendix renders with spell tracking, spells appendix includes those spells."""
        # Create mock spells
        mock_fireball = Spell.model_validate(
            {
                "name": "Fireball",
                "source": {"abbreviation": "PHB"},
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
                "components": {
                    "v": True,
                    "s": True,
                    "m": "a tiny ball of bat guano and sulfur",
                },
                "duration": [{"type": "instant"}],
                "entries": ["A bright streak flashes from your pointing finger..."],
            }
        )

        mock_shield = Spell.model_validate(
            {
                "name": "Shield",
                "source": {"abbreviation": "PHB"},
                "level": 1,
                "school": "A",
                "time": [{"number": 1, "unit": "reaction"}],
                "range": {"type": "point", "distance": {"type": "self"}},
                "components": {"v": True, "s": True},
                "duration": [
                    {"type": "timed", "duration": {"type": "round", "amount": 1}}
                ],
                "entries": ["An invisible barrier of magical force appears..."],
            }
        )

        # Create mock omnidexer
        mock_omnidexer = MagicMock(spec=Omnidexer)
        mock_omnidexer.find.side_effect = lambda content_type, name, source=None: {
            ("spell", "fireball"): mock_fireball,
            ("spell", "shield"): mock_shield,
        }.get((content_type.type_name, name.lower()))

        # Create mock template engine
        mock_template_engine = MagicMock(spec=LaTeXTemplateEngine)

        # Create creature with spell references
        creature_data = {
            "name": "Test Wizard",
            "source": {"abbreviation": "TEST"},
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [12],
            "hp": {"average": 20},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 16,
            "wis": 12,
            "cha": 10,
            "action": [
                {
                    "name": "Spellcasting",
                    "entries": [
                        "The wizard casts {@spell fireball|phb} at 3rd level.",
                        "As a reaction, the wizard can cast {@spell shield|phb}.",
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Create ContentTracker and add the creature (but NO spells initially)
        content_tracker = ContentTracker()
        content_tracker.add_content("creature", "Test Wizard", "TEST", page="1")

        # Create AppendixGenerator and mock collectors
        appendix_generator = AppendixGenerator(mock_omnidexer, mock_template_engine)

        # Mock the creature collector
        appendix_generator.creature_collector.collect_by_names = MagicMock()
        mock_creature_result = MagicMock()
        mock_creature_result.creatures = [creature]
        appendix_generator.creature_collector.collect_by_names.return_value = (
            mock_creature_result
        )

        # Mock the spell collector
        appendix_generator.spell_collector.collect_by_names = MagicMock()
        mock_spell_result = MagicMock()
        mock_spell_result.spells = [mock_fireball, mock_shield]
        appendix_generator.spell_collector.collect_by_names.return_value = (
            mock_spell_result
        )

        # Mock the entry renderers to simulate actual tag processing
        def mock_creature_render(creature_obj, context):
            # Simulate the creature renderer processing {@spell} tags and tracking them
            if context.content_tracker:
                # This simulates what would happen when {@spell} tags are processed
                context.content_tracker.add_content(
                    "spell", "fireball", "PHB", page="1"
                )
                context.content_tracker.add_content("spell", "shield", "PHB", page="1")
            return "\\section{Test Wizard} Mock creature content with spells"

        def mock_spell_render(spell_obj, context):
            return f"\\subsubsection{{{spell_obj.name}}} Mock spell content"

        mock_creature_renderer = MagicMock()
        mock_creature_renderer.render.side_effect = mock_creature_render

        mock_spell_renderer = MagicMock()
        mock_spell_renderer.render.side_effect = mock_spell_render

        appendix_generator.entry_registry.get_renderer = MagicMock()
        appendix_generator.entry_registry.get_renderer.side_effect = (
            lambda content_type: {
                "creature": mock_creature_renderer,
                "spell": mock_spell_renderer,
            }[content_type]
        )

        # Generate appendices with both creatures and spells enabled
        flags = AppendixFlags(creatures=True, spells=True, items=False)

        # This should:
        # 1. Generate creature appendix and capture spell references during rendering
        # 2. Generate spell appendix including the newly tracked spells
        appendices = appendix_generator.generate_appendices(content_tracker, flags)

        # Verify both appendices were generated
        assert len(appendices) == 2

        # Find the appendices
        creature_appendix = next(
            app for app in appendices if app.content_type == "creature"
        )
        spell_appendix = next(app for app in appendices if app.content_type == "spell")

        # Verify creature appendix
        assert creature_appendix.title == "Appendix C: Creatures"
        assert creature_appendix.item_count == 1

        # Verify spell appendix includes creature-referenced spells
        assert spell_appendix.title == "Appendix A: Spells"
        assert spell_appendix.item_count == 2  # fireball and shield

        # Verify spell collector was called with the tracked spells
        appendix_generator.spell_collector.collect_by_names.assert_called_once()
        called_spell_names = (
            appendix_generator.spell_collector.collect_by_names.call_args[0][0]
        )
        assert "fireball" in called_spell_names
        assert "shield" in called_spell_names
