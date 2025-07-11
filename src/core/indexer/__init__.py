"""Cross-reference and tag resolution system."""

from .tag_resolver import TagResolver, TagMatch
from .reference_index import ReferenceIndex

__all__ = ["TagResolver", "TagMatch", "ReferenceIndex"]
