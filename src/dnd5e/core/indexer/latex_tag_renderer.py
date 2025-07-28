"""LaTeX-enhanced tag renderer for advanced cross-references and hyperlinks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dnd5e.core.logging import get_logger

from .cross_reference_manager import CrossReferenceManager
from .hyperlink_manager import HyperlinkManager
from .latex_content_tracker import LaTeXContentTracker
from .tag_ast import ASTNode, DocumentNode, TagNode
from .tag_renderer import RendererContext, TagRenderer

logger = get_logger(__name__)

if TYPE_CHECKING:
    from dnd5e.core.loaders.omnidexer import Omnidexer


class LaTeXRendererContext(RendererContext):
    """Enhanced context for LaTeX-specific rendering with cross-references."""

    def __init__(
        self,
        renderer: LaTeXTagRenderer,
        omnidexer: Omnidexer | None = None,
        cross_ref_manager: CrossReferenceManager | None = None,
        hyperlink_manager: HyperlinkManager | None = None,
    ):
        super().__init__(renderer, omnidexer)
        self.cross_ref_manager = cross_ref_manager
        self.hyperlink_manager = hyperlink_manager
        self.latex_mode = True  # Flag for handlers to enable LaTeX features


class LaTeXTagRenderer(TagRenderer):
    """Enhanced tag renderer with LaTeX-specific features for cross-references and hyperlinks."""

    def __init__(
        self,
        omnidexer: Omnidexer | None = None,
        cross_ref_manager: CrossReferenceManager | None = None,
        hyperlink_manager: HyperlinkManager | None = None,
    ):
        super().__init__(omnidexer)

        # LaTeX-specific managers
        self.cross_ref_manager = cross_ref_manager or CrossReferenceManager()
        self.hyperlink_manager = hyperlink_manager or HyperlinkManager()

        # Enhanced content tracker for LaTeX
        self.latex_content_tracker = LaTeXContentTracker()

    def render_document(self, document: DocumentNode) -> str:
        """Render document with LaTeX context."""
        context = LaTeXRendererContext(
            self, self.omnidexer, self.cross_ref_manager, self.hyperlink_manager
        )
        return self.render_node(document, context)

    def render_node(self, node: ASTNode, context: RendererContext | None = None) -> str:
        """Render node with LaTeX enhancements."""
        if context is None:
            context = LaTeXRendererContext(
                self, self.omnidexer, self.cross_ref_manager, self.hyperlink_manager
            )

        if isinstance(node, TagNode):
            # Enhanced handling for content reference tags
            if self._is_content_reference_tag(node):
                # Ensure we have LaTeX context for content references
                if not isinstance(context, LaTeXRendererContext):
                    context = LaTeXRendererContext(
                        self,
                        self.omnidexer,
                        self.cross_ref_manager,
                        self.hyperlink_manager,
                    )
                return self._render_content_reference(node, context)

        # Fall back to standard rendering
        return super().render_node(node, context)

    def _is_content_reference_tag(self, node: TagNode) -> bool:
        """Check if tag is a content reference that should get cross-references."""
        content_ref_types = {
            "creature",
            "spell",
            "item",
            "class",
            "race",
            "background",
            "feat",
            "condition",
            "adventure",
            "book",
        }
        return node.tag_type in content_ref_types

    def _render_content_reference(
        self, node: TagNode, context: LaTeXRendererContext
    ) -> str:
        """Render content reference with cross-reference and hyperlink support."""
        # Get base rendering from standard handler
        handler = self._handlers.get(node.tag_type)
        if not handler:
            return self._fallback_render(node)

        try:
            # Track content as usual
            handler.track_content(node, self.content_tracker)

            # Get base rendered text
            base_text = handler.render(node, context)

            # Add LaTeX enhancements if in LaTeX mode
            if isinstance(context, LaTeXRendererContext):
                return self._enhance_with_cross_reference(node, base_text, context)

            return base_text

        except Exception as e:
            logger.error(f"Error rendering content reference {node.tag_type}: {e}")
            return self._fallback_render(node)

    def _enhance_with_cross_reference(
        self, node: TagNode, base_text: str, context: LaTeXRendererContext
    ) -> str:
        """Enhance rendered text with cross-references and hyperlinks."""
        # Generate unique reference ID
        ref_id = self._generate_reference_id(node)

        # Register this content for cross-referencing
        if context.cross_ref_manager is not None:
            context.cross_ref_manager.register_content(
                content_type=node.tag_type,
                name=getattr(node, "name", ""),
                ref_id=ref_id,
                source=getattr(node, "source", None),
            )

        # Create hyperlinked version if enabled
        if (
            context.hyperlink_manager is not None
            and context.hyperlink_manager.should_create_hyperlink(node.tag_type)
        ):
            return context.hyperlink_manager.create_hyperlink(
                text=base_text, ref_id=ref_id, content_type=node.tag_type
            )

        return base_text

    def _generate_reference_id(self, node: TagNode) -> str:
        """Generate unique LaTeX reference ID for content."""
        # Create safe LaTeX label from content type and name
        content_type = node.tag_type
        name = getattr(node, "name", "")

        # Sanitize name for LaTeX labels
        safe_name = self._sanitize_for_label(name)

        return f"{content_type}:{safe_name}"

    def _sanitize_for_label(self, text: str | None) -> str:
        """Sanitize text for use in LaTeX labels."""
        import re

        # Handle None or empty text
        if not text:
            return "unnamed"

        # Convert to lowercase and replace non-alphanumeric with hyphens
        sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")

        # Ensure it's not empty
        return sanitized if sanitized else "unnamed"

    def get_cross_reference_database(self) -> dict[str, Any]:
        """Get all registered cross-references for document processing."""
        return self.cross_ref_manager.get_all_references()

    def get_latex_content_tracker(self) -> LaTeXContentTracker:
        """Get the enhanced content tracker."""
        return self.latex_content_tracker

    def enable_hyperlinks(self, enable: bool = True) -> None:
        """Enable or disable hyperlink generation."""
        self.hyperlink_manager.enabled = enable

    def set_cross_reference_format(self, ref_format: str) -> None:
        """Set the format for cross-references (page, section, etc.)."""
        self.cross_ref_manager.set_reference_format(ref_format)
