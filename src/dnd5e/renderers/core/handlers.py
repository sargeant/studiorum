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
    FormatStyle,
    RenderingContext,
    TagHandler,
    TagValidationError,
)

if TYPE_CHECKING:
    from dnd5e.core.text.tag_ast import TagNode
    from dnd5e.core.text.tag_types import FormattingNode, SpecialTag

logger = get_logger(__name__)


class BaseTagHandler:
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


class CreatureTagHandler(BaseTagHandler):
    """Core handler for creature reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("creature")
        except ValueError:
            logger.debug("Content type 'creature' not found in registry")
            content_type = None
        super().__init__("creature", content_type)

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


class SpellTagHandler(BaseTagHandler):
    """Core handler for spell reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("spell")
        except ValueError:
            logger.debug("Content type 'spell' not found in registry")
            content_type = None
        super().__init__("spell", content_type)

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


class ItemTagHandler(BaseTagHandler):
    """Core handler for item reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("item")
        except ValueError:
            logger.debug("Content type 'item' not found in registry")
            content_type = None
        super().__init__("item", content_type)

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


class ClassTagHandler(BaseTagHandler):
    """Core handler for class reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("class")
        except ValueError:
            logger.debug("Content type 'class' not found in registry")
            content_type = None
        super().__init__("class", content_type)

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


class FeatTagHandler(BaseTagHandler):
    """Core handler for feat reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("feat")
        except ValueError:
            logger.debug("Content type 'feat' not found in registry")
            content_type = None
        super().__init__("feat", content_type)

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


class RaceTagHandler(BaseTagHandler):
    """Core handler for race reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("race")
        except ValueError:
            logger.debug("Content type 'race' not found in registry")
            content_type = None
        super().__init__("race", content_type)

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


class BackgroundTagHandler(BaseTagHandler):
    """Core handler for background reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("background")
        except ValueError:
            logger.debug("Content type 'background' not found in registry")
            content_type = None
        super().__init__("background", content_type)

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


class AdventureTagHandler(BaseTagHandler):
    """Core handler for adventure reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("adventure")
        except ValueError:
            logger.debug("Content type 'adventure' not found in registry")
            content_type = None
        super().__init__("adventure", content_type)

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


class BookTagHandler(BaseTagHandler):
    """Core handler for book reference tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("book")
        except ValueError:
            logger.debug("Content type 'book' not found in registry")
            content_type = None
        super().__init__("book", content_type)

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


class ConditionTagHandler(BaseTagHandler):
    """Core handler for condition tags."""

    def __init__(self) -> None:
        try:
            content_type = ContentType("condition")
        except ValueError:
            logger.debug("Content type 'condition' not found in registry")
            content_type = None
        super().__init__("condition", content_type)

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


class DCTagHandler:
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


class ChanceTagHandler:
    """Core handler for chance (@chance) tags.

    This handler processes chance tags that specify probability percentages,
    returning appropriate display text for LaTeX rendering.
    """

    def __init__(self) -> None:
        """Initialize the chance handler."""
        self.tag_type = "chance"
        self.supported_tags = ["chance"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "chance"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str | SpecialTag:
        """Process a chance tag node and return appropriate display text.

        Args:
            node: The parsed chance tag AST node
            context: Rendering context (unused for chance tags)

        Returns:
            Display text for the chance percentage
        """
        percentage: str = getattr(node, "percentage", "")
        display_text: str | None = getattr(node, "display_text", None)

        if not percentage:
            logger.warning("Empty percentage value in chance tag")
            return "[Chance]"

        # Use display text if provided, otherwise format percentage
        if display_text:
            return display_text
        else:
            return f"{percentage} percent"

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for chance tags, use process_tag instead."""
        return ContentReferenceInfo(
            name="Chance",
            display_text="Chance",
            source=None,
            page=None,
            content_type=None,
            format_style=FormatStyle.PLAIN,
        )

    def should_include_page_reference(self, page: str | None) -> bool:
        """Chance tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Chance tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Chance tags don't need appendix tracking."""
        pass


class DiceTagHandler:
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


