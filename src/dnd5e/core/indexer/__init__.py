"""Cross-reference and tag resolution system."""

from .new_tag_resolver import TagResolverFacade
from .reference_index import ReferenceIndex
from .semantic_resolver import SemanticTagResolver
from .tag_resolver import TagMatch, TagResolver
from .tag_types import (
    ContentReference,
    FormattingNode,
    FormatType,
    SpecialTag,
    TagContext,
    TagResolutionResult,
)

__all__ = [
    # Original classes
    "TagResolver",
    "TagMatch",
    "ReferenceIndex",
    # New AST-based system
    "TagResolverFacade",
    # Supporting classes
    "SemanticTagResolver",
    # Intermediate representation types
    "ContentReference",
    "FormattingNode",
    "SpecialTag",
    "TagContext",
    "TagResolutionResult",
    "FormatType",
]
