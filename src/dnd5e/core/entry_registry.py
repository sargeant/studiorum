"""Entry type registry and validation infrastructure for 5etools entries.

This module provides a comprehensive registry of known entry types based on
the 5etools implementation, along with validation infrastructure to handle
unknown entry types and validation modes.
"""

import logging
import warnings
from collections import defaultdict
from enum import Enum
from typing import Any

from .exceptions import (
    EntryProcessingWarning,
    EntryValidationError,
    MalformedEntryError,
    UnknownEntryTypeError,
)

logger = logging.getLogger(__name__)


class ValidationMode(Enum):
    """Validation modes for entry processing."""

    STRICT = "strict"  # Fail on unknown entry types
    PERMISSIVE = "permissive"  # Warn on unknown entry types, allow processing
    SILENT = "silent"  # Ignore unknown entry types silently (legacy behavior)


class EntryTypeCategory(Enum):
    """Categories of entry types for organization."""

    RECURSIVE = "recursive"  # Container types with nested entries
    BLOCK = "block"  # Block-level content
    INLINE = "inline"  # Inline content
    LIST_ITEM = "list_item"  # List item types
    EMBEDDED = "embedded"  # Embedded entities
    MEDIA = "media"  # Media content
    MISC = "misc"  # Miscellaneous types


