"""
Entry registry validation using Result pattern.

This module provides validation for entry data structures using the Result[T, E]
pattern. It handles validation of entries in the entry registry system with
standardized error reporting and type safety.
"""

from __future__ import annotations

import logging
from typing import Any

from dnd5e.core.entry_registry import (
    EntryTypeRegistry,
    ValidatedEntry,
    ValidationContext,
    ValidationMode,
    ValidationResult,
)
from dnd5e.core.error_types import (
    ErrorSeverity,
    UnknownTypeError,
    ValidationError,
    create_unknown_type_error,
    create_validation_error,
)
from dnd5e.core.model_validation import validate_required_field
from dnd5e.core.result import Error, Result, Success, collect_results

logger = logging.getLogger(__name__)


class StandardizedEntryValidator:
    """
    Entry validator using standardized Result pattern.

    This class provides a new validation interface that uses Result[T, E]
    while maintaining compatibility with the existing EntryRegistry system.
    """

    def __init__(self, entry_registry: EntryTypeRegistry | None = None):
        """
        Initialize validator with optional registry.

        Args:
            entry_registry: Existing entry registry (creates default if None)
        """
        self.registry = entry_registry or EntryTypeRegistry()

    def validate_entry(
        self,
        entry_data: Any,
        source: str | None = None,
        parent_name: str | None = None,
        validation_mode: ValidationMode = ValidationMode.STRICT,
    ) -> Result[ValidatedEntry, ValidationError]:
        """
        Validate entry data using standardized Result pattern.

        Args:
            entry_data: Entry data to validate (dict, string, or other)
            source: Source file or location identifier
            parent_name: Name of parent container for context
            validation_mode: Validation strictness mode

        Returns:
            Success with ValidatedEntry, or Error with detailed validation information

        Examples:
            ```python
            validator = StandardizedEntryValidator()

            # Validate a dictionary entry
            result = validator.validate_entry(
                {"type": "section", "name": "Combat", "entries": [...]},
                source="phb.json",
                parent_name="Chapter 9"
            )

            if result.is_success():
                entry = result.unwrap()
                print(f"Validated entry: {entry.type}")
            else:
                error = result.error
                logger.error(f"Validation failed: {error.message}")
                for suggestion in error.suggestions or []:
                    logger.info(f"Suggestion: {suggestion}")
            ```
        """
        # Handle empty/null data
        if entry_data is None:
            return Error(
                create_validation_error(
                    message="Entry data cannot be None",
                    source=source,
                    parent_name=parent_name,
                    severity=ErrorSeverity.ERROR,
                    suggestions=[
                        "Provide valid entry data (string, dict, or other supported type)"
                    ],
                )
            )

        # Validate string entries (always valid)
        if isinstance(entry_data, str):
            return Success(ValidatedEntry.from_string(entry_data))

        # Validate dictionary entries
        if isinstance(entry_data, dict):
            return self._validate_dict_entry(
                entry_data, source, parent_name, validation_mode
            )

        # Handle other types
        return self._validate_other_entry(entry_data, source, parent_name)

    def validate_entry_type(
        self,
        entry_type: str,
        source: str | None = None,
        parent_name: str | None = None,
        validation_mode: ValidationMode = ValidationMode.STRICT,
    ) -> Result[str, UnknownTypeError]:
        """
        Validate that an entry type is known.

        Args:
            entry_type: Entry type to validate
            source: Source file or location identifier
            parent_name: Name of parent container for context
            validation_mode: Validation strictness mode

        Returns:
            Success with normalized entry type, or Error with unknown type information
        """
        if self.registry.is_known_type(entry_type):
            return Success(entry_type)

        # Get available types for suggestions
        available_types = list(self.registry.known_types)

        error = create_unknown_type_error(
            entry_type=entry_type,
            available_types=available_types,
            source=source,
            parent_name=parent_name,
        )

        # Adjust severity based on validation mode
        if validation_mode == ValidationMode.SILENT:
            # In silent mode, unknown types are warnings
            error = UnknownTypeError(
                message=error.message,
                category=error.category,
                severity=ErrorSeverity.WARNING,
                source=error.source,
                suggestions=error.suggestions,
                entry_type=error.entry_type,
                parent_name=error.parent_name,
                available_types=error.available_types,
            )
        elif validation_mode == ValidationMode.PERMISSIVE:
            # In permissive mode, unknown types are warnings but continue
            error = UnknownTypeError(
                message=error.message,
                category=error.category,
                severity=ErrorSeverity.WARNING,
                source=error.source,
                suggestions=error.suggestions,
                entry_type=error.entry_type,
                parent_name=error.parent_name,
                available_types=error.available_types,
            )

        return Error(error)

    def validate_entry_batch(
        self,
        entries: list[Any],
        source: str | None = None,
        parent_name: str | None = None,
        validation_mode: ValidationMode = ValidationMode.STRICT,
        continue_on_error: bool = True,
    ) -> Result[list[ValidatedEntry], list[ValidationError]]:
        """
        Validate multiple entries as a batch.

        Args:
            entries: List of entry data to validate
            source: Source file or location identifier
            parent_name: Name of parent container for context
            validation_mode: Validation strictness mode
            continue_on_error: Whether to continue processing after errors

        Returns:
            Success with list of ValidatedEntry objects, or Error with list of validation errors
        """
        results: list[Result[ValidatedEntry, ValidationError]] = []

        for i, entry_data in enumerate(entries):
            # Provide context for each entry
            entry_parent = f"{parent_name}[{i}]" if parent_name else f"entry[{i}]"

            result = self.validate_entry(
                entry_data=entry_data,
                source=source,
                parent_name=entry_parent,
                validation_mode=validation_mode,
            )

            results.append(result)

            # Stop on first error if continue_on_error is False
            if not continue_on_error and result.is_error():
                break

        return collect_results(results)

    def _validate_dict_entry(
        self,
        entry_data: dict[str, Any],
        source: str | None,
        parent_name: str | None,
        validation_mode: ValidationMode,
    ) -> Result[ValidatedEntry, ValidationError]:
        """Validate a dictionary entry."""
        # Extract entry type
        type_result = validate_required_field(entry_data, "type", source, parent_name)
        if type_result.is_error():
            return type_result  # type: ignore[return-value]

        entry_type = str(type_result.unwrap())

        # Validate entry type is known
        type_validation = self.validate_entry_type(
            entry_type, source, parent_name, validation_mode
        )

        if type_validation.is_error():
            error = type_validation.error  # type: ignore[attr-defined]

            # Handle based on validation mode
            if validation_mode == ValidationMode.STRICT:
                # Convert to ValidationError
                validation_error = create_validation_error(
                    message=error.message,
                    field_name="type",
                    entry_type=entry_type,
                    source=source,
                    parent_name=parent_name,
                    severity=error.severity,
                    suggestions=error.suggestions,
                )
                return Error(validation_error)
            else:
                # Log warning but continue
                logger.warning(
                    f"Unknown entry type '{entry_type}' in {source or 'unknown source'}"
                )

        # Create ValidatedEntry from dictionary
        try:
            validated_entry = ValidatedEntry.from_dict(entry_data)
            return Success(validated_entry)

        except Exception as e:
            error = create_validation_error(
                message=f"Failed to create ValidatedEntry: {e}",
                entry_type=entry_type,
                source=source,
                parent_name=parent_name,
                severity=ErrorSeverity.ERROR,
                suggestions=["Check entry structure and required fields"],
            )
            return Error(error)

    def _validate_other_entry(
        self,
        entry_data: Any,
        source: str | None,
        parent_name: str | None,
    ) -> Result[ValidatedEntry, ValidationError]:
        """Validate non-string, non-dict entry data."""
        # Handle lists (convert to entries)
        if isinstance(entry_data, list):
            validated_entry = ValidatedEntry(
                type="list",
                content=None,
                entries=entry_data,
            )
            return Success(validated_entry)

        # Handle other types by converting to string representation
        if hasattr(entry_data, "__str__"):
            content_str = str(entry_data)
            validated_entry = ValidatedEntry(
                type="converted",
                content=content_str,
            )
            return Success(validated_entry)

        # Unsupported type
        error = create_validation_error(
            message=f"Unsupported entry data type: {type(entry_data).__name__}",
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Entry data should be a string, dict, or list",
                f"Convert {type(entry_data).__name__} to a supported format",
            ],
        )
        return Error(error)


