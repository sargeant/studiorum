"""Tests for core tag handler interfaces and protocols."""

from unittest.mock import MagicMock, Mock

import pytest

from studiorum.renderers.core.interfaces import (
    ContentReferenceInfo,
    EnhancementPipeline,
    FormatStyle,
    RenderingContext,
    TagValidationError,
    UnifiedTagRenderer,
)


@pytest.mark.rendering
class TestContentReferenceInfo:
    """Test ContentReferenceInfo model."""

    def test_content_reference_info_creation(self):
        """Test creating ContentReferenceInfo with required fields."""
        info = ContentReferenceInfo(
            name="Goblin",
            display_text="Goblin",
        )

        assert info.name == "Goblin"
        assert info.display_text == "Goblin"
        assert info.source is None
        assert info.page is None
        assert info.content_type is None
        assert info.format_style == FormatStyle.PLAIN

    def test_content_reference_info_with_all_fields(self):
        """Test creating ContentReferenceInfo with all fields."""
        from studiorum.core.models.content import ContentType

        info = ContentReferenceInfo(
            name="Adult Red Dragon",
            display_text="adult red dragon",
            source="MM",
            page="98",
            content_type=ContentType("creature"),
            format_style=FormatStyle.BOLD,
        )

        assert info.name == "Adult Red Dragon"
        assert info.display_text == "adult red dragon"
        assert info.source == "MM"
        assert info.page == "98"
        assert info.content_type == ContentType("creature")
        assert info.format_style == FormatStyle.BOLD

    def test_content_reference_info_validation_empty_name(self):
        """Test that empty names are now allowed after validation relaxation."""
        # Empty names are now allowed in Phase 5 architecture
        info = ContentReferenceInfo(
            name="",  # Empty name is now acceptable
            display_text="Some text",
        )
        assert info.name == ""
        assert info.display_text == "Some text"


@pytest.mark.rendering
class TestTagValidationError:
    """Test TagValidationError model."""

    def test_tag_validation_error_creation(self):
        """Test creating TagValidationError."""
        error = TagValidationError(
            error_type="missing_content",
            message="Spell 'Fireball' not found",
            tag_type="spell",
            tag_name="Fireball",
            source="PHB",
        )

        assert error.error_type == "missing_content"
        assert error.message == "Spell 'Fireball' not found"
        assert error.tag_type == "spell"
        assert error.tag_name == "Fireball"
        assert error.source == "PHB"

    def test_tag_validation_error_minimal(self):
        """Test creating TagValidationError with minimal fields."""
        error = TagValidationError(
            error_type="validation_failed",
            message="Something went wrong",
            tag_type="creature",
        )

        assert error.error_type == "validation_failed"
        assert error.message == "Something went wrong"
        assert error.tag_type == "creature"
        assert error.tag_name is None
        assert error.source is None


@pytest.mark.rendering
class TestRenderingContext:
    """Test RenderingContext model."""

    def test_rendering_context_minimal(self):
        """Test creating RenderingContext with minimal fields."""
        context = RenderingContext(output_format="latex")

        assert context.output_format == "latex"
        assert context.debug_mode is False
        assert context.omnidexer is None
        assert context.content_tracker is None
        assert context.metadata == {}

    def test_rendering_context_with_services(self):
        """Test creating RenderingContext with service dependencies."""
        mock_omnidexer = Mock()
        mock_tracker = Mock()

        context = RenderingContext(
            output_format="html",
            debug_mode=True,
            omnidexer=mock_omnidexer,
            content_tracker=mock_tracker,
            metadata={"custom": "value"},
        )

        assert context.output_format == "html"
        assert context.debug_mode is True
        assert context.omnidexer is mock_omnidexer
        assert context.content_tracker is mock_tracker
        assert context.metadata == {"custom": "value"}


