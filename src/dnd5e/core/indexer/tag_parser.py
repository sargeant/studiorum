"""Lark-based parser for D&D 5e.tools tags."""

import logging
import re
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
        tag_parts = children[1:] if len(children) > 1 else []

        # Parse tag parts (name, source, display_text, page)
        parts = []
        for part in tag_parts:
            if isinstance(part, list):
                # Content part with potential nested tags
                part_text = self._render_content_part(part)
                parts.append(part_text)
            elif isinstance(part, str):
                parts.append(part)

        # Create appropriate tag node based on type
        return self._create_tag_node(tag_type, parts)

    def tag_type(self, children: list[Token]) -> str:
        """Transform tag type."""
        return str(children[0])

    def content_part(self, children: list[Any]) -> list[ASTNode]:
        """Transform content part (may contain nested tags)."""
        nodes: list[ASTNode] = []
        current_text = ""

        for child in children:
            if isinstance(child, TagNode):
                # Flush any accumulated text
                if current_text:
                    nodes.append(TextNode(current_text))
                    current_text = ""
                nodes.append(child)
            elif isinstance(child, str):
                current_text += child

        # Flush remaining text
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

    def _render_content_part(self, part: list[ASTNode]) -> str:
        """Render a content part to string (for simple cases)."""
        result = ""
        for node in part:
            if isinstance(node, TextNode):
                result += node.text
            elif isinstance(node, TagNode):
                # For nested tags, we'll need to render them appropriately
                # For now, just use a placeholder
                result += f"{{@{node.tag_type}...}}"
        return result

    def _create_tag_node(self, tag_type: str, parts: list[str]) -> TagNode:
        """Create the appropriate tag node based on type and parts."""
        # Parse common parts: name, source, display_text, page
        name = parts[0] if len(parts) > 0 else ""
        source = parts[1] if len(parts) > 1 and parts[1] else None
        display_text = parts[2] if len(parts) > 2 and parts[2] else None
        page = parts[3] if len(parts) > 3 and parts[3] else None

        # Create display text nodes
        display_text_nodes: list[ASTNode] | None = None
        if display_text:
            display_text_nodes = [TextNode(display_text)]

        # Content reference tags
        if tag_type == "creature":
            return CreatureTagNode(name, source, display_text_nodes, page)
        elif tag_type == "spell":
            return SpellTagNode(name, source, display_text_nodes, page)
        elif tag_type == "item":
            return ItemTagNode(name, source, display_text_nodes, page)
        elif tag_type == "class":
            return ClassTagNode(name, source, display_text_nodes, page)
        elif tag_type == "race":
            return RaceTagNode(name, source, display_text_nodes, page)
        elif tag_type == "background":
            return BackgroundTagNode(name, source, display_text_nodes, page)
        elif tag_type == "feat":
            return FeatTagNode(name, source, display_text_nodes, page)

        # Formatting tags
        elif tag_type in ("bold", "b"):
            bold_content_nodes: list[ASTNode] = (
                display_text_nodes if display_text_nodes else [TextNode(name)]
            )
            return BoldTagNode(bold_content_nodes)
        elif tag_type in ("italic", "i"):
            italic_content_nodes: list[ASTNode] = (
                display_text_nodes if display_text_nodes else [TextNode(name)]
            )
            return ItalicTagNode(italic_content_nodes)
        elif tag_type == "dice":
            return DiceTagNode(name)

        # Special tags
        elif tag_type == "hit":
            return HitTagNode(name)
        elif tag_type == "dc":
            return DCTagNode(name)
        elif tag_type == "damage":
            return DamageTagNode(name)
        elif tag_type == "condition":
            return ConditionTagNode(name)
        elif tag_type == "chance":
            return ChanceTagNode(name)
        elif tag_type == "recharge":
            return RechargeTagNode(name)

        # Reference tags
        elif tag_type == "adventure":
            return AdventureTagNode(name, source, display_text_nodes, page)
        elif tag_type == "book":
            return BookTagNode(name, source, page)

        # UI tags (ignored)
        elif tag_type == "filter":
            return FilterTagNode(name)
        elif tag_type == "loader":
            return LoaderTagNode(name)

        # Generic tag for unknown types
        else:
            return TagNode(tag_type)


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
            # Use regex-based fallback for complex cases
            return self._parse_with_regex_fallback(text)
        except TagParseError as e:
            logger.warning("Tag parsing failed: %s", e)
            doc = DocumentNode()
            doc.add_child(TextNode(text))
            return doc
        except Exception as e:
            logger.error("Unexpected error during tag parsing: %s", e)
            doc = DocumentNode()
            doc.add_child(TextNode(text))
            return doc

    def _parse_with_regex_fallback(self, text: str) -> DocumentNode:
        """Parse using regex fallback for better error handling."""
        # Use regex to find tags and split text
        tag_pattern = r"{@(\w+)\s+([^}]+)}"

        doc = DocumentNode()
        last_end = 0

        for match in re.finditer(tag_pattern, text):
            start, end = match.span()

            # Add text before the tag
            if start > last_end:
                before_text = text[last_end:start]
                if before_text:
                    doc.add_child(TextNode(before_text))

            # Parse the tag
            tag_type = match.group(1)
            tag_content = match.group(2)
            tag_node = self._parse_tag_content(tag_type, tag_content)
            doc.add_child(tag_node)

            last_end = end

        # Add remaining text
        if last_end < len(text):
            remaining_text = text[last_end:]
            if remaining_text:
                doc.add_child(TextNode(remaining_text))

        return doc

    def _parse_tag_content(self, tag_type: str, content: str) -> TagNode:
        """Parse tag content into appropriate tag node."""
        # Split by pipe, handling escaped pipes
        parts = self._split_tag_content(content)

        # Create transformer and build tag
        transformer = TagASTTransformer(content)
        return transformer._create_tag_node(tag_type, parts)

    def _split_tag_content(self, content: str) -> list[str]:
        """Split tag content by pipes, handling escaped characters."""
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
