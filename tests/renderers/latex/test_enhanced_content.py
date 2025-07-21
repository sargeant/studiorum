"""Tests for enhanced LaTeX content renderers with DND template environments."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.adventures import Adventure  # type: ignore
from dnd5e.core.models.backgrounds import Background  # type: ignore
from dnd5e.core.models.classes import Class  # type: ignore
from dnd5e.core.models.content import ContentType  # type: ignore
from dnd5e.core.models.creatures import Creature  # type: ignore
from dnd5e.core.models.feats import Feat  # type: ignore
from dnd5e.core.models.items import Item  # type: ignore
from dnd5e.core.models.races import Race  # type: ignore
from dnd5e.core.models.spells import Spell  # type: ignore
from dnd5e.renderers.base import RenderContext  # type: ignore
from dnd5e.renderers.latex.content import (  # type: ignore
    LaTeXAdventureRenderer,
    LaTeXBackgroundRenderer,
    LaTeXClassRenderer,
    LaTeXContentRendererRegistry,
    LaTeXCreatureRenderer,
    LaTeXFeatRenderer,
    LaTeXItemRenderer,
    LaTeXRaceRenderer,
    LaTeXSpellRenderer,
)


class TestEnhancedLaTeXCreatureRenderer:
    """Test cases for enhanced LaTeX creature renderer using DND environments."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXCreatureRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_enhanced_creature_rendering_uses_dnd_template(self) -> None:
        """Test that enhanced creature renderer uses DND template format."""
        creature: Any = Mock(spec=Creature)
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
        creature.skill = {"perception": "+17", "stealth": "+7"}
        creature.damage_resist = ["fire", "cold"]
        creature.condition_immune = ["charmed", "frightened"]
        creature.senses = ["blindsight 60 ft.", "darkvision 120 ft."]
        creature.languages = ["Common", "Draconic"]
        creature.trait = [
            {
                "name": "Legendary Resistance",
                "entries": [
                    "If the dragon fails a saving throw, it can choose to succeed instead (3/Day)."
                ],
            }
        ]
        creature.action = [
            {
                "name": "Multiattack",
                "entries": [
                    "The dragon can use its Frightful Presence. It then makes three attacks."
                ],
            }
        ]
        creature.legendary = [
            {"name": "Tail Attack", "entries": ["The dragon makes a tail attack."]}
        ]

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\begin{DndMonster}[float*=b,width=\\textwidth + 8pt]{Ancient Red Dragon}"

            result = self.renderer.render_content(creature, self.context)

            assert result.startswith("\\begin{DndMonster}")
            mock_render.assert_called_once()
            # Verify that creature_dnd template is used
            assert mock_render.call_args[0][0] == "creature_dnd"

    def test_parse_ac_data_complex(self) -> None:
        """Test parsing complex AC data structures."""
        # Test with natural armor
        ac_data = [{"ac": 15, "from": ["natural armor"]}]
        result = self.renderer._parse_ac_data(ac_data)
        assert result["value"] == 15
        assert result["source"] == "natural armor"
        assert result["text"] == "15 (natural armor)"

        # Test with multiple sources
        ac_data = [{"ac": 18, "from": ["plate armor", "shield"]}]
        result = self.renderer._parse_ac_data(ac_data)
        assert result["value"] == 18
        assert "plate armor" in result["source"]
        assert "shield" in result["source"]

    def test_build_creature_variables_comprehensive(self) -> None:
        """Test building comprehensive creature template variables."""
        creature: Any = Mock(spec=Creature)
        creature.name = "Test Dragon"
        creature.size = ["L"]
        creature.type = "dragon"
        creature.alignment = ["L", "G"]
        creature.ac = [{"ac": 18}]
        creature.hp = {"average": 200, "formula": "16d12 + 80"}
        creature.speed = {"walk": 40, "fly": 80}
        creature.strength = 25
        creature.dexterity = 14
        creature.constitution = 21
        creature.intelligence = 16
        creature.wisdom = 13
        creature.charisma = 19
        creature.cr = "13"

        variables = self.renderer._build_creature_variables(creature, self.context)

        assert "name" in variables
        assert variables["name"] == "Test Dragon"
        assert "ac_value" in variables
        assert variables["ac_value"] == 18
        assert "hp_average" in variables
        assert variables["hp_average"] == 200

    def test_format_cr_enhanced_with_xp(self) -> None:
        """Test enhanced CR formatting with experience points."""
        # Test standard CRs - just verify it returns a string with CR and XP
        result = self.renderer._format_cr_enhanced("5")
        assert "5" in result
        assert "XP" in result

        result = self.renderer._format_cr_enhanced("10")
        assert "10" in result
        assert "XP" in result

        # Test fractional CRs
        result = self.renderer._format_cr_enhanced("1/8")
        assert "1/8" in result
        assert "XP" in result


