"""LaTeX compilation configuration and settings."""

from enum import Enum
from pathlib import Path
from typing import Any, TypedDict, Unpack

from pydantic import BaseModel, Field, field_validator

from studiorum.core.security import ExecutableNotFoundError, get_latex_executable

# Engine-Package Compatibility Matrix
# Defines which LaTeX packages are supported by each engine
ENGINE_PACKAGE_COMPATIBILITY: dict[str, set[str]] = {
    "lualatex": {
        # LuaLaTeX supports all packages including Unicode and system fonts
        "dndbook",
        "dnd",
        "fontspec",
        "geometry",
        "xcolor",
        "graphicx",
        "fancyhdr",
        "tikz",
        "tcolorbox",
        "hyperref",
        "enumitem",
        "multicol",
        "caption",
        "amsmath",
        "amsfonts",
        "amssymb",
        "babel",
        "polyglossia",
        "unicode-math",
    },
    "xelatex": {
        # XeLaTeX supports most packages including fontspec for system fonts
        "dndbook",
        "dnd",
        "fontspec",
        "geometry",
        "xcolor",
        "graphicx",
        "fancyhdr",
        "tikz",
        "tcolorbox",
        "hyperref",
        "enumitem",
        "multicol",
        "caption",
        "amsmath",
        "amsfonts",
        "amssymb",
        "babel",
        "polyglossia",
    },
    "pdflatex": {
        # PDFLaTeX is more limited - no fontspec, no system fonts, limited Unicode
        "dndbook",
        "dnd",
        "geometry",
        "xcolor",
        "graphicx",
        "fancyhdr",
        "tikz",
        "tcolorbox",
        "hyperref",
        "enumitem",
        "multicol",
        "caption",
        "amsmath",
        "amsfonts",
        "amssymb",
        "babel",
        "inputenc",
        "fontenc",
    },
}


class CompilationConfigKwargs(TypedDict, total=False):
    """Keyword arguments for CompilationConfig."""

    primary_engine: "LaTeXEngine"
    fallback_engines: list["LaTeXEngine"]
    max_passes: int
    timeout_seconds: int
    output_dir: Path | None
    keep_intermediate_files: bool
    verbose_logging: bool
    engine_options: dict[str, list[str]]
    check_dependencies: bool
    required_packages: list[str]
    show_progress: bool
    progress_style: str


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


