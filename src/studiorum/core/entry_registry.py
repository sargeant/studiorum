"""Which 5etools entry types Studiorum knows, and what to do with the others.

The entry parser and the LaTeX entry processor check each entry's ``type``
here. An unknown type fails in strict mode, warns in permissive mode, and
passes silently otherwise; the registry counts what it sees either way.
"""

import warnings
from collections import Counter
from enum import Enum

from studiorum.core.logging import get_logger

from .error_types import UnknownTypeError, create_unknown_type_error
from .exceptions import EntryProcessingWarning
from .models.entry_types import TYPED_ENTRY_TYPES
from .result import Error, Result, Success

logger = get_logger(__name__)


class ValidationMode(Enum):
    """Validation modes for entry processing."""

    STRICT = "strict"  # Fail on unknown entry types
    PERMISSIVE = "permissive"  # Warn on unknown entry types, allow processing
    SILENT = "silent"  # Ignore unknown entry types silently (legacy behavior)


# 5etools' entry types (its renderer's switch), plus those with typed models
KNOWN_ENTRY_TYPES: frozenset[str] = TYPED_ENTRY_TYPES | {
    # Containers of other entries
    "entries",
    "options",
    "list",
    "table",
    "tableGroup",
    "inset",
    "insetReadaloud",
    "variant",
    "variantInner",
    "variantSub",
    "spellcasting",
    "quote",
    "optfeature",
    "patron",
    "section",
    # Blocks
    "abilityDc",
    "abilityAttackMod",
    "abilityGeneric",
    # Inline
    "inline",
    "inlineBlock",
    "bonus",
    "bonusSpeed",
    "dice",
    "link",
    "actions",
    "attack",
    "ingredient",
    # List items
    "item",
    "itemSub",
    "itemSpell",
    # Embedded content
    "statblockInline",
    "statblock",
    # Media
    "image",
    "gallery",
    # Other
    "flowchart",
    "flowBlock",
    "homebrew",
    "code",
    "hr",
    "wrappedHtml",
    "cell",
}


class EntryTypeRegistry:
    """Checks entry types against ``KNOWN_ENTRY_TYPES`` and counts them."""

    def __init__(self, validation_mode: ValidationMode = ValidationMode.PERMISSIVE):
        self.validation_mode = validation_mode
        self.entry_counts: Counter[str] = Counter()
        self.unknown_types: set[str] = set()

    def validate_entry_type(
        self,
        entry_type: str,
        *,
        source: str | None = None,
        parent_name: str | None = None,
        validation_mode: ValidationMode | None = None,
    ) -> Result[None, UnknownTypeError]:
        """Count ``entry_type``; an Error if it is unknown in strict mode."""
        mode = validation_mode or self.validation_mode
        self.entry_counts[entry_type] += 1
        if entry_type in KNOWN_ENTRY_TYPES:
            return Success(None)

        self.unknown_types.add(entry_type)
        if mode == ValidationMode.STRICT:
            return Error(
                create_unknown_type_error(
                    entry_type=entry_type,
                    available_types=sorted(KNOWN_ENTRY_TYPES),
                    source=source,
                    parent_name=parent_name,
                )
            )
        if mode == ValidationMode.PERMISSIVE:
            message = f"Unknown entry type encountered: '{entry_type}'"
            if source:
                message += f" (source: {source})"
            if parent_name:
                message += f" (parent: {parent_name})"
            warnings.warn(message, EntryProcessingWarning, stacklevel=3)
            logger.warning(message)
        return Success(None)

    def reset_statistics(self) -> None:
        self.entry_counts.clear()
        self.unknown_types.clear()


_global_registry: EntryTypeRegistry | None = None


def get_registry() -> EntryTypeRegistry:
    """The registry the parser and entry processor share."""
    global _global_registry

    if _global_registry is None:
        _global_registry = EntryTypeRegistry()

    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry for testing."""
    global _global_registry
    _global_registry = None


def set_validation_mode(mode: ValidationMode) -> None:
    """Set the validation mode on the shared registry."""
    get_registry().validation_mode = mode
