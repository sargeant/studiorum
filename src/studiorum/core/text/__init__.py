"""Text processing and tag parsing system."""

from .protocols import TextExtractionProtocol
from .tag_parser import TagParser
from .tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagContext,
    TagResolutionResult,
)
from .text_extractor import TextExtractor

__all__ = [
    # Core classes
    "TagParser",
    "TextExtractor",
    # Protocols
    "TextExtractionProtocol",
    # Types
    "ContentReference",
    "FormattingNode",
    "SpecialTag",
    "TagContext",
    "TagResolutionResult",
    "FormatType",
]
