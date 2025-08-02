"""Comprehensive tests for Pydantic tag types models."""

from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from dnd5e.core.indexer.tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagContext,
    TagResolutionResult,
)
from dnd5e.core.models.content import BaseContent, ContentType, Source


class TestFormatType:
    """Tests for FormatType enum."""

    def test_format_type_values(self) -> None:
        """Test FormatType enum values."""
        assert FormatType.BOLD == "bold"
        assert FormatType.ITALIC == "italic"
        assert FormatType.MONOSPACE == "monospace"
        assert FormatType.EMPHASIS == "emphasis"

    def test_format_type_membership(self) -> None:
        """Test FormatType membership checks."""
        assert "bold" in FormatType
        assert "italic" in FormatType
        assert "invalid" not in FormatType


class TestContentReference:
    """Tests for ContentReference Pydantic model."""

    @pytest.fixture
    def mock_content(self) -> BaseContent:
        """Create mock BaseContent for testing."""
        content = Mock(spec=BaseContent)
        content.name = "Test Content"
        content.source = Source(abbreviation="TEST", name="Test Source")
        return content

    def test_content_reference_creation_minimal(self) -> None:
        """Test creating ContentReference with minimal required fields."""
        ref = ContentReference(content_type=ContentType.CREATURE, name="Dragon")

        assert ref.content_type == ContentType.CREATURE
        assert ref.name == "Dragon"
        assert ref.source is None
        assert ref.display_text is None
        assert ref.page is None
        assert ref.resolved_content is None

    def test_content_reference_creation_full(self, mock_content: BaseContent) -> None:
        """Test creating ContentReference with all fields."""
        ref = ContentReference(
            content_type=ContentType.SPELL,
            name="Fireball",
            source="PHB",
            display_text="powerful fireball",
            page="251",
            resolved_content=mock_content,
        )

        assert ref.content_type == ContentType.SPELL
        assert ref.name == "Fireball"
        assert ref.source == "PHB"
        assert ref.display_text == "powerful fireball"
        assert ref.page == "251"
        assert ref.resolved_content == mock_content

    def test_content_reference_name_validation(self) -> None:
        """Test name field validation."""
        # Valid name
        ref = ContentReference(content_type=ContentType.CREATURE, name="Dragon")
        assert ref.name == "Dragon"

        # Name with whitespace gets stripped
        ref = ContentReference(content_type=ContentType.CREATURE, name="  Dragon  ")
        assert ref.name == "Dragon"

        # Empty name should fail due to min_length constraint
        with pytest.raises(ValidationError) as exc_info:
            ContentReference(content_type=ContentType.CREATURE, name="")
        assert "at least 1 character" in str(exc_info.value)

        # Whitespace-only name gets stripped to empty but doesn't fail validation
        # (the min_length constraint applies before the validator runs)
        ref = ContentReference(content_type=ContentType.CREATURE, name="   ")
        assert ref.name == ""  # Gets stripped to empty string

    def test_content_reference_source_validation(self) -> None:
        """Test source field validation."""
        # Valid source
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", source="PHB"
        )
        assert ref.source == "PHB"

        # Source with whitespace gets stripped
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", source="  PHB  "
        )
        assert ref.source == "PHB"

        # Empty source becomes None
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", source=""
        )
        assert ref.source is None

        # Whitespace-only source becomes None
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", source="   "
        )
        assert ref.source is None

        # None source remains None
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", source=None
        )
        assert ref.source is None

    def test_content_reference_display_text_validation(self) -> None:
        """Test display_text field validation."""
        # Valid display text
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            display_text="mighty dragon",
        )
        assert ref.display_text == "mighty dragon"

        # Display text with whitespace gets stripped
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            display_text="  mighty dragon  ",
        )
        assert ref.display_text == "mighty dragon"

        # Empty display text becomes None
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", display_text=""
        )
        assert ref.display_text is None

        # Whitespace-only display text becomes None
        ref = ContentReference(
            content_type=ContentType.CREATURE, name="Dragon", display_text="   "
        )
        assert ref.display_text is None

    def test_content_reference_is_resolved_property(
        self, mock_content: BaseContent
    ) -> None:
        """Test is_resolved property."""
        # Unresolved reference
        ref = ContentReference(content_type=ContentType.CREATURE, name="Dragon")
        assert not ref.is_resolved

        # Resolved reference
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            resolved_content=mock_content,
        )
        assert ref.is_resolved

    def test_content_reference_effective_name_property(self) -> None:
        """Test effective_name property."""
        # No display text - uses name
        ref = ContentReference(content_type=ContentType.CREATURE, name="Dragon")
        assert ref.effective_name == "Dragon"

        # With display text - uses display text
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            display_text="mighty dragon",
        )
        assert ref.effective_name == "mighty dragon"

    def test_content_reference_str_method(self, mock_content: BaseContent) -> None:
        """Test __str__ method."""
        # Unresolved reference
        ref = ContentReference(content_type=ContentType.CREATURE, name="Dragon")
        assert str(ref) == "Dragon"

        # Unresolved with display text
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            display_text="mighty dragon",
        )
        assert str(ref) == "mighty dragon"

        # Resolved reference
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            resolved_content=mock_content,
        )
        assert str(ref) == "Dragon (TEST)"

    def test_content_reference_frozen_config(self) -> None:
        """Test that ContentReference is frozen (immutable)."""
        ref = ContentReference(content_type=ContentType.CREATURE, name="Dragon")

        with pytest.raises(ValidationError):
            ref.name = "New Name"

        with pytest.raises(ValidationError):
            ref.content_type = ContentType.SPELL

    def test_content_reference_arbitrary_types_allowed(
        self, mock_content: BaseContent
    ) -> None:
        """Test that arbitrary types are allowed for resolved_content."""
        # Should accept mock objects or other complex types
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            resolved_content=mock_content,
        )
        assert ref.resolved_content == mock_content


