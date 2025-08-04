"""Entry type registry and validation infrastructure for 5etools entries.

This module provides a comprehensive registry of known entry types based on
the 5etools implementation, along with validation infrastructure to handle
unknown entry types and validation modes.
"""

import logging
import warnings
from collections import defaultdict
from enum import Enum
from typing import Any, Union, overload

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base_context import ProcessingContext
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


class ValidationContext(ProcessingContext[Any]):
    """Context information for entry validation operations.

    This model provides structured context for validation operations,
    replacing the scattered dict[str, Any] parameters with a cohesive
    data structure that supports the flexible validation requirements.

    Inherits from ProcessingContext to provide standardized context management.
    """

    model_config = ConfigDict(
        extra="allow",  # Allow additional context fields
        arbitrary_types_allowed=True,  # Support complex entry types
    )

    # Legacy fields mapped to base context
    entry_data: Any = Field(
        ..., description="The entry data to validate (dict, string, or other)"
    )
    source: str | None = Field(
        None, description="Source file or book name for error context"
    )
    parent_name: str | None = Field(
        None, description="Name of parent section/container for error context"
    )
    entry_type: str | None = Field(None, description="Detected or expected entry type")
    validation_mode: "ValidationMode | None" = Field(
        None, description="Override validation mode for this context"
    )

    def __init__(self, **data: Any) -> None:
        # Map legacy fields to base context fields
        if "entry_data" in data and "content" not in data:
            data["content"] = data["entry_data"]
        if "entry_type" in data and "content_type_name" not in data:
            data["content_type_name"] = data.get("entry_type", "unknown")
        elif "content_type_name" not in data:
            # Provide default content type name if not specified
            data["content_type_name"] = "entry"
        if "source" in data and "source_file" not in data:
            data["source_file"] = data["source"]
        if "parent_name" in data and "source_section" not in data:
            data["source_section"] = data["parent_name"]

        # Set up processing options
        if "processing_options" not in data:
            data["processing_options"] = {}
        if "validation_mode" in data and data["validation_mode"] is not None:
            data["processing_options"]["validation_mode"] = data["validation_mode"]

        super().__init__(**data)

    @field_validator("entry_data", mode="before")
    @classmethod
    def validate_entry_data(cls, v: Any) -> Any:
        """Accept any entry data type for maximum flexibility."""
        return v


class ValidatedEntry(BaseModel):
    """Represents a validated and normalized entry structure.

    This model replaces dict[str, Any] returns from validation functions
    with a structured representation that maintains type safety while
    supporting the diverse entry formats found in 5etools data.
    """

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields from 5etools
        arbitrary_types_allowed=True,  # Support nested content
    )

    type: str = Field(..., description="Entry type (e.g., 'section', 'table', 'text')")
    content: Any | None = Field(None, description="Entry content (varies by type)")
    name: str | None = Field(None, description="Entry name/title if applicable")
    entries: list[Any] | None = Field(
        None, description="Nested entries for recursive types"
    )

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: Any) -> str:
        """Ensure type is always a string."""
        return str(v) if v is not None else "unknown"

    @classmethod
    def from_string(cls, content: str) -> "ValidatedEntry":
        """Create a ValidatedEntry from a plain string."""
        return cls(type="text", content=content)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidatedEntry":
        """Create a ValidatedEntry from a dictionary.

        Uses smart field mapping to extract common entry fields
        while preserving all original data via extra="allow".
        """
        # Extract known fields with fallbacks
        entry_type = data.get("type", "unknown")
        content = data.get("content")
        name = data.get("name")
        entries = data.get("entries")

        # Create validated entry with all original data preserved
        return cls(
            type=entry_type,
            content=content,
            name=name,
            entries=entries,
            **{
                k: v
                for k, v in data.items()
                if k not in {"type", "content", "name", "entries"}
            },
        )


