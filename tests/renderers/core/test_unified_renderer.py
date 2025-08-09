"""Tests for the unified tag renderer and integration layer."""

from __future__ import annotations

from unittest.mock import Mock, create_autospec

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.renderers.core.interfaces import (
    ContentReferenceInfo,
    CoreTagHandler,
    EnhancementConfiguration,
    EnhancementPipeline,
    FormatStyle,
    RenderingContext,
    UnifiedTagRenderer,
)
from dnd5e.renderers.core.unified_renderer import (
    AdaptiveRenderer,
    EnhancementPipelineBuilder,
    StandardUnifiedRenderer,
    create_debug_renderer,
    create_full_latex_renderer,
    create_simple_latex_renderer,
)


class MockCoreHandler:
    """Mock core handler for testing."""

    def __init__(self, tag_type: str, content_info: ContentReferenceInfo) -> None:
        self.tag_type = tag_type
        self.content_info = content_info

    def handles_tag_type(self, tag_type: str) -> bool:
        return tag_type == self.tag_type

    def extract_content_info(self, node, context) -> ContentReferenceInfo:
        return self.content_info

    def should_include_page_reference(self, page: str | None) -> bool:
        return page is not None and page != "1"

    def validate_content_reference(self, node, context) -> list:
        return []  # No validation errors

    def track_content_for_appendix(self, node, context) -> None:
        pass  # No-op for testing


@pytest.mark.rendering
class TestUnifiedTagRenderer:
    """Tests for the base unified tag renderer."""

    def test_init_with_config(self):
        """Test renderer initialization with configuration."""
        core_handlers = []
        pipeline = Mock(spec=EnhancementPipeline)
        config = EnhancementConfiguration(output_format="latex")

        renderer = UnifiedTagRenderer(core_handlers, pipeline, config)

        assert renderer.core_handlers == core_handlers
        assert renderer.enhancement_pipeline == pipeline
        assert renderer.config == config

    def test_init_with_default_config(self):
        """Test renderer initialization with default configuration."""
        core_handlers = []
        pipeline = Mock(spec=EnhancementPipeline)

        renderer = UnifiedTagRenderer(core_handlers, pipeline)

        assert renderer.config.output_format == "latex"

    def test_render_tag_success(self):
        """Test successful tag rendering."""
        content_info = ContentReferenceInfo(
            name="Dragon",
            display_text="Ancient Red Dragon",
            content_type=ContentType("creature"),
            format_style=FormatStyle.BOLD,
        )

        core_handler = MockCoreHandler("creature", content_info)

        pipeline = Mock(spec=EnhancementPipeline)
        pipeline.apply_enhancements.return_value = "\\textbf{Ancient Red Dragon}"

        renderer = UnifiedTagRenderer([core_handler], pipeline)

        # Create mock node
        mock_node = Mock()
        mock_node.tag_type = "creature"

        context = RenderingContext(output_format="latex")

        result = renderer.render_tag(mock_node, context)

        assert result == "\\textbf{Ancient Red Dragon}"
        pipeline.apply_enhancements.assert_called_once()

    def test_render_tag_no_handler(self):
        """Test tag rendering when no handler is found."""
        renderer = UnifiedTagRenderer([], Mock(spec=EnhancementPipeline))

        mock_node = Mock()
        mock_node.tag_type = "unknown"
        mock_node.name = "Unknown Tag"

        context = RenderingContext(output_format="latex")

        result = renderer.render_tag(mock_node, context)

        assert result == "Unknown Tag"

    def test_render_tag_handler_error(self):
        """Test tag rendering when handler raises error."""
        core_handler = Mock(spec=CoreTagHandler)
        core_handler.handles_tag_type.return_value = True
        core_handler.extract_content_info.side_effect = Exception("Handler error")

        pipeline = Mock(spec=EnhancementPipeline)

        renderer = UnifiedTagRenderer([core_handler], pipeline)

        mock_node = Mock()
        mock_node.tag_type = "test"
        mock_node.name = "Test Tag"

        context = RenderingContext(output_format="latex")

        result = renderer.render_tag(mock_node, context)

        assert result == "[Test Tag]"  # Error fallback

    def test_enhanced_context_creation(self):
        """Test creation of enhanced context with configuration."""
        config = EnhancementConfiguration(
            output_format="latex",
            hyperlink_manager=Mock(),
            content_tracker=Mock(),
        )

        renderer = UnifiedTagRenderer([], Mock(spec=EnhancementPipeline), config)

        base_context = RenderingContext(
            output_format="latex",
            debug_mode=True,
            metadata={"existing": "value"},
        )

        enhanced_context = renderer._create_enhanced_context(base_context)

        # Should preserve original values
        assert enhanced_context.output_format == "latex"
        assert enhanced_context.debug_mode is True

        # Should add configuration
        assert "enhancement_config" in enhanced_context.metadata
        assert "hyperlink_manager" in enhanced_context.metadata
        assert "content_tracker" in enhanced_context.metadata
        assert enhanced_context.metadata["existing"] == "value"


