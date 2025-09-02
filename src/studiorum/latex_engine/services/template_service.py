"""Template service implementation for LaTeX document generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger
from studiorum.renderers.core.interfaces import RenderingContext

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.core.services.protocols import OmnidexerProtocol, TagResolverProtocol
    from studiorum.core.text.protocols import TextExtractionProtocol
    from studiorum.core.text.tag_resolver import TagResolver
    from studiorum.latex_engine.formatters.protocols import LaTeXFormattingProtocol
    from studiorum.latex_engine.services.context_bound_template_service import (
        ContextBoundTemplateService,
    )
    from studiorum.latex_engine.services.protocols import ContextBoundTemplateProtocol

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
        tag_resolver: TagResolverProtocol,
        omnidexer: OmnidexerProtocol,
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

    def render_entry_description(
        self,
        entry: Any,
        content_tracker: ContentTracker,
    ) -> str:
        """Render entry description with explicit context passing.

        This method provides a context-aware alternative to the problematic
        get_description_text() methods that used stack inspection.

        Args:
            entry: Entry object containing description data
            content_tracker: Content tracker for appendix generation

        Returns:
            Rendered description text suitable for LaTeX templates
        """
        if entry is None:
            return ""

        # 1. Extract text from entry using injected component
        text = self.text_extractor.extract_from_entry(entry)
        if not text:
            return ""

        # 2. Create rendering context with content tracker
        rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=content_tracker,
            tag_resolver=self.tag_resolver,
            debug_mode=False,
        )

        # 3. Process the text using the tag resolver with explicit context
        try:
            processed_text = self.tag_resolver.process_text(text, rendering_context)
            # 4. Apply LaTeX formatting using injected component
            return self.latex_formatter.format_text(processed_text, entry)
        except Exception as e:
            logger.warning(f"Failed to process entry text: {e}")
            # Fallback to escaped raw text
            return self.latex_formatter.escape_latex_chars(text)

    def render_entry_content_only(
        self,
        entry: Any,
        content_tracker: ContentTracker,
    ) -> str:
        """Render entry content without the entry name.

        This is useful for higher level entries where the name is handled
        separately in the template (e.g., as \\paragraph{}).

        Args:
            entry: Entry object containing description data
            content_tracker: Content tracker for appendix generation

        Returns:
            Rendered content text without the entry name
        """
        if entry is None:
            return ""

        # 1. Extract only the content from entry using injected component
        text = self.text_extractor.extract_content_only_from_entry(entry)
        if not text:
            return ""

        # 2. Create rendering context with content tracker
        rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=content_tracker,
            tag_resolver=self.tag_resolver,
            debug_mode=False,
        )

        # 3. Process the text using the tag resolver with explicit context
        try:
            processed_text = self.tag_resolver.process_text(text, rendering_context)
            # 4. Apply LaTeX formatting using injected component
            return self.latex_formatter.format_text(processed_text, entry)
        except Exception as e:
            logger.warning(f"Failed to process entry text: {e}")
            # Fallback to escaped raw text
            return self.latex_formatter.escape_latex_chars(text)

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