class TestFormattingNode:
    """Tests for FormattingNode Pydantic model."""

    def test_formatting_node_creation(self) -> None:
        """Test creating FormattingNode."""
        node = FormattingNode(format_type=FormatType.BOLD, content="bold text")

        assert node.format_type == FormatType.BOLD
        assert node.content == "bold text"

    def test_formatting_node_content_validation(self) -> None:
        """Test content field validation."""
        # Valid content
        node = FormattingNode(format_type=FormatType.ITALIC, content="italic text")
        assert node.content == "italic text"

        # Content with whitespace gets stripped
        node = FormattingNode(format_type=FormatType.ITALIC, content="  italic text  ")
        assert node.content == "italic text"

        # Empty content should fail due to min_length constraint
        with pytest.raises(ValidationError) as exc_info:
            FormattingNode(format_type=FormatType.BOLD, content="")
        assert "at least 1 character" in str(exc_info.value)

        # Whitespace-only content gets stripped to empty but doesn't fail validation
        # (the min_length constraint applies before the validator runs)
        node = FormattingNode(format_type=FormatType.BOLD, content="   ")
        assert node.content == ""  # Gets stripped to empty string

    def test_formatting_node_str_method(self) -> None:
        """Test __str__ method."""
        node = FormattingNode(format_type=FormatType.BOLD, content="bold text")
        assert str(node) == "bold(bold text)"

        node = FormattingNode(format_type=FormatType.ITALIC, content="italic text")
        assert str(node) == "italic(italic text)"

    def test_formatting_node_frozen_config(self) -> None:
        """Test that FormattingNode is frozen (immutable)."""
        node = FormattingNode(format_type=FormatType.BOLD, content="bold text")

        with pytest.raises(ValidationError):
            node.content = "new content"

        with pytest.raises(ValidationError):
            node.format_type = FormatType.ITALIC

    @pytest.mark.parametrize(
        "format_type",
        [FormatType.BOLD, FormatType.ITALIC, FormatType.MONOSPACE, FormatType.EMPHASIS],
    )
    def test_formatting_node_all_format_types(self, format_type: FormatType) -> None:
        """Test FormattingNode with all format types."""
        node = FormattingNode(format_type=format_type, content="test content")
        assert node.format_type == format_type
        assert node.content == "test content"


