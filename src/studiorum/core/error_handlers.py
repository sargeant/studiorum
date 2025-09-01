"""
MCP-specific error handling utilities.

This module provides utilities for handling errors in MCP server context,
including error aggregation, formatting, and response generation.
"""

from __future__ import annotations

import logging
from typing import Any

from studiorum.core.error_conversion import create_mcp_compatible_error
from studiorum.core.error_types import (
    BaseError,
    ErrorCategory,
    ErrorSeverity,
    MCPError,
    MCPErrorCode,
)
from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, is_error_result

logger = get_logger(__name__)


class ErrorAggregator:
    """
    Aggregates and manages errors during complex operations.

    Useful for operations that can have multiple errors/warnings
    but should continue processing.
    """

    def __init__(self, continue_on_error: bool = True):
        """
        Initialize error aggregator.

        Args:
            continue_on_error: Whether to continue after collecting errors
        """
        self.continue_on_error = continue_on_error
        self.errors: list[BaseError] = []
        self.warnings: list[BaseError] = []

    def add_error(self, error: BaseError) -> None:
        """Add an error to the aggregator."""
        if error.severity == ErrorSeverity.WARNING:
            self.warnings.append(error)
            logger.warning(
                f"Warning: {error.message}",
                extra={
                    "category": error.category.value,
                    "source": error.source,
                },
            )
        else:
            self.errors.append(error)
            logger.error(
                f"Error: {error.message}",
                extra={
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "source": error.source,
                },
            )

    def add_result_error(self, result: Result[Any, BaseError]) -> None:
        """Add an error from a Result if it's an error."""
        if is_error_result(result):
            self.add_error(result.error)

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were collected."""
        return len(self.warnings) > 0

    def should_stop(self) -> bool:
        """Check if processing should stop based on errors and configuration."""
        if not self.continue_on_error and self.has_errors():
            return True

        # Stop on critical errors regardless of continue_on_error setting
        return any(error.severity == ErrorSeverity.CRITICAL for error in self.errors)

    def create_summary_error(self, operation: str) -> BaseError | None:
        """
        Create a summary error if there are any errors.

        Args:
            operation: Description of the operation that had errors

        Returns:
            Summary error, or None if no errors
        """
        if not self.has_errors():
            return None

        error_count = len(self.errors)
        warning_count = len(self.warnings)

        if error_count == 1 and warning_count == 0:
            # Single error - return it directly
            return self.errors[0]

        # Multiple errors - create summary
        message_parts = []
        if error_count > 0:
            message_parts.append(f"{error_count} error{'s' if error_count > 1 else ''}")
        if warning_count > 0:
            message_parts.append(
                f"{warning_count} warning{'s' if warning_count > 1 else ''}"
            )

        summary_message = f"{operation} completed with {' and '.join(message_parts)}"

        # Use most severe error category
        categories = [error.category for error in self.errors]
        if ErrorCategory.SYSTEM_ERROR in categories:
            category = ErrorCategory.SYSTEM_ERROR
        elif ErrorCategory.VALIDATION in categories:
            category = ErrorCategory.VALIDATION
        else:
            category = ErrorCategory.PROCESSING

        from studiorum.core.error_types import ProcessingError

        return ProcessingError(
            message=summary_message,
            category=category,
            severity=ErrorSeverity.ERROR,
            context={
                "error_count": error_count,
                "warning_count": warning_count,
                "errors": [error.message for error in self.errors[:5]],  # First 5
                "warnings": [warning.message for warning in self.warnings[:5]],
            },
            suggestions=[
                "Check individual error messages for specific issues",
                "Review input data and configuration",
            ],
        )

    def to_mcp_error_response(self, operation: str) -> dict[str, Any] | None:
        """
        Create MCP-compatible error response.

        Args:
            operation: Description of the operation

        Returns:
            MCP error response dict, or None if no errors
        """
        summary_error = self.create_summary_error(operation)
        if summary_error is None:
            return None

        return create_mcp_compatible_error(summary_error)


class MCPErrorHandler:
    """
    Handles error formatting and response generation for MCP server.
    """

    @staticmethod
    def format_validation_error(
        message: str,
        field_name: str | None = None,
        suggestions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Format a validation error for MCP response."""
        error = MCPError(
            message=message,
            error_code=MCPErrorCode.VALIDATION_FAILED,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            suggestions=suggestions or [],
            data={"field_name": field_name} if field_name else {},
        )
        return error.to_json_rpc_error()

    @staticmethod
    def format_content_not_found_error(
        content_type: str,
        identifier: str,
        suggestions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Format a content not found error for MCP response."""
        error = MCPError(
            message=f"{content_type} '{identifier}' not found",
            error_code=MCPErrorCode.CONTENT_NOT_FOUND,
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.ERROR,
            suggestions=suggestions
            or [
                f"Check that {content_type.lower()} '{identifier}' exists",
                "Verify spelling and capitalization",
                "Check available sources and filters",
            ],
            data={
                "content_type": content_type,
                "identifier": identifier,
            },
        )
        return error.to_json_rpc_error()

    @staticmethod
    def format_service_error(
        service_name: str,
        operation: str,
        details: str | None = None,
    ) -> dict[str, Any]:
        """Format a service error for MCP response."""
        message = f"Service '{service_name}' failed during {operation}"
        if details:
            message += f": {details}"

        error = MCPError(
            message=message,
            error_code=MCPErrorCode.SERVICE_UNAVAILABLE,
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Try the operation again",
                "Check service configuration",
                "Contact system administrator if problem persists",
            ],
            data={
                "service_name": service_name,
                "operation": operation,
                "details": details,
            },
        )
        return error.to_json_rpc_error()

    @staticmethod
    def format_configuration_error(
        config_section: str,
        issue: str,
        suggestions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Format a configuration error for MCP response."""
        error = MCPError(
            message=f"Configuration error in {config_section}: {issue}",
            error_code=MCPErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.ERROR,
            suggestions=suggestions
            or [
                f"Check configuration for {config_section}",
                "Verify configuration file syntax",
                "Review documentation for required settings",
            ],
            data={
                "config_section": config_section,
                "issue": issue,
            },
        )
        return error.to_json_rpc_error()

    @staticmethod
    def format_processing_error(
        operation: str,
        details: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Format a processing error for MCP response."""
        error = MCPError(
            message=f"Processing failed during {operation}: {details}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Check input data format",
                "Verify data completeness",
                "Try with different parameters",
            ],
            data={
                "operation": operation,
                "details": details,
                **(context or {}),
            },
        )
        return error.to_json_rpc_error()

    @staticmethod
    def format_internal_error(
        operation: str,
        error_details: str | None = None,
        include_debug_info: bool = False,
    ) -> dict[str, Any]:
        """Format an internal error for MCP response."""
        message = f"Internal error during {operation}"
        if error_details and include_debug_info:
            message += f": {error_details}"

        error = MCPError(
            message=message,
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            suggestions=[
                "Report this error to the system administrator",
                "Try the operation again later",
            ],
            data={
                "operation": operation,
                "debug_info": error_details if include_debug_info else None,
            },
        )
        return error.to_json_rpc_error()


def handle_result_error(
    result: Result[Any, BaseError],
    operation: str,
    default_error_code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR,
) -> dict[str, Any] | None:
    """
    Convert a Result error to MCP error response.

    Args:
        result: Result to check and convert
        operation: Operation name for context
        default_error_code: Default error code if conversion fails

    Returns:
        MCP error response dict, or None if result is success

    Example:
        ```python
        result = some_operation()
        error_response = handle_result_error(result, "content search")
        if error_response:
            return error_response

        # Continue with success case
        data = result.unwrap()
        ```
    """
    if result.is_success():
        return None

    if not is_error_result(result):
        return None

    error = result.error

    try:
        return create_mcp_compatible_error(error)
    except Exception as e:
        # Fallback error handling
        logger.error(
            f"Failed to convert error to MCP format: {e}",
            extra={"operation": operation, "original_error": str(error)},
        )

        return MCPErrorHandler.format_internal_error(
            operation=operation,
            error_details=f"Error conversion failed: {e}",
        )


def log_error_context(error: BaseError, operation: str) -> None:
    """
    Log error with full context for debugging.

    Args:
        error: Error to log
        operation: Operation context
    """
    log_level = logging.ERROR
    if error.severity == ErrorSeverity.WARNING:
        log_level = logging.WARNING
    elif error.severity == ErrorSeverity.CRITICAL:
        log_level = logging.CRITICAL

    extra_context = {
        "operation": operation,
        "error_category": error.category.value,
        "error_severity": error.severity.value,
        "error_source": error.source,
    }

    # Add error-specific context
    field_name = getattr(error, "field_name", None)
    if field_name:
        extra_context["field_name"] = field_name
    entry_type = getattr(error, "entry_type", None)
    if entry_type:
        extra_context["entry_type"] = entry_type

    logger.log(log_level, error.message, extra=extra_context)

    # Log suggestions at debug level
    if error.suggestions:
        logger.debug(
            f"Error suggestions for {operation}: {'; '.join(error.suggestions)}",
            extra=extra_context,
        )
