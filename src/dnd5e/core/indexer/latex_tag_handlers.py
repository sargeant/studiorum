"""Enhanced tag handlers with LaTeX-specific features for cross-references and hyperlinks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .content_tracker import ContentTracker
from .cross_reference_manager import CrossReferenceManager
from .hyperlink_manager import HyperlinkManager
from .tag_ast import TagNode
from .tag_handlers import (
    AdventureTagHandler,
    BaseContentTagHandler,
    BookTagHandler,
    ConditionTagHandler,
    TagHandler,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .latex_tag_renderer import LaTeXRendererContext


class LaTeXBaseContentTagHandler(BaseContentTagHandler):
    """Enhanced base handler for content reference tags with LaTeX cross-references."""

    def __init__(self, tag_type: str, latex_format: str):
        super().__init__(tag_type, latex_format)

    def render(self, node: TagNode, context: LaTeXRendererContext) -> str:
        """Render content reference with LaTeX enhancements."""
        # Get display text
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            display_text = "".join(
                context.render_node(child) for child in node.display_text_nodes
            )
        else:
            display_text = getattr(node, "name", str(node))

        # Escape LaTeX special characters
        display_text = self._escape_latex(display_text)

        # Apply base formatting
        formatted_text = self.latex_format.format(display_text)

        # Add LaTeX enhancements if in LaTeX mode
        if hasattr(context, "latex_mode") and context.latex_mode:
            return self._add_latex_enhancements(node, formatted_text, context)

        return formatted_text

    def _add_latex_enhancements(
        self, node: TagNode, formatted_text: str, context: LaTeXRendererContext
    ) -> str:
        """Add cross-references and hyperlinks to formatted text."""
        name = getattr(node, "name", "")
        if not name:
            return formatted_text

        # Register with cross-reference manager
        if context.cross_ref_manager:
            ref_id = context.cross_ref_manager.register_content(
                content_type=self.tag_type,
                name=name,
                source=getattr(node, "source", None),
                page=getattr(node, "page", None),
            )

            # Create hyperlink if enabled
            if (
                context.hyperlink_manager
                and context.hyperlink_manager.should_create_hyperlink(self.tag_type)
            ):
                return context.hyperlink_manager.create_hyperlink(
                    text=formatted_text, ref_id=ref_id, content_type=self.tag_type
                )

        return formatted_text


class LaTeXCreatureTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced creature tag handler with cross-references."""

    def __init__(self):
        super().__init__("creature", "\\textbf{{{}}}")


class LaTeXSpellTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced spell tag handler with cross-references."""

    def __init__(self):
        super().__init__("spell", "\\textit{{{}}}")


class LaTeXItemTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced item tag handler with cross-references."""

    def __init__(self):
        super().__init__("item", "\\textit{{{}}}")


class LaTeXClassTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced class tag handler with cross-references."""

    def __init__(self):
        super().__init__("class", "\\textbf{{{}}}")


class LaTeXRaceTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced race tag handler with cross-references."""

    def __init__(self):
        super().__init__("race", "{}")  # No special formatting for races


class LaTeXBackgroundTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced background tag handler with cross-references."""

    def __init__(self):
        super().__init__("background", "{}")  # No special formatting


class LaTeXFeatTagHandler(LaTeXBaseContentTagHandler):
    """Enhanced feat tag handler with cross-references."""

    def __init__(self):
        super().__init__("feat", "\\textbf{{{}}}")


class LaTeXConditionTagHandler(ConditionTagHandler):
    """Enhanced condition tag handler with cross-references."""

    def render(self, node: TagNode, context: LaTeXRendererContext) -> str:
        """Render condition with potential cross-reference."""
        condition = getattr(node, "condition", "")
        formatted_text = f"\\textit{{{condition}}}"

        # Add LaTeX enhancements if in LaTeX mode
        if hasattr(context, "latex_mode") and context.latex_mode and condition:
            return self._add_condition_enhancements(condition, formatted_text, context)

        return formatted_text

    def _add_condition_enhancements(
        self, condition: str, formatted_text: str, context: LaTeXRendererContext
    ) -> str:
        """Add cross-references for conditions."""
        # Register condition for cross-referencing
        if context.cross_ref_manager:
            ref_id = context.cross_ref_manager.register_content(
                content_type="condition", name=condition
            )

            # Create hyperlink for conditions
            if (
                context.hyperlink_manager
                and context.hyperlink_manager.should_create_hyperlink("condition")
            ):
                return context.hyperlink_manager.create_hyperlink(
                    text=formatted_text, ref_id=ref_id, content_type="condition"
                )

        return formatted_text


class LaTeXAdventureTagHandler(AdventureTagHandler):
    """Enhanced adventure tag handler with cross-references."""

    def render(self, node: TagNode, context: LaTeXRendererContext) -> str:
        """Render adventure reference with enhancements."""
        # Get base rendering
        base_text = super().render(node, context)

        # Add LaTeX enhancements if in LaTeX mode
        if hasattr(context, "latex_mode") and context.latex_mode:
            return self._add_adventure_enhancements(node, base_text, context)

        return base_text

    def _add_adventure_enhancements(
        self, node: TagNode, base_text: str, context: LaTeXRendererContext
    ) -> str:
        """Add cross-references for adventure content."""
        name = getattr(node, "name", "")
        if not name:
            return base_text

        # Register adventure for cross-referencing
        if context.cross_ref_manager:
            ref_id = context.cross_ref_manager.register_content(
                content_type="adventure",
                name=name,
                source=getattr(node, "source", None),
                page=getattr(node, "page", None),
            )

            # Create hyperlink if enabled
            if (
                context.hyperlink_manager
                and context.hyperlink_manager.should_create_hyperlink("adventure")
            ):
                # Extract just the adventure name for hyperlink, keep page reference
                if " (p. " in base_text:
                    adventure_part, page_part = base_text.split(" (p. ", 1)
                    hyperlinked_adventure = context.hyperlink_manager.create_hyperlink(
                        text=f"\\textit{{{adventure_part}}}",
                        ref_id=ref_id,
                        content_type="adventure",
                        include_page_ref=False,
                    )
                    return f"{hyperlinked_adventure} (p. {page_part}"
                else:
                    return context.hyperlink_manager.create_hyperlink(
                        text=f"\\textit{{{base_text}}}",
                        ref_id=ref_id,
                        content_type="adventure",
                    )

        return f"\\textit{{{base_text}}}"  # At least italicize adventure names


class LaTeXBookTagHandler(BookTagHandler):
    """Enhanced book tag handler with cross-references."""

    def render(self, node: TagNode, context: LaTeXRendererContext) -> str:
        """Render book reference with enhancements."""
        # Get base rendering
        base_text = super().render(node, context)

        # Add LaTeX enhancements if in LaTeX mode
        if hasattr(context, "latex_mode") and context.latex_mode:
            return self._add_book_enhancements(node, base_text, context)

        return base_text

    def _add_book_enhancements(
        self, node: TagNode, base_text: str, context: LaTeXRendererContext
    ) -> str:
        """Add cross-references for book content."""
        name = getattr(node, "name", "")
        if not name:
            return base_text

        # Register book for cross-referencing
        if context.cross_ref_manager:
            ref_id = context.cross_ref_manager.register_content(
                content_type="book",
                name=name,
                source=getattr(node, "source", None),
                page=getattr(node, "page", None),
            )

            # Create hyperlink if enabled
            if (
                context.hyperlink_manager
                and context.hyperlink_manager.should_create_hyperlink("book")
            ):
                # Extract just the book name for hyperlink, keep page reference
                if ", p. " in base_text:
                    book_part, page_part = base_text.split(", p. ", 1)
                    hyperlinked_book = context.hyperlink_manager.create_hyperlink(
                        text=f"\\textit{{{book_part}}}",
                        ref_id=ref_id,
                        content_type="book",
                        include_page_ref=False,
                    )
                    return f"{hyperlinked_book}, p. {page_part}"
                else:
                    return context.hyperlink_manager.create_hyperlink(
                        text=f"\\textit{{{base_text}}}",
                        ref_id=ref_id,
                        content_type="book",
                    )

        return f"\\textit{{{base_text}}}"  # At least italicize book names


class LaTeXScaledDiceTagHandler(TagHandler):
    """Handler for scaled dice expressions with level scaling."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "scaledice"

    def render(self, node: TagNode, context: LaTeXRendererContext) -> str:
        """Render scaled dice expression."""
        # Extract scaled dice information
        expression = getattr(node, "expression", "")
        scaling = getattr(node, "scaling", "")

        if scaling:
            return f"\\texttt{{{expression}}} ({scaling})"
        else:
            return f"\\texttt{{{expression}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Scaled dice tags don't need content tracking."""
        pass


