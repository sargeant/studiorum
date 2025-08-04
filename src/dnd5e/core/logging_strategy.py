"""
Consistent logging strategy for error handling.

This module provides standardized logging patterns that work with the Result[T, E]
pattern and integrate with the existing logging infrastructure.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum
from typing import Any

from dnd5e.core.error_types import (
    BaseError,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
)
from dnd5e.core.result import Result


class LogLevel(str, Enum):
    """Standardized log levels for error handling."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorLogFormatter:
    """
    Formatter for error messages with consistent structure.

    Provides standardized formatting for errors across all modules.
    """

    @staticmethod
    def format_error(error: BaseError, include_suggestions: bool = True) -> str:
        """
        Format an error for logging.

        Args:
            error: The error to format
            include_suggestions: Whether to include suggestions in the message

        Returns:
            Formatted error message
        """
        parts = [error.message]

        # Add source information if available
        if error.source:
            parts.append(f"Source: {error.source}")

        # Add category and severity
        parts.append(f"Category: {error.category.value}")
        parts.append(f"Severity: {error.severity.value}")

        # Add suggestions if requested and available
        if include_suggestions and error.suggestions:
            suggestions_str = " | ".join(error.suggestions)
            parts.append(f"Suggestions: {suggestions_str}")

        return " | ".join(parts)

    @staticmethod
    def format_context(context: ErrorContext) -> str:
        """
        Format error context for logging.

        Args:
            context: The error context to format

        Returns:
            Formatted context string
        """
        return context.format_context()

    @staticmethod
    def format_result_error(result: Result[Any, BaseError]) -> str:
        """
        Format a Result error for logging.

        Args:
            result: Result containing an error

        Returns:
            Formatted error message, or empty string if Result is success
        """
        if result.is_success():
            return ""

        error = result.error  # type: ignore[attr-defined]
        return ErrorLogFormatter.format_error(error)


class StandardizedLogger:
    """
    Standardized logger that enforces consistent error handling patterns.

    This class wraps the standard Python logger with error-specific methods
    that ensure consistent formatting and appropriate log levels.
    """

    def __init__(self, name: str, logger: logging.Logger | None = None):
        """
        Initialize the standardized logger.

        Args:
            name: Logger name (usually module name)
            logger: Existing logger instance (creates new if None)
        """
        self.name = name
        self.logger = logger or logging.getLogger(name)
        self.formatter = ErrorLogFormatter()

    def log_error(
        self,
        error: BaseError,
        context: ErrorContext | None = None,
        include_suggestions: bool = True,
    ) -> None:
        """
        Log an error with appropriate level based on severity.

        Args:
            error: Error to log
            context: Optional context information
            include_suggestions: Whether to include suggestions in log message
        """
        # Format the error message
        message = self.formatter.format_error(error, include_suggestions)

        # Add context if provided
        if context:
            context_str = self.formatter.format_context(context)
            message = f"{message} | Context: {context_str}"

        # Log at appropriate level based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message)
        elif error.severity == ErrorSeverity.ERROR:
            self.logger.error(message)
        elif error.severity == ErrorSeverity.WARNING:
            self.logger.warning(message)
        else:  # INFO
            self.logger.info(message)

    def log_result(
        self,
        result: Result[Any, BaseError | list[BaseError]],
        operation: str,
        success_message: str | None = None,
        context: ErrorContext | None = None,
    ) -> None:
        """
        Log the result of an operation.

        Args:
            result: Result to log
            operation: Name of the operation that produced this result
            success_message: Custom success message (default generated if None)
            context: Optional context information
        """
        if result.is_success():
            message = success_message or f"{operation} completed successfully"
            if context:
                context_str = self.formatter.format_context(context)
                message = f"{message} | Context: {context_str}"
            self.logger.info(message)
        else:
            error = result.error  # type: ignore[attr-defined]

            # Handle list of errors (from collect_results)
            if isinstance(error, list):
                # Create context if not provided
                if context is None:
                    context = ErrorContext(operation=operation)

                # Log a summary for multiple errors
                self.error(
                    f"{operation} failed with {len(error)} errors | Context: {context.format_context()}"
                )

                # Log each individual error
                for i, individual_error in enumerate(error):
                    error_context = ErrorContext(
                        operation=f"{operation}_error_{i + 1}",
                        content_type=context.content_type,
                        content_name=context.content_name,
                        file_path=context.file_path,
                        additional_info=context.additional_info,
                    )
                    self.log_error(individual_error, error_context)
            else:
                # Single error
                if context is None:
                    context = ErrorContext(operation=operation)
                self.log_error(error, context)

    def log_validation_summary(
        self,
        total_items: int,
        successful: int,
        failed: int,
        warnings: int,
        operation: str = "validation",
    ) -> None:
        """
        Log a summary of validation results.

        Args:
            total_items: Total number of items processed
            successful: Number of successful validations
            failed: Number of failed validations
            warnings: Number of warnings generated
            operation: Name of the operation
        """
        if failed > 0:
            self.logger.warning(
                f"{operation.title()} completed: {successful}/{total_items} successful, "
                f"{failed} failed, {warnings} warnings"
            )
        elif warnings > 0:
            self.logger.info(
                f"{operation.title()} completed: {successful}/{total_items} successful, "
                f"{warnings} warnings"
            )
        else:
            self.logger.info(
                f"{operation.title()} completed successfully: {successful}/{total_items} items"
            )

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)


