"""Cross-reference and tag resolution system."""

from .reference_index import ReferenceIndex
from .tag_resolver import TagMatch, TagResolver

__all__ = ["TagResolver", "TagMatch", "ReferenceIndex"]
