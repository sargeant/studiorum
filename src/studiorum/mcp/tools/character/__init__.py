"""Character progression tools for the MCP server.

This package provides character progression analysis tools including:
- Level progression analysis
- Feat recommendation
- Multiclass option analysis
- Character optimization guidance

Built on the existing studiorum infrastructure with <200ms performance targets.
"""

from .models import (
    CharacterAnalysisRequest,
    CharacterAnalysisResponse,
    CharacterProgressionData,
    ClassFeatureData,
    FeatAnalysis,
    LevelProgressionAnalysis,
    MulticlassOption,
    SpellProgressionData,
)

__all__ = [
    "CharacterAnalysisRequest",
    "CharacterAnalysisResponse",
    "CharacterProgressionData",
    "ClassFeatureData",
    "FeatAnalysis",
    "LevelProgressionAnalysis",
    "MulticlassOption",
    "SpellProgressionData",
]
