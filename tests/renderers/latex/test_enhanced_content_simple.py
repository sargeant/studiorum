"""Simplified tests for enhanced LaTeX content renderers with DND template environments."""

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.classes import Class
from dnd5e.core.models.content import ContentType
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.items import Item
from dnd5e.core.models.races import Race
from dnd5e.core.models.spells import Spell
from dnd5e.renderers.base import RenderContext
from dnd5e.renderers.latex.content import (
    LaTeXClassRenderer,
    LaTeXContentRendererRegistry,
    LaTeXCreatureRenderer,
    LaTeXItemRenderer,
    LaTeXRaceRenderer,
    LaTeXSpellRenderer,
)


class TestEnhancedLaTeXCreatureRenderer:
    """Test cases for enhanced LaTeX creature renderer using DND environments."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXCreatureRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self):
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.CREATURE}

    def test_enhanced_creature_rendering_uses_dnd_template(self):
        """Test that enhanced creature renderer uses DND template format."""
        creature = Mock(spec=Creature)
        creature.name = "Ancient Red Dragon"
        creature.size = ["G"]
        creature.type = "dragon"
        creature.alignment = ["C", "E"]
        creature.ac = [{"ac": 22, "from": ["natural armor"]}]
        creature.hp = {"average": 546, "formula": "28d20 + 252"}
        creature.speed = {"walk": 40, "climb": 40, "fly": 80}
        creature.strength = 30
        creature.dexterity = 10
        creature.constitution = 29
        creature.intelligence = 18
        creature.wisdom = 15
        creature.charisma = 23
        creature.cr = "24"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\begin{DndMonster}[float*=b,width=\\textwidth + 8pt]{Ancient Red Dragon}"

            result = self.renderer.render_content(creature, self.context)

            assert "\\begin{DndMonster}" in result
            mock_render.assert_called_once()
            # Verify that creature_dnd template is used by default
            assert mock_render.call_args[0][0] == "creature_dnd"

    def test_parse_ac_data_basic(self):
        """Test parsing AC data structures."""
        # Test with natural armor
        ac_data = [{"ac": 15, "from": ["natural armor"]}]
        result = self.renderer._parse_ac_data(ac_data)
        assert result["value"] == 15
        assert result["source"] == "natural armor"
        assert result["text"] == "15 (natural armor)"

        # Test with no source
        ac_data = [{"ac": 13}]
        result = self.renderer._parse_ac_data(ac_data)
        assert result["value"] == 13
        assert result["source"] is None
        assert result["text"] == "13"

    def test_format_cr_enhanced_basic(self):
        """Test enhanced CR formatting with experience points."""
        # Test that it returns a string with CR and XP
        result = self.renderer._format_cr_enhanced("5")
        assert "5" in result
        assert "XP" in result

        # Test fractional CR
        result = self.renderer._format_cr_enhanced("1/2")
        assert "1/2" in result
        assert "XP" in result

        # Test zero CR
        result = self.renderer._format_cr_enhanced("0")
        assert "0" in result
        assert "XP" in result


class TestEnhancedLaTeXSpellRenderer:
    """Test cases for enhanced LaTeX spell renderer using DND environments."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXSpellRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self):
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.SPELL}

    def test_enhanced_spell_rendering_uses_dnd_template(self):
        """Test that enhanced spell renderer uses DND spell header format."""
        spell = Mock(spec=Spell)
        spell.name = "Fireball"
        spell.level = 3
        spell.school = "V"
        spell.casting_time = [{"number": 1, "unit": "action"}]
        spell.range = {"type": "point", "distance": {"type": "feet", "amount": 150}}
        spell.components = {
            "v": True,
            "s": True,
            "m": "a tiny ball of bat guano and sulfur",
        }
        spell.duration = [{"type": "instant"}]
        spell.entries = ["A bright streak flashes from your pointing finger."]
        spell.higher_level = [
            "When you cast this spell using a spell slot of 4th level or higher."
        ]
        spell.source = {"abbreviation": "PHB", "name": "Player's Handbook", "page": 241}

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\DndSpellHeader{Fireball}{3rd-level evocation}"

            result = self.renderer.render_content(spell, self.context)

            assert "\\DndSpellHeader" in result
            mock_render.assert_called_once()
            # Verify that spell_dnd template is used by default
            assert mock_render.call_args[0][0] == "spell_dnd"

    def test_expand_school_abbreviation(self):
        """Test school abbreviation expansion."""
        assert self.renderer._expand_school_abbreviation("A") == "Abjuration"
        assert self.renderer._expand_school_abbreviation("C") == "Conjuration"
        assert self.renderer._expand_school_abbreviation("D") == "Divination"
        assert self.renderer._expand_school_abbreviation("E") == "Enchantment"
        assert self.renderer._expand_school_abbreviation("V") == "Evocation"
        assert self.renderer._expand_school_abbreviation("I") == "Illusion"
        assert self.renderer._expand_school_abbreviation("N") == "Necromancy"
        assert self.renderer._expand_school_abbreviation("T") == "Transmutation"
        assert self.renderer._expand_school_abbreviation("Unknown") == "Unknown"

    def test_format_level_school_text(self):
        """Test level and school text formatting."""
        # Test cantrip
        result = self.renderer._format_level_school(0, "V")
        assert result == "Evocation cantrip"

        # Test 1st level spell
        result = self.renderer._format_level_school(1, "A")
        assert result == "1st-level abjuration"

        # Test higher level spell
        result = self.renderer._format_level_school(5, "E")
        assert result == "5th-level enchantment"

    def test_format_casting_time_enhanced(self):
        """Test enhanced casting time formatting."""
        # Test standard action
        time_data = [{"number": 1, "unit": "action"}]
        result = self.renderer._format_casting_time_enhanced(time_data)
        assert "1 action" in result

        # Test longer casting time
        time_data = [{"number": 10, "unit": "minute"}]
        result = self.renderer._format_casting_time_enhanced(time_data)
        assert "10 minute" in result

    def test_format_range_enhanced(self):
        """Test enhanced range formatting with special cases."""
        # Test self range
        range_data = {"type": "point", "distance": {"type": "self"}}
        result = self.renderer._format_range_enhanced(range_data)
        assert result == "Self"

        # Test feet range
        range_data = {"type": "point", "distance": {"type": "feet", "amount": 120}}
        result = self.renderer._format_range_enhanced(range_data)
        assert "120" in result and "feet" in result