class CompilationConfig(BaseModel):
    """Configuration for LaTeX compilation process."""

    # Engine configuration
    primary_engine: LaTeXEngine = Field(
        default=LaTeXEngine.LUALATEX, description="Primary LaTeX engine to use"
    )
    fallback_engines: list[LaTeXEngine] = Field(
        default_factory=lambda: [LaTeXEngine.XELATEX],
        description="Fallback engines to try if primary fails",
    )

    # Compilation behavior
    mode: CompilationMode = Field(
        default=CompilationMode.NORMAL, description="Compilation mode"
    )
    max_passes: int = Field(
        default=4, ge=1, le=10, description="Maximum compilation passes"
    )
    timeout_seconds: int = Field(
        default=300, ge=10, le=3600, description="Timeout per compilation pass"
    )

    # Output configuration
    output_dir: Path | None = Field(
        None, description="Output directory for compiled files"
    )
    keep_intermediate_files: bool = Field(
        default=False, description="Keep intermediate LaTeX files"
    )
    verbose_logging: bool = Field(
        default=False, description="Enable verbose compilation logging"
    )

    # Engine-specific options
    engine_options: dict[str, list[str]] = Field(
        default_factory=dict, description="Engine-specific command options"
    )

    # Dependency checking
    check_dependencies: bool = Field(
        default=True, description="Check for required LaTeX packages"
    )
    required_packages: list[str] = Field(
        default_factory=lambda: ["dndbook", "dnd"],
        description="Required LaTeX packages",
    )

    # Progress tracking
    show_progress: bool = Field(default=True, description="Show compilation progress")
    progress_style: str = Field(default="rich", description="Progress display style")

    @field_validator("progress_style")
    @classmethod
    def validate_progress_style(cls, v: str) -> str:
        """Validate progress style is supported."""
        valid_styles = {"rich", "simple", "none"}
        if v not in valid_styles:
            raise ValueError(
                f"Invalid progress style: {v}. Must be one of {valid_styles}"
            )
        return v

    @field_validator("engine_options")
    @classmethod
    def validate_engine_options(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        """Validate engine options format."""
        valid_engines = {engine.value for engine in LaTeXEngine}
        for engine in v:
            if engine not in valid_engines:
                raise ValueError(f"Unknown LaTeX engine: {engine}")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Initialize default engine options."""
        if not self.engine_options:
            self.engine_options = self._get_default_engine_options()

    def _get_default_engine_options(self) -> dict[str, list[str]]:
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

    def get_engine_command(self, engine: LaTeXEngine) -> list[str]:
        """Get the complete command for a LaTeX engine.

        Args:
            engine: LaTeX engine to use

        Returns:
            Command as list of strings

        Raises:
            ExecutableNotFoundError: If the LaTeX engine is not found
        """
        # Use secure executable path resolution to prevent B607 vulnerabilities
        engine_path = get_latex_executable(engine.value)
        cmd = [engine_path]
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
    def for_mode(
        cls, mode: CompilationMode, **kwargs: Unpack[CompilationConfigKwargs]
    ) -> "CompilationConfig":
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

    def validate_config(self) -> list[str]:
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

        # Validate engine-package compatibility
        compatibility_errors = self.validate_engine_package_compatibility()
        errors.extend(compatibility_errors)

        return errors

    def get_compatible_engines(
        self, packages: list[str] | None = None
    ) -> list[LaTeXEngine]:
        """Get engines compatible with the required packages.

        Args:
            packages: List of required packages. If None, uses self.required_packages

        Returns:
            List of engines that support all required packages
        """
        if packages is None:
            packages = self.required_packages

        compatible_engines = []
        all_engines = [self.primary_engine] + self.fallback_engines

        for engine in all_engines:
            if self.is_engine_compatible_with_packages(engine, packages):
                compatible_engines.append(engine)

        return compatible_engines

    def is_engine_compatible_with_packages(
        self, engine: LaTeXEngine, packages: list[str]
    ) -> bool:
        """Check if an engine supports all required packages.

        Args:
            engine: LaTeX engine to check
            packages: List of required packages

        Returns:
            True if engine supports all packages
        """
        supported_packages = ENGINE_PACKAGE_COMPATIBILITY.get(engine.value, set())
        return all(package in supported_packages for package in packages)

    def get_filtered_fallback_engines(self) -> list[LaTeXEngine]:
        """Get fallback engines filtered by package compatibility.

        Returns:
            List of fallback engines compatible with required packages
        """
        return [
            engine
            for engine in self.fallback_engines
            if self.is_engine_compatible_with_packages(engine, self.required_packages)
        ]

    def validate_engine_package_compatibility(self) -> list[str]:
        """Validate that primary and fallback engines support required packages.

        Returns:
            List of compatibility errors (empty if all compatible)
        """
        errors = []

        # Check primary engine
        if not self.is_engine_compatible_with_packages(
            self.primary_engine, self.required_packages
        ):
            incompatible_packages = [
                pkg
                for pkg in self.required_packages
                if pkg
                not in ENGINE_PACKAGE_COMPATIBILITY.get(
                    self.primary_engine.value, set()
                )
            ]
            errors.append(
                f"Primary engine {self.primary_engine.value} doesn't support packages: "
                f"{', '.join(incompatible_packages)}"
            )

        # Check if any fallback engines are compatible
        compatible_fallbacks = self.get_filtered_fallback_engines()
        if not compatible_fallbacks:
            errors.append(
                f"No fallback engines support all required packages: {', '.join(self.required_packages)}"
            )

        return errors


class CompilationResult(BaseModel):
    """Result of a LaTeX compilation attempt."""

    success: bool = Field(description="Whether compilation was successful")
    engine_used: LaTeXEngine = Field(description="LaTeX engine that was used")
    passes_completed: int = Field(
        ge=0, description="Number of compilation passes completed"
    )
    total_time: float = Field(ge=0.0, description="Total compilation time in seconds")
    output_file: Path | None = Field(None, description="Path to compiled output file")
    log_file: Path | None = Field(None, description="Path to compilation log file")
    error_message: str | None = Field(
        None, description="Error message if compilation failed"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of compilation warnings"
    )

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


class CompilationPass(BaseModel):
    """Information about a single compilation pass."""

    pass_number: int = Field(ge=1, description="Pass number (1-based)")
    engine: LaTeXEngine = Field(description="LaTeX engine used for this pass")
    command: list[str] = Field(description="Command line arguments used")
    start_time: float = Field(description="Start time timestamp")
    end_time: float | None = Field(None, description="End time timestamp")
    return_code: int | None = Field(None, description="Process return code")
    stdout: str = Field(default="", description="Standard output from compilation")
    stderr: str = Field(default="", description="Standard error from compilation")
    needs_rerun: bool = Field(
        default=False, description="Whether another pass is needed"
    )

    @property
    def duration(self) -> float | None:
        """Duration of this pass in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def success(self) -> bool:
        """Whether this pass completed successfully."""
        return self.return_code == 0
