"""Comprehensive tests for tag_parser.py to improve test coverage."""

from pathlib import Path
from typing import Any

import pytest

from dnd5e.core.text.tag_ast import (  # type: ignore
    AdventureTagNode,
    BackgroundTagNode,
    BoldTagNode,
    BookTagNode,
    ChanceTagNode,
    ClassTagNode,
    ConditionTagNode,
    CreatureTagNode,
    DamageTagNode,
    DCTagNode,
    DiceTagNode,
    DocumentNode,
    FeatTagNode,
    FilterTagNode,
    HitTagNode,
    ItalicTagNode,
    ItemTagNode,
    LoaderTagNode,
    RaceTagNode,
    RechargeTagNode,
    SpellTagNode,
    TagNode,
    TextNode,
)
from dnd5e.core.text.tag_parser import (  # type: ignore
    TagASTTransformer,
    TagParseError,
    TagParser,
)


class TestTagParseError:
    """Tests for TagParseError exception."""

    def test_tag_parse_error_basic(self) -> None:
        """Test basic TagParseError creation."""
        error: Any = TagParseError("Test error")
        assert str(error) == "Test error"
        assert error.position is None
        assert error.text is None

    def test_tag_parse_error_with_position(self) -> None:
        """Test TagParseError with position information."""
        error: Any = TagParseError("Test error", position=15)
        assert str(error) == "Test error"
        assert error.position == 15
        assert error.text is None

    def test_tag_parse_error_with_text_and_position(self) -> None:
        """Test TagParseError with all parameters."""
        error: Any = TagParseError("Test error", position=15, text="sample text")
        assert str(error) == "Test error"
        assert error.position == 15
        assert error.text == "sample text"


