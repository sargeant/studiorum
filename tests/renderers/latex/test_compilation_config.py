"""Tests for LaTeX compilation configuration."""

from pathlib import Path
from typing import Any

import pytest

from dnd5e.renderers.latex.compilation_config import (  # type: ignore
    CompilationConfig,
    CompilationMode,
    CompilationResult,
    LaTeXEngine,
)


@pytest.mark.rendering
class TestLaTeXEngine:
    """Tests for LaTeX engine enum."""

    def test_engine_values(self) -> None:
        """Test engine enum values."""
        assert LaTeXEngine.LUALATEX.value == "lualatex"
        assert LaTeXEngine.XELATEX.value == "xelatex"
        assert LaTeXEngine.PDFLATEX.value == "pdflatex"


@pytest.mark.rendering
class TestCompilationMode:
    """Tests for compilation mode enum."""

    def test_mode_values(self) -> None:
        """Test mode enum values."""
        assert CompilationMode.DRAFT.value == "draft"
        assert CompilationMode.NORMAL.value == "normal"
        assert CompilationMode.FINAL.value == "final"


@pytest.mark.rendering
class TestCompilationConfig:
    """Tests for compilation configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config: Any = CompilationConfig()

        assert config.primary_engine == LaTeXEngine.LUALATEX
        assert config.fallback_engines == [LaTeXEngine.XELATEX, LaTeXEngine.PDFLATEX]
        assert config.mode == CompilationMode.NORMAL
        assert config.max_passes == 4
        assert config.timeout_seconds == 300
        assert config.output_dir is None
        assert config.keep_intermediate_files is False
        assert config.verbose_logging is False
        assert config.check_dependencies is True
        assert config.show_progress is True
        assert config.progress_style == "rich"

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config: Any = CompilationConfig(
            primary_engine=LaTeXEngine.XELATEX,
            mode=CompilationMode.DRAFT,
            max_passes=2,
            timeout_seconds=120,
            show_progress=False,
        )

        assert config.primary_engine == LaTeXEngine.XELATEX
        assert config.mode == CompilationMode.DRAFT
        assert config.max_passes == 2
        assert config.timeout_seconds == 120
        assert config.show_progress is False

    def test_engine_options_initialization(self) -> None:
        """Test that engine options are properly initialized."""
        config: Any = CompilationConfig()

        assert LaTeXEngine.LUALATEX.value in config.engine_options
        assert LaTeXEngine.XELATEX.value in config.engine_options
        assert LaTeXEngine.PDFLATEX.value in config.engine_options

        # Check that all engines have basic options
        for engine in LaTeXEngine:
            options = config.engine_options[engine.value]
            assert "-interaction=nonstopmode" in options
            assert "-file-line-error" in options
            assert "-synctex=1" in options

    def test_get_engine_command(self) -> None:
        """Test engine command generation."""
        config: Any = CompilationConfig()

        # Test LuaLaTeX command
        cmd = config.get_engine_command(LaTeXEngine.LUALATEX)
        assert cmd[0] == "lualatex"
        assert "-interaction=nonstopmode" in cmd
        assert "-shell-escape" in cmd

        # Test XeLaTeX command
        cmd = config.get_engine_command(LaTeXEngine.XELATEX)
        assert cmd[0] == "xelatex"
        assert "-interaction=nonstopmode" in cmd
        assert "-shell-escape" in cmd

        # Test PDFLaTeX command
        cmd = config.get_engine_command(LaTeXEngine.PDFLATEX)
        assert cmd[0] == "pdflatex"
        assert "-interaction=nonstopmode" in cmd
        assert (
            "-shell-escape" not in cmd
        )  # PDFLaTeX doesn't get shell-escape by default

    def test_get_engine_command_draft_mode(self) -> None:
        """Test engine command generation in draft mode."""
        config: Any = CompilationConfig(mode=CompilationMode.DRAFT)

        cmd = config.get_engine_command(LaTeXEngine.LUALATEX)
        assert "-draftmode" in cmd

    def test_should_run_multipass(self) -> None:
        """Test multipass compilation detection."""
        # Normal mode should run multipass
        config: Any = CompilationConfig(mode=CompilationMode.NORMAL)
        assert config.should_run_multipass() is True

        # Draft mode should not run multipass
        config_draft: Any = CompilationConfig(mode=CompilationMode.DRAFT)
        assert config_draft.should_run_multipass() is False

        # Single pass should not run multipass
        config_single: Any = CompilationConfig(max_passes=1)
        assert config_single.should_run_multipass() is False

    def test_get_timeout_for_pass(self) -> None:
        """Test timeout calculation for passes."""
        config: Any = CompilationConfig(timeout_seconds=300)

        # First pass gets full timeout
        assert config.get_timeout_for_pass(1) == 300

        # Subsequent passes get reduced timeout but capped at 60 seconds
        assert config.get_timeout_for_pass(2) == 60  # min(150, 60) = 60
        assert config.get_timeout_for_pass(3) == 60  # min(150, 60) = 60

        # With smaller initial timeout, gets half
        config_small: Any = CompilationConfig(timeout_seconds=100)
        assert config_small.get_timeout_for_pass(1) == 100
        assert config_small.get_timeout_for_pass(2) == 50  # min(50, 60) = 50

        # With very small timeout, still gets half
        config_tiny: Any = CompilationConfig(timeout_seconds=60)
        assert config_tiny.get_timeout_for_pass(1) == 60
        assert config_tiny.get_timeout_for_pass(2) == 30  # min(30, 60) = 30

    def test_for_mode_draft(self) -> None:
        """Test creating draft mode configuration."""
        config = CompilationConfig.for_mode(CompilationMode.DRAFT)

        assert config.mode == CompilationMode.DRAFT
        assert config.max_passes == 1
        assert config.timeout_seconds == 60
        assert config.check_dependencies is False
        assert config.show_progress is False

    def test_for_mode_final(self) -> None:
        """Test creating final mode configuration."""
        config = CompilationConfig.for_mode(CompilationMode.FINAL)

        assert config.mode == CompilationMode.FINAL
        assert config.max_passes == 5
        assert config.timeout_seconds == 600
        assert config.check_dependencies is True
        assert config.keep_intermediate_files is True

    def test_for_mode_with_kwargs(self) -> None:
        """Test creating mode configuration with additional options."""
        config = CompilationConfig.for_mode(
            CompilationMode.DRAFT,
            primary_engine=LaTeXEngine.XELATEX,
            verbose_logging=True,
        )

        assert config.mode == CompilationMode.DRAFT
        assert config.primary_engine == LaTeXEngine.XELATEX
        assert config.verbose_logging is True
        # Draft mode overrides
        assert config.max_passes == 1
        assert config.show_progress is False

    def test_validate_success(self) -> None:
        """Test successful configuration validation."""
        config: Any = CompilationConfig()
        errors = config.validate_config()
        assert len(errors) == 0

    def test_validate_errors(self) -> None:
        """Test configuration validation errors."""
        # Use model_construct to bypass Pydantic validation and create invalid object
        config: Any = CompilationConfig.model_construct(
            max_passes=0,
            timeout_seconds=5,
            output_dir="not_a_path",  # Should be Path object
        )

        errors = config.validate_config()
        assert len(errors) == 3
        assert any("max_passes must be at least 1" in error for error in errors)
        assert any("timeout_seconds should be at least 10" in error for error in errors)
        assert any("output_dir must be a Path object" in error for error in errors)

    def test_validate_max_passes_too_high(self) -> None:
        """Test validation of excessive max_passes."""
        # Use model_construct to bypass Pydantic validation
        config: Any = CompilationConfig.model_construct(max_passes=15)
        errors = config.validate_config()
        assert len(errors) == 1
        assert "max_passes should not exceed 10" in errors[0]

    def test_validate_valid_output_dir(self) -> None:
        """Test validation with valid output directory."""
        config: Any = CompilationConfig(output_dir=Path("/tmp"))
        errors = config.validate_config()
        assert len(errors) == 0


@pytest.mark.rendering
class TestCompilationResult:
    """Tests for compilation result."""

    def test_successful_result(self) -> None:
        """Test successful compilation result."""
        result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=2,
            total_time=45.5,
            output_file=Path("test.pdf"),
        )

        assert result.success is True
        assert result.engine_used == LaTeXEngine.LUALATEX
        assert result.passes_completed == 2
        assert result.total_time == 45.5
        assert result.output_file == Path("test.pdf")
        assert result.error_message is None

    def test_failed_result(self) -> None:
        """Test failed compilation result."""
        result: Any = CompilationResult(
            success=False,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=15.2,
            error_message="Package not found",
        )

        assert result.success is False
        assert result.error_message == "Package not found"

    def test_str_representation_success(self) -> None:
        """Test string representation of successful result."""
        result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=3,
            total_time=67.8,
        )

        str_repr: Any = str(result)
        assert "Compilation successful" in str_repr
        assert "lualatex" in str_repr
        assert "3 passes" in str_repr
        assert "67.8s" in str_repr

    def test_str_representation_failure(self) -> None:
        """Test string representation of failed result."""
        result: Any = CompilationResult(
            success=False,
            engine_used=LaTeXEngine.XELATEX,
            passes_completed=0,
            total_time=5.0,
            error_message="Syntax error",
        )

        str_repr: Any = str(result)
        assert "Compilation failed" in str_repr
        assert "xelatex" in str_repr
        assert "Syntax error" in str_repr

    def test_str_representation_no_error_message(self) -> None:
        """Test string representation with no error message."""
        result: Any = CompilationResult(
            success=False,
            engine_used=LaTeXEngine.PDFLATEX,
            passes_completed=1,
            total_time=10.0,
        )

        str_repr: Any = str(result)
        assert "Unknown error" in str_repr

    def test_warnings_list(self) -> None:
        """Test warnings list functionality."""
        result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=30.0,
            warnings=["Warning 1", "Warning 2"],
        )

        assert len(result.warnings) == 2
        assert "Warning 1" in result.warnings
        assert "Warning 2" in result.warnings

    def test_default_warnings_list(self) -> None:
        """Test default empty warnings list."""
        result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=30.0,
        )

        assert len(result.warnings) == 0
        assert isinstance(result.warnings, list)