class ValidationResult(BaseModel):
    """Result of an entry validation operation.

    This model provides comprehensive validation results, replacing
    simple return values with structured information about the
    validation process and its outcomes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = Field(..., description="Whether validation succeeded")
    entry: ValidatedEntry = Field(..., description="The validated and normalized entry")
    warnings: list[str] = Field(
        default_factory=list, description="Validation warnings encountered"
    )
    errors: list[str] = Field(
        default_factory=list, description="Validation errors encountered"
    )
    context: ValidationContext | None = Field(
        None, description="Original validation context"
    )

    @property
    def has_warnings(self) -> bool:
        """Check if validation produced warnings."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if validation produced errors."""
        return len(self.errors) > 0


class ProcessingStatistics(BaseModel):
    """Structured processing statistics for entry validation.

    This model replaces dict[str, int] statistics with a more
    comprehensive and type-safe representation that includes
    metadata and computed metrics.
    """

    entry_counts: dict[str, int] = Field(
        default_factory=dict, description="Count of entries by type"
    )
    unknown_types: set[str] = Field(
        default_factory=set, description="Set of encountered unknown types"
    )
    validation_errors: int = Field(
        default=0, description="Total validation errors encountered"
    )
    validation_warnings: int = Field(
        default=0, description="Total validation warnings encountered"
    )

    @property
    def total_entries(self) -> int:
        """Total number of entries processed."""
        return sum(self.entry_counts.values())

    @property
    def known_type_count(self) -> int:
        """Number of known entry types processed."""
        # This will be computed by the registry based on its known types
        return len(self.entry_counts) - len(self.unknown_types)

    @property
    def unknown_type_count(self) -> int:
        """Number of unknown entry types encountered."""
        return len(self.unknown_types)

    def increment_entry_count(self, entry_type: str) -> None:
        """Increment the count for a specific entry type."""
        self.entry_counts[entry_type] = self.entry_counts.get(entry_type, 0) + 1

    def add_unknown_type(self, entry_type: str) -> None:
        """Add an unknown entry type to the tracking set."""
        self.unknown_types.add(entry_type)

    def reset(self) -> None:
        """Reset all statistics to initial state."""
        self.entry_counts.clear()
        self.unknown_types.clear()
        self.validation_errors = 0
        self.validation_warnings = 0


