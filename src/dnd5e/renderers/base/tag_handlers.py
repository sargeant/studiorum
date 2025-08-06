"""Tag handlers for the new tag resolution system."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, cast

from dnd5e.core.indexer.content_tracker import ContentTracker
from dnd5e.core.latex_utils import escape_latex_text
from dnd5e.core.logging import get_logger
from dnd5e.core.models.content import ContentType
from dnd5e.core.text.tag_ast import (
    AdventureTagNode,
    BoldTagNode,
    BookTagNode,
    ChanceTagNode,
    ConditionTagNode,
    DamageTagNode,
    DCTagNode,
    DiceTagNode,
    FilterTagNode,
    HitTagNode,
    ItalicTagNode,
    LoaderTagNode,
    RechargeTagNode,
    TagNode,
)

if TYPE_CHECKING:
    from .tag_renderer import RendererContext

logger = get_logger(__name__)


class TagHandler(ABC):
    """Abstract base class for tag handlers."""

    @abstractmethod
    def handles(self, tag_type: str) -> bool:
        """Check if this handler can process the given tag type."""
        pass

    @abstractmethod
    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render the tag node to output format."""
        pass

    @abstractmethod
    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Track content references for appendix generation."""
        pass


class BaseContentTagHandler(TagHandler):
    """Base handler for content reference tags (creature, spell, item, etc.)."""

    def __init__(
        self, tag_type: str, latex_format: str, content_type: ContentType | None = None
    ):
        self.tag_type = tag_type
        self.latex_format = latex_format  # e.g., "\\textbf{{{}}}" for bold
        self.content_type = content_type  # For validation

    def handles(self, tag_type: str) -> bool:
        """Check if this handler handles the tag type."""
        return tag_type == self.tag_type

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render content reference tag."""
        # Validate content reference
        self._validate_content_reference(node, context)

        # Get the display text from the node
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # Render display text nodes recursively
            display_text = "".join(
                context.render_node(child) for child in node.display_text_nodes
            )
        else:
            # Fallback to node name
            display_text = getattr(node, "name", str(node))

        # Escape LaTeX special characters
        display_text = self._escape_latex(display_text)

        # Apply formatting
        return self.latex_format.format(display_text)

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Track content for appendix generation."""
        name = getattr(node, "name", None)
        source = getattr(node, "source", None)
        page = getattr(node, "page", None)

        if name:
            tracker.add_content(self.tag_type, name, source, page)

    def _validate_content_reference(
        self, node: TagNode, context: "RendererContext"
    ) -> bool:
        """Validate that the content reference exists. Returns True if valid."""
        if not self.content_type or not context.omnidexer:
            return True  # Skip validation if we don't have the info

        name = getattr(node, "name", None)
        source = getattr(node, "source", None)

        if not name:
            return True  # No name to validate

        # Try to find the content
        try:
            content = context.omnidexer.find(self.content_type, name, source)
            if content is None:
                source_info = f" from {source}" if source else ""
                logger.warning(
                    "Invalid %s reference: '%s'%s not found",
                    self.tag_type,
                    name,
                    source_info,
                )
                return False
            return True
        except Exception as e:
            logger.debug(
                "Error validating %s reference '%s': %s", self.tag_type, name, e
            )
            return True  # Don't fail on validation errors

    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters."""
        return escape_latex_text(text)


class CreatureTagHandler(BaseContentTagHandler):
    """Handler for creature reference tags."""

    def __init__(self) -> None:
        super().__init__("creature", "\\textbf{{{}}}", ContentType.CREATURE)


class SpellTagHandler(BaseContentTagHandler):
    """Handler for spell reference tags."""

    def __init__(self) -> None:
        super().__init__("spell", "\\textit{{{}}}", ContentType.SPELL)


class ItemTagHandler(BaseContentTagHandler):
    """Handler for item reference tags."""

    def __init__(self) -> None:
        super().__init__("item", "\\textit{{{}}}", ContentType.ITEM)


class ClassTagHandler(BaseContentTagHandler):
    """Handler for class reference tags."""

    def __init__(self) -> None:
        super().__init__("class", "\\textbf{{{}}}", ContentType.CLASS)


