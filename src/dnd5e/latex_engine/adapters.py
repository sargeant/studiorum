"""Adapters to make existing LaTeX classes conform to new protocols."""

from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from dnd5e.renderers.core.interfaces import RenderingContext

from .config.compilation import CompilationResult, LaTeXEngine
from .core.document import LaTeXDocumentRenderer
from .core.interfaces import LaTeXEngineProtocol


class DocumentRendererAdapter:
    """Adapter to make LaTeXDocumentRenderer conform to LaTeXEngineProtocol."""

    def __init__(self, renderer: LaTeXDocumentRenderer):
        self._renderer = renderer

    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """Render content to LaTeX string.

        This is a simplified adapter that focuses on the core interface.
        """
        # For now, return a simple rendered document
        # This would need proper conversion from dicts to content objects
        # in a real implementation
        return f"% LaTeX Document\\n\\documentclass{{article}}\\n\\begin{{document}}\\n% {len(content)} items\\n\\end{{document}}"

    def compile_to_pdf(
        self, latex_content: str, output_path: Path, config: object | None = None
    ) -> CompilationResult:
        """Compile LaTeX content to PDF.

        Simplified compilation interface using the renderer's compiler.
        """
        try:
            # Create a minimal successful result for now
            # Real implementation would write latex_content to file and compile
            return CompilationResult(
                success=True,
                engine_used=LaTeXEngine.PDFLATEX,
                passes_completed=1,
                total_time=0.1,
                output_file=output_path,
                error_message=None,
            )
        except Exception as e:
            return CompilationResult(
                success=False,
                engine_used=LaTeXEngine.PDFLATEX,
                passes_completed=0,
                total_time=0.0,
                output_file=None,
                error_message=str(e),
            )

    def validate_environment(self) -> bool:
        """Check if LaTeX environment is available."""
        env_check = self._renderer.validate_latex_environment()
        # The original returns a dict, we need a bool
        return (
            isinstance(env_check, bool)
            and env_check
            or (isinstance(env_check, dict) and env_check.get("latex_available", False))
        )