class DamageTagHandler:
    """Core handler for damage (@damage) tags.

    This handler processes damage tags that specify damage expressions,
    returning SpecialTag objects for LaTeX rendering.

    Format: {@damage 1d4 + 1} displays "1d4+1" (damage expression)
    """

    def __init__(self) -> None:
        """Initialize the damage handler."""
        self.tag_type = "damage"
        self.supported_tags = ["damage"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "damage"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str | SpecialTag:
        """Process a damage tag node and return a SpecialTag.

        Args:
            node: The parsed damage tag AST node
            context: Rendering context (unused for damage tags)

        Returns:
            SpecialTag object for LaTeX rendering
        """
        # Import here to avoid circular import
        from dnd5e.core.text.tag_types import SpecialTag

        damage_expression = getattr(node, "damage_type", "")
        if not damage_expression:
            logger.warning("Empty damage expression in tag")
            return "[Damage]"  # Fallback for empty expressions

        return SpecialTag(tag_type="damage", value=damage_expression)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for damage tags, use process_tag instead."""
        # Damage tags are handled via process_tag method, this is just for protocol compatibility
        return ContentReferenceInfo(
            name="damage",
            display_text="damage",
            source=None,
            page=None,
            content_type=None,
            format_style=FormatStyle.PLAIN,
        )

    def should_include_page_reference(self, page: str | None) -> bool:
        """Damage tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Damage tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Damage tags don't need appendix tracking."""
        pass


class VariantRuleTagHandler(BaseTagHandler):
    """Core handler for variant rule (@variantrule) tags.

    This handler processes variant rule reference tags, removing redundant
    context like "[Area of Effect]" and rendering just the rule name.

    Example: {@variantrule Sphere [Area of Effect]|XPHB|Sphere} -> "Sphere"
    """

    def __init__(self) -> None:
        try:
            content_type = ContentType("variantrule")
        except ValueError:
            logger.debug("Content type 'variantrule' not found in registry")
            content_type = None
        super().__init__("variantrule", content_type)

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract variant rule reference information."""
        name = getattr(node, "name", "")
        display_text = self._extract_display_text(node, context)
        source = self._extract_source_info(node)
        page = self._extract_page_info(node)

        # Use clean_display_text from VariantRuleTagNode if available
        # This properly handles the _TagPipedDisplayTextThird pattern
        clean_display_text = getattr(node, "clean_display_text", None)
        clean_text = (
            clean_display_text
            if clean_display_text
            else (name if name else display_text)
        )

        return ContentReferenceInfo(
            name=name or display_text,
            display_text=clean_text,
            source=source,
            page=page,
            content_type=self.content_type,
            format_style=FormatStyle.ITALIC,  # Variant rules are formatted in italics
        )


class CardTagHandler(BaseTagHandler):
    """Core handler for card (@card) tags.

    This handler processes card tags and returns the card name
    for simple text rendering.
    """

    def __init__(self) -> None:
        """Initialize the card handler."""
        self.tag_type = "card"
        self.supported_tags = ["card"]

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info from card tag - returns card name for display."""
        # Card tags have format {@card CardName|DeckName|Source}
        # We extract the card name (first parameter)
        card_name = getattr(node, "name", "")
        if not card_name:
            card_name = "[Card]"

        return ContentReferenceInfo(
            name=card_name,
            display_text=card_name,
            content_type=None,  # Cards don't have specific content types
            source=getattr(node, "source", ""),
            page_reference=None,
        )

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


class AbilityTagHandler:
    """Core handler for ability score (@ability) tags.

    This handler processes ability tags that specify ability scores with modifiers,
    returning the modifier value for display.

    Format: {@ability con 10|+0} displays "+0" (the modifier after |)
    """

    def __init__(self) -> None:
        """Initialize the ability handler."""
        self.tag_type = "ability"
        self.supported_tags = ["ability"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "ability"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Process an ability tag node and return the modifier.

        Args:
            node: The parsed ability tag AST node
            context: Rendering context (unused for ability tags)

        Returns:
            String containing the ability modifier (e.g., "+2", "-1")
        """
        # Ability tags have format {@ability con 10|+0}
        # We want to return the modifier part after the | if present

        # First, try to get the modifier from display_text_nodes (the part after |)
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # Extract text content from display_text_nodes
            display_text = ""
            for child in node.display_text_nodes:
                if hasattr(child, "text"):
                    display_text += str(child.text)
                else:
                    display_text += str(child)

            display_text = display_text.strip()
            if display_text:
                # If it's already a properly formatted modifier like "+2", "-1"
                if display_text.startswith(("+", "-")):
                    return display_text
                # If it's just a number, add proper sign
                try:
                    modifier = int(display_text)
                    return f"+{modifier}" if modifier >= 0 else str(modifier)
                except ValueError:
                    # If it's not a pure number, return as-is
                    return display_text

        # Fallback: calculate modifier from ability score in the name field
        # This handles cases where no display text is provided: {@ability con 10}
        if hasattr(node, "name") and node.name:
            name = str(node.name).strip()
            # Expected format: "con 10" where 10 is the ability score
            parts = name.split()
            if len(parts) >= 2:
                try:
                    # Last part should be the ability score
                    ability_score = int(parts[-1])
                    # Calculate modifier from ability score using D&D formula
                    modifier = (ability_score - 10) // 2
                    return f"+{modifier}" if modifier >= 0 else str(modifier)
                except (ValueError, IndexError):
                    pass

        logger.warning(f"Could not extract ability modifier from tag: {node}")
        return "+0"

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for ability tags, use process_tag instead."""
        raise NotImplementedError("Use process_tag for ability tags")

    def should_include_page_reference(self, page: str | None) -> bool:
        """Ability tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Ability tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Ability tags don't need appendix tracking."""
        pass


class SavingThrowTagHandler:
    """Core handler for saving throw (@savingThrow) tags.

    This handler processes saving throw tags that specify ability scores,
    converting them to modifiers for display.

    Format: {@savingThrow con 3} displays "+3" (calculated from ability score)
    """

    def __init__(self) -> None:
        """Initialize the saving throw handler."""
        self.tag_type = "savingThrow"
        self.supported_tags = ["savingThrow"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "savingThrow"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Process a saving throw tag node and return the modifier.

        Args:
            node: The parsed saving throw tag AST node
            context: Rendering context (unused for saving throw tags)

        Returns:
            String containing the saving throw modifier (e.g., "+3", "-1")
        """
        # Saving throw tags have format {@savingThrow con 3} where 3 is already the modifier
        # Extract the modifier from the name field

        if hasattr(node, "name") and node.name:
            name = str(node.name).strip()
            # Expected format: "con 3" where 3 is the modifier value (not ability score)
            parts = name.split()
            if len(parts) >= 2:
                try:
                    # Last part should be the modifier
                    modifier = int(parts[-1])
                    return f"+{modifier}" if modifier >= 0 else str(modifier)
                except (ValueError, IndexError):
                    pass

        logger.warning(f"Could not extract saving throw modifier from tag: {node}")
        return "+0"

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for saving throw tags, use process_tag instead."""
        raise NotImplementedError("Use process_tag for saving throw tags")

    def should_include_page_reference(self, page: str | None) -> bool:
        """Saving throw tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Saving throw tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Saving throw tags don't need appendix tracking."""
        pass


class SkillCheckTagHandler:
    """Core handler for skill check (@skillCheck) tags.

    This handler processes skill check tags that specify skill modifiers,
    formatting them with proper signs for display.

    Format: {@skillCheck athletics 4} displays "+4"
    """

    def __init__(self) -> None:
        """Initialize the skill check handler."""
        self.tag_type = "skillCheck"
        self.supported_tags = ["skillCheck"]

    def handles_tag_type(self, tag_type: str) -> bool:
        """Check if this handler processes the given tag type."""
        return tag_type == "skillCheck"

    def process_tag(self, node: TagNode, context: RenderingContext) -> str:
        """Process a skill check tag node and return the modifier.

        Args:
            node: The parsed skill check tag AST node
            context: Rendering context (unused for skill check tags)

        Returns:
            String containing the skill check modifier (e.g., "+4", "-1")
        """
        # Skill check tags have format {@skillCheck athletics 4} where 4 is already the modifier
        # Extract the modifier from the name field

        if hasattr(node, "name") and node.name:
            name = str(node.name).strip()
            # Expected format: "athletics 4" where 4 is the modifier value
            parts = name.split()
            if len(parts) >= 2:
                try:
                    # Last part should be the modifier
                    modifier = int(parts[-1])
                    return f"+{modifier}" if modifier >= 0 else str(modifier)
                except (ValueError, IndexError):
                    pass

        logger.warning(f"Could not extract skill check modifier from tag: {node}")
        return "+0"

    def extract_content_info(
        self, node: TagNode, context: RenderingContext
    ) -> ContentReferenceInfo:
        """Extract content info - not used for skill check tags, use process_tag instead."""
        raise NotImplementedError("Use process_tag for skill check tags")

    def should_include_page_reference(self, page: str | None) -> bool:
        """Skill check tags don't have page references."""
        return False

    def validate_content_reference(
        self, node: TagNode, context: RenderingContext
    ) -> list[TagValidationError]:
        """Skill check tags don't need content validation."""
        return []

    def track_content_for_appendix(
        self, node: TagNode, context: RenderingContext
    ) -> None:
        """Skill check tags don't need appendix tracking."""
        pass


class FormattingTagHandler(BaseTagHandler):
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
def get_default_core_handlers() -> list[TagHandler]:
    """Get the list of default core tag handlers."""
    return [
        CreatureTagHandler(),
        SpellTagHandler(),
        ItemTagHandler(),
        ClassTagHandler(),
        FeatTagHandler(),
        RaceTagHandler(),
        BackgroundTagHandler(),
        AdventureTagHandler(),
        BookTagHandler(),
        ConditionTagHandler(),
        DCTagHandler(),
        ChanceTagHandler(),
        DiceTagHandler(),
        DamageTagHandler(),
        VariantRuleTagHandler(),
        CardTagHandler(),
        AbilityTagHandler(),
        SavingThrowTagHandler(),
        SkillCheckTagHandler(),
        FormattingTagHandler(),
    ]
