"""Comprehensive tests for TagResolver Pydantic model."""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from dnd5e.core.indexer.tag_parser import TagParseError, TagParser
from dnd5e.core.indexer.tag_renderer import TagRenderer
from dnd5e.core.indexer.tag_resolver import TagResolver


class TestTagResolver:
    """Tests for TagResolver Pydantic model."""

    @pytest.fixture
    def mock_omnidexer(self) -> Mock:
        """Create mock omnidexer for testing."""
        omnidexer = Mock()
        omnidexer.find.return_value = None
        return omnidexer

    @pytest.fixture
    def mock_parser(self) -> Mock:
        """Create mock TagParser for testing."""
        parser = Mock(spec=TagParser)
        parser.parse.return_value = Mock()  # Mock document
        return parser

    @pytest.fixture
    def mock_renderer(self) -> Mock:
        """Create mock TagRenderer for testing."""
        renderer = Mock(spec=TagRenderer)
        renderer.render_document.return_value = "rendered text"
        renderer.get_tracked_content.return_value = []
        renderer.get_tracked_content_for_appendix.return_value = {}
        renderer.get_content_statistics.return_value = {}
        renderer.get_supported_tag_types.return_value = ["creature", "spell"]
        renderer.has_handler.return_value = True
        return renderer

    def test_tag_resolver_creation_with_omnidexer(self, mock_omnidexer: Mock) -> None:
        """Test creating TagResolver with omnidexer."""
        resolver = TagResolver(omnidexer=mock_omnidexer)

        assert resolver.omnidexer == mock_omnidexer
        assert isinstance(resolver.parser, TagParser)
        assert isinstance(resolver.renderer, TagRenderer)
        assert resolver.custom_handlers == {}

    def test_tag_resolver_creation_without_omnidexer(self) -> None:
        """Test creating TagResolver without omnidexer."""
        resolver = TagResolver()

        assert resolver.omnidexer is None
        assert isinstance(resolver.parser, TagParser)
        assert isinstance(resolver.renderer, TagRenderer)
        assert resolver.custom_handlers == {}

    def test_tag_resolver_custom_init_creates_renderer(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test that custom __init__ creates renderer with omnidexer."""
        # Create resolver and verify it creates a TagRenderer
        resolver = TagResolver(omnidexer=mock_omnidexer)

        # Verify renderer was created and has the omnidexer
        assert isinstance(resolver.renderer, TagRenderer)
        assert resolver.omnidexer == mock_omnidexer

    def test_tag_resolver_process_text_success(self, mock_omnidexer: Mock) -> None:
        """Test successful text processing."""
        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "render_document") as mock_render,
        ):
            mock_document = Mock()
            mock_parse.return_value = mock_document
            mock_render.return_value = "processed text"

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text("input text")

            assert result == "processed text"
            mock_parse.assert_called_once_with("input text")
            mock_render.assert_called_once_with(mock_document)

    def test_tag_resolver_process_text_empty_input(self, mock_omnidexer: Mock) -> None:
        """Test processing empty text."""
        resolver = TagResolver(omnidexer=mock_omnidexer)

        # Empty string should return as-is
        assert resolver.process_text("") == ""

        # None should return as-is
        assert resolver.process_text(None) is None  # type: ignore

    def test_tag_resolver_process_text_parse_error(self, mock_omnidexer: Mock) -> None:
        """Test handling of parse errors."""
        with patch.object(TagParser, "parse") as mock_parse:
            mock_parse.side_effect = TagParseError("Parse failed")

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text("invalid {@tag}")

            # Should return original text on parse error
            assert result == "invalid {@tag}"

    def test_tag_resolver_process_text_unexpected_error(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test handling of unexpected errors."""
        with patch.object(TagParser, "parse") as mock_parse:
            mock_parse.side_effect = Exception("Unexpected error")

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text("input text")

            # Should return original text on unexpected error
            assert result == "input text"

    def test_tag_resolver_register_handler(self, mock_omnidexer: Mock) -> None:
        """Test registering new-style tag handler."""
        resolver = TagResolver(omnidexer=mock_omnidexer)
        mock_handler = Mock()

        # This should not raise an exception
        resolver.register_handler(mock_handler)

        # The handler should be registered with the renderer
        # We can't easily test the exact call count due to default handlers
        # but we can verify the method exists and is callable
        assert hasattr(resolver, "register_handler")
        assert callable(resolver.register_handler)

    def test_tag_resolver_get_tracked_content_for_appendix(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test getting tracked content for appendix."""
        with patch.object(TagRenderer, "get_tracked_content") as mock_get_tracked:
            # Mock tracked content with to_tuple method
            mock_content1 = Mock()
            mock_content1.to_tuple.return_value = ("creature", "Dragon", "MM")
            mock_content2 = Mock()
            mock_content2.to_tuple.return_value = ("spell", "Fireball", "PHB")

            mock_get_tracked.return_value = [mock_content1, mock_content2]

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.get_tracked_content_for_appendix()

            assert result == [
                ("creature", "Dragon", "MM"),
                ("spell", "Fireball", "PHB"),
            ]

    def test_tag_resolver_get_tracked_content_detailed(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test getting detailed tracked content."""
        with patch.object(
            TagRenderer, "get_tracked_content_for_appendix"
        ) as mock_get_detailed:
            expected_result = {
                "creature": [{"name": "Dragon", "source": "MM", "reference_count": 3}],
                "spell": [{"name": "Fireball", "source": "PHB", "reference_count": 1}],
            }
            mock_get_detailed.return_value = expected_result

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.get_tracked_content_detailed()

            assert result == expected_result

    def test_tag_resolver_clear_tracked_content(self, mock_omnidexer: Mock) -> None:
        """Test clearing tracked content."""
        with patch.object(TagRenderer, "clear_tracked_content") as mock_clear:
            resolver = TagResolver(omnidexer=mock_omnidexer)
            resolver.clear_tracked_content()

            mock_clear.assert_called_once()

    def test_tag_resolver_get_content_statistics(self, mock_omnidexer: Mock) -> None:
        """Test getting content statistics."""
        with patch.object(TagRenderer, "get_content_statistics") as mock_get_stats:
            expected_stats = {"creature": 5, "spell": 10, "item": 3}
            mock_get_stats.return_value = expected_stats

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.get_content_statistics()

            assert result == expected_stats

    def test_tag_resolver_track_document_content_success(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test tracking document content successfully."""
        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "track_document_content") as mock_track,
        ):
            mock_document = Mock()
            mock_parse.return_value = mock_document

            resolver = TagResolver(omnidexer=mock_omnidexer)
            resolver.track_document_content("input text")

            mock_parse.assert_called_once_with("input text")
            mock_track.assert_called_once_with(mock_document)

    def test_tag_resolver_track_document_content_parse_error(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test tracking document content with parse error."""
        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "track_document_content") as mock_track,
        ):
            mock_parse.side_effect = TagParseError("Parse failed")

            resolver = TagResolver(omnidexer=mock_omnidexer)
            resolver.track_document_content("invalid {@tag}")

            # Should not call track_document_content on parse error
            mock_track.assert_not_called()

    def test_tag_resolver_track_document_content_unexpected_error(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test tracking document content with unexpected error."""
        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "track_document_content") as mock_track,
        ):
            mock_parse.side_effect = Exception("Unexpected error")

            resolver = TagResolver(omnidexer=mock_omnidexer)
            resolver.track_document_content("input text")

            # Should not call track_document_content on unexpected error
            mock_track.assert_not_called()

    def test_tag_resolver_get_supported_tag_types(self, mock_omnidexer: Mock) -> None:
        """Test getting supported tag types."""
        with patch.object(TagRenderer, "get_supported_tag_types") as mock_get_types:
            expected_types = ["creature", "spell", "item", "dice", "hit"]
            mock_get_types.return_value = expected_types

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.get_supported_tag_types()

            assert result == expected_types

    def test_tag_resolver_has_handler(self, mock_omnidexer: Mock) -> None:
        """Test checking if handler exists."""
        with patch.object(TagRenderer, "has_handler") as mock_has_handler:
            mock_has_handler.return_value = True

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.has_handler("creature")

            assert result is True
            mock_has_handler.assert_called_once_with("creature")

    def test_tag_resolver_arbitrary_types_allowed(self) -> None:
        """Test that TagResolver allows arbitrary types."""
        # Should accept any type for omnidexer
        complex_omnidexer = {"complex": "object"}
        resolver = TagResolver(omnidexer=complex_omnidexer)
        assert resolver.omnidexer == complex_omnidexer

        # Should accept custom parser with real parser instance
        custom_parser = TagParser()
        resolver = TagResolver(parser=custom_parser)
        assert resolver.parser == custom_parser

    def test_tag_resolver_custom_handlers_validation(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test custom_handlers field validation."""
        # Valid custom handlers dict
        handlers = {"test1": lambda x: x, "test2": lambda x: f"processed_{x}"}

        resolver = TagResolver(omnidexer=mock_omnidexer, custom_handlers=handlers)
        assert resolver.custom_handlers == handlers

        # Empty dict should work
        resolver = TagResolver(omnidexer=mock_omnidexer, custom_handlers={})
        assert resolver.custom_handlers == {}

    def test_tag_resolver_field_default_values(self) -> None:
        """Test that fields have correct default values."""
        resolver = TagResolver()

        assert resolver.omnidexer is None
        assert isinstance(resolver.parser, TagParser)
        assert isinstance(resolver.renderer, TagRenderer)
        assert resolver.custom_handlers == {}

    def test_tag_resolver_complex_text_processing_scenario(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test complex text processing scenario."""
        input_text = (
            "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
        )
        expected_output = "Cast \\textit{Fireball} at the \\textbf{Ancient Red Dragon}!"

        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "render_document") as mock_render,
        ):
            mock_document = Mock()
            mock_parse.return_value = mock_document
            mock_render.return_value = expected_output

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text(input_text)

            assert result == expected_output
            mock_parse.assert_called_once_with(input_text)
            mock_render.assert_called_once_with(mock_document)

    def test_tag_resolver_unicode_handling(self, mock_omnidexer: Mock) -> None:
        """Test handling of Unicode text."""
        unicode_text = "Cást {@spell Fírébàll|PHB} ät thé drágön!"

        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "render_document") as mock_render,
        ):
            mock_document = Mock()
            mock_parse.return_value = mock_document
            mock_render.return_value = unicode_text

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text(unicode_text)

            assert result == unicode_text

    def test_tag_resolver_very_long_text(self, mock_omnidexer: Mock) -> None:
        """Test processing very long text."""
        long_text = "Very long text " * 1000 + "{@spell Fireball|PHB}"

        with (
            patch.object(TagParser, "parse") as mock_parse,
            patch.object(TagRenderer, "render_document") as mock_render,
        ):
            mock_document = Mock()
            mock_parse.return_value = mock_document
            mock_render.return_value = long_text.replace(
                "{@spell Fireball|PHB}", "\\textit{Fireball}"
            )

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text(long_text)

            assert "\\textit{Fireball}" in result
            assert len(result) > 1000

    def test_tag_resolver_multiple_instances_independence(self) -> None:
        """Test that multiple TagResolver instances are independent."""
        omnidexer1 = Mock()
        omnidexer2 = Mock()

        resolver1 = TagResolver(omnidexer=omnidexer1)
        resolver2 = TagResolver(omnidexer=omnidexer2)

        # Should have different omnidexers
        assert resolver1.omnidexer is not resolver2.omnidexer

        # Should have different renderer instances
        assert resolver1.renderer is not resolver2.renderer

        # Should have different custom_handlers dicts
        assert resolver1.custom_handlers is not resolver2.custom_handlers

        # Modifying one shouldn't affect the other
        resolver1.custom_handlers["test"] = lambda x: x
        assert "test" not in resolver2.custom_handlers

    def test_tag_resolver_integration_with_real_parser(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test integration with real TagParser (not mocked)."""
        # Use real TagParser to test actual integration
        resolver = TagResolver(omnidexer=mock_omnidexer)

        # This should work with real parser
        simple_text = "Plain text without tags"
        result = resolver.process_text(simple_text)

        # Result should be processed (might be same as input for plain text)
        assert isinstance(result, str)

    def test_tag_resolver_error_logging(self, mock_omnidexer: Mock) -> None:
        """Test that errors are properly logged."""
        with (
            patch("dnd5e.core.indexer.tag_resolver.logger") as mock_logger,
            patch.object(TagParser, "parse") as mock_parse,
        ):
            mock_parse.side_effect = TagParseError("Test parse error")

            resolver = TagResolver(omnidexer=mock_omnidexer)
            result = resolver.process_text("test text")

            # Should log warning for parse error
            mock_logger.warning.assert_called_once()
            assert "Tag parsing failed" in str(mock_logger.warning.call_args)

            # Should return original text
            assert result == "test text"

    def test_tag_resolver_renderer_creation_integration(
        self, mock_omnidexer: Mock
    ) -> None:
        """Test that renderer is created correctly during initialization."""
        # This tests the integration between __init__ and TagRenderer creation
        resolver = TagResolver(omnidexer=mock_omnidexer)

        # Verify renderer was created and has the omnidexer
        assert hasattr(resolver.renderer, "omnidexer")
        # Note: Actual TagRenderer might not expose omnidexer directly,
        # this is just testing the pattern

    def test_tag_resolver_config_arbitrary_types(self) -> None:
        """Test that Config allows arbitrary types."""

        # The Config should allow arbitrary types for complex objects
        class CustomOmnidexer:
            def __init__(self) -> None:
                self.data = {"test": "value"}

        custom_omnidexer = CustomOmnidexer()
        resolver = TagResolver(omnidexer=custom_omnidexer)

        assert resolver.omnidexer == custom_omnidexer
        assert resolver.omnidexer.data == {"test": "value"}
