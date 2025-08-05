"""Tag handlers for the new tag resolution system."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, cast

from ..latex_utils import escape_latex_text
from .content_tracker import ContentTracker
from .tag_ast import (
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

    def __init__(self, tag_type: str, latex_format: str):
        self.tag_type = tag_type
        self.latex_format = latex_format  # e.g., "\\textbf{{{}}}" for bold

    def handles(self, tag_type: str) -> bool:
        """Check if this handler handles the tag type."""
        return tag_type == self.tag_type

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render content reference tag."""
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

    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters."""
        return escape_latex_text(text)


class CreatureTagHandler(BaseContentTagHandler):
    """Handler for creature reference tags."""

    def __init__(self) -> None:
        super().__init__("creature", "\\textbf{{{}}}")


class SpellTagHandler(BaseContentTagHandler):
    """Handler for spell reference tags."""

    def __init__(self) -> None:
        super().__init__("spell", "\\textit{{{}}}")


class ItemTagHandler(BaseContentTagHandler):
    """Handler for item reference tags."""

    def __init__(self) -> None:
        super().__init__("item", "\\textit{{{}}}")


class ClassTagHandler(BaseContentTagHandler):
    """Handler for class reference tags."""

    def __init__(self) -> None:
        super().__init__("class", "\\textbf{{{}}}")


class RaceTagHandler(BaseContentTagHandler):
    """Handler for race reference tags."""

    def __init__(self) -> None:
        super().__init__("race", "{}")  # No special formatting for races


class BackgroundTagHandler(BaseContentTagHandler):
    """Handler for background reference tags."""

    def __init__(self) -> None:
        super().__init__("background", "{}")  # No special formatting


class FeatTagHandler(BaseContentTagHandler):
    """Handler for feat reference tags."""

    def __init__(self) -> None:
        super().__init__("feat", "\\textbf{{{}}}")


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
        if "-" in recharge:
            return f"(Recharge {recharge})"
        else:
            return f"(Recharge {recharge}--6)"

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
            if adventure_node.page:
                return f"{display_text} (p. {adventure_node.page})"
            return display_text
        else:
            # Use adventure name
            if adventure_node.page:
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
    """Handler for @area tags - renders as 'area $content'."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "area"

    def render(self, node: TagNode, context: "RendererContext") -> str:
        """Render area tag with 'area ' prefix."""
        # Get the display text from the node
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # Render display text nodes recursively
            display_text = "".join(
                context.render_node(child) for child in node.display_text_nodes
            )
        else:
            # Fallback to node name
            display_text = getattr(node, "name", str(node))

        # Return with "area " prefix and escape LaTeX special characters
        return f"area {escape_latex_text(display_text)}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Area tags don't need content tracking."""
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
        # Formatting handlers
        BoldTagHandler(),
        ItalicTagHandler(),
        DiceTagHandler(),
        # Special handlers
        HitTagHandler(),
        DCTagHandler(),
        DamageTagHandler(),
        ConditionTagHandler(),
        ChanceTagHandler(),
        RechargeTagHandler(),
        # Reference handlers
        AdventureTagHandler(),
        BookTagHandler(),
        # UI handlers (ignored)
        FilterTagHandler(),
        LoaderTagHandler(),
        # Special formatting handlers
        AreaTagHandler(),
        # Note: Simple passthrough tags (skill, quickref, status, etc.)
        # are handled automatically by the improved fallback renderer
    ]
