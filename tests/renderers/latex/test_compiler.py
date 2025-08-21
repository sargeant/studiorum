"""Tests for LaTeX compiler."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from studiorum.latex_engine.config.compilation import (  # type: ignore
    CompilationConfig,
    CompilationMode,
    CompilationResult,
    LaTeXEngine,
)
from studiorum.latex_engine.core.compiler import LaTeXCompiler  # type: ignore
from tests.test_helpers import reset_test_environment

# Ensure async tests work properly
pytestmark = pytest.mark.asyncio


@pytest.mark.rendering
class TestLaTeXCompiler:
    """Tests for LaTeX compiler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        # Create config that won't actually try to compile
        self.config = CompilationConfig(
            show_progress=False, check_dependencies=False, timeout_seconds=10
        )
        self.compiler = LaTeXCompiler(self.config)

    def test_compiler_initialization(self) -> None:
        """Test compiler initialization."""
        assert self.compiler.config == self.config
        assert self.compiler.error_parser is not None
        assert self.compiler.progress_tracker is not None

    def test_compiler_initialization_with_default_config(self) -> None:
        """Test compiler initialization with default config."""
        compiler: Any = LaTeXCompiler()
        assert compiler.config is not None
        assert compiler.config.primary_engine == LaTeXEngine.LUALATEX

    def test_compiler_initialization_validation_error(self) -> None:
        """Test compiler initialization with invalid config."""
        # Use model_construct to bypass Pydantic validation
        invalid_config: Any = CompilationConfig.model_construct(max_passes=0)

        with pytest.raises(ValueError, match="Invalid configuration"):
            LaTeXCompiler(invalid_config)

    @patch("subprocess.run")
    @patch("studiorum.latex_engine.core.compiler.get_latex_executable")
    def test_check_engine_availability_success(
        self, mock_get_executable: Any, mock_run: Any
    ) -> None:
        """Test successful engine availability check."""
        mock_get_executable.return_value = "lualatex"
        mock_run.return_value = Mock(returncode=0)

        result = self.compiler._check_engine_availability(LaTeXEngine.LUALATEX)
        assert result is True

        mock_get_executable.assert_called_once_with("lualatex")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "lualatex"
        assert "--version" in args

    @patch("subprocess.run")
    def test_check_engine_availability_failure(self, mock_run: Any) -> None:
        """Test failed engine availability check."""
        mock_run.return_value = Mock(returncode=1)

        result = self.compiler._check_engine_availability(LaTeXEngine.LUALATEX)
        assert result is False

    @patch("subprocess.run")
    def test_check_engine_availability_timeout(self, mock_run: Any) -> None:
        """Test engine availability check with timeout."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("lualatex", 10)

        result = self.compiler._check_engine_availability(LaTeXEngine.LUALATEX)
        assert result is False

    @patch("subprocess.run")
    def test_check_engine_availability_file_not_found(self, mock_run: Any) -> None:
        """Test engine availability check with file not found."""
        mock_run.side_effect = FileNotFoundError()

        result = self.compiler._check_engine_availability(LaTeXEngine.LUALATEX)
        assert result is False

    async def test_check_dependencies_success(self) -> None:
        """Test successful dependency check."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as f:
            f.write(
                "\\documentclass{dndbook}\n\\usepackage{dnd}\n\\usepackage{fontspec}\n"
            )
            tex_file: Any = Path(f.name)

        try:
            # Override config to check dependencies
            self.compiler.config.check_dependencies = True
            self.compiler.config.required_packages = ["dndbook", "dnd", "fontspec"]

            missing = await self.compiler._check_dependencies(tex_file)
            assert len(missing) == 0
        finally:
            tex_file.unlink()

    async def test_check_dependencies_missing_packages(self) -> None:
        """Test dependency check with missing packages."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as f:
            f.write("\\documentclass{article}\n")
            tex_file: Any = Path(f.name)

        try:
            # Override config to check dependencies
            self.compiler.config.check_dependencies = True
            self.compiler.config.required_packages = ["dndbook", "dnd"]

            missing = await self.compiler._check_dependencies(tex_file)
            assert len(missing) == 2
            assert any("dndbook" in dep for dep in missing)
            assert any("dnd" in dep for dep in missing)
        finally:
            tex_file.unlink()

    async def test_check_dependencies_file_error(self) -> None:
        """Test dependency check with file read error."""
        nonexistent_file: Any = Path("/nonexistent/file.tex")

        missing = await self.compiler._check_dependencies(nonexistent_file)
        assert len(missing) == 1
        assert "Error reading LaTeX file" in missing[0]

    def test_needs_additional_pass_rerun_warning(self) -> None:
        """Test detection of need for additional pass from rerun warning."""
        stdout = "LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right."

        result = self.compiler._needs_additional_pass(stdout, Path("/tmp"))
        assert result is True

    def test_needs_additional_pass_missing_toc(self) -> None:
        """Test detection of need for additional pass from missing TOC."""
        stdout = "No file document.toc."

        result = self.compiler._needs_additional_pass(stdout, Path("/tmp"))
        assert result is True

    def test_needs_additional_pass_undefined_label(self) -> None:
        """Test detection of need for additional pass from undefined label."""
        stdout = "LaTeX Warning: Label `sec:intro' undefined on input line 10."

        result = self.compiler._needs_additional_pass(stdout, Path("/tmp"))
        assert result is True

    def test_needs_additional_pass_false(self) -> None:
        """Test detection when no additional pass is needed."""
        stdout = "Output written on document.pdf (1 page, 12345 bytes)."

        result = self.compiler._needs_additional_pass(stdout, Path("/tmp"))
        assert result is False

    def test_get_pass_description(self) -> None:
        """Test pass description generation."""
        assert self.compiler._get_pass_description(1, 4) == "Initial compilation"
        assert (
            self.compiler._get_pass_description(2, 4)
            == "Cross-references and citations"
        )
        assert self.compiler._get_pass_description(3, 4) == "Table of contents"
        assert self.compiler._get_pass_description(4, 4) == "Index and final formatting"
        assert self.compiler._get_pass_description(5, 5) == "Additional pass 5"

    @patch("subprocess.run")
    @patch("studiorum.latex_engine.core.compiler.get_latex_executable")
    def test_get_available_engines(
        self, mock_get_executable: Any, mock_run: Any
    ) -> None:
        """Test getting available engines."""

        # Mock get_latex_executable to return the command names
        def mock_get_executable_fn(engine_name: str) -> str:
            return engine_name

        mock_get_executable.side_effect = mock_get_executable_fn

        # Mock successful checks for LuaLaTeX and XeLaTeX, failed for PDFLaTeX
        def mock_subprocess_run(cmd: Any, **kwargs: Any) -> Any:
            if cmd[0] == "lualatex":
                return Mock(returncode=0)
            elif cmd[0] == "xelatex":
                return Mock(returncode=0)
            elif cmd[0] == "pdflatex":
                return Mock(returncode=1)
            else:
                return Mock(returncode=1)

        mock_run.side_effect = mock_subprocess_run

        available = self.compiler.get_available_engines()
        assert LaTeXEngine.LUALATEX in available
        assert LaTeXEngine.XELATEX in available
        assert LaTeXEngine.PDFLATEX not in available

    @patch("subprocess.run")
    @patch("studiorum.latex_engine.core.compiler.get_latex_executable")
    @patch("studiorum.latex_engine.core.compiler.get_latex_utility")
    def test_validate_environment(
        self, mock_get_utility: Any, mock_get_executable: Any, mock_run: Any
    ) -> None:
        """Test environment validation."""

        # Mock executable resolution
        def mock_get_executable_fn(engine_name: str) -> str:
            return engine_name

        def mock_get_utility_fn(utility_name: str) -> str:
            return utility_name

        mock_get_executable.side_effect = mock_get_executable_fn
        mock_get_utility.side_effect = mock_get_utility_fn

        # Mock LuaLaTeX available, others not
        def mock_subprocess_run(cmd: Any, **kwargs: Any) -> Any:
            if cmd[0] == "lualatex":
                return Mock(returncode=0)
            elif cmd[0] == "kpsewhich":
                return Mock(returncode=0)  # DND template available
            else:
                return Mock(returncode=1)

        mock_run.side_effect = mock_subprocess_run

        results = self.compiler.validate_environment()
        assert results["engine_lualatex"] is True
        assert results["engine_xelatex"] is False
        assert results["engine_pdflatex"] is False
        assert results["dnd_template"] is True

    async def test_compile_document_simple(self) -> None:
        """Test simple document compilation (mocked)."""
        latex_content = """\\documentclass{article}
