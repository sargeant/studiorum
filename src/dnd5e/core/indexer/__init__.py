"""Cross-reference and tag resolution system."""

from .reference_index import ReferenceIndex
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
    "TagResolver",
    "ReferenceIndex",
    # Intermediate representation types
    "ContentReference",
    "FormattingNode",
    "SpecialTag",
    "TagContext",
    "TagResolutionResult",
    "FormatType",
]