@pytest.mark.rendering
class TestStandardUnifiedRenderer:
    """Tests for the standard unified renderer implementations."""

    def test_create_latex_renderer(self):
        """Test LaTeX renderer creation."""
        core_handlers = []
        hyperlink_manager = Mock()
        content_tracker = Mock()

        renderer = StandardUnifiedRenderer.create_latex_renderer(
            core_handlers,
            hyperlink_manager,
            content_tracker,
            enable_hyperlinks=True,
            enable_content_tracking=True,
        )

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "latex"
        assert renderer.config.enable_hyperlinks is True
        assert renderer.config.enable_content_tracking is True
        assert renderer.config.enable_latex_formatting is True
        assert renderer.config.hyperlink_manager is hyperlink_manager
        assert renderer.config.content_tracker is content_tracker

    def test_create_html_renderer(self):
        """Test HTML renderer creation."""
        core_handlers = []
        hyperlink_manager = Mock()
        content_tracker = Mock()

        renderer = StandardUnifiedRenderer.create_html_renderer(
            core_handlers,
            hyperlink_manager,
            content_tracker,
        )

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "html"
        assert renderer.config.enable_hyperlinks is False  # HTML hyperlinks different
        assert renderer.config.enable_content_tracking is True
        assert renderer.config.enable_latex_formatting is False

    def test_create_markdown_renderer(self):
        """Test Markdown renderer creation."""
        core_handlers = []
        content_tracker = Mock()

        renderer = StandardUnifiedRenderer.create_markdown_renderer(
            core_handlers,
            content_tracker,
        )

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "markdown"
        assert renderer.config.enable_hyperlinks is False
        assert renderer.config.enable_content_tracking is True
        assert renderer.config.enable_latex_formatting is False


@pytest.mark.rendering
class TestAdaptiveRenderer:
    """Tests for the adaptive multi-format renderer."""

    def test_init(self):
        """Test adaptive renderer initialization."""
        core_handlers = []
        hyperlink_manager = Mock()
        content_tracker = Mock()

        renderer = AdaptiveRenderer(
            core_handlers,
            hyperlink_manager,
            content_tracker,
        )

        assert renderer.core_handlers == core_handlers
        assert renderer.hyperlink_manager is hyperlink_manager
        assert renderer.content_tracker is content_tracker
        assert len(renderer._renderer_cache) == 0

    def test_get_latex_renderer(self):
        """Test getting LaTeX renderer."""
        core_handlers = []
        renderer = AdaptiveRenderer(core_handlers)

        latex_renderer = renderer.get_renderer("latex")

        assert isinstance(latex_renderer, StandardUnifiedRenderer)
        assert latex_renderer.config.output_format == "latex"

        # Should cache the renderer
        assert "latex" in renderer._renderer_cache
        assert renderer.get_renderer("latex") is latex_renderer

    def test_get_html_renderer(self):
        """Test getting HTML renderer."""
        core_handlers = []
        renderer = AdaptiveRenderer(core_handlers)

        html_renderer = renderer.get_renderer("html")

        assert isinstance(html_renderer, StandardUnifiedRenderer)
        assert html_renderer.config.output_format == "html"

    def test_get_markdown_renderer(self):
        """Test getting Markdown renderer."""
        core_handlers = []
        renderer = AdaptiveRenderer(core_handlers)

        md_renderer = renderer.get_renderer("markdown")

        assert isinstance(md_renderer, StandardUnifiedRenderer)
        assert md_renderer.config.output_format == "markdown"

    def test_get_unknown_format_defaults_to_latex(self):
        """Test that unknown formats default to LaTeX."""
        core_handlers = []
        renderer = AdaptiveRenderer(core_handlers)

        unknown_renderer = renderer.get_renderer("unknown")

        assert isinstance(unknown_renderer, StandardUnifiedRenderer)
        assert unknown_renderer.config.output_format == "latex"

    def test_render_tag_delegates_to_format_renderer(self):
        """Test that render_tag delegates to format-specific renderer."""
        core_handlers = []
        renderer = AdaptiveRenderer(core_handlers)

        mock_node = Mock()
        mock_node.name = "Test"

        context = RenderingContext(output_format="latex")

        # Mock the cached renderer
        mock_latex_renderer = Mock()
        mock_latex_renderer.render_tag.return_value = "Rendered"
        renderer._renderer_cache["latex"] = mock_latex_renderer

        result = renderer.render_tag(mock_node, context)

        assert result == "Rendered"
        mock_latex_renderer.render_tag.assert_called_once_with(mock_node, context)


