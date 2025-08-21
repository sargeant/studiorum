"""Tests for new EntryRenderer classes."""

from typing import Any
from unittest.mock import Mock

import pytest

from studiorum.core.models.creatures import Creature
from studiorum.core.models.items import Item
from studiorum.core.models.spells import Spell
from studiorum.renderers.core.interfaces import RenderingContext
from studiorum.renderers.latex.entry_renderers import (
    BaseEntryRenderer,
    CreatureEntryRenderer,
    ItemEntryRenderer,
    SpellEntryRenderer,
)


@pytest.fixture
def mock_context() -> Mock:
    """Create mock render context."""
    context = Mock(spec=RenderingContext)
    context.tag_resolver = Mock()
    context.tag_resolver.process_text.side_effect = lambda x: x
    return context


@pytest.mark.rendering
class TestBaseEntryRenderer:
    """Test base entry renderer functionality."""

    def test_cannot_instantiate_base_renderer(self) -> None:
        """Test that BaseEntryRenderer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEntryRenderer()

    def test_base_renderer_interface(self) -> None:
        """Test that concrete renderers implement required methods."""
        renderer = SpellEntryRenderer()

        # Check required methods exist
        assert hasattr(renderer, "render")
        assert hasattr(renderer, "get_template_name")
        assert hasattr(renderer, "get_template_context")
        assert callable(renderer.render)
        assert callable(renderer.get_template_name)
        assert callable(renderer.get_template_context)


@pytest.mark.rendering
class TestSpellEntryRenderer:
    """Test SpellEntryRenderer functionality."""

    @pytest.fixture
    def renderer(self) -> SpellEntryRenderer:
        """Create SpellEntryRenderer for testing."""
        return SpellEntryRenderer()

    @pytest.fixture
    def sample_spell_data(self) -> dict[str, Any]:
        """Sample spell data for testing."""
        return {
            "name": "Fireball",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 241},
            "level": 3,
            "school": "V",  # Evocation
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
            "components": {
                "v": True,
                "s": True,
                "m": {"text": "a tiny ball of bat guano and sulfur"},
            },
            "duration": [{"type": "instant"}],
            "entries": [
                "A bright streak flashes from your pointing finger to a point you choose.",
                "Each creature in a 20-foot-radius sphere centered on that point must make a Dexterity saving throw.",
            ],
            "entriesHigherLevel": [
                {
                    "type": "entries",
                    "name": "At Higher Levels",
                    "entries": [
                        "When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."
                    ],
                }
            ],
            "damageInflict": ["fire"],
            "savingThrow": ["dexterity"],
        }

    def test_get_template_name(self, renderer: SpellEntryRenderer) -> None:
        """Test template name selection."""
        assert renderer.get_template_name() == "spell_entry"

    def test_get_template_context_basic(
        self,
        renderer: SpellEntryRenderer,
        sample_spell_data: dict[str, Any],
        mock_context: Mock,
    ) -> None:
        """Test basic template context generation."""
        spell = Spell.model_validate(sample_spell_data)

        context = renderer.get_template_context(spell, mock_context)

        # Check that spell is passed through
        assert context["spell"] == spell

        # Check that model formatting methods are used
        assert context["level_text"] == spell.get_enhanced_level_text()
        assert context["components_text"] == spell.get_enhanced_components_text()
        assert context["duration_text"] == spell.get_enhanced_duration_text()

        # Check processed text entries
        assert "description_text" in context
        assert "higher_level_text" in context

    def test_get_template_context_with_tag_processing(
        self, renderer: SpellEntryRenderer, sample_spell_data: dict[str, Any]
    ) -> None:
        """Test template context generation.

        Note: Entry renderers do not perform tag processing - that happens
        at a different layer in the architecture.
        """
        mock_context = Mock(spec=RenderingContext)
        # Tag resolver is provided but not used by entry renderers
        mock_context.tag_resolver = Mock()
        mock_context.tag_resolver.process_text.return_value = "PROCESSED_TEXT"

        spell = Spell.model_validate(sample_spell_data)
        context = renderer.get_template_context(spell, mock_context)

        # Check that raw description text is returned (not processed)
        assert "description_text" in context
        assert context["description_text"] != "PROCESSED_TEXT"  # Should be raw text
        # Tag resolver should NOT be called by entry renderers
        mock_context.tag_resolver.process_text.assert_not_called()

    def test_get_template_context_without_tag_resolver(
        self, renderer: SpellEntryRenderer, sample_spell_data: dict[str, Any]
    ) -> None:
        """Test template context without tag resolver."""
        mock_context = Mock(spec=RenderingContext)
        mock_context.tag_resolver = None

        spell = Spell.model_validate(sample_spell_data)
        context = renderer.get_template_context(spell, mock_context)

        # Should still work without tag resolver
        assert "description_text" in context
        assert context["description_text"] != ""

    def test_render_integration(
        self,
        renderer: SpellEntryRenderer,
        sample_spell_data: dict[str, Any],
        mock_context: Mock,
    ) -> None:
        """Test full render integration."""
        # Mock the template engine on the instance
        mock_template_engine = Mock()
        mock_template_engine.render_template.return_value = "RENDERED_OUTPUT"
        renderer.template_engine = mock_template_engine

        spell = Spell.model_validate(sample_spell_data)
        result = renderer.render(spell, mock_context)

        assert result == "RENDERED_OUTPUT"
        mock_template_engine.render_template.assert_called_once()

        # Check that correct template and context were used
        call_args = mock_template_engine.render_template.call_args
        assert call_args[0][0] == "spell_entry"  # template name

        template_context = call_args[0][1]
        assert template_context["spell"] == spell

    def test_render_with_missing_optional_data(
        self, renderer: SpellEntryRenderer, mock_context: Mock
    ) -> None:
        """Test rendering spell with minimal data."""
        minimal_spell_data = {
            "name": "Test Spell",
            "source": {"abbreviation": "TEST", "name": "Test Source"},
            "level": 1,
            "school": "A",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "self"},
            "components": {"v": True},
            "duration": [{"type": "instant"}],
            "entries": ["Test description."],
        }

        spell = Spell.model_validate(minimal_spell_data)

        # Should not raise any errors
        context = renderer.get_template_context(spell, mock_context)
        assert context["spell"] == spell
        assert context["level_text"] != ""
        assert context["components_text"] != ""

    def test_error_handling(
        self, renderer: SpellEntryRenderer, mock_context: Mock
    ) -> None:
        """Test error handling in renderer."""
        # Test with invalid content type - use a mock object that doesn't have the right methods
        invalid_content = Mock()
        invalid_content.get_enhanced_level_text.side_effect = AttributeError(
            "not a spell"
        )

        with pytest.raises(AttributeError):
            renderer.get_template_context(invalid_content, mock_context)


@pytest.mark.rendering
class TestCreatureEntryRenderer:
    """Test CreatureEntryRenderer functionality."""

    @pytest.fixture
    def renderer(self) -> CreatureEntryRenderer:
        """Create CreatureEntryRenderer for testing."""
        return CreatureEntryRenderer()

    @pytest.fixture
    def sample_creature_data(self) -> dict[str, Any]:
        """Sample creature data for testing."""
        return {
            "name": "Adult Red Dragon",
            "source": {"abbreviation": "MM", "name": "Monster Manual", "page": 98},
            "size": ["H"],
            "type": {"type": "dragon"},
            "alignment": ["C", "E"],
            "ac": [{"ac": 19, "from": ["natural armor"]}],
            "hp": {"average": 256, "formula": "19d12 + 152"},
            "speed": {"walk": 40, "climb": 40, "fly": 80},
            "str": 27,
            "dex": 10,
            "con": 25,
            "int": 16,
            "wis": 13,
            "cha": 21,
            "save": {"dex": "+6", "con": "+13", "wis": "+7", "cha": "+11"},
            "skill": {"perception": "+13", "stealth": "+6"},
            "senses": ["blindsight 60 ft.", "darkvision 120 ft."],
            "passive": 23,
            "resist": ["fire"],
            "languages": ["Common", "Draconic"],
            "cr": "17",
            "trait": [
                {
                    "name": "Legendary Resistance",
                    "entries": [
                        "If the dragon fails a saving throw, it can choose to succeed instead (3/Day)."
                    ],
                }
            ],
            "action": [
                {
                    "name": "Multiattack",
                    "entries": [
                        "The dragon can use its Frightful Presence. It then makes three attacks: one with its bite and two with its claws."
                    ],
                }
            ],
        }

    def test_get_template_name(self, renderer: CreatureEntryRenderer) -> None:
        """Test creature template name."""
        assert renderer.get_template_name() == "creature_entry"

    def test_get_template_context(
        self,
        renderer: CreatureEntryRenderer,
        sample_creature_data: dict[str, Any],
        mock_context: Mock,
    ) -> None:
        """Test creature template context generation."""
        mock_context = Mock(spec=RenderingContext)
        mock_context.tag_resolver = None

        creature = Creature.model_validate(sample_creature_data)
        context = renderer.get_template_context(creature, mock_context)

        # Check basic context
        assert context["creature"] == creature

        # Check computed fields using model methods
        assert "size_type_alignment" in context
        assert "ability_scores" in context
        assert "formatted_abilities" in context


@pytest.mark.rendering
class TestItemEntryRenderer:
    """Test ItemEntryRenderer functionality."""

    @pytest.fixture
    def renderer(self) -> ItemEntryRenderer:
        """Create ItemEntryRenderer for testing."""
        return ItemEntryRenderer()

    @pytest.fixture
    def sample_item_data(self) -> dict[str, Any]:
        """Sample item data for testing."""
        return {
            "name": "Longsword",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook", "page": 149},
            "type": "M",
            "rarity": "none",
            "weight": 3,
            "value": 1500,  # 15 gp in cp
            "entries": ["A versatile martial weapon."],
            "weapon": True,
            "weaponCategory": "martial",
            "property": ["V"],
            "dmg1": "1d8",
            "dmgType": "S",
        }

    def test_get_template_name(self, renderer: ItemEntryRenderer) -> None:
        """Test item template name."""
        assert renderer.get_template_name() == "item_entry"

    def test_get_template_context(
        self, renderer: ItemEntryRenderer, sample_item_data: dict[str, Any]
    ) -> None:
        """Test item template context generation."""
        mock_context = Mock(spec=RenderingContext)
        mock_context.tag_resolver = None

        item = Item.model_validate(sample_item_data)
        context = renderer.get_template_context(item, mock_context)

        # Check basic context
        assert context["item"] == item

        # Check formatted fields
        assert "type_text" in context
        assert "rarity_text" in context
        assert "weight_text" in context
        assert "value_text" in context


@pytest.mark.rendering
class TestEntryRendererRegistry:
    """Test entry renderer registry functionality."""

    def test_renderer_registration(self) -> None:
        """Test that renderers are properly registered."""
        from studiorum.renderers.latex.entry_renderers import EntryRendererRegistry

        registry = EntryRendererRegistry()

        # Test spell renderer registration
        spell_renderer = registry.get_renderer("spell")
        assert isinstance(spell_renderer, SpellEntryRenderer)

        # Test creature renderer registration
        creature_renderer = registry.get_renderer("creature")
        assert isinstance(creature_renderer, CreatureEntryRenderer)

        # Test item renderer registration
        item_renderer = registry.get_renderer("item")
        assert isinstance(item_renderer, ItemEntryRenderer)

    def test_unknown_content_type(self) -> None:
        """Test handling of unknown content types."""
        from studiorum.renderers.latex.entry_renderers import EntryRendererRegistry

        registry = EntryRendererRegistry()

        with pytest.raises(ValueError, match="No renderer registered for content type"):
            registry.get_renderer("unknown_type")

    def test_custom_renderer_registration(self) -> None:
        """Test registration of custom renderers."""
        from studiorum.renderers.latex.entry_renderers import EntryRendererRegistry

        class CustomRenderer(BaseEntryRenderer):
            def get_template_name(self) -> str:
                return "custom.tex"

            def get_template_context(
                self, content: Any, context: RenderingContext
            ) -> dict[str, Any]:
                return {"content": content}

        registry = EntryRendererRegistry()
        custom_instance = CustomRenderer()
        registry.register_renderer("custom", custom_instance)

        custom_renderer = registry.get_renderer("custom")
        assert isinstance(custom_renderer, CustomRenderer)
        assert custom_renderer is custom_instance


@pytest.mark.rendering
class TestRendererPerformance:
    """Test renderer performance and resource usage."""

    def test_renderer_reuse(self) -> None:
        """Test that renderers can be reused efficiently."""
        from studiorum.renderers.latex.entry_renderers import EntryRendererRegistry

        registry = EntryRendererRegistry()

        # Get same renderer multiple times
        renderer1 = registry.get_renderer("spell")
        renderer2 = registry.get_renderer("spell")

        # Should return same instance for efficiency
        assert renderer1 is renderer2

    def test_memory_usage_with_large_content(self) -> None:
        """Test memory usage with large content objects."""
        renderer = SpellEntryRenderer()
        mock_context = Mock(spec=RenderingContext)
        mock_context.tag_resolver = None

        # Create spell with large description
        large_description = ["This is a very long description. " * 1000]
        large_spell_data = {
            "name": "Large Spell",
            "source": {"abbreviation": "TEST", "name": "Test Source"},
            "level": 9,
            "school": "V",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "unlimited"},
            "components": {"v": True, "s": True},
            "duration": [{"type": "permanent"}],
            "entries": large_description,
        }

        spell = Spell.model_validate(large_spell_data)

        # Should handle large content without issues
        context = renderer.get_template_context(spell, mock_context)
        assert context["spell"] == spell
        assert len(context["description_text"]) > 1000
