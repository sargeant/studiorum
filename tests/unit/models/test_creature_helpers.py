"""Unit tests for creature helper methods added in Phase 1 of creature rendering parity.

Tests the six new helper methods:
- get_pronoun_subject()
- get_pronoun_object()
- get_pronoun_possessive()
- get_short_name()
- get_section_header()
- get_legendary_actions_header()

These tests ensure 5etools parity for creature text generation and template rendering.
"""

import pytest

from studiorum.core.models.creatures import Ability, Creature
from tests.test_helpers import reset_test_environment


class TestCreaturePronounHelpers:
    """Test pronoun helper methods for named vs generic creatures."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_pronouns_named_creature(self):
        """Test pronouns for named creatures (isNamedCreature=True)."""
        creature_data = {
            "name": "Strahd von Zarovich",
            "source": "COS",
            "isNamedCreature": True,
            "size": ["M"],
            "type": "undead",
            "alignment": ["lawful evil"],
            "ac": [17],
            "hp": {"average": 144, "formula": "17d12 + 68"},
            "speed": {"walk": 30},
            "str": 18,
            "dex": 18,
            "con": 18,
            "int": 20,
            "wis": 15,
            "cha": 18,
            "cr": "15",
        }

        creature = Creature.model_validate(creature_data)

        # Named creatures use "they/them/their"
        assert creature.get_pronoun_subject() == "they"
        assert creature.get_pronoun_object() == "them"
        assert creature.get_pronoun_possessive() == "their"

    def test_pronouns_generic_creature(self):
        """Test pronouns for generic creatures (isNamedCreature=False/None)."""
        creature_data = {
            "name": "Goblin",
            "source": "MM",
            "size": ["S"],
            "type": "humanoid",
            "alignment": ["neutral evil"],
            "ac": [15],
            "hp": {"average": 7, "formula": "2d6"},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 10,
            "wis": 8,
            "cha": 8,
            "cr": "1/4",
        }

        creature = Creature.model_validate(creature_data)

        # Generic creatures use "it/its/its"
        assert creature.get_pronoun_subject() == "it"
        assert creature.get_pronoun_object() == "its"
        assert creature.get_pronoun_possessive() == "its"

    def test_pronouns_explicitly_false_named_creature(self):
        """Test pronouns when isNamedCreature is explicitly False."""
        creature_data = {
            "name": "Ancient Red Dragon",
            "source": "MM",
            "isNamedCreature": False,
            "size": ["G"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [22],
            "hp": {"average": 546},
            "speed": {"walk": 40, "fly": 80},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "cr": "24",
        }

        creature = Creature.model_validate(creature_data)

        # Even large creatures use "it/its/its" when not named
        assert creature.get_pronoun_subject() == "it"
        assert creature.get_pronoun_object() == "its"
        assert creature.get_pronoun_possessive() == "its"


class TestCreatureShortNameHelpers:
    """Test short name formatting for different cases."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_short_name_named_creature_no_prefix(self):
        """Test that named creatures don't get 'the' prefix."""
        creature_data = {
            "name": "Strahd von Zarovich",
            "source": "COS",
            "isNamedCreature": True,
            "size": ["M"],
            "type": "undead",
            "alignment": ["lawful evil"],
            "ac": [17],
            "hp": {"average": 144},
            "speed": {"walk": 30},
            "str": 18,
            "dex": 18,
            "con": 18,
            "int": 20,
            "wis": 15,
            "cha": 18,
            "cr": "15",
        }

        creature = Creature.model_validate(creature_data)

        # Named creatures: no prefix, use first name
        assert creature.get_short_name() == "Strahd"
        assert creature.get_short_name(is_title_case=True) == "Strahd"
        assert creature.get_short_name(is_sentence_case=True) == "Strahd"

    def test_short_name_generic_creature_with_prefix(self):
        """Test that generic creatures get 'the/The' prefix."""
        creature_data = {
            "name": "Ancient Red Dragon",
            "source": "MM",
            "size": ["G"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [22],
            "hp": {"average": 546},
            "speed": {"walk": 40, "fly": 80},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "cr": "24",
        }

        creature = Creature.model_validate(creature_data)

        # Generic creatures: get prefix, lowercase base
        assert creature.get_short_name() == "the ancient red dragon"
        assert creature.get_short_name(is_title_case=True) == "The Ancient Red Dragon"
        assert (
            creature.get_short_name(is_sentence_case=True) == "The Ancient red dragon"
        )

    def test_short_name_with_comma_separator(self):
        """Test short name extraction for names with comma separators."""
        creature_data = {
            "name": "Hobgoblin Captain, Elite Warrior",
            "source": "MM",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["lawful evil"],
            "ac": [17],
            "hp": {"average": 39},
            "speed": {"walk": 30},
            "str": 15,
            "dex": 14,
            "con": 16,
            "int": 12,
            "wis": 10,
            "cha": 13,
            "cr": "3",
        }

        creature = Creature.model_validate(creature_data)

        # Should use part before comma
        assert creature.get_short_name() == "the hobgoblin captain"
        assert creature.get_short_name(is_title_case=True) == "The Hobgoblin Captain"

    def test_short_name_explicit_string_override(self):
        """Test short name when explicitly set as string."""
        creature_data = {
            "name": "Very Long Dragon Name With Many Words",
            "source": "TEST",
            "shortName": "Dragon",
            "size": ["L"],
            "type": "dragon",
            "alignment": ["neutral"],
            "ac": [18],
            "hp": {"average": 200},
            "speed": {"walk": 40, "fly": 80},
            "str": 23,
            "dex": 10,
            "con": 21,
            "int": 14,
            "wis": 11,
            "cha": 19,
            "cr": "13",
        }

        creature = Creature.model_validate(creature_data)

        # Should use explicit short name
        assert creature.get_short_name() == "the dragon"
        assert creature.get_short_name(is_title_case=True) == "The Dragon"

    def test_short_name_explicit_true_uses_full_name(self):
        """Test short name when explicitly set to True."""
        creature_data = {
            "name": "Fire Giant",
            "source": "MM",
            "shortName": True,
            "size": ["H"],
            "type": "giant",
            "alignment": ["lawful evil"],
            "ac": [18],
            "hp": {"average": 162},
            "speed": {"walk": 30},
            "str": 25,
            "dex": 9,
            "con": 23,
            "int": 10,
            "wis": 14,
            "cha": 13,
            "cr": "9",
        }

        creature = Creature.model_validate(creature_data)

        # shortName: true means use full name
        assert creature.get_short_name() == "the fire giant"
        assert creature.get_short_name(is_title_case=True) == "The Fire Giant"

    def test_short_name_edge_cases(self):
        """Test edge cases for short name generation."""
        # Empty name case
        creature_data = {
            "name": "",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [10],
            "hp": {"average": 4},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "0",
        }

        creature = Creature.model_validate(creature_data)
        assert creature.get_short_name() == "the "


class TestCreatureSectionHeaderHelpers:
    """Test section header accessor methods."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_get_section_header_existing(self):
        """Test getting custom header for an existing section."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            # Custom header for actions
            "action_header": ["Custom action header text"],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_section_header("action")
        assert header == ["Custom action header text"]

    def test_get_section_header_nonexistent(self):
        """Test getting header for non-existent section."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_section_header("nonexistent")
        assert header is None

    def test_get_section_header_multiple_sections(self):
        """Test section header access for multiple section types."""
        creature_data = {
            "name": "Test Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 58},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "2",
            # Multiple custom headers
            "trait_header": ["Trait header"],
            "action_header": ["Action header"],
            "reaction_header": ["Reaction header"],
        }

        creature = Creature.model_validate(creature_data)

        assert creature.get_section_header("trait") == ["Trait header"]
        assert creature.get_section_header("action") == ["Action header"]
        assert creature.get_section_header("reaction") == ["Reaction header"]
        assert creature.get_section_header("legendary") is None


class TestCreatureLegendaryActionsHeaderHelpers:
    """Test legendary actions header generation."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_legendary_actions_header_no_legendary_actions(self):
        """Test that creatures without legendary actions return None."""
        creature_data = {
            "name": "Regular Goblin",
            "source": "MM",
            "size": ["S"],
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
            "cr": "1/4",
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()
        assert header is None

    def test_legendary_actions_header_default_count(self):
        """Test legendary actions header with default count (3)."""
        creature_data = {
            "name": "Adult Red Dragon",
            "source": "MM",
            "size": ["H"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [19],
            "hp": {"average": 256},
            "speed": {"walk": 40, "fly": 80},
            "str": 27,
            "dex": 10,
            "con": 25,
            "int": 16,
            "wis": 13,
            "cha": 21,
            "cr": "17",
            "legendary": [
                Ability(
                    name="Detect",
                    entries=["The dragon makes a Wisdom (Perception) check."],
                ),
                Ability(
                    name="Tail Attack", entries=["The dragon makes a tail attack."]
                ),
                Ability(name="Wing Attack", entries=["The dragon beats its wings."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        assert header is not None
        assert len(header) == 1
        header_text = header[0]

        # Should mention 3 actions and use generic pronouns
        assert "The Adult Red Dragon can take 3 legendary actions" in header_text
        assert "its turn" in header_text
        assert (
            "The Adult Red Dragon regains spent legendary actions at the start of its turn"
            in header_text
        )

    def test_legendary_actions_header_named_creature(self):
        """Test legendary actions header for named creature with proper pronouns."""
        creature_data = {
            "name": "Strahd von Zarovich",
            "source": "COS",
            "isNamedCreature": True,
            "size": ["M"],
            "type": "undead",
            "alignment": ["lawful evil"],
            "ac": [17],
            "hp": {"average": 144},
            "speed": {"walk": 30},
            "str": 18,
            "dex": 18,
            "con": 18,
            "int": 20,
            "wis": 15,
            "cha": 18,
            "cr": "15",
            "legendary": [
                Ability(name="Move", entries=["Strahd moves up to his speed."]),
                Ability(
                    name="Unarmed Strike", entries=["Strahd makes an unarmed strike."]
                ),
                Ability(name="Cast Spell", entries=["Strahd casts a spell."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        assert header is not None
        header_text = header[0]

        # Should use proper pronouns for named creatures
        assert "Strahd can take 3 legendary actions" in header_text
        assert "their turn" in header_text
        assert (
            "Strahd regains spent legendary actions at the start of their turn"
            in header_text
        )

    def test_legendary_actions_header_custom_count(self):
        """Test legendary actions header with custom action count."""
        creature_data = {
            "name": "Powerful Lich",
            "source": "TEST",
            "size": ["M"],
            "type": "undead",
            "alignment": ["neutral evil"],
            "ac": [17],
            "hp": {"average": 135},
            "speed": {"walk": 30, "fly": 60},
            "str": 11,
            "dex": 16,
            "con": 16,
            "int": 20,
            "wis": 14,
            "cha": 16,
            "cr": "21",
            "legendaryActions": 4,  # Custom count
            "legendary": [
                Ability(name="Cantrip", entries=["The lich casts a cantrip."]),
                Ability(name="Teleport", entries=["The lich teleports."]),
                Ability(name="Spell", entries=["The lich casts a spell."]),
                Ability(
                    name="Frightening Gaze", entries=["The lich uses frightening gaze."]
                ),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        assert header is not None
        header_text = header[0]

        # Should use custom count
        assert "The Powerful Lich can take 4 legendary actions" in header_text

    def test_legendary_actions_header_lair_variant(self):
        """Test legendary actions header with lair action count variant."""
        creature_data = {
            "name": "Ancient Dragon",
            "source": "TEST",
            "size": ["G"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [22],
            "hp": {"average": 546},
            "speed": {"walk": 40, "fly": 80},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "cr": "24",
            "legendaryActions": 3,
            "legendaryActionsLair": 5,  # Different lair count
            "legendary": [
                Ability(name="Detect", entries=["The dragon makes a Wisdom check."]),
                Ability(
                    name="Tail Attack", entries=["The dragon makes a tail attack."]
                ),
                Ability(name="Wing Attack", entries=["The dragon beats its wings."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        assert header is not None
        header_text = header[0]

        # Should mention both counts
        assert "3 legendary actions" in header_text
        assert "(or 5 when in its lair)" in header_text
        assert (
            "The Ancient Dragon can take 3 legendary actions (or 5 when in its lair)"
            in header_text
        )

    def test_legendary_actions_header_precedence_custom_header(self):
        """Test precedence: legendary_header overrides generated text."""
        creature_data = {
            "name": "Custom Dragon",
            "source": "TEST",
            "size": ["L"],
            "type": "dragon",
            "alignment": ["neutral"],
            "ac": [18],
            "hp": {"average": 200},
            "speed": {"walk": 40, "fly": 80},
            "str": 23,
            "dex": 10,
            "con": 21,
            "int": 14,
            "wis": 11,
            "cha": 19,
            "cr": "13",
            "legendaryHeader": [
                "Custom legendary actions header that overrides default generation."
            ],
            "legendary": [
                Ability(name="Attack", entries=["The dragon attacks."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        assert header == [
            "Custom legendary actions header that overrides default generation."
        ]

    def test_legendary_actions_header_precedence_generic_section(self):
        """Test precedence: generic 'legendary' section header overrides generated text."""
        creature_data = {
            "name": "Section Header Dragon",
            "source": "TEST",
            "size": ["L"],
            "type": "dragon",
            "alignment": ["neutral"],
            "ac": [18],
            "hp": {"average": 200},
            "speed": {"walk": 40, "fly": 80},
            "str": 23,
            "dex": 10,
            "con": 21,
            "int": 14,
            "wis": 11,
            "cha": 19,
            "cr": "13",
            "legendaryHeader": ["Generic legendary section header."],
            "legendary": [
                Ability(name="Attack", entries=["The dragon attacks."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        # legendary_header takes precedence
        assert header == ["Generic legendary section header."]

    def test_legendary_actions_header_singular_action(self):
        """Test legendary actions header text for single action (grammar)."""
        creature_data = {
            "name": "Single Action Creature",
            "source": "TEST",
            "size": ["M"],
            "type": "monstrosity",
            "alignment": ["neutral"],
            "ac": [15],
            "hp": {"average": 100},
            "speed": {"walk": 30},
            "str": 16,
            "dex": 14,
            "con": 16,
            "int": 10,
            "wis": 12,
            "cha": 10,
            "cr": "5",
            "legendaryActions": 1,  # Single action
            "legendary": [
                Ability(name="Strike", entries=["The creature strikes."]),
            ],
        }

        creature = Creature.model_validate(creature_data)
        header = creature.get_legendary_actions_header()

        assert header is not None
        header_text = header[0]

        # Should use singular "action" not "actions"
        assert "1 legendary action" in header_text
        assert "1 legendary actions" not in header_text


class TestCreatureHelpersIntegration:
    """Integration tests combining multiple helper methods."""

    def setup_method(self) -> None:
        reset_test_environment()

    def test_helpers_work_together_named_creature(self):
        """Test that all helper methods work together for named creature."""
        creature_data = {
            "name": "Acererak the Eternal",
            "source": "TOA",
            "isNamedCreature": True,
            "size": ["M"],
            "type": "undead",
            "alignment": ["neutral evil"],
            "ac": [21],
            "hp": {"average": 285},
            "speed": {"walk": 30, "fly": 60},
            "str": 13,
            "dex": 16,
            "con": 20,
            "int": 27,
            "wis": 15,
            "cha": 20,
            "cr": "23",
            "legendaryActions": 3,
            "legendary": [
                Ability(
                    name="At-Will Spell",
                    entries=["Acererak casts a spell of 3rd level or lower."],
                ),
                Ability(name="Attack", entries=["Acererak makes one attack."]),
                Ability(
                    name="Disrupt Life", entries=["Acererak disrupts the life force."]
                ),
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Test pronoun consistency
        assert creature.get_pronoun_subject() == "they"
        assert creature.get_pronoun_object() == "them"
        assert creature.get_pronoun_possessive() == "their"

        # Test name formatting
        assert creature.get_short_name() == "Acererak"
        assert creature.get_short_name(is_title_case=True) == "Acererak"

        # Test legendary header uses proper pronouns and name
        header = creature.get_legendary_actions_header()
        assert header is not None
        header_text = header[0]
        assert "Acererak can take 3 legendary actions" in header_text
        assert "their turn" in header_text

    def test_helpers_work_together_generic_creature(self):
        """Test that all helper methods work together for generic creature."""
        creature_data = {
            "name": "Ancient Black Dragon",
            "source": "MM",
            "size": ["G"],
            "type": "dragon",
            "alignment": ["chaotic evil"],
            "ac": [22],
            "hp": {"average": 367},
            "speed": {"walk": 40, "fly": 80, "swim": 40},
            "str": 27,
            "dex": 14,
            "con": 25,
            "int": 16,
            "wis": 15,
            "cha": 19,
            "cr": "21",
            "legendary": [
                Ability(name="Detect", entries=["The dragon makes a Wisdom check."]),
                Ability(
                    name="Tail Attack", entries=["The dragon makes a tail attack."]
                ),
                Ability(name="Wing Attack", entries=["The dragon beats its wings."]),
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Test pronoun consistency
        assert creature.get_pronoun_subject() == "it"
        assert creature.get_pronoun_object() == "its"
        assert creature.get_pronoun_possessive() == "its"

        # Test name formatting with prefix
        assert creature.get_short_name() == "the ancient black dragon"
        assert creature.get_short_name(is_title_case=True) == "The Ancient Black Dragon"

        # Test legendary header uses proper pronouns and name
        header = creature.get_legendary_actions_header()
        assert header is not None
        header_text = header[0]
        assert "The Ancient Black Dragon can take 3 legendary actions" in header_text
        assert "its turn" in header_text