class RaceTagHandler(BaseContentTagHandler):
    """Handler for race reference tags."""

    def __init__(self) -> None:
        super().__init__(
            "race", "{}", ContentType.RACE
        )  # No special formatting for races


class BackgroundTagHandler(BaseContentTagHandler):
    """Handler for background reference tags."""

    def __init__(self) -> None:
        super().__init__(
            "background", "{}", ContentType.BACKGROUND
        )  # No special formatting


class FeatTagHandler(BaseContentTagHandler):
    """Handler for feat reference tags."""

    def __init__(self) -> None:
        super().__init__("feat", "\\textbf{{{}}}", ContentType.FEAT)


class BoldTagHandler(TagHandler):
    """Handler for bold formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type in ("bold", "b")

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render bold formatting."""
        # Type check and cast to specific node type
        assert isinstance(node, BoldTagNode), f"Expected BoldTagNode, got {type(node)}"
        bold_node = cast(BoldTagNode, node)

        # Render content nodes recursively
        content = "".join(
            context.render_node(child) for child in bold_node.content_nodes
        )
        return f"\\textbf{{{content}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Bold tags don't need content tracking."""
        pass


class ItalicTagHandler(TagHandler):
    """Handler for italic formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type in ("italic", "i")

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render italic formatting."""
        # Type check and cast to specific node type
        assert isinstance(node, ItalicTagNode), (
            f"Expected ItalicTagNode, got {type(node)}"
        )
        italic_node = cast(ItalicTagNode, node)

        # Render content nodes recursively
        content = "".join(
            context.render_node(child) for child in italic_node.content_nodes
        )
        return f"\\textit{{{content}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Italic tags don't need content tracking."""
        pass


class DiceTagHandler(TagHandler):
    """Handler for dice expression tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "dice"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render dice expression."""
        # Type check and cast to specific node type
        assert isinstance(node, DiceTagNode), f"Expected DiceTagNode, got {type(node)}"
        dice_node = cast(DiceTagNode, node)

        return f"{dice_node.expression}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Dice tags don't need content tracking."""
        pass


class HitTagHandler(TagHandler):
    """Handler for hit bonus tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "hit"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render hit bonus."""
        # Type check and cast to specific node type
        assert isinstance(node, HitTagNode), f"Expected HitTagNode, got {type(node)}"
        hit_node = cast(HitTagNode, node)

        bonus = hit_node.bonus
        if not bonus.startswith(("+", "-")):
            bonus = f"+{bonus}"
        return bonus

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Hit tags don't need content tracking."""
        pass


class DCTagHandler(TagHandler):
    """Handler for difficulty class tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "dc"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render difficulty class."""
        # Type check and cast to specific node type
        assert isinstance(node, DCTagNode), f"Expected DCTagNode, got {type(node)}"
        dc_node = cast(DCTagNode, node)

        return f"DC {dc_node.dc}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """DC tags don't need content tracking."""
        pass


class DamageTagHandler(TagHandler):
    """Handler for damage type tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "damage"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render damage type."""
        # Type check and cast to specific node type
        assert isinstance(node, DamageTagNode), (
            f"Expected DamageTagNode, got {type(node)}"
        )
        damage_node = cast(DamageTagNode, node)

        return damage_node.damage_type

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Damage tags don't need content tracking."""
        pass


class ConditionTagHandler(TagHandler):
    """Handler for condition tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "condition"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render condition."""
        # Type check and cast to specific node type
        assert isinstance(node, ConditionTagNode), (
            f"Expected ConditionTagNode, got {type(node)}"
        )
        condition_node = cast(ConditionTagNode, node)

        return f"\\textit{{{condition_node.condition}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Condition tags don't need content tracking."""
        pass


class ChanceTagHandler(TagHandler):
    """Handler for percentage chance tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "chance"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render percentage chance."""
        # Type check and cast to specific node type
        assert isinstance(node, ChanceTagNode), (
            f"Expected ChanceTagNode, got {type(node)}"
        )
        chance_node = cast(ChanceTagNode, node)

        return f"{chance_node.percentage}\\%"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Chance tags don't need content tracking."""
        pass