@pytest.mark.rendering
class TestEnhancementPipelineBuilder:
    """Tests for the enhancement pipeline builder."""

    def test_empty_builder(self):
        """Test empty pipeline builder."""
        builder = EnhancementPipelineBuilder()

        assert len(builder.enhancers) == 0

        # Should create default pipeline when built
        pipeline = builder.build()
        assert isinstance(pipeline, EnhancementPipeline)

    def test_add_latex_formatting(self):
        """Test adding LaTeX formatting enhancer."""
        builder = EnhancementPipelineBuilder()
        builder.add_latex_formatting(priority=150)

        assert len(builder.enhancers) == 1
        assert builder.enhancers[0].get_enhancement_priority() == 150

    def test_add_hyperlinks(self):
        """Test adding hyperlink enhancer."""
        builder = EnhancementPipelineBuilder()
        builder.add_hyperlinks(priority=250)

        assert len(builder.enhancers) == 1
        assert builder.enhancers[0].get_enhancement_priority() == 250

    def test_add_content_tracking(self):
        """Test adding content tracking enhancer."""
        builder = EnhancementPipelineBuilder()
        builder.add_content_tracking(priority=350)

        assert len(builder.enhancers) == 1
        assert builder.enhancers[0].get_enhancement_priority() == 350

    def test_add_validation(self):
        """Test adding validation enhancer."""
        builder = EnhancementPipelineBuilder()
        builder.add_validation(priority=450)

        assert len(builder.enhancers) == 1
        assert builder.enhancers[0].get_enhancement_priority() == 450

    def test_add_custom_enhancer(self):
        """Test adding custom enhancer."""
        builder = EnhancementPipelineBuilder()
        custom_enhancer = Mock()

        builder.add_custom_enhancer(custom_enhancer)

        assert len(builder.enhancers) == 1
        assert builder.enhancers[0] is custom_enhancer

    def test_method_chaining(self):
        """Test that builder methods support chaining."""
        builder = EnhancementPipelineBuilder()

        result = (
            builder.add_latex_formatting()
            .add_hyperlinks()
            .add_content_tracking()
            .add_validation()
        )

        assert result is builder
        assert len(builder.enhancers) == 4

    def test_build_pipeline(self):
        """Test building enhancement pipeline."""
        builder = EnhancementPipelineBuilder()
        builder.add_latex_formatting(100)
        builder.add_hyperlinks(200)

        pipeline = builder.build()

        assert isinstance(pipeline, EnhancementPipeline)
        # Enhancers should be in the pipeline (order tested elsewhere)

    def test_build_composite(self):
        """Test building composite enhancer."""
        builder = EnhancementPipelineBuilder()
        builder.add_latex_formatting(100)
        builder.add_hyperlinks(200)

        composite = builder.build_composite()

        from dnd5e.renderers.core.enhancers import CompositeEnhancer

        assert isinstance(composite, CompositeEnhancer)
        assert composite.get_enhancement_priority() == 100  # Lowest priority


@pytest.mark.rendering
class TestConvenienceFunctions:
    """Tests for convenience renderer creation functions."""

    def test_create_simple_latex_renderer(self):
        """Test simple LaTeX renderer creation."""
        core_handlers = []

        renderer = create_simple_latex_renderer(core_handlers)

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "latex"
        assert renderer.config.enable_hyperlinks is False
        assert renderer.config.enable_content_tracking is False

    def test_create_full_latex_renderer(self):
        """Test full LaTeX renderer creation."""
        core_handlers = []
        hyperlink_manager = Mock()
        content_tracker = Mock()

        renderer = create_full_latex_renderer(
            core_handlers,
            hyperlink_manager,
            content_tracker,
        )

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "latex"
        assert renderer.config.enable_hyperlinks is True
        assert renderer.config.enable_content_tracking is True
        assert renderer.config.hyperlink_manager is hyperlink_manager
        assert renderer.config.content_tracker is content_tracker

    def test_create_debug_renderer(self):
        """Test debug renderer creation."""
        core_handlers = []

        renderer = create_debug_renderer(core_handlers, output_format="latex")

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "latex"
        assert renderer.config.enable_hyperlinks is False  # Simplified for debugging
        assert renderer.config.enable_content_tracking is True

    def test_create_debug_renderer_non_latex(self):
        """Test debug renderer creation for non-LaTeX format."""
        core_handlers = []

        renderer = create_debug_renderer(core_handlers, output_format="html")

        assert isinstance(renderer, StandardUnifiedRenderer)
        assert renderer.config.output_format == "html"
        assert renderer.config.enable_latex_formatting is False
