"""Protocols for LaTeX engine services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.renderers.core.interfaces import RenderingContext


@runtime_checkable
class TemplateServiceProtocol(Protocol):
    """Protocol for template services providing entry rendering."""

    # Service dependencies (required for context binding)
    omnidexer: Any
    tag_resolver: Any

    def get_service_name(self) -> str:
        """Return service name for debugging."""
        ...

    # Legacy method render_entry_description removed - use RecursiveEntryProcessor instead

    def bind_context(
        self, content_tracker: ContentTracker
    ) -> ContextBoundTemplateProtocol:
        """Create a context-bound service with clean APIs."""
        ...


@runtime_checkable
class ContextBoundTemplateProtocol(Protocol):
    """Protocol for context-bound template services with clean APIs."""

    def render_entry(self, entry: Any) -> str:
        """Render entry with bound context (preferred API)."""
        ...

    @property
    def content_tracker(self) -> ContentTracker:
        """Access to the bound ContentTracker for advanced use cases."""
        ...

    def create_rendering_context(
        self, output_format: str = "latex", debug_mode: bool = False, **metadata: Any
    ) -> RenderingContext:
        """Create a RenderingContext using the bound ContentTracker."""
        ...
