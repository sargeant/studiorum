"""Factory functions for creating LaTeX engines."""

from studiorum.core.types import LaTeXConfig

from .adapters import DocumentRendererAdapter
from .core.document import LaTeXDocumentRenderer
from .core.interfaces import LaTeXEngineProtocol


def create_latex_engine(config: LaTeXConfig | None = None) -> LaTeXEngineProtocol:
    """The LaTeX engine the convert commands render documents with."""
    return DocumentRendererAdapter(LaTeXDocumentRenderer(config))
