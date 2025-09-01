"""Progress adapter for bridging DisplayManager to ProgressCallback protocol.

Provides clean separation between CLI display layer and service progress reporting
while enabling granular progress updates during data loading operations.
"""

import time
from typing import Any

from studiorum.cli.display_manager import DisplayManager, TaskID
from studiorum.core.protocols.progress import ProgressCallback


class DisplayProgressAdapter:
    """Adapter bridging DisplayManager to ProgressCallback protocol.

    Enables service layer progress reporting without coupling to Rich UI.
    Includes throttling to prevent update flooding.
    """

    def __init__(
        self,
        display_manager: DisplayManager,
        *,
        throttle_ms: int = 50,
    ) -> None:
        """Initialize adapter with throttling.

        Args:
            display_manager: DisplayManager instance for UI updates
            throttle_ms: Minimum milliseconds between updates (default 50ms)
        """
        self._display = display_manager
        self._throttle_ms = throttle_ms / 1000.0  # Convert to seconds
        self._active_operations: dict[str, TaskID] = {}
        self._last_updates: dict[str, float] = {}
        self._operation_counter = 0

    def start_operation(
        self,
        operation: str,
        *,
        total: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start progress-tracked operation with DisplayManager task.

        Args:
            operation: Operation description for display
            total: Total work units (None for indeterminate)
            metadata: Additional context (ignored by adapter)

        Returns:
            Operation ID for subsequent updates
        """
        # Generate unique operation ID
        self._operation_counter += 1
        operation_id = f"op_{self._operation_counter}"

        # Create task in DisplayManager
        task_id = self._display.add_task(operation, total=total)
        self._active_operations[operation_id] = task_id
        self._last_updates[operation_id] = 0.0

        return operation_id

    def update_progress(
        self,
        operation_id: str,
        *,
        advance: int | None = None,
        completed: int | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update operation progress with throttling.

        Args:
            operation_id: ID from start_operation()
            advance: Amount to advance progress
            completed: Absolute completion amount
            description: Update operation description
            metadata: Additional context (ignored)
        """
        if operation_id not in self._active_operations:
            return  # Silently ignore unknown operations

        # Throttle updates to prevent flooding
        current_time = time.time()
        if current_time - self._last_updates.get(operation_id, 0) < self._throttle_ms:
            return

        task_id = self._active_operations[operation_id]
        self._display.update_task(
            task_id,
            advance=advance,
            completed=completed,
            description=description,
        )

        self._last_updates[operation_id] = current_time

    def complete_operation(
        self,
        operation_id: str,
        *,
        result: str | None = None,
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Complete operation and clean up tracking.

        Args:
            operation_id: ID from start_operation()
            result: Success message (updates description if provided)
            error: Exception if failed (ignored - caller handles)
            metadata: Additional context (ignored)
        """
        if operation_id not in self._active_operations:
            return  # Silently ignore unknown operations

        task_id = self._active_operations[operation_id]

        # Update task to completion with final message if provided
        if result:
            self._display.update_task(task_id, completed=100, description=result)
        else:
            self._display.update_task(task_id, completed=100)

        # Clean up tracking
        del self._active_operations[operation_id]
        del self._last_updates[operation_id]


class NullProgressAdapter:
    """Null progress adapter for testing and no-progress scenarios."""

    def start_operation(
        self,
        operation: str,
        *,
        total: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return "null_op"

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


def create_progress_adapter(display_manager: DisplayManager) -> ProgressCallback:
    """Create progress adapter for DisplayManager.

    Checks STUDIORUM_PROGRESS environment variable to disable progress.

    Args:
        display_manager: DisplayManager instance

    Returns:
        ProgressCallback implementation
    """
    import os

    # Check if progress is disabled via environment variable
    if os.getenv("STUDIORUM_PROGRESS", "true").lower() in ("false", "0", "no", "off"):
        return NullProgressAdapter()

    return DisplayProgressAdapter(display_manager)


def create_null_progress_adapter() -> ProgressCallback:
    """Create null progress adapter for testing.

    Returns:
        No-op ProgressCallback implementation
    """
    return NullProgressAdapter()
