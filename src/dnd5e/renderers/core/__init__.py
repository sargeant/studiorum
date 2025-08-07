"""Core tag handler architecture with consolidated business logic.

This module provides the foundation for the composition-based tag handling system,
separating business logic from presentation concerns.

Architecture Overview:
- Core handlers contain only business logic (no LaTeX-specific formatting)
- Enhancement pipeline applies presentation-specific formatting
- Single source of truth for all tag handling business rules
"""

from .handlers import (
    CoreAdventureTagHandler,
    CoreBookTagHandler,
    CoreCreatureTagHandler,
    CoreItemTagHandler,
    CoreSpellTagHandler,
)
from .interfaces import (
    CoreTagHandler,
    EnhancementPipeline,
    RenderingContext,
    TagHandlerEnhancer,
)

__all__ = [
    # Interfaces
    "CoreTagHandler",
    "TagHandlerEnhancer",
    "EnhancementPipeline",
    "RenderingContext",
    # Core Handlers
    "CoreCreatureTagHandler",
    "CoreSpellTagHandler",
    "CoreItemTagHandler",
    "CoreAdventureTagHandler",
    "CoreBookTagHandler",
]
