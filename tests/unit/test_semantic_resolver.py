"""Tests for semantic tag resolution (without formatting)."""

from typing import Any
from unittest.mock import Mock

import pytest

from dnd5e.core.indexer.semantic_resolver import SemanticTagResolver
from dnd5e.core.indexer.tag_resolver import TagMatch
from dnd5e.core.indexer.tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagContext,
)
from dnd5e.core.models.content import ContentType


class TestSemanticTagResolver:
    """Tests for semantic tag resolution without formatting concerns."""

    def test_content_reference_resolution_found(self) -> None:
        """Test resolving content reference tags when content is found."""
        # Mock omnidexer that finds content
        mock_content = Mock()
        mock_content.name = "Ancient Red Dragon"
        mock_content.source.abbreviation = "MM"

        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = mock_content

        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        tag_match = TagMatch(
            tag_type="creature",
            name="Ancient Red Dragon",
            source="MM",
            display_text=None,
            page=None,
        )

        result = resolver.resolve_tag(tag_match)

        # Should return ContentReference with resolved content
        assert isinstance(result, ContentReference)
        assert result.content_type == ContentType.CREATURE
        assert result.name == "Ancient Red Dragon"
        assert result.source == "MM"
        assert result.resolved_content == mock_content
        assert result.is_resolved is True

        # Verify omnidexer was called correctly
        mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Ancient Red Dragon", "MM"
        )

    def test_content_reference_resolution_not_found(self) -> None:
        """Test resolving content reference tags when content is not found."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None  # Content not found

        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        tag_match = TagMatch(
            tag_type="spell",
            name="Unknown Spell",
            source="PHB",
            display_text="Magic Missile",  # Custom display text
            page=None,
        )

        result = resolver.resolve_tag(tag_match)

        # Should still return ContentReference but with no resolved content
        assert isinstance(result, ContentReference)
        assert result.content_type == ContentType.SPELL
        assert result.name == "Unknown Spell"
        assert result.source == "PHB"
        assert result.display_text == "Magic Missile"
        assert result.resolved_content is None
        assert result.is_resolved is False

    def test_formatting_node_resolution(self) -> None:
        """Test resolving pure formatting tags."""
        mock_omnidexer = Mock()
        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        # Test bold tag
        bold_tag = TagMatch(tag_type="bold", name="important text")
        result = resolver.resolve_tag(bold_tag)

        assert isinstance(result, FormattingNode)
        assert result.format_type == FormatType.BOLD
        assert result.content == "important text"

        # Test italic tag
        italic_tag = TagMatch(tag_type="italic", name="emphasized text")
        result = resolver.resolve_tag(italic_tag)

        assert isinstance(result, FormattingNode)
        assert result.format_type == FormatType.ITALIC
        assert result.content == "emphasized text"

        # Test dice tag (monospace)
        dice_tag = TagMatch(tag_type="dice", name="1d6+2")
        result = resolver.resolve_tag(dice_tag)

        assert isinstance(result, FormattingNode)
        assert result.format_type == FormatType.MONOSPACE
        assert result.content == "1d6+2"

    def test_special_tag_resolution(self) -> None:
        """Test resolving special tags with custom semantics."""
        mock_omnidexer = Mock()
        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        # Test hit tag
        hit_tag = TagMatch(tag_type="hit", name="5")
        result = resolver.resolve_tag(hit_tag)

        assert isinstance(result, SpecialTag)
        assert result.tag_type == "hit"
        assert result.value == "5"

        # Test DC tag
        dc_tag = TagMatch(tag_type="dc", name="15", display_text="hard save")
        result = resolver.resolve_tag(dc_tag)

        assert isinstance(result, SpecialTag)
        assert result.tag_type == "dc"
        assert result.value == "15"
        assert result.display_text == "hard save"

        # Test recharge tag with normalization
        recharge_tag = TagMatch(tag_type="recharge", name="5")
        result = resolver.resolve_tag(recharge_tag)

        assert isinstance(result, SpecialTag)
        assert result.tag_type == "recharge"
        assert result.value == "5--6"  # Should be normalized

    def test_unknown_tag_fallback(self) -> None:
        """Test handling of unknown tag types."""
        mock_omnidexer = Mock()
        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        unknown_tag = TagMatch(
            tag_type="unknown", name="some content", display_text="fallback text"
        )
        result = resolver.resolve_tag(unknown_tag)

        # Should return display_text as fallback
        assert isinstance(result, str)
        assert result == "fallback text"

        # Test fallback to name when no display_text
        unknown_tag2 = TagMatch(tag_type="unknown", name="some content")
        result2 = resolver.resolve_tag(unknown_tag2)

        assert isinstance(result2, str)
        assert result2 == "some content"

    def test_effective_name_property(self) -> None:
        """Test ContentReference effective_name property."""
        ref1 = ContentReference(
            content_type=ContentType.SPELL, name="fireball", display_text="magical fire"
        )
        assert ref1.effective_name == "magical fire"

        ref2 = ContentReference(content_type=ContentType.SPELL, name="fireball")
        assert ref2.effective_name == "fireball"

    def test_special_tag_effective_value_property(self) -> None:
        """Test SpecialTag effective_value property."""
        tag1 = SpecialTag(tag_type="hit", value="5", display_text="+5 attack")
        assert tag1.effective_value == "+5 attack"

        tag2 = SpecialTag(tag_type="hit", value="5")
        assert tag2.effective_value == "5"

    def test_book_tag_page_handling(self) -> None:
        """Test special handling of book tags where display_text might be page."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None

        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        # Book tag with numeric display_text (should become page)
        book_tag = TagMatch(
            tag_type="book",
            name="Player's Handbook",
            source="PHB",
            display_text="123",  # Numeric, should become page
        )

        result = resolver.resolve_tag(book_tag)

        assert isinstance(result, ContentReference)
        assert result.name == "Player's Handbook"
        assert result.page == "123"
        assert result.display_text is None  # Should be None since it became page

    def test_custom_handler_registration(self) -> None:
        """Test registering custom semantic handlers."""
        mock_omnidexer = Mock()
        context = TagContext(omnidexer=mock_omnidexer)
        resolver = SemanticTagResolver(context)

        # Register custom handler
        def custom_handler(tag: TagMatch) -> SpecialTag:
            return SpecialTag(tag_type="custom", value=f"processed_{tag.name}")

        resolver.register_tag_handler("custom", custom_handler)

        # Test custom handler
        custom_tag = TagMatch(tag_type="custom", name="test")
        result = resolver.resolve_tag(custom_tag)

        assert isinstance(result, SpecialTag)
        assert result.tag_type == "custom"
        assert result.value == "processed_test"
