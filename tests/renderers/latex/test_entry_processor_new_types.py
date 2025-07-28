"""Tests for LaTeX entry processor new entry types."""

from unittest.mock import Mock

from dnd5e.renderers.base import RenderContext
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor


class TestNewEntryTypes:
    """Test new entry types added for issue #89."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = RecursiveEntryProcessor(use_dnd_template=True)
        self.context = RenderContext()

        # Mock tag resolver to return escaped text
        mock_tag_resolver = Mock()
        mock_tag_resolver.process_text = Mock(side_effect=lambda x: f"processed_{x}")
        self.context.tag_resolver = mock_tag_resolver

    def test_process_entry_dict_actions(self):
        """Test processing actions entry."""
        entry = {
            "type": "actions",
            "name": "Multiattack",
            "entries": ["The creature makes two weapon attacks."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Multiattack.}" in result
        assert "processed_The creature makes two weapon attacks." in result

    def test_process_entry_dict_actions_no_name(self):
        """Test processing actions entry without name."""
        entry = {"type": "actions", "entries": ["The creature attacks."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_The creature attacks." in result
        assert "\\textbf{" not in result

    def test_process_entry_dict_attack(self):
        """Test processing attack entry."""
        entry = {
            "type": "attack",
            "name": "Longsword",
            "entries": [
                "{@atk mw} {@hit 7} to hit, reach 5 ft., one target. {@h}11 ({@damage 2d8 + 2}) slashing damage."
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textit{Longsword.}" in result
        assert "processed_{@atk mw} {@hit 7} to hit" in result

    def test_process_entry_dict_attack_no_name(self):
        """Test processing attack entry without name."""
        entry = {"type": "attack", "entries": ["{@atk mw} {@hit 5} to hit."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_{@atk mw} {@hit 5} to hit." in result
        assert "\\textit{" not in result

    def test_process_entry_dict_options(self):
        """Test processing options entry."""
        entry = {
            "type": "options",
            "entries": [
                {
                    "type": "entries",
                    "name": "Option 1",
                    "entries": ["First choice description"],
                },
                {
                    "type": "entries",
                    "name": "Option 2",
                    "entries": ["Second choice description"],
                },
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\begin{itemize}" in result
        assert "\\item \\subsection{Option 1}" in result
        assert "\\item \\subsection{Option 2}" in result
        assert "processed_First choice description" in result
        assert "processed_Second choice description" in result
        assert "\\end{itemize}" in result

    def test_process_entry_dict_options_empty(self):
        """Test processing empty options entry."""
        entry = {"type": "options", "entries": []}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == ""

    def test_process_entry_dict_variant(self):
        """Test processing variant entry."""
        entry = {
            "type": "variant",
            "name": "Optional Rule",
            "entries": ["This variant rule changes how combat works."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Variant: Optional Rule}" in result
        assert "processed_This variant rule changes how combat works." in result

    def test_process_entry_dict_variant_no_name(self):
        """Test processing variant entry without name."""
        entry = {"type": "variant", "entries": ["This is a variant rule."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Variant:}" in result
        assert "processed_This is a variant rule." in result

    def test_process_entry_dict_variant_sub(self):
        """Test processing variantSub entry."""
        entry = {
            "type": "variantSub",
            "name": "Sub-variant",
            "entries": ["This is a sub-variant of the main rule."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textit{Sub-variant:}" in result
        assert "processed_This is a sub-variant of the main rule." in result

    def test_process_entry_dict_variant_sub_no_name(self):
        """Test processing variantSub entry without name."""
        entry = {"type": "variantSub", "entries": ["A sub-variant rule."]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_A sub-variant rule." in result
        assert "\\textit{" not in result

    def test_process_entry_dict_ability_dc(self):
        """Test processing abilityDc entry."""
        entry = {"type": "abilityDc", "name": "Spell Save DC", "attributes": ["cha"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Spell Save DC:}" in result
        assert "8 + proficiency bonus + Charisma modifier" in result

    def test_process_entry_dict_ability_dc_no_name(self):
        """Test processing abilityDc entry without name."""
        entry = {"type": "abilityDc", "attributes": ["wis"]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Save DC:}" in result
        assert "8 + proficiency bonus + Wisdom modifier" in result

    def test_process_entry_dict_ability_attack_mod(self):
        """Test processing abilityAttackMod entry."""
        entry = {
            "type": "abilityAttackMod",
            "name": "Spell Attack Bonus",
            "attributes": ["int"],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Spell Attack Bonus:}" in result
        assert "proficiency bonus + Intelligence modifier" in result

    def test_process_entry_dict_ability_generic(self):
        """Test processing abilityGeneric entry."""
        entry = {
            "type": "abilityGeneric",
            "name": "Special Ability",
            "text": "+{@mod str} to damage rolls",
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Special Ability:}" in result
        assert "processed_+{@mod str} to damage rolls" in result

    def test_process_entry_dict_spellcasting(self):
        """Test processing spellcasting entry."""
        entry = {
            "type": "spellcasting",
            "name": "Spellcasting",
            "headerEntries": ["The creature is an 11th-level spellcaster."],
            "spells": {
                "0": {"spells": ["{@spell mage hand}", "{@spell minor illusion}"]},
                "1": {
                    "slots": 4,
                    "spells": ["{@spell magic missile}", "{@spell shield}"],
                },
            },
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Spellcasting.}" in result
        assert "processed_The creature is an 11th-level spellcaster." in result
        assert "\\textbf{Cantrips (at will):}" in result
        assert "processed_{@spell mage hand}" in result
        assert "\\textbf{1st level (4 slots):}" in result
        assert "processed_{@spell magic missile}" in result

    def test_process_entry_dict_bonus(self):
        """Test processing bonus entry."""
        entry = {"type": "bonus", "value": 2}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "+2"

    def test_process_entry_dict_bonus_negative(self):
        """Test processing negative bonus entry."""
        entry = {"type": "bonus", "value": -1}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "-1"

    def test_process_entry_dict_bonus_speed(self):
        """Test processing bonusSpeed entry."""
        entry = {"type": "bonusSpeed", "value": 10}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "+10 ft."

    def test_process_entry_dict_dice(self):
        """Test processing dice entry."""
        entry = {"type": "dice", "toRoll": [{"number": 2, "faces": 6, "modifier": 3}]}
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "2d6+3"

    def test_process_entry_dict_dice_multiple(self):
        """Test processing dice entry with multiple dice."""
        entry = {
            "type": "dice",
            "toRoll": [
                {"number": 1, "faces": 8},
                {"number": 2, "faces": 4, "modifier": -1},
            ],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert result == "1d8, 2d4-1"

    def test_process_entry_dict_item_simple(self):
        """Test processing item entry as simple string."""
        entry = {
            "type": "item",
            "name": "Simple Item",
            "entry": "This is a simple list item.",
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Simple Item.}" in result
        assert "processed_This is a simple list item." in result

    def test_process_entry_dict_item_with_entries(self):
        """Test processing item entry with nested entries."""
        entry = {
            "type": "item",
            "name": "Complex Item",
            "entries": ["First paragraph.", "Second paragraph."],
        }
        result = self.processor.process_entry_dict(entry, self.context)

        assert "\\textbf{Complex Item.}" in result
        assert "processed_First paragraph." in result
        assert "processed_Second paragraph." in result

    def test_process_entry_dict_item_no_name(self):
        """Test processing item entry without name."""
        entry = {"type": "item", "entry": "Unnamed item content."}
        result = self.processor.process_entry_dict(entry, self.context)

        assert "processed_Unnamed item content." in result
