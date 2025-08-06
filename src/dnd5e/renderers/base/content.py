"""Content-specific renderer interface."""

from abc import abstractmethod
from typing import Any

from ...core.models.content import BaseContent, ContentType
from .context import RenderContext
from .renderer import BaseRenderer


class ContentRenderer(BaseRenderer):
    """Abstract base class for content-specific renderers.

    Handles rendering individual content items like spells, creatures, items, etc.
    Content renderers can be combined by document renderers to create complete documents.
    """

    @property
    @abstractmethod
    def supported_content_types(self) -> set[ContentType]:
        """Return set of content types this renderer supports."""
        pass

    @abstractmethod
    def render_content(self, content: BaseContent, context: RenderContext) -> str:
        """Render individual content item.

        Args:
            content: Content item to render
            context: Rendering context

        Returns:
            Rendered content as string
        """
        pass

    def can_render(self, content: BaseContent) -> bool:
        """Check if this renderer can handle the given content.

        Args:
            content: Content to check

        Returns:
            True if content can be rendered
        """
        # Determine content type from the content object
        content_type = ContentType.from_content(content)
        return content_type in self.supported_content_types

    def render(self, content: BaseContent, context: RenderContext | None = None) -> str:
        """Render content using the content-specific interface.

        Implementation of BaseRenderer.render() that delegates to render_content().

        Args:
            content: Content to render
            context: Optional context dict (will be converted to RenderContext)

        Returns:
            Rendered content
        """
        if not self.can_render(content):
            from .renderer import RenderingError

            content_type = ContentType.from_content(content)
            raise RenderingError(
                f"Renderer {self.__class__.__name__} cannot handle content type {content_type}"
            )

        # Convert dict context to RenderContext if needed
        if isinstance(context, dict):
            render_context = RenderContext(**context)
        elif context is None:
            render_context = RenderContext()
        else:
            render_context = context

        return self.render_content(content, render_context)

    def get_supported_content_types(self) -> set[str]:
        """Return set of content type names this renderer supports.

        Returns:
            Set of content type names as strings
        """
        return {ct.value for ct in self.supported_content_types}
