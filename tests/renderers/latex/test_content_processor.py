"""Tests for LaTeX content processors."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.items import Item
from dnd5e.core.models.spells import Spell
from dnd5e.renderers.base import RenderContext
from dnd5e.renderers.latex.content_processor import (
    ContentProcessor,
    ContentProcessorRegistry,
    CreatureProcessor,
    ItemProcessor,
    SpellProcessor,
)


class TestSpellProcessor:
    """Test cases for spell content processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = SpellProcessor()
        self.context = Mock(spec=RenderContext)

    def test_supports_content_type(self):
        """Test content type support."""
        assert self.processor.supports_content_type(ContentType.SPELL)
        assert not self.processor.supports_content_type(ContentType.CREATURE)
        assert not self.processor.supports_content_type(ContentType.ITEM)

    def test_process_invalid_content_type(self):
        """Test processing with invalid content type."""
        invalid_content = Mock(spec=Creature)

        with pytest.raises(ValueError, match="Expected Spell, got"):
            self.processor.process(invalid_content, self.context)

    def test_process_basic_spell(self):
        """Test processing basic spell data."""
        spell = Mock(spec=Spell)
        spell.level = 3
        spell.entries = ["A bright streak flashes from your pointing finger."]
        spell.higher_level = [
            "When you cast this spell using a spell slot of 4th level or higher."
        ]
        spell.components = Mock()
        spell.components.verbal = True
        spell.components.somatic = True
        spell.components.material = "a tiny ball of bat guano and sulfur"
        spell.duration = [Mock()]
        spell.duration[0].concentration = True
        spell.classes = {"fromClassList": [{"name": "Sorcerer"}, {"name": "Wizard"}]}

        # Mock damage and saving throw attributes
        spell.damage_inflict = ["fire"]
        spell.saving_throw = ["dexterity"]
        spell.spell_attack = None

        result = self.processor.process(spell, self.context)

        assert result["spell_level_ordinal"] == "3rd"
        assert result["is_cantrip"] is False
        assert result["is_ritual"] is False
        assert result["verbal_component"] is True
        assert result["somatic_component"] is True
        assert result["material_component"] == "a tiny ball of bat guano and sulfur"
        assert result["concentration_required"] is True
        assert result["class_availability"] == ["Sorcerer", "Wizard"]
        assert "fire" in result["spell_tags"]
        assert "save" in result["spell_tags"]

    def test_get_spell_level_ordinal(self):
        """Test spell level ordinal conversion."""
        assert self.processor._get_spell_level_ordinal(0) == "Cantrip"
        assert self.processor._get_spell_level_ordinal(1) == "1st"
        assert self.processor._get_spell_level_ordinal(2) == "2nd"
        assert self.processor._get_spell_level_ordinal(3) == "3rd"
        assert self.processor._get_spell_level_ordinal(4) == "4th"
        assert self.processor._get_spell_level_ordinal(9) == "9th"
        assert self.processor._get_spell_level_ordinal(10) == "10th"

    def test_extract_damage_dice(self):
        """Test damage dice extraction from spell entries."""
        spell = Mock(spec=Spell)
        spell.entries = [
            "The target takes 3d6 fire damage.",
            "Additional text without dice.",
            "Another spell effect with 2d8+4 damage.",
        ]

        result = self.processor._extract_damage_dice(spell)
        assert result == "3d6"

    def test_extract_damage_dice_no_entries(self):
        """Test damage dice extraction with no entries."""
        spell = Mock(spec=Spell)
        spell.entries = []

        result = self.processor._extract_damage_dice(spell)
        assert result is None

    def test_extract_spell_tags(self):
        """Test spell tag extraction."""
        spell = Mock(spec=Spell)
        spell.damage_inflict = ["fire", "cold"]
        spell.saving_throw = ["dexterity"]
        spell.spell_attack = ["ranged"]

        result = self.processor._extract_spell_tags(spell)

        assert "fire" in result
        assert "cold" in result
        assert "save" in result
        assert "attack" in result

    def test_has_verbal_component_object(self):
        """Test verbal component detection with component object."""
        spell = Mock(spec=Spell)
        spell.components = Mock()
        spell.components.verbal = True

        result = self.processor._has_verbal_component(spell)
        assert result is True

    def test_has_verbal_component_dict(self):
        """Test verbal component detection with component dict."""
        spell = Mock(spec=Spell)
        spell.components = {"v": True, "s": False}

        result = self.processor._has_verbal_component(spell)
        assert result is True

    def test_extract_material_component_object(self):
        """Test material component extraction with component object."""
        spell = Mock(spec=Spell)
        spell.components = Mock()
        spell.components.material = "a pinch of sulfur"

        result = self.processor._extract_material_component(spell)
        assert result == "a pinch of sulfur"

    def test_extract_material_component_dict(self):
        """Test material component extraction with component dict."""
        spell = Mock(spec=Spell)
        spell.components = {"m": "a diamond worth 1000 gp"}

        result = self.processor._extract_material_component(spell)
        assert result == "a diamond worth 1000 gp"

    def test_requires_concentration_true(self):
        """Test concentration requirement detection (true case)."""
        spell = Mock(spec=Spell)
        spell.duration = [Mock()]
        spell.duration[0].concentration = True

        result = self.processor._requires_concentration(spell)
        assert result is True

    def test_requires_concentration_dict(self):
        """Test concentration requirement detection with dict."""
        spell = Mock(spec=Spell)
        spell.duration = [{"concentration": True, "type": "timed"}]

        result = self.processor._requires_concentration(spell)
        assert result is True

    def test_extract_upcast_effects(self):
        """Test upcast effects extraction."""
        spell = Mock(spec=Spell)
        spell.higher_level = [
            "When you cast this spell using a spell slot of 4th level or higher,",
            "the damage increases by 1d6 for each slot level above 3rd.",
        ]

        result = self.processor._extract_upcast_effects(spell)
        assert "4th level or higher" in result
        assert "1d6 for each slot level" in result

    def test_get_class_availability(self):
        """Test class availability extraction."""
        spell = Mock(spec=Spell)
        spell.classes = {
            "fromClassList": [
                {"name": "Bard"},
                {"name": "Sorcerer"},
                {"name": "Warlock"},
                {"name": "Wizard"},
            ]
        }

        result = self.processor._get_class_availability(spell)
        assert "Bard" in result
        assert "Sorcerer" in result
        assert "Warlock" in result
        assert "Wizard" in result


