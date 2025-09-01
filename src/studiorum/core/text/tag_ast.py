"""AST nodes for the tag resolution system."""

from typing import Any, Protocol, TypeGuard, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceTrackingNode(Protocol):
    """Protocol for AST nodes that can track source information.

    This protocol enables type-safe dynamic attribute assignment for
    source metadata without breaking mypy type checking.
    """

    source: str | None
    page: str | None

    def add_source_info(
        self, source: str | None = None, page: str | None = None
    ) -> None:
        """Add source tracking information to this node."""
        ...


def can_track_source(node: Any) -> TypeGuard[SourceTrackingNode]:
    """Type guard to check if a node can track source information."""
    return (
        hasattr(node, "source")
        and hasattr(node, "page")
        and hasattr(node, "add_source_info")
        and callable(node.add_source_info)
    )


def enhance_for_source_tracking(node: Any) -> SourceTrackingNode:
    """Safely enhance any AST node with source tracking capability.

    This function adds source tracking attributes to nodes that don't have them
    and returns a properly typed node that conforms to SourceTrackingNode protocol.
    """
    if not hasattr(node, "source"):
        node.source = None
    if not hasattr(node, "page"):
        node.page = None
    if not hasattr(node, "add_source_info"):

        def add_source_info(source: str | None = None, page: str | None = None) -> None:
            if source is not None:
                node.source = source
            if page is not None:
                node.page = page

        node.add_source_info = add_source_info

    return cast(SourceTrackingNode, node)


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
    """Base class for all tag nodes that supports source tracking."""

    def __init__(self, tag_type: str, original_text_span: TextSpan | None = None):
        super().__init__(original_text_span)
        self.tag_type = tag_type
        # Default attributes for generic tags (used in parser fallback)
        self.name: str = ""
        self.display_text_nodes: list[ASTNode] = []
        # Flag support - many tags use flags in final parameter for behavior modification
        self.flags: str = ""
        # Source tracking attributes (implements SourceTrackingNode protocol)
        self.source: str | None = None
        self.page: str | None = None

    def add_source_info(
        self, source: str | None = None, page: str | None = None
    ) -> None:
        """Add source tracking information to this node."""
        if source is not None:
            self.source = source
        if page is not None:
            self.page = page

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

    def __init__(
        self,
        percentage: str,
        display_text: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("chance", original_text_span)
        self.percentage = percentage
        self.display_text = display_text

    def __repr__(self) -> str:
        return f"ChanceTagNode(percentage={self.percentage!r}, display_text={self.display_text!r})"


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


class HitYourSpellAttackTagNode(TagNode):
    """Node representing a hit your spell attack tag."""

    def __init__(
        self,
        display_text: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("hitYourSpellAttack", original_text_span)
        self.display_text = display_text or "your spell attack modifier"

    def __repr__(self) -> str:
        return f"HitYourSpellAttackTagNode(display_text={self.display_text!r})"


class AttackRollTagNode(TagNode):
    """Node representing an attack roll tag (@atkr)."""

    def __init__(
        self,
        attack_types: str,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("atkr", original_text_span)
        self.attack_types = attack_types  # e.g., "m", "r", "m,r"

    def __repr__(self) -> str:
        return f"AttackRollTagNode(attack_types={self.attack_types!r})"


class HitResultTagNode(TagNode):
    """Node representing a hit result tag (@h)."""

    def __init__(
        self,
        bonus: str | None = None,
        original_text_span: TextSpan | None = None,
    ):
        super().__init__("h", original_text_span)
        self.bonus = bonus or ""

    def __repr__(self) -> str:
        return f"HitResultTagNode(bonus={self.bonus!r})"


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
        self.name = content  # Set name for _nodes_to_text compatibility

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


class VariantRuleTagNode(TagNode):
    """Node for variant rule reference tags."""

    def __init__(
        self,
        name: str,
        source: str | None = None,
        display_text_nodes: list[ASTNode] | None = None,
        page: str | None = None,
        clean_display_text: str | None = None,
    ):
        super().__init__("variantrule")
        self.name = name
        self.source = source
        self.page = page
        self.clean_display_text = clean_display_text
        self.display_text_nodes = display_text_nodes or []
        self.children.extend(self.display_text_nodes)

    def __repr__(self) -> str:
        return f"VariantRuleTagNode(name={self.name!r}, clean_display_text={self.clean_display_text!r})"
