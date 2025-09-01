"""Tests for rule type models (Action, Condition, Sense, Hazard, Status)."""

import pytest
from pydantic import ValidationError

from studiorum.core.models.content import Source
from studiorum.core.models.rule_types import Action, Condition, Hazard, Sense, Status


@pytest.fixture
def phb_source():
    """Standard PHB source for testing."""
    return Source(abbreviation="PHB", name="Player's Handbook", page=123)


@pytest.fixture
def xphb_source():
    """XPHB source for testing."""
    return Source(abbreviation="XPHB", name="2024 Player's Handbook", page=456)


class TestAction:
    """Tests for Action model."""

    def test_action_creation(self, phb_source):
        """Test creating a basic action."""
        action = Action(
            name="Attack",
            source=phb_source,
            entries=["Make an attack roll against a target within range."],
        )
        assert action.name == "Attack"
        assert action.source.abbreviation == "PHB"
        assert len(action.entries) == 1
        assert action.page is None

    def test_action_with_time_and_flags(self, phb_source):
        """Test creating an action with time requirements and SRD flags."""
        action = Action(
            name="Dash",
            source=phb_source,
            page=192,
            entries=["Double your speed for the turn."],
            time=[{"number": 1, "unit": "action"}],
            srd=True,
            basicRules=True,  # Use JSON field name (alias)
        )
        assert action.name == "Dash"
        assert action.page == 192
        assert action.srd is True
        assert action.basic_rules is True
        assert len(action.time) == 1
        assert action.time[0]["unit"] == "action"

    def test_action_hash_key(self, phb_source):
        """Test action hash key generation."""
        action = Action(name="Help", source=phb_source, entries=[])
        assert action.get_hash_key() == "action:Help:PHB"

    def test_action_validation_error(self, phb_source):
        """Test action validation with invalid data."""
        with pytest.raises(ValidationError):
            Action(source=phb_source, entries=[])  # Missing name should fail


class TestCondition:
    """Tests for Condition model."""

    def test_condition_creation(self, phb_source):
        """Test creating a basic condition."""
        condition = Condition(
            name="Blinded",
            source=phb_source,
            entries=[
                {
                    "type": "list",
                    "items": [
                        "A blinded creature can't see and automatically fails any ability check that requires sight.",
                        "Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage.",
                    ],
                }
            ],
        )
        assert condition.name == "Blinded"
        assert condition.source.abbreviation == "PHB"
        assert len(condition.entries) == 1

    def test_condition_with_reprints(self, phb_source):
        """Test condition with reprint references."""
        condition = Condition(
            name="Charmed",
            source=phb_source,
            page=290,
            srd=True,
            reprintedAs=["Charmed|XPHB"],  # Use JSON field name (alias)
            entries=["A charmed creature can't attack the charmer."],
        )
        assert condition.name == "Charmed"
        assert condition.reprinted_as == ["Charmed|XPHB"]
        assert condition.srd is True

    def test_condition_hash_key(self, xphb_source):
        """Test condition hash key generation."""
        condition = Condition(name="Exhaustion", source=xphb_source, entries=[])
        assert condition.get_hash_key() == "condition:Exhaustion:XPHB"


class TestSense:
    """Tests for Sense model."""

    def test_sense_creation(self, phb_source):
        """Test creating a basic sense."""
        sense = Sense(
            name="Blindsight",
            source=phb_source,
            page=183,
            entries=[
                "A creature with blindsight can perceive its surroundings without relying on sight, within a specific radius."
            ],
        )
        assert sense.name == "Blindsight"
        assert sense.page == 183
        assert len(sense.entries) == 1

    def test_sense_with_reprints(self, phb_source):
        """Test sense with reprint references."""
        sense = Sense(
            name="Darkvision",
            source=phb_source,
            srd=True,
            basicRules=True,  # Use JSON field name (alias)
            reprintedAs=["Darkvision|XPHB"],  # Use JSON field name (alias)
            entries=[
                "You can see in dim light within 60 feet as if it were bright light."
            ],
        )
        assert sense.name == "Darkvision"
        assert sense.srd is True
        assert sense.basic_rules is True
        assert len(sense.reprinted_as) == 1

    def test_sense_hash_key(self, phb_source):
        """Test sense hash key generation."""
        sense = Sense(name="Tremorsense", source=phb_source, entries=[])
        assert sense.get_hash_key() == "sense:Tremorsense:PHB"


