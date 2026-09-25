"""LaTeX document rendering and PDF compilation."""

from .core.interfaces import LaTeXEngineProtocol
from .factories import create_latex_engine

__all__ = [
    "LaTeXEngineProtocol",
    "create_latex_engine",
]

# Version information
__version__ = "1.0.0"
