"""LaTeX-specific tag rendering - handles formatting structured tag results."""

from dnd5e.core.latex_utils import escape_latex_text
from dnd5e.core.text.tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagResolutionResult,
)

from ...core.logging import get_logger
from ...core.models.content import ContentType

logger = get_logger(__name__)


class LaTeXTagRenderer:
    """Renders structured tag resolution results to LaTeX-formatted strings.

    This class handles the presentation layer - converting structured
    objects into LaTeX commands and properly escaping text for LaTeX.
    It knows nothing about content resolution or semantic meaning.
    """

    def __init__(self) -> None:
        """Initialize the LaTeX renderer."""
        pass

    def render(self, result: TagResolutionResult) -> str:
        """Render a tag resolution result to LaTeX-formatted string.

        Args:
            result: The structured result from semantic resolution

        Returns:
            LaTeX-formatted string
        """
        if isinstance(result, str):
            return self._escape_latex(result)
        elif isinstance(result, ContentReference):
            return self._render_content_reference(result)
        elif isinstance(result, FormattingNode):
            return self._render_formatting_node(result)
        elif isinstance(result, SpecialTag):
            return self._render_special_tag(result)
        else:
            logger.warning(f"Unknown tag result type: {type(result)}")
            return str(result)  # type: ignore[no-any-return]

    def _render_content_reference(self, ref: ContentReference) -> str:
        """Render a content reference with appropriate LaTeX formatting.

        Different content types get different visual treatment:
        - Creatures, classes, feats: bold
        - Spells, items, conditions: italic
        - Others: plain text with LaTeX escaping

        For backward compatibility, only apply formatting if content was resolved.
        """
        display_text = ref.effective_name

        # For backward compatibility: only format if content was actually resolved
        if ref.is_resolved:
            # Apply content-type specific formatting using string comparison (Phase 3 migration)
            content_type_str = ref.content_type.value if ref.content_type else "unknown"
            if content_type_str in ("creature", "class", "feat"):
                formatted = f"\\textbf{{{self._escape_latex(display_text)}}}"
            elif content_type_str in ("spell", "item"):
                formatted = f"\\textit{{{self._escape_latex(display_text)}}}"
            else:
                formatted = self._escape_latex(display_text)
        else:
            # Unresolved content: just return plain text (original behavior)
            formatted = self._escape_latex(display_text)

        # Add page reference if available (string-based comparison)
        if ref.page:
            content_type_str = ref.content_type.value if ref.content_type else "unknown"
            if content_type_str == "adventure":
                formatted += f" (p. {ref.page})"
            elif content_type_str == "book":
                formatted += f", p. {ref.page}"

        return formatted

    def _render_formatting_node(self, node: FormattingNode) -> str:
        """Render a formatting node with appropriate LaTeX commands."""
        # Check if content already contains LaTeX commands (from nested processing)
        # If so, don't escape it to avoid double-escaping
        if "\\" in node.content and any(
            cmd in node.content
            for cmd in ["\\textbf", "\\textit", "\\texttt", "\\emph"]
        ):
            # Content already contains LaTeX commands, use as-is
            content = node.content
        else:
            # Regular text content, escape it
            content = self._escape_latex(node.content)

        if node.format_type == FormatType.BOLD:
            return f"\\textbf{{{content}}}"
        elif node.format_type == FormatType.ITALIC:
            return f"\\textit{{{content}}}"
        elif node.format_type == FormatType.MONOSPACE:
            return f"\\texttt{{{content}}}"
        elif node.format_type == FormatType.EMPHASIS:
            return f"\\emph{{{content}}}"
        else:
            logger.warning(f"Unknown format type: {node.format_type}")
            return content

    def _render_special_tag(self, tag: SpecialTag) -> str:
        """Render special tags with custom LaTeX formatting."""
        if tag.tag_type == "hit":
            # Attack bonus: +5
            return f"+{tag.effective_value}"
        elif tag.tag_type == "dc":
            # Difficulty class: DC 15
            return f"DC {tag.effective_value}"
        elif tag.tag_type == "note":
            # Notes in parentheses
            return f"({self._escape_latex(tag.effective_value)})"
        elif tag.tag_type == "chance":
            # Percentage with escaped %
            return f"{tag.effective_value}\\%"
        elif tag.tag_type == "coinflip":
            # Always 50%
            return "50\\%"
        elif tag.tag_type == "recharge":
            # Recharge notation
            return f"(Recharge {tag.effective_value})"
        elif tag.tag_type == "dice":
            # Dice expression: 1d8 + 2
            return self._escape_latex(tag.effective_value)
        elif tag.tag_type in ("filter", "loader"):
            # UI elements - typically omitted in print
            return ""
        else:
            logger.debug(f"Unknown special tag type: {tag.tag_type}")
            return self._escape_latex(tag.effective_value)

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters and Unicode characters in text."""
        return escape_latex_text(text)


class ContentTypeStyleConfig:
    """Configuration for content type styling in LaTeX.

    This allows customization of how different content types are rendered
    without modifying the core renderer logic.
    """

    def __init__(self) -> None:
        self.styles = self._build_dynamic_styles()

    def _build_dynamic_styles(self) -> dict[ContentType, str]:
        """Build style mappings from registry metadata (Phase 3 migration).

        Returns:
            Dictionary mapping ContentType enum instances to style strings
        """
        from ...core.models.content import ContentType
        from ...core.registry.content_type_registry import get_content_type_registry

        # Default styles for known content types
        default_styles = {
            "creature": "bold",
            "class": "bold",
            "feat": "bold",
            "spell": "italic",
            "item": "italic",
            "background": "plain",
            "race": "plain",
            "adventure": "plain",
            "book": "plain",
        }

        # Build style mapping with ContentType keys
        styles: dict[ContentType, str] = {}

        try:
            registry = get_content_type_registry()
            for enum_value, metadata in registry.get_all().items():
                try:
                    # Use ContentType constructor for safe validation (Phase 3 pattern)
                    content_type = ContentType(enum_value)
                    style = default_styles.get(enum_value, "plain")
                    styles[content_type] = style

                except ValueError:
                    # Skip test-only registrations that aren't valid enum members
                    continue

        except ImportError:
            # Registry not available, use defaults with enum conversion
            for content_type_str, style in default_styles.items():
                try:
                    content_type = ContentType(content_type_str)
                    styles[content_type] = style
                except ValueError:
                    continue

        return styles

    def get_style(self, content_type: ContentType) -> str:
        """Get the style for a content type."""
        return self.styles.get(content_type, "plain")

    def set_style(self, content_type: ContentType, style: str) -> None:
        """Set the style for a content type."""
        if style not in ("bold", "italic", "plain"):
            raise ValueError(f"Unknown style: {style}")
        self.styles[content_type] = style


class ConfigurableLaTeXTagRenderer(LaTeXTagRenderer):
    """LaTeX renderer with configurable content type styling."""

    def __init__(self, style_config: ContentTypeStyleConfig | None = None):
        super().__init__()
        self.style_config = style_config or ContentTypeStyleConfig()

    def _render_content_reference(self, ref: ContentReference) -> str:
        """Render content reference using configurable styling."""
        display_text = ref.effective_name
        style = self.style_config.get_style(ref.content_type)

        # Apply style based on configuration
        if style == "bold":
            formatted = f"\\textbf{{{self._escape_latex(display_text)}}}"
        elif style == "italic":
            formatted = f"\\textit{{{self._escape_latex(display_text)}}}"
        else:  # plain
            formatted = self._escape_latex(display_text)

        # Add page reference if available, and not 1 (string-based comparison)
        if ref.page and ref.page != "1":
            content_type_str = ref.content_type.value if ref.content_type else "unknown"
            if content_type_str == "adventure":
                formatted += f" (p. {ref.page})"
            elif content_type_str == "book":
                formatted += f", p. {ref.page}"

        return formatted
