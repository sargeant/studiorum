"""LaTeX content-specific renderers (legacy).

This module contained the old rendering system that has been replaced
by the EntryRenderer architecture. The classes below are kept for
backward compatibility only and should not be used for new code.

Use EntryRendererRegistry from entry_renderers.py instead.
"""

from typing import Any

from ...core.models.content import ContentType
from ..base import ContentRenderer

# Legacy classes kept for backward compatibility only
# These are deprecated and will be removed in a future version


class LaTeXContentRenderer(ContentRenderer):
    """Legacy base LaTeX content renderer (deprecated)."""

    def __init__(self, config: dict[str, Any] | None = None):  # type: ignore[override]
        """Initialize LaTeX content renderer."""
        super().__init__(config)  # type: ignore[arg-type]

    @property
    def output_format(self) -> str:
        """Return the output format."""
        return "latex"

    def render_content(self, content: Any, context: Any) -> str:  # noqa: ARG002
        """Legacy render method (deprecated)."""
        raise NotImplementedError(
            "Legacy renderers are deprecated. Use EntryRenderer system instead."
        )


class LaTeXSpellRenderer(LaTeXContentRenderer):
    """Legacy spell renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.SPELL}


class LaTeXCreatureRenderer(LaTeXContentRenderer):
    """Legacy creature renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.CREATURE}


class LaTeXItemRenderer(LaTeXContentRenderer):
    """Legacy item renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.ITEM}


class LaTeXClassRenderer(LaTeXContentRenderer):
    """Legacy class renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.CLASS}


class LaTeXRaceRenderer(LaTeXContentRenderer):
    """Legacy race renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.RACE}


class LaTeXAdventureRenderer(LaTeXContentRenderer):
    """Legacy adventure renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.ADVENTURE}


class LaTeXBackgroundRenderer(LaTeXContentRenderer):
    """Legacy background renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.BACKGROUND}


class LaTeXFeatRenderer(LaTeXContentRenderer):
    """Legacy feat renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.FEAT}


class LaTeXBookRenderer(LaTeXContentRenderer):
    """Legacy book renderer (deprecated)."""

    @property
    def supported_content_types(self) -> set[ContentType]:
        """Return supported content types."""
        return {ContentType.BOOK}


class LaTeXContentRendererRegistry:
    """Legacy renderer registry (deprecated)."""

    def __init__(self) -> None:
        """Initialize renderer registry."""
        self._renderers: dict[ContentType, ContentRenderer] = {}

    def register_renderer(
        self, content_type: ContentType, renderer: ContentRenderer
    ) -> None:
        """Register a renderer for a content type."""
        self._renderers[content_type] = renderer

    def get_renderer(self, content_type: ContentType) -> ContentRenderer | None:
        """Get renderer for content type."""
        return self._renderers.get(content_type)
