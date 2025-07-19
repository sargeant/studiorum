"""Advanced LaTeX layout management for D&D content.

This module provides sophisticated layout capabilities for creating professional-quality
D&D documents using the DND-5e-LaTeX-Template environments and advanced LaTeX features.

The layout system includes:
- Multi-column layout management with intelligent breaking
- Float positioning and management (figures, tables, sidebars)
- Sidebar and inset environment handling
- Automatic table formatting and optimization
- Advanced typography features
"""

from .base import LayoutHint, LayoutManager, LayoutStrategy
from .float_manager import FloatManager
from .layout_engine import LayoutEngine
from .multi_column import MultiColumnManager
from .sidebar_manager import SidebarManager
from .table_formatter import TableFormatter
from .typography import TypographyManager

__all__ = [
    "LayoutManager",
    "LayoutHint",
    "LayoutStrategy",
    "MultiColumnManager",
    "FloatManager",
    "SidebarManager",
    "TableFormatter",
    "TypographyManager",
    "LayoutEngine",
]
