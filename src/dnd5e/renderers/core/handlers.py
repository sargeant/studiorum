"""Core tag handlers containing consolidated business logic.

These handlers extract and process tag content according to business rules,
without any presentation-specific formatting. They return structured data
that can be enhanced by presentation layers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dnd5e.core.logging import get_logger
from dnd5e.core.models.content import ContentType

from .interfaces import (
    ContentReferenceInfo,
    CoreTagHandler,
    FormatStyle,
    RenderingContext,
    TagValidationError,
)

if TYPE_CHECKING:
    from dnd5e.core.text.tag_ast import TagNode
    from dnd5e.core.text.tag_types import FormattingNode, SpecialTag

logger = get_logger(__name__)


class BaseCoreTagHandler:
    """Base implementation for core tag handlers with common business logic."""

    def __init__(self, tag_type: str, content_type: ContentType | None = None) -> None:
        """Initialize the core handler.

        Args:
            tag_type: Type of tag this handler processes
            content_type: Content type for validation (optional)
        """
        self.tag_type = tag_type
        self.content_type = content_type
        # For compatibility with registration systems that expect supported_tags
        self.supported_tags = [tag_type]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == self.tag_type

    def should_include_page_reference(self, page: str | None) -> bool:
        """Business rule: Don't show page '1' in references."""
        return page is not None and page != "1"

    def _extract_display_text(self, node: TagNode, context: RenderingContext) -> str:
        """Extract display text using the standard priority order.

        Priority:
        1. display_text_nodes (if available and not empty)
        2. name attribute
        3. string representation of node

        Args:
            node: Tag node to extract text from
            context: Rendering context for recursive rendering

        Returns:
            Display text for the tag
        """
        # Check for display_text_nodes first (highest priority)
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # This would normally require recursive rendering through context
            # For now, we'll extract the basic text content
            # TODO: Implement proper recursive display text rendering
            display_parts = []
            for child_node in node.display_text_nodes:
                if hasattr(child_node, "text"):
                    display_parts.append(str(child_node.text))
                else:
                    display_parts.append(str(child_node))
            return "".join(display_parts)

        # Fallback to name attribute
        if hasattr(node, "name") and node.name is not None:
            return str(node.name)

        # Final fallback to string representation
        return str(node)

    def _extract_page_info(self, node: TagNode) -> str | None:
        """Extract page information from node."""
        page = getattr(node, "page", None)
        # Handle Mock objects from tests - they should be treated as None unless explicitly set to a string
        if page is not None and not isinstance(page, str):
            return None
        return page

    def _extract_source_info(self, node: TagNode) -> str | None:
        """Extract source information from node."""
        source = getattr(node, "source", None)
        # Handle Mock objects from tests - they should be treated as None unless explicitly set to a string
        if source is not None and not isinstance(source, str):
            return None
        return source

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Validate content reference using omnidexer if available."""
        errors: list[TagValidationError] = []

        # Skip validation if no content type or omnidexer
        if not self.content_type or not context.omnidexer:
            return errors

        name = getattr(node, "name", None)
        if not name:
            return errors  # No name to validate

        source = self._extract_source_info(node)

        try:
            content = context.omnidexer.find(self.content_type, name, source)
            if content is None:
                source_info = f" from {source}" if source else ""
                errors.append(
                    TagValidationError(
                        error_type="missing_content",
                        message=f"Invalid {self.tag_type} reference: '{name}'{source_info} not found",
                        tag_type=self.tag_type,
                        tag_name=name,
                        source=source,
                    )
                )
        except Exception as e:
            # Log but don't fail on validation errors
            logger.debug(f"Error validating {self.tag_type} reference '{name}': {e}")

        return errors

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Register content with tracker for appendix generation."""
        if not context.content_tracker:
            return

        name = getattr(node, "name", None)
        if name:
            source = self._extract_source_info(node)
            page = self._extract_page_info(node)
            context.content_tracker.add_content(self.tag_type, name, source, page)


class CoreCreatureTagHandler(BaseCoreTagHandler):
    """Core handler for creature reference tags."""

    def __init__(self) -> None:
        super().__init__("creature", ContentType.CREATURE)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract creature reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.BOLD,  # Creatures are formatted in bold
        )


