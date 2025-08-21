"""Mock LaTeX engine for testing without LaTeX installation."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from studiorum.renderers.core.interfaces import RenderingContext

from ..config.compilation import CompilationResult, LaTeXEngine
from ..core.document import LaTeXDocumentRenderer
from ..core.interfaces import LaTeXEngineProtocol


class MockLaTeXEngine:
    """Mock LaTeX engine that doesn't require LaTeX installation.

    This uses the real LaTeX renderer for accurate output but skips
    PDF compilation for testing without LaTeX installation.
    """

    def __init__(self) -> None:
        """Initialize with real LaTeX renderer."""
        self.renderer = LaTeXDocumentRenderer()

    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """Render content using real LaTeX renderer.

        Args:
            content: List of content items to render
            context: Rendering context

        Returns:
            Real LaTeX document as string
        """
        # Use the real renderer for accurate LaTeX output
        # Type cast needed since mock accepts broader type than renderer
        result = self.renderer.render_document(content, context)  # type: ignore[arg-type]
        return str(result) if result else ""

    def compile_to_pdf(
        self, latex_content: str, output_path: Path, config: object | None = None
    ) -> CompilationResult:
        """Mock compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX source code
            output_path: Path where PDF should be written
            config: Optional compilation configuration

        Returns:
            CompilationResult with success status
        """
        # Create a fake PDF file for testing
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("Mock PDF content - not a real PDF")

        return CompilationResult(
            success=True,
            engine_used=LaTeXEngine.PDFLATEX,
            passes_completed=1,
            total_time=0.01,
            output_file=output_path,
            error_message=None,
        )

    def validate_environment(self) -> bool:
        """Mock environment validation.

        Returns:
            Always True for mock engine
        """
        return True
