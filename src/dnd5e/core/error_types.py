"""
Error types for use with Result pattern.

This module defines structured error types that work well with the Result[T, E]
pattern while integrating with the existing exception hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from dnd5e.core.exceptions import (
    DnD5eError,
    EntryProcessingError,
    EntryValidationError,
    MalformedEntryError,
    UnknownEntryTypeError,
)


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""

    CRITICAL = "critical"  # System cannot continue
    ERROR = "error"  # Operation failed but system can continue
    WARNING = "warning"  # Potential issue but operation succeeded
    INFO = "info"  # Informational message


class ErrorCategory(str, Enum):
    """Categories of errors for classification."""

    VALIDATION = "validation"  # Data validation failures
    PROCESSING = "processing"  # Content processing failures
    IO = "io"  # File/network I/O failures
    CONFIGURATION = "configuration"  # Configuration/setup issues
    RENDER = "render"  # Rendering/output failures
    SYSTEM = "system"  # System/infrastructure issues


@dataclass(frozen=True)
class BaseError:
    """
    Base error type for Result pattern.

    Provides common fields and functionality for all error types.
    """

    message: str
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.ERROR
    source: str | None = None
    suggestions: list[str] | None = None

    def to_exception(self) -> DnD5eError:
        """Convert this error to an appropriate exception."""
        return DnD5eError(self.message)

    def with_suggestion(self, suggestion: str) -> BaseError:
        """Add a suggestion to this error."""
        suggestions = list(self.suggestions or [])
        suggestions.append(suggestion)
        return self.__class__(
            message=self.message,
            category=self.category,
            severity=self.severity,
            source=self.source,
            suggestions=suggestions,
        )


@dataclass(frozen=True)
class ValidationError(BaseError):
    """Error for validation failures."""

    field_name: str | None = None
    entry_type: str | None = None
    parent_name: str | None = None

    def __post_init__(self) -> None:
        """Ensure category is set to validation."""
        if self.category != ErrorCategory.VALIDATION:
            object.__setattr__(self, "category", ErrorCategory.VALIDATION)

    def to_exception(self) -> EntryValidationError:
        """Convert to EntryValidationError exception."""
        return EntryValidationError(
            message=self.message,
            field_name=self.field_name,
            source=self.source,
            parent_name=self.parent_name,
            entry_type=self.entry_type,
        )


@dataclass(frozen=True)
class ProcessingError(BaseError):
    """Error for content processing failures."""

    entry_type: str | None = None
    parent_name: str | None = None
    context: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Ensure category is set to processing."""
        if self.category != ErrorCategory.PROCESSING:
            object.__setattr__(self, "category", ErrorCategory.PROCESSING)

    def to_exception(self) -> EntryProcessingError:
        """Convert to EntryProcessingError exception."""
        return EntryProcessingError(
            message=self.message,
            source=self.source,
            parent_name=self.parent_name,
            entry_type=self.entry_type,
        )


@dataclass(frozen=True)
class UnknownTypeError(ProcessingError):
    """Error for unknown entry types."""

    available_types: list[str] | None = None

    def __post_init__(self) -> None:
        """Ensure entry_type is required and category is set."""
        super().__post_init__()
        if not self.entry_type:
            raise ValueError("entry_type is required for UnknownTypeError")

    def to_exception(self) -> UnknownEntryTypeError:
        """Convert to UnknownEntryTypeError exception."""
        if not self.entry_type:
            raise ValueError("entry_type is required for UnknownTypeError")
        return UnknownEntryTypeError(
            entry_type=self.entry_type,
            source=self.source,
            parent_name=self.parent_name,
        )


@dataclass(frozen=True)
class MalformedDataError(ProcessingError):
    """Error for malformed data structures."""

    expected_type: str | None = None
    actual_type: str | None = None

    def to_exception(self) -> MalformedEntryError:
        """Convert to MalformedEntryError exception."""
        return MalformedEntryError(
            message=self.message,
            source=self.source,
            parent_name=self.parent_name,
        )


