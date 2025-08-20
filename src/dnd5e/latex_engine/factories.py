"""Factory functions for creating LaTeX engines."""

from typing import Optional

from dnd5e.core.types import LaTeXConfig

from .adapters import DocumentRendererAdapter
from .core.document import LaTeXDocumentRenderer
from .core.interfaces import LaTeXEngineProtocol


def create_latex_engine(config: LaTeXConfig | None = None) -> LaTeXEngineProtocol:
    """Create a real LaTeX engine.

    Args:
        config: Optional LaTeX configuration

    Returns:
        LaTeX engine instance
    """
    renderer = LaTeXDocumentRenderer(config)
    return DocumentRendererAdapter(renderer)


def create_mock_latex_engine() -> LaTeXEngineProtocol:
    """Create a mock LaTeX engine for testing.

    Returns:
        Mock LaTeX engine that doesn't require LaTeX installation
    """
    from .testing.mock_engine import MockLaTeXEngine

    return MockLaTeXEngine()
