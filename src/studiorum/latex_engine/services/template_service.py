"""Template service implementation for LaTeX document generation."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.latex_engine.services.protocols import ContextBoundTemplateProtocol
    from studiorum.renderers.tags import TagResolver


class TemplateService:
    """The tag resolver and omnidexer that templates render entries with."""

    def __init__(
        self,
        tag_resolver: TagResolver,
        omnidexer: Omnidexer,
    ) -> None:
        """Initialize the template service with injected components.

        Args:
            tag_resolver: Tag resolver service for processing tags
            omnidexer: Omnidexer service for content resolution
        """
        self.tag_resolver = tag_resolver
        self.omnidexer = omnidexer

    def get_service_name(self) -> str:
        """Return service name for debugging."""
        return "TemplateService"

    def bind_context(
        self, content_tracker: ContentTracker
    ) -> ContextBoundTemplateProtocol:
        """Create a context-bound service with clean APIs.

        Args:
            content_tracker: ContentTracker to bind for all operations

        Returns:
            ContextBoundTemplateService with injected context
        """
        from studiorum.latex_engine.services.context_bound_template_service import (
            ContextBoundTemplateService,
        )

        return ContextBoundTemplateService(self, content_tracker)


# The CLI registers where templates get their TemplateService until the render
# pipeline takes it as a parameter (restructure step 10).
_template_service_provider: ContextVar[Callable[[], TemplateService] | None] = (
    ContextVar("_template_service_provider", default=None)
)


def set_template_service_provider(
    provider: Callable[[], TemplateService] | None,
) -> None:
    """Set the function that returns the TemplateService templates should use."""
    _template_service_provider.set(provider)


def active_template_service() -> TemplateService | None:
    """The registered TemplateService, or None when nothing has registered one."""
    provider = _template_service_provider.get()
    return provider() if provider is not None else None
