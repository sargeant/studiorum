"""LaTeX compilation configuration and settings."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class LaTeXEngine(Enum):
    """Supported LaTeX engines."""

    LUALATEX = "lualatex"
    XELATEX = "xelatex"
    PDFLATEX = "pdflatex"


class CompilationMode(Enum):
    """Compilation mode options."""

    DRAFT = "draft"  # Fast compilation, minimal features
    NORMAL = "normal"  # Standard compilation
    FINAL = "final"  # Full compilation with all features


@dataclass
class CompilationConfig:
    """Configuration for LaTeX compilation process."""

    # Engine configuration
    primary_engine: LaTeXEngine = LaTeXEngine.LUALATEX
    fallback_engines: List[LaTeXEngine] = field(
        default_factory=lambda: [LaTeXEngine.XELATEX, LaTeXEngine.PDFLATEX]
    )

    # Compilation behavior
    mode: CompilationMode = CompilationMode.NORMAL
    max_passes: int = 4
    timeout_seconds: int = 300  # 5 minutes default

    # Output configuration
    output_dir: Optional[Path] = None
    keep_intermediate_files: bool = False
    verbose_logging: bool = False

    # Engine-specific options
    engine_options: Dict[str, List[str]] = field(default_factory=dict)

    # Dependency checking
    check_dependencies: bool = True
    required_packages: List[str] = field(
        default_factory=lambda: ["dndbook", "dnd", "fontspec"]
    )

    # Progress tracking
    show_progress: bool = True
    progress_style: str = "rich"  # "rich", "simple", "none"

    def __post_init__(self) -> None:
        """Initialize default engine options."""
        if not self.engine_options:
            self.engine_options = self._get_default_engine_options()

    def _get_default_engine_options(self) -> Dict[str, List[str]]:
        """Get default options for each LaTeX engine.

        Returns:
            Dictionary mapping engine names to option lists
        """
        base_options = ["-interaction=nonstopmode", "-file-line-error", "-synctex=1"]

        return {
            LaTeXEngine.LUALATEX.value: base_options
            + ["-shell-escape"],  # Often needed for DND template features
            LaTeXEngine.XELATEX.value: base_options + ["-shell-escape"],
            LaTeXEngine.PDFLATEX.value: base_options,
        }

    def get_engine_command(self, engine: LaTeXEngine) -> List[str]:
        """Get the complete command for a LaTeX engine.

        Args:
            engine: LaTeX engine to use

        Returns:
            Command as list of strings
        """
        cmd = [engine.value]
        cmd.extend(self.engine_options.get(engine.value, []))

        # Add mode-specific options
        if self.mode == CompilationMode.DRAFT:
            cmd.extend(["-draftmode"])

        return cmd

    def should_run_multipass(self) -> bool:
        """Check if multi-pass compilation should be attempted.

        Returns:
            True if multi-pass compilation is enabled
        """
        return self.mode != CompilationMode.DRAFT and self.max_passes > 1

    def get_timeout_for_pass(self, pass_number: int) -> int:
        """Get timeout for a specific compilation pass.

        Args:
            pass_number: Which pass (1-based)

        Returns:
            Timeout in seconds
        """
        # First pass often takes longer
        if pass_number == 1:
            return self.timeout_seconds
        else:
            # Subsequent passes are usually faster
            return min(self.timeout_seconds // 2, 60)

    @classmethod
    def for_mode(cls, mode: CompilationMode, **kwargs: object) -> "CompilationConfig":
        """Create configuration optimized for a specific mode.

        Args:
            mode: Compilation mode
            **kwargs: Additional configuration options

        Returns:
            Optimized configuration
        """
        config = cls(mode=mode, **kwargs)

        if mode == CompilationMode.DRAFT:
            config.max_passes = 1
            config.timeout_seconds = 60
            config.check_dependencies = False
            config.show_progress = False
        elif mode == CompilationMode.FINAL:
            config.max_passes = 5
            config.timeout_seconds = 600  # 10 minutes
            config.check_dependencies = True
            config.keep_intermediate_files = True

        return config

    def validate(self) -> List[str]:
        """Validate the configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if self.max_passes < 1:
            errors.append("max_passes must be at least 1")

        if self.max_passes > 10:
            errors.append("max_passes should not exceed 10 to prevent infinite loops")

        if self.timeout_seconds < 10:
            errors.append("timeout_seconds should be at least 10 seconds")

        if self.output_dir and not isinstance(self.output_dir, Path):
            errors.append("output_dir must be a Path object")

        return errors


@dataclass
class CompilationResult:
    """Result of a LaTeX compilation attempt."""

    success: bool
    engine_used: LaTeXEngine
    passes_completed: int
    total_time: float
    output_file: Optional[Path] = None
    log_file: Optional[Path] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation of compilation result."""
        if self.success:
            return (
                f"Compilation successful using {self.engine_used.value} "
                f"({self.passes_completed} passes, {self.total_time:.1f}s)"
            )
        else:
            return (
                f"Compilation failed using {self.engine_used.value}: "
                f"{self.error_message or 'Unknown error'}"
            )


@dataclass
class CompilationPass:
    """Information about a single compilation pass."""

    pass_number: int
    engine: LaTeXEngine
    command: List[str]
    start_time: float
    end_time: Optional[float] = None
    return_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    needs_rerun: bool = False

    @property
    def duration(self) -> Optional[float]:
        """Duration of this pass in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def success(self) -> bool:
        """Whether this pass completed successfully."""
        return self.return_code == 0