class TestHazard:
    """Tests for Hazard model."""

    def test_hazard_creation(self):
        """Test creating a basic hazard."""
        source = Source(
            abbreviation="IDRotF", name="Icewind Dale: Rime of the Frostmaiden"
        )
        hazard = Hazard(
            name="Avalanche",
            source=source,
            page=10,
            trapHazType="WLD",  # Use JSON field name (alias)
            entries=[
                "An avalanche is a mass of snow and debris falling rapidly down a mountainside."
            ],
        )
        assert hazard.name == "Avalanche"
        assert hazard.source.abbreviation == "IDRotF"
        assert hazard.trap_haz_type == "WLD"
        assert len(hazard.entries) == 1

    def test_hazard_hash_key(self):
        """Test hazard hash key generation."""
        source = Source(abbreviation="DMG")
        hazard = Hazard(name="Falling", source=source, entries=[])
        assert hazard.get_hash_key() == "hazard:Falling:DMG"

    def test_hazard_without_type(self, phb_source):
        """Test hazard without trap_haz_type."""
        hazard = Hazard(name="Burning", source=phb_source, entries=["You are on fire."])
        assert hazard.name == "Burning"
        assert hazard.trap_haz_type is None


class TestStatus:
    """Tests for Status model."""

    def test_status_creation(self, phb_source):
        """Test creating a basic status."""
        status = Status(
            name="Concentration",
            source=phb_source,
            page=203,
            srd=True,
            basicRules=True,  # Use JSON field name (alias)
            entries=[
                "Some spells require you to maintain concentration in order to keep their magic active."
            ],
        )
        assert status.name == "Concentration"
        assert status.page == 203
        assert status.srd is True
        assert status.basic_rules is True
        assert len(status.entries) == 1

    def test_status_with_reprints(self, phb_source):
        """Test status with reprint references."""
        status = Status(
            name="Surprised",
            source=phb_source,
            reprintedAs=["Surprised|XPHB"],  # Use JSON field name (alias)
            entries=["You are caught off guard."],
        )
        assert status.name == "Surprised"
        assert len(status.reprinted_as) == 1

    def test_status_hash_key(self, xphb_source):
        """Test status hash key generation."""
        status = Status(name="Concentration", source=xphb_source, entries=[])
        assert status.get_hash_key() == "status:Concentration:XPHB"


class TestRuleTypeSourceHandling:
    """Tests for source handling across all rule types."""

    def test_string_source_conversion(self):
        """Test that string sources are properly converted."""
        action = Action(name="Test", source="PHB", entries=[])
        assert action.source.abbreviation == "PHB"
        assert action.source.name == "PHB"  # Should default to abbreviation

    def test_dict_source_conversion(self):
        """Test that dict sources are properly converted."""
        condition = Condition(
            name="Test",
            source={"abbreviation": "XPHB", "name": "2024 Player's Handbook"},
            entries=[],
        )
        assert condition.source.abbreviation == "XPHB"
        assert condition.source.name == "2024 Player's Handbook"

    def test_hash_key_consistency(self):
        """Test that hash keys are consistent across identical content."""
        source1 = Source(abbreviation="PHB")
        source2 = Source(abbreviation="PHB", name="Player's Handbook")

        action1 = Action(name="Attack", source=source1, entries=[])
        action2 = Action(name="Attack", source=source2, entries=[])

        assert action1.get_hash_key() == action2.get_hash_key()


class TestFieldAliases:
    """Tests for field aliases in rule type models."""

    def test_basic_rules_alias(self, phb_source):
        """Test basicRules field alias."""
        action = Action(
            name="Test",
            source=phb_source,
            entries=[],
            basicRules=True,  # Using JSON field name
        )
        assert action.basic_rules is True

    def test_reprinted_as_alias(self, phb_source):
        """Test reprintedAs field alias."""
        condition = Condition(
            name="Test",
            source=phb_source,
            entries=[],
            reprintedAs=["Test|XPHB"],  # Using JSON field name
        )
        assert condition.reprinted_as == ["Test|XPHB"]

    def test_trap_haz_type_alias(self, phb_source):
        """Test trapHazType field alias."""
        hazard = Hazard(
            name="Test",
            source=phb_source,
            entries=[],
            trapHazType="ENV",  # Using JSON field name
        )
        assert hazard.trap_haz_type == "ENV"
