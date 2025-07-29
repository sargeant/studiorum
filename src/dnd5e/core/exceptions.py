"""Custom exceptions for D&D 5e content processing."""

from typing import Any


class DnD5eError(Exception):
    """Base exception for all D&D 5e processing errors."""

    pass


class EntryProcessingError(DnD5eError):
    """Base exception for entry processing issues.

    This exception provides context about where the error occurred
    during entry processing, including source information and parent context.
    """

    def __init__(
        self,
        message: str,
        entry: dict[str, Any] | None = None,
        source: str | None = None,
        parent_name: str | None = None,
        entry_type: str | None = None,
    ):
        """Initialize entry processing error with context.

        Args:
            message: Error message describing what went wrong
            entry: The entry dict that caused the error
            source: Source file or book name
            parent_name: Name of parent section/container
            entry_type: Type of entry being processed
        """
        self.entry = entry
        self.source = source
        self.parent_name = parent_name
        self.entry_type = entry_type

        # Build contextual error message
        context_parts = []
        if source:
            context_parts.append(f"source: {source}")
        if parent_name:
            context_parts.append(f"parent: {parent_name}")
        if entry_type:
            context_parts.append(f"type: {entry_type}")

        if context_parts:
            context_str = " (" + ", ".join(context_parts) + ")"
            super().__init__(f"{message}{context_str}")
        else:
            super().__init__(message)


class UnknownEntryTypeError(EntryProcessingError):
    """Exception raised when an unknown entry type is encountered.

    This exception is raised when the entry processor encounters an entry
    type that is not in the known entry type registry.
    """

    def __init__(
        self,
        entry_type: str,
        entry: dict[str, Any] | None = None,
        source: str | None = None,
        parent_name: str | None = None,
    ):
        """Initialize unknown entry type error.

        Args:
            entry_type: The unknown entry type that was encountered
            entry: The entry dict with the unknown type
            source: Source file or book name
            parent_name: Name of parent section/container
        """
        message = f"Unknown entry type: '{entry_type}'"
        super().__init__(
            message=message,
            entry=entry,
            source=source,
            parent_name=parent_name,
            entry_type=entry_type,
        )


class EntryValidationError(EntryProcessingError):
    """Exception raised when entry validation fails.

    This exception is raised when an entry fails validation checks,
    such as missing required fields or invalid field values.
    """

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        entry: dict[str, Any] | None = None,
        source: str | None = None,
        parent_name: str | None = None,
        entry_type: str | None = None,
    ):
        """Initialize entry validation error.

        Args:
            message: Validation error message
            field_name: Name of field that failed validation
            entry: The entry dict that failed validation
            source: Source file or book name
            parent_name: Name of parent section/container
            entry_type: Type of entry being validated
        """
        self.field_name = field_name

        if field_name:
            message = f"Validation failed for field '{field_name}': {message}"

        super().__init__(
            message=message,
            entry=entry,
            source=source,
            parent_name=parent_name,
            entry_type=entry_type,
        )


class MalformedEntryError(EntryProcessingError):
    """Exception raised when an entry has structural problems.

    This exception is raised when an entry is malformed in a way that
    prevents basic processing, such as wrong data types or missing
    fundamental structure.
    """

    def __init__(
        self,
        message: str,
        entry: Any | None = None,
        source: str | None = None,
        parent_name: str | None = None,
    ):
        """Initialize malformed entry error.

        Args:
            message: Error message describing the structural problem
            entry: The malformed entry (may not be a dict)
            source: Source file or book name
            parent_name: Name of parent section/container
        """
        # Handle case where entry might not be a dict
        entry_dict = entry if isinstance(entry, dict) else None
        entry_type = entry_dict.get("type") if entry_dict else None

        super().__init__(
            message=f"Malformed entry: {message}",
            entry=entry_dict,
            source=source,
            parent_name=parent_name,
            entry_type=entry_type,
        )


class EntryProcessingWarning(UserWarning):
    """Warning for non-fatal entry processing issues.

    This warning is used for issues that don't prevent processing
    but indicate potential data quality problems.
    """

    pass
