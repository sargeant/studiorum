"""Text processing and tag parsing system."""

from .tag_parser import TagParser
from .tag_resolver import TagResolver
from .tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagContext,
    TagResolutionResult,
)

__all__ = [
    # Core classes
    "TagParser",
    "TagResolver",
    # Types
    "ContentReference",
    "FormattingNode",
    "SpecialTag",
    "TagContext",
    "TagResolutionResult",
    "FormatType",
]