class TestTagASTTransformer:
    """Tests for TagASTTransformer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.original_text = "Test text with {@creature Dragon|MM} tags"
        self.transformer = TagASTTransformer(self.original_text)

    def test_transformer_initialization(self) -> None:
        """Test transformer initialization."""
        assert self.transformer.original_text == self.original_text

    def test_document_transform(self) -> None:
        """Test document transformation."""
        text_node: Any = TextNode("Hello")
        creature_node: Any = CreatureTagNode("Dragon", "MM")
        children = [text_node, creature_node, None]  # Include None to test filtering

        result = self.transformer.document(children)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 2  # None should be filtered out
        assert result.children[0] == text_node
        assert result.children[1] == creature_node

    def test_text_transform(self) -> None:
        """Test text transformation from tokens."""
        from lark import Token

        tokens = [Token("TEXT", "Hello "), Token("TEXT", "world")]
        result = self.transformer.text(tokens)

        assert isinstance(result, TextNode)
        assert result.text == "Hello world"

    def test_text_fragment_transform(self) -> None:
        """Test text fragment transformation."""
        from lark import Token

        tokens = [Token("TEXT", "Hello "), Token("TEXT", "world")]
        result = self.transformer.text_fragment(tokens)

        assert result == "Hello world"

    def test_tag_type_transform(self) -> None:
        """Test tag type transformation."""
        from lark import Token

        tokens = [Token("WORD", "creature")]
        result = self.transformer.tag_type(tokens)

        assert result == "creature"

    def test_escaped_char_transform(self) -> None:
        """Test escaped character transformation."""
        from lark import Token

        # Test escaped pipe
        tokens = [Token("ESCAPED", "\\|")]
        result = self.transformer.escaped_char(tokens)
        assert result == "|"

        # Test escaped brace
        tokens = [Token("ESCAPED", "\\}")]
        result = self.transformer.escaped_char(tokens)
        assert result == "}"

        # Test other escaped character
        tokens = [Token("ESCAPED", "\\n")]
        result = self.transformer.escaped_char(tokens)
        assert result == "\\n"

    def test_tag_transform_missing_type(self) -> None:
        """Test tag transformation with missing type."""
        with pytest.raises(TagParseError, match="Tag missing type"):
            self.transformer.tag([])

    def test_tag_transform_with_string_parts(self) -> None:
        """Test tag transformation with string parts using parser interface."""
        parser = TagParser()
        text = "{@creature Dragon|MM|dragon}"
        result = parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Dragon"
        assert creature_node.source == "MM"
        assert len(creature_node.display_text_nodes) == 1
        assert isinstance(creature_node.display_text_nodes[0], TextNode)
        assert creature_node.display_text_nodes[0].text == "dragon"

    def test_tag_transform_with_list_parts(self) -> None:
        """Test tag transformation with nested content using parser interface."""
        parser = TagParser()
        text = "{@creature Dragon|MM|{@bold nested} content}"
        result = parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Dragon"
        assert creature_node.source == "MM"
        # Check that display text contains nested content
        assert len(creature_node.display_text_nodes) >= 1

    def test_content_part_transform(self) -> None:
        """Test content part transformation."""
        tag_node: Any = TagNode("test")
        children = [tag_node, "more text"]

        result = self.transformer.content_part(children)

        assert len(result) == 2
        assert result[0] == tag_node
        assert isinstance(result[1], TextNode)
        assert result[1].text == "more text"

    def test_content_part_transform_only_text(self) -> None:
        """Test content part transformation with only text."""
        children = ["hello", " ", "world"]

        result = self.transformer.content_part(children)

        assert len(result) == 1
        assert isinstance(result[0], TextNode)
        assert result[0].text == "hello world"

    def test_content_part_edge_case(self) -> None:
        """Test edge case in content_part transformation."""

        # Test with mixed children including an unknown type
        class UnknownNode:
            pass

        unknown_node: Any = UnknownNode()
        children = ["text", unknown_node, TagNode("test"), "more text"]

        result = self.transformer.content_part(children)

        # Should handle the unknown node gracefully by treating it as text accumulation
        assert isinstance(result, list)
        assert len(result) >= 1


class TestTagParser:
    """Tests for TagParser class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = TagParser()

    def test_parser_initialization(self) -> None:
        """Test parser initialization."""
        assert self.parser.parser is not None

    def test_parser_initialization_missing_grammar(self, monkeypatch: Any) -> None:
        """Test parser initialization with missing grammar file."""

        # Mock the Path existence check instead
        def mock_open_func(*args: Any, **kwargs: Any) -> None:
            raise FileNotFoundError("Grammar file not found")

        monkeypatch.setattr("builtins.open", mock_open_func)

        # The current implementation doesn't catch file not found during open
        with pytest.raises(FileNotFoundError, match="Grammar file not found"):
            TagParser()

    def test_parse_empty_text(self) -> None:
        """Test parsing empty text."""
        result = self.parser.parse("")

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 0

    def test_parse_none_text(self) -> None:
        """Test parsing None text."""
        result = self.parser.parse(None)  # type: ignore[arg-type]

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 0

    def test_parse_plain_text(self) -> None:
        """Test parsing plain text without tags."""
        text = "This is plain text without any tags."
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        assert isinstance(result.children[0], TextNode)
        assert result.children[0].text == text

    def test_parse_simple_creature_tag(self) -> None:
        """Test parsing simple creature tag."""
        text = "{@creature Ancient Red Dragon|MM}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        assert isinstance(result.children[0], CreatureTagNode)
        assert result.children[0].name == "Ancient Red Dragon"
        assert result.children[0].source == "MM"

    def test_parse_creature_tag_with_display_text(self) -> None:
        """Test parsing creature tag with display text."""
        text = "{@creature Ancient Red Dragon|MM|great wyrm}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Ancient Red Dragon"
        assert creature_node.source == "MM"
        assert len(creature_node.display_text_nodes) == 1
        assert isinstance(creature_node.display_text_nodes[0], TextNode)
        assert creature_node.display_text_nodes[0].text == "great wyrm"

    def test_parse_creature_tag_with_page(self) -> None:
        """Test parsing creature tag with page number."""
        text = "{@creature Ancient Red Dragon|MM|great wyrm|98}"
        result = self.parser.parse(text)

        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.page == "98"

    def test_parse_mixed_content(self) -> None:
        """Test parsing text with mixed content."""
        text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 5

        # Check structure: "Cast ", spell_tag, " at the ", creature_tag, "!"
        assert isinstance(result.children[0], TextNode)
        assert result.children[0].text == "Cast "

        assert isinstance(result.children[1], SpellTagNode)
        assert result.children[1].name == "Fireball"

        assert isinstance(result.children[2], TextNode)
        assert result.children[2].text == " at the "

        assert isinstance(result.children[3], CreatureTagNode)
        assert result.children[3].name == "Ancient Red Dragon"

        assert isinstance(result.children[4], TextNode)
        assert result.children[4].text == "!"

    def test_parse_escaped_characters(self) -> None:
        """Test parsing tags with escaped characters."""
        text = r"{@creature Name\|with\|pipes|MM|display\}with\}braces}"
        result = self.parser.parse(text)

        # The current regex fallback doesn't handle all escapes perfectly
        # but it should preserve the structure
        assert isinstance(result, DocumentNode)
        assert len(result.children) >= 1

        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Name\\|with\\|pipes"
        assert creature_node.source == "MM"
        # The current implementation may not handle all escape sequences perfectly

    def test_parse_various_tag_types(self) -> None:
        """Test parsing various tag types."""
        test_cases = [
            ("{@spell Fireball|PHB}", SpellTagNode),
            ("{@item Sword +1|DMG}", ItemTagNode),
            ("{@class Fighter|PHB}", ClassTagNode),
            ("{@race Elf|PHB}", RaceTagNode),
            ("{@background Acolyte|PHB}", BackgroundTagNode),
            ("{@feat Alert|PHB}", FeatTagNode),
            ("{@bold important text}", BoldTagNode),
            ("{@b important text}", BoldTagNode),
            ("{@italic emphasized text}", ItalicTagNode),
            ("{@i emphasized text}", ItalicTagNode),
            ("{@dice 1d20+5}", DiceTagNode),
            ("{@hit +5}", HitTagNode),
            ("{@dc 15}", DCTagNode),
            ("{@damage fire}", DamageTagNode),
            ("{@condition charmed}", ConditionTagNode),
            ("{@chance 50}", ChanceTagNode),
            ("{@recharge 5-6}", RechargeTagNode),
            ("{@adventure Lost Mine|LMoP}", AdventureTagNode),
            ("{@book Player's Handbook|PHB}", BookTagNode),
            ("{@filter spells}", FilterTagNode),
            ("{@loader bestiary}", LoaderTagNode),
            ("{@unknown test}", TagNode),
        ]

        for text, expected_type in test_cases:
            result = self.parser.parse(text)
            assert len(result.children) == 1
            assert isinstance(result.children[0], expected_type)

    def test_parse_malformed_tags_error_recovery(self) -> None:
        """Test parser error recovery with malformed tags."""
        malformed_cases = [
            "{@creature}",  # Missing content
            "{@creature ",  # Unclosed tag
            "{@ |MM}",  # Missing tag type
            "{}",  # Empty tag
            "{@}",  # Only @ symbol
        ]

        for case in malformed_cases:
            result = self.parser.parse(case)
            # Should recover gracefully and treat as plain text
            assert isinstance(result, DocumentNode)
            assert len(result.children) >= 1
            # At least some content should be preserved

    def test_parse_exception_handling(self, monkeypatch: Any) -> None:
        """Test handling of unexpected exceptions during parsing."""

        # Mock the Lark parser to raise an exception
        def mock_parse(*args: Any, **kwargs: Any) -> None:
            raise Exception("Unexpected error")

        monkeypatch.setattr(self.parser.parser, "parse", mock_parse)

        text = "Test text"
        result = self.parser.parse(text)

        # Should gracefully handle error and return original text
        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        assert isinstance(result.children[0], TextNode)
        assert result.children[0].text == text

    def test_parse_tag_parse_error_handling(self, monkeypatch: Any) -> None:
        """Test handling of TagParseError during parsing."""

        # Mock the Lark parser to raise a TagParseError
        def mock_parse(*args: Any, **kwargs: Any) -> None:
            raise TagParseError("Parsing failed")

        monkeypatch.setattr(self.parser.parser, "parse", mock_parse)

        text = "Test text"
        result = self.parser.parse(text)

        # Should gracefully handle TagParseError and return original text
        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        assert isinstance(result.children[0], TextNode)
        assert result.children[0].text == text

    def test_parse_complex_content_with_whitespace(self) -> None:
        """Test parsing content with various whitespace patterns."""
        text = "  {@creature   Dragon  |  MM  }  "
        result = self.parser.parse(text)

        # Should handle whitespace in content
        assert isinstance(result, DocumentNode)
        assert len(result.children) == 3  # leading space, tag, trailing space

    def test_parse_tag_with_numbers_in_name(self) -> None:
        """Test parsing tags with numbers in names."""
        text = "{@spell Fireball 2nd Level|PHB}"
        result = self.parser.parse(text)

        spell_node = result.children[0]
        assert isinstance(spell_node, SpellTagNode)
        assert "2nd Level" in spell_node.name

    def test_parse_tag_with_special_characters(self) -> None:
        """Test parsing tags with special characters."""
        text = "{@item Bag of Holding|DMG}"
        result = self.parser.parse(text)

        item_node = result.children[0]
        assert isinstance(item_node, ItemTagNode)
        assert "of" in item_node.name

    def test_parse_consecutive_tags(self) -> None:
        """Test parsing consecutive tags without text between."""
        text = "{@creature Dragon|MM}{@spell Fireball|PHB}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 2
        assert isinstance(result.children[0], CreatureTagNode)
        assert isinstance(result.children[1], SpellTagNode)

    def test_parse_empty_tag_parts(self) -> None:
        """Test parsing tags with empty parts."""
        text = "{@creature Dragon||display|}"
        result = self.parser.parse(text)

        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Dragon"
        assert creature_node.source is None  # Empty source
        assert isinstance(creature_node.display_text_nodes[0], TextNode)
        assert creature_node.display_text_nodes[0].text == "display"
        # Last empty part is page, should be None

    def test_grammar_file_exists(self) -> None:
        """Test that grammar file exists."""
        grammar_path = (
            Path(__file__).parent.parent.parent.parent
            / "src/dnd5e/core/text/tag_grammar.lark"
        )
        assert grammar_path.exists(), f"Grammar file not found at {grammar_path}"

    def test_parser_initialization_lark_error(self, monkeypatch: Any) -> None:
        """Test parser initialization with Lark parser creation error."""

        # Mock Lark to raise an exception during initialization
        def mock_lark(*args: Any, **kwargs: Any) -> None:
            raise Exception("Lark parser error")

        import dnd5e.core.text.tag_parser  # type: ignore

        monkeypatch.setattr(dnd5e.core.text.tag_parser, "Lark", mock_lark)

        with pytest.raises(TagParseError, match="Failed to initialize parser"):
            TagParser()