class TestSpecialTag:
    """Tests for SpecialTag Pydantic model."""

    def test_special_tag_creation_minimal(self) -> None:
        """Test creating SpecialTag with minimal fields."""
        tag = SpecialTag(tag_type="dice", value="1d6")

        assert tag.tag_type == "dice"
        assert tag.value == "1d6"
        assert tag.display_text is None
        assert tag.metadata is None

    def test_special_tag_creation_full(self) -> None:
        """Test creating SpecialTag with all fields."""
        metadata = {"sides": 6, "count": 1}
        tag = SpecialTag(
            tag_type="dice", value="1d6", display_text="roll a die", metadata=metadata
        )

        assert tag.tag_type == "dice"
        assert tag.value == "1d6"
        assert tag.display_text == "roll a die"
        assert tag.metadata == metadata

    def test_special_tag_tag_type_validation(self) -> None:
        """Test tag_type field validation."""
        # Valid tag type
        tag = SpecialTag(tag_type="dice", value="1d6")
        assert tag.tag_type == "dice"

        # Tag type gets normalized to lowercase
        tag = SpecialTag(tag_type="DICE", value="1d6")
        assert tag.tag_type == "dice"

        # Tag type with whitespace gets stripped and normalized
        tag = SpecialTag(tag_type="  DICE  ", value="1d6")
        assert tag.tag_type == "dice"

        # Empty tag type should fail
        with pytest.raises(ValidationError) as exc_info:
            SpecialTag(tag_type="", value="1d6")
        assert "at least 1 character" in str(exc_info.value)

        # Whitespace-only tag type should fail
        with pytest.raises(ValidationError) as exc_info:
            SpecialTag(tag_type="   ", value="1d6")
        assert "Tag type cannot be empty" in str(exc_info.value)

    def test_special_tag_value_validation(self) -> None:
        """Test value field validation."""
        # Valid value
        tag = SpecialTag(tag_type="dice", value="1d6")
        assert tag.value == "1d6"

        # Value with whitespace gets stripped
        tag = SpecialTag(tag_type="dice", value="  1d6  ")
        assert tag.value == "1d6"

        # Empty value should fail due to min_length constraint
        with pytest.raises(ValidationError) as exc_info:
            SpecialTag(tag_type="dice", value="")
        assert "at least 1 character" in str(exc_info.value)

        # Whitespace-only value gets stripped to empty but doesn't fail validation
        # (the min_length constraint applies before the validator runs)
        tag = SpecialTag(tag_type="dice", value="   ")
        assert tag.value == ""  # Gets stripped to empty string

    def test_special_tag_display_text_validation(self) -> None:
        """Test display_text field validation."""
        # Valid display text
        tag = SpecialTag(tag_type="dice", value="1d6", display_text="roll dice")
        assert tag.display_text == "roll dice"

        # Display text with whitespace gets stripped
        tag = SpecialTag(tag_type="dice", value="1d6", display_text="  roll dice  ")
        assert tag.display_text == "roll dice"

        # Empty display text becomes None
        tag = SpecialTag(tag_type="dice", value="1d6", display_text="")
        assert tag.display_text is None

        # Whitespace-only display text becomes None
        tag = SpecialTag(tag_type="dice", value="1d6", display_text="   ")
        assert tag.display_text is None

    def test_special_tag_effective_value_property(self) -> None:
        """Test effective_value property."""
        # No display text - uses value
        tag = SpecialTag(tag_type="dice", value="1d6")
        assert tag.effective_value == "1d6"

        # With display text - uses display text
        tag = SpecialTag(tag_type="dice", value="1d6", display_text="roll dice")
        assert tag.effective_value == "roll dice"

    def test_special_tag_str_method(self) -> None:
        """Test __str__ method."""
        # Without display text
        tag = SpecialTag(tag_type="dice", value="1d6")
        assert str(tag) == "dice(1d6)"

        # With display text
        tag = SpecialTag(tag_type="dice", value="1d6", display_text="roll dice")
        assert str(tag) == "dice(roll dice)"

    def test_special_tag_frozen_config(self) -> None:
        """Test that SpecialTag is frozen (immutable)."""
        tag = SpecialTag(tag_type="dice", value="1d6")

        with pytest.raises(ValidationError):
            tag.value = "2d6"

        with pytest.raises(ValidationError):
            tag.tag_type = "hit"

    def test_special_tag_metadata_arbitrary_dict(self) -> None:
        """Test that metadata can contain arbitrary dict values."""
        metadata = {
            "string_key": "value",
            "int_key": 42,
            "list_key": [1, 2, 3],
            "nested_dict": {"inner": "value"},
        }
        tag = SpecialTag(tag_type="dice", value="1d6", metadata=metadata)
        assert tag.metadata == metadata

    @pytest.mark.parametrize(
        "tag_type,value",
        [
            ("dice", "1d6"),
            ("hit", "+5"),
            ("dc", "15"),
            ("damage", "2d8+3"),
            ("save", "Dexterity"),
            ("skill", "Perception"),
        ],
    )
    def test_special_tag_various_types(self, tag_type: str, value: str) -> None:
        """Test SpecialTag with various tag types."""
        tag = SpecialTag(tag_type=tag_type, value=value)
        assert tag.tag_type == tag_type.lower()  # Should be normalized
        assert tag.value == value


