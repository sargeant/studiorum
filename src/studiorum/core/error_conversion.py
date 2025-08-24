"""
Utilities for Result/Exception interoperability during transition period.

This module provides conversion utilities between Result patterns and exceptions
to enable gradual migration from exception-based to Result-based error handling.
"""

from __future__ import annotations

import functools
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

from studiorum.core.error_types import (
    BaseError,
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ProcessingError,
    ServiceError,
    ValidationError,
    create_processing_error,
    create_validation_error,
)

# Legacy exception imports removed in Phase 3
# Exception classes are no longer used - only Result patterns
from studiorum.core.result import Error, Result, Success, is_error_result

T = TypeVar("T")
E = TypeVar("E", bound=BaseError)


def exception_to_error(exception: Exception, source: str | None = None) -> BaseError:
    """
    Convert a generic exception to a structured error.

    This function is maintained for compatibility with external code that still
    raises generic exceptions. All internal code should use Result patterns.

    Args:
        exception: Exception to convert
        source: Source location for context

    Returns:
        Structured error for the exception
    """
    # Generic exception conversion for any remaining exceptions
    return ProcessingError(
        message=f"Unexpected error: {exception}",
        category=ErrorCategory.SYSTEM_ERROR,
        severity=ErrorSeverity.CRITICAL,
        source=source,
        context={"exception_type": type(exception).__name__},
    )


def wrap_exception_as_result[T](
    func: Callable[..., T],
) -> Callable[..., Result[T, BaseError]]:
    """
    Decorator to wrap a function that might raise exceptions into Result pattern.

    Args:
        func: Function that might raise exceptions

    Returns:
        Function that returns Result[T, BaseError]

    Example:
        ```python
        @wrap_exception_as_result
        def risky_operation(data: dict) -> ProcessedData:
            # This might raise exceptions
            return process_data(data)

        # Usage
        result = risky_operation(some_data)
        if result.is_success():
            data = result.unwrap()
        else:
            error = result.error
            print(f"Error: {error.message}")
        ```
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, BaseError]:
        try:
            result = func(*args, **kwargs)
            return Success(result)
        except Exception as e:
            error = exception_to_error(e)
            return Error(error)

    return wrapper


def unwrap_or_raise[T](result: Result[T, BaseError]) -> T:
    """
    Unwrap a Result or raise a RuntimeError for legacy compatibility.

    NOTE: This function is deprecated. New code should handle Result patterns directly.
    It's maintained only for backward compatibility during the migration period.

    Args:
        result: Result to unwrap

    Returns:
        Success value

    Raises:
        RuntimeError with error details

    Example:
        ```python
        # DEPRECATED - Use Result patterns directly instead
        def legacy_api(data: dict) -> ProcessedData:
            result = new_result_based_function(data)
            return unwrap_or_raise(result)  # Raises RuntimeError on error
        ```
    """
    if result.is_success():
        return result.unwrap()
    else:
        if is_error_result(result):
            error = result.error
            # Convert structured error to RuntimeError for legacy compatibility
            raise RuntimeError(f"Operation failed: {error.message}")
        else:
            # This should not happen, but handle gracefully
            raise RuntimeError("Result is neither success nor error")


def collect_errors_and_warnings[T](
    results: list[Result[T, BaseError]],
) -> tuple[list[T], list[BaseError], list[BaseError]]:
    """
    Collect success values, errors, and warnings from a list of results.

    Args:
        results: List of Result objects to process

    Returns:
        Tuple of (success_values, errors, warnings)

    Example:
        ```python
        results = [validate_item(item) for item in items]
        successes, errors, warnings = collect_errors_and_warnings(results)

        if errors:
            print(f"Found {len(errors)} errors")
        if warnings:
            print(f"Found {len(warnings)} warnings")
        print(f"Successfully processed {len(successes)} items")
        ```
    """
    successes: list[T] = []
    errors: list[BaseError] = []
    warnings: list[BaseError] = []

    for result in results:
        if result.is_success():
            successes.append(result.unwrap())
        elif is_error_result(result):
            error = result.error
            if error.severity == ErrorSeverity.WARNING:
                warnings.append(error)
            else:
                errors.append(error)

    return successes, errors, warnings


def create_mcp_compatible_error(
    base_error: BaseError,
    error_code: MCPErrorCode | None = None,
) -> dict[str, Any]:
    """
    Convert a BaseError to MCP-compatible JSON-RPC error format.

    Args:
        base_error: Error to convert
        error_code: Override error code (inferred from category if None)

    Returns:
        JSON-RPC error dict

    Example:
        ```python
        error = create_validation_error("Invalid data", field_name="name")
        mcp_error = create_mcp_compatible_error(error)

        # Returns:
        # {
        #     "code": 1002,
        #     "message": "Invalid data",
        #     "data": {
        #         "category": "validation",
        #         "severity": "error",
        #         "field_name": "name",
        #         ...
        #     }
        # }
        ```
    """
    # Infer error code from category if not provided
    if error_code is None:
        if base_error.category == ErrorCategory.VALIDATION:
            error_code = MCPErrorCode.VALIDATION_FAILED
        elif base_error.category == ErrorCategory.PROCESSING:
            error_code = MCPErrorCode.PROCESSING_ERROR
        elif base_error.category == ErrorCategory.CONFIGURATION:
            error_code = MCPErrorCode.CONFIGURATION_ERROR
        elif base_error.category in (ErrorCategory.SYSTEM_ERROR, ErrorCategory.IO):
            error_code = MCPErrorCode.INTERNAL_ERROR
        else:
            error_code = MCPErrorCode.INTERNAL_ERROR

    # Extract additional data from error-specific fields
    additional_data = {}
    if isinstance(base_error, ValidationError):
        if base_error.field_name:
            additional_data["field_name"] = base_error.field_name
        if base_error.entry_type:
            additional_data["entry_type"] = base_error.entry_type
        if base_error.parent_name:
            additional_data["parent_name"] = base_error.parent_name
    elif isinstance(base_error, ProcessingError):
        if base_error.entry_type:
            additional_data["entry_type"] = base_error.entry_type
        if base_error.parent_name:
            additional_data["parent_name"] = base_error.parent_name
        if base_error.context:
            additional_data.update(base_error.context)

    return {
        "code": error_code.value,
        "message": base_error.message,
        "data": {
            "category": base_error.category.value,
            "severity": base_error.severity.value,
            "source": base_error.source,
            "suggestions": base_error.suggestions or [],
            **additional_data,
        },
    }