\\begin{document}
Hello World
\\end{document}"""

        with patch.object(self.compiler, "_compile_in_directory") as mock_compile:
            mock_result: Any = CompilationResult(
                success=True,
                engine_used=LaTeXEngine.LUALATEX,
                passes_completed=1,
                total_time=5.0,
            )
            mock_compile.return_value = mock_result

            result = await self.compiler.compile_document(latex_content, "test")
            assert result.success is True
            assert result.engine_used == LaTeXEngine.LUALATEX

            # Check that compile was called with correct arguments
            mock_compile.assert_called_once()
            args = mock_compile.call_args[0]
            assert args[0] == latex_content
            assert args[1] == "test"
            assert isinstance(args[2], Path)  # working directory

    async def test_compile_document_with_working_dir(self) -> None:
        """Test document compilation with specified working directory."""
        latex_content = "\\documentclass{article}\\begin{document}Test\\end{document}"
        working_dir: Any = Path("/tmp/test")

        with patch.object(self.compiler, "_compile_in_directory") as mock_compile:
            mock_result: Any = CompilationResult(
                success=True,
                engine_used=LaTeXEngine.LUALATEX,
                passes_completed=1,
                total_time=5.0,
            )
            mock_compile.return_value = mock_result

            await self.compiler.compile_document(latex_content, "test", working_dir)

            # Check that specified working directory was used
            args = mock_compile.call_args[0]
            assert args[2] == working_dir

    @patch("subprocess.run")
    def test_run_compilation_pass_success(self, mock_run: Any) -> None:
        """Test successful compilation pass."""
        mock_run.return_value = Mock(
            returncode=0, stdout="Output written on document.pdf", stderr=""
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file: Any = Path(temp_dir) / "test.tex"
            tex_file.write_text(
                "\\documentclass{article}\\begin{document}Test\\end{document}"
            )

            comp_pass = self.compiler._run_compilation_pass(
                LaTeXEngine.LUALATEX, tex_file, Path(temp_dir), 1
            )

            assert comp_pass.success is True
            assert comp_pass.return_code == 0
            assert comp_pass.pass_number == 1
            assert comp_pass.engine == LaTeXEngine.LUALATEX
            assert comp_pass.duration is not None

    @patch("subprocess.run")
    def test_run_compilation_pass_failure(self, mock_run: Any) -> None:
        """Test failed compilation pass."""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="! LaTeX Error: Something went wrong"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file: Any = Path(temp_dir) / "test.tex"
            tex_file.write_text(
                "\\documentclass{article}\\begin{document}Test\\end{document}"
            )

            comp_pass = self.compiler._run_compilation_pass(
                LaTeXEngine.LUALATEX, tex_file, Path(temp_dir), 1
            )

            assert comp_pass.success is False
            assert comp_pass.return_code == 1
            assert "LaTeX Error" in comp_pass.stderr

    @patch("subprocess.run")
    def test_run_compilation_pass_timeout(self, mock_run: Any) -> None:
        """Test compilation pass timeout."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("lualatex", 10)

        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file: Any = Path(temp_dir) / "test.tex"
            tex_file.write_text(
                "\\documentclass{article}\\begin{document}Test\\end{document}"
            )

            comp_pass = self.compiler._run_compilation_pass(
                LaTeXEngine.LUALATEX, tex_file, Path(temp_dir), 1
            )

            assert comp_pass.success is False
            assert comp_pass.return_code == -1
            assert "timed out" in comp_pass.stderr

    def test_analyze_compilation_errors(self) -> None:
        """Test compilation error analysis."""
        from studiorum.latex_engine.config.compilation import (
            CompilationPass,  # type: ignore
        )

        comp_pass: Any = CompilationPass(
            pass_number=1,
            engine=LaTeXEngine.LUALATEX,
            command=["lualatex", "test.tex"],
            start_time=0.0,
            end_time=1.0,
            return_code=1,
            stdout="",
            stderr="! LaTeX Error: File not found",
        )

        errors = self.compiler._analyze_compilation_errors(comp_pass)
        assert len(errors) > 0

        # Should find the error in stderr
        error_messages = [error.message for error in errors]
        assert any("File not found" in msg for msg in error_messages)

    def test_analyze_compilation_errors_timeout(self) -> None:
        """Test compilation error analysis for timeout."""
        from studiorum.latex_engine.config.compilation import (
            CompilationPass,  # type: ignore
        )

        comp_pass: Any = CompilationPass(
            pass_number=1,
            engine=LaTeXEngine.LUALATEX,
            command=["lualatex", "test.tex"],
            start_time=0.0,
            end_time=1.0,
            return_code=-1,
            stdout="",
            stderr="timeout occurred",
        )

        errors = self.compiler._analyze_compilation_errors(comp_pass)
        assert len(errors) > 0

        # Should detect timeout
        error_categories = [error.category for error in errors]
        from studiorum.latex_engine.utils.error_parser import (
            ErrorCategory,  # type: ignore
        )

        assert ErrorCategory.TIMEOUT_ERROR in error_categories


