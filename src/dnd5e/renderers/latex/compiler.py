"""LaTeX compilation engine with multi-pass support and error handling."""

import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .compilation_config import (
    CompilationConfig,
    CompilationPass,
    CompilationResult,
    LaTeXEngine,
)
from .error_parser import LaTeXErrorParser
from .progress_tracker import ProgressTracker


class LaTeXCompiler:
    """Robust LaTeX compiler with multi-pass support and error handling."""

    def __init__(self, config: CompilationConfig | None = None):
        """Initialize LaTeX compiler.

        Args:
            config: Compilation configuration (default if None)
        """
        self.config = config or CompilationConfig()
        self.error_parser = LaTeXErrorParser()
        self.progress_tracker = ProgressTracker(
            style=self.config.progress_style if self.config.show_progress else "none"
        )

        # Validation
        config_errors = self.config.validate_config()
        if config_errors:
            raise ValueError(f"Invalid configuration: {'; '.join(config_errors)}")

    async def compile_document(
        self,
        latex_content: str,
        output_name: str = "document",
        working_dir: Path | None = None,
    ) -> CompilationResult:
        """Compile a LaTeX document to PDF.

        Args:
            latex_content: LaTeX source code
            output_name: Base name for output files (without extension)
            working_dir: Directory to work in (temporary if None)

        Returns:
            CompilationResult with success status and details
        """
        # Determine working directory
        if working_dir:
            work_dir = Path(working_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
            cleanup_dir = False
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="latex_compile_"))
            cleanup_dir = True

        try:
            return await self._compile_in_directory(
                latex_content, output_name, work_dir
            )
        finally:
            if cleanup_dir and not self.config.keep_intermediate_files:
                shutil.rmtree(work_dir, ignore_errors=True)

    async def _compile_in_directory(
        self, latex_content: str, output_name: str, work_dir: Path
    ) -> CompilationResult:
        """Compile LaTeX document in specified directory.

        Args:
            latex_content: LaTeX source code
            output_name: Base name for output files
            work_dir: Working directory

        Returns:
            CompilationResult
        """
        start_time = time.time()
        tex_file = work_dir / f"{output_name}.tex"

        # Write LaTeX source to file
        tex_file.write_text(latex_content, encoding="utf-8")

        # Try engines in order of preference
        engines_to_try = [self.config.primary_engine] + self.config.fallback_engines
        last_result = None

        for engine in engines_to_try:
            if not self._check_engine_availability(engine):
                continue

            try:
                result = await self._compile_with_engine(engine, tex_file, work_dir)
                if result.success:
                    result.total_time = time.time() - start_time
                    return result
                last_result = result
            except Exception as e:
                last_result = CompilationResult(
                    success=False,
                    engine_used=engine,
                    passes_completed=0,
                    total_time=time.time() - start_time,
                    error_message=str(e),
                )

        # If we get here, all engines failed
        if last_result:
            last_result.total_time = time.time() - start_time
            return last_result
        else:
            return CompilationResult(
                success=False,
                engine_used=engines_to_try[0],
                passes_completed=0,
                total_time=time.time() - start_time,
                error_message="No LaTeX engines available",
            )

    async def _compile_with_engine(
        self, engine: LaTeXEngine, tex_file: Path, work_dir: Path
    ) -> CompilationResult:
        """Compile with a specific LaTeX engine.

        Args:
            engine: LaTeX engine to use
            tex_file: Path to .tex file
            work_dir: Working directory

        Returns:
            CompilationResult
        """
        output_name = tex_file.stem
        pdf_file = work_dir / f"{output_name}.pdf"
        log_file = work_dir / f"{output_name}.log"

        # Check dependencies before compilation
        if self.config.check_dependencies:
            dep_errors = await self._check_dependencies(tex_file)
            if dep_errors:
                return CompilationResult(
                    success=False,
                    engine_used=engine,
                    passes_completed=0,
                    total_time=0.0,
                    error_message=f"Missing dependencies: {'; '.join(dep_errors)}",
                )

        # Determine number of passes needed
        max_passes = (
            1 if not self.config.should_run_multipass() else self.config.max_passes
        )

        passes_completed = 0
        compilation_passes: list[CompilationPass] = []

        with self.progress_tracker.compilation(engine.value, max_passes) as tracker:
            try:
                for pass_num in range(1, max_passes + 1):
                    pass_desc = self._get_pass_description(pass_num, max_passes)

                    with tracker.compilation_pass(pass_num, pass_desc):
                        comp_pass = self._run_compilation_pass(
                            engine, tex_file, work_dir, pass_num
                        )
                        compilation_passes.append(comp_pass)
                        passes_completed += 1

                        if not comp_pass.success:
                            # Parse errors from this pass
                            errors = self._analyze_compilation_errors(comp_pass)
                            error_summary = self.error_parser.get_error_summary(errors)

                            return CompilationResult(
                                success=False,
                                engine_used=engine,
                                passes_completed=passes_completed,
                                total_time=0.0,
                                output_file=pdf_file if pdf_file.exists() else None,
                                log_file=log_file if log_file.exists() else None,
                                error_message=error_summary,
                            )

                        # Check if additional passes are needed
                        if pass_num < max_passes and not comp_pass.needs_rerun:
                            break

                # Compilation successful
                return CompilationResult(
                    success=True,
                    engine_used=engine,
                    passes_completed=passes_completed,
                    total_time=0.0,
                    output_file=pdf_file if pdf_file.exists() else None,
                    log_file=log_file if log_file.exists() else None,
                )

            except Exception as e:
                tracker.show_error(str(e))
                return CompilationResult(
                    success=False,
                    engine_used=engine,
                    passes_completed=passes_completed,
                    total_time=0.0,
                    error_message=f"Compilation exception: {str(e)}",
                )

    def _run_compilation_pass(
        self, engine: LaTeXEngine, tex_file: Path, work_dir: Path, pass_number: int
    ) -> CompilationPass:
        """Run a single compilation pass.

        Args:
            engine: LaTeX engine to use
            tex_file: Path to .tex file
            work_dir: Working directory
            pass_number: Pass number (1-based)

        Returns:
            CompilationPass with results
        """
        # Build command
        cmd = self.config.get_engine_command(engine)
        cmd.append(str(tex_file.name))

        # Create compilation pass object
        comp_pass = CompilationPass(
            pass_number=pass_number, engine=engine, command=cmd, start_time=time.time()
        )

        # Update progress
        self.progress_tracker.update_progress(0.1, "Starting compilation")

        try:
            # Run compilation
            timeout = self.config.get_timeout_for_pass(pass_number)

            self.progress_tracker.update_progress(0.3, "Running LaTeX engine")

            process = subprocess.run(
                cmd, cwd=work_dir, capture_output=True, text=True, timeout=timeout
            )

            comp_pass.end_time = time.time()
            comp_pass.return_code = process.returncode
            comp_pass.stdout = process.stdout
            comp_pass.stderr = process.stderr

            self.progress_tracker.update_progress(0.8, "Analyzing output")

            # Check if additional passes needed
            if comp_pass.success:
                comp_pass.needs_rerun = self._needs_additional_pass(
                    comp_pass.stdout, work_dir
                )

            self.progress_tracker.update_progress(1.0, "Pass complete")

            return comp_pass

        except subprocess.TimeoutExpired:
            comp_pass.end_time = time.time()
            comp_pass.return_code = -1
            comp_pass.stderr = "Compilation timed out"
            return comp_pass

        except Exception as e:
            comp_pass.end_time = time.time()
            comp_pass.return_code = -1
            comp_pass.stderr = str(e)
            return comp_pass

    def _get_pass_description(self, pass_num: int, max_passes: int) -> str:
        """Get description for a compilation pass.

        Args:
            pass_num: Current pass number
            max_passes: Maximum passes

        Returns:
            Pass description
        """
        if pass_num == 1:
            return "Initial compilation"
        elif pass_num == 2:
            return "Cross-references and citations"
        elif pass_num == 3:
            return "Table of contents"
        elif pass_num == 4:
            return "Index and final formatting"
        else:
            return f"Additional pass {pass_num}"

    def _needs_additional_pass(self, stdout: str, work_dir: Path) -> bool:
        """Check if additional compilation pass is needed.

        Args:
            stdout: Compilation output
            work_dir: Working directory

        Returns:
            True if another pass is needed
        """
        # Check for common indicators that another pass is needed
        rerun_indicators = [
            r"LaTeX Warning:.*Rerun",
            r"Package rerunfilecheck Warning:.*Rerun",
            r"No file.*\.toc",
            r"No file.*\.aux",
            r"Label.*undefined",
            r"Citation.*undefined",
        ]

        for indicator in rerun_indicators:
            if re.search(indicator, stdout, re.IGNORECASE):
                return True

        # Check for missing auxiliary files
        aux_extensions = [".toc", ".lof", ".lot", ".idx", ".ind"]
        tex_files = list(work_dir.glob("*.tex"))
        if tex_files:
            base_name = tex_files[0].stem
            for ext in aux_extensions:
                aux_file = work_dir / f"{base_name}{ext}"
                if not aux_file.exists() and ext in stdout:
                    return True

        return False

    def _check_engine_availability(self, engine: LaTeXEngine) -> bool:
        """Check if a LaTeX engine is available on the system.

        Args:
            engine: LaTeX engine to check

        Returns:
            True if engine is available
        """
        try:
            result = subprocess.run(
                [engine.value, "--version"], capture_output=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    async def _check_dependencies(self, tex_file: Path) -> list[str]:
        """Check for missing LaTeX packages and dependencies.

        Args:
            tex_file: Path to LaTeX file to check

        Returns:
            List of missing dependencies
        """
        missing_deps = []

        try:
            with open(tex_file, encoding="utf-8") as f:
                content = f.read()

            # Check for required packages
            for package in self.config.required_packages:
                if (
                    package not in content
                    and f"\\usepackage{{{package}}}" not in content
                ):
                    missing_deps.append(f"Package '{package}' not found in document")

            # Could add more sophisticated dependency checking here
            # For example, checking if package files exist in LaTeX installation

        except Exception as e:
            missing_deps.append(f"Error reading LaTeX file: {e}")

        return missing_deps

    def _analyze_compilation_errors(self, comp_pass: CompilationPass) -> list:
        """Analyze compilation errors from a pass.

        Args:
            comp_pass: Compilation pass to analyze

        Returns:
            List of LaTeX errors
        """
        timeout_occurred = (
            comp_pass.return_code == -1 and "timeout" in comp_pass.stderr.lower()
        )

        return self.error_parser.analyze_compilation_failure(
            comp_pass.return_code or 0,
            comp_pass.stdout,
            comp_pass.stderr,
            timeout_occurred,
        )

    def get_available_engines(self) -> list[LaTeXEngine]:
        """Get list of available LaTeX engines on the system.

        Returns:
            List of available engines
        """
        available = []
        for engine in LaTeXEngine:
            if self._check_engine_availability(engine):
                available.append(engine)
        return available

    def validate_environment(self) -> dict[str, bool]:
        """Validate the LaTeX compilation environment.

        Returns:
            Dictionary of validation results
        """
        results = {}

        # Check engines
        for engine in LaTeXEngine:
            results[f"engine_{engine.value}"] = self._check_engine_availability(engine)

        # Check for DND template (basic check)
        try:
            # Try to find DND template files
            result = subprocess.run(
                ["kpsewhich", "dndbook.cls"], capture_output=True, timeout=10
            )
            results["dnd_template"] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            results["dnd_template"] = False

        return results
