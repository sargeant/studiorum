"""Modern AST-based tag resolution system."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from dnd5e.core.logging import get_logger
from dnd5e.renderers.core.handlers import get_default_core_handlers
from dnd5e.renderers.core.interfaces import RenderingContext, TagHandler
from dnd5e.renderers.core.unified_renderer import StandardUnifiedRenderer

from .tag_parser import TagParseError, TagParser

logger = get_logger(__name__)


class TagResolver(BaseModel):
    """Modern AST-based tag resolver providing comprehensive tag processing."""

    omnidexer: Any = Field(None, description="Content indexer for tag resolution")
    parser: TagParser = Field(
        default_factory=TagParser, description="Tag parser instance"
    )
    renderer: StandardUnifiedRenderer = Field(
        description="Core unified renderer instance"
    )
    rendering_context: RenderingContext = Field(
        description="Rendering context for tag processing"
    )
    custom_handlers: dict[str, Callable] = Field(
        default_factory=dict, description="Custom handlers for backward compatibility"
    )

    def __init__(self, omnidexer: Any = None, **data: Any) -> None:
        # Create renderer with core handlers
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)

        # Create rendering context
        rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=omnidexer,
            content_tracker=None,  # Will be set if needed
            debug_mode=False,
        )

        # Call parent constructor with computed fields
        super().__init__(
            omnidexer=omnidexer,
            renderer=renderer,
            rendering_context=rendering_context,
            **data,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def process_text(self, text: str, context: RenderingContext | None = None) -> str:
        """Process text with tags and return rendered output.

        This method processes text using the modern core architecture.

        Args:
            text: Text to process with tags
            context: Optional rendering context to override default context,
                    particularly useful for passing ContentTracker
        """
        if not text:
            return text

        try:
            # Parse text to AST
            document = self.parser.parse(text)

            # Determine which context to use for rendering
            render_context = self.rendering_context
            if context:
                # Merge external context with internal context
                # This is especially important for ContentTracker integration
                render_context = RenderingContext(
                    output_format=context.output_format
                    or self.rendering_context.output_format,
                    omnidexer=context.omnidexer or self.rendering_context.omnidexer,
                    content_tracker=context.content_tracker
                    or self.rendering_context.content_tracker,
                    debug_mode=context.debug_mode
                    if context.debug_mode is not None
                    else self.rendering_context.debug_mode,
                    metadata={**self.rendering_context.metadata, **context.metadata},
                )

                # Update renderer's enhancement configuration with new ContentTracker
                if context.content_tracker and hasattr(
                    self.renderer, "enhancement_config"
                ):
                    self.renderer.enhancement_config.content_tracker = (
                        context.content_tracker
                    )

            # Render each node in the document
            result_parts = []
            for node in document.children:
                # Import here to avoid circular imports
                from dnd5e.core.text.tag_ast import TagNode, TextNode

                if isinstance(node, TagNode):  # TagNode
                    rendered = self.renderer.render_tag(node, render_context)
                    result_parts.append(rendered)
                elif isinstance(node, TextNode):  # TextNode - extract and escape text
                    from dnd5e.core.latex_utils import escape_latex_text

                    result_parts.append(escape_latex_text(node.text))
                else:  # Other node types
                    result_parts.append(str(node))

            return "".join(result_parts)

        except TagParseError as e:
            logger.warning(f"Tag parsing failed for text '{text[:50]}': {e}")
            return text
        except Exception as e:
            logger.error(f"Unexpected error processing tags in text '{text[:50]}': {e}")
            return text

    def register_handler(self, handler: TagHandler) -> None:
        """Register a new core tag handler."""
        # Add to the core handlers list
        self.renderer.core_handlers.append(handler)

    def get_supported_tag_types(self) -> list[str]:
        """Get all supported tag types from registered core handlers."""
        tag_types = []
        for handler in self.renderer.core_handlers:
            if hasattr(handler, "supported_tags"):
                tag_types.extend(handler.supported_tags)
        return list(set(tag_types))  # Remove duplicates

    def has_handler(self, tag_type: str) -> bool:
        """Check if a handler exists for the given tag type."""
        for handler in self.renderer.core_handlers:
            if hasattr(handler, "handles_tag_type") and handler.handles_tag_type(
                tag_type
            ):
                return True
        return False
