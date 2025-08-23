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
from studiorum.core.exceptions import (
    DnD5eError,
    EntryProcessingError,
    EntryValidationError,
    UnknownEntryTypeError,
)
from studiorum.core.result import Error, Result, Success, is_error_result

T = TypeVar("T")
E = TypeVar("E", bound=BaseError)


def exception_to_error(exception: Exception, source: str | None = None) -> BaseError:
    """
    Convert an exception to a structured error.

    Args:
        exception: Exception to convert
        source: Source location for context

    Returns:
        Structured error appropriate for the exception type
    """
    if isinstance(exception, EntryValidationError):
        return create_validation_error(
            message=str(exception),
            field_name=exception.field_name,
            entry_type=exception.entry_type,
            source=source or exception.source,
            parent_name=exception.parent_name,
            severity=ErrorSeverity.ERROR,
        )

    if isinstance(exception, EntryProcessingError):
        return create_processing_error(
            message=str(exception),
            entry_type=exception.entry_type,
            source=source or exception.source,
            parent_name=exception.parent_name,
            severity=ErrorSeverity.ERROR,
        )

    if isinstance(exception, UnknownEntryTypeError):
        return create_processing_error(
            message=str(exception),
            entry_type=exception.entry_type,
            source=source or exception.source,
            parent_name=exception.parent_name,
            severity=ErrorSeverity.ERROR,
        )

    if isinstance(exception, DnD5eError):
        return ProcessingError(
            message=str(exception),
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.ERROR,
            source=source,
        )

    # Generic exception conversion
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
    Unwrap a Result or convert error back to exception.

    Useful for gradually migrating code that expects exceptions.

    Args:
        result: Result to unwrap

    Returns:
        Success value

    Raises:
        Exception converted from error

    Example:
        ```python
        # Use Result internally but provide exception interface
        def legacy_api(data: dict) -> ProcessedData:
            result = new_result_based_function(data)
            return unwrap_or_raise(result)  # Raises on error
        ```
    """
    if result.is_success():
        return result.unwrap()
    else:
        if is_error_result(result):
            error = result.error
            raise error.to_exception()
        else:
            # This should not happen, but handle gracefully
            raise RuntimeError("Result is neither success nor error")


class ResultMode:
    """Configuration for enabling Result pattern behavior."""

    _enabled = False

    @classmethod
    def enable(cls) -> None:
        """Enable Result pattern mode globally."""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable Result pattern mode globally."""
        cls._enabled = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Result pattern mode is enabled."""
        return cls._enabled


def with_result_mode(
    result_func: Callable[..., Result[T, BaseError]],
    exception_func: Callable[..., T],
) -> Callable[..., T | Result[T, BaseError]]:
    """
    Create a function that can work in both Result and Exception modes.

    Args:
        result_func: Function that returns Result
        exception_func: Function that raises exceptions

    Returns:
        Function that uses Result or Exception based on mode

    Example:
        ```python
        def process_with_result(data: dict) -> Result[ProcessedData, BaseError]:
            # Implementation using Result pattern
            ...

        def process_with_exception(data: dict) -> ProcessedData:
            # Implementation using exceptions
            ...

        # Create hybrid function
        process_data = with_result_mode(process_with_result, process_with_exception)

        # Usage adapts to mode
        ResultMode.enable()
        result = process_data(data)  # Returns Result[ProcessedData, BaseError]

        ResultMode.disable()
        data = process_data(data)  # Returns ProcessedData or raises
        ```
    """

    @functools.wraps(result_func)
    def wrapper(*args: Any, **kwargs: Any) -> T | Result[T, BaseError]:
        if ResultMode.is_enabled():
            return result_func(*args, **kwargs)
        else:
            result = result_func(*args, **kwargs)
            return unwrap_or_raise(result)

    return wrapper


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
