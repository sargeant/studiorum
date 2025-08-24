"""Legacy exception classes removed in Phase 3.

This module now only contains EntryProcessingWarning for backward compatibility.
All error handling has been migrated to Result[T, E] patterns using structured
error types from studiorum.core.error_types.

For new code, use:
- create_processing_error() instead of EntryProcessingError
- create_validation_error() instead of EntryValidationError
- create_unknown_type_error() instead of UnknownEntryTypeError
- Result[T, E] patterns instead of raising exceptions
"""


class EntryProcessingWarning(UserWarning):
    """Warning for non-fatal entry processing issues.

    This warning is kept for backward compatibility with existing code
    that uses warnings.warn() for non-fatal issues. New code should
    prefer Result[T, E] patterns with appropriate severity levels.
    """

    pass
