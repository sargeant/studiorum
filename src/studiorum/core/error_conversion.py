"""
MCP error conversion utilities.

This module provides utilities for converting structured BaseError instances
to MCP-compatible JSON-RPC error responses and for collecting/aggregating
errors from Result patterns.

All bridge functions for exception conversion have been removed in Phase 4.
"""

from __future__ import annotations

from typing import Any

from studiorum.core.error_types import (
    BaseError,
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ProcessingError,
    ValidationError,
)

# Legacy exception imports removed in Phase 3
# Exception classes are no longer used - only Result patterns
from studiorum.core.result import Error, Result, Success, is_error_result

# Bridge functions removed in Phase 4 - error conversion module now only contains MCP utilities


# exception_to_error() removed in Phase 4
# Use Result[T, E] patterns directly instead of converting exceptions


# wrap_exception_as_result() removed in Phase 4
# Write functions to return Result[T, E] directly instead of using exception wrappers


# unwrap_or_raise() removed in Phase 4
# Use isinstance(result, Error) and proper Result[T, E] handling instead


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
