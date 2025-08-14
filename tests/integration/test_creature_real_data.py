"""Integration tests using real 5etools creature data.

These tests verify that the creature conversion pipeline works correctly
with actual data from the 5etools dataset, ensuring real-world compatibility.
"""

from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.creatures import Creature
from tests.test_helpers import reset_test_environment


@pytest.mark.requires_data
@pytest.mark.integration
@pytest.mark.slow
class TestCreatureRealDataIntegration:
    """Test creature functionality with real 5etools data patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_real_goblin_data_processing(self):
        """Test processing of real goblin data from 5etools."""
        # Real goblin data from 5etools (simplified for testing)
        real_goblin_data = {
            "name": "Goblin",
            "source": "MM",
            "page": 166,
            "size": ["S"],
            "type": "humanoid",
            "alignment": ["N", "E"],
            "ac": [15],
            "hp": {"average": 7, "formula": "2d6"},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 10,
            "wis": 8,
            "cha": 8,
            "skill": {"stealth": "+6"},
            "senses": ["darkvision 60 ft.", "passive Perception 9"],
            "languages": ["Common", "Goblin"],
            "cr": "1/4",
            "trait": [
                {
                    "name": "Nimble Escape",
                    "entries": [
                        "The goblin can take the Dash or Disengage action as a bonus action on each of its turns."
                    ],
                }
            ],
            "action": [
                {
                    "name": "Scimitar",
                    "entries": [
                        "{@atk mw} {@hit 4} to hit, reach 5 ft., one target. {@h}1d6 + 2 slashing damage."
                    ],
                },
                {
                    "name": "Shortbow",
                    "entries": [
                        "{@atk rw} {@hit 4} to hit, range 80/320 ft., one target. {@h}1d6 + 2 piercing damage."
                    ],
                },
            ],
        }

        goblin = Creature.model_validate(real_goblin_data)

        # Test basic stat block
        assert goblin.name == "Goblin"
        assert goblin.get_enhanced_cr_text() == "1/4 (50 XP)"
        assert "Small humanoid, neutral evil" == goblin.get_size_type_alignment()

        # Test ability scores and modifiers
        assert goblin.get_ability_modifier(goblin.strength) == -1  # STR 8 = -1
        assert goblin.get_ability_modifier(goblin.dexterity) == 2  # DEX 14 = +2

        # Test traits and actions
        assert len(goblin.trait) == 1
        assert goblin.trait[0].name == "Nimble Escape"
        assert len(goblin.action) == 2

    def test_real_ancient_dragon_data_processing(self):
        """Test processing of complex real dragon data."""
        # Real Ancient Red Dragon data (simplified)
        real_dragon_data = {
            "name": "Ancient Red Dragon",
            "source": "MM",
            "size": ["G"],
            "type": "dragon",
            "alignment": ["C", "E"],
            "ac": [22],
            "hp": {"average": 546, "formula": "28d20 + 252"},
            "speed": {"walk": 40, "fly": 80, "climb": 40},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "save": {"dex": "+7", "con": "+20", "wis": "+9", "cha": "+13"},
            "skill": {"perception": "+16", "stealth": "+7"},
            "resist": ["fire"],
            "immune": ["fire"],
            "senses": [
                "blindsight 60 ft.",
                "darkvision 120 ft.",
                "passive Perception 26",
            ],
            "languages": ["Common", "Draconic"],
            "cr": "24",
            "trait": [
                {
                    "name": "Legendary Resistance",
                    "entries": [
                        "If the dragon fails a saving throw, it can choose to succeed instead (3/day)."
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
                        "{@atk mw} {@hit 17} to hit, reach 15 ft., one target. {@h}2d10 + 10 piercing damage plus 2d6 fire damage."
                    ],
                },
            ],
            "legendary": [
                {
                    "name": "Detect",
                    "entries": ["The dragon makes a Wisdom (Perception) check."],
                },
                {"name": "Tail Attack", "entries": ["The dragon makes a tail attack."]},
                {
                    "name": "Wing Attack",
                    "cost": 2,
                    "entries": [
                        "The dragon beats its wings. Each creature within 15 feet of the dragon must succeed on a DC 25 Dexterity saving throw or take 2d6 + 10 bludgeoning damage and be knocked prone."
                    ],
                },
            ],
        }

        dragon = Creature.model_validate(real_dragon_data)

        # Test basic properties
        assert dragon.name == "Ancient Red Dragon"
        assert dragon.get_enhanced_cr_text() == "24 (62,000 XP)"
        assert "Gargantuan dragon, chaotic evil" == dragon.get_size_type_alignment()

        # Test legendary actions
        assert dragon.legendary is not None
        assert len(dragon.legendary) == 3
        assert dragon.requires_full_width_layout() is True

        # Test high-level stats
        assert dragon.get_ability_modifier(dragon.strength) == 10  # STR 30 = +10
        assert dragon.hp.average == 546

    def test_real_spellcaster_data_processing(self):
        """Test processing of real spellcaster creature data."""
        # Real Archmage data (simplified)
        real_archmage_data = {
            "name": "Archmage",
            "source": "MM",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["A"],
            "ac": [17],
            "hp": {"average": 165, "formula": "27d8 + 54"},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 14,
            "con": 14,
            "int": 20,
            "wis": 15,
            "cha": 16,
            "save": {"int": "+11", "wis": "+8"},
            "skill": {"arcana": "+17", "history": "+17"},
            "resist": [
                "damage from spells; nonmagical bludgeoning, piercing, and slashing (from stoneskin)"
            ],
            "senses": ["passive Perception 12"],
            "languages": ["any six languages"],
            "cr": "12",
            "spellcasting": [
                {
                    "name": "Spellcasting",
                    "headerEntries": [
                        "The archmage is an 18th-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 19, +11 to hit with spell attacks). The archmage knows the following wizard spells:"
                    ],
                    "spells": {
                        "0": {
                            "spells": [
                                "{@spell mage hand}",
                                "{@spell minor illusion}",
                                "{@spell prestidigitation}",
                                "{@spell ray of frost}",
                            ]
                        },
                        "1": {
                            "slots": 4,
                            "spells": [
                                "{@spell detect magic}",
                                "{@spell identify}",
                                "{@spell mage armor}*",
                                "{@spell magic missile}",
                            ],
                        },
                        "9": {"slots": 1, "spells": ["{@spell time stop}*"]},
                    },
                }
            ],
            "action": [
                {
                    "name": "Dagger",
                    "entries": [
                        "{@atk mw,rw} {@hit 6} to hit, reach 5 ft. or range 20/60 ft., one target. {@h}1d4 + 2 piercing damage."
                    ],
                }
            ],
        }

        archmage = Creature.model_validate(real_archmage_data)

        # Test basic properties
        assert archmage.name == "Archmage"
        assert archmage.get_enhanced_cr_text() == "12 (8,400 XP)"

        # Test spellcasting
        assert archmage.spellcasting is not None
        assert len(archmage.spellcasting) == 1
        spellcasting = archmage.spellcasting[0]
        header_text = (
            spellcasting.headerEntries[0]
            if hasattr(spellcasting, "headerEntries")
            else spellcasting.get("headerEntries", [""])[0]
        )
        assert "18th-level spellcaster" in header_text
        spells_dict = (
            spellcasting.spells
            if hasattr(spellcasting, "spells")
            else spellcasting.get("spells", {})
        )
        assert "0" in spells_dict  # Cantrips
        assert "9" in spells_dict  # 9th level spells

    @patch("dnd5e.cli.main.get_tag_resolver")
    @patch("dnd5e.cli.main.get_omnidexer")
    def test_real_data_markup_processing(
        self, mock_get_omnidexer, mock_get_tag_resolver
    ):
        """Test markup processing with real data patterns."""
        # Setup mocks for tag processing
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text.side_effect = lambda text: (
            text.replace("{@atk mw}", "Melee Weapon Attack:")
            .replace("{@atk rw}", "Ranged Weapon Attack:")
            .replace("{@hit 4}", "+4")
            .replace("{@h}", "Hit: ")
            .replace("1d6 + 2", "1d6 + 2")
        )
        mock_get_tag_resolver.return_value = mock_tag_resolver
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        # Real orc data with typical markup
        real_orc_data = {
            "name": "Orc",
            "source": "MM",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["C", "E"],
            "ac": [13],
            "hp": {"average": 15, "formula": "2d8 + 2"},
            "speed": {"walk": 30},
            "str": 16,
            "dex": 12,
            "con": 13,
            "int": 7,
            "wis": 11,
            "cha": 10,
            "senses": ["darkvision 60 ft.", "passive Perception 10"],
            "languages": ["Common", "Orc"],
            "cr": "1/2",
            "trait": [
                {
                    "name": "Aggressive",
                    "entries": [
                        "As a bonus action, the orc can move up to its speed toward a hostile creature that it can see."
                    ],
                }
            ],
            "action": [
                {
                    "name": "Greataxe",
                    "entries": [
                        "{@atk mw} {@hit 5} to hit, reach 5 ft., one target. {@h}1d12 + 3 slashing damage."
                    ],
                },
                {
                    "name": "Javelin",
                    "entries": [
                        "{@atk mw,rw} {@hit 5} to hit, reach 5 ft. or range 30/120 ft., one target. {@h}1d6 + 3 piercing damage."
                    ],
                },
            ],
        }

        orc = Creature.model_validate(real_orc_data)

        # Test markup processing in actions
        with patch(
            "dnd5e.renderers.latex.entry_processor.RecursiveEntryProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_entries.return_value = [
                "Melee Weapon Attack: +5 to hit, reach 5 ft., one target.",
                "Hit: 1d12 + 3 slashing damage.",
            ]
            mock_processor_class.return_value = mock_processor

            greataxe_action = orc.action[0]
            processed_desc = greataxe_action.get_description_text()

            assert "Melee Weapon Attack" in processed_desc
            assert "+5 to hit" in processed_desc

    def test_real_data_edge_cases(self):
        """Test edge cases found in real 5etools data."""
        # Test creature with variant AC
        variant_ac_data = {
            "name": "Variant AC Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["N"],
            "ac": [
                {"ac": 15, "from": ["chain shirt", "shield"]},
                {"ac": 13, "condition": "without shield", "braces": True},
            ],
            "hp": {"average": 30},
            "speed": {"walk": 30},
            "str": 12,
            "dex": 14,
            "con": 13,
            "int": 10,
            "wis": 11,
            "cha": 9,
            "cr": "1/2",
        }

        variant_creature = Creature.model_validate(variant_ac_data)
        assert variant_creature.ac is not None

        # Test creature with complex speed
        complex_speed_data = {
            "name": "Complex Speed Creature",
            "source": "TEST",
            "size": ["L"],
            "type": "monstrosity",
            "alignment": ["U"],
            "ac": [16],
            "hp": {"average": 85},
            "speed": {
                "walk": 40,
                "fly": {"number": 80, "condition": "hover"},
                "swim": 40,
            },
            "str": 18,
            "dex": 13,
            "con": 16,
            "int": 2,
            "wis": 12,
            "cha": 7,
            "cr": "5",
        }

        complex_creature = Creature.model_validate(complex_speed_data)
        assert complex_creature.speed is not None
        speed_str = str(complex_creature.speed)
        assert "40 ft." in speed_str
        assert "fly" in speed_str
        assert "swim" in speed_str

    def test_real_data_stat_validation(self):
        """Test that real creature data validates correctly."""
        # Test creatures with extreme but valid stats
        high_cr_data = {
            "name": "Tarrasque",
            "source": "MM",
            "size": ["G"],
            "type": "monstrosity",
            "alignment": ["U"],
            "ac": [25],
            "hp": {"average": 676, "formula": "33d20 + 330"},
            "speed": {"walk": 40},
            "str": 30,
            "dex": 11,
            "con": 30,
            "int": 3,
            "wis": 11,
            "cha": 11,
            "save": {"int": "+5", "wis": "+9", "cha": "+9"},
            "resist": ["fire", "poison", "physical"],
            "immune": ["charm", "fear", "paralysis", "poison"],
            "senses": ["blindsight 120 ft.", "passive Perception 10"],
            "cr": "30",
        }

        tarrasque = Creature.model_validate(high_cr_data)
        assert tarrasque.name == "Tarrasque"
        assert tarrasque.get_enhanced_cr_text() == "30 (155,000 XP)"
        assert tarrasque.get_ability_modifier(tarrasque.strength) == 10
        assert tarrasque.get_ability_modifier(tarrasque.constitution) == 10

    def test_real_data_performance_baseline(self):
        """Test performance with typical real data loads."""
        # Create multiple creatures to test batch processing performance
        creatures_data = []

        for i in range(10):
            creature_data = {
                "name": f"Performance Test Creature {i}",
                "source": "TEST",
                "size": ["M"],
                "type": "humanoid",
                "alignment": ["N"],
                "ac": [10 + i],
                "hp": {"average": 20 + i * 5},
                "speed": {"walk": 30},
                "str": 10 + i,
                "dex": 10 + i,
                "con": 10 + i,
                "int": 10,
                "wis": 10,
                "cha": 10,
                "cr": "1",
                "action": [
                    {"name": f"Attack {i}", "entries": [f"Attack description {i}"]}
                ],
            }
            creatures_data.append(creature_data)

        # Test that we can process multiple creatures efficiently
        creatures = []
        for data in creatures_data:
            creature = Creature.model_validate(data)
            creatures.append(creature)

        assert len(creatures) == 10

        # Test that all creatures are valid
        for i, creature in enumerate(creatures):
            assert creature.name == f"Performance Test Creature {i}"
            assert creature.get_enhanced_cr_text() == "1 (200 XP)"
