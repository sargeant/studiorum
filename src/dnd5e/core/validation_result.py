"""
Standardized validation using Result pattern.

This module provides consistent validation patterns that use Result[T, E]
instead of mixed exception/None return patterns.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from dnd5e.core.error_types import (
    ErrorSeverity,
    ValidationError,
    create_validation_error,
)
from dnd5e.core.result import Error, Result, Success

T = TypeVar("T", bound=BaseModel)


def validate_model[T: BaseModel](
    model_class: type[T],
    data: dict[str, Any],
    source: str | None = None,
    parent_name: str | None = None,
    strict: bool = True,
) -> Result[T, ValidationError]:
    """
    Validate data against a Pydantic model.

    Args:
        model_class: The Pydantic model class to validate against
        data: Data to validate
        source: Source identifier for error context
        parent_name: Parent container name for error context
        strict: Whether to use strict validation

    Returns:
        Success with validated model instance, or Error with validation details

    Examples:
        ```python
        from dnd5e.core.models.spells import Spell

        result = validate_model(Spell, spell_data, source="phb.json")
        if result.is_success():
            spell = result.unwrap()
            print(f"Validated spell: {spell.name}")
        else:
            error = result.error
            print(f"Validation failed: {error.message}")
        ```
    """
    try:
        # Use Pydantic's validation
        validated = model_class.model_validate(data, strict=strict)
        return Success(validated)

    except PydanticValidationError as e:
        # Convert Pydantic error to our standardized error
        error_msg = _format_pydantic_error(e)
        field_name = _extract_primary_field(e)

        validation_error = create_validation_error(
            message=error_msg,
            field_name=field_name,
            entry_type=model_class.__name__,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.ERROR,
            suggestions=_generate_validation_suggestions(e, model_class),
        )

        return Error(validation_error)

    except Exception as e:
        # Handle unexpected validation errors
        validation_error = create_validation_error(
            message=f"Unexpected validation error: {e}",
            entry_type=model_class.__name__,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.CRITICAL,
        )

        return Error(validation_error)


def validate_field[T: BaseModel](
    value: Any,
    validator: Callable[[Any], T],
    field_name: str,
    source: str | None = None,
    parent_name: str | None = None,
) -> Result[T, ValidationError]:
    """
    Validate a single field value.

    Args:
        value: Value to validate
        validator: Function that validates and converts the value
        field_name: Name of the field being validated
        source: Source identifier for error context
        parent_name: Parent container name for error context

    Returns:
        Success with validated value, or Error with validation details

    Examples:
        ```python
        def validate_level(value: Any) -> int:
            if not isinstance(value, int):
                raise ValueError("Level must be an integer")
            if not 1 <= value <= 9:
                raise ValueError("Level must be between 1 and 9")
            return value

        result = validate_field(spell_level, validate_level, "level")
        ```
    """
    try:
        validated = validator(value)
        return Success(validated)

    except (ValueError, TypeError) as e:
        validation_error = create_validation_error(
            message=str(e),
            field_name=field_name,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.ERROR,
        )

        return Error(validation_error)

    except Exception as e:
        validation_error = create_validation_error(
            message=f"Unexpected field validation error: {e}",
            field_name=field_name,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.CRITICAL,
        )

        return Error(validation_error)


def validate_required_field(
    data: dict[str, Any],
    field_name: str,
    source: str | None = None,
    parent_name: str | None = None,
) -> Result[Any, ValidationError]:
    """
    Validate that a required field exists.

    Args:
        data: Data dict to check
        field_name: Name of required field
        source: Source identifier for error context
        parent_name: Parent container name for error context

    Returns:
        Success with field value, or Error if field is missing
    """
    if field_name not in data:
        validation_error = create_validation_error(
            message=f"Required field '{field_name}' is missing",
            field_name=field_name,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.ERROR,
            suggestions=[f"Add '{field_name}' field to the data"],
        )
        return Error(validation_error)

    value = data[field_name]
    if value is None:
        validation_error = create_validation_error(
            message=f"Required field '{field_name}' cannot be null",
            field_name=field_name,
            source=source,
            parent_name=parent_name,
            severity=ErrorSeverity.ERROR,
            suggestions=[f"Provide a valid value for '{field_name}'"],
        )
        return Error(validation_error)

    return Success(value)


def validate_optional_field[T: BaseModel](
    data: dict[str, Any],
    field_name: str,
    default: T | None = None,
) -> Result[T | None, ValidationError]:
    """
    Validate an optional field, returning default if missing.

    Args:
        data: Data dict to check
        field_name: Name of optional field
        default: Default value if field is missing

    Returns:
        Success with field value or default, never fails
    """
    value = data.get(field_name, default)
    return Success(value)


def _format_pydantic_error(error: PydanticValidationError) -> str:
    """Format a Pydantic validation error for display."""
    if len(error.errors()) == 1:
        err = error.errors()[0]
        field = ".".join(str(loc) for loc in err["loc"]) if err["loc"] else "root"
        return f"{field}: {err['msg']}"
    else:
        # Multiple errors - create summary
        return f"{len(error.errors())} validation errors: {error.errors()[0]['msg']}"


def _extract_primary_field(error: PydanticValidationError) -> str | None:
    """Extract the primary field name from a Pydantic error."""
    if error.errors():
        loc = error.errors()[0]["loc"]
        if loc:
            return str(loc[0])
    return None


def _generate_validation_suggestions(
    error: PydanticValidationError,
    model_class: type[BaseModel],
) -> list[str]:
    """Generate helpful suggestions for validation errors."""
    suggestions = []

    for err in error.errors()[:3]:  # Limit to first 3 errors
        err_type = err["type"]
        field = ".".join(str(loc) for loc in err["loc"]) if err["loc"] else "root"

        if err_type == "missing":
            suggestions.append(f"Add required field '{field}' to the data")
        elif err_type == "value_error":
            suggestions.append(f"Check the value format for field '{field}'")
        elif err_type == "type_error":
            expected_type = err.get("ctx", {}).get("expected_type", "correct type")
            suggestions.append(f"Field '{field}' should be of type {expected_type}")
        elif err_type in ("string_too_short", "string_too_long"):
            suggestions.append(f"Check the length requirements for field '{field}'")
        elif err_type in (
            "greater_than",
            "greater_than_equal",
            "less_than",
            "less_than_equal",
        ):
            suggestions.append(f"Check the numeric constraints for field '{field}'")

    # Add general suggestion if no specific ones
    if not suggestions:
        suggestions.append("Check the data format and required fields")

    return suggestions


class ValidationMode:
    """
    Validation mode configuration for different strictness levels.
    """

    STRICT = "strict"  # Fail on any validation error
    PERMISSIVE = "permissive"  # Continue processing, collect errors
    SILENT = "silent"  # Continue processing, ignore errors

    @classmethod
    def should_raise(cls, mode: str, error: ValidationError) -> bool:
        """Determine if an error should be raised based on mode."""
        if mode == cls.STRICT:
            return True
        elif mode == cls.PERMISSIVE:
            return error.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)
        else:  # SILENT
            return error.severity == ErrorSeverity.CRITICAL

    @classmethod
    def should_log(cls, mode: str, error: ValidationError) -> bool:
        """Determine if an error should be logged based on mode."""
        if mode == cls.STRICT:
            return True
        elif mode == cls.PERMISSIVE:
            return True
        else:  # SILENT
            return error.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)


def validate_with_mode[T: BaseModel](
    validation_fn: Callable[[], Result[T, ValidationError]],
    mode: str = ValidationMode.STRICT,
) -> Result[T, ValidationError]:
    """
    Execute validation with a specific mode.

    Args:
        validation_fn: Function that performs validation
        mode: Validation mode (strict/permissive/silent)

    Returns:
        Result of validation, potentially modified based on mode
    """
    result = validation_fn()

    if result.is_error():
        error = result.error  # type: ignore[attr-defined]

        # Adjust error severity based on mode
        if mode == ValidationMode.SILENT and error.severity == ErrorSeverity.WARNING:
            # In silent mode, convert warnings to info
            adjusted_error = ValidationError(
                message=error.message,
                category=error.category,
                severity=ErrorSeverity.INFO,
                source=error.source,
                suggestions=error.suggestions,
                field_name=error.field_name,
                entry_type=error.entry_type,
                parent_name=error.parent_name,
            )
            return Error(adjusted_error)

    return result
