"""LaTeX token renderer for 5e creature tokens."""

from typing import TYPE_CHECKING

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.models.tokens import TokenSheet

logger = get_logger(__name__)


class TokenRenderer:
    """Renders token sheets to LaTeX using Jinja2 templates."""

    def __init__(self) -> None:
        """Initialize token renderer."""
        logger.debug("TokenRenderer initialized")

    def render(self, token_sheet: "TokenSheet") -> str:
        """Render token sheet to LaTeX.

        Args:
            token_sheet: Token sheet data to render

        Returns:
            LaTeX document string
        """
        from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

        logger.debug(
            f"Rendering token sheet with {token_sheet.get_total_token_count()} tokens"
        )

        template_engine = LaTeXTemplateEngine()

        tokens_by_size = {}
        for size in token_sheet.get_size_order():
            tokens = token_sheet.get_tokens_for_size(size)
            if tokens:
                tokens_by_size[size] = tokens

        context = {
            "paper_size": token_sheet.paper_size.lower(),
            "margins": token_sheet.margins,
            "tokens_by_size": tokens_by_size,
            "column_config": token_sheet.column_config,
        }

        return template_engine.render_template("tokens/token_sheet.tex.j2", context)

    def get_supported_sizes(self) -> list[str]:
        """Get list of supported token sizes."""
        return ["tiny", "small", "medium", "large", "huge", "gargantuan"]

    def get_default_columns(self) -> dict[str, int]:
        """Get default column configuration for each size."""
        return {
            "tiny": 6,
            "small": 6,
            "medium": 6,
            "large": 3,
            "huge": 2,
            "gargantuan": 1,
        }