class TestEnhancedLaTeXSpellRenderer:
    """Test cases for enhanced LaTeX spell renderer using DND environments."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXSpellRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_enhanced_spell_rendering_uses_dnd_template(self) -> None:
        """Test that enhanced spell renderer uses DND spell header format."""
        spell: Any = Mock(spec=Spell)
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
            "When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."
        ]
        spell.source = "PHB"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\DndSpellHeader{Fireball}{3rd-level evocation}"

            result = self.renderer.render_content(spell, self.context)

            assert "\\DndSpellHeader" in result
            mock_render.assert_called_once()
            # Verify that spell_dnd template is used
            assert mock_render.call_args[0][0] == "spell_dnd"

    def test_expand_school_abbreviation(self) -> None:
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

    def test_format_level_school_text(self) -> None:
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

    def test_format_casting_time_enhanced(self) -> None:
        """Test enhanced casting time formatting."""
        # Test standard action
        time_data = [{"number": 1, "unit": "action"}]
        result = self.renderer._format_casting_time_enhanced(time_data)
        assert result == "1 action"

        # Test longer casting time
        time_data = [{"number": 10, "unit": "minute"}]
        result = self.renderer._format_casting_time_enhanced(time_data)
        assert result == "10 minutes"

        # Test conditional casting time
        time_data = [{"number": 1, "unit": "action", "condition": "ritual"}]
        result = self.renderer._format_casting_time_enhanced(time_data)
        assert "ritual" in result

    def test_format_range_enhanced(self) -> None:
        """Test enhanced range formatting with special cases."""
        # Test self range
        range_data = {"type": "point", "distance": {"type": "self"}}
        result = self.renderer._format_range_enhanced(range_data)
        assert result == "Self"

        # Test sphere area
        range_data = {"type": "sphere", "distance": {"amount": 20}}
        result = self.renderer._format_range_enhanced(range_data)
        assert result == "Self (20-foot radius)"

        # Test cone area
        range_data = {"type": "cone", "distance": {"amount": 30}}
        result = self.renderer._format_range_enhanced(range_data)
        assert result == "Self (30-foot cone)"


class TestLaTeXItemRenderer:
    """Test cases for enhanced LaTeX item renderer with table formatting."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXItemRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_render_item_table_multiple_items(self) -> None:
        """Test rendering multiple items as a table."""
        items = [
            Mock(spec=Item),
            Mock(spec=Item),
            Mock(spec=Item),
        ]

        # Set attributes explicitly
        items[0].name = "Longsword"
        items[0].type = "M"
        items[0].rarity = "common"
        items[0].entries = ["A versatile weapon."]
        items[0].requires_attunement = False
        items[0].properties = ["versatile"]
        items[0].weight = None
        items[0].value = None
        items[0].charges = None
        items[0].source = "PHB"

        items[1].name = "Chain Mail"
        items[1].type = "HA"
        items[1].rarity = "common"
        items[1].entries = ["Heavy armor."]
        items[1].requires_attunement = False
        items[1].properties = None
        items[1].weight = None
        items[1].value = None
        items[1].charges = None
        items[1].source = "PHB"

        items[2].name = "Ring of Protection"
        items[2].type = "R"
        items[2].rarity = "rare"
        items[2].entries = ["Magic ring."]
        items[2].requires_attunement = True
        items[2].properties = None
        items[2].weight = None
        items[2].value = None
        items[2].charges = None
        items[2].source = "PHB"

        # Mock the item methods
        for item in items:
            item.is_weapon.return_value = item.name == "Longsword"
            item.is_armor.return_value = item.name == "Chain Mail"
            item.is_magic_item.return_value = item.name == "Ring of Protection"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\begin{DndTable}[header=Items]{X l l}"

            result = self.renderer.render_item_table(items, self.context)  # type: ignore[arg-type]

            assert "\\begin{DndTable}" in result
            mock_render.assert_called_once()
            # Verify that item_dnd template is used
            assert mock_render.call_args[0][0] == "item_dnd"

    def test_determine_table_columns_weapon_focus(self) -> None:
        """Test table column determination for weapon-focused tables."""
        items = [
            Mock(spec=Item, name="Longsword"),
            Mock(spec=Item, name="Greatsword"),
            Mock(spec=Item, name="Dagger"),
        ]

        for item in items:
            item.is_weapon.return_value = True
            item.is_armor.return_value = False

        columns = self.renderer._determine_table_columns(items)  # type: ignore[arg-type]

        # Should include weapon-specific columns
        assert "damage" in columns.get("headers", [])
        assert "properties" in columns.get("headers", [])

    def test_determine_table_columns_armor_focus(self) -> None:
        """Test table column determination for armor-focused tables."""
        items = [
            Mock(spec=Item, name="Leather Armor"),
            Mock(spec=Item, name="Chain Mail"),
            Mock(spec=Item, name="Plate Armor"),
        ]

        for item in items:
            item.is_weapon.return_value = False
            item.is_armor.return_value = True

        columns = self.renderer._determine_table_columns(items)  # type: ignore[arg-type]

        # Should include armor-specific columns
        assert "ac" in columns.get("headers", [])
        assert "stealth" in columns.get("headers", [])


