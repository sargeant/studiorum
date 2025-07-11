"""Tests for data models."""

import pytest
from pydantic import ValidationError

from src.core.models.spells import Spell, SpellComponent
from src.core.models.creatures import Creature, ArmorClass, HitPoints
from src.core.models.content import Source, ContentType


class TestSource:
    """Tests for Source model."""
    
    def test_source_creation(self):
        """Test basic source creation."""
        source = Source(abbreviation="PHB", name="Player's Handbook", page=123)
        assert source.abbreviation == "PHB"
        assert source.name == "Player's Handbook"
        assert source.page == 123
    
    def test_source_str(self):
        """Test source string representation."""
        source = Source(abbreviation="PHB", name="Player's Handbook", page=123)
        assert str(source) == "PHB, p. 123"
        
        source_no_page = Source(abbreviation="PHB", name="Player's Handbook")
        assert str(source_no_page) == "PHB"


class TestSpell:
    """Tests for Spell model."""
    
    def test_spell_creation(self, sample_spell_data):
        """Test basic spell creation."""
        spell = Spell.model_validate(sample_spell_data)
        assert spell.name == "Fireball"
        assert spell.level == 3
        assert spell.school == "Evocation"  # Should be expanded from "V"
    
    def test_spell_validation_error(self):
        """Test spell validation with invalid data."""
        with pytest.raises(ValidationError):
            Spell.model_validate({
                "name": "Test Spell",
                "level": 10,  # Invalid level > 9
                "school": "V"
            })
    
    def test_spell_level_text(self, sample_spell):
        """Test spell level text formatting."""
        assert sample_spell.get_level_text() == "3rd-level evocation"
        
        cantrip_spell = Spell.model_validate({
            "name": "Test Cantrip",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
            "level": 0,
            "school": "V",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point"},
            "components": {"v": True},
            "duration": [{"type": "instant"}],
            "entries": ["Test"]
        })
        assert cantrip_spell.get_level_text() == "Evocation cantrip"
    
    def test_spell_components_text(self, sample_spell):
        """Test spell components text formatting."""
        components_text = sample_spell.get_components_text()
        assert "V" in components_text
        assert "S" in components_text
        assert "M" in components_text
        assert "bat guano" in components_text


class TestCreature:
    """Tests for Creature model."""
    
    def test_creature_creation(self, sample_creature_data):
        """Test basic creature creation."""
        creature = Creature.model_validate(sample_creature_data)
        assert creature.name == "Ancient Red Dragon"
        assert creature.strength == 30
        assert creature.get_ability_modifier(30) == 10
    
    def test_ability_modifier_calculation(self, sample_creature):
        """Test ability modifier calculation."""
        assert sample_creature.get_ability_modifier(10) == 0
        assert sample_creature.get_ability_modifier(8) == -1
        assert sample_creature.get_ability_modifier(18) == 4
        assert sample_creature.get_ability_modifier(30) == 10
    
    def test_ability_text_formatting(self, sample_creature):
        """Test ability score text formatting."""
        assert sample_creature.get_ability_text(18) == "18 (+4)"
        assert sample_creature.get_ability_text(8) == "8 (-1)"
        assert sample_creature.get_ability_text(10) == "10 (+0)"
    
    def test_size_type_alignment(self, sample_creature):
        """Test size/type/alignment formatting."""
        size_type_alignment = sample_creature.get_size_type_alignment()
        assert "Gargantuan" in size_type_alignment or "G" in size_type_alignment
        assert "dragon" in size_type_alignment
    
    def test_armor_class_parsing(self, sample_creature_data):
        """Test AC parsing from various formats."""
        creature = Creature.model_validate(sample_creature_data)
        ac_text = creature.get_ac_text()
        assert "22" in ac_text


class TestSpellComponent:
    """Tests for SpellComponent model."""
    
    def test_material_component_parsing(self):
        """Test parsing of material components."""
        # Boolean material component
        comp1 = SpellComponent.model_validate({"v": True, "s": False, "m": True})
        assert comp1.material is True
        
        # String material component
        comp2 = SpellComponent.model_validate({"v": True, "s": True, "m": "a diamond worth 1,000 gp"})
        assert comp2.material == "a diamond worth 1,000 gp"
        
        # Dict material component (legacy format)
        comp3 = SpellComponent.model_validate({"v": True, "s": True, "m": {"text": "bat guano"}})
        assert comp3.material == "bat guano"


class TestArmorClass:
    """Tests for ArmorClass model."""
    
    def test_armor_class_creation(self):
        """Test AC creation and string representation.""" 
        ac = ArmorClass.model_validate({"ac": 15, "from": ["leather armor", "+1 shield"]})
        assert ac.ac == 15
        assert str(ac) == "15 (leather armor, +1 shield)"
        
        simple_ac = ArmorClass(ac=12)
        assert str(simple_ac) == "12"


class TestHitPoints:
    """Tests for HitPoints model."""
    
    def test_hit_points_creation(self):
        """Test HP creation and string representation."""
        hp = HitPoints(average=58, formula="9d8 + 18")
        assert hp.average == 58
        assert hp.formula == "9d8 + 18"
        assert str(hp) == "58 (9d8 + 18)"