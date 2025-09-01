"""Abstract base renderer interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from studiorum.core.models.content import BaseContent
from studiorum.core.types import RendererConfig

from ..core.interfaces import RenderingContext


class RenderingError(Exception):
    """Exception raised during rendering operations."""

    pass


class BaseRenderer(ABC):
    """Abstract base class for all renderers.

    Defines the core interface that all renderers must implement,
    regardless of output format (LaTeX, HTML, Markdown, etc.).
    """

    def __init__(self, config: RendererConfig | None = None):
        """Initialize renderer with optional configuration.

        Args:
            config: Renderer-specific configuration options
        """
        self.config = config or {}

    @property
    @abstractmethod
    def output_format(self) -> str:
        """Return the output format this renderer produces (e.g., 'latex', 'html')."""
        pass

    @abstractmethod
    def render(
        self, content: BaseContent, context: RenderingContext | None = None
    ) -> str:
        """Render content to the target format.

        Args:
            content: The content to render
            context: Optional rendering context and parameters

        Returns:
            Rendered content as string

        Raises:
            RenderingError: If rendering fails
        """
        pass

    def render_to_file(
        self,
        content: BaseContent,
        output_path: Path,
        context: RenderingContext | None = None,
    ) -> None:
        """Render content and write to file.

        Args:
            content: The content to render
            output_path: Path to write rendered output
            context: Optional rendering context

        Raises:
            RenderingError: If rendering or file writing fails
        """
        try:
            rendered = self.render(content, context)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
        except Exception as e:
            raise RenderingError(f"Failed to render to file {output_path}: {e}") from e

    def validate_content(self, content: BaseContent) -> bool:
        """Validate that content can be rendered by this renderer.

        Args:
            content: Content to validate

        Returns:
            True if content can be rendered, False otherwise
        """
        return True  # Default implementation accepts all content

    def get_supported_content_types(self) -> set[str]:
        """Return set of content types this renderer supports.

        Returns:
            Set of content type names (e.g., {'spell', 'creature', 'item'})
        """
        return set()  # Default implementation supports no specific types