class TestLaTeXClassRenderer:
    """Test cases for LaTeX class renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXClassRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x
        self.context.get = Mock(return_value=True)

    def test_supported_content_types(self) -> None:
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.CLASS}

    def test_render_content_class(self) -> None:
        """Test rendering class content."""
        class_data: Any = Mock(spec=Class)
        class_data.name = "Fighter"
        class_data.hit_die = "d10"
        class_data.proficiency = [
            "All armor",
            "shields",
            "simple weapons",
            "martial weapons",
        ]
        class_data.class_table = {
            "columns": ["Level", "Proficiency Bonus", "Features"],
            "rows": [
                ["1st", "+2", "Fighting Style, Second Wind"],
                ["2nd", "+2", "Action Surge (one use)"],
            ],
        }
        class_data.class_features = [
            {
                "name": "Fighting Style",
                "entries": [
                    "You adopt a particular style of fighting as your specialty."
                ],
            }
        ]
        class_data.subclass_title = "Martial Archetype"
        class_data.subclasses = [
            {
                "name": "Champion",
                "entries": [
                    "The archetypal Champion focuses on the development of raw physical power."
                ],
            }
        ]

        # Add attributes that _build_class_variables expects
        class_data.hd = None
        class_data.starting_proficiencies = None
        class_data.starting_equipment = None
        class_data.spellcasting_ability = None
        class_data.caster_progression = None
        class_data.cantrip_progression = None
        class_data.multiclassing = None
        class_data.source = None

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered class template"

            result = self.renderer.render_content(class_data, self.context)

            assert result == "rendered class template"
            mock_render.assert_called_once()
            # Verify that class_dnd template is used
            assert mock_render.call_args[0][0] == "class_dnd"

    def test_process_class_table_data(self) -> None:
        """Test processing class table data for rendering."""
        table_data = {
            "columns": [
                "Level",
                "Proficiency Bonus",
                "Features",
                "Spell Slots per Level",
            ],
            "column_labels": ["Level", "Prof. Bonus", "Features", "1st", "2nd", "3rd"],
            "rows": [
                ["1st", "+2", "Spellcasting, Ritual Casting", "2", "—", "—"],
                ["2nd", "+2", "—", "3", "—", "—"],
                ["3rd", "+2", "—", "4", "2", "—"],
            ],
        }

        result = self.renderer._process_class_table_data(table_data)

        assert result["headers"] == table_data["column_labels"]
        assert len(result["rows"]) == 3
        assert result["columns"] == "l c X c c c"  # LaTeX column specification

    def test_format_class_features(self) -> None:
        """Test formatting class features."""
        features = [
            {
                "name": "Spellcasting",
                "entries": [
                    "You have learned to untangle and reshape the fabric of reality.",
                    "See chapter 10 for the general rules of spellcasting.",
                ],
            },
            {
                "name": "Ritual Casting",
                "entries": [
                    "You can cast a spell as a ritual if that spell has the ritual tag."
                ],
            },
        ]

        result = self.renderer._format_class_features(features, self.context)

        assert len(result) == 2
        assert result[0]["name"] == "Spellcasting"
        assert "untangle and reshape" in result[0]["description"]
        assert result[1]["name"] == "Ritual Casting"
        assert "ritual tag" in result[1]["description"]


class TestLaTeXRaceRenderer:
    """Test cases for LaTeX race renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXRaceRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x
        self.context.get = Mock(return_value=True)

    def test_supported_content_types(self) -> None:
        """Test supported content types."""
        assert self.renderer.supported_content_types == {ContentType.RACE}

    def test_render_content_race(self) -> None:
        """Test rendering race content."""
        race_data: Any = Mock(spec=Race)
        race_data.name = "Elf"
        race_data.size = ["M"]
        race_data.speed = {"walk": 30}
        race_data.ability = [{"dex": 2}]
        race_data.trait_tags = ["Keen Senses", "Fey Ancestry", "Trance"]
        race_data.entries = [
            "Elves are a magical people of otherworldly grace, living in places of ethereal beauty."
        ]
        race_data.subraces = [
            {
                "name": "High Elf",
                "ability": [{"int": 1}],
                "entries": ["High elves are graceful warriors and wizards."],
            }
        ]

        # Add attributes that _build_race_variables expects
        race_data.darkvision = None
        race_data.additionalSpells = None
        race_data.language_proficiencies = None
        race_data.skill_proficiencies = None
        race_data.weapon_proficiencies = None
        race_data.armor_proficiencies = None
        race_data.tool_proficiencies = None
        race_data.resistances = None
        race_data.condition_immunities = None
        race_data.source = None

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "rendered race template"

            result = self.renderer.render_content(race_data, self.context)

            assert result == "rendered race template"
            mock_render.assert_called_once()
            # Verify that race_dnd template is used
            assert mock_render.call_args[0][0] == "race_dnd"

    def test_format_ability_score_increases(self) -> None:
        """Test formatting ability score increases."""
        abilities = [{"dex": 2, "int": 1}, {"str": 1}]

        result = self.renderer._format_ability_score_increases(abilities)

        assert "Dexterity +2" in result
        assert "Intelligence +1" in result
        assert "Strength +1" in result

    def test_format_racial_traits(self) -> None:
        """Test formatting racial traits."""
        trait_tags = ["Keen Senses", "Fey Ancestry", "Trance"]
        entries = [
            "You have proficiency with the Perception skill.",
            "You have advantage on saving throws against being charmed.",
            "Elves don't need to sleep. Instead, they meditate deeply.",
        ]

        result = self.renderer._format_racial_traits(trait_tags, entries, self.context)

        assert len(result) == 3
        assert result[0]["name"] == "Keen Senses"
        assert "Perception skill" in result[0]["description"]

    def test_format_subraces(self) -> None:
        """Test formatting subraces."""
        subraces = [
            {
                "name": "High Elf",
                "ability": [{"int": 1}],
                "entries": ["High elves are graceful warriors and wizards."],
            },
            {
                "name": "Wood Elf",
                "ability": [{"wis": 1}],
                "entries": ["Wood elves are fleet of foot and possess keen senses."],
            },
        ]

        result = self.renderer._format_subraces(subraces, self.context)

        assert len(result) == 2
        assert result[0]["name"] == "High Elf"
        assert "Intelligence +1" in result[0]["ability_increases"]
        assert result[1]["name"] == "Wood Elf"
        assert "Wisdom +1" in result[1]["ability_increases"]


