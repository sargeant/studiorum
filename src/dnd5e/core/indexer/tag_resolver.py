"""Modern AST-based tag resolution system."""

from collections.abc import Callable
from typing import Any

from dnd5e.core.logging import get_logger

from .tag_handlers import TagHandler
from .tag_parser import TagParseError, TagParser
from .tag_renderer import TagRenderer

logger = get_logger(__name__)


class TagResolver:
    """Modern AST-based tag resolver providing comprehensive tag processing."""

    def __init__(self, omnidexer: Any = None) -> None:
        self.omnidexer = omnidexer
        self.parser = TagParser()
        self.renderer = TagRenderer(omnidexer)

        # For backward compatibility with custom handlers
        self._custom_handlers: dict[str, Callable] = {}

    def process_text(self, text: str) -> str:
        """Process text with tags and return rendered output.

        This method maintains compatibility with the old TagResolver.process_text API.
        """
        if not text:
            return text

        try:
            # Parse text to AST
            document = self.parser.parse(text)

            # Render AST to output
            return self.renderer.render_document(document)

        except TagParseError as e:
            logger.warning("Tag parsing failed for text '%s': %s", text[:50], e)
            return text
        except Exception as e:
            logger.error(
                "Unexpected error processing tags in text '%s': %s", text[:50], e
            )
            return text

    def register_tag_handler(self, tag_type: str, handler_func: Callable) -> None:
        """Register a custom tag handler function.

        Note: Legacy function-based handlers are deprecated.
        Please implement TagHandler interface instead.
        """
        self._custom_handlers[tag_type] = handler_func
        raise NotImplementedError(
            "Function-based handler registration is deprecated. "
            "Please implement TagHandler interface instead."
        )

    def register_handler(self, handler: TagHandler) -> None:
        """Register a new-style tag handler."""
        self.renderer.register_handler(handler)

    def get_tracked_content_for_appendix(self) -> list[tuple]:
        """Get tracked content for appendix generation.

        Returns content in the format: [(type, name, source), ...]
        """
        tracked_content = self.renderer.get_tracked_content()
        return [content.to_tuple() for content in tracked_content]

    def get_tracked_content_detailed(self) -> dict[str, list[dict[str, str | int]]]:
        """Get detailed tracked content for appendix generation."""
        return self.renderer.get_tracked_content_for_appendix()

    def clear_tracked_content(self) -> None:
        """Clear all tracked content."""
        self.renderer.clear_tracked_content()

    def get_content_statistics(self) -> dict[str, int]:
        """Get statistics about tracked content."""
        return self.renderer.get_content_statistics()

    def track_document_content(self, text: str) -> None:
        """Track content in a document without rendering."""
        try:
            document = self.parser.parse(text)
            self.renderer.track_document_content(document)
        except TagParseError as e:
            logger.debug("Tag parsing failed during content tracking: %s", e)
        except Exception as e:
            logger.warning("Unexpected error tracking document content: %s", e)

    def get_supported_tag_types(self) -> list[str]:
        """Get all supported tag types."""
        return self.renderer.get_supported_tag_types()

    def has_handler(self, tag_type: str) -> bool:
        """Check if a handler exists for the given tag type."""
        return self.renderer.has_handler(tag_type)

    # Backward compatibility properties and methods
    @property
    def _tag_handlers(self) -> dict[str, Any]:
        """Backward compatibility property."""
        # Return a dict-like view of handlers for backward compatibility
        return self._custom_handlers
