"""Unified tag renderer implementing the composition-based architecture.

This module provides the main integration layer that combines core business
logic handlers with presentation enhancement pipelines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dnd5e.core.logging import get_logger

from .enhancers import (
    CompositeEnhancer,
    create_latex_enhancement_pipeline,
    create_plain_text_enhancement_pipeline,
)
from .interfaces import (
    CoreTagHandler,
    EnhancementConfiguration,
    EnhancementPipeline,
    RenderingContext,
    TagHandlerEnhancer,
    UnifiedTagRenderer,
)

if TYPE_CHECKING:
    from dnd5e.core.indexer.content_tracker import ContentTracker
    from dnd5e.core.indexer.hyperlink_manager import HyperlinkManager
    from dnd5e.core.text.tag_ast import TagNode

logger = get_logger(__name__)


class StandardUnifiedRenderer(UnifiedTagRenderer):
    """Standard implementation of the unified tag renderer with common configurations."""

    @classmethod
    def create_latex_renderer(
        cls,
        core_handlers: list[CoreTagHandler],
        hyperlink_manager: HyperlinkManager | None = None,
        content_tracker: ContentTracker | None = None,
        enable_hyperlinks: bool = True,
        enable_content_tracking: bool = True,
    ) -> StandardUnifiedRenderer:
        """Create a renderer configured for LaTeX output.

        Args:
            core_handlers: Core business logic handlers
            hyperlink_manager: Optional hyperlink manager service
            content_tracker: Optional content tracker service
            enable_hyperlinks: Whether to enable hyperlink generation
            enable_content_tracking: Whether to enable content tracking

        Returns:
            Configured unified renderer for LaTeX
        """
        # Create LaTeX enhancement pipeline
        latex_enhancers = create_latex_enhancement_pipeline()
        enhancement_pipeline = EnhancementPipeline(latex_enhancers)

        # Create configuration
        config = EnhancementConfiguration(
            output_format="latex",
            enable_hyperlinks=enable_hyperlinks,
            enable_content_tracking=enable_content_tracking,
            enable_latex_formatting=True,
            hyperlink_manager=hyperlink_manager,
            content_tracker=content_tracker,
        )

        return cls(core_handlers, enhancement_pipeline, config)

    @classmethod
    def create_html_renderer(
        cls,
        core_handlers: list[CoreTagHandler],
        hyperlink_manager: HyperlinkManager | None = None,
        content_tracker: ContentTracker | None = None,
    ) -> StandardUnifiedRenderer:
        """Create a renderer configured for HTML output.

        Args:
            core_handlers: Core business logic handlers
            hyperlink_manager: Optional hyperlink manager service
            content_tracker: Optional content tracker service

        Returns:
            Configured unified renderer for HTML
        """
        # For now, use plain text pipeline as placeholder for HTML
        # TODO: Implement HTML-specific enhancers
        html_enhancers = create_plain_text_enhancement_pipeline()
        enhancement_pipeline = EnhancementPipeline(html_enhancers)

        config = EnhancementConfiguration(
            output_format="html",
            enable_hyperlinks=False,  # HTML hyperlinks need different implementation
            enable_content_tracking=True,
            enable_latex_formatting=False,
            hyperlink_manager=hyperlink_manager,
            content_tracker=content_tracker,
        )

        return cls(core_handlers, enhancement_pipeline, config)

    @classmethod
    def create_markdown_renderer(
        cls,
        core_handlers: list[CoreTagHandler],
        content_tracker: ContentTracker | None = None,
    ) -> StandardUnifiedRenderer:
        """Create a renderer configured for Markdown output.

        Args:
            core_handlers: Core business logic handlers
            content_tracker: Optional content tracker service

        Returns:
            Configured unified renderer for Markdown
        """
        # Use minimal pipeline for Markdown
        markdown_enhancers = create_plain_text_enhancement_pipeline()
        enhancement_pipeline = EnhancementPipeline(markdown_enhancers)

        config = EnhancementConfiguration(
            output_format="markdown",
            enable_hyperlinks=False,
            enable_content_tracking=True,
            enable_latex_formatting=False,
            content_tracker=content_tracker,
        )

        return cls(core_handlers, enhancement_pipeline, config)


class AdaptiveRenderer:
    """Adaptive renderer that can switch between different output formats."""

    def __init__(
        self,
        core_handlers: list[CoreTagHandler],
        hyperlink_manager: HyperlinkManager | None = None,
        content_tracker: ContentTracker | None = None,
    ) -> None:
        """Initialize adaptive renderer with core services.

        Args:
            core_handlers: Core business logic handlers
            hyperlink_manager: Hyperlink manager service
            content_tracker: Content tracker service
        """
        self.core_handlers = core_handlers
        self.hyperlink_manager = hyperlink_manager
        self.content_tracker = content_tracker

        # Cache renderers by format
        self._renderer_cache: dict[str, StandardUnifiedRenderer] = {}

    def get_renderer(self, output_format: str) -> StandardUnifiedRenderer:
        """Get or create a renderer for the specified output format.

        Args:
            output_format: Target output format (latex, html, markdown)

        Returns:
            Configured unified renderer for the format
        """
        if output_format not in self._renderer_cache:
            self._renderer_cache[output_format] = self._create_renderer(output_format)

        return self._renderer_cache[output_format]

    def render_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Render a tag using the appropriate format-specific renderer.

        Args:
            node: Tag node to render
            context: Rendering context with output format

        Returns:
            Rendered tag for the specified format
        """
        renderer = self.get_renderer(context.output_format)
        return renderer.render_tag(node, context)

    def _create_renderer(self, output_format: str) -> StandardUnifiedRenderer:
        """Create a renderer for the specified output format.

        Args:
            output_format: Target output format

        Returns:
            Configured renderer for the format
        """
        if output_format.lower() == "latex":
            return StandardUnifiedRenderer.create_latex_renderer(
                self.core_handlers,
                self.hyperlink_manager,
                self.content_tracker,
            )
        elif output_format.lower() == "html":
            return StandardUnifiedRenderer.create_html_renderer(
                self.core_handlers,
                self.hyperlink_manager,
                self.content_tracker,
            )
        elif output_format.lower() == "markdown":
            return StandardUnifiedRenderer.create_markdown_renderer(
                self.core_handlers,
                self.content_tracker,
            )
        else:
            logger.warning(f"Unknown output format '{output_format}', using LaTeX")
            return StandardUnifiedRenderer.create_latex_renderer(
                self.core_handlers,
                self.hyperlink_manager,
                self.content_tracker,
            )


