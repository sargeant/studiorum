"""Lark-based parser for D&D 5e.tools tags."""

from pathlib import Path
from typing import Any

from lark import Lark, Token, Transformer

from dnd5e.core.logging import get_logger

from .tag_ast import (
    ActionTagNode,
    AdventureTagNode,
    AreaTagNode,
    ASTNode,
    BackgroundTagNode,
    BoldTagNode,
    BookTagNode,
    ChanceTagNode,
    ClassTagNode,
    ConditionTagNode,
    CreatureTagNode,
    DamageTagNode,
    DCTagNode,
    DiceTagNode,
    DocumentNode,
    FeatTagNode,
    FilterTagNode,
    HazardTagNode,
    HitTagNode,
    ItalicTagNode,
    ItemTagNode,
    LoaderTagNode,
    RaceTagNode,
    RechargeTagNode,
    SenseTagNode,
    SkillTagNode,
    SpellTagNode,
    StatusTagNode,
    TagNode,
    TextNode,
)

logger = get_logger(__name__)


class TagParseError(Exception):
    """Exception raised when tag parsing fails."""

    def __init__(
        self, message: str, position: int | None = None, text: str | None = None
    ):
        super().__init__(message)
        self.position = position
        self.text = text


class TagASTTransformer(Transformer):
    """Transformer that converts Lark parse tree to our custom AST."""

    # Parameter count expectations for validation
    TAG_PARAMETER_COUNTS = {
        # Standard content tags: name|source|display|page (1-4 parameters)
        "creature": (1, 4),
        "spell": (1, 4),
        "item": (1, 4),
        "class": (1, 4),
        "race": (1, 4),
        "background": (1, 4),
        "feat": (1, 4),
        "condition": (1, 4),
        "disease": (1, 4),
        "status": (1, 4),
        "skill": (1, 4),
        "action": (1, 4),
        "sense": (1, 4),
        "hazard": (1, 4),
        # Adventure/book tags: display|source|chapter/page|section (1-4 parameters)
        "adventure": (1, 4),
        "book": (1, 4),
        # Special reference tags
        "area": (1, 3),  # name|area_id|flags
        "deity": (1, 4),  # name|pantheon|source|display
        # Simple value tags
        "recharge": (1, 2),  # value|flags
        "chance": (1, 1),
        "dice": (1, 1),
        "damage": (1, 1),
        "hit": (1, 1),
        "dc": (1, 1),
        # Ability score tags
        "ability": (1, 2),  # ability_score|modifier
        "savingThrow": (1, 1),  # modifier_value
        "skillCheck": (1, 1),  # skill_modifier_value
        # Formatting tags
        "bold": (1, 1),
        "italic": (1, 1),
        "s": (1, 1),
        "strike": (1, 1),
        "u": (1, 1),
        "underline": (1, 1),
        "code": (1, 1),
        "note": (1, 1),
        "quickref": (1, 5),
        "loader": (1, 1),
        "filter": (1, 1),
    }

    def __init__(self, original_text: str):
        super().__init__()
        self.original_text = original_text

    def document(self, children: list[ASTNode]) -> DocumentNode:
        """Transform document node."""
        doc = DocumentNode()
        for child in children:
            if child is not None:
                doc.add_child(child)
        return doc

    def text(self, children: list[Token]) -> TextNode:
        """Transform plain text."""
        text_content = "".join(str(token) for token in children)
        return TextNode(text_content)

    def text_fragment(self, children: list[Token]) -> str:
        """Transform text fragment."""
        return "".join(str(token) for token in children)

    def tag(self, children: list[Any]) -> TagNode:
        """Transform a tag based on its type and content."""
        if len(children) < 1:
            raise TagParseError("Tag missing type")

        tag_type = str(children[0])

        # Extract content parts from Lark grammar output
        parts_with_nodes: list[list[ASTNode]] = []
        if len(children) > 1:
            tag_content = children[1]
            # tag_content is list[list[ASTNode]] from tag_content rule
            parts_with_nodes = tag_content

        # Create appropriate tag node based on type with node support
        return self._create_tag_node_with_nodes(tag_type, parts_with_nodes)

    def tag_type(self, children: list[Token]) -> str:
        """Transform tag type."""
        return str(children[0])

    def tag_content(self, children: list[Any]) -> list[list[ASTNode]]:
        """Transform tag content into list of content parts."""
        # Each child is a content_part (list of nodes)
        return children

    def pipe_separated_content(self, children: list[Any]) -> list[ASTNode]:
        """Transform pipe-separated content part."""
        # The child should be a content_part (list of nodes)
        return children[0] if children else []

    def content_part(self, children: list[Any]) -> list[ASTNode]:
        """Transform content part (may contain nested tags)."""
        from lark import Tree

        nodes: list[ASTNode] = []

        # First pass: collect all text tokens and their positions
        all_parts: list[tuple[str, TagNode | str]] = []
        for child in children:
            if isinstance(child, TagNode):
                all_parts.append(("tag", child))
            elif isinstance(child, Tree):
                # Tree node containing a transformed tag - extract the tag
                if child.children and isinstance(child.children[0], TagNode):
                    all_parts.append(("tag", child.children[0]))
            elif isinstance(child, str | Token):
                all_parts.append(("text", str(child)))

        # Second pass: build nodes with proper whitespace handling
        current_text = ""
        for i, (part_type, part_value) in enumerate(all_parts):
            if part_type == "tag":
                # Flush accumulated text before tag
                if current_text:
                    # For first text part, strip leading whitespace
                    if i == 0 or (i > 0 and all_parts[i - 1][0] != "text"):
                        current_text = current_text.lstrip()
                    nodes.append(TextNode(current_text))
                    current_text = ""
                assert isinstance(part_value, TagNode)  # Type narrowing
                nodes.append(part_value)
            elif part_type == "text":
                assert isinstance(part_value, str)  # Type narrowing
                current_text += part_value

        # Flush remaining text
        if current_text:
            # Strip leading whitespace if this is the only/first text
            if not nodes:
                current_text = current_text.lstrip()
            # Always strip trailing whitespace from final text
            current_text = current_text.rstrip()
            if current_text:
                nodes.append(TextNode(current_text))

        return nodes

    def escaped_char(self, children: list[Token]) -> str:
        """Transform escaped characters."""
        escaped = str(children[0])
        if escaped == "\\|":
            return "|"
        elif escaped == "\\}":
            return "}"
        return escaped

    def _validate_parameter_count(self, tag_type: str, actual_count: int) -> None:
        """Validate that the tag has the expected number of parameters."""
        if tag_type in self.TAG_PARAMETER_COUNTS:
            min_count, max_count = self.TAG_PARAMETER_COUNTS[tag_type]
            if actual_count < min_count:
                logger.warning(
                    f"Tag '@{tag_type}' has {actual_count} parameters, "
                    f"expected at least {min_count}"
                )
            elif actual_count > max_count:
                logger.warning(
                    f"Tag '@{tag_type}' has {actual_count} parameters, "
                    f"expected at most {max_count}"
                )
        # For unknown tag types, we don't validate (allows extensibility)

    def _create_tag_node_with_nodes(
        self, tag_type: str, parts: list[list[ASTNode]]
    ) -> TagNode:
        """Create the appropriate tag node with nested node support."""
        # Validate parameter count
        self._validate_parameter_count(tag_type, len(parts))

        # Extract parts: name, source, display_text, page
        name_nodes = parts[0] if len(parts) > 0 else []
        source_nodes = parts[1] if len(parts) > 1 else []
        display_text_nodes = parts[2] if len(parts) > 2 else []
        page_nodes = parts[3] if len(parts) > 3 else []

        # Convert simple parts to strings (name, source, page should be simple)
        name = self._nodes_to_text(name_nodes) if name_nodes else ""
        source = self._nodes_to_text(source_nodes) if source_nodes else None
        page = self._nodes_to_text(page_nodes) if page_nodes else None

        # Keep display_text as nodes for nested tag support
        final_display_text_nodes = display_text_nodes if display_text_nodes else None

        # Adventure tags have different structure: {displayText|source|chapter/page}
        if tag_type == "adventure":
            display_text = name  # First part is display text for adventures
            adventure_source = source
            chapter_page = (
                self._nodes_to_text(display_text_nodes) if display_text_nodes else None
            )
            return AdventureTagNode(display_text, adventure_source, None, chapter_page)

        # Book tags have similar structure: {displayText|source|page}
        elif tag_type == "book":
            display_text = name  # First part is display text for books
            book_source = source
            book_page = (
                self._nodes_to_text(display_text_nodes) if display_text_nodes else None
            )
            return BookTagNode(display_text, book_source, book_page)

        # Content reference tags (use standard structure)
        elif tag_type == "creature":
            return CreatureTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "spell":
            return SpellTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "item":
            return ItemTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "class":
            return ClassTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "race":
            return RaceTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "background":
            return BackgroundTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "feat":
            return FeatTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "condition":
            return ConditionTagNode(name)
        elif tag_type == "skill":
            return SkillTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "action":
            return ActionTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "status":
            return StatusTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "sense":
            return SenseTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "hazard":
            return HazardTagNode(name, source, final_display_text_nodes, page)

        # Formatting tags (use display text if available, otherwise first part)
        elif tag_type in ("bold", "b"):
            content_nodes = display_text_nodes if display_text_nodes else name_nodes
            return BoldTagNode(content_nodes)
        elif tag_type in ("italic", "i"):
            content_nodes = display_text_nodes if display_text_nodes else name_nodes
            return ItalicTagNode(content_nodes)

        # Dice and special tags
        elif tag_type == "dice":
            return DiceTagNode(name)
        elif tag_type == "damage":
            return DamageTagNode(name)
        elif tag_type == "hit":
            return HitTagNode(name)
        elif tag_type == "dc":
            return DCTagNode(name)
        elif tag_type == "chance":
            return ChanceTagNode(name)
        elif tag_type == "recharge":
            # Recharge tags can have format: recharge_value|flags
            flags = self._nodes_to_text(source_nodes) if source_nodes else None
            return RechargeTagNode(name, flags)
        elif tag_type == "filter":
            return FilterTagNode(name)
        elif tag_type == "loader":
            return LoaderTagNode(name)
        elif tag_type == "area":
            # Area tags have format: name|area_id|flags
            area_id = source  # Second part is area_id, not source
            flags = (
                self._nodes_to_text(display_text_nodes) if display_text_nodes else None
            )
            return AreaTagNode(name, area_id, flags)

        # Ability score tags (preserve display text for modifiers)
        elif tag_type == "ability":
            # Ability tags have format: ability_score|modifier
            # We want to preserve the display text (modifier) for rendering
            node = TagNode(tag_type)
            node.name = name  # "con 10" - contains ability and score
            node.display_text_nodes = (
                final_display_text_nodes  # "+0" - the modifier to display
            )
            return node

        elif tag_type == "savingThrow":
            # Saving throw tags have format: ability_modifier
            # The name contains the modifier value that should be displayed
            node = TagNode(tag_type)
            node.name = name  # "con 3" - contains ability and modifier
            node.display_text_nodes = final_display_text_nodes or [TextNode(name)]
            return node

        elif tag_type == "skillCheck":
            # Skill check tags have format: skill_modifier
            # The name contains the skill and modifier value that should be displayed
            node = TagNode(tag_type)
            node.name = name  # "athletics 4" - contains skill and modifier
            node.display_text_nodes = final_display_text_nodes or [TextNode(name)]
            return node

        # Generic fallback - create node with name/display text for automatic passthrough
        else:
            node = TagNode(tag_type)
            node.name = name  # Store the parsed name for fallback rendering

            # For simple passthrough, always prefer name over additional reference parts
            # This handles cases like {@quickref difficult terrain||3} where we want
            # "difficult terrain" (name) not "3" (display text reference)
            if name:
                node.display_text_nodes = [TextNode(name)]
            else:
                node.display_text_nodes = []
            return node

    def _nodes_to_text(self, nodes: list[ASTNode]) -> str:
        """Convert a list of nodes to plain text string."""
        result = ""
        for node in nodes:
            if isinstance(node, TextNode):
                result += node.text
            elif isinstance(node, TagNode):
                # For nested tags in simple fields, just use the tag name or type
                if hasattr(node, "name") and node.name:
                    result += node.name
                elif hasattr(node, "tag_type"):
                    result += f"[{node.tag_type}]"
                else:
                    result += "[tag]"
        return result


class TagParser:
    """Main parser class for D&D 5e.tools tags."""

    def __init__(self) -> None:
        # Load grammar from file
        grammar_path = Path(__file__).parent / "tag_grammar.lark"
        with open(grammar_path) as f:
            grammar = f.read()

        # Create lark parser
        try:
            self.parser = Lark(grammar, start="document", parser="lalr", debug=False)
        except Exception as e:
            raise TagParseError(f"Failed to initialize parser: {e}")

    def parse(self, text: str) -> DocumentNode:
        """Parse text containing tags and return AST."""
        if not text:
            return DocumentNode()

        try:
            # Use Lark parser directly for proper nested tag support
            tree = self.parser.parse(text)
            transformer = TagASTTransformer(text)
            ast = transformer.transform(tree)
            assert isinstance(ast, DocumentNode)
            return ast
        except Exception as e:
            logger.warning("Tag parsing failed: %s. Falling back to TextNode.", e)
            doc = DocumentNode()
            doc.add_child(TextNode(text))
            return doc
