"""Tests for spell reference parsing."""

from dnd5e.core.references import SpellReference, SpellReferenceParser


class TestSpellReferenceParser:
    """Test spell reference parsing functionality."""

    def test_extract_simple_spell_reference(self):
        """Test extracting a simple spell reference."""
        text = "The creature casts {@spell detect magic}."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 1
        assert references[0].name == "detect magic"
        assert references[0].source is None
        assert references[0].display_text is None
        assert references[0].original_tag == "{@spell detect magic}"

    def test_extract_spell_reference_with_source(self):
        """Test extracting spell reference with source."""
        text = "The lich casts {@spell finger of death|phb}."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 1
        assert references[0].name == "finger of death"
        assert references[0].source == "phb"
        assert references[0].display_text is None

    def test_extract_spell_reference_with_display_text(self):
        """Test extracting spell reference with display text."""
        text = "The wizard uses {@spell counterspell|phb|Counterspell}."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 1
        assert references[0].name == "counterspell"
        assert references[0].source == "phb"
        assert references[0].display_text == "Counterspell"

    def test_extract_multiple_spell_references(self):
        """Test extracting multiple spell references from text."""
        text = """
        The archmage can cast {@spell detect magic} and {@spell fireball|phb}.
        They also know {@spell wish|phb|Wish}.
        """
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 3
        assert references[0].name == "detect magic"
        assert references[1].name == "fireball"
        assert references[1].source == "phb"
        assert references[2].name == "wish"
        assert references[2].display_text == "Wish"

    def test_extract_no_spell_references(self):
        """Test text with no spell references."""
        text = "The creature attacks with its claws."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 0

    def test_extract_malformed_spell_reference(self):
        """Test handling of malformed spell references."""
        text = "The creature casts {@spell}."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 0

    def test_extract_spell_reference_with_many_pipes(self):
        """Test handling spell reference with unexpected number of parts."""
        text = "The creature casts {@spell magic missile|phb|Magic Missile|extra|part}."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 1
        assert references[0].name == "magic missile"
        assert references[0].source == "phb"

    def test_case_insensitive_matching(self):
        """Test that spell tag matching is case insensitive."""
        text = "The creature casts {@SPELL FIREBALL|PHB}."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 1
        assert references[0].name == "FIREBALL"
        assert references[0].source == "PHB"

    def test_multiline_text_extraction(self):
        """Test extracting spell references from multiline text."""
        text = """
        Spellcasting. The archmage is an 18th-level spellcaster.
        It can cast {@spell detect magic} at will.

        1st level (4 slots): {@spell magic missile|phb}, {@spell shield|phb}
        2nd level (3 slots): {@spell misty step|phb}
        """
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 4
        spell_names = [ref.name for ref in references]
        assert "detect magic" in spell_names
        assert "magic missile" in spell_names
        assert "shield" in spell_names
        assert "misty step" in spell_names

    def test_whitespace_handling(self):
        """Test that whitespace around spell references is handled correctly."""
        text = "The creature casts {@spell  detect magic  |  phb  |  Display Text  }."
        references = SpellReferenceParser.extract_spell_references(text)

        assert len(references) == 1
        assert references[0].name == "detect magic"
        assert references[0].source == "phb"
        assert references[0].display_text == "Display Text"


class TestSpellReference:
    """Test SpellReference class functionality."""

    def test_spell_reference_str_simple(self):
        """Test string representation of simple spell reference."""
        ref = SpellReference(name="fireball")
        assert str(ref) == "fireball"

    def test_spell_reference_str_with_source(self):
        """Test string representation with source."""
        ref = SpellReference(name="fireball", source="phb")
        assert str(ref) == "fireball (phb)"

    def test_spell_reference_str_with_display_text(self):
        """Test string representation with display text."""
        ref = SpellReference(name="fireball", source="phb", display_text="Fireball")
        assert str(ref) == "Fireball"

    def test_spell_reference_str_display_text_overrides_source(self):
        """Test that display text takes precedence over source in string representation."""
        ref = SpellReference(
            name="fireball", source="phb", display_text="Fire Explosion"
        )
        assert str(ref) == "Fire Explosion"
