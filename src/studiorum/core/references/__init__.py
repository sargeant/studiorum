"""Indexing and cross-reference system."""

from .reference_index import ReferenceIndex
from .spell_references import (
    SpellReference,
    SpellReferenceParser,
    SpellReferenceResolver,
)

__all__ = [
    # Core classes
    "ReferenceIndex",
    # Spell reference classes
    "SpellReference",
    "SpellReferenceParser",
    "SpellReferenceResolver",
]