class TestCreatureProcessor:
    """Test cases for creature content processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = CreatureProcessor()
        self.context = Mock(spec=RenderContext)

    def test_supports_content_type(self):
        """Test content type support."""
        assert self.processor.supports_content_type(ContentType.CREATURE)
        assert not self.processor.supports_content_type(ContentType.SPELL)
        assert not self.processor.supports_content_type(ContentType.ITEM)

    def test_process_invalid_content_type(self):
        """Test processing with invalid content type."""
        invalid_content = Mock(spec=Spell)

        with pytest.raises(ValueError, match="Expected Creature, got"):
            self.processor.process(invalid_content, self.context)

    def test_process_basic_creature(self):
        """Test processing basic creature data."""
        creature = Mock(spec=Creature)
        creature.cr = "5"
        creature.size = ["L"]
        creature.strength = 18
        creature.dexterity = 14
        creature.constitution = 16
        creature.intelligence = 10
        creature.wisdom = 12
        creature.charisma = 8
        creature.skill = {"perception": "+3"}
        creature.trait = [
            {"name": "Spellcasting", "entries": ["The creature is a spellcaster."]}
        ]
        creature.legendary = [
            {"name": "Tail Attack", "entries": ["The creature makes a tail attack."]}
        ]
        creature.type = "dragon"

        result = self.processor.process(creature, self.context)

        assert result["cr_numeric"] == 5.0
        assert result["cr_category"] == "High"
        assert result["size_category"] == "Large"
        assert result["proficiency_bonus"] == 3
        assert result["is_spellcaster"] is True
        assert result["legendary_creature"] is True
        assert "large" in result["creature_tags"]
        assert "dragon" in result["creature_tags"]

    def test_get_numeric_cr_fractions(self):
        """Test numeric CR conversion for fractions."""
        assert self.processor._get_numeric_cr("1/8") == 0.125
        assert self.processor._get_numeric_cr("1/4") == 0.25
        assert self.processor._get_numeric_cr("1/2") == 0.5

    def test_get_numeric_cr_integers(self):
        """Test numeric CR conversion for integers."""
        assert self.processor._get_numeric_cr("1") == 1.0
        assert self.processor._get_numeric_cr("5") == 5.0
        assert self.processor._get_numeric_cr("20") == 20.0

    def test_get_numeric_cr_invalid(self):
        """Test numeric CR conversion for invalid values."""
        assert self.processor._get_numeric_cr("invalid") == 0.0
        assert self.processor._get_numeric_cr(None) == 0.0

    def test_get_cr_category(self):
        """Test CR category assignment."""
        assert self.processor._get_cr_category("0") == "Trivial"
        assert self.processor._get_cr_category("1/4") == "Low"
        assert self.processor._get_cr_category("2") == "Medium"
        assert self.processor._get_cr_category("8") == "High"
        assert self.processor._get_cr_category("15") == "Epic"
        assert self.processor._get_cr_category("25") == "Legendary"

    def test_get_size_category(self):
        """Test size category conversion."""
        assert self.processor._get_size_category(["T"]) == "Tiny"
        assert self.processor._get_size_category(["S"]) == "Small"
        assert self.processor._get_size_category(["M"]) == "Medium"
        assert self.processor._get_size_category(["L"]) == "Large"
        assert self.processor._get_size_category(["H"]) == "Huge"
        assert self.processor._get_size_category(["G"]) == "Gargantuan"
        assert self.processor._get_size_category([]) == "Medium"

    def test_calculate_proficiency_bonus(self):
        """Test proficiency bonus calculation."""
        assert self.processor._calculate_proficiency_bonus("1") == 2
        assert self.processor._calculate_proficiency_bonus("4") == 2
        assert self.processor._calculate_proficiency_bonus("5") == 3
        assert self.processor._calculate_proficiency_bonus("8") == 3
        assert self.processor._calculate_proficiency_bonus("9") == 4
        assert self.processor._calculate_proficiency_bonus("20") == 6
        assert self.processor._calculate_proficiency_bonus("30") == 9

    def test_calculate_ability_modifiers(self):
        """Test ability modifier calculation."""
        creature = Mock(spec=Creature)
        creature.strength = 18
        creature.dexterity = 14
        creature.constitution = 16
        creature.intelligence = 8
        creature.wisdom = 12
        creature.charisma = 10

        result = self.processor._calculate_ability_modifiers(creature)

        assert result["str"] == 4  # (18-10)//2
        assert result["dex"] == 2  # (14-10)//2
        assert result["con"] == 3  # (16-10)//2
        assert result["int"] == -1  # (8-10)//2
        assert result["wis"] == 1  # (12-10)//2
        assert result["cha"] == 0  # (10-10)//2

    def test_calculate_passive_perception_with_proficiency(self):
        """Test passive perception calculation with perception proficiency."""
        creature = Mock(spec=Creature)
        creature.wisdom = 14  # +2 modifier
        creature.cr = "5"  # +3 proficiency bonus
        creature.skill = {"perception": "+5"}

        result = self.processor._calculate_passive_perception(creature)
        assert result == 15  # 10 + 2 (wis) + 3 (prof)

    def test_calculate_passive_perception_without_proficiency(self):
        """Test passive perception calculation without perception proficiency."""
        creature = Mock(spec=Creature)
        creature.wisdom = 14  # +2 modifier
        creature.cr = "5"  # +3 proficiency bonus
        creature.skill = {}  # No perception skill

        result = self.processor._calculate_passive_perception(creature)
        assert result == 12  # 10 + 2 (wis), no proficiency

    def test_is_spellcaster_true(self):
        """Test spellcaster detection (true case)."""
        creature = Mock(spec=Creature)
        creature.trait = [
            {
                "name": "Spellcasting",
                "entries": ["The creature is a 9th-level spellcaster."],
            }
        ]

        result = self.processor._is_spellcaster(creature)
        assert result is True

    def test_is_spellcaster_false(self):
        """Test spellcaster detection (false case)."""
        creature = Mock(spec=Creature)
        creature.trait = [
            {
                "name": "Keen Senses",
                "entries": ["The creature has advantage on perception checks."],
            }
        ]

        result = self.processor._is_spellcaster(creature)
        assert result is False

    def test_is_legendary_true(self):
        """Test legendary creature detection (true case)."""
        creature = Mock(spec=Creature)
        creature.legendary = [
            {"name": "Tail Attack", "entries": ["The creature makes a tail attack."]}
        ]

        result = self.processor._is_legendary(creature)
        assert result is True

    def test_is_legendary_false(self):
        """Test legendary creature detection (false case)."""
        creature = Mock(spec=Creature)
        creature.legendary = []

        result = self.processor._is_legendary(creature)
        assert result is False

    def test_extract_creature_tags(self):
        """Test creature tag extraction."""
        creature = Mock(spec=Creature)
        creature.size = ["L"]
        creature.type = "dragon"
        creature.cr = "8"
        creature.trait = [
            {"name": "Spellcasting", "entries": ["The creature is a spellcaster."]}
        ]
        creature.legendary = [
            {"name": "Tail Attack", "entries": ["The creature makes a tail attack."]}
        ]

        result = self.processor._extract_creature_tags(creature)

        assert "large" in result
        assert "dragon" in result
        assert "high" in result  # CR category
        assert "spellcaster" in result
        assert "legendary" in result


class TestItemProcessor:
    """Test cases for item content processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ItemProcessor()
        self.context = Mock(spec=RenderContext)

    def test_supports_content_type(self):
        """Test content type support."""
        assert self.processor.supports_content_type(ContentType.ITEM)
        assert not self.processor.supports_content_type(ContentType.SPELL)
        assert not self.processor.supports_content_type(ContentType.CREATURE)

    def test_process_invalid_content_type(self):
        """Test processing with invalid content type."""
        invalid_content = Mock(spec=Spell)

        with pytest.raises(ValueError, match="Expected Item, got"):
            self.processor.process(invalid_content, self.context)

    def test_process_basic_item(self):
        """Test processing basic item data."""
        item = Mock(spec=Item)
        item.is_weapon.return_value = True
        item.is_armor.return_value = False
        item.is_magic_item.return_value = False
        item.rarity = "uncommon"
        item.requires_attunement = True
        item.properties = ["versatile", "finesse"]
        item.value = 1500  # 15 gp in copper pieces

        result = self.processor.process(item, self.context)

        assert result["item_category"] == "Weapon"
        assert result["rarity_tier"] == "Uncommon"
        assert result["is_magic_item"] is False
        assert result["requires_attunement"] is True
        assert result["item_properties"] == ["versatile", "finesse"]
        assert result["value_tier"] == "Moderate"

    def test_get_item_category_weapon(self):
        """Test item category determination for weapons."""
        item = Mock(spec=Item)
        item.is_weapon.return_value = True
        item.is_armor.return_value = False

        result = self.processor._get_item_category(item)
        assert result == "Weapon"

    def test_get_item_category_armor(self):
        """Test item category determination for armor."""
        item = Mock(spec=Item)
        item.is_weapon.return_value = False
        item.is_armor.return_value = True

        result = self.processor._get_item_category(item)
        assert result == "Armor"

    def test_get_item_category_magic_item(self):
        """Test item category determination for magic items."""
        item = Mock(spec=Item)
        item.is_weapon.return_value = False
        item.is_armor.return_value = False
        item.is_magic_item.return_value = True

        result = self.processor._get_item_category(item)
        assert result == "Magic Item"

    def test_get_rarity_tier(self):
        """Test rarity tier determination."""
        item = Mock(spec=Item)

        item.rarity = "common"
        assert self.processor._get_rarity_tier(item) == "Common"

        item.rarity = "uncommon"
        assert self.processor._get_rarity_tier(item) == "Uncommon"

        item.rarity = "rare"
        assert self.processor._get_rarity_tier(item) == "Rare"

        item.rarity = "very rare"
        assert self.processor._get_rarity_tier(item) == "Very Rare"

        item.rarity = "legendary"
        assert self.processor._get_rarity_tier(item) == "Legendary"

    def test_requires_attunement_boolean(self):
        """Test attunement requirement with boolean value."""
        item = Mock(spec=Item)
        item.requires_attunement = True

        result = self.processor._requires_attunement(item)
        assert result is True

    def test_requires_attunement_string(self):
        """Test attunement requirement with string value."""
        item = Mock(spec=Item)
        item.requires_attunement = "by a spellcaster"

        result = self.processor._requires_attunement(item)
        assert result is True

    def test_get_damage_output_weapon(self):
        """Test damage output extraction for weapons."""
        item = Mock(spec=Item)
        item.is_weapon.return_value = True
        item.damage = "1d8"

        result = self.processor._get_damage_output(item)
        assert result == "1d8"

    def test_get_damage_output_non_weapon(self):
        """Test damage output extraction for non-weapons."""
        item = Mock(spec=Item)
        item.is_weapon.return_value = False

        result = self.processor._get_damage_output(item)
        assert result is None

    def test_get_armor_rating_armor(self):
        """Test armor rating extraction for armor."""
        item = Mock(spec=Item)
        item.is_armor.return_value = True
        item.ac = 16

        result = self.processor._get_armor_rating(item)
        assert result == 16

    def test_get_armor_rating_non_armor(self):
        """Test armor rating extraction for non-armor."""
        item = Mock(spec=Item)
        item.is_armor.return_value = False

        result = self.processor._get_armor_rating(item)
        assert result is None

    def test_get_value_tier(self):
        """Test value tier determination."""
        item = Mock(spec=Item)

        item.value = 50  # Less than 1 gp
        assert self.processor._get_value_tier(item) == "Cheap"

        item.value = 500  # 5 gp
        assert self.processor._get_value_tier(item) == "Affordable"

        item.value = 5000  # 50 gp
        assert self.processor._get_value_tier(item) == "Moderate"

        item.value = 50000  # 500 gp
        assert self.processor._get_value_tier(item) == "Costly"

        item.value = 500000  # 5000 gp
        assert self.processor._get_value_tier(item) == "Expensive"