def migrate_validation_result(
    validation_result: ValidationResult,
) -> Result[ValidatedEntry, ValidationError]:
    """
    Convert legacy ValidationResult to standardized Result pattern.

    Args:
        validation_result: Legacy ValidationResult from existing code

    Returns:
        Standardized Result with the same information

    Examples:
        ```python
        # Convert existing validation result
        legacy_result = entry_registry.validate_entry_structure(context)
        standardized_result = migrate_validation_result(legacy_result)

        # Now use standardized pattern
        if standardized_result.is_success():
            entry = standardized_result.unwrap()
            # ... process entry
        ```
    """
    if validation_result.success:
        return Success(validation_result.entry)
    else:
        # Combine errors and warnings into a single error message
        error_parts = []
        if validation_result.errors:
            error_parts.extend(validation_result.errors)
        if validation_result.warnings:
            error_parts.extend(f"Warning: {w}" for w in validation_result.warnings)

        message = "; ".join(error_parts) if error_parts else "Validation failed"

        # Extract context information
        context = validation_result.context
        source = context.source if context else None
        parent_name = context.parent_name if context else None
        entry_type = context.entry_type if context else None

        error = create_validation_error(
            message=message,
            entry_type=entry_type,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.ERROR
            if validation_result.errors
            else ErrorSeverity.WARNING,
        )

        return Error(error)


