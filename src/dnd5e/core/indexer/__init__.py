"""Cross-reference and tag resolution system."""

from .new_tag_resolver import TagResolverFacade
from .refactored_tag_resolver import RefactoredTagResolver, create_tag_resolver
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
    # Refactored classes (interim)
    "RefactoredTagResolver",
    "SemanticTagResolver",
    "create_tag_resolver",
    # Intermediate representation types
    "ContentReference",
    "FormattingNode",
    "SpecialTag",
    "TagContext",
    "TagResolutionResult",
    "FormatType",
]