class ErrorContext(BaseModel):
    """
    Context information for error reporting.

    Used to provide additional information about where and how errors occurred.
    """

    operation: str = Field(
        description="The operation being performed when error occurred"
    )
    content_type: str | None = Field(
        default=None, description="Type of content being processed"
    )
    content_name: str | None = Field(
        default=None, description="Name/identifier of content"
    )
    file_path: str | None = Field(
        default=None, description="Path to file being processed"
    )
    line_number: int | None = Field(
        default=None, description="Line number where error occurred"
    )
    additional_info: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )

    def format_context(self) -> str:
        """Format context information for display."""
        parts = [f"Operation: {self.operation}"]

        if self.content_type:
            parts.append(f"Content Type: {self.content_type}")
        if self.content_name:
            parts.append(f"Content: {self.content_name}")
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.line_number:
            parts.append(f"Line: {self.line_number}")

        if self.additional_info:
            for key, value in self.additional_info.items():
                parts.append(f"{key}: {value}")

        return " | ".join(parts)


def create_validation_error(
    message: str,
    field_name: str | None = None,
    entry_type: str | None = None,
    source: str | None = None,
    parent_name: str | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> ValidationError:
    """
    Create a validation error with common parameters.

    Args:
        message: Error message describing the validation failure
        field_name: Name of field that failed validation
        entry_type: Type of entry being validated
        source: Source file or location
        parent_name: Name of parent container
        severity: Error severity level
        suggestions: List of suggestions for fixing the error

    Returns:
        ValidationError instance
    """
    return ValidationError(
        message=message,
        category=ErrorCategory.VALIDATION,
        severity=severity,
        source=source,
        suggestions=suggestions,
        field_name=field_name,
        entry_type=entry_type,
        parent_name=parent_name,
    )


def create_processing_error(
    message: str,
    entry_type: str | None = None,
    source: str | None = None,
    parent_name: str | None = None,
    context: dict[str, Any] | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> ProcessingError:
    """
    Create a processing error with common parameters.

    Args:
        message: Error message describing the processing failure
        entry_type: Type of entry being processed
        source: Source file or location
        parent_name: Name of parent container
        context: Additional context information
        severity: Error severity level
        suggestions: List of suggestions for fixing the error

    Returns:
        ProcessingError instance
    """
    return ProcessingError(
        message=message,
        category=ErrorCategory.PROCESSING,
        severity=severity,
        source=source,
        suggestions=suggestions,
        entry_type=entry_type,
        parent_name=parent_name,
        context=context,
    )


def create_unknown_type_error(
    entry_type: str,
    available_types: list[str] | None = None,
    source: str | None = None,
    parent_name: str | None = None,
    suggestions: list[str] | None = None,
) -> UnknownTypeError:
    """
    Create an unknown type error with suggestions.

    Args:
        entry_type: The unknown entry type
        available_types: List of known entry types
        source: Source file or location
        parent_name: Name of parent container
        suggestions: Custom suggestions (auto-generated if not provided)

    Returns:
        UnknownTypeError instance
    """
    message = f"Unknown entry type: '{entry_type}'"

    # Auto-generate suggestions if not provided
    if suggestions is None:
        suggestions = []
        if available_types:
            # Find similar types (simple string similarity)
            similar = [
                t
                for t in available_types
                if t.lower() in entry_type.lower() or entry_type.lower() in t.lower()
            ]
            if similar:
                suggestions.append(f"Did you mean one of: {', '.join(similar[:3])}?")
            else:
                suggestions.append(
                    f"Available types: {', '.join(available_types[:10])}"
                )

    return UnknownTypeError(
        message=message,
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.ERROR,
        source=source,
        suggestions=suggestions,
        entry_type=entry_type,
        parent_name=parent_name,
        available_types=available_types,
    )
