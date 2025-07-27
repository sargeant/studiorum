"""Progress tracking for LaTeX compilation."""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Optional, Protocol

# Type annotation for display_manager (can be None when import fails)
display_manager: Any = None

try:
    from rich.console import Console
    from rich.progress import TaskID

    RICH_AVAILABLE = True

    # Import display manager
    try:
        from dnd5e.cli.display_manager import display_manager

        DISPLAY_MANAGER_AVAILABLE = True
    except ImportError:
        DISPLAY_MANAGER_AVAILABLE = False
        display_manager = None

except ImportError:
    RICH_AVAILABLE = False
    DISPLAY_MANAGER_AVAILABLE = False
    display_manager = None


class ProgressReporter(Protocol):
    """Protocol for progress reporting implementations."""

    def start_compilation(self, engine: str, total_passes: int) -> None:
        """Start compilation tracking."""
        ...

    def start_pass(self, pass_number: int, description: str) -> None:
        """Start a compilation pass."""
        ...

    def update_pass_progress(self, progress: float, status: str) -> None:
        """Update progress within current pass."""
        ...

    def finish_pass(self, success: bool, duration: float) -> None:
        """Finish current pass."""
        ...

    def finish_compilation(self, success: bool, total_duration: float) -> None:
        """Finish compilation."""
        ...

    def show_error(self, message: str) -> None:
        """Display an error message."""
        ...


class RichProgressReporter:
    """Rich-based progress reporter with fancy output."""

    def __init__(self, console: Console | None = None):
        """Initialize rich progress reporter.

        Args:
            console: Rich console instance (created if None)
        """
        if not RICH_AVAILABLE:
            raise ImportError("Rich library not available for progress tracking")

        # Use display manager if available, otherwise fallback to console
        if DISPLAY_MANAGER_AVAILABLE and display_manager is not None:
            self.console = display_manager.console
            self.use_display_manager = True
        else:
            self.console = console or Console()
            self.use_display_manager = False

        self.main_task: TaskID | None = None
        self.pass_task: TaskID | None = None
        self.current_pass = 0
        self.total_passes = 0
        self.start_time = 0.0

    def start_compilation(self, engine: str, total_passes: int) -> None:
        """Start compilation tracking."""
        self.total_passes = total_passes
        self.start_time = time.time()

        if self.use_display_manager and display_manager is not None:
            # Use the display manager's progress system
            self.main_task = display_manager.add_task(
                f"[bold green]Compiling with {engine}", total=total_passes
            )
        else:
            # Fallback: Simple console output (no progress conflicts)
            self.console.print(
                f"[bold cyan]Starting LaTeX compilation with {engine}[/]"
            )

        self.console.print(f"[bold cyan]Starting LaTeX compilation with {engine}[/]")

    def start_pass(self, pass_number: int, description: str) -> None:
        """Start a compilation pass."""
        self.current_pass = pass_number

        if self.use_display_manager and display_manager is not None:
            # Remove previous pass task if it exists
            if self.pass_task:
                # Display manager doesn't have remove_task, so we just create a new one
                pass

            self.pass_task = display_manager.add_task(
                f"[yellow]Pass {pass_number}: {description}", total=100
            )
        else:
            # Fallback: Just log the pass
            self.console.print(f"[yellow]Starting Pass {pass_number}: {description}[/]")

    def update_pass_progress(self, progress: float, status: str) -> None:
        """Update progress within current pass."""
        if self.use_display_manager and display_manager is not None and self.pass_task:
            display_manager.update_task(
                self.pass_task,
                completed=progress * 100,
                description=f"[yellow]Pass {self.current_pass}: {status}",
            )
        elif not self.use_display_manager:
            # Fallback: Log progress
            self.console.print(
                f"[yellow]Pass {self.current_pass}: {status} ({progress:.1%})[/]"
            )

    def finish_pass(self, success: bool, duration: float) -> None:
        """Finish current pass."""
        if self.use_display_manager and display_manager is not None:
            if self.pass_task:
                status_text = "[green]✓[/]" if success else "[red]✗[/]"
                display_manager.update_task(
                    self.pass_task,
                    completed=100,
                    description=f"[yellow]Pass {self.current_pass}: Complete {status_text} ({duration:.1f}s)",
                )

            if self.main_task:
                display_manager.update_task(self.main_task, advance=1)
        else:
            # Fallback: Log completion
            status_text = "✓" if success else "✗"
            self.console.print(
                f"[yellow]Pass {self.current_pass}: Complete {status_text} ({duration:.1f}s)[/]"
            )

    def finish_compilation(self, success: bool, total_duration: float) -> None:
        """Finish compilation."""
        if self.use_display_manager and display_manager is not None:
            # Mark main task as complete
            if self.main_task:
                display_manager.update_task(self.main_task, completed=100)

        # Always log the final result
        status_icon = "✅" if success else "❌"
        status_text = "[bold green]successful[/]" if success else "[bold red]failed[/]"
        self.console.print(
            f"\n{status_icon} Compilation {status_text} in {total_duration:.1f} seconds"
        )

    def show_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[bold red]Error:[/] {message}")


