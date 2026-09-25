"""Context-bound template service for clean APIs without parameter threading.

This module implements the context binding pattern that eliminates the need
to pass ContentTracker parameters through every method call. The bound service
maintains the ContentTracker context internally and provides clean APIs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# RenderingContext imported locally in render_entry to support mocking

if TYPE_CHECKING:
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.latex_engine.services.protocols import TemplateServiceProtocol
    from studiorum.renderers.context import RenderingContext


class ContextBoundTemplateService:
    """Template service bound to a specific ContentTracker context.

    This class wraps a TemplateService and provides clean APIs that don't
    require ContentTracker parameters, as the context is injected once
    during binding and reused for all operations.
    """

    def __init__(
        self, base_service: TemplateServiceProtocol, content_tracker: ContentTracker
    ) -> None:
        """Initialize bound service with injected context.

        Args:
            base_service: The underlying TemplateService to wrap
            content_tracker: ContentTracker context to bind for all operations
        """
        self._service = base_service
        self._tracker = content_tracker

    def render_entry(self, entry: Any) -> str:
        """Render entry with bound context.

        Args:
            entry: Entry object containing description data

        Returns:
            Rendered entry text suitable for LaTeX templates
        """
        from studiorum.latex_engine.entries import EntryRenderer

        renderer = EntryRenderer(
            tracker=self._tracker, omnidexer=self._service.omnidexer
        )
        return "\n\n".join(
            renderer.entries(entry if isinstance(entry, list) else [entry])
        )

    def render_entries(self, entries: list[Any]) -> str:
        """Render multiple entries efficiently with bound context.

        Args:
            entries: List of entry objects to render

        Returns:
            Combined rendered text from all entries
        """
        if not entries:
            return ""

        rendered_parts = []
        for entry in entries:
            rendered = self.render_entry(entry)
            if rendered:
                rendered_parts.append(rendered)

        return "\n\n".join(rendered_parts)

    # Legacy bound APIs removed in favor of render_entry()

    @property
    def content_tracker(self) -> ContentTracker:
        """Access to the bound ContentTracker for advanced use cases."""
        return self._tracker

    def create_rendering_context(
        self, output_format: str = "latex", debug_mode: bool = False, **metadata: Any
    ) -> RenderingContext:
        """Create a RenderingContext using the bound ContentTracker.

        This is a convenience method for advanced users who need direct
        access to RenderingContext creation with the bound context.

        Args:
            output_format: Target output format (default: "latex")
            debug_mode: Whether debug mode is enabled (default: False)
            **metadata: Additional context metadata

        Returns:
            RenderingContext with bound ContentTracker and service dependencies
        """
        from studiorum.renderers.context import RenderingContext

        return RenderingContext(
            output_format=output_format,
            omnidexer=self._service.omnidexer,
            content_tracker=self._tracker,
            tag_resolver=self._service.tag_resolver,
            debug_mode=debug_mode,
            metadata=metadata,
        )
