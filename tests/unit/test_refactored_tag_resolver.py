"""Tests for the refactored tag resolver integration."""

from typing import Any
from unittest.mock import Mock

import pytest

from dnd5e.core.indexer.refactored_tag_resolver import RefactoredTagResolver
from dnd5e.core.indexer.tag_resolver import TagMatch
from dnd5e.core.indexer.tag_types import ContentReference, FormattingNode, SpecialTag
from dnd5e.core.models.content import ContentType
from dnd5e.renderers.latex.tag_renderer import LaTeXTagRenderer


class TestRefactoredTagResolver:
    """Tests for the integrated refactored tag resolver."""

    def test_basic_text_processing_no_tags(self) -> None:
        """Test processing text without any tags."""
        mock_omnidexer = Mock()
        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "This is plain text without any tags."
        result = resolver.process_text(text)

        assert result == text
        mock_omnidexer.find.assert_not_called()

    def test_creature_tag_processing_found(self) -> None:
        """Test processing creature tags when content is found."""
        mock_content = Mock()
        mock_content.name = "Ancient Red Dragon"
        mock_content.source.abbreviation = "MM"

        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = mock_content

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "The {@creature Ancient Red Dragon|MM} attacks!"
        result = resolver.process_text(text)

        expected = "The \\textbf{Ancient Red Dragon} attacks!"
        assert result == expected

        mock_omnidexer.find.assert_called_once_with(
            ContentType.CREATURE, "Ancient Red Dragon", "MM"
        )

    def test_creature_tag_processing_not_found(self) -> None:
        """Test processing creature tags when content is not found."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None  # Not found

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "The {@creature Unknown Beast|MM|mysterious creature} lurks."
        result = resolver.process_text(text)

        # Unresolved content - no formatting applied (backward compatibility)
        expected = "The mysterious creature lurks."
        assert result == expected

    def test_multiple_tag_types_in_text(self) -> None:
        """Test processing text with multiple different tag types."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None  # Simplify by not resolving

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = (
            "The {@creature Dragon} casts {@spell Fireball} dealing "
            "{@dice 8d6} damage. Make a {@dc 15} Dexterity save or take "
            "{@b double} damage!"
        )

        result = resolver.process_text(text)

        # Unresolved content references get no formatting (backward compatibility)
        # But pure formatting tags like {@b} and special tags still work
        expected = (
            "The Dragon casts Fireball dealing "
            "\\texttt{8d6} damage. Make a DC 15 Dexterity save or take "
            "\\textbf{double} damage!"
        )
        assert result == expected

    def test_latex_character_escaping_in_tags(self) -> None:
        """Test that LaTeX characters in tag content are properly escaped."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "The {@creature Dragon & Wyvern} costs {@b $50}."
        result = resolver.process_text(text)

        # Unresolved creature gets no formatting, but {@b} still works
        expected = "The Dragon \\& Wyvern costs \\textbf{\\$50}."
        assert result == expected

    def test_resolve_to_object_method(self) -> None:
        """Test the new resolve_to_object method."""
        mock_content = Mock()
        mock_content.name = "Fireball"

        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = mock_content

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "Cast {@spell Fireball} for {@dice 8d6} damage."
        results = resolver.resolve_to_object(text)

        # Should have 5 parts: text, spell, text, dice, text
        assert len(results) == 5

        assert results[0] == "Cast "

        assert isinstance(results[1], ContentReference)
        assert results[1].content_type == ContentType.SPELL
        assert results[1].name == "Fireball"
        assert results[1].resolved_content == mock_content

        assert results[2] == " for "

        assert isinstance(results[3], FormattingNode)
        assert results[3].content == "8d6"

        assert results[4] == " damage."

    def test_special_tags_in_resolve_to_object(self) -> None:
        """Test resolve_to_object with special tags."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "Roll {@hit +5} with {@chance 75} success rate."
        results = resolver.resolve_to_object(text)

        assert len(results) == 5
        assert results[0] == "Roll "

        assert isinstance(results[1], SpecialTag)
        assert results[1].tag_type == "hit"
        assert results[1].value == "+5"

        assert results[2] == " with "

        assert isinstance(results[3], SpecialTag)
        assert results[3].tag_type == "chance"
        assert results[3].value == "75"

        assert results[4] == " success rate."

    def test_default_renderer_creation(self) -> None:
        """Test that default LaTeX renderer is created when none provided."""
        mock_omnidexer = Mock()
        resolver = RefactoredTagResolver(mock_omnidexer)  # No renderer

        # Accessing renderer property should create default
        renderer = resolver.renderer
        assert isinstance(renderer, LaTeXTagRenderer)

        # Should be cached
        assert resolver.renderer is renderer

    def test_custom_renderer_setting(self) -> None:
        """Test setting a custom renderer."""
        mock_omnidexer = Mock()
        resolver = RefactoredTagResolver(mock_omnidexer)

        custom_renderer = Mock()
        custom_renderer.render.return_value = "CUSTOM_OUTPUT"

        resolver.set_renderer(custom_renderer)

        text = "Test {@spell Fireball}."
        result = resolver.process_text(text)

        # Should use custom renderer
        custom_renderer.render.assert_called_once()
        assert "CUSTOM_OUTPUT" in result

    def test_custom_handler_registration(self) -> None:
        """Test registering custom semantic handlers."""
        mock_omnidexer = Mock()
        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        # Register custom handler that returns SpecialTag
        def custom_handler(tag_match: TagMatch) -> SpecialTag:
            return SpecialTag(tag_type="custom", value=f"processed_{tag_match.name}")

        resolver.register_tag_handler("custom", custom_handler)

        text = "Use {@custom mydata} here."
        result = resolver.process_text(text)

        # SpecialTag with type "custom" should render as escaped value (with LaTeX escaping)
        assert "processed\\_mydata" in result

    def test_error_handling_in_tag_processing(self) -> None:
        """Test graceful error handling during tag processing."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.side_effect = Exception("Database error")

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "The {@creature Dragon} is dangerous."
        result = resolver.process_text(text)

        # Should fall back to tag name when semantic resolution fails
        assert "Dragon" in result
        # Should not contain LaTeX formatting since it's just plain text fallback
        assert "\\textbf{" not in result

    def test_empty_and_none_text_handling(self) -> None:
        """Test handling of empty or None text."""
        mock_omnidexer = Mock()
        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        assert resolver.process_text("") == ""
        # Note: process_text expects str, but we test the error case
        result = resolver.process_text(None)  # type: ignore[arg-type]
        assert result is None

        # resolve_to_object should handle empty text
        results = resolver.resolve_to_object("")
        assert results == [""]

    def test_tag_with_all_components(self) -> None:
        """Test tag with name, source, display text, and page."""
        mock_content = Mock()
        mock_content.name = "Strahd von Zarovich"

        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = mock_content

        renderer = LaTeXTagRenderer()
        resolver = RefactoredTagResolver(mock_omnidexer, renderer)

        text = "Meet {@creature Strahd von Zarovich|CoS|the vampire lord|234}."
        result = resolver.process_text(text)

        # Should use display text for rendering
        assert "\\textbf{the vampire lord}" in result

        # Check the resolved object
        objects = resolver.resolve_to_object(text)
        creature_ref = objects[1]  # Second element should be the ContentReference

        assert isinstance(creature_ref, ContentReference)
        assert creature_ref.name == "Strahd von Zarovich"
        assert creature_ref.source == "CoS"
        assert creature_ref.display_text == "the vampire lord"
        assert creature_ref.page == "234"
        assert creature_ref.resolved_content == mock_content

    def test_backward_compatibility_interface(self) -> None:
        """Test that the interface is backward compatible with original TagResolver."""
        mock_omnidexer = Mock()
        mock_omnidexer.find.return_value = None

        # These methods should exist and work like the original
        resolver = RefactoredTagResolver(mock_omnidexer)

        # process_text method
        result = resolver.process_text("Test {@b bold} text.")
        assert "\\textbf{bold}" in result

        # register_tag_handler method
        def dummy_handler(tag: TagMatch) -> str:
            return "dummy"

        resolver.register_tag_handler("dummy", dummy_handler)

        # Should not raise any errors
        assert True