@contextmanager
def error_logging_context(
    logger: StandardizedLogger,
    operation: str,
    content_type: str | None = None,
    content_name: str | None = None,
    file_path: str | None = None,
) -> Iterator[ErrorContext]:
    """
    Context manager for error logging with automatic context tracking.

    Args:
        logger: Logger to use for any errors
        operation: Name of the operation being performed
        content_type: Type of content being processed
        content_name: Name of content being processed
        file_path: Path to file being processed

    Yields:
        ErrorContext that can be used for logging

    Examples:
        ```python
        logger = get_standardized_logger(__name__)

        with error_logging_context(
            logger,
            "spell_validation",
            content_type="spell",
            content_name="Fireball"
        ) as context:
            result = validate_spell(spell_data)
            logger.log_result(result, "spell_validation", context=context)
        ```
    """
    context = ErrorContext(
        operation=operation,
        content_type=content_type,
        content_name=content_name,
        file_path=file_path,
    )

    try:
        yield context
    except Exception as e:
        # Log unexpected exceptions with context
        logger.error(f"Unexpected error in {operation}: {e}")
        raise


def get_standardized_logger(name: str) -> StandardizedLogger:
    """
    Get a standardized logger for a module.

    Args:
        name: Module name (usually __name__)

    Returns:
        StandardizedLogger instance

    Examples:
        ```python
        # At module level
        logger = get_standardized_logger(__name__)

        # In functions
        def validate_content(data):
            result = some_validation(data)
            logger.log_result(result, "content_validation")
            return result
        ```
    """
    return StandardizedLogger(name)


def configure_error_logging(
    level: LogLevel = LogLevel.INFO,
    format_string: str | None = None,
) -> None:
    """
    Configure global error logging settings.

    Args:
        level: Default logging level
        format_string: Custom format string for log messages
    """
    # Convert our LogLevel to Python logging level
    python_level = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
    }[level]

    # Default format includes error context
    default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=python_level,
        format=format_string or default_format,
    )


class LoggingStrategy:
    """
    Guidelines for consistent logging across modules.

    This class documents the standardized logging patterns and provides
    utility methods for common logging scenarios.
    """

    @staticmethod
    def should_log_error(error: BaseError, mode: str = "normal") -> bool:
        """
        Determine if an error should be logged based on mode and severity.

        Args:
            error: Error to check
            mode: Logging mode (strict/normal/silent)

        Returns:
            True if error should be logged
        """
        if mode == "strict":
            return True
        elif mode == "normal":
            return error.severity in (
                ErrorSeverity.ERROR,
                ErrorSeverity.CRITICAL,
                ErrorSeverity.WARNING,
            )
        else:  # silent
            return error.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL)

    @staticmethod
    def get_log_level_for_error(error: BaseError) -> LogLevel:
        """
        Get appropriate log level for an error.

        Args:
            error: Error to check

        Returns:
            Appropriate LogLevel
        """
        severity_to_level = {
            ErrorSeverity.CRITICAL: LogLevel.CRITICAL,
            ErrorSeverity.ERROR: LogLevel.ERROR,
            ErrorSeverity.WARNING: LogLevel.WARNING,
            ErrorSeverity.INFO: LogLevel.INFO,
        }
        return severity_to_level[error.severity]

    @staticmethod
    def create_operation_context(
        operation: str,
        **additional_info: Any,
    ) -> ErrorContext:
        """
        Create error context for an operation.

        Args:
            operation: Name of the operation
            **additional_info: Additional context information

        Returns:
            ErrorContext instance
        """
        return ErrorContext(
            operation=operation,
            additional_info=additional_info,
        )


# Module-level example usage
def example_usage() -> None:
    """Example of how to use the standardized logging."""
    # Configure logging
    configure_error_logging(LogLevel.INFO)

    # Get logger for this module
    logger = get_standardized_logger(__name__)

    # Example 1: Log a Result
    from dnd5e.core.error_types import create_validation_error
    from dnd5e.core.result import Error, Success

    # Success case
    success_result: Result[str, BaseError | list[BaseError]] = Success(
        "validated content"
    )
    logger.log_result(
        success_result, "content_validation", "Content validated successfully"
    )

    # Error case
    error = create_validation_error("Missing required field 'name'", field_name="name")
    error_result: Result[str, BaseError | list[BaseError]] = Error(error)
    logger.log_result(error_result, "content_validation")

    # Example 2: Use error logging context
    with error_logging_context(
        logger,
        "spell_processing",
        content_type="spell",
        content_name="Fireball",
        file_path="spells.json",
    ) as context:
        # Simulate some processing
        result: Result[str, BaseError | list[BaseError]] = Success("processed spell")
        logger.log_result(result, "spell_processing", context=context)

    # Example 3: Log validation summary
    logger.log_validation_summary(
        total_items=100,
        successful=95,
        failed=3,
        warnings=2,
        operation="spell_validation",
    )


if __name__ == "__main__":
    example_usage()