class EntryTypeRegistry:
    """Registry of known entry types with validation capabilities.

    This registry is based on the comprehensive analysis of the 5etools
    implementation and provides validation, categorization, and statistics
    tracking for entry processing.
    """

    # Known entry types from 5etools analysis, organized by category
    _KNOWN_TYPES: dict[EntryTypeCategory, set[str]] = {
        EntryTypeCategory.RECURSIVE: {
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
        },
        EntryTypeCategory.BLOCK: {"abilityDc", "abilityAttackMod", "abilityGeneric"},
        EntryTypeCategory.INLINE: {
            "inline",
            "inlineBlock",
            "bonus",
            "bonusSpeed",
            "dice",
            "link",
            "actions",
            "attack",
            "ingredient",
        },
        EntryTypeCategory.LIST_ITEM: {"item", "itemSub", "itemSpell"},
        EntryTypeCategory.EMBEDDED: {"statblockInline", "statblock"},
        EntryTypeCategory.MEDIA: {"image", "gallery"},
        EntryTypeCategory.MISC: {
            "flowchart",
            "flowBlock",
            "homebrew",
            "code",
            "hr",
            "wrappedHtml",
        },
    }

    def __init__(self, validation_mode: ValidationMode = ValidationMode.PERMISSIVE):
        """Initialize the entry type registry.

        Args:
            validation_mode: How to handle unknown entry types
        """
        self.validation_mode = validation_mode
        self._statistics: defaultdict[str, int] = defaultdict(int)
        self._unknown_types: set[str] = set()

        # Build flat set of all known types for fast lookup
        self._all_known_types: set[str] = set()
        for category_types in self._KNOWN_TYPES.values():
            self._all_known_types.update(category_types)

    @property
    def known_types(self) -> set[str]:
        """Get all known entry types."""
        return self._all_known_types.copy()

    @property
    def unknown_types(self) -> set[str]:
        """Get set of unknown entry types encountered."""
        return self._unknown_types.copy()

    @property
    def statistics(self) -> dict[str, int]:
        """Get processing statistics."""
        return dict(self._statistics)

    def get_category(self, entry_type: str) -> EntryTypeCategory | None:
        """Get the category for an entry type.

        Args:
            entry_type: The entry type to categorize

        Returns:
            Category of the entry type, or None if unknown
        """
        for category, types in self._KNOWN_TYPES.items():
            if entry_type in types:
                return category
        return None

    def is_known_type(self, entry_type: str) -> bool:
        """Check if an entry type is known.

        Args:
            entry_type: The entry type to check

        Returns:
            True if the entry type is known
        """
        return entry_type in self._all_known_types

    def validate_entry_type(
        self,
        entry_type: str,
        entry: dict[str, Any] | None = None,
        source: str | None = None,
        parent_name: str | None = None,
    ) -> None:
        """Validate an entry type according to the current validation mode.

        Args:
            entry_type: The entry type to validate
            entry: The entry dict (for error context)
            source: Source file or book name
            parent_name: Name of parent section/container

        Raises:
            UnknownEntryTypeError: If validation_mode is STRICT and type is unknown
        """
        self._statistics[entry_type] += 1

        if not self.is_known_type(entry_type):
            self._unknown_types.add(entry_type)

            if self.validation_mode == ValidationMode.STRICT:
                raise UnknownEntryTypeError(
                    entry_type=entry_type,
                    entry=entry,
                    source=source,
                    parent_name=parent_name,
                )
            elif self.validation_mode == ValidationMode.PERMISSIVE:
                warning_msg = f"Unknown entry type encountered: '{entry_type}'"
                if source:
                    warning_msg += f" (source: {source})"
                if parent_name:
                    warning_msg += f" (parent: {parent_name})"

                warnings.warn(warning_msg, EntryProcessingWarning, stacklevel=3)
                logger.warning(warning_msg)
            # SILENT mode does nothing

    def validate_entry_structure(
        self,
        entry: Any,
        source: str | None = None,
        parent_name: str | None = None,
    ) -> dict[str, Any]:
        """Validate basic entry structure.

        Args:
            entry: The entry to validate
            source: Source file or book name
            parent_name: Name of parent section/container

        Returns:
            The entry as a validated dict

        Raises:
            MalformedEntryError: If entry structure is invalid
        """
        if isinstance(entry, str):
            # String entries are valid (plain text)
            return {"type": "text", "content": entry}

        if not isinstance(entry, dict):
            raise MalformedEntryError(
                message=f"Entry must be dict or string, got {type(entry).__name__}",
                entry=entry,
                source=source,
                parent_name=parent_name,
            )

        return entry

    def validate_required_fields(
        self,
        entry: dict[str, Any],
        required_fields: set[str],
        source: str | None = None,
        parent_name: str | None = None,
    ) -> None:
        """Validate that required fields are present in an entry.

        Args:
            entry: The entry dict to validate
            required_fields: Set of required field names
            source: Source file or book name
            parent_name: Name of parent section/container

        Raises:
            EntryValidationError: If required fields are missing
        """
        entry_type = entry.get("type", "unknown")
        missing_fields = required_fields - set(entry.keys())

        if missing_fields:
            raise EntryValidationError(
                message=f"Missing required fields: {', '.join(sorted(missing_fields))}",
                entry=entry,
                source=source,
                parent_name=parent_name,
                entry_type=entry_type,
            )

    def get_common_fields(self, entry_type: str) -> set[str]:
        """Get common fields expected for an entry type.

        This is based on common patterns observed in 5etools data.

        Args:
            entry_type: The entry type

        Returns:
            Set of commonly expected field names
        """
        # Check specific entry types first
        if entry_type in {"section", "entries", "inset", "variant"}:
            return {"type", "name"}
        elif entry_type == "table":
            return {"type", "rows"}
        elif entry_type == "list":
            return {"type", "items"}
        elif entry_type == "image":
            return {"type", "href"}

        # Then check categories for generic handling
        category = self.get_category(entry_type)
        if category == EntryTypeCategory.RECURSIVE:
            return {"type", "entries"}
        else:
            return {"type"}

    def reset_statistics(self) -> None:
        """Reset processing statistics."""
        self._statistics.clear()
        self._unknown_types.clear()

    def log_statistics(self) -> None:
        """Log current processing statistics."""
        if not self._statistics:
            logger.info("No entry processing statistics available")
            return

        total_entries = sum(self._statistics.values())
        logger.info(
            f"Entry processing statistics: {total_entries} total entries processed"
        )

        # Log known types
        known_stats = {
            entry_type: count
            for entry_type, count in self._statistics.items()
            if entry_type in self._all_known_types
        }
        if known_stats:
            logger.info("Known entry types processed:")
            for entry_type, count in sorted(
                known_stats.items(), key=lambda x: x[1], reverse=True
            ):
                logger.info(f"  {entry_type}: {count}")

        # Log unknown types
        unknown_stats = {
            entry_type: count
            for entry_type, count in self._statistics.items()
            if entry_type not in self._all_known_types
        }
        if unknown_stats:
            logger.warning(
                f"Unknown entry types encountered: {len(unknown_stats)} types"
            )
            for entry_type, count in sorted(
                unknown_stats.items(), key=lambda x: x[1], reverse=True
            ):
                logger.warning(f"  {entry_type}: {count}")


# Global registry instance
_global_registry = EntryTypeRegistry()


def get_registry() -> EntryTypeRegistry:
    """Get the global entry type registry instance."""
    return _global_registry


def set_validation_mode(mode: ValidationMode) -> None:
    """Set the global validation mode."""
    _global_registry.validation_mode = mode


def validate_entry_type(
    entry_type: str,
    entry: dict[str, Any] | None = None,
    source: str | None = None,
    parent_name: str | None = None,
) -> None:
    """Validate an entry type using the global registry."""
    _global_registry.validate_entry_type(entry_type, entry, source, parent_name)


def validate_entry_structure(
    entry: Any,
    source: str | None = None,
    parent_name: str | None = None,
) -> dict[str, Any]:
    """Validate entry structure using the global registry."""
    return _global_registry.validate_entry_structure(entry, source, parent_name)