class EnhancementPipelineBuilder:
    """Builder for creating custom enhancement pipelines."""

    def __init__(self) -> None:
        """Initialize empty pipeline builder."""
        self.enhancers: list = []

    def add_latex_formatting(self, priority: int = 100) -> EnhancementPipelineBuilder:
        """Add LaTeX formatting enhancer.

        Args:
            priority: Pipeline priority for this enhancer

        Returns:
            Builder instance for chaining
        """
        from .enhancers import LaTeXFormatEnhancer

        self.enhancers.append(LaTeXFormatEnhancer(priority))
        return self

    def add_hyperlinks(self, priority: int = 200) -> EnhancementPipelineBuilder:
        """Add hyperlink enhancer.

        Args:
            priority: Pipeline priority for this enhancer

        Returns:
            Builder instance for chaining
        """
        from .enhancers import HyperlinkEnhancer

        self.enhancers.append(HyperlinkEnhancer(priority))
        return self

    def add_content_tracking(self, priority: int = 300) -> EnhancementPipelineBuilder:
        """Add content tracking enhancer.

        Args:
            priority: Pipeline priority for this enhancer

        Returns:
            Builder instance for chaining
        """
        from .enhancers import ContentTrackerEnhancer

        self.enhancers.append(ContentTrackerEnhancer(priority))
        return self

    def add_validation(self, priority: int = 400) -> EnhancementPipelineBuilder:
        """Add validation enhancer.

        Args:
            priority: Pipeline priority for this enhancer

        Returns:
            Builder instance for chaining
        """
        from .enhancers import ValidationEnhancer

        self.enhancers.append(ValidationEnhancer(priority))
        return self

    def add_custom_enhancer(
        self, enhancer: TagHandlerEnhancer
    ) -> EnhancementPipelineBuilder:
        """Add a custom enhancer.

        Args:
            enhancer: Custom enhancer implementing TagHandlerEnhancer

        Returns:
            Builder instance for chaining
        """
        self.enhancers.append(enhancer)
        return self

    def build(self) -> EnhancementPipeline:
        """Build the enhancement pipeline.

        Returns:
            Configured enhancement pipeline
        """
        if not self.enhancers:
            # Default to basic pipeline if none specified
            return EnhancementPipeline(create_plain_text_enhancement_pipeline())

        return EnhancementPipeline(self.enhancers.copy())

    def build_composite(self) -> CompositeEnhancer:
        """Build a composite enhancer containing all configured enhancers.

        Returns:
            Composite enhancer with all configured enhancers
        """
        if not self.enhancers:
            # Default to basic enhancers if none specified
            self.enhancers = create_plain_text_enhancement_pipeline()

        return CompositeEnhancer(self.enhancers.copy())


# Convenience functions for common renderer configurations


def create_simple_latex_renderer(
    core_handlers: list[CoreTagHandler],
) -> StandardUnifiedRenderer:
    """Create a simple LaTeX renderer with minimal configuration.

    Args:
        core_handlers: Core business logic handlers

    Returns:
        LaTeX renderer with default settings
    """
    return StandardUnifiedRenderer.create_latex_renderer(
        core_handlers,
        enable_hyperlinks=False,  # Simplified - no hyperlinks
        enable_content_tracking=False,  # Simplified - no tracking
    )


def create_full_latex_renderer(
    core_handlers: list[CoreTagHandler],
    hyperlink_manager: HyperlinkManager,
    content_tracker: ContentTracker,
) -> StandardUnifiedRenderer:
    """Create a full-featured LaTeX renderer with all enhancements.

    Args:
        core_handlers: Core business logic handlers
        hyperlink_manager: Hyperlink manager service
        content_tracker: Content tracker service

    Returns:
        LaTeX renderer with all features enabled
    """
    return StandardUnifiedRenderer.create_latex_renderer(
        core_handlers,
        hyperlink_manager,
        content_tracker,
        enable_hyperlinks=True,
        enable_content_tracking=True,
    )


def create_debug_renderer(
    core_handlers: list[CoreTagHandler],
    output_format: str = "latex",
) -> StandardUnifiedRenderer:
    """Create a renderer optimized for debugging with enhanced validation.

    Args:
        core_handlers: Core business logic handlers
        output_format: Target output format

    Returns:
        Renderer configured for debugging
    """
    # Build pipeline with emphasis on validation
    builder = EnhancementPipelineBuilder()

    if output_format.lower() == "latex":
        builder.add_latex_formatting(100)

    builder.add_validation(200)  # Validation runs early for debugging
    builder.add_content_tracking(300)

    pipeline = builder.build()

    config = EnhancementConfiguration(
        output_format=output_format,
        enable_hyperlinks=False,  # Simplified for debugging
        enable_content_tracking=True,
        enable_latex_formatting=(output_format.lower() == "latex"),
    )

    return StandardUnifiedRenderer(core_handlers, pipeline, config)