class EntryTypeDefinition(BaseModel):
    """Definition of an entry type with its category and metadata.

    This model structures the entry type registry data for better
    organization and extensibility.
    """

    name: str = Field(..., description="Entry type name")
    category: EntryTypeCategory = Field(..., description="Entry type category")
    common_fields: set[str] = Field(
        default_factory=set, description="Commonly expected fields for this type"
    )
    required_fields: set[str] = Field(
        default_factory=set, description="Required fields for this type"
    )
    description: str | None = Field(None, description="Description of the entry type")


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
        self._statistics: ProcessingStatistics = ProcessingStatistics()

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
        return self._statistics.unknown_types.copy()

    @property
    def statistics(self) -> ProcessingStatistics:
        """Get processing statistics."""
        return self._statistics

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

    def validate_entry_type(self, context: ValidationContext) -> None:
        """Validate an entry type according to the current validation mode.

        Args:
            context: ValidationContext containing entry data and validation parameters

        Raises:
            UnknownEntryTypeError: If validation_mode is STRICT and type is unknown
        """
        entry_type = context.entry_type or "unknown"
        entry_data = (
            context.entry_data if isinstance(context.entry_data, dict) else None
        )
        source = context.source
        parent_name = context.parent_name
        validation_mode = context.validation_mode or self.validation_mode

        # Update statistics
        self._statistics.increment_entry_count(entry_type)

        if not self.is_known_type(entry_type):
            self._statistics.add_unknown_type(entry_type)

            if validation_mode == ValidationMode.STRICT:
                raise UnknownEntryTypeError(
                    entry_type=entry_type,
                    entry=entry_data,
                    source=source,
                    parent_name=parent_name,
                )
            elif validation_mode == ValidationMode.PERMISSIVE:
                warning_msg = f"Unknown entry type encountered: '{entry_type}'"
                if source:
                    warning_msg += f" (source: {source})"
                if parent_name:
                    warning_msg += f" (parent: {parent_name})"

                warnings.warn(warning_msg, EntryProcessingWarning, stacklevel=3)
                logger.warning(warning_msg)
                self._statistics.validation_warnings += 1
            # SILENT mode does nothing

    def validate_entry_structure(self, context: ValidationContext) -> ValidationResult:
        """Validate basic entry structure using ValidationContext.

        Args:
            context: ValidationContext containing entry data and validation parameters

        Returns:
            ValidationResult with structured validation information
        """
        entry = context.entry_data

        warnings_list: list[str] = []
        errors_list: list[str] = []

        try:
            if isinstance(entry, str):
                # String entries are valid (plain text)
                validated_entry = ValidatedEntry.from_string(entry)

                return ValidationResult(
                    success=True,
                    entry=validated_entry,
                    warnings=warnings_list,
                    errors=errors_list,
                    context=context,
                )

            if not isinstance(entry, dict):
                error_msg = f"Entry must be dict or string, got {type(entry).__name__}"
                errors_list.append(error_msg)
                # Create a fallback ValidatedEntry for error cases
                validated_entry = ValidatedEntry(type="error", content=str(entry))
                return ValidationResult(
                    success=False,
                    entry=validated_entry,
                    warnings=warnings_list,
                    errors=errors_list,
                    context=context,
                )

            # Valid dict entry
            validated_entry = ValidatedEntry.from_dict(entry)

            return ValidationResult(
                success=True,
                entry=validated_entry,
                warnings=warnings_list,
                errors=errors_list,
                context=context,
            )

        except Exception as e:
            errors_list.append(str(e))
            validated_entry = ValidatedEntry(type="error", content=str(entry))
            return ValidationResult(
                success=False,
                entry=validated_entry,
                warnings=warnings_list,
                errors=errors_list,
                context=context,
            )

    def validate_required_fields(
        self,
        entry: ValidatedEntry,
        required_fields: set[str],
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate that required fields are present in an entry.

        Args:
            entry: The ValidatedEntry to validate
            required_fields: Set of required field names
            context: ValidationContext for validation parameters

        Returns:
            ValidationResult with validation information
        """
        # Use original entry data from context if available, otherwise use ValidatedEntry
        if context and isinstance(context.entry_data, dict):
            available_fields = set(context.entry_data.keys())
        else:
            # Fallback to checking non-None fields in ValidatedEntry
            entry_dict = entry.model_dump()
            available_fields = {k for k, v in entry_dict.items() if v is not None}

        missing_fields = required_fields - available_fields

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(sorted(missing_fields))}"

            return ValidationResult(
                success=False,
                entry=entry,
                warnings=[],
                errors=[error_msg],
                context=context,
            )

        # No missing fields
        return ValidationResult(
            success=True,
            entry=entry,
            warnings=[],
            errors=[],
            context=context,
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
        self._statistics.reset()

    def log_statistics(self) -> None:
        """Log current processing statistics."""
        stats = self._statistics

        if stats.total_entries == 0:
            logger.info("No entry processing statistics available")
            return

        logger.info(
            f"Entry processing statistics: {stats.total_entries} total entries processed"
        )

        # Log validation metrics
        if stats.validation_errors > 0:
            logger.warning(f"Validation errors encountered: {stats.validation_errors}")
        if stats.validation_warnings > 0:
            logger.info(f"Validation warnings encountered: {stats.validation_warnings}")

        # Log known types
        known_stats = {
            entry_type: count
            for entry_type, count in stats.entry_counts.items()
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
            for entry_type, count in stats.entry_counts.items()
            if entry_type in stats.unknown_types
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


def reset_entry_registry() -> None:
    """Reset the global entry type registry (for testing).

    This recreates the global registry instance to ensure clean state.
    """
    global _global_registry
    _global_registry = EntryTypeRegistry()


def set_validation_mode(mode: ValidationMode) -> None:
    """Set the global validation mode."""
    _global_registry.validation_mode = mode
