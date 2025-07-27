"""Display manager for coordinating Rich displays across the CLI.

This module provides a centralized display manager that ensures only one
Rich display is active at a time, preventing the "Only one live display
may be active at once" error.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any

from rich.console import Console
from rich.progress import Progress, TaskID


class DisplayManager:
    """Singleton manager for coordinating Rich displays.

    Ensures only one Progress context is active at any time and provides
    a shared Console instance for all CLI operations.
    """

    _instance: DisplayManager | None = None

    def __new__(cls) -> DisplayManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        self.console = Console()
        self._active_progress: Progress | None = None
        self._active_tasks: dict[str, TaskID] = {}
        self._initialized = True

    @contextlib.contextmanager
    def progress(self, description: str = "") -> Iterator[Progress]:
        """Create or reuse the active Progress context.

        Args:
            description: Optional description for logging context

        Yields:
            The active Progress instance

        Raises:
            RuntimeError: If a Progress context is already active
        """
        if self._active_progress is not None:
            # Reuse existing progress instead of creating new one
            yield self._active_progress
            return

        self._active_progress = Progress(console=self.console)
        try:
            with self._active_progress:
                yield self._active_progress
        finally:
            self._active_progress = None
            self._active_tasks.clear()

    def add_task(self, description: str, total: int | None = None) -> TaskID:
        """Add a task to the active progress display.

        Args:
            description: Task description
            total: Total units of work (None for indeterminate)

        Returns:
            Task ID for updating progress

        Raises:
            RuntimeError: If no Progress context is active
        """
        if self._active_progress is None:
            raise RuntimeError(
                "No active progress context. Use display_manager.progress() first."
            )

        task_id = self._active_progress.add_task(description, total=total)
        self._active_tasks[description] = task_id
        return task_id

    def update_task(self, task_id: TaskID, **kwargs: Any) -> None:
        """Update task progress.

        Args:
            task_id: Task ID to update
            **kwargs: Progress update arguments (advance, completed, etc.)
        """
        if self._active_progress is None:
            return  # Silently ignore if no active progress

        self._active_progress.update(task_id, **kwargs)

    def get_task(self, description: str) -> TaskID | None:
        """Get task ID by description.

        Args:
            description: Task description

        Returns:
            Task ID if found, None otherwise
        """
        return self._active_tasks.get(description)

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to the shared console.

        Args:
            *args: Arguments to print
            **kwargs: Console print arguments
        """
        self.console.print(*args, **kwargs)

    def log(self, *args: Any, **kwargs: Any) -> None:
        """Log to the shared console.

        Args:
            *args: Arguments to log
            **kwargs: Console log arguments
        """
        self.console.log(*args, **kwargs)

    @property
    def has_active_progress(self) -> bool:
        """Check if there's an active progress display."""
        return self._active_progress is not None


# Global instance
display_manager = DisplayManager()