class TestEnhancedContentRendererRegistry:
    """Test cases for enhanced content renderer registry with all renderer types."""

    def test_registry_includes_all_enhanced_renderers(self) -> None:
        """Test that registry includes all enhanced renderer types."""
        registry: Any = LaTeXContentRendererRegistry()

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

    def test_get_renderer_enhanced_types(self) -> None:
        """Test getting renderers for enhanced content types."""
        registry: Any = LaTeXContentRendererRegistry()

        class_renderer = registry.get_renderer(ContentType.CLASS)
        race_renderer = registry.get_renderer(ContentType.RACE)

        assert class_renderer is not None
        assert race_renderer is not None
        assert isinstance(class_renderer, LaTeXClassRenderer)
        assert isinstance(race_renderer, LaTeXRaceRenderer)


class TestLaTeXAdventureRenderer:
    """Test cases for LaTeX adventure renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXAdventureRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self) -> None:
        """Test that adventure renderer supports correct content types."""
        assert self.renderer.supported_content_types == {ContentType.ADVENTURE}

    def test_render_content_adventure(self) -> None:
        """Test rendering an adventure to LaTeX."""
        adventure: Any = Mock(spec=Adventure)
        adventure.name = "Lost Mine of Phandelver"
        adventure.entries = ["This is an adventure for 1st-level characters."]
        adventure.source = "LMoP"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = (
                "\\section{Lost Mine of Phandelver}\nContent here"
            )

            result = self.renderer.render_content(adventure, self.context)

            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            assert args[0] == "adventure_dnd.tex.j2"
            assert "name" in args[1]
            assert "Lost Mine of Phandelver" in args[1]["name"]
            assert result == "\\section{Lost Mine of Phandelver}\nContent here"

    def test_render_content_wrong_type(self) -> None:
        """Test that renderer raises error for wrong content type."""
        spell: Any = Mock(spec=Spell)
        with pytest.raises(ValueError, match="Expected Adventure"):
            self.renderer.render_content(spell, self.context)


class TestLaTeXBackgroundRenderer:
    """Test cases for LaTeX background renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXBackgroundRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self) -> None:
        """Test that background renderer supports correct content types."""
        assert self.renderer.supported_content_types == {ContentType.BACKGROUND}

    def test_render_content_background(self) -> None:
        """Test rendering a background to LaTeX."""
        background: Any = Mock(spec=Background)
        background.name = "Acolyte"
        background.entries = ["You have spent your life in the service of a temple."]
        background.skill_proficiencies = ["Insight", "Religion"]
        background.tool_proficiencies = None
        background.language_proficiencies = ["Two of your choice"]
        background.source = "PHB"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\subsubsection{Acolyte}\nContent here"

            result = self.renderer.render_content(background, self.context)

            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            assert args[0] == "background_dnd.tex.j2"
            assert "name" in args[1]
            assert "Acolyte" in args[1]["name"]
            assert result == "\\subsubsection{Acolyte}\nContent here"

    def test_format_proficiencies_simple_list(self) -> None:
        """Test formatting simple proficiency list."""
        proficiencies = ["Insight", "Religion"]
        result = self.renderer._format_proficiencies(proficiencies)
        assert result == "Insight, Religion"

    def test_format_proficiencies_empty(self) -> None:
        """Test formatting empty proficiency list."""
        result = self.renderer._format_proficiencies(None)
        assert result == ""

    def test_render_content_wrong_type(self) -> None:
        """Test that renderer raises error for wrong content type."""
        spell: Any = Mock(spec=Spell)
        with pytest.raises(ValueError, match="Expected Background"):
            self.renderer.render_content(spell, self.context)