class SimpleProgressReporter:
    """Simple text-based progress reporter."""

    def __init__(self) -> None:
        """Initialize simple progress reporter."""
        self.current_pass = 0
        self.total_passes = 0
        self.start_time = 0.0

    def start_compilation(self, engine: str, total_passes: int) -> None:
        """Start compilation tracking."""
        self.total_passes = total_passes
        self.start_time = time.time()
        print(f"Starting LaTeX compilation with {engine}...")

    def start_pass(self, pass_number: int, description: str) -> None:
        """Start a compilation pass."""
        self.current_pass = pass_number
        print(f"Pass {pass_number}/{self.total_passes}: {description}")

    def update_pass_progress(self, progress: float, status: str) -> None:
        """Update progress within current pass."""
        # Simple reporter doesn't show sub-pass progress
        pass

    def finish_pass(self, success: bool, duration: float) -> None:
        """Finish current pass."""
        status = "✓" if success else "✗"
        print(f"  {status} Pass {self.current_pass} complete ({duration:.1f}s)")

    def finish_compilation(self, success: bool, total_duration: float) -> None:
        """Finish compilation."""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"\n{status}: Compilation finished in {total_duration:.1f} seconds")

    def show_error(self, message: str) -> None:
        """Display an error message."""
        print(f"ERROR: {message}")


class NoProgressReporter:
    """No-op progress reporter for silent operation."""

    def start_compilation(self, engine: str, total_passes: int) -> None:
        """Start compilation tracking."""
        pass

    def start_pass(self, pass_number: int, description: str) -> None:
        """Start a compilation pass."""
        pass

    def update_pass_progress(self, progress: float, status: str) -> None:
        """Update progress within current pass."""
        pass

    def finish_pass(self, success: bool, duration: float) -> None:
        """Finish current pass."""
        pass

    def finish_compilation(self, success: bool, total_duration: float) -> None:
        """Finish compilation."""
        pass

    def show_error(self, message: str) -> None:
        """Display an error message."""
        pass


@dataclass
class CompilationProgress:
    """Tracks compilation progress state."""

    engine: str
    total_passes: int
    current_pass: int = 0
    pass_description: str = ""
    pass_progress: float = 0.0
    pass_status: str = ""
    overall_progress: float = 0.0
    start_time: float = 0.0

    def update_overall_progress(self) -> None:
        """Update overall progress based on current pass."""
        if self.total_passes > 0:
            pass_progress = (self.current_pass - 1) / self.total_passes
            current_pass_progress = self.pass_progress / self.total_passes
            self.overall_progress = min(1.0, pass_progress + current_pass_progress)


class ProgressTracker:
    """Main progress tracking coordinator."""

    def __init__(self, style: str = "rich", console: Console | None = None):
        """Initialize progress tracker.

        Args:
            style: Progress style ("rich", "simple", "none")
            console: Rich console for rich style
        """
        self.style = style
        self._reporter = self._create_reporter(style, console)
        self._progress = CompilationProgress("", 0)

    def _create_reporter(self, style: str, console: Console | None) -> ProgressReporter:
        """Create appropriate progress reporter.

        Args:
            style: Progress style
            console: Rich console

        Returns:
            Progress reporter instance
        """
        if style == "rich" and RICH_AVAILABLE:
            return RichProgressReporter(console)
        elif style == "simple":
            return SimpleProgressReporter()
        else:
            return NoProgressReporter()

    @contextmanager
    def compilation(self, engine: str, total_passes: int) -> Any:
        """Context manager for tracking full compilation.

        Args:
            engine: LaTeX engine being used
            total_passes: Total number of passes expected
        """
        self._progress = CompilationProgress(engine, total_passes)
        self._progress.start_time = time.time()

        try:
            self._reporter.start_compilation(engine, total_passes)
            yield self
        finally:
            duration = time.time() - self._progress.start_time
            # Success is determined by whether any exceptions occurred
            success = True
            try:
                # This will be set to False if an exception occurred
                success = not hasattr(self, "_compilation_failed")
            except:
                success = False

            self._reporter.finish_compilation(success, duration)

    @contextmanager
    def compilation_pass(self, pass_number: int, description: str) -> Any:
        """Context manager for tracking a single compilation pass.

        Args:
            pass_number: Pass number (1-based)
            description: Description of this pass
        """
        self._progress.current_pass = pass_number
        self._progress.pass_description = description
        self._progress.pass_progress = 0.0

        pass_start_time = time.time()

        try:
            self._reporter.start_pass(pass_number, description)
            yield self
            success = True
        except Exception:
            success = False
            self._compilation_failed = True
            raise
        finally:
            duration = time.time() - pass_start_time
            self._reporter.finish_pass(success, duration)

    def update_progress(self, progress: float, status: str = "") -> None:
        """Update progress within current pass.

        Args:
            progress: Progress value (0.0 to 1.0)
            status: Current status description
        """
        self._progress.pass_progress = progress
        self._progress.pass_status = status
        self._progress.update_overall_progress()

        self._reporter.update_pass_progress(progress, status)

    def show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: Error message to display
        """
        self._reporter.show_error(message)

    @property
    def progress(self) -> CompilationProgress:
        """Get current progress state."""
        return self._progress
