"""Integration tests for creature spell indexing."""

import pytest

from dnd5e.core.interfaces import DeepIndexable
from dnd5e.core.models.content import ContentType
from dnd5e.core.models.creatures import Creature
from dnd5e.core.references import SpellReferenceParser


@pytest.mark.integration
class TestCreatureSpellIndexing:
    """Test creature spell indexing functionality."""

    def test_creature_implements_deep_indexable(self):
        """Test that Creature implements DeepIndexable protocol."""
        # Create a minimal creature
        creature_data = {
            "name": "Test Creature",
            "source": {"abbreviation": "TEST"},
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 30},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 12,
            "con": 11,
            "int": 10,
            "wis": 13,
            "cha": 8,
        }

        creature = Creature.model_validate(creature_data)
        assert isinstance(creature, DeepIndexable)

    def test_extract_spell_references_from_creature_traits(self):
        """Test extracting spell references from creature traits."""
        creature_data = {
            "name": "Archmage",
            "source": {"abbreviation": "MM"},
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["any alignment"],
            "ac": [15],
            "hp": {"average": 165},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 14,
            "con": 12,
            "int": 20,
            "wis": 15,
            "cha": 16,
            "trait": [
                {
                    "name": "Spellcasting",
                    "entries": [
                        "The archmage can cast {@spell detect magic} at will.",
                        "1st level (4 slots): {@spell magic missile|phb}, {@spell shield|phb}",
                        "9th level (1 slot): {@spell wish|phb}",
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Extract spell references directly from the text
        trait_text = creature.trait[0].get_description_text()
        references = SpellReferenceParser.extract_spell_references(trait_text)

        assert len(references) >= 3
        spell_names = [ref.name for ref in references]
        assert "detect magic" in spell_names
        assert "magic missile" in spell_names
        assert "wish" in spell_names

    def test_extract_spell_references_from_creature_actions(self):
        """Test extracting spell references from creature actions."""
        creature_data = {
            "name": "Lich",
            "source": {"abbreviation": "MM"},
            "size": ["Medium"],
            "type": "undead",
            "alignment": ["any evil alignment"],
            "ac": [17],
            "hp": {"average": 135},
            "speed": {"walk": 30},
            "str": 11,
            "dex": 16,
            "con": 16,
            "int": 20,
            "wis": 14,
            "cha": 16,
            "action": [
                {
                    "name": "Disrupt Life",
                    "entries": [
                        "Each non-undead creature within 20 feet of the lich must make a DC 18 Constitution saving throw against this magic, taking 21 (6d6) necrotic damage on a failed save, or half as much damage on a successful one."
                    ],
                },
                {
                    "name": "Spellcasting",
                    "entries": [
                        "The lich casts {@spell counterspell|phb}.",
                        "It can also cast {@spell finger of death|phb} or {@spell fireball|phb}.",
                    ],
                },
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Extract spell references from actions
        all_text = ""
        for action in creature.action:
            all_text += " " + action.get_description_text()

        references = SpellReferenceParser.extract_spell_references(all_text)

        assert len(references) >= 3
        spell_names = [ref.name for ref in references]
        assert "counterspell" in spell_names
        assert "finger of death" in spell_names
        assert "fireball" in spell_names

    def test_creature_with_no_spells(self):
        """Test creature with no spell references."""
        creature_data = {
            "name": "Goblin",
            "source": {"abbreviation": "MM"},
            "size": ["Small"],
            "type": "humanoid",
            "alignment": ["neutral evil"],
            "ac": [15],
            "hp": {"average": 7},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 10,
            "wis": 8,
            "cha": 8,
            "action": [
                {
                    "name": "Scimitar",
                    "entries": [
                        "Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage."
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Extract spell references from actions
        action_text = creature.action[0].get_description_text()
        references = SpellReferenceParser.extract_spell_references(action_text)

        assert len(references) == 0

    def test_creature_with_complex_spellcasting_structure(self):
        """Test creature with complex spellcasting in multiple ability lists."""
        creature_data = {
            "name": "Draconic Sorcerer",
            "source": {"abbreviation": "VGM"},
            "size": ["Medium"],
            "type": "humanoid",
            "alignment": ["any alignment"],
            "ac": [13],
            "hp": {"average": 40},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 16,
            "con": 13,
            "int": 12,
            "wis": 11,
            "cha": 17,
            "trait": [
                {
                    "name": "Spellcasting",
                    "entries": [
                        "Cantrips (at will): {@spell mage hand|phb}, {@spell prestidigitation|phb}"
                    ],
                }
            ],
            "action": [
                {
                    "name": "Cast Spell",
                    "entries": ["The sorcerer casts {@spell burning hands|phb}."],
                }
            ],
            "reaction": [
                {
                    "name": "Shield",
                    "entries": [
                        "The sorcerer casts {@spell shield|phb} as a reaction."
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Collect all text from all ability types
        all_text = ""
        for ability_list in [creature.trait, creature.action, creature.reaction]:
            if ability_list:
                for ability in ability_list:
                    all_text += " " + ability.get_description_text()

        references = SpellReferenceParser.extract_spell_references(all_text)

        assert len(references) >= 4
        spell_names = [ref.name for ref in references]
        assert "mage hand" in spell_names
        assert "prestidigitation" in spell_names
        assert "burning hands" in spell_names
        assert "shield" in spell_names


@pytest.mark.asyncio
@pytest.mark.integration
class TestCreatureDeepIndexingIntegration:
    """Test full deep indexing integration with mock omnidexer."""

    def test_creature_deep_indexing_with_mock_omnidexer(self):
        """Test that creature deep indexing works with a mock omnidexer."""
        from unittest.mock import MagicMock

        from dnd5e.core.models.spells import Spell

        # Create mock spell objects
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
        mock_omnidexer = MagicMock()
        mock_omnidexer.find.side_effect = lambda content_type, name, source=None: {
            (ContentType.SPELL, "fireball", "phb"): mock_fireball,
            (ContentType.SPELL, "shield", "phb"): mock_shield,
        }.get((content_type, name.lower(), source.lower() if source else None))

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
                        "The wizard casts {@spell fireball|phb} or {@spell shield|phb}."
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Test deep indexing
        deep_entries = creature.get_deep_index_entries(mock_omnidexer)

        assert len(deep_entries) == 2
        assert mock_fireball in deep_entries
        assert mock_shield in deep_entries

    def test_creature_deep_indexing_handles_missing_spells(self):
        """Test that deep indexing handles missing spells gracefully."""
        from unittest.mock import MagicMock

        # Create mock omnidexer that finds nothing
        mock_omnidexer = MagicMock()
        mock_omnidexer.find.return_value = None
        mock_omnidexer.search.return_value = []

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
                    "entries": ["The wizard casts {@spell nonexistent spell|phb}."],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Test deep indexing doesn't crash on missing spells
        deep_entries = creature.get_deep_index_entries(mock_omnidexer)

        assert len(deep_entries) == 0