class TestLaTeXFeatRenderer:
    """Test cases for LaTeX feat renderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = LaTeXFeatRenderer()
        self.context = Mock(spec=RenderContext)
        self.context.tag_resolver = Mock()
        self.context.tag_resolver.process_text.side_effect = lambda x: x

    def test_supported_content_types(self) -> None:
        """Test that feat renderer supports correct content types."""
        assert self.renderer.supported_content_types == {ContentType.FEAT}

    def test_render_content_feat(self) -> None:
        """Test rendering a feat to LaTeX."""
        feat: Any = Mock(spec=Feat)
        feat.name = "Alert"
        feat.entries = ["Always on the lookout for danger."]
        feat.prerequisite = None
        feat.ability = None
        feat.source = "PHB"

        with patch.object(
            self.renderer.template_engine, "render_template"
        ) as mock_render:
            mock_render.return_value = "\\paragraph{Alert}\nContent here"

            result = self.renderer.render_content(feat, self.context)

            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            assert args[0] == "feat_dnd.tex.j2"
            assert "name" in args[1]
            assert "Alert" in args[1]["name"]
            assert result == "\\paragraph{Alert}\nContent here"

    def test_format_prerequisites_empty(self) -> None:
        """Test formatting empty prerequisites."""
        result = self.renderer._format_prerequisites(None)
        assert result == ""

    def test_format_ability_improvements_empty(self) -> None:
        """Test formatting empty ability improvements."""
        result = self.renderer._format_ability_improvements(None)
        assert result == ""

    def test_render_content_wrong_type(self) -> None:
        """Test that renderer raises error for wrong content type."""
        spell: Any = Mock(spec=Spell)
        with pytest.raises(ValueError, match="Expected Feat"):
            self.renderer.render_content(spell, self.context)


class TestEnhancedContentRendererRegistryUpdated:
    """Test cases for enhanced content renderer registry with new renderers."""

    def test_registry_includes_all_enhanced_renderers_updated(self) -> None:
        """Test that registry includes all enhanced renderers including new ones."""
        registry: Any = LaTeXContentRendererRegistry()

        # Test that all content types have renderers
        assert ContentType.SPELL in registry._renderers
        assert ContentType.CREATURE in registry._renderers
        assert ContentType.ITEM in registry._renderers
        assert ContentType.CLASS in registry._renderers
        assert ContentType.RACE in registry._renderers
        assert ContentType.ADVENTURE in registry._renderers
        assert ContentType.BACKGROUND in registry._renderers
        assert ContentType.FEAT in registry._renderers

        # Test that renderers are of correct types
        assert isinstance(registry._renderers[ContentType.SPELL], LaTeXSpellRenderer)
        assert isinstance(
            registry._renderers[ContentType.CREATURE], LaTeXCreatureRenderer
        )
        assert isinstance(registry._renderers[ContentType.ITEM], LaTeXItemRenderer)
        assert isinstance(registry._renderers[ContentType.CLASS], LaTeXClassRenderer)
        assert isinstance(registry._renderers[ContentType.RACE], LaTeXRaceRenderer)
        assert isinstance(
            registry._renderers[ContentType.ADVENTURE], LaTeXAdventureRenderer
        )
        assert isinstance(
            registry._renderers[ContentType.BACKGROUND], LaTeXBackgroundRenderer
        )
        assert isinstance(registry._renderers[ContentType.FEAT], LaTeXFeatRenderer)

    def test_get_renderer_new_types(self) -> None:
        """Test getting renderers for new content types."""
        registry: Any = LaTeXContentRendererRegistry()

        adventure_renderer = registry.get_renderer(ContentType.ADVENTURE)
        background_renderer = registry.get_renderer(ContentType.BACKGROUND)
        feat_renderer = registry.get_renderer(ContentType.FEAT)

        assert adventure_renderer is not None
        assert background_renderer is not None
        assert feat_renderer is not None
        assert isinstance(adventure_renderer, LaTeXAdventureRenderer)
        assert isinstance(background_renderer, LaTeXBackgroundRenderer)
        assert isinstance(feat_renderer, LaTeXFeatRenderer)


if __name__ == "__main__":
    pytest.main([__file__])
