"""Mock LaTeX engine for testing without LaTeX installation."""

from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from dnd5e.renderers.core.interfaces import RenderingContext

from ..config.compilation import CompilationResult, LaTeXEngine
from ..core.interfaces import LaTeXEngineProtocol


class MockLaTeXEngine:
    """Mock LaTeX engine that doesn't require LaTeX installation."""

    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """Render content to mock LaTeX string.

        Args:
            content: List of content items to render
            context: Rendering context

        Returns:
            Mock LaTeX document as string
        """
        # Generate simple mock LaTeX based on content
        latex_lines = [
            "% Mock LaTeX Document",
            "\\documentclass{article}",
            "\\begin{document}",
            f"% Generated for {len(content)} content items",
        ]

        # Add mock content
        for i, item in enumerate(content):
            item_name = getattr(item, "name", f"Item {i}")
            latex_lines.append(f"\\section{{{item_name}}}")
            latex_lines.append("% Mock content placeholder")

        latex_lines.extend(["\\end{document}", "% End of mock LaTeX document"])

        return "\n".join(latex_lines)

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