class TestContentProcessorRegistry:
    """Test cases for content processor registry."""

    def test_init_registers_default_processors(self):
        """Test that initialization registers default processors."""
        registry = ContentProcessorRegistry()

        assert ContentType.SPELL in registry._processors
        assert ContentType.CREATURE in registry._processors
        assert ContentType.ITEM in registry._processors

        assert isinstance(registry._processors[ContentType.SPELL], SpellProcessor)
        assert isinstance(registry._processors[ContentType.CREATURE], CreatureProcessor)
        assert isinstance(registry._processors[ContentType.ITEM], ItemProcessor)

    def test_register_processor(self):
        """Test processor registration."""
        registry = ContentProcessorRegistry()
        custom_processor = Mock(spec=ContentProcessor)
        custom_processor.supports_content_type.return_value = True

        registry.register_processor(custom_processor)

        # Should register for all content types it supports
        for content_type in ContentType:
            if custom_processor.supports_content_type(content_type):
                assert registry._processors[content_type] == custom_processor

    def test_get_processor_exists(self):
        """Test getting existing processor."""
        registry = ContentProcessorRegistry()

        processor = registry.get_processor(ContentType.SPELL)
        assert processor is not None
        assert isinstance(processor, SpellProcessor)

    def test_get_processor_not_exists(self):
        """Test getting non-existing processor."""
        registry = ContentProcessorRegistry()

        # Mock a content type that doesn't have a processor
        fake_content_type = Mock()
        processor = registry.get_processor(fake_content_type)
        assert processor is None

    def test_process_content_with_processor(self):
        """Test content processing with available processor."""
        registry = ContentProcessorRegistry()
        spell = Mock(spec=Spell)
        spell.level = 1
        spell.entries = []
        spell.higher_level = []
        spell.components = Mock()
        spell.components.verbal = False
        spell.components.somatic = False
        spell.components.material = None
        spell.duration = []
        spell.classes = {}
        context = Mock(spec=RenderContext)

        # Mock the content type detection
        with patch(
            "dnd5e.renderers.latex.content_processor.ContentType.from_content"
        ) as mock_from_content:
            mock_from_content.return_value = ContentType.SPELL

            result = registry.process_content(spell, context)

            assert isinstance(result, dict)
            assert "spell_level_ordinal" in result

    def test_process_content_without_processor(self):
        """Test content processing without available processor."""
        registry = ContentProcessorRegistry()
        unknown_content = Mock()
        context = Mock(spec=RenderContext)

        # Mock the content type detection to return unknown type
        with patch(
            "dnd5e.renderers.latex.content_processor.ContentType.from_content"
        ) as mock_from_content:
            fake_content_type = Mock()
            mock_from_content.return_value = fake_content_type

            result = registry.process_content(unknown_content, context)

            assert result == {}


if __name__ == "__main__":
    pytest.main([__file__])
