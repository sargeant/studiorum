"""AST nodes for the tag resolution system."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TextSpan(BaseModel):
    """Represents a span of text in the original input with validation."""

    start: int = Field(ge=0, description="Starting position in the text")
    end: int = Field(ge=0, description="Ending position in the text")
    text: str = Field(min_length=0, description="The text content of this span")

    @field_validator("end")
    @classmethod
    def validate_end_after_start(cls, v: int, info: Any) -> int:
        """Validate that end position is >= start position."""
        if "start" in info.data and v < info.data["start"]:
            raise ValueError("End position must be >= start position")
        return v

    @property
    def length(self) -> int:
        """Get the length of the text span."""
        return self.end - self.start

    @property
    def is_empty(self) -> bool:
        """Check if this is an empty span."""
        return self.start == self.end

    model_config = ConfigDict(frozen=True)


class ASTNode:
    """Base class for all AST nodes."""

    def __init__(self, original_text_span: TextSpan | None = None):
        self.original_text_span = original_text_span
        self.children: list[ASTNode] = []

    def add_child(self, child: "ASTNode") -> None:
        """Add a child node."""
        self.children.append(child)

    def accept(self, visitor: "ASTVisitor") -> Any:
        """Accept a visitor for processing this node."""
        return visitor.visit(self)


class DocumentNode(ASTNode):
    """Root node containing the entire document."""

    def __init__(self, original_text_span: TextSpan | None = None):
        super().__init__(original_text_span)


class TextNode(ASTNode):
    """Node representing plain text content."""

    def __init__(self, text: str, original_text_span: TextSpan | None = None):
        super().__init__(original_text_span)
        self.text = text

    def __repr__(self) -> str:
        return f"TextNode(text={self.text!r})"


class TagNode(ASTNode):
    """Base class for all tag nodes."""

    def __init__(self, tag_type: str, original_text_span: TextSpan | None = None):
        super().__init__(original_text_span)
        self.tag_type = tag_type
        # Default attributes for generic tags (used in parser fallback)
        self.name: str = ""
        self.display_text_nodes: list[ASTNode] = []
        # Flag support - many tags use flags in final parameter for behavior modification
        self.flags: str = ""

    def __repr__(self) -> str:
        return f"TagNode(tag_type={self.tag_type!r})"


# Content Reference Tags


class CreatureTagNode(TagNode):
    """Node representing a creature reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("creature", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"CreatureTagNode(name={self.name!r}, source={self.source!r})"


class SpellTagNode(TagNode):
    """Node representing a spell reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("spell", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"SpellTagNode(name={self.name!r}, source={self.source!r})"


class ItemTagNode(TagNode):
    """Node representing an item reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("item", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"ItemTagNode(name={self.name!r}, source={self.source!r})"


class ClassTagNode(TagNode):
    """Node representing a class reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("class", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"ClassTagNode(name={self.name!r}, source={self.source!r})"


class RaceTagNode(TagNode):
    """Node representing a race reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("race", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"RaceTagNode(name={self.name!r}, source={self.source!r})"


class BackgroundTagNode(TagNode):
    """Node representing a background reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("background", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"BackgroundTagNode(name={self.name!r}, source={self.source!r})"


class FeatTagNode(TagNode):
    """Node representing a feat reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("feat", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"FeatTagNode(name={self.name!r}, source={self.source!r})"


# Formatting Tags


class BoldTagNode(TagNode):
    """Node representing a bold formatting tag."""

    def __init__(
        self,
        content_nodes: list[ASTNode],
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("bold", original_text_span)
        self.content_nodes = content_nodes
        self.children.extend(content_nodes)

    def __repr__(self) -> str:
        return f"BoldTagNode(content_nodes={len(self.content_nodes)} nodes)"


class ItalicTagNode(TagNode):
    """Node representing an italic formatting tag."""

    def __init__(
        self,
        content_nodes: list[ASTNode],
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("italic", original_text_span)
        self.content_nodes = content_nodes
        self.children.extend(content_nodes)

    def __repr__(self) -> str:
        return f"ItalicTagNode(content_nodes={len(self.content_nodes)} nodes)"


class DiceTagNode(TagNode):
    """Node representing a dice expression tag."""

    def __init__(self, expression: str, original_text_span: TextSpan | None = None):
        super().__init__("dice", original_text_span)
        self.expression = expression

    def __repr__(self) -> str:
        return f"DiceTagNode(expression={self.expression!r})"


# Special Tags


class HitTagNode(TagNode):
    """Node representing a hit bonus tag."""

    def __init__(self, bonus: str, original_text_span: TextSpan | None = None):
        super().__init__("hit", original_text_span)
        self.bonus = bonus

    def __repr__(self) -> str:
        return f"HitTagNode(bonus={self.bonus!r})"


class DCTagNode(TagNode):
    """Node representing a difficulty class tag."""

    def __init__(self, dc: str, original_text_span: TextSpan | None = None):
        super().__init__("dc", original_text_span)
        self.dc = dc

    def __repr__(self) -> str:
        return f"DCTagNode(dc={self.dc!r})"


class DamageTagNode(TagNode):
    """Node representing a damage type tag."""

    def __init__(self, damage_type: str, original_text_span: TextSpan | None = None):
        super().__init__("damage", original_text_span)
        self.damage_type = damage_type

    def __repr__(self) -> str:
        return f"DamageTagNode(damage_type={self.damage_type!r})"


class ConditionTagNode(TagNode):
    """Node representing a condition tag."""

    def __init__(self, condition: str, original_text_span: TextSpan | None = None):
        super().__init__("condition", original_text_span)
        self.condition = condition

    def __repr__(self) -> str:
        return f"ConditionTagNode(condition={self.condition!r})"


class ChanceTagNode(TagNode):
    """Node representing a percentage chance tag."""

    def __init__(self, percentage: str, original_text_span: TextSpan | None = None):
        super().__init__("chance", original_text_span)
        self.percentage = percentage

    def __repr__(self) -> str:
        return f"ChanceTagNode(percentage={self.percentage!r})"


class RechargeTagNode(TagNode):
    """Node representing a recharge tag."""

    def __init__(
        self,
        recharge: str,
        flags: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("recharge", original_text_span)
        self.recharge = recharge
        self.flags = flags or ""

    def __repr__(self) -> str:
        return f"RechargeTagNode(recharge={self.recharge!r}, flags={self.flags!r})"


# Reference Tags


class AdventureTagNode(TagNode):
    """Node representing an adventure reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("adventure", original_text_span)
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = (
            display_text_nodes if display_text_nodes else [TextNode(name)]
        )
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"AdventureTagNode(name={self.name!r}, source={self.source!r}, page={self.page!r})"


class BookTagNode(TagNode):
    """Node representing a book reference tag."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        page: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("book", original_text_span)
        self.name = name
        self.source = source
        self.page = page

    def __repr__(self) -> str:
        return f"BookTagNode(name={self.name!r}, source={self.source!r}, page={self.page!r})"


# UI Tags (ignored in output)


class FilterTagNode(TagNode):
    """Node representing a filter tag (ignored in output)."""

    def __init__(self, content: str, original_text_span: TextSpan | None = None):
        super().__init__("filter", original_text_span)
        self.content = content

    def __repr__(self) -> str:
        return f"FilterTagNode(content={self.content!r})"


class LoaderTagNode(TagNode):
    """Node representing a loader tag (ignored in output)."""

    def __init__(self, content: str, original_text_span: TextSpan | None = None):
        super().__init__("loader", original_text_span)
        self.content = content

    def __repr__(self) -> str:
        return f"LoaderTagNode(content={self.content!r})"


class AreaTagNode(TagNode):
    """Node representing an area reference tag."""

    def __init__(
        self,
        name: str,
        area_id: str | None = None,
        flags: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("area", original_text_span)
        self.name = name
        self.area_id = area_id
        self.flags = flags or ""
        # Set display text based on flags (following 5etools logic)
        if "x" in self.flags:
            # Just the name, no prefix
            display_text = name
        elif "u" in self.flags:
            # Uppercase "Area"
            display_text = f"Area {name}"
        else:
            # Lowercase "area"
            display_text = f"area {name}"

        self.display_text_nodes = [TextNode(display_text)]
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"AreaTagNode(name={self.name!r}, area_id={self.area_id!r}, flags={self.flags!r})"


class SkillTagNode(TagNode):
    """Node for skill reference tags."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
    ):
        super().__init__("skill")
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = display_text_nodes or []
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"SkillTagNode(name={self.name!r})"


class ActionTagNode(TagNode):
    """Node for action reference tags."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
    ):
        super().__init__("action")
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = display_text_nodes or []
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"ActionTagNode(name={self.name!r})"


class StatusTagNode(TagNode):
    """Node for status reference tags."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
    ):
        super().__init__("status")
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = display_text_nodes or []
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"StatusTagNode(name={self.name!r})"


class SenseTagNode(TagNode):
    """Node for sense reference tags."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
    ):
        super().__init__("sense")
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = display_text_nodes or []
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"SenseTagNode(name={self.name!r})"


class HazardTagNode(TagNode):
    """Node for hazard reference tags."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
    ):
        super().__init__("hazard")
        self.name = name
        self.source = source
        self.page = page
        self.display_text_nodes = display_text_nodes or []
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"HazardTagNode(name={self.name!r})"


# Visitor Pattern


class ASTVisitor:
    """Base visitor class for processing AST nodes."""

    def visit(self, node: ASTNode) -> Any:
        """Visit a node and dispatch to the appropriate method."""
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)

    def generic_visit(self, node: ASTNode) -> Any:
        """Default visit method for unhandled node types."""
        results = []
        for child in node.children:
            result = self.visit(child)
            if result is not None:
                results.append(result)
        return results

    # Default implementations for common node types
    def visit_DocumentNode(self, node: DocumentNode) -> Any:
        return self.generic_visit(node)

    def visit_TextNode(self, node: TextNode) -> Any:
        return node.text

    def visit_TagNode(self, node: TagNode) -> Any:
        return self.generic_visit(node)