class TestLaTeXItemRenderer:
    """Test cases for enhanced LaTeX item renderer with table formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXItemRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self):
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.ITEM}

    def test_render_item_table_multiple_items(self):
        """Test rendering multiple items as a table."""
        items = [
            Mock(spec=Item, name="Longsword", type="M", rarity="common"),
            Mock(spec=Item, name="Chain Mail", type="HA", rarity="common"),
            Mock(spec=Item, name="Ring of Protection", type="R", rarity="rare"),
        ]

        # Mock the item methods that might be called
        for item in items:
            item.is_weapon = Mock(return_value=item.name == "Longsword")
            item.is_armor = Mock(return_value=item.name == "Chain Mail")
            if hasattr(item, "is_magic_item"):
                item.is_magic_item = Mock(
                    return_value=item.name == "Ring of Protection"
                )

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\begin{DndTable}[header=Items]{X l l}"

            result = self.renderer.render_item_table(items, self.context)

            assert "\\begin{DndTable}" in result
            mock_render.assert_called_once()
            # Verify that item_dnd template is used
            assert mock_render.call_args[0][0] == "item_dnd"

    def test_determine_table_columns_basic(self):
        """Test table column determination."""
        items = [Mock(spec=Item, name="Test Item")]

        # Mock required methods
        for item in items:
            item.is_weapon = Mock(return_value=False)
            item.is_armor = Mock(return_value=False)

        columns = self.renderer._determine_table_columns(items)

        # Should return some column specification
        assert isinstance(columns, str)
        assert len(columns) > 0


class TestLaTeXClassRenderer:
    """Test cases for LaTeX class renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXClassRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self):
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.CLASS}

    def test_render_content_class_basic(self):
        """Test basic class rendering."""
        class_data = Mock(spec=Class)
        class_data.name = "Fighter"

        # Make context more realistic by adding get method
        self.context.get = Mock(return_value=True)

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered class template"

            result = self.renderer.render_content(class_data, self.context)

            assert result == "rendered class template"
            mock_render.assert_called_once()
            # Verify that class_dnd template is used
            assert mock_render.call_args[0][0] == "class_dnd"


class TestLaTeXRaceRenderer:
    """Test cases for LaTeX race renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = LaTeXRaceRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self):
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.RACE}

    def test_render_content_race_basic(self):
        """Test basic race rendering."""
        race_data = Mock(spec=Race)
        race_data.name = "Elf"

        # Make context more realistic by adding get method
        self.context.get = Mock(return_value=True)

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered race template"

            result = self.renderer.render_content(race_data, self.context)

            assert result == "rendered race template"
            mock_render.assert_called_once()
            # Verify that race_dnd template is used
            assert mock_render.call_args[0][0] == "race_dnd"


class TestEnhancedContentRendererRegistry:
    """Test cases for enhanced content renderer registry with all renderer types."""

    def test_registry_includes_all_enhanced_renderers(self):
        """Test that registry includes all enhanced renderer types."""
        registry = LaTeXContentRendererRegistry()

        # Test that all content types have renderers
        assert ContentType.SPELL in registry._renderers
        assert ContentType.CREATURE in registry._renderers
        assert ContentType.ITEM in registry._renderers
        assert ContentType.CLASS in registry._renderers
        assert ContentType.RACE in registry._renderers

        # Test that renderers are of correct types
        assert isinstance(registry._renderers[ContentType.SPELL], LaTeXSpellRenderer)
        assert isinstance(
            registry._renderers[ContentType.CREATURE], LaTeXCreatureRenderer
        )
        assert isinstance(registry._renderers[ContentType.ITEM], LaTeXItemRenderer)
        assert isinstance(registry._renderers[ContentType.CLASS], LaTeXClassRenderer)
        assert isinstance(registry._renderers[ContentType.RACE], LaTeXRaceRenderer)

    def test_get_renderer_enhanced_types(self):
        """Test getting renderers for enhanced content types."""
        registry = LaTeXContentRendererRegistry()

        class_renderer = registry.get_renderer(ContentType.CLASS)
        race_renderer = registry.get_renderer(ContentType.RACE)

        assert class_renderer is not None
        assert race_renderer is not None
        assert isinstance(class_renderer, LaTeXClassRenderer)
        assert isinstance(race_renderer, LaTeXRaceRenderer)


if __name__ == "__main__":
    pytest.main([__file__])
