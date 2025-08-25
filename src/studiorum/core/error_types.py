"""
Error types for use with Result pattern.

This module defines structured error types that work well with the Result[T, E]
pattern while integrating with the existing exception hierarchy.

All error types use Pydantic models for consistency with the codebase and
to provide MCP-compatible JSON-RPC error formatting.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Legacy exception imports removed in Phase 3
# All error handling now uses Result[T, E] patterns exclusively

__all__ = [
    # Enums
    "ErrorSeverity",
    "ErrorCategory",
    "MCPErrorCode",
    # Base error types
    "BaseError",
    "MCPError",
    "ErrorContext",
    # Validation errors
    "ValidationError",
    # Processing errors
    "ProcessingError",
    "UnknownTypeError",
    "MalformedDataError",
    # MCP-specific errors
    "ContentNotFoundError",
    "ContentNotFoundExceptionError",
    "ConfigurationError",
    "ServiceError",
    "PerformanceError",
    "MCPException",
    # Architecture errors (converted from exceptions)
    "ContentSourceError",
    "ContentValidationError",
    "ContentLoadingError",
    "ReferenceTrackingError",
    "TemplateCompositionError",
    # Factory functions
    "create_validation_error",
    "create_processing_error",
    "create_unknown_type_error",
    "create_content_source_error",
    "create_content_validation_error",
    "create_content_loading_error",
    "create_reference_tracking_error",
    "create_template_composition_error",
]


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
    SYSTEM_ERROR = "system_error"  # System/infrastructure issues
    USER_ERROR = "user_error"  # User input errors


class MCPErrorCode(Enum):
    """MCP JSON-RPC error codes for structured error responses."""

    # MCP JSON-RPC standard codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Application-specific error codes (positive range)
    CONTENT_NOT_FOUND = 1001
    VALIDATION_FAILED = 1002
    PROCESSING_ERROR = 1003
    CONFIGURATION_ERROR = 1004
    SERVICE_UNAVAILABLE = 1005


class BaseError(BaseModel):
    """
    Base error type for Result pattern.

    Provides common fields and functionality for all error types.
    Uses Pydantic for consistency with codebase standards.
    """

    model_config = ConfigDict(frozen=True)

    message: str
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.ERROR
    source: str | None = None
    suggestions: list[str] | None = Field(default_factory=list)

    # to_exception() method removed in Phase 3
    # All error handling now uses Result[T, E] patterns

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


class MCPError(BaseModel):
    """MCP-compatible error with structured JSON-RPC response."""

    model_config = ConfigDict(frozen=True)

    message: str
    error_code: MCPErrorCode
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.ERROR
    source: str | None = None
    suggestions: list[str] | None = Field(default_factory=list)
    data: dict[str, Any] | None = Field(default_factory=dict)

    def to_json_rpc_error(self) -> dict[str, Any]:
        """Convert to JSON-RPC error format."""
        return {
            "code": self.error_code.value,
            "message": self.message,
            "data": {
                "category": self.category.value,
                "severity": self.severity.value,
                "source": self.source,
                "suggestions": self.suggestions,
                **(self.data or {}),
            },
        }


class ValidationError(BaseError):
    """Error for validation failures."""

    model_config = ConfigDict(frozen=True)

    field_name: str | None = None
    entry_type: str | None = None
    parent_name: str | None = None
    category: ErrorCategory = ErrorCategory.VALIDATION

    # to_exception() method removed in Phase 3
    # Use Result[T, E] patterns instead of exceptions


class ProcessingError(BaseError):
    """Error for content processing failures."""

    model_config = ConfigDict(frozen=True)

    entry_type: str | None = None
    parent_name: str | None = None
    context: dict[str, Any] | None = Field(default_factory=dict)
    category: ErrorCategory = ErrorCategory.PROCESSING

    # to_exception() method removed in Phase 3
    # Use Result[T, E] patterns instead of exceptions


class UnknownTypeError(ProcessingError):
    """Error for unknown entry types."""

    model_config = ConfigDict(frozen=True)

    available_types: list[str] | None = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        """Ensure entry_type is required."""
        if not self.entry_type:
            raise ValueError("entry_type is required for UnknownTypeError")

    # to_exception() method removed in Phase 3
    # Use Result[T, E] patterns instead of exceptions


class MalformedDataError(ProcessingError):
    """Error for malformed data structures."""

    model_config = ConfigDict(frozen=True)

    expected_type: str | None = None
    actual_type: str | None = None

    # to_exception() method removed in Phase 3
    # Use Result[T, E] patterns instead of exceptions


# New MCP-specific error types


class ContentNotFoundError(MCPError):
    """Content could not be located or resolved."""

    model_config = ConfigDict(frozen=True)

    error_code: MCPErrorCode = MCPErrorCode.CONTENT_NOT_FOUND
    category: ErrorCategory = ErrorCategory.USER_ERROR


class ContentNotFoundExceptionError(Exception):
    """Exception wrapper for ContentNotFoundError model."""

    def __init__(self, content_error: ContentNotFoundError):
        """Initialize with a ContentNotFoundError model."""
        self.content_error = content_error
        super().__init__(content_error.message)


class ConfigurationError(MCPError):
    """Configuration validation or loading failed."""

    model_config = ConfigDict(frozen=True)

    error_code: MCPErrorCode = MCPErrorCode.CONFIGURATION_ERROR
    category: ErrorCategory = ErrorCategory.SYSTEM_ERROR


class ServiceError(MCPError):
    """Service initialization or operation failed."""

    model_config = ConfigDict(frozen=True)

    error_code: MCPErrorCode = MCPErrorCode.SERVICE_UNAVAILABLE
    category: ErrorCategory = ErrorCategory.SYSTEM_ERROR


class PerformanceError(MCPError):
    """Operation exceeded performance constraints."""

    model_config = ConfigDict(frozen=True)

    error_code: MCPErrorCode = MCPErrorCode.PROCESSING_ERROR
    category: ErrorCategory = ErrorCategory.SYSTEM_ERROR


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


class MCPException(Exception):
    """Exception wrapper for MCPError models.

    This allows MCPError models to be raised as exceptions while
    maintaining their structured data format.
    """

    def __init__(self, mcp_error: MCPError):
        """Initialize with an MCPError model."""
        self.mcp_error = mcp_error
        super().__init__(mcp_error.message)

    def to_json_rpc_error(self) -> dict[str, Any]:
        """Convert to JSON-RPC error format."""
        return self.mcp_error.to_json_rpc_error()


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


# Architecture Error Types (converted from exception-based patterns)


class ContentSourceError(BaseError):
    """Error for content source operations."""

    model_config = ConfigDict(frozen=True)

    source_location: str = "unknown"
    source_type: str = "unknown"
    category: ErrorCategory = ErrorCategory.IO


class ContentValidationError(ContentSourceError):
    """Error for content validation failures."""

    model_config = ConfigDict(frozen=True)

    validation_errors: list[str] | None = Field(default_factory=list)
    category: ErrorCategory = ErrorCategory.VALIDATION


class ContentLoadingError(ContentSourceError):
    """Error for content loading failures."""

    model_config = ConfigDict(frozen=True)

    items_processed: int = 0
    items_failed: int = 0
    category: ErrorCategory = ErrorCategory.IO


class ReferenceTrackingError(BaseError):
    """Error for reference tracking operations."""

    model_config = ConfigDict(frozen=True)

    reference_type: str = "unknown"
    reference_name: str = "unknown"
    category: ErrorCategory = ErrorCategory.PROCESSING


class TemplateCompositionError(BaseError):
    """Error for template composition failures."""

    model_config = ConfigDict(frozen=True)

    template_name: str = "unknown"
    component_name: str = "unknown"
    category: ErrorCategory = ErrorCategory.RENDER


def create_content_source_error(
    message: str,
    source_location: str = "unknown",
    source_type: str = "unknown",
    source: str | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> ContentSourceError:
    """Create a content source error with common parameters."""
    return ContentSourceError(
        message=message,
        category=ErrorCategory.IO,
        severity=severity,
        source=source,
        suggestions=suggestions or [],
        source_location=source_location,
        source_type=source_type,
    )


def create_content_validation_error(
    message: str,
    validation_errors: list[str] | None = None,
    source_location: str = "unknown",
    source_type: str = "unknown",
    source: str | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> ContentValidationError:
    """Create a content validation error with common parameters."""
    return ContentValidationError(
        message=message,
        category=ErrorCategory.VALIDATION,
        severity=severity,
        source=source,
        suggestions=suggestions or [],
        source_location=source_location,
        source_type=source_type,
        validation_errors=validation_errors or [],
    )


def create_content_loading_error(
    message: str,
    items_processed: int = 0,
    items_failed: int = 0,
    source_location: str = "unknown",
    source_type: str = "unknown",
    source: str | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> ContentLoadingError:
    """Create a content loading error with common parameters."""
    return ContentLoadingError(
        message=message,
        category=ErrorCategory.IO,
        severity=severity,
        source=source,
        suggestions=suggestions or [],
        source_location=source_location,
        source_type=source_type,
        items_processed=items_processed,
        items_failed=items_failed,
    )


def create_reference_tracking_error(
    message: str,
    reference_type: str = "unknown",
    reference_name: str = "unknown",
    source: str | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> ReferenceTrackingError:
    """Create a reference tracking error with common parameters."""
    return ReferenceTrackingError(
        message=message,
        category=ErrorCategory.PROCESSING,
        severity=severity,
        source=source,
        suggestions=suggestions or [],
        reference_type=reference_type,
        reference_name=reference_name,
    )


def create_template_composition_error(
    message: str,
    template_name: str = "unknown",
    component_name: str = "unknown",
    source: str | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    suggestions: list[str] | None = None,
) -> TemplateCompositionError:
    """Create a template composition error with common parameters."""
    return TemplateCompositionError(
        message=message,
        category=ErrorCategory.RENDER,
        severity=severity,
        source=source,
        suggestions=suggestions or [],
        template_name=template_name,
        component_name=component_name,
    )