def create_compatibility_wrapper(
    standardized_validator: StandardizedEntryValidator,
) -> EntryTypeRegistry:
    """
    Create a wrapper that provides legacy EntryTypeRegistry interface using standardized validation.

    Args:
        standardized_validator: The new standardized validator

    Returns:
        EntryTypeRegistry-compatible object that uses Result pattern internally

    This allows gradual migration from ValidationResult to Result pattern.
    """

    class CompatibilityWrapper(EntryTypeRegistry):
        def __init__(self, validator: StandardizedEntryValidator):
            super().__init__()
            self._validator = validator

        def validate_entry_structure(
            self, context: ValidationContext
        ) -> ValidationResult:
            """Legacy method that uses Result pattern internally."""
            # Convert to Result pattern
            result = self._validator.validate_entry(
                entry_data=context.entry_data,
                source=context.source,
                parent_name=context.parent_name,
                validation_mode=context.validation_mode or ValidationMode.STRICT,
            )

            # Convert back to ValidationResult for compatibility
            if result.is_success():
                return ValidationResult(
                    success=True,
                    entry=result.unwrap(),
                    warnings=[],
                    errors=[],
                    context=context,
                )
            else:
                error = result.error  # type: ignore[attr-defined]
                return ValidationResult(
                    success=False,
                    entry=ValidatedEntry(type="error", content=error.message),
                    warnings=[]
                    if error.severity != ErrorSeverity.WARNING
                    else [error.message],
                    errors=[error.message]
                    if error.severity == ErrorSeverity.ERROR
                    else [],
                    context=context,
                )

    return CompatibilityWrapper(standardized_validator)


# Example usage and migration patterns
def example_usage() -> None:
    """Example of how to use the standardized validation."""
    validator = StandardizedEntryValidator()

    # Example 1: Validate a single entry
    entry_data = {
        "type": "section",
        "name": "Combat Rules",
        "entries": [
            "Combat is turn-based...",
            {"type": "list", "items": ["Rule 1", "Rule 2"]},
        ],
    }

    result = validator.validate_entry(
        entry_data=entry_data,
        source="phb.json",
        parent_name="Chapter 9",
        validation_mode=ValidationMode.STRICT,
    )

    if result.is_success():
        entry = result.unwrap()
        print(f"Successfully validated {entry.type} entry: {entry.name}")
    else:
        error = result.error  # type: ignore[attr-defined]
        print(f"Validation failed: {error.message}")
        if error.suggestions:
            for suggestion in error.suggestions:
                print(f"  Suggestion: {suggestion}")

    # Example 2: Validate multiple entries
    entries = [
        "This is a text entry",
        {"type": "section", "name": "Section 1"},
        {"type": "unknown_type", "content": "This will warn in permissive mode"},
    ]

    batch_result = validator.validate_entry_batch(
        entries=entries,
        source="sample.json",
        validation_mode=ValidationMode.PERMISSIVE,
    )

    if batch_result.is_success():
        validated_entries = batch_result.unwrap()
        print(f"Successfully validated {len(validated_entries)} entries")
    else:
        errors = batch_result.error  # type: ignore[attr-defined]
        print(f"Batch validation had {len(errors)} errors")

    # Example 3: Migration from legacy code
    from dnd5e.core.entry_registry import EntryTypeRegistry, ValidationContext

    legacy_registry = EntryTypeRegistry()
    context = ValidationContext(
        entry_data={"type": "section", "name": "Test"},
        source="test.json",
    )

    # Legacy way
    legacy_result = legacy_registry.validate_entry_structure(context)

    # Convert to standardized Result
    standardized_result = migrate_validation_result(legacy_result)

    # Now use Result pattern
    entry = standardized_result.unwrap_or_else(
        lambda error: ValidatedEntry(type="error", content=error.message)
    )
    print(f"Migrated result: {entry.type}")


if __name__ == "__main__":
    example_usage()
