"""Validation error tracking and deduplication system."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, TypedDict

from pydantic import ValidationError


class ErrorContext(TypedDict, total=False):
    """Context information for validation errors."""

    file: str
    item_name: str
    content_type: str


class ErrorDetails(TypedDict):
    """Stored details for a validation error."""

    error_type: str
    message: str
    field_path: str
    first_context: ErrorContext


class ErrorSummary(TypedDict):
    """Summary information for an error."""

    count: int
    files: list[str]
    error_type: str
    message: str
    field_path: str


class ValidationErrorTracker:
    """Tracks and deduplicates validation errors across processing sessions.

    This class helps reduce duplicate logging by:
    1. Creating unique signatures for validation errors
    2. Tracking which errors have already been logged
    3. Providing summary statistics and reporting
    4. Categorizing errors for better troubleshooting
    """

    def __init__(self) -> None:
        """Initialize the error tracker."""
        self._logged_errors: set[str] = set()
        self._error_counts: dict[str, int] = defaultdict(int)
        self._error_files: dict[str, set[str]] = defaultdict(set)
        self._error_details: dict[str, ErrorDetails] = {}

    def should_log_error(self, error: ValidationError, context: ErrorContext) -> bool:
        """Check if this error should be logged (not already seen).

        Args:
            error: The ValidationError to check
            context: Context information (file, item_name, etc.)

        Returns:
            True if error should be logged, False if already seen
        """
        error_signature = self._create_error_signature(error, context)
        return error_signature not in self._logged_errors

    def record_error(self, error: ValidationError, context: ErrorContext) -> None:
        """Record a validation error for tracking and statistics.

        Args:
            error: The ValidationError to record
            context: Context information (file, item_name, etc.)
        """
        error_signature = self._create_error_signature(error, context)

        # Mark as logged
        self._logged_errors.add(error_signature)

        # Update counts and file tracking
        self._error_counts[error_signature] += 1
        if "file" in context:
            self._error_files[error_signature].add(context["file"])

        # Store error details for summary
        if error_signature not in self._error_details:
            self._error_details[error_signature] = ErrorDetails(
                error_type=self._categorize_error(error),
                message=self._extract_core_message(error),
                field_path=self._extract_field_path(error),
                first_context=context.copy(),
            )

    def get_summary(self) -> dict[str, ErrorSummary]:
        """Get a summary of all recorded validation errors.

        Returns:
            Dictionary mapping error signatures to error details with counts
        """
        summary: dict[str, ErrorSummary] = {}

        for error_sig in self._error_counts:
            summary[error_sig] = ErrorSummary(
                count=self._error_counts[error_sig],
                files=list(self._error_files[error_sig]),
                error_type=self._error_details[error_sig]["error_type"],
                message=self._error_details[error_sig]["message"],
                field_path=self._error_details[error_sig]["field_path"],
            )

        return summary

    def format_error_message(
        self, error: ValidationError, context: ErrorContext
    ) -> str:
        """Format a validation error with contextual information and suggestions.

        Args:
            error: The ValidationError to format
            context: Context information (file, item_name, etc.)

        Returns:
            Formatted error message with context and suggestions
        """
        base_message = str(error)

        # Extract contextual info
        file_name = context.get("file", "unknown file")
        item_name = context.get("item_name", "unknown item")
        content_type = context.get("content_type", "unknown type")

        # Format with context
        formatted_message = (
            f"Validation failed for {content_type.lower()} '{item_name}' "
            f"in {file_name}: {base_message}"
        )

        # Add suggestions for common issues
        suggestion = self._get_error_suggestion(error, context)
        if suggestion:
            formatted_message += f"\nSuggestion: {suggestion}"

        return formatted_message

    def _create_error_signature(
        self, error: ValidationError, context: ErrorContext
    ) -> str:
        """Create a unique signature for a validation error.

        The signature is based on error type, field path, and core message,
        but excludes specific values and file paths to enable deduplication.

        Args:
            error: The ValidationError
            context: Context information

        Returns:
            Unique error signature hash
        """
        # Extract core components that identify the error type
        error_type = self._categorize_error(error)
        field_path = self._extract_field_path(error)
        core_message = self._extract_core_message(error)
        content_type = context.get("content_type", "")

        # Create signature from stable components
        signature_data = f"{error_type}:{field_path}:{core_message}:{content_type}"

        # Hash for consistent, collision-resistant signature
        return hashlib.sha256(signature_data.encode()).hexdigest()[:16]

    def _categorize_error(self, error: ValidationError) -> str:
        """Categorize a validation error by type.

        Args:
            error: The ValidationError to categorize

        Returns:
            Category name for the error
        """
        error_str = str(error).lower()

        if "field required" in error_str or "missing" in error_str:
            return "missing_required_fields"
        elif "input should be a valid" in error_str or "parsing" in error_str:
            return "type_validation_errors"
        elif "unable to parse" in error_str or "parsing" in error_str:
            return "parsing_errors"
        elif "unknown" in error_str or "unrecognized" in error_str:
            return "unknown_structure_errors"
        else:
            return "other_errors"

    def _extract_field_path(self, error: ValidationError) -> str:
        """Extract the field path from a validation error.

        Args:
            error: The ValidationError

        Returns:
            Dot-separated field path
        """
        try:
            # Get first error location
            if error.errors():
                first_error = error.errors()[0]
                loc = first_error.get("loc", ())
                return ".".join(str(part) for part in loc)
        except (AttributeError, IndexError, KeyError):
            pass

        return "unknown_field"

    def _extract_core_message(self, error: ValidationError) -> str:
        """Extract the core error message, removing specific values.

        Args:
            error: The ValidationError

        Returns:
            Generalized error message
        """
        try:
            if error.errors():
                first_error = error.errors()[0]
                msg = first_error.get("msg", str(error))

                # Generalize specific values in common error messages
                generalized = msg

                # Remove specific values from common patterns
                import re

                generalized = re.sub(r"'[^']*'", "'VALUE'", generalized)
                generalized = re.sub(r'"[^"]*"', '"VALUE"', generalized)
                generalized = re.sub(r"\b\d+\b", "NUMBER", generalized)

                return generalized
        except (AttributeError, KeyError):
            pass

        return str(error)

    def _get_error_suggestion(
        self, error: ValidationError, context: ErrorContext
    ) -> str | None:
        """Get a helpful suggestion for fixing a validation error.

        Args:
            error: The ValidationError
            context: Context information

        Returns:
            Suggestion string or None if no specific suggestion available
        """
        error_str = str(error).lower()
        field_path = self._extract_field_path(error)
        content_type = context.get("content_type", "").lower()

        # Suggestions for common field issues
        if "field required" in error_str:
            if content_type == "spell":
                if "level" in field_path:
                    return "Add 'level' field (0 for cantrips, 1-9 for spells)"
                elif "school" in field_path:
                    return "Add 'school' field (A=Abjuration, C=Conjuration, D=Divination, E=Enchantment, V=Evocation, I=Illusion, N=Necromancy, T=Transmutation)"
                elif "components" in field_path:
                    return "Add 'components' object with v/s/m properties (e.g., {'v': true, 's': true})"
            elif content_type == "creature":
                if "alignment" in field_path:
                    return "Add 'alignment' array (e.g., ['L', 'G'] for Lawful Good, or ['N'] for Neutral)"
                elif "ac" in field_path:
                    return "Add 'ac' field as integer or object with armor details"

        elif "input should be a valid" in error_str:
            if "integer" in error_str:
                return f"Ensure {field_path} is a numeric value, not a string"
            elif "boolean" in error_str:
                return f"Ensure {field_path} is true/false, not a string"

        return None