@pytest.mark.rendering
class TestEnhancementPipeline:
    """Test EnhancementPipeline functionality."""

    def test_enhancement_pipeline_ordering(self):
        """Test that enhancers are ordered by priority."""
        # Create mock enhancers with different priorities
        enhancer1 = Mock()
        enhancer1.get_enhancement_priority.return_value = 300

        enhancer2 = Mock()
        enhancer2.get_enhancement_priority.return_value = 100

        enhancer3 = Mock()
        enhancer3.get_enhancement_priority.return_value = 200

        # Create pipeline (should sort by priority)
        pipeline = EnhancementPipeline([enhancer1, enhancer2, enhancer3])

        # Check that enhancers are ordered correctly (100, 200, 300)
        assert pipeline.enhancers[0] is enhancer2  # Priority 100
        assert pipeline.enhancers[1] is enhancer3  # Priority 200
        assert pipeline.enhancers[2] is enhancer1  # Priority 300

    def test_enhancement_pipeline_apply(self):
        """Test applying enhancements in pipeline."""
        # Create mock enhancers
        enhancer1 = Mock()
        enhancer1.get_enhancement_priority.return_value = 100
        enhancer1.enhance_content_reference.return_value = "enhanced1"

        enhancer2 = Mock()
        enhancer2.get_enhancement_priority.return_value = 200
        enhancer2.enhance_content_reference.return_value = "enhanced2"

        # Create pipeline
        pipeline = EnhancementPipeline([enhancer1, enhancer2])

        # Create test content and context
        content_info = ContentReferenceInfo(name="Test", display_text="Test")
        context = RenderingContext(output_format="latex")

        # Apply enhancements
        result = pipeline.apply_enhancements(content_info, context)

        # Should return the last enhancement result
        assert result == "enhanced2"

        # Verify both enhancers were called
        enhancer1.enhance_content_reference.assert_called_once_with(
            content_info, context
        )
        # Second enhancer should receive updated content_info with display_text from first enhancer
        expected_updated_info = ContentReferenceInfo(
            name="Test",
            display_text="enhanced1",  # Updated from first enhancer
            source=None,
            page=None,
            content_type=None,
            format_style=FormatStyle.PLAIN,
        )
        enhancer2.enhance_content_reference.assert_called_once_with(
            expected_updated_info, context
        )

    def test_enhancement_pipeline_error_handling(self):
        """Test that pipeline handles enhancer errors gracefully."""
        # Create mock enhancers - one fails, one succeeds
        failing_enhancer = Mock()
        failing_enhancer.get_enhancement_priority.return_value = 100
        failing_enhancer.enhance_content_reference.side_effect = Exception(
            "Enhancer failed"
        )

        working_enhancer = Mock()
        working_enhancer.get_enhancement_priority.return_value = 200
        working_enhancer.enhance_content_reference.return_value = "success"

        # Create pipeline
        pipeline = EnhancementPipeline([failing_enhancer, working_enhancer])

        # Create test content and context
        content_info = ContentReferenceInfo(name="Test", display_text="Test")
        context = RenderingContext(output_format="latex")

        # Apply enhancements - should not raise exception
        result = pipeline.apply_enhancements(content_info, context)

        # Should return result from working enhancer
        assert result == "success"


@pytest.mark.rendering
class TestUnifiedTagRenderer:
    """Test UnifiedTagRenderer integration."""

    def test_unified_renderer_creation(self):
        """Test creating UnifiedTagRenderer."""
        mock_handler = Mock()
        mock_pipeline = Mock()

        renderer = UnifiedTagRenderer([mock_handler], mock_pipeline)

        assert renderer.core_handlers == [mock_handler]
        assert renderer.enhancement_pipeline is mock_pipeline

    def test_render_tag_success_path(self):
        """Test successful tag rendering."""
        # Create mock core handler
        mock_handler = Mock()
        mock_handler.handles_tag_type.return_value = True
        mock_content_info = ContentReferenceInfo(name="Test", display_text="Test")
        mock_handler.extract_content_info.return_value = mock_content_info
        mock_handler.validate_content_reference.return_value = []  # No errors

        # Create mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.apply_enhancements.return_value = "final result"

        # Create renderer
        renderer = UnifiedTagRenderer([mock_handler], mock_pipeline)

        # Create mock tag node
        mock_node = Mock()
        mock_node.tag_type = "test"

        # Create context
        context = RenderingContext(output_format="latex")

        # Render tag
        result = renderer.render_tag(mock_node, context)

        # Verify result
        assert result == "final result"

        # Verify handler was called correctly
        mock_handler.handles_tag_type.assert_called_once_with("test")
        mock_handler.extract_content_info.assert_called_once_with(mock_node, context)
        mock_handler.validate_content_reference.assert_called_once_with(
            mock_node, context
        )
        mock_handler.track_content_for_appendix.assert_called_once_with(
            mock_node, context
        )

        # Verify pipeline was called with content info and some context
        # The context may be enhanced with additional metadata
        mock_pipeline.apply_enhancements.assert_called_once()
        call_args = mock_pipeline.apply_enhancements.call_args
        assert call_args[0][0] == mock_content_info  # First arg should be content_info
        called_context = call_args[0][1]  # Second arg should be the context
        assert called_context.output_format == "latex"  # Should preserve output format

    def test_render_tag_unknown_type(self):
        """Test rendering unknown tag type."""
        # Create mock handler that doesn't handle the tag
        mock_handler = Mock()
        mock_handler.handles_tag_type.return_value = False

        mock_pipeline = Mock()

        # Create renderer
        renderer = UnifiedTagRenderer([mock_handler], mock_pipeline)

        # Create mock tag node
        mock_node = Mock()
        mock_node.tag_type = "unknown"
        mock_node.name = "Unknown Tag"

        # Create context
        context = RenderingContext(output_format="latex")

        # After Phase 2: Should raise ValueError for unknown tags (no fallbacks)
        with pytest.raises(
            ValueError, match="No handler available for tag type 'unknown'"
        ):
            renderer.render_tag(mock_node, context)

    def test_render_tag_error_handling(self):
        """Test error handling in tag rendering."""
        # Create mock handler that raises exception
        mock_handler = Mock()
        mock_handler.handles_tag_type.return_value = True
        mock_handler.extract_content_info.side_effect = Exception("Handler failed")

        mock_pipeline = Mock()

        # Create renderer
        renderer = UnifiedTagRenderer([mock_handler], mock_pipeline)

        # Create mock tag node
        mock_node = Mock()
        mock_node.tag_type = "test"
        mock_node.name = "Test Tag"

        # Create context
        context = RenderingContext(output_format="latex")

        # After Phase 2: Should propagate handler errors instead of fallback
        with pytest.raises(Exception, match="Handler failed"):
            renderer.render_tag(mock_node, context)
