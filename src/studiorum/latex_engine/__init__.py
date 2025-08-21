"""LaTeX engine module for document rendering and compilation.

This module provides a clean interface for LaTeX document generation,
separating the LaTeX engine from CLI logic and enabling testing without
LaTeX installation.
"""

from .core.interfaces import LaTeXEngineProtocol
from .factories import create_latex_engine, create_mock_latex_engine

__all__ = [
    "LaTeXEngineProtocol",
    "create_latex_engine",
    "create_mock_latex_engine",
]

# Version information
__version__ = "1.0.0"
