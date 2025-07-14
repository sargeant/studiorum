"""Tag renderer and dispatcher for the new tag system."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .content_tracker import ContentTracker
from .tag_ast import ASTNode, DocumentNode, TagNode, TextNode
from .tag_handlers import TagHandler, get_default_handlers

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ...loaders.omnidexer import Omnidexer


class RendererContext:
    """Context object passed to handlers during rendering."""

    def __init__(
        self, renderer: "TagRenderer", omnidexer: Optional["Omnidexer"] = None
    ):
        self.renderer = renderer
        self.omnidexer = omnidexer
        self.content_tracker = renderer.content_tracker

    def render_node(self, node: ASTNode) -> str:
        """Render a node using the renderer."""
        return self.renderer.render_node(node, self)


class TagRenderer:
    """Main renderer/dispatcher for tag processing."""

    def __init__(self, omnidexer: Optional["Omnidexer"] = None):
        self.omnidexer = omnidexer
        self.content_tracker = ContentTracker()
        self._handlers: Dict[str, TagHandler] = {}

        # Register default handlers
        for handler in get_default_handlers():
            self.register_handler(handler)

    def register_handler(self, handler: TagHandler) -> None:
        """Register a tag handler."""
        # Find all tag types this handler can handle
        for tag_type in self._get_handler_types(handler):
            self._handlers[tag_type] = handler

    def _get_handler_types(self, handler: TagHandler) -> List[str]:
        """Get all tag types a handler can process."""
        # This is a simple implementation - in practice, you might want
        # handlers to declare their types more explicitly
        common_types = [
            "creature",
            "spell",
            "item",
            "class",
            "race",
            "background",
            "feat",
            "bold",
            "b",
            "italic",
            "i",
            "dice",
            "hit",
            "dc",
            "damage",
            "condition",
            "chance",
            "recharge",
            "adventure",
            "book",
            "filter",
            "loader",
        ]

        types = []
        for tag_type in common_types:
            if handler.handles(tag_type):
                types.append(tag_type)

        return types

    def render_document(self, document: DocumentNode) -> str:
        """Render an entire document."""
        context = RendererContext(self, self.omnidexer)
        return self.render_node(document, context)

    def render_node(
        self, node: ASTNode, context: Optional[RendererContext] = None
    ) -> str:
        """Render a single AST node."""
        if context is None:
            context = RendererContext(self, self.omnidexer)

        if isinstance(node, TextNode):
            return node.text

        elif isinstance(node, TagNode):
            # Find appropriate handler
            handler = self._handlers.get(node.tag_type)
            if handler:
                try:
                    # Track content if this is a content reference
                    handler.track_content(node, self.content_tracker)
                    # Render the tag
                    return handler.render(node, context)
                except (AttributeError, ValueError, TypeError) as e:
                    logger.warning("Tag handler failed for '%s': %s", node.tag_type, e)
                    return self._fallback_render(node)
                except Exception as e:
                    logger.error("Unexpected error in tag handler for '%s': %s", node.tag_type, e)
                    return self._fallback_render(node)
            else:
                # No handler found - use fallback
                return self._fallback_render(node)

        elif isinstance(node, DocumentNode):
            # Render all children
            return "".join(self.render_node(child, context) for child in node.children)

        else:
            # Generic node - render children
            return "".join(self.render_node(child, context) for child in node.children)

    def _fallback_render(self, node: TagNode) -> str:
        """Fallback rendering for unknown or failed tags."""
        # Try to extract meaningful content
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # Use display text
            context = RendererContext(self, self.omnidexer)
            return "".join(
                self.render_node(child, context) for child in node.display_text_nodes
            )
        elif hasattr(node, "name"):
            # Use tag name
            return str(node.name)
        else:
            # Last resort - show tag type
            return f"{{@{node.tag_type}...}}"

    def track_document_content(self, document: DocumentNode) -> None:
        """Track all content in a document without rendering."""
        self._track_node_content(document)

    def _track_node_content(self, node: ASTNode) -> None:
        """Recursively track content in a node."""
        if isinstance(node, TagNode):
            handler = self._handlers.get(node.tag_type)
            if handler:
                try:
                    handler.track_content(node, self.content_tracker)
                except (AttributeError, ValueError, TypeError) as e:
                    logger.debug("Content tracking failed for tag '%s': %s", node.tag_type, e)
                except Exception as e:
                    logger.warning("Unexpected error tracking content for '%s': %s", node.tag_type, e)

        # Track content in children
        for child in node.children:
            self._track_node_content(child)

    def get_tracked_content(self) -> List[Any]:
        """Get all tracked content for appendix generation."""
        return self.content_tracker.get_tracked_content()

    def get_tracked_content_for_appendix(self) -> Dict[str, List[Dict[str, str]]]:
        """Get tracked content formatted for appendix generation."""
        return self.content_tracker.export_for_appendix()

    def clear_tracked_content(self) -> None:
        """Clear all tracked content."""
        self.content_tracker.clear()

    def get_content_statistics(self) -> Dict[str, int]:
        """Get statistics about tracked content."""
        return self.content_tracker.get_statistics()

    def has_handler(self, tag_type: str) -> bool:
        """Check if a handler exists for the given tag type."""
        return tag_type in self._handlers

    def get_supported_tag_types(self) -> List[str]:
        """Get all supported tag types."""
        return sorted(list(self._handlers.keys()))

    def unregister_handler(self, tag_type: str) -> bool:
        """Unregister a handler for a tag type. Returns True if removed."""
        if tag_type in self._handlers:
            del self._handlers[tag_type]
            return True
        return False
