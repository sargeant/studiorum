"""Progress reporting protocol for cross-layer communication.

This module provides a protocol-based approach to progress reporting that maintains
architectural separation between CLI and service layers while enabling granular
progress updates during data loading operations.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for reporting progress during long-running operations.

    Enables services to report granular progress without coupling to specific
    display implementations (Rich, logging, etc.).
    """

    def start_operation(
        self,
        operation: str,
        *,
        total: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start a new progress-tracked operation.

        Args:
            operation: Human-readable operation description
            total: Total units of work (None for indeterminate)
            metadata: Additional context for the operation

        Returns:
            Operation ID for subsequent updates
        """
        ...

    def update_progress(
        self,
        operation_id: str,
        *,
        advance: int | None = None,
        completed: int | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update progress for an active operation.

        Args:
            operation_id: ID returned from start_operation()
            advance: Amount to advance progress by
            completed: Set absolute completion amount
            description: Update operation description
            metadata: Additional progress metadata
        """
        ...

    def complete_operation(
        self,
        operation_id: str,
        *,
        result: str | None = None,
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mark an operation as complete.

        Args:
            operation_id: ID returned from start_operation()
            result: Success message or final status
            error: Exception if operation failed
            metadata: Final operation metadata
        """
        ...


@runtime_checkable
class ProgressAwareService(Protocol):
    """Protocol for services that support progress reporting.

    Services implementing this protocol can accept optional progress callbacks
    to report detailed progress during operations.
    """

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Set progress callback for this service.

        Args:
            callback: Progress callback to use (None to disable)
        """
        ...

    def get_progress_callback(self) -> ProgressCallback | None:
        """Get current progress callback.

        Returns:
            Current progress callback or None if not set
        """
        ...


class NoOpProgressCallback:
    """No-op implementation for when progress reporting is disabled."""

    def start_operation(
        self,
        operation: str,
        *,
        total: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return "noop"

    def update_progress(
        self,
        operation_id: str,
        *,
        advance: int | None = None,
        completed: int | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    def complete_operation(
        self,
        operation_id: str,
        *,
        result: str | None = None,
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass
