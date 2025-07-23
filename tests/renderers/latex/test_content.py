"""Tests for LaTeX content renderers."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.content import ContentType  # type: ignore
from dnd5e.core.models.creatures import Creature  # type: ignore
from dnd5e.core.models.items import Item  # type: ignore
from dnd5e.core.models.spells import Spell  # type: ignore
from dnd5e.renderers.base import RenderContext  # type: ignore
from dnd5e.renderers.latex.content import (  # type: ignore
    LaTeXClassRenderer,
    LaTeXContentRenderer,
    LaTeXContentRendererRegistry,
    LaTeXCreatureRenderer,
    LaTeXItemRenderer,
    LaTeXRaceRenderer,
    LaTeXSpellRenderer,
)


class TestLaTeXContentRenderer:
    """Test cases for base LaTeX content renderer."""

    def test_init(self) -> None:
        """Test renderer initialization."""
        renderer: Any = LaTeXSpellRenderer()  # Use concrete implementation
        assert renderer.output_format == "latex"
        assert renderer.template_engine is not None

    def test_init_with_config(self) -> None:
        """Test renderer initialization with config."""
        config = {"test_key": "test_value"}
        renderer: Any = LaTeXSpellRenderer(config)  # Use concrete implementation
        assert renderer.config == config

    def test_escape_latex_basic(self) -> None:
        """Test basic LaTeX escaping."""
        renderer: Any = LaTeXSpellRenderer()  # Use concrete implementation

        # Test basic characters
        assert renderer.escape_latex("Hello & World") == "Hello \\& World"
        assert renderer.escape_latex("50% off") == "50\\% off"
        assert renderer.escape_latex("Cost: $5") == "Cost: \\$5"
        assert renderer.escape_latex("Section #1") == "Section \\#1"
        assert renderer.escape_latex("file_name") == "file\\_name"
        assert renderer.escape_latex("{hello}") == "\\{hello\\}"
        assert renderer.escape_latex("x^2") == "x\\textasciicircum{}2"
        assert renderer.escape_latex("~home") == "\\textasciitilde{}home"
        assert (
            renderer.escape_latex("path\\to\\file")
            == "path\\textbackslash\\{\\}to\\textbackslash\\{\\}file"
        )

    def test_escape_latex_empty(self) -> None:
        """Test escaping empty or None text."""
        renderer: Any = LaTeXSpellRenderer()  # Use concrete implementation
        assert renderer.escape_latex("") == ""
        assert renderer.escape_latex(None) == ""

    def test_process_text_with_tags_no_resolver(self) -> None:
        """Test text processing without tag resolver."""
        renderer: Any = LaTeXSpellRenderer()  # Use concrete implementation
        context: Any = Mock(spec=RenderContext)
        context.tag_resolver = None

        result = renderer.process_text_with_tags("Hello & World", context)
        assert result == "Hello \\& World"

    def test_process_text_with_tags_with_resolver(self) -> None:
        """Test text processing with tag resolver."""
        renderer: Any = LaTeXSpellRenderer()  # Use concrete implementation
        context: Any = Mock(spec=RenderContext)
        context.tag_resolver = Mock()
        context.tag_resolver.process_text.return_value = "Processed text"

        result = renderer.process_text_with_tags("Text with tags", context)
        assert result == "Processed text"
        context.tag_resolver.process_text.assert_called_once_with("Text with tags")

    def test_process_text_with_tags_empty_text(self) -> None:
        """Test text processing with empty text."""
        renderer: Any = LaTeXSpellRenderer()  # Use concrete implementation
        context: Any = Mock(spec=RenderContext)
        context.tag_resolver = Mock()

        result = renderer.process_text_with_tags("", context)
        assert result == ""
        context.tag_resolver.process_text.assert_not_called()


class TestLaTeXSpellRenderer:
    """Test cases for LaTeX spell renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXSpellRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self) -> None:
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.SPELL}

    def test_render_content_invalid_type(self) -> None:
        """Test rendering with invalid content type."""
        invalid_content: Any = Mock()
        with pytest.raises(ValueError, match="Expected Spell, got"):
            self.renderer.render_content(invalid_content, self.context)

    def test_render_content_spell(self) -> None:
        """Test rendering spell content."""
        spell: Any = Mock(spec=Spell)
        spell.name = "Test Spell"
        spell.level = 1
        spell.get_level_text.return_value = "1st-level"
        spell.school = "Evocation"
        spell.casting_time = [{"number": 1, "unit": "action"}]
        spell.range = {"type": "point", "distance": {"type": "feet", "amount": 120}}
        spell.components = {"v": True, "s": True, "m": "a component"}
        spell.duration = [{"type": "instant"}]
        spell.get_casting_time_text.return_value = "1 action"
        spell.get_range_text.return_value = "120 feet"
        spell.get_components_text.return_value = "V, S, M"
        spell.get_duration_text.return_value = "Instantaneous"
        spell.entries = ["Test description"]
        spell.higher_level = None
        spell.source = "PHB"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered template"

            result = self.renderer.render_content(spell, self.context)

            assert result == "rendered template"
            # Check that render_template was called with the DND template
            assert mock_render.call_count == 1
            call_args = mock_render.call_args
            assert call_args[0][0] == "spell_dnd"  # Template name

            # Check some key variables are present
            variables = call_args[0][1]
            assert variables["name"] == "Test Spell"
            assert variables["level"] == 1
            assert variables["school"] == "Evocation"
            assert variables["source_reference"] == "PHB"

    def test_render_content_spell_with_higher_levels(self) -> None:
        """Test rendering spell with higher levels."""
        spell: Any = Mock(spec=Spell)
        spell.name = "Test Spell"
        spell.level = 1
        spell.get_level_text.return_value = "1st-level"
        spell.school = "Evocation"
        spell.casting_time = [{"number": 1, "unit": "action"}]
        spell.range = {"type": "point", "distance": {"type": "feet", "amount": 120}}
        spell.components = {"v": True, "s": True, "m": "a component"}
        spell.duration = [{"type": "instant"}]
        spell.get_casting_time_text.return_value = "1 action"
        spell.get_range_text.return_value = "120 feet"
        spell.get_components_text.return_value = "V, S, M"
        spell.get_duration_text.return_value = "Instantaneous"
        spell.entries = ["Test description"]
        spell.higher_level = ["Higher level text"]
        spell.source = "PHB"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered template"

            result = self.renderer.render_content(spell, self.context)

            assert result == "rendered template"
            # Check that higher_levels is properly processed
            variables = mock_render.call_args[0][1]
            assert "higher_levels" in variables

    def test_format_casting_time_empty(self) -> None:
        """Test formatting empty casting time."""
        result = self.renderer._format_casting_time([])
        assert result == "Unknown"

    def test_format_casting_time_single(self) -> None:
        """Test formatting single casting time."""
        time_data = [{"number": 1, "unit": "action"}]
        result = self.renderer._format_casting_time(time_data)
        assert result == "1 action"

    def test_format_casting_time_multiple(self) -> None:
        """Test formatting multiple casting times."""
        time_data = [{"number": 1, "unit": "action"}, {"number": 2, "unit": "minute"}]
        result = self.renderer._format_casting_time(time_data)
        assert result == "1 action, 2 minutes"

    def test_format_range_empty(self) -> None:
        """Test formatting empty range."""
        result = self.renderer._format_range({})
        assert result == "Unknown"

    def test_format_range_self(self) -> None:
        """Test formatting self range."""
        range_data = {"type": "point", "distance": {"type": "self"}}
        result = self.renderer._format_range(range_data)
        assert result == "Self"

    def test_format_range_touch(self) -> None:
        """Test formatting touch range."""
        range_data = {"type": "point", "distance": {"type": "touch"}}
        result = self.renderer._format_range(range_data)
        assert result == "Touch"

    def test_format_range_feet(self) -> None:
        """Test formatting feet range."""
        range_data = {"type": "point", "distance": {"type": "feet", "amount": 120}}
        result = self.renderer._format_range(range_data)
        assert result == "120 feet"

    def test_format_range_sphere(self) -> None:
        """Test formatting sphere range."""
        range_data = {"type": "sphere", "distance": {"amount": 20}}
        result = self.renderer._format_range(range_data)
        assert result == "Self (20-foot radius)"

    def test_format_range_cone(self) -> None:
        """Test formatting cone range."""
        range_data = {"type": "cone", "distance": {"amount": 15}}
        result = self.renderer._format_range(range_data)
        assert result == "Self (15-foot cone)"

    def test_format_range_line(self) -> None:
        """Test formatting line range."""
        range_data = {"type": "line", "distance": {"amount": 30}}
        result = self.renderer._format_range(range_data)
        assert result == "Self (30-foot line)"

    def test_format_range_unknown(self) -> None:
        """Test formatting unknown range type."""
        range_data = {"type": "unknown", "value": "special"}
        result = self.renderer._format_range(range_data)
        assert result == str(range_data)

    def test_format_components_empty(self) -> None:
        """Test formatting empty components."""
        result = self.renderer._format_components({})
        assert result == "None"

    def test_format_components_verbal(self) -> None:
        """Test formatting verbal components."""
        components = {"v": True}
        result = self.renderer._format_components(components)
        assert result == "V"

    def test_format_components_somatic(self) -> None:
        """Test formatting somatic components."""
        components = {"s": True}
        result = self.renderer._format_components(components)
        assert result == "S"

    def test_format_components_material_simple(self) -> None:
        """Test formatting simple material components."""
        components = {"m": True}
        result = self.renderer._format_components(components)
        assert result == "M"

    def test_format_components_material_with_text(self) -> None:
        """Test formatting material components with text."""
        components = {"m": "a pinch of sulfur"}
        result = self.renderer._format_components(components)
        assert result == "M (a pinch of sulfur)"

    def test_format_components_all(self) -> None:
        """Test formatting all components."""
        components = {"v": True, "s": True, "m": "a diamond worth 1000 gp"}
        result = self.renderer._format_components(components)
        assert result == "V, S, M (a diamond worth 1000 gp)"

    def test_format_duration_empty(self) -> None:
        """Test formatting empty duration."""
        result = self.renderer._format_duration([])
        assert result == "Unknown"

    def test_format_duration_instant(self) -> None:
        """Test formatting instant duration."""
        duration_data = [{"type": "instant"}]
        result = self.renderer._format_duration(duration_data)
        assert result == "Instantaneous"

    def test_format_duration_timed(self) -> None:
        """Test formatting timed duration."""
        duration_data = [{"type": "timed", "duration": {"amount": 1, "type": "hour"}}]
        result = self.renderer._format_duration(duration_data)
        assert result == "1 hour"

    def test_format_duration_timed_plural(self) -> None:
        """Test formatting timed duration with plural."""
        duration_data = [{"type": "timed", "duration": {"amount": 8, "type": "hour"}}]
        result = self.renderer._format_duration(duration_data)
        assert result == "8 hours"

    def test_format_duration_concentration(self) -> None:
        """Test formatting concentration duration."""
        duration_data = [
            {
                "type": "timed",
                "duration": {"amount": 1, "type": "minute"},
                "concentration": True,
            }
        ]
        result = self.renderer._format_duration(duration_data)
        assert result == "Concentration, up to 1 minute"

    def test_format_duration_unknown(self) -> None:
        """Test formatting unknown duration type."""
        duration_data = [{"type": "permanent"}]
        result = self.renderer._format_duration(duration_data)
        assert result == "Permanent"

    def test_format_entries_empty(self) -> None:
        """Test formatting empty entries."""
        result = self.renderer._format_entries([], self.context)
        assert result == ""

    def test_format_entries_strings(self) -> None:
        """Test formatting string entries."""
        entries = ["First entry", "Second entry"]
        result = self.renderer._format_entries(entries, self.context)  # type: ignore[arg-type]
        assert result == "First entry\n\nSecond entry"

    def test_format_entries_mixed(self) -> None:
        """Test formatting mixed entries."""
        entries = ["String entry", {"type": "list", "items": ["item1", "item2"]}]
        result = self.renderer._format_entries(entries, self.context)  # type: ignore[arg-type]
        assert "String entry" in result
        assert "{'type': 'list', 'items': ['item1', 'item2']}" in result

    def test_format_higher_levels_none(self) -> None:
        """Test formatting higher levels with None."""
        spell: Any = Mock(spec=Spell)
        spell.higher_level = None

        result = self.renderer._format_higher_levels(spell, self.context)
        assert result is None

    def test_format_higher_levels_empty(self) -> None:
        """Test formatting higher levels with empty list."""
        spell: Any = Mock(spec=Spell)
        spell.higher_level = []

        result = self.renderer._format_higher_levels(spell, self.context)
        assert result is None

    def test_format_higher_levels_strings(self) -> None:
        """Test formatting higher levels with strings."""
        spell: Any = Mock(spec=Spell)
        spell.higher_level = ["Text 1", "Text 2"]

        result = self.renderer._format_higher_levels(spell, self.context)
        assert result == "Text 1 Text 2"

    def test_format_higher_levels_dict(self) -> None:
        """Test formatting higher levels with dict entries."""
        spell: Any = Mock(spec=Spell)
        spell.higher_level = [{"entries": ["Entry 1", "Entry 2"]}]

        result = self.renderer._format_higher_levels(spell, self.context)
        assert result == "Entry 1 Entry 2"


class TestLaTeXCreatureRenderer:
    """Test cases for LaTeX creature renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXCreatureRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self) -> None:
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.CREATURE}

    def test_render_content_invalid_type(self) -> None:
        """Test rendering with invalid content type."""
        invalid_content: Any = Mock()
        with pytest.raises(ValueError, match="Expected Creature, got"):
            self.renderer.render_content(invalid_content, self.context)

    def test_render_content_creature(self) -> None:
        """Test rendering creature content."""
        creature: Any = Mock(spec=Creature)
        creature.name = "Test Creature"
        creature.size = ["M"]
        creature.type = "humanoid"
        creature.alignment = ["N"]
        creature.ac = [{"ac": 15}]
        creature.hp = {"average": 50, "formula": "10d8+10"}
        creature.speed = {"walk": 30}
        creature.strength = 16
        creature.dexterity = 14
        creature.constitution = 13
        creature.intelligence = 10
        creature.wisdom = 12
        creature.charisma = 8
        creature.cr = "2"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered template"

            result = self.renderer.render_content(creature, self.context)

            assert result == "rendered template"
            mock_render.assert_called_once()

    def test_format_size_empty(self) -> None:
        """Test formatting empty size."""
        result = self.renderer._format_size([])
        assert result == "Medium"

    def test_format_size_tiny(self) -> None:
        """Test formatting tiny size."""
        result = self.renderer._format_size(["T"])
        assert result == "Tiny"

    def test_format_size_small(self) -> None:
        """Test formatting small size."""
        result = self.renderer._format_size(["S"])
        assert result == "Small"

    def test_format_size_medium(self) -> None:
        """Test formatting medium size."""
        result = self.renderer._format_size(["M"])
        assert result == "Medium"

    def test_format_size_large(self) -> None:
        """Test formatting large size."""
        result = self.renderer._format_size(["L"])
        assert result == "Large"

    def test_format_size_huge(self) -> None:
        """Test formatting huge size."""
        result = self.renderer._format_size(["H"])
        assert result == "Huge"

    def test_format_size_gargantuan(self) -> None:
        """Test formatting gargantuan size."""
        result = self.renderer._format_size(["G"])
        assert result == "Gargantuan"

    def test_format_size_unknown(self) -> None:
        """Test formatting unknown size."""
        result = self.renderer._format_size(["X"])
        assert result == "X"

    def test_format_alignment_empty(self) -> None:
        """Test formatting empty alignment."""
        result = self.renderer._format_alignment([])
        assert result == "unaligned"

    def test_format_alignment_lawful_good(self) -> None:
        """Test formatting lawful good alignment."""
        result = self.renderer._format_alignment(["L", "G"])
        assert result == "lawful good"

    def test_format_alignment_chaotic_evil(self) -> None:
        """Test formatting chaotic evil alignment."""
        result = self.renderer._format_alignment(["C", "E"])
        assert result == "chaotic evil"

    def test_format_alignment_neutral(self) -> None:
        """Test formatting neutral alignment."""
        result = self.renderer._format_alignment(["N"])
        assert result == "neutral"

    def test_format_alignment_unknown(self) -> None:
        """Test formatting unknown alignment."""
        result = self.renderer._format_alignment(["UNKNOWN"])
        assert result == "unknown"

    def test_format_ac_empty(self) -> None:
        """Test formatting empty AC."""
        result = self.renderer._format_ac([])
        assert result == "10"

    def test_format_ac_pydantic(self) -> None:
        """Test formatting AC with Pydantic model."""
        ac_mock: Any = Mock()
        ac_mock.ac = 15
        ac_mock.__str__ = Mock(return_value="15 (Natural Armor)")

        result = self.renderer._format_ac([ac_mock])
        assert result == "15 (Natural Armor)"

    def test_format_ac_dict(self) -> None:
        """Test formatting AC with dict."""
        ac_data = [{"ac": 15, "from": ["Natural Armor"]}]
        result = self.renderer._format_ac(ac_data)
        assert result == "15 (Natural Armor)"

    def test_format_ac_dict_no_from(self) -> None:
        """Test formatting AC with dict without from."""
        ac_data = [{"ac": 15}]
        result = self.renderer._format_ac(ac_data)
        assert result == "15"

    def test_format_ac_simple(self) -> None:
        """Test formatting simple AC."""
        result = self.renderer._format_ac([15])
        assert result == "15"

    def test_format_hp_empty(self) -> None:
        """Test formatting empty HP."""
        result = self.renderer._format_hp(None)
        assert result == "1 (1d4)"

    def test_format_hp_pydantic(self) -> None:
        """Test formatting HP with Pydantic model."""
        hp_mock: Any = Mock()
        hp_mock.average = 50
        hp_mock.__str__ = Mock(return_value="50 (10d8+10)")

        result = self.renderer._format_hp(hp_mock)
        assert result == "50 (10d8+10)"

    def test_format_hp_dict(self) -> None:
        """Test formatting HP with dict."""
        hp_data = {"average": 50, "formula": "10d8+10"}
        result = self.renderer._format_hp(hp_data)
        assert result == "50 (10d8+10)"

    def test_format_hp_simple(self) -> None:
        """Test formatting simple HP."""
        result = self.renderer._format_hp(50)
        assert result == "50"

    def test_format_speed_empty(self) -> None:
        """Test formatting empty speed."""
        result = self.renderer._format_speed(None)
        assert result == "30 ft."

    def test_format_speed_pydantic(self) -> None:
        """Test formatting speed with Pydantic model."""
        speed_mock: Any = Mock()
        speed_mock.walk = 30
        speed_mock.__str__ = Mock(return_value="30 ft.")

        result = self.renderer._format_speed(speed_mock)
        assert result == "30 ft."

    def test_format_speed_dict_walk_only(self) -> None:
        """Test formatting speed with dict (walk only)."""
        speed_data = {"walk": 30}
        result = self.renderer._format_speed(speed_data)
        assert result == "30 ft."

    def test_format_speed_dict_multiple(self) -> None:
        """Test formatting speed with dict (multiple types)."""
        speed_data = {"walk": 30, "fly": 60, "swim": 20}
        result = self.renderer._format_speed(speed_data)
        assert "30 ft." in result
        assert "fly 60 ft." in result
        assert "swim 20 ft." in result

    def test_format_speed_simple(self) -> None:
        """Test formatting simple speed."""
        result = self.renderer._format_speed(30)
        assert result == "30"

    def test_format_ability_score_positive(self) -> None:
        """Test formatting positive ability score."""
        result = self.renderer._format_ability_score(16)
        assert result == "16 (+3)"

    def test_format_ability_score_zero(self) -> None:
        """Test formatting zero modifier ability score."""
        result = self.renderer._format_ability_score(10)
        assert result == "10 (+0)"

    def test_format_ability_score_negative(self) -> None:
        """Test formatting negative ability score."""
        result = self.renderer._format_ability_score(8)
        assert result == "8 (-1)"

    def test_format_cr(self) -> None:
        """Test formatting challenge rating."""
        result = self.renderer._format_cr("5")
        assert result == "5 (XP varies)"

    def test_format_skills_empty(self) -> None:
        """Test formatting empty skills."""
        result = self.renderer._format_skills(None)
        assert result is None

    def test_format_skills_string_values(self) -> None:
        """Test formatting skills with string values."""
        skills = {"perception": "+5", "stealth": "+3"}
        result = self.renderer._format_skills(skills)
        assert result == "Perception +5, Stealth +3"

    def test_format_skills_integer_values(self) -> None:
        """Test formatting skills with integer values."""
        skills = {"perception": 5, "stealth": -2}
        result = self.renderer._format_skills(skills)
        assert result == "Perception +5, Stealth -2"

    def test_format_damage_list_empty(self) -> None:
        """Test formatting empty damage list."""
        result = self.renderer._format_damage_list(None)
        assert result is None

    def test_format_damage_list_strings(self) -> None:
        """Test formatting damage list with strings."""
        damage_data = ["fire", "cold", "lightning"]
        result = self.renderer._format_damage_list(damage_data)
        assert result == "fire, cold, lightning"

    def test_format_damage_list_mixed(self) -> None:
        """Test formatting damage list with mixed types."""
        damage_data = ["fire", {"type": "cold", "note": "except from magic"}]
        result = self.renderer._format_damage_list(damage_data)
        assert result is not None
        assert "fire" in result
        assert "cold" in result

    def test_format_condition_list_empty(self) -> None:
        """Test formatting empty condition list."""
        result = self.renderer._format_condition_list(None)
        assert result is None

    def test_format_condition_list(self) -> None:
        """Test formatting condition list."""
        conditions = ["charmed", "frightened", "paralyzed"]
        result = self.renderer._format_condition_list(conditions)
        assert result == "charmed, frightened, paralyzed"

    def test_format_senses_empty(self) -> None:
        """Test formatting empty senses."""
        result = self.renderer._format_senses(None)
        assert result is None

    def test_format_senses(self) -> None:
        """Test formatting senses."""
        senses = ["darkvision 60 ft.", "passive Perception 12"]
        result = self.renderer._format_senses(senses)
        assert result == "darkvision 60 ft., passive Perception 12"

    def test_format_languages_empty(self) -> None:
        """Test formatting empty languages."""
        result = self.renderer._format_languages(None)
        assert result is None

    def test_format_languages(self) -> None:
        """Test formatting languages."""
        languages = ["Common", "Elvish", "Draconic"]
        result = self.renderer._format_languages(languages)
        assert result == "Common, Elvish, Draconic"

    def test_format_traits_empty(self) -> None:
        """Test formatting empty traits."""
        result = self.renderer._format_traits(None, self.context)
        assert result is None

    def test_format_traits(self) -> None:
        """Test formatting traits."""
        traits_data = [
            {
                "name": "Keen Sight",
                "entries": [
                    "The creature has advantage on sight-based perception checks."
                ],
            },
            {
                "name": "Magic Resistance",
                "entries": ["Advantage on saving throws against spells."],
            },
        ]
        result = self.renderer._format_traits(traits_data, self.context)

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "Keen Sight"
        assert "advantage on sight-based perception checks" in result[0]["description"]
        assert result[1]["name"] == "Magic Resistance"
        assert "Advantage on saving throws" in result[1]["description"]

    def test_format_actions_empty(self) -> None:
        """Test formatting empty actions."""
        result = self.renderer._format_actions(None, self.context)
        assert result is None

    def test_format_actions(self) -> None:
        """Test formatting actions."""
        actions_data = [
            {"name": "Multiattack", "entries": ["The creature makes two attacks."]},
            {
                "name": "Bite",
                "entries": [
                    "Melee weapon attack: +5 to hit, reach 5 ft., one target. Hit: 10 (2d6 + 3) piercing damage."
                ],
            },
        ]
        result = self.renderer._format_actions(actions_data, self.context)

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "Multiattack"
        assert "makes two attacks" in result[0]["description"]
        assert result[1]["name"] == "Bite"
        assert "Melee weapon attack" in result[1]["description"]


class TestLaTeXItemRenderer:
    """Test cases for LaTeX item renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXItemRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x
        self.context.get = Mock(return_value=True)

    def test_supported_content_types(self) -> None:
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.ITEM}

    def test_render_content_invalid_type(self) -> None:
        """Test rendering with invalid content type."""
        invalid_content: Any = Mock()
        with pytest.raises(ValueError, match="Expected Item, got"):
            self.renderer.render_content(invalid_content, self.context)

    def test_render_content_item(self) -> None:
        """Test rendering item content."""
        item: Any = Mock(spec=Item)
        item.name = "Test Item"
        item.type = "Weapon"
        item.rarity = "rare"
        item.entries = ["Test description"]
        item.properties = ["versatile"]
        item.requires_attunement = False
        item.weight = None
        item.value = None
        item.charges = None
        item.source = "DMG"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered template"

            result = self.renderer.render_content(item, self.context)

            assert result == "rendered template"
            mock_render.assert_called_once()

    def test_render_content_item_minimal(self) -> None:
        """Test rendering item with minimal data."""
        item: Any = Mock(spec=Item)
        item.name = "Simple Item"
        item.type = None
        item.rarity = None
        item.entries = None
        item.properties = None
        item.requires_attunement = None
        item.weight = None
        item.value = None
        item.charges = None
        item.source = None

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered template"

            result = self.renderer.render_content(item, self.context)

            assert result == "rendered template"
            variables = mock_render.call_args[0][1]
            assert variables["name"] == "Simple Item"
            # Just check that basic variables are present, don't check specific values
            assert "type_text" in variables
            assert "rarity_text" in variables
            assert "description" in variables

    def test_format_rarity_empty(self) -> None:
        """Test formatting empty rarity."""
        result = self.renderer._format_rarity(None)
        assert result == ""

    def test_format_rarity_common(self) -> None:
        """Test formatting common rarity."""
        result = self.renderer._format_rarity("common")
        assert result == ", common"

    def test_format_rarity_rare(self) -> None:
        """Test formatting rare rarity."""
        result = self.renderer._format_rarity("rare")
        assert result == ", rare"

    def test_format_entries_empty(self) -> None:
        """Test formatting empty entries."""
        result = self.renderer._format_entries([], self.context)
        assert result == ""

    def test_format_entries_strings(self) -> None:
        """Test formatting string entries."""
        entries = ["First paragraph", "Second paragraph"]
        result = self.renderer._format_entries(entries, self.context)  # type: ignore[arg-type]
        assert result == "First paragraph\n\nSecond paragraph"

    def test_format_entries_mixed(self) -> None:
        """Test formatting mixed entries."""
        entries = ["String entry", {"type": "table", "caption": "Test Table"}]
        result = self.renderer._format_entries(entries, self.context)  # type: ignore[arg-type]
        assert "String entry" in result
        assert "table" in result

    def test_format_properties_empty(self) -> None:
        """Test formatting empty properties."""
        result = self.renderer._format_properties(None)
        assert result is None

    def test_format_properties(self) -> None:
        """Test formatting properties."""
        properties = ["versatile", "light", "finesse"]
        result = self.renderer._format_properties(properties)
        assert result == "versatile, light, finesse"


