"""Document-level renderer interface."""

from abc import abstractmethod
from pathlib import Path
from typing import List

from ...core.models.content import BaseContent
from .context import RenderContext
from .renderer import BaseRenderer


class DocumentRenderer(BaseRenderer):
    """Abstract base class for document-level renderers.

    Handles rendering complete documents with multiple content items,
    including document structure, table of contents, and cross-references.
    """

    @abstractmethod
    def render_document(
        self, content_items: List[BaseContent], context: RenderContext
    ) -> str:
        """Render a complete document from multiple content items.

        Args:
            content_items: List of content to include in document
            context: Rendering context with options and utilities

        Returns:
            Complete rendered document as string
        """
        pass

    @abstractmethod
    def render_document_header(self, context: RenderContext) -> str:
        """Render document header/preamble.

        Args:
            context: Rendering context with metadata

        Returns:
            Document header content
        """
        pass

    @abstractmethod
    def render_document_footer(self, context: RenderContext) -> str:
        """Render document footer/closing.

        Args:
            context: Rendering context

        Returns:
            Document footer content
        """
        pass

    def render_table_of_contents(
        self, content_items: List[BaseContent], context: RenderContext
    ) -> str:
        """Render table of contents.

        Args:
            content_items: Content items to include in ToC
            context: Rendering context

        Returns:
            Table of contents markup
        """
        return ""  # Default implementation returns empty string

    def render_index(
        self, content_items: List[BaseContent], context: RenderContext
    ) -> str:
        """Render document index.

        Args:
            content_items: Content items to index
            context: Rendering context

        Returns:
            Index markup
        """
        return ""  # Default implementation returns empty string

    def render_document_to_file(
        self,
        content_items: List[BaseContent],
        output_path: Path,
        context: RenderContext,
    ) -> None:
        """Render complete document and write to file.

        Args:
            content_items: Content to include in document
            output_path: Path to write document
            context: Rendering context
        """
        try:
            document = self.render_document(content_items, context)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(document, encoding="utf-8")
        except Exception as e:
            from .renderer import RenderingError

            raise RenderingError(
                f"Failed to render document to {output_path}: {e}"
            ) from e
