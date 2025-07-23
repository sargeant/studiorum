"""Lark-based parser for D&D 5e.tools tags."""

import logging
from pathlib import Path
from typing import Any

from lark import Lark, Token, Transformer

from dnd5e.core.logging import get_logger

from .tag_ast import (
    AdventureTagNode,
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
    HitTagNode,
    ItalicTagNode,
    ItemTagNode,
    LoaderTagNode,
    RaceTagNode,
    RechargeTagNode,
    SpellTagNode,
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

        # The second child should be the tag_content result (list of content parts)
        if len(children) > 1:
            tag_content = children[
                1
            ]  # This should be list[list[ASTNode]] from tag_content
            parts_with_nodes = tag_content
        else:
            parts_with_nodes = []

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
        all_parts = []
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
                nodes.append(part_value)
            elif part_type == "text":
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

    def _create_tag_node_with_nodes(
        self, tag_type: str, parts: list[list[ASTNode]]
    ) -> TagNode:
        """Create the appropriate tag node with nested node support."""
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

        # Content reference tags
        if tag_type == "creature":
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
        elif tag_type == "adventure":
            return AdventureTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "book":
            return BookTagNode(name, source, final_display_text_nodes, page)
        elif tag_type == "condition":
            return ConditionTagNode(name, source, final_display_text_nodes, page)

        # Formatting tags (use first part as content)
        elif tag_type in ("bold", "b"):
            content_nodes = name_nodes if name_nodes else []
            return BoldTagNode(content_nodes)
        elif tag_type in ("italic", "i"):
            content_nodes = name_nodes if name_nodes else []
            return ItalicTagNode(content_nodes)

        # Dice and special tags
        elif tag_type == "dice":
            return DiceTagNode(name, final_display_text_nodes)
        elif tag_type == "damage":
            return DamageTagNode(name, final_display_text_nodes)
        elif tag_type == "hit":
            return HitTagNode(name, final_display_text_nodes)
        elif tag_type == "dc":
            return DCTagNode(name, final_display_text_nodes)
        elif tag_type == "chance":
            return ChanceTagNode(name, final_display_text_nodes)
        elif tag_type == "recharge":
            return RechargeTagNode(name, final_display_text_nodes)
        elif tag_type == "filter":
            return FilterTagNode(name, final_display_text_nodes)
        elif tag_type == "loader":
            return LoaderTagNode(name, final_display_text_nodes)

        # Generic fallback
        else:
            return TagNode(tag_type, name, source, final_display_text_nodes, page)

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

    def _create_tag_node(self, tag_type: str, parts: list[str]) -> TagNode:
        """Legacy method for backward compatibility with tests.

        Converts string parts to node lists and delegates to new method.
        """
        parts_with_nodes = []
        for part in parts:
            if part:
                parts_with_nodes.append([TextNode(part)])
            else:
                parts_with_nodes.append([])

        return self._create_tag_node_with_nodes(tag_type, parts_with_nodes)

    def _render_content_part(self, nodes: list[ASTNode]) -> str:
        """Legacy method for backward compatibility with tests.

        Converts node list back to string representation.
        """
        return self._nodes_to_text(nodes)


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
            return ast
        except Exception as e:
            logger.warning("Tag parsing failed: %s. Falling back to TextNode.", e)
            doc = DocumentNode()
            doc.add_child(TextNode(text))
            return doc

    def _split_tag_content(self, content: str) -> list[str]:
        """Legacy method for backward compatibility with tests.

        Split tag content by pipes, handling escaped characters.
        """
        parts = []
        current_part = ""
        i = 0

        while i < len(content):
            char = content[i]

            if char == "\\" and i + 1 < len(content):
                # Escaped character
                next_char = content[i + 1]
                if next_char in ("|", "}"):
                    current_part += next_char
                    i += 2
                else:
                    current_part += char
                    i += 1
            elif char == "|":
                # Pipe separator
                parts.append(current_part)
                current_part = ""
                i += 1
            else:
                current_part += char
                i += 1

        # Add the last part
        parts.append(current_part)
        return parts

    def _parse_tag_content(self, tag_type: str, content: str) -> TagNode:
        """Legacy method for backward compatibility with tests.

        Parse tag content into appropriate tag node.
        """
        # Split by pipe, handling escaped pipes
        parts = self._split_tag_content(content)

        # Create transformer and build tag
        transformer = TagASTTransformer(content)
        return transformer._create_tag_node(tag_type, parts)

    def _parse_with_regex_fallback(self, text: str) -> DocumentNode:
        """Legacy method for backward compatibility with tests.

        This now just delegates to the main parse method since we removed
        the regex fallback, but keeping for test compatibility.
        """
        # Just use the regular Lark parser - no need for regex fallback anymore
        return self.parse(text)