@pytest.mark.rendering
class TestLaTeXCompilerIntegration:
    """Integration tests for LaTeX compiler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.config = CompilationConfig(
            show_progress=False,
            check_dependencies=False,
            timeout_seconds=10,  # Minimum required by validation
            max_passes=1,  # Single pass for faster testing
        )
        self.compiler = LaTeXCompiler(self.config)

    async def test_compile_simple_document_no_latex(self) -> None:
        """Test compiling when no LaTeX engines are available."""
        # Mock no engines available
        with patch.object(
            self.compiler, "_check_engine_availability", return_value=False
        ):
            latex_content = (
                "\\documentclass{article}\\begin{document}Hello\\end{document}"
            )

            result = await self.compiler.compile_document(latex_content, "test")
            assert result.success is False
            assert result.error_message is not None
            assert "No compatible LaTeX engines available" in result.error_message

    async def test_compile_with_dependency_error(self) -> None:
        """Test compilation with dependency check failure."""
        # Enable dependency checking
        self.compiler.config.check_dependencies = True
        self.compiler.config.required_packages = ["nonexistent-package"]

        # Mock engine availability
        with patch.object(
            self.compiler, "_check_engine_availability", return_value=True
        ):
            latex_content = (
                "\\documentclass{article}\\begin{document}Hello\\end{document}"
            )

            result = await self.compiler.compile_document(latex_content, "test")
            assert result.success is False
            assert result.error_message is not None
            assert "Missing dependencies" in result.error_message

    @patch("subprocess.run")
    async def test_compile_with_engine_fallback(self, mock_run: Any) -> None:
        """Test compilation with engine fallback."""

        # Mock first engine (LuaLaTeX) not available, second (XeLaTeX) available
        def mock_availability_check(engine: Any) -> bool:
            if engine == LaTeXEngine.LUALATEX:
                return False
            elif engine == LaTeXEngine.XELATEX:
                return True
            else:
                return False

        # Mock successful XeLaTeX compilation
        mock_run.return_value = Mock(
            returncode=0, stdout="Output written on document.pdf", stderr=""
        )

        with patch.object(
            self.compiler,
            "_check_engine_availability",
            side_effect=mock_availability_check,
        ):
            latex_content = (
                "\\documentclass{article}\\begin{document}Hello\\end{document}"
            )

            result = await self.compiler.compile_document(latex_content, "test")
            assert result.success is True
            assert result.engine_used == LaTeXEngine.XELATEX

    def test_compiler_with_different_modes(self) -> None:
        """Test compiler behavior with different compilation modes."""
        # Test draft mode
        draft_config = CompilationConfig.for_mode(CompilationMode.DRAFT)
        draft_compiler: Any = LaTeXCompiler(draft_config)

        assert draft_compiler.config.max_passes == 1
        assert draft_compiler.config.show_progress is False
        assert draft_compiler.config.check_dependencies is False

        # Test final mode
        final_config = CompilationConfig.for_mode(CompilationMode.FINAL)
        final_compiler: Any = LaTeXCompiler(final_config)

        assert final_compiler.config.max_passes == 5
        assert final_compiler.config.check_dependencies is True
        assert final_compiler.config.keep_intermediate_files is True