class LaTeXFilterTagHandler(TagHandler):
    """Enhanced filter tag handler that can optionally preserve content for debugging."""

    def __init__(self, preserve_for_debug: bool = False):
        self.preserve_for_debug = preserve_for_debug

    def handles(self, tag_type: str) -> bool:
        return tag_type == "filter"

    def render(self, node: TagNode, context: LaTeXRendererContext) -> str:
        """Render filter tag (usually empty)."""
        if self.preserve_for_debug:
            # Preserve filter content as LaTeX comment for debugging
            filter_content = getattr(node, "filter_expression", "")
            return f"% Filter: {filter_content}\n"
        return ""

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Filter tags don't need content tracking."""
        pass


def get_latex_enhanced_handlers(
    preserve_debug_filters: bool = False,
) -> list[TagHandler]:
    """Get list of LaTeX-enhanced tag handlers."""
    return [
        # Enhanced content reference handlers
        LaTeXCreatureTagHandler(),
        LaTeXSpellTagHandler(),
        LaTeXItemTagHandler(),
        LaTeXClassTagHandler(),
        LaTeXRaceTagHandler(),
        LaTeXBackgroundTagHandler(),
        LaTeXFeatTagHandler(),
        LaTeXConditionTagHandler(),
        # Enhanced reference handlers
        LaTeXAdventureTagHandler(),
        LaTeXBookTagHandler(),
        # New LaTeX-specific handlers
        LaTeXScaledDiceTagHandler(),
        LaTeXFilterTagHandler(preserve_debug_filters),
    ]


def register_latex_handlers(
    renderer, cross_ref_manager: CrossReferenceManager | None = None
):
    """Register LaTeX-enhanced handlers with a renderer."""
    # Get LaTeX handlers
    latex_handlers = get_latex_enhanced_handlers()

    # Register each handler
    for handler in latex_handlers:
        renderer.register_handler(handler)

    # Set up cross-reference manager if provided
    if cross_ref_manager and hasattr(renderer, "cross_ref_manager"):
        renderer.cross_ref_manager = cross_ref_manager

    logger.info(f"Registered {len(latex_handlers)} LaTeX-enhanced tag handlers")


def create_content_reference_factory(
    content_types: dict[str, str],
) -> dict[str, type[LaTeXBaseContentTagHandler]]:
    """Factory for creating content reference handlers dynamically."""
    handlers = {}

    for content_type, latex_format in content_types.items():
        # Create closure to capture variables
        def create_handler_class(ct, lf):
            class DynamicContentHandler(LaTeXBaseContentTagHandler):
                def __init__(self):
                    super().__init__(ct, lf)

            return DynamicContentHandler

        HandlerClass = create_handler_class(content_type, latex_format)

        # Set a proper class name
        HandlerClass.__name__ = f"LaTeX{content_type.title()}TagHandler"
        handlers[content_type] = HandlerClass

    return handlers
