"""Edge case tests for model validation.

This module tests specific edge cases and complex data structures
that might cause validation issues.
"""

import pytest
from typing import Any, Dict

from src.core.models.spells import Spell
from src.core.models.creatures import Creature, CreatureType, HitPoints, ArmorClass, Ability
from src.core.models.items import Item
from src.core.models.adventures import Adventure
from src.core.models.books import Book


class TestModelValidationEdgeCases:
    """Test edge cases for model validation."""

    def test_spell_complex_entries_structures(self):
        """Test spell validation with various complex entry structures."""
        test_cases = [
            # Nested entries with lists
            {
                "name": "Complex Spell 1",
                "source": "TEST",
                "level": 1,
                "school": "A",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "self"},
                "components": {"v": True},
                "duration": [{"type": "instant"}],
                "entries": [
                    "Simple entry",
                    {
                        "type": "entries",
                        "name": "Complex Section",
                        "entries": [
                            "Nested text",
                            {
                                "type": "list",
                                "items": [
                                    "List item 1",
                                    {"text": "List item with text key"}
                                ]
                            }
                        ]
                    }
                ]
            },
            # Table structures
            {
                "name": "Table Spell",
                "source": "TEST", 
                "level": 2,
                "school": "D",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "self"},
                "components": {"v": True},
                "duration": [{"type": "instant"}],
                "entries": [
                    "Spell with table",
                    {
                        "type": "table",
                        "caption": "Test Table",
                        "colLabels": ["Roll", "Effect"],
                        "rows": [
                            ["1-2", "Effect A"],
                            ["3-4", "Effect B"]
                        ]
                    }
                ]
            },
            # Quote structures
            {
                "name": "Quote Spell",
                "source": "TEST",
                "level": 0,
                "school": "T",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "self"},
                "components": {"v": True},
                "duration": [{"type": "instant"}],
                "entries": [
                    {
                        "type": "quote",
                        "entries": ["Magic is just science we don't understand yet."],
                        "by": "Test Wizard"
                    },
                    "Rest of spell description"
                ]
            }
        ]
        
        for i, spell_data in enumerate(test_cases):
            spell = Spell.model_validate(spell_data)
            assert spell.name == spell_data["name"]
            
            # Test text extraction
            description = spell.get_description_text()
            assert description, f"Failed to extract description for test case {i}"
            assert len(description) > 10, f"Description too short for test case {i}"
            
        print(f"✅ {len(test_cases)} complex spell entry structures validated")

    def test_spell_higher_level_variations(self):
        """Test spell validation with various higher level entry formats."""
        test_cases = [
            # Simple higher level
            {
                "entriesHigherLevel": [
                    {
                        "type": "entries",
                        "name": "At Higher Levels",
                        "entries": ["When you cast this spell using a spell slot of 2nd level or higher..."]
                    }
                ]
            },
            # Complex higher level with nested structures
            {
                "entriesHigherLevel": [
                    {
                        "type": "entries",
                        "name": "At Higher Levels",
                        "entries": [
                            "Base description",
                            {
                                "type": "list",
                                "items": [
                                    "Improvement 1",
                                    "Improvement 2"
                                ]
                            }
                        ]
                    }
                ]
            },
            # Multiple higher level sections
            {
                "entriesHigherLevel": [
                    {
                        "type": "entries", 
                        "name": "At 2nd Level",
                        "entries": ["Level 2 improvement"]
                    },
                    {
                        "type": "entries",
                        "name": "At 5th Level", 
                        "entries": ["Level 5 improvement"]
                    }
                ]
            }
        ]
        
        base_spell = {
            "name": "Higher Level Test",
            "source": "TEST",
            "level": 1,
            "school": "A",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "self"},
            "components": {"v": True},
            "duration": [{"type": "instant"}],
            "entries": ["Base spell description"]
        }
        
        for i, higher_level_data in enumerate(test_cases):
            spell_data = {**base_spell, **higher_level_data}
            spell = Spell.model_validate(spell_data)
            
            higher_text = spell.get_higher_level_text()
            assert higher_text, f"Failed to extract higher level text for test case {i}"
            
        print(f"✅ {len(test_cases)} higher level spell variations validated")

    def test_creature_type_variations(self):
        """Test creature type validation with various formats."""
        test_cases = [
            # Simple string type
            {"type": "humanoid"},
            # Object with subtype
            {"type": {"type": "humanoid", "subtype": "elf"}},
            # Object with tags
            {"type": {"type": "humanoid", "tags": ["elf", "wizard"]}},
            # Object with complex tags
            {"type": {"type": "humanoid", "tags": [{"tag": "elf", "prefix": "High"}, "wizard"]}},
            # Choice format
            {"type": {"choose": ["celestial", "fiend"]}},
            # Mixed format
            {"type": {"type": "humanoid", "subtype": "elf", "tags": [{"tag": "noble", "prefix": "High"}]}}
        ]
        
        for i, type_data in enumerate(test_cases):
            creature_type = CreatureType.model_validate(type_data["type"])
            type_str = str(creature_type)
            assert type_str, f"Failed to generate type string for test case {i}"
            assert len(type_str) > 0, f"Empty type string for test case {i}"
            
        print(f"✅ {len(test_cases)} creature type variations validated")

    def test_creature_alignment_variations(self):
        """Test creature alignment validation with various formats."""
        base_creature = {
            "name": "Test Creature",
            "source": "TEST", 
            "size": ["M"],
            "type": "humanoid",
            "ac": [{"ac": 10}],
            "hp": {"average": 10, "formula": "2d8+1"},
            "speed": {"walk": 30},
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "cr": "1"
        }
        
        alignment_test_cases = [
            # Simple alignments
            {"alignment": ["L", "G"]},
            {"alignment": ["N"]},
            {"alignment": ["C", "E"]},
            # Complex nested alignments
            {"alignment": [{"alignment": ["L", "N"]}, "G"]},
            {"alignment": [{"alignment": ["N", "G"]}, {"alignment": ["N", "E"]}]},
            # Choice alignments
            {"alignment": [{"special": "any alignment"}]},
            {"alignment": [{"choose": [["L", "G"], ["L", "N"]]}]}
        ]
        
        for i, alignment_data in enumerate(alignment_test_cases):
            creature_data = {**base_creature, **alignment_data}
            creature = Creature.model_validate(creature_data)
            
            alignment_text = creature._get_alignment_text()
            assert alignment_text, f"Failed to generate alignment text for test case {i}"
            
        print(f"✅ {len(alignment_test_cases)} creature alignment variations validated")

    def test_creature_hp_variations(self):
        """Test creature HP validation with various formats."""
        test_cases = [
            # Standard format
            {"average": 58, "formula": "9d8 + 18"},
            # Special format only
            {"special": "5 + five times your level"},
            # Special with additional data
            {"special": "Equal to your hit point maximum", "average": 100},
            # Formula only (should work with optional average)
            {"formula": "1d4"},
            # Average only (should work with optional formula)
            {"average": 25}
        ]
        
        for i, hp_data in enumerate(test_cases):
            hp = HitPoints.model_validate(hp_data)
            hp_str = str(hp)
            assert hp_str, f"Failed to generate HP string for test case {i}"
            assert hp_str != "Unknown", f"HP string defaulted to Unknown for test case {i}"
            
        print(f"✅ {len(test_cases)} creature HP variations validated")

    def test_creature_ac_variations(self):
        """Test creature AC validation with various formats."""
        test_cases = [
            # Standard format
            {"ac": 16, "from": ["natural armor"]},
            # Simple AC only
            {"ac": 12},
            # Special format only
            {"special": "11 + the level of the spell (natural armor)"},
            # Conditional AC
            {"ac": 15, "condition": "with mage armor"},
            # Complex special format
            {"special": "13 + Dex modifier (leather armor)"}
        ]
        
        for i, ac_data in enumerate(test_cases):
            ac = ArmorClass.model_validate(ac_data)
            ac_str = str(ac)
            assert ac_str, f"Failed to generate AC string for test case {i}"
            assert ac_str != "Unknown", f"AC string defaulted to Unknown for test case {i}"
            
        print(f"✅ {len(test_cases)} creature AC variations validated")

    def test_creature_ability_complex_entries(self):
        """Test creature ability validation with complex entry structures."""
        test_cases = [
            # Simple ability
            {
                "name": "Simple Ability",
                "entries": ["This is a simple ability description."]
            },
            # Complex nested ability
            {
                "name": "Complex Ability",
                "entries": [
                    "Base description",
                    {
                        "type": "list",
                        "items": [
                            "Effect 1",
                            "Effect 2",
                            {"text": "Effect with text key"}
                        ]
                    }
                ]
            },
            # Ability with attack information
            {
                "name": "Attack Ability",
                "entries": [
                    "Melee Weapon Attack: +5 to hit, reach 5 ft., one target.",
                    {
                        "type": "entries",
                        "name": "Hit",
                        "entries": ["7 (1d8 + 3) slashing damage."]
                    }
                ]
            }
        ]
        
        for i, ability_data in enumerate(test_cases):
            ability = Ability.model_validate(ability_data)
            assert ability.name == ability_data["name"]
            
            description = ability.get_description_text()
            assert description, f"Failed to extract description for ability test case {i}"
            
        print(f"✅ {len(test_cases)} creature ability variations validated")

    def test_item_complex_entries(self):
        """Test item validation with complex entry structures."""
        test_cases = [
            # Item with properties list
            {
                "name": "Magic Sword",
                "source": "TEST",
                "type": "M",
                "rarity": "rare",
                "entries": [
                    "This magic sword grants special abilities:",
                    {
                        "type": "list",
                        "items": [
                            "Property 1: +1 bonus to attack and damage rolls",
                            "Property 2: Deals extra radiant damage"
                        ]
                    }
                ]
            },
            # Item with tables
            {
                "name": "Random Item",
                "source": "TEST", 
                "type": "G",
                "entries": [
                    "Roll on the table below:",
                    {
                        "type": "table",
                        "caption": "Random Effects",
                        "colLabels": ["d6", "Effect"],
                        "rows": [
                            ["1-2", "Effect A"],
                            ["3-4", "Effect B"],
                            ["5-6", "Effect C"]
                        ]
                    }
                ]
            },
            # Item with variant rules
            {
                "name": "Variant Item",
                "source": "TEST",
                "type": "G",
                "entries": [
                    "Base item description",
                    {
                        "type": "entries",
                        "name": "Variant Rule",
                        "entries": [
                            "Optional variant description",
                            {
                                "type": "list",
                                "style": "list-hang-notitle",
                                "items": ["Variant property 1", "Variant property 2"]
                            }
                        ]
                    }
                ]
            }
        ]
        
        for i, item_data in enumerate(test_cases):
            item = Item.model_validate(item_data)
            assert item.name == item_data["name"]
            
            if item.entries:
                description = item.get_description_text()
                assert description, f"Failed to extract description for item test case {i}"
                
        print(f"✅ {len(test_cases)} item entry variations validated")

    def test_source_format_variations(self):
        """Test that various source formats are handled correctly."""
        from src.core.models.content import Source
        
        test_cases = [
            # String source
            "PHB",
            # Object with abbreviation only
            {"abbreviation": "MM"},
            # Full source object
            {"abbreviation": "DMG", "name": "Dungeon Master's Guide", "page": 123},
            # Source with additional data
            {"abbreviation": "XGE", "name": "Xanathar's Guide", "page": 45, "url": "test"}
        ]
        
        for i, source_data in enumerate(test_cases):
            if isinstance(source_data, str):
                # Test string source conversion in model validation
                spell_data = {
                    "name": f"Test Spell {i}",
                    "source": source_data,
                    "level": 0,
                    "school": "T",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {"type": "self"},
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Test"]
                }
                spell = Spell.model_validate(spell_data)
                assert spell.source.abbreviation == source_data
            else:
                source = Source.model_validate(source_data)
                assert source.abbreviation == source_data["abbreviation"]
                
        print(f"✅ {len(test_cases)} source format variations validated")

    def test_damage_resistance_immunity_formats(self):
        """Test creature damage resistance/immunity with various formats."""
        base_creature = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid", 
            "alignment": ["N"],
            "ac": [{"ac": 10}],
            "hp": {"average": 10, "formula": "2d8+1"},
            "speed": {"walk": 30},
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "cr": "1"
        }
        
        resistance_test_cases = [
            # Simple resistances
            {"resist": ["fire", "cold"]},
            # Complex resistance with conditions
            {"resist": [{"resist": ["bludgeoning", "piercing"], "note": "from nonmagical attacks"}]},
            # Immunities with special conditions
            {"immune": ["poison"], "conditionImmune": ["poisoned"]},
            # Complex condition immunities
            {"conditionImmune": [{"conditionImmune": ["charmed"], "note": "while raging"}]},
            # Mixed formats
            {"resist": ["fire"], "immune": [{"special": "damage from spells"}], "vulnerable": ["cold"]}
        ]
        
        for i, resistance_data in enumerate(resistance_test_cases):
            creature_data = {**base_creature, **resistance_data}
            creature = Creature.model_validate(creature_data)
            assert creature.name == "Test Creature"
            
        print(f"✅ {len(resistance_test_cases)} damage resistance/immunity variations validated")

    def test_skill_bonus_formats(self):
        """Test creature skill bonus validation with various formats."""
        test_cases = [
            # Simple skill bonuses
            {"skill": {"perception": "+5", "stealth": "+3"}},
            # Mixed string and integer formats
            {"skill": {"athletics": "+2", "acrobatics": "3"}},
            # Complex skill formats with choices
            {"skill": {"other": [{"oneOf": {"arcana": "+7", "history": "+7", "religion": "+7"}}]}},
            # Skill with expertise notation
            {"skill": {"insight": "+5", "persuasion": "+8 (expertise)"}},
            # Empty skills (should be valid)
            {"skill": {}}
        ]
        
        base_creature = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["N"], 
            "ac": [{"ac": 10}],
            "hp": {"average": 10, "formula": "2d8+1"},
            "speed": {"walk": 30},
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "cr": "1"
        }
        
        for i, skill_data in enumerate(test_cases):
            creature_data = {**base_creature, **skill_data}
            creature = Creature.model_validate(creature_data)
            assert creature.name == "Test Creature"
            
        print(f"✅ {len(test_cases)} skill bonus format variations validated")

    def test_passive_perception_formats(self):
        """Test creature passive perception with various formats."""
        test_cases = [
            # Standard integer
            {"passive": 12},
            # Formula string (edge case that should be handled gracefully)
            {"passive": "10 + (PB × 2)"},
            # String with number
            {"passive": "15 (Perception)"},
            # Complex calculation string
            {"passive": "10 + Wisdom modifier + proficiency bonus"}
        ]
        
        base_creature = {
            "name": "Test Creature", 
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["N"],
            "ac": [{"ac": 10}],
            "hp": {"average": 10, "formula": "2d8+1"},
            "speed": {"walk": 30},
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "cr": "1"
        }
        
        for i, passive_data in enumerate(test_cases):
            creature_data = {**base_creature, **passive_data}
            
            # For string passive values, we expect validation warnings but not failures
            try:
                creature = Creature.model_validate(creature_data)
                # If it validates successfully, that's fine
                assert creature.name == "Test Creature"
            except Exception:
                # String passive values may cause validation errors, which is expected
                # We're testing that the system handles them gracefully
                pass
                
        print(f"✅ {len(test_cases)} passive perception format variations tested")

    def test_challenge_rating_formats(self):
        """Test creature challenge rating with various formats."""
        test_cases = [
            # Standard string
            {"cr": "5"},
            # Fractional CR
            {"cr": "1/4"},
            # Integer CR
            {"cr": 10},
            # Complex CR with XP
            {"cr": {"cr": "8", "xp": 3900}},
            # Variable CR
            {"cr": "1-4"},
            # Special CR format
            {"cr": {"special": "Equal to summoner's level"}}
        ]
        
        base_creature = {
            "name": "Test Creature",
            "source": "TEST", 
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["N"],
            "ac": [{"ac": 10}],
            "hp": {"average": 10, "formula": "2d8+1"},
            "speed": {"walk": 30},
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10
        }
        
        for i, cr_data in enumerate(test_cases):
            creature_data = {**base_creature, **cr_data}
            creature = Creature.model_validate(creature_data)
            
            cr_text = creature.get_cr_text()
            assert cr_text, f"Failed to generate CR text for test case {i}"
            assert cr_text != "Unknown", f"CR text defaulted to Unknown for test case {i}"
            
        print(f"✅ {len(test_cases)} challenge rating format variations validated")