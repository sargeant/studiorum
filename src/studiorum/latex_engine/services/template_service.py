"""Template service implementation for LaTeX document generation."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import TYPE_CHECKING

from studiorum.core.logging import get_logger
from studiorum.renderers.context import RenderingContext

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.core.text.protocols import TextExtractionProtocol
    from studiorum.latex_engine.formatters.protocols import LaTeXFormattingProtocol
    from studiorum.latex_engine.services.protocols import ContextBoundTemplateProtocol
    from studiorum.renderers.tags import TagResolver

logger = get_logger(__name__)


class TemplateService:
    """Template service for orchestrating entry processing with component injection.

    This service coordinates TextExtractor, TagResolver, and LaTeXFormatter
    components to provide clean entry rendering without parameter threading.
    """

    def __init__(
        self,
        text_extractor: TextExtractionProtocol,
        latex_formatter: LaTeXFormattingProtocol,
        tag_resolver: TagResolver,
        omnidexer: Omnidexer,
    ) -> None:
        """Initialize the template service with injected components.

        Args:
            text_extractor: Component for extracting text from entries
            latex_formatter: Component for LaTeX formatting
            tag_resolver: Tag resolver service for processing tags
            omnidexer: Omnidexer service for content resolution
        """
        self.text_extractor = text_extractor
        self.latex_formatter = latex_formatter
        self.tag_resolver = tag_resolver
        self.omnidexer = omnidexer

    def get_service_name(self) -> str:
        """Return service name for debugging."""
        return "TemplateService"

    def bind_context(
        self, content_tracker: ContentTracker
    ) -> ContextBoundTemplateProtocol:
        """Create a context-bound service with clean APIs.

        Args:
            content_tracker: ContentTracker to bind for all operations

        Returns:
            ContextBoundTemplateService with injected context
        """
        from studiorum.latex_engine.services.context_bound_template_service import (
            ContextBoundTemplateService,
        )

        return ContextBoundTemplateService(self, content_tracker)

    # Legacy method render_entry_description removed - use RecursiveEntryProcessor instead

    # Legacy API removed: render_entry_content_only

    # Legacy API removed: render_entry_content_only

    def process_field_text(self, text: str) -> str:
        """Process text that may contain embedded tags and return LaTeX-safe output.

        This is used for spell fields like casting time that may contain embedded
        tags like {@variantrule ...} that need to be rendered.

        Args:
            text: Raw text that may contain embedded tags

        Returns:
            Processed text with tags rendered and LaTeX-escaped
        """
        if not text:
            return ""

        # Create a minimal rendering context for processing field text
        rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=None,  # Field text processing doesn't need appendix tracking
            tag_resolver=self.tag_resolver,
            debug_mode=False,
        )

        try:
            # Process any embedded tags in the text
            processed_text = self.tag_resolver.process_text(text, rendering_context)
            # Apply LaTeX escaping to the final result
            return self.latex_formatter.escape_latex_chars(processed_text)
        except Exception as e:
            logger.warning(f"Failed to process field text tags: {e}")
            # Fallback to escaped raw text
            return self.latex_formatter.escape_latex_chars(text)


# The CLI registers where templates get their TemplateService until the render
# pipeline takes it as a parameter (restructure step 10).
_template_service_provider: ContextVar[Callable[[], TemplateService] | None] = (
    ContextVar("_template_service_provider", default=None)
)


def set_template_service_provider(
    provider: Callable[[], TemplateService] | None,
) -> None:
    """Set the function that returns the TemplateService templates should use."""
    _template_service_provider.set(provider)


def active_template_service() -> TemplateService | None:
    """The registered TemplateService, or None when nothing has registered one."""
    provider = _template_service_provider.get()
    return provider() if provider is not None else None
