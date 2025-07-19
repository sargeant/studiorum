"""Tag handlers for the new tag resolution system."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
        # Basic LaTeX escaping
        replacements = {
            "\\": "\\textbackslash{}",
            "{": "\\{",
            "}": "\\}",
            "$": "\\$",
            "&": "\\&",
            "%": "\\%",
            "#": "\\#",
            "^": "\\textasciicircum{}",
            "_": "\\_",
            "~": "\\textasciitilde{}",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text


class CreatureTagHandler(BaseContentTagHandler):
    """Handler for creature reference tags."""

    def __init__(self):
        super().__init__("creature", "\\textbf{{{}}}")


class SpellTagHandler(BaseContentTagHandler):
    """Handler for spell reference tags."""

    def __init__(self):
        super().__init__("spell", "\\textit{{{}}}")


class ItemTagHandler(BaseContentTagHandler):
    """Handler for item reference tags."""

    def __init__(self):
        super().__init__("item", "\\textit{{{}}}")


class ClassTagHandler(BaseContentTagHandler):
    """Handler for class reference tags."""

    def __init__(self):
        super().__init__("class", "\\textbf{{{}}}")


class RaceTagHandler(BaseContentTagHandler):
    """Handler for race reference tags."""

    def __init__(self):
        super().__init__("race", "{}")  # No special formatting for races


class BackgroundTagHandler(BaseContentTagHandler):
    """Handler for background reference tags."""

    def __init__(self):
        super().__init__("background", "{}")  # No special formatting


class FeatTagHandler(BaseContentTagHandler):
    """Handler for feat reference tags."""

    def __init__(self):
        super().__init__("feat", "\\textbf{{{}}}")


class BoldTagHandler(TagHandler):
    """Handler for bold formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type in ("bold", "b")

    def render(self, node: BoldTagNode, context: "RendererContext") -> str:
        """Render bold formatting."""
        # Render content nodes recursively
        content = "".join(context.render_node(child) for child in node.content_nodes)
        return f"\\textbf{{{content}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Bold tags don't need content tracking."""
        pass


class ItalicTagHandler(TagHandler):
    """Handler for italic formatting tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type in ("italic", "i")

    def render(self, node: ItalicTagNode, context: "RendererContext") -> str:
        """Render italic formatting."""
        # Render content nodes recursively
        content = "".join(context.render_node(child) for child in node.content_nodes)
        return f"\\textit{{{content}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Italic tags don't need content tracking."""
        pass


class DiceTagHandler(TagHandler):
    """Handler for dice expression tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "dice"

    def render(self, node: DiceTagNode, context: "RendererContext") -> str:
        """Render dice expression."""
        return f"\\texttt{{{node.expression}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Dice tags don't need content tracking."""
        pass


class HitTagHandler(TagHandler):
    """Handler for hit bonus tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "hit"

    def render(self, node: HitTagNode, context: "RendererContext") -> str:
        """Render hit bonus."""
        bonus = node.bonus
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

    def render(self, node: DCTagNode, context: "RendererContext") -> str:
        """Render difficulty class."""
        return f"DC {node.dc}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """DC tags don't need content tracking."""
        pass


class DamageTagHandler(TagHandler):
    """Handler for damage type tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "damage"

    def render(self, node: DamageTagNode, context: "RendererContext") -> str:
        """Render damage type."""
        return node.damage_type

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Damage tags don't need content tracking."""
        pass


class ConditionTagHandler(TagHandler):
    """Handler for condition tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "condition"

    def render(self, node: ConditionTagNode, context: "RendererContext") -> str:
        """Render condition."""
        return f"\\textit{{{node.condition}}}"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Condition tags don't need content tracking."""
        pass


class ChanceTagHandler(TagHandler):
    """Handler for percentage chance tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "chance"

    def render(self, node: ChanceTagNode, context: "RendererContext") -> str:
        """Render percentage chance."""
        return f"{node.percentage}\\%"

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Chance tags don't need content tracking."""
        pass


class RechargeTagHandler(TagHandler):
    """Handler for recharge tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "recharge"

    def render(self, node: RechargeTagNode, context: "RendererContext") -> str:
        """Render recharge information."""
        recharge = node.recharge
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

    def render(self, node: AdventureTagNode, context: "RendererContext") -> str:
        """Render adventure reference."""
        if hasattr(node, "display_text_nodes") and node.display_text_nodes:
            # Use display text
            display_text = "".join(
                context.render_node(child) for child in node.display_text_nodes
            )
            if node.page:
                return f"{display_text} (p. {node.page})"
            return display_text
        else:
            # Use adventure name
            if node.page:
                return f"{node.name} (p. {node.page})"
            return node.name

    def track_content(self, node: AdventureTagNode, tracker: ContentTracker) -> None:
        """Track adventure for appendix."""
        tracker.add_content("adventure", node.name, node.source, node.page)


class BookTagHandler(TagHandler):
    """Handler for book reference tags."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "book"

    def render(self, node: BookTagNode, context: "RendererContext") -> str:
        """Render book reference."""
        if node.page:
            return f"{node.name}, p. {node.page}"
        return node.name

    def track_content(self, node: BookTagNode, tracker: ContentTracker) -> None:
        """Track book for appendix."""
        tracker.add_content("book", node.name, node.source, node.page)


class FilterTagHandler(TagHandler):
    """Handler for filter tags (ignored in output)."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "filter"

    def render(self, node: FilterTagNode, context: "RendererContext") -> str:
        """Filter tags are omitted from output."""
        return ""

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Filter tags don't need content tracking."""
        pass


class LoaderTagHandler(TagHandler):
    """Handler for loader tags (ignored in output)."""

    def handles(self, tag_type: str) -> bool:
        return tag_type == "loader"

    def render(self, node: LoaderTagNode, context: "RendererContext") -> str:
        """Loader tags are omitted from output."""
        return ""

    def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
        """Loader tags don't need content tracking."""
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
    ]