class TestLaTeXContentRendererRegistry:
    """Test cases for LaTeX content renderer registry."""

    def test_init(self) -> None:
        """Test registry initialization."""
        registry: Any = LaTeXContentRendererRegistry()
        assert len(registry._renderers) == 9
        assert ContentType.SPELL in registry._renderers
        assert ContentType.CREATURE in registry._renderers
        assert ContentType.ITEM in registry._renderers
        assert ContentType.CLASS in registry._renderers
        assert ContentType.RACE in registry._renderers
        assert ContentType.ADVENTURE in registry._renderers
        assert ContentType.BACKGROUND in registry._renderers
        assert ContentType.FEAT in registry._renderers

    def test_register_renderer(self) -> None:
        """Test registering a renderer."""
        registry: Any = LaTeXContentRendererRegistry()
        mock_renderer: Any = Mock()

        registry.register_renderer(ContentType.SPELL, mock_renderer)

        assert registry._renderers[ContentType.SPELL] == mock_renderer

    def test_get_renderer_exists(self) -> None:
        """Test getting existing renderer."""
        registry: Any = LaTeXContentRendererRegistry()

        renderer = registry.get_renderer(ContentType.SPELL)

        assert renderer is not None
        assert isinstance(renderer, LaTeXSpellRenderer)

    def test_get_renderer_not_exists(self) -> None:
        """Test getting non-existing renderer."""
        registry: Any = LaTeXContentRendererRegistry()

        # Use a mock content type that doesn't exist
        fake_content_type: Any = Mock()
        renderer = registry.get_renderer(fake_content_type)

        assert renderer is None

    def test_register_default_renderers(self) -> None:
        """Test default renderer registration."""
        registry: Any = LaTeXContentRendererRegistry()

        # Test that default renderers are registered
        spell_renderer = registry.get_renderer(ContentType.SPELL)
        creature_renderer = registry.get_renderer(ContentType.CREATURE)
        item_renderer = registry.get_renderer(ContentType.ITEM)
        class_renderer = registry.get_renderer(ContentType.CLASS)
        race_renderer = registry.get_renderer(ContentType.RACE)

        assert isinstance(spell_renderer, LaTeXSpellRenderer)
        assert isinstance(creature_renderer, LaTeXCreatureRenderer)
        assert isinstance(item_renderer, LaTeXItemRenderer)
        assert isinstance(class_renderer, LaTeXClassRenderer)
        assert isinstance(race_renderer, LaTeXRaceRenderer)


if __name__ == "__main__":
    pytest.main([__file__])