class RechargeTagHandler(TagHandler):
    """Handler for recharge tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "recharge"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render recharge information."""
        # Type check and cast to specific node type
        assert isinstance(node, RechargeTagNode), (
            f"Expected RechargeTagNode, got {type(node)}"
        )
        recharge_node = cast(RechargeTagNode, node)

        recharge = recharge_node.recharge
        flags = recharge_node.flags

        # Check for minimal formatting flag
        is_minimal = "m" in flags

        if "-" in recharge:
            recharge_text = f"Recharge {recharge}"
        else:
            recharge_text = f"Recharge {recharge}--6"

        # Apply formatting based on flags
        if is_minimal:
            return recharge_text
        else:
            return f"({recharge_text})"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Recharge tags don't need content tracking."""
        pass


class AdventureTagHandler(TagHandler):
    """Handler for adventure reference tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "adventure"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render adventure reference."""
        # Type check and cast to specific node type
        assert isinstance(node, AdventureTagNode), (
            f"Expected AdventureTagNode, got {type(node)}"
        )
        adventure_node = cast(AdventureTagNode, node)

        if (
            hasattr(adventure_node, "display_text_nodes")
            and adventure_node.display_text_nodes
        ):
            # Use display text
            display_text = "".join(
                context.render_node(child)
                for child in adventure_node.display_text_nodes
            )
            if adventure_node.page and adventure_node.page != "1":
                return f"{display_text} (p. {adventure_node.page})"
            return display_text
        else:
            # Use adventure name
            if adventure_node.page and adventure_node.page != "1":
                return f"{adventure_node.name} (p. {adventure_node.page})"
            return adventure_node.name

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Track adventure for appendix."""
        # Type check and cast to specific node type
        assert isinstance(node, AdventureTagNode), (
            f"Expected AdventureTagNode, got {type(node)}"
        )
        adventure_node = cast(AdventureTagNode, node)

        tracker.add_content(
            "adventure", adventure_node.name, adventure_node.source, adventure_node.page
        )


class BookTagHandler(TagHandler):
    """Handler for book reference tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "book"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render book reference."""
        # Type check and cast to specific node type
        assert isinstance(node, BookTagNode), f"Expected BookTagNode, got {type(node)}"
        book_node = cast(BookTagNode, node)

        if book_node.page:
            return f"{book_node.name}, p. {book_node.page}"
        return book_node.name

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Track book for appendix."""
        # Type check and cast to specific node type
        assert isinstance(node, BookTagNode), f"Expected BookTagNode, got {type(node)}"
        book_node = cast(BookTagNode, node)

        tracker.add_content("book", book_node.name, book_node.source, book_node.page)


class FilterTagHandler(TagHandler):
    """Handler for filter tags (ignored in output)."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "filter"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Filter tags return their display text."""
        assert isinstance(node, FilterTagNode), (
            f"Expected FilterTagNode, got {type(node)}"
        )
        filter_node = cast(FilterTagNode, node)

        # Extract display text (first part before |)
        # Format: "Common|items|rarity=Common" -> "Common"
        content = filter_node.content
        if "|" in content:
            return content.split("|", 1)[0]
        return content

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Filter tags don't need content tracking."""
        pass


class LoaderTagHandler(TagHandler):
    """Handler for loader tags (ignored in output)."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "loader"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Loader tags are omitted from output."""
        # Type check (though we don't use the node)
        assert isinstance(node, LoaderTagNode), (
            f"Expected LoaderTagNode, got {type(node)}"
        )
        return ""

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Loader tags don't need content tracking."""
        pass


# Note: Simple passthrough tags (skill, quickref, status, etc.) are now
# handled automatically by the improved fallback renderer. No explicit handlers needed!


class AreaTagHandler(TagHandler):
    """Handler for @area tags - renders with appropriate prefix based on flags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "area"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render area tag with appropriate prefix based on flags."""
        # Get the display text from the node
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # Render display text nodes recursively
            display_text = "".join(
                context.render_node(child) for child in node.display_text_nodes
            )
        else:
            # Fallback to node name with default "area " prefix
            display_text = f"area {getattr(node, 'name', str(node))}"

        # AreaTagNode already handles the prefix logic based on flags
        return escape_latex_text(display_text)

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Area tags don't need content tracking."""
        pass


