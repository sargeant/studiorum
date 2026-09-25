"""Adapters to make existing LaTeX classes conform to new protocols."""

from collections.abc import Sequence

from studiorum.renderers.context import RenderingContext

from .core.document import LaTeXDocumentRenderer


class DocumentRendererAdapter:
    """Adapter to make LaTeXDocumentRenderer conform to LaTeXEngineProtocol."""

    def __init__(self, renderer: LaTeXDocumentRenderer):
        self._renderer = renderer

    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """Render content to LaTeX string.

        This adapter delegates to the wrapped LaTeX document renderer.
        """
        # Convert content to the proper format expected by the renderer
        from typing import cast

        from studiorum.core.models.content import BaseContent

        # Ensure content is in the right format
        content_items: list[BaseContent] = []
        for item in content:
            if isinstance(item, BaseContent):
                content_items.append(item)
            elif hasattr(item, "__dict__"):
                # If it's an object but not BaseContent, cast it (assume compatibility)
                content_items.append(cast(BaseContent, item))
            else:
                # Skip invalid items (dicts, primitives, etc.)
                continue

        # Delegate to the actual renderer
        return self._renderer.render_document(content_items, context)