class CoreSpellTagHandler(BaseCoreTagHandler):
    """Core handler for spell reference tags."""

    def __init__(self) -> None:
        super().__init__("spell", ContentType.SPELL)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract spell reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.ITALIC,  # Spells are formatted in italic
        )


class CoreItemTagHandler(BaseCoreTagHandler):
    """Core handler for item reference tags."""

    def __init__(self) -> None:
        super().__init__("item", ContentType.ITEM)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract item reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.ITALIC,  # Items are formatted in italic
        )


class CoreClassTagHandler(BaseCoreTagHandler):
    """Core handler for class reference tags."""

    def __init__(self) -> None:
        super().__init__("class", ContentType.CLASS)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract class reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.BOLD,  # Classes are formatted in bold
        )


class CoreFeatTagHandler(BaseCoreTagHandler):
    """Core handler for feat reference tags."""

    def __init__(self) -> None:
        super().__init__("feat", ContentType.FEAT)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract feat reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.BOLD,  # Feats are formatted in bold
        )


class CoreRaceTagHandler(BaseCoreTagHandler):
    """Core handler for race reference tags."""

    def __init__(self) -> None:
        super().__init__("race", ContentType.RACE)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract race reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.PLAIN,  # Races have no special formatting
        )


class CoreBackgroundTagHandler(BaseCoreTagHandler):
    """Core handler for background reference tags."""

    def __init__(self) -> None:
        super().__init__("background", ContentType.BACKGROUND)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract background reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.PLAIN,  # Backgrounds have no special formatting
        )


class CoreAdventureTagHandler(BaseCoreTagHandler):
    """Core handler for adventure reference tags."""

    def __init__(self) -> None:
        super().__init__("adventure", ContentType.ADVENTURE)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract adventure reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        # Let the enhancer handle page reference formatting
        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.PLAIN,  # Adventures have no special formatting by default
        )


class CoreBookTagHandler(BaseCoreTagHandler):
    """Core handler for book reference tags."""

    def __init__(self) -> None:
        super().__init__("book", ContentType.BOOK)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract book reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        # Let the enhancer handle page reference formatting
        return ContentReferenceInfo(
            name=name or display_text,
            display_text=display_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.PLAIN,  # Books have no special formatting by default
        )


class CoreConditionTagHandler(BaseCoreTagHandler):
    """Core handler for condition tags."""

    def __init__(self) -> None:
        # Conditions don't have a dedicated content type yet in some cases
        super().__init__("condition", None)

    def _extract_display_text(self, node: TagNode, context: RenderingContext) -> str:
        """Extract display text for conditions with special attribute handling.

        Priority for conditions:
        1. display_text_nodes (if available and not empty)
        2. condition attribute
        3. name attribute
        4. string representation of node
        """
        # Check for display_text_nodes first (highest priority)
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # This would normally require recursive rendering through context
            # For now, we'll extract the basic text content
            display_parts = []
            for child_node in node.display_text_nodes:
                if hasattr(child_node, "text"):
                    display_parts.append(str(child_node.text))
                else:
                    display_parts.append(str(child_node))
            return "".join(display_parts)

        # Check for condition attribute (conditions' primary identifier)
        condition = getattr(node, "condition", None)
        if condition is not None and isinstance(condition, str):
            return str(condition)

        # Fallback to name attribute
        name = getattr(node, "name", None)
        if name is not None and isinstance(name, str):
            return str(name)

        # Final fallback to string representation
        return str(node)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract condition information."""
        # Conditions use a 'condition' attribute instead of 'name'
        condition = getattr(node, "condition", None)
        name = getattr(node, "name", None)

        # Handle Mock objects from tests
        if condition is not None and not isinstance(condition, str):
            condition = None
        if name is not None and not isinstance(name, str):
            name = None

        condition_name = condition or name or ""
        display_text = self._extract_display_text(node, context)

        return ContentReferenceInfo(
            name=condition_name,
            display_text=display_text,
            source=None,  # Conditions typically don't have source references
            page=None,  # Conditions typically don't have page references
            content_type=self.content_type,
            format_style=FormatStyle.ITALIC,  # Conditions are formatted in italic
        )


class CoreDCTagHandler:
    """Core handler for difficulty class (@dc) tags.

    This handler processes DC tags that specify difficulty classes,
    returning SpecialTag objects for LaTeX rendering.
    """

    def __init__(self) -> None:
        """Initialize the DC handler."""
        self.tag_type = "dc"
        self.supported_tags = ["dc"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "dc"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str | SpecialTag:
        """Process a DC tag node and return a SpecialTag.

        Args:
            node: The parsed DC tag AST node
            context: Rendering context (unused for DC tags)

        Returns:
            SpecialTag object for LaTeX rendering
        """
        # Import here to avoid circular import
        from dnd5e.core.text.tag_types import SpecialTag

        dc_value = getattr(node, "dc", "")
        if not dc_value:
            logger.warning("Empty DC value in tag")
            return dc_value

        return SpecialTag(tag_type="dc", value=dc_value)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for DC tags, use process_tag instead."""
        # DC tags are handled via process_tag method, this is just for protocol compatibility
        return ContentReferenceInfo(
            name="DC",
            display_text="DC",
            source=None,
            page=None,
            content_type=None,
            format_style=FormatStyle.PLAIN,
        )

    def should_include_page_reference(self, page: str | None) -> bool:
        """DC tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """DC tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """DC tags don't need appendix tracking."""
        pass