# Additional formatting and special tag handlers


class StrikethroughTagHandler(TagHandler):
    """Handler for strikethrough formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type in ("s", "strike")

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render strikethrough text."""
        # Get content from first parameter
        content = getattr(node, "name", str(node))
        return f"\\sout{{{escape_latex_text(content)}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Strikethrough tags don't need content tracking."""
        pass


class UnderlineTagHandler(TagHandler):
    """Handler for underline formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type in ("u", "underline")

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render underlined text."""
        # Get content from first parameter
        content = getattr(node, "name", str(node))
        return f"\\underline{{{escape_latex_text(content)}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Underline tags don't need content tracking."""
        pass


class CodeTagHandler(TagHandler):
    """Handler for monospace code formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "code"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render monospace code."""
        # Get content from first parameter
        content = getattr(node, "name", str(node))
        return f"\\texttt{{{escape_latex_text(content)}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Code tags don't need content tracking."""
        pass


class SkillTagHandler(BaseContentTagHandler):
    """Handler for skill reference tags."""

    def __init__(self) -> None:
        # No SKILL ContentType exists yet, so no validation
        super().__init__("skill", "\\textit{{{}}}", None)


class ActionTagHandler(BaseContentTagHandler):
    """Handler for action reference tags."""

    def __init__(self) -> None:
        super().__init__("action", "\\textit{{{}}}", ContentType.ACTION)


class StatusTagHandler(BaseContentTagHandler):
    """Handler for status reference tags."""

    def __init__(self) -> None:
        super().__init__("status", "\\textit{{{}}}", ContentType.STATUS)


class SenseTagHandler(BaseContentTagHandler):
    """Handler for sense reference tags."""

    def __init__(self) -> None:
        super().__init__("sense", "\\textit{{{}}}", ContentType.SENSE)


class HazardTagHandler(BaseContentTagHandler):
    """Handler for hazard reference tags."""

    def __init__(self) -> None:
        super().__init__("hazard", "\\textbf{{{}}}", ContentType.HAZARD)


class QuickrefTagHandler(TagHandler):
    """Handler for quickref tags - simple passthrough to first parameter."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "quickref"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render quickref as simple text."""
        # Quickref format is usually {@quickref name||page} - use the name
        content = getattr(node, "name", str(node))
        return escape_latex_text(content)

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Quickref tags don't need content tracking."""
        pass


class NoteTagHandler(TagHandler):
    """Handler for note callout tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "note"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render note as emphasized text."""
        content = getattr(node, "name", str(node))
        return f"\\textit{{Note: {escape_latex_text(content)}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Note tags don't need content tracking."""
        pass


# Registry of all default handlers
def get_default_handlers() -> list[TagHandler]:
    """Get the list of default tag handlers."""
    return [
        # Content reference handlers
        CreatureTagHandler(),
        SpellTagHandler(),
        ItemTagHandler(),
        ClassTagHandler(),
        RaceTagHandler(),
        BackgroundTagHandler(),
        FeatTagHandler(),
        SkillTagHandler(),
        ActionTagHandler(),
        StatusTagHandler(),
        SenseTagHandler(),
        HazardTagHandler(),
        # Formatting handlers
        BoldTagHandler(),
        ItalicTagHandler(),
        StrikethroughTagHandler(),
        UnderlineTagHandler(),
        CodeTagHandler(),
        DiceTagHandler(),
        # Special handlers
        HitTagHandler(),
        DCTagHandler(),
        DamageTagHandler(),
        ConditionTagHandler(),
        ChanceTagHandler(),
        RechargeTagHandler(),
        QuickrefTagHandler(),
        NoteTagHandler(),
        # Reference handlers
        AdventureTagHandler(),
        BookTagHandler(),
        # UI handlers (ignored)
        FilterTagHandler(),
        LoaderTagHandler(),
        # Special formatting handlers
        AreaTagHandler(),
    ]