class TestTagContext:
    """Tests for TagContext Pydantic model."""

    def test_tag_context_creation(self) -> None:
        """Test creating TagContext."""
        mock_omnidexer = Mock()
        context = TagContext(omnidexer=mock_omnidexer)

        assert context.omnidexer == mock_omnidexer

    def test_tag_context_find_content_method(self) -> None:
        """Test find_content method."""
        mock_omnidexer = Mock()
        mock_content = Mock(spec=BaseContent)
        mock_omnidexer.find.return_value = mock_content

        context = TagContext(omnidexer=mock_omnidexer)
        result = context.find_content(ContentType.CREATURE, "Dragon", "MM")

        assert result == mock_content
        mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Dragon", "MM"
        )

    def test_tag_context_find_content_without_source(self) -> None:
        """Test find_content method without source."""
        mock_omnidexer = Mock()
        mock_content = Mock(spec=BaseContent)
        mock_omnidexer.find.return_value = mock_content

        context = TagContext(omnidexer=mock_omnidexer)
        result = context.find_content(ContentType.CREATURE, "Dragon")

        assert result == mock_content
        mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Dragon", None
        )

    def test_tag_context_find_content_returns_none(self) -> None:
        """Test find_content method when content not found."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None

        context = TagContext(omnidexer=mock_omnidexer)
        result = context.find_content(ContentType.CREATURE, "NonexistentCreature", "MM")

        assert result is None

    def test_tag_context_frozen_config(self) -> None:
        """Test that TagContext is frozen (immutable)."""
        mock_omnidexer = Mock()
        context = TagContext(omnidexer=mock_omnidexer)

        with pytest.raises(ValidationError):
            context.omnidexer = Mock()

    def test_tag_context_arbitrary_types_allowed(self) -> None:
        """Test that arbitrary types are allowed for omnidexer."""
        # Should accept any object type for omnidexer
        complex_omnidexer = {"complex": "object", "with": ["various", "types"]}
        context = TagContext(omnidexer=complex_omnidexer)
        assert context.omnidexer == complex_omnidexer


class TestTagResolutionResult:
    """Tests for TagResolutionResult union type."""

    def test_tag_resolution_result_content_reference(self) -> None:
        """Test TagResolutionResult with ContentReference."""
        mock_content = Mock(spec=BaseContent)
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Dragon",
            resolved_content=mock_content,
        )

        # Should be a valid TagResolutionResult
        result: TagResolutionResult = ref
        assert isinstance(result, ContentReference)

    def test_tag_resolution_result_formatting_node(self) -> None:
        """Test TagResolutionResult with FormattingNode."""
        node = FormattingNode(format_type=FormatType.BOLD, content="bold text")

        # Should be a valid TagResolutionResult
        result: TagResolutionResult = node
        assert isinstance(result, FormattingNode)

    def test_tag_resolution_result_special_tag(self) -> None:
        """Test TagResolutionResult with SpecialTag."""
        tag = SpecialTag(tag_type="dice", value="1d6")

        # Should be a valid TagResolutionResult
        result: TagResolutionResult = tag
        assert isinstance(result, SpecialTag)

    def test_tag_resolution_result_string(self) -> None:
        """Test TagResolutionResult with string."""
        text = "plain text"

        # Should be a valid TagResolutionResult
        result: TagResolutionResult = text
        assert isinstance(result, str)
        assert result == "plain text"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_content_reference_with_very_long_strings(self) -> None:
        """Test ContentReference with very long strings."""
        long_name = "A" * 1000
        long_source = "B" * 100
        long_display_text = "C" * 500
        long_page = "D" * 50

        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name=long_name,
            source=long_source,
            display_text=long_display_text,
            page=long_page,
        )

        assert ref.name == long_name
        assert ref.source == long_source
        assert ref.display_text == long_display_text
        assert ref.page == long_page

    def test_special_tag_with_complex_metadata(self) -> None:
        """Test SpecialTag with complex metadata structures."""
        complex_metadata = {
            "nested": {"deep": {"values": [1, 2, {"inner": "value"}]}},
            "list_of_dicts": [
                {"name": "item1", "value": 10},
                {"name": "item2", "value": 20},
            ],
            "mixed_types": [1, "string", True, None, 3.14],
        }

        tag = SpecialTag(tag_type="complex", value="test", metadata=complex_metadata)
        assert tag.metadata == complex_metadata

    def test_unicode_handling(self) -> None:
        """Test handling of Unicode characters."""
        # Unicode in content reference
        ref = ContentReference(
            content_type=ContentType.CREATURE,
            name="Drágón",
            source="PH🅱",
            display_text="mágic drágón",
        )
        assert ref.name == "Drágón"
        assert ref.source == "PH🅱"
        assert ref.display_text == "mágic drágón"

        # Unicode in formatting node
        node = FormattingNode(format_type=FormatType.BOLD, content="bóld téxt")
        assert node.content == "bóld téxt"

        # Unicode in special tag
        tag = SpecialTag(tag_type="dicé", value="1d6", display_text="röll dïcé")
        assert tag.tag_type == "dicé"  # Lowercase but preserves unicode
        assert tag.value == "1d6"
        assert tag.display_text == "röll dïcé"

    def test_whitespace_edge_cases(self) -> None:
        """Test various whitespace scenarios."""
        # Different types of whitespace
        whitespace_types = [
            "  normal spaces  ",
            "\t\ttabs\t\t",
            "\n\nnewlines\n\n",
            "\r\rcarriage returns\r\r",
            " \t\n\rmixed\r\n\t ",
        ]

        for whitespace_text in whitespace_types:
            ref = ContentReference(
                content_type=ContentType.CREATURE,
                name=whitespace_text,
                source=whitespace_text,
                display_text=whitespace_text,
            )
            # All should be stripped to the inner text
            expected = whitespace_text.strip()
            assert ref.name == expected
            if expected:  # Non-empty after strip
                assert ref.source == expected
                assert ref.display_text == expected
            else:  # Empty after strip
                assert ref.source is None
                assert ref.display_text is None