class CoreDiceTagHandler:
    """Core handler for dice (@dice) tags.

    This handler processes dice tags that specify dice expressions,
    returning SpecialTag objects for LaTeX rendering.
    """

    def __init__(self) -> None:
        """Initialize the dice handler."""
        self.tag_type = "dice"
        self.supported_tags = ["dice"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "dice"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str | SpecialTag:
        """Process a dice tag node and return a SpecialTag.

        Args:
            node: The parsed dice tag AST node
            context: Rendering context (unused for dice tags)

        Returns:
            SpecialTag object for LaTeX rendering
        """
        # Import here to avoid circular import
        from dnd5e.core.text.tag_types import SpecialTag

        dice_expression = getattr(node, "expression", "")
        if not dice_expression:
            logger.warning("Empty dice expression in tag")
            return dice_expression

        return SpecialTag(tag_type="dice", value=dice_expression)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for dice tags, use process_tag instead."""
        # Dice tags are handled via process_tag method, this is just for protocol compatibility
        return ContentReferenceInfo(
            name="dice",
            display_text="dice",
            source=None,
            page=None,
            content_type=None,
            format_style=FormatStyle.PLAIN,
        )

    def should_include_page_reference(self, page: str | None) -> bool:
        """Dice tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Dice tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Dice tags don't need appendix tracking."""
        pass


class CoreCardTagHandler:
    """Core handler for card (@card) tags.

    This handler processes card tags and returns the card name
    for simple text rendering.
    """

    def __init__(self) -> None:
        """Initialize the card handler."""
        self.tag_type = "card"
        self.supported_tags = ["card"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "card"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Process a card tag node and return the card name.

        Args:
            node: The parsed card tag AST node
            context: Rendering context

        Returns:
            String containing the card name
        """
        # Card tags have format {@card CardName|DeckName|Source}
        # We extract the card name (first parameter)
        card_name = getattr(node, "name", "")
        if not card_name:
            return "[Card]"

        # Escape LaTeX special characters in the card name
        from dnd5e.core.latex_utils import escape_latex_text

        return escape_latex_text(card_name)


class CoreFormattingTagHandler:
    """Core handler for formatting tags like @i (italic) and @b (bold).

    This handler processes pure formatting tags that don't reference content,
    returning FormattingNode objects for presentation layer rendering.
    """

    def __init__(self) -> None:
        """Initialize the formatting handler."""
        self.tag_type = "formatting"  # Generic type for multiple formatting tags
        self.supported_tags = ["italic", "bold", "code", "tt"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type in self.supported_tags

    def process_tag(
        self, node: TagNode, context: RenderingContext
    ) -> str | FormattingNode:
        """Process a formatting tag node and return a FormattingNode.

        Args:
            node: The parsed tag AST node
            context: Rendering context (unused for formatting)

        Returns:
            FormattingNode object for LaTeX rendering
        """
        # Import here to avoid circular import
        from dnd5e.core.text.tag_types import FormattingNode, FormatType

        tag_type = getattr(node, "tag_type", "")

        # Extract content text from child nodes, processing nested tags
        content_parts = []
        if hasattr(node, "content_nodes"):
            for child in node.content_nodes:
                if hasattr(child, "text"):
                    # Simple text node
                    content_parts.append(str(child.text))
                elif hasattr(child, "tag_type"):
                    # This is a nested tag node - we need to render it properly
                    child_tag_type = getattr(child, "tag_type", "")

                    if child_tag_type == "bold":
                        # Extract text from nested bold tag
                        child_content = self._extract_nested_content(child, context)
                        content_parts.append(f"\\textbf{{{child_content}}}")
                    elif child_tag_type == "italic":
                        # Extract text from nested italic tag
                        child_content = self._extract_nested_content(child, context)
                        content_parts.append(f"\\textit{{{child_content}}}")
                    elif child_tag_type == "dc":
                        # Handle nested DC tags by processing them directly
                        dc_value = getattr(child, "dc", "")
                        content_parts.append(f"DC {dc_value}")
                    else:
                        # For other nested tags, try to render them through the unified renderer
                        # Fall back to extracting meaningful content if no rendering available
                        rendered_content = None

                        # Try to render using unified renderer in context
                        if hasattr(context, "renderer") and hasattr(
                            context.renderer, "render_tag"
                        ):
                            try:
                                rendered_content = context.renderer.render_tag(
                                    child, context
                                )
                            except Exception:
                                pass

                        # Try using tag resolver if renderer unavailable
                        if rendered_content is None:
                            tag_resolver = context.metadata.get("tag_resolver")
                            if tag_resolver and hasattr(tag_resolver, "renderer"):
                                try:
                                    rendered_content = tag_resolver.renderer.render_tag(
                                        child, tag_resolver.rendering_context
                                    )
                                except Exception:
                                    pass

                        # Fall back to extracting name or meaningful content
                        if rendered_content is None:
                            if hasattr(child, "name") and child.name:
                                rendered_content = str(child.name)
                            elif hasattr(child, "tag_type"):
                                rendered_content = (
                                    f"[{child.tag_type.replace('_', ' ').title()}]"
                                )
                            else:
                                rendered_content = "[Unknown Tag]"

                        content_parts.append(rendered_content)
                else:
                    content_parts.append(str(child))

        content_text = "".join(content_parts).strip()

        if not content_text:
            logger.warning(f"Empty content in formatting tag: {tag_type}")
            return content_text

        # Map tag types to format types
        if tag_type == "bold":
            format_type = FormatType.BOLD
        elif tag_type == "italic":
            format_type = FormatType.ITALIC
        elif tag_type in ("code", "tt"):
            format_type = FormatType.MONOSPACE
        else:
            logger.warning(f"Unknown formatting tag type: {tag_type}")
            return content_text

        return FormattingNode(format_type=format_type, content=content_text)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for formatting tags, use process_tag instead."""
        # Formatting tags are handled via process_tag method, this is just for protocol compatibility
        return ContentReferenceInfo(
            name="formatting",
            display_text="formatting",
            source=None,
            page=None,
            content_type=None,
            format_style=FormatStyle.PLAIN,
        )

    def should_include_page_reference(self, page: str | None) -> bool:
        """Formatting tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Formatting tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Formatting tags don't need appendix tracking."""
        pass

    def _extract_nested_content(self, node: TagNode, context: RenderingContext) -> str:
        """Extract text content from a nested tag node."""
        from dnd5e.core.latex_utils import escape_latex_text

        content_parts = []
        if hasattr(node, "content_nodes"):
            for child in node.content_nodes:
                if hasattr(child, "text"):
                    content_parts.append(str(child.text))
                else:
                    content_parts.append(str(child))

        content_text = "".join(content_parts).strip()
        return escape_latex_text(content_text)


# Registry of core handlers for easy access
def get_default_core_handlers() -> list[CoreTagHandler]:
    """Get the list of default core tag handlers."""
    return [
        CoreCreatureTagHandler(),
        CoreSpellTagHandler(),
        CoreItemTagHandler(),
        CoreClassTagHandler(),
        CoreFeatTagHandler(),
        CoreRaceTagHandler(),
        CoreBackgroundTagHandler(),
        CoreAdventureTagHandler(),
        CoreBookTagHandler(),
        CoreConditionTagHandler(),
        CoreDCTagHandler(),
        CoreDiceTagHandler(),
        CoreCardTagHandler(),
        CoreFormattingTagHandler(),
    ]
