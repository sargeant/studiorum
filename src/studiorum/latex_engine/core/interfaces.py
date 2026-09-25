"""The interface the convert commands render documents through."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from studiorum.renderers.context import RenderingContext


@runtime_checkable
class LaTeXEngineProtocol(Protocol):
    """Renders content to a LaTeX document."""

    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """The complete LaTeX document for ``content``."""
        ...