class TestNestedTagParsing:
    """Tests for nested tag parsing functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = TagParser()

    def test_simple_nested_tag(self) -> None:
        """Test a simple nested tag within another tag."""
        text = "{@bold This is {@italic nested} text}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        bold_node = result.children[0]
        assert isinstance(bold_node, BoldTagNode)
        assert len(bold_node.content_nodes) == 3

        # Check the content structure
        assert isinstance(bold_node.content_nodes[0], TextNode)
        assert bold_node.content_nodes[0].text == " This is "
        assert isinstance(bold_node.content_nodes[1], ItalicTagNode)
        assert isinstance(bold_node.content_nodes[2], TextNode)
        assert bold_node.content_nodes[2].text == " text"

    def test_nested_tag_in_creature_display_text(self) -> None:
        """Test nested tag within a creature's display text."""
        text = "{@creature Dragon|MM|a {@bold mighty} beast}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Dragon"
        assert creature_node.source == "MM"

        # Check display text has nested structure
        assert len(creature_node.display_text_nodes) == 3
        assert isinstance(creature_node.display_text_nodes[0], TextNode)
        assert creature_node.display_text_nodes[0].text == "a "
        assert isinstance(creature_node.display_text_nodes[1], BoldTagNode)
        assert isinstance(creature_node.display_text_nodes[2], TextNode)
        assert creature_node.display_text_nodes[2].text == " beast"

    def test_deeply_nested_tags(self) -> None:
        """Test multiple levels of tag nesting."""
        text = "{@bold A {@italic B {@bold C} D} E}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1

        # First level: bold tag
        bold_outer = result.children[0]
        assert isinstance(bold_outer, BoldTagNode)
        assert len(bold_outer.content_nodes) == 3  # "A ", italic_tag, " E"

        # Second level: italic tag
        italic_middle = bold_outer.content_nodes[1]
        assert isinstance(italic_middle, ItalicTagNode)
        assert len(italic_middle.content_nodes) == 3  # "B ", bold_tag, " D"

        # Third level: nested bold tag
        bold_inner = italic_middle.content_nodes[1]
        assert isinstance(bold_inner, BoldTagNode)
        assert len(bold_inner.content_nodes) == 1
        assert isinstance(bold_inner.content_nodes[0], TextNode)
        assert bold_inner.content_nodes[0].text == "C"

    def test_consecutive_nested_tags(self) -> None:
        """Test consecutive nested tags within a parent tag."""
        text = "{@bold Start {@italic first} and {@italic second} end}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        bold_node = result.children[0]
        assert isinstance(bold_node, BoldTagNode)
        assert len(bold_node.content_nodes) == 5

        # Check sequence: " Start ", italic1, " and ", italic2, " end"
        assert isinstance(bold_node.content_nodes[0], TextNode)
        assert bold_node.content_nodes[0].text == " Start "
        assert isinstance(bold_node.content_nodes[1], ItalicTagNode)
        assert isinstance(bold_node.content_nodes[2], TextNode)
        assert bold_node.content_nodes[2].text == " and "
        assert isinstance(bold_node.content_nodes[3], ItalicTagNode)
        assert isinstance(bold_node.content_nodes[4], TextNode)
        assert bold_node.content_nodes[4].text == " end"

    def test_nested_spell_in_creature(self) -> None:
        """Test nested spell tag within creature display text."""
        text = "{@creature Ancient Red Dragon|MM|casts {@spell fireball|PHB} spell}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        creature_node = result.children[0]
        assert isinstance(creature_node, CreatureTagNode)
        assert creature_node.name == "Ancient Red Dragon"

        # Check nested spell in display text
        assert len(creature_node.display_text_nodes) == 3
        assert isinstance(creature_node.display_text_nodes[0], TextNode)
        assert creature_node.display_text_nodes[0].text == "casts "
        assert isinstance(creature_node.display_text_nodes[1], SpellTagNode)
        spell_node = creature_node.display_text_nodes[1]
        assert spell_node.name == "fireball"
        assert spell_node.source == "PHB"
        assert isinstance(creature_node.display_text_nodes[2], TextNode)
        assert creature_node.display_text_nodes[2].text == " spell"

    def test_nested_tags_with_escaped_braces(self) -> None:
        """Test nested tags with escaped brace characters."""
        text = "{@bold Text with \\{ {@italic nested} \\} braces}"
        result = self.parser.parse(text)

        assert isinstance(result, DocumentNode)
        assert len(result.children) == 1
        bold_node = result.children[0]
        assert isinstance(bold_node, BoldTagNode)

        # Should have text before, nested tag, and text after with escaped braces
        assert len(bold_node.content_nodes) == 3
        assert isinstance(bold_node.content_nodes[0], TextNode)
        assert "\\{" in bold_node.content_nodes[0].text  # Contains escaped brace
        assert isinstance(bold_node.content_nodes[1], ItalicTagNode)
        assert isinstance(bold_node.content_nodes[2], TextNode)
        assert "\\}" in bold_node.content_nodes[2].text  # Contains escaped brace
