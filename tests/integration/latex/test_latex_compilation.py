"""LaTeX compilation integration tests.

These tests perform actual LaTeX compilation and require:
- LaTeX installation (texlive)
- DND-5e-LaTeX-Template
- Actual document compilation

WARNING: These tests are slow and require LaTeX installation.
They are separate from regular unit tests which use mocking.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import pytest

from studiorum.cli.main import get_tag_resolver
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.document_metadata import DocumentMetadata, DocumentType
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.resolvers.content_resolver import ContentResolver
from studiorum.latex_engine.core.document import LaTeXDocumentRenderer
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_data_helpers import requires_latex_template


def check_latex_available() -> bool:
    """Check if LaTeX is available on the system."""
    try:
        result = subprocess.run(
            ["pdflatex", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_dnd_template_available() -> bool:
    """Check if DND-5e-LaTeX-Template is available."""
    try:
        result = subprocess.run(
            ["kpsewhich", "DND-5e.cls"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def compile_latex(tex_content: str, output_dir: Path) -> tuple[bool, str, str]:
    """Compile LaTeX content and return success status with stdout/stderr.

    Args:
        tex_content: LaTeX document content
        output_dir: Directory to compile in

    Returns:
        (success, stdout, stderr)
    """
    tex_file = output_dir / "document.tex"
    tex_file.write_text(tex_content, encoding="utf-8")

    try:
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-output-directory",
                str(output_dir),
                str(tex_file),
            ],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for compilation
            cwd=output_dir,
        )

        return result.returncode == 0, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return False, "", "LaTeX compilation timed out after 120 seconds"
    except Exception as e:
        return False, "", f"LaTeX compilation failed with exception: {e}"


@pytest.mark.needs_latex
@requires_latex_template()
class TestLaTeXCompilation:
    """Integration tests that perform actual LaTeX compilation."""

    def setup_method(self):
        """Set up test environment."""
        if not check_latex_available():
            pytest.skip("LaTeX (pdflatex) not available")

    def test_minimal_latex_document_compiles(self):
        """Test that a minimal LaTeX document compiles successfully."""
        minimal_doc = r"""
\documentclass[letterpaper,10pt,twoside,twocolumn,openany]{DND-5e}

\begin{document}

\chapter{Test Chapter}

This is a test document to verify LaTeX compilation works.

\section{Test Section}

This section contains basic text to ensure the DND template is working correctly.

\end{document}
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            success, stdout, stderr = compile_latex(minimal_doc, temp_path)

            if not success:
                pytest.fail(
                    f"LaTeX compilation failed:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
                )

            # Check that PDF was created
            pdf_file = temp_path / "document.pdf"
            assert pdf_file.exists(), "PDF file was not created"
            assert pdf_file.stat().st_size > 0, "PDF file is empty"

    def test_test_book_renders_and_compiles(self):
        """Test that test book content renders to LaTeX and compiles successfully."""
        # Load test data
        omnidexer = Omnidexer()
        omnidexer.load_all_data()

        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_book("test")

        if not result.is_success:
            pytest.skip(f"Test book not available: {result.status}")

        book = result.content

        # Create rendering context
        content_tracker = ContentTracker()
        tag_resolver = get_tag_resolver()

        document_metadata = DocumentMetadata(
            title=book.name,
            document_type=DocumentType.BOOK,
            include_toc=True,
        )

        context = RenderingContext(
            output_format="latex",
            omnidexer=omnidexer,
            content_tracker=content_tracker,
            metadata={
                "title": book.name,
                "tag_resolver": tag_resolver,
                "document_metadata": document_metadata,
                "content_tracker": content_tracker,
            },
        )

        # Render document
        renderer = LaTeXDocumentRenderer()
        latex_content = renderer.render_document(book.contents, context)

        assert latex_content, "LaTeX content should not be empty"
        assert "\\documentclass" in latex_content, (
            "LaTeX content should include document class"
        )
        assert "\\begin{document}" in latex_content, (
            "LaTeX content should include document begin"
        )
        assert "\\end{document}" in latex_content, (
            "LaTeX content should include document end"
        )

        # Try to compile the generated LaTeX
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            success, stdout, stderr = compile_latex(latex_content, temp_path)

            if not success:
                # Save the generated LaTeX for debugging
                debug_file = temp_path / "debug_output.tex"
                debug_file.write_text(latex_content, encoding="utf-8")

                pytest.fail(
                    f"Generated LaTeX failed to compile:\n"
                    f"STDOUT:\n{stdout}\n"
                    f"STDERR:\n{stderr}\n"
                    f"Generated LaTeX saved to: {debug_file}"
                )

            # Check that PDF was created
            pdf_file = temp_path / "document.pdf"
            assert pdf_file.exists(), "PDF file was not created"
            assert pdf_file.stat().st_size > 0, "PDF file is empty"

    def test_test_adventure_renders_and_compiles(self):
        """Test that test adventure content renders to LaTeX and compiles successfully."""
        # Load test data
        omnidexer = Omnidexer()
        omnidexer.load_all_data()

        resolver = ContentResolver(omnidexer)
        result = resolver.resolve_adventure("test")

        if not result.is_success:
            pytest.skip(f"Test adventure not available: {result.status}")

        adventure = result.content

        # Create rendering context
        content_tracker = ContentTracker()
        tag_resolver = get_tag_resolver()

        document_metadata = DocumentMetadata(
            title=adventure.name,
            document_type=DocumentType.ADVENTURE,
            include_toc=True,
        )

        context = RenderingContext(
            output_format="latex",
            omnidexer=omnidexer,
            content_tracker=content_tracker,
            metadata={
                "title": adventure.name,
                "tag_resolver": tag_resolver,
                "document_metadata": document_metadata,
                "content_tracker": content_tracker,
                "appendix_spells": True,
                "appendix_items": True,
                "appendix_creatures": True,
            },
        )

        # Render document
        renderer = LaTeXDocumentRenderer()
        latex_content = renderer.render_document(adventure.contents, context)

        assert latex_content, "LaTeX content should not be empty"
        assert "\\documentclass" in latex_content, (
            "LaTeX content should include document class"
        )
        assert "\\begin{document}" in latex_content, (
            "LaTeX content should include document begin"
        )
        assert "\\end{document}" in latex_content, (
            "LaTeX content should include document end"
        )

        # Try to compile the generated LaTeX
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            success, stdout, stderr = compile_latex(latex_content, temp_path)

            if not success:
                # Save the generated LaTeX for debugging
                debug_file = temp_path / "debug_output.tex"
                debug_file.write_text(latex_content, encoding="utf-8")

                pytest.fail(
                    f"Generated LaTeX failed to compile:\n"
                    f"STDOUT:\n{stdout}\n"
                    f"STDERR:\n{stderr}\n"
                    f"Generated LaTeX saved to: {debug_file}"
                )

            # Check that PDF was created
            pdf_file = temp_path / "document.pdf"
            assert pdf_file.exists(), "PDF file was not created"
            assert pdf_file.stat().st_size > 0, "PDF file is empty"


@pytest.mark.needs_latex
class TestCLILaTeXIntegration:
    """Integration tests for CLI LaTeX compilation."""

    def setup_method(self):
        """Set up test environment."""
        if not check_latex_available():
            pytest.skip("LaTeX (pdflatex) not available")

        if not check_dnd_template_available():
            pytest.skip("DND-5e-LaTeX-Template not available")

    def _get_test_env(self) -> dict[str, str]:
        """Get environment variables for test subprocess calls."""
        import os

        env = os.environ.copy()
        env["STUDIORUM_CONFIG_FILE"] = "test-config.yaml"
        return env

    def test_cli_book_to_pdf_compilation(self):
        """Test CLI book conversion with actual PDF compilation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / "test-book.tex"
            pdf_file = temp_path / "test-book.pdf"

            # Generate LaTeX using CLI
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "test",
                    "--output",
                    str(tex_file),
                ],
                capture_output=True,
                text=True,
                env=self._get_test_env(),
                timeout=60,
            )

            if result.returncode != 0:
                pytest.fail(
                    f"CLI book conversion failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )

            assert tex_file.exists(), "LaTeX file was not created by CLI"

            # Compile the generated LaTeX to PDF
            tex_content = tex_file.read_text(encoding="utf-8")
            success, stdout, stderr = compile_latex(tex_content, temp_path)

            if not success:
                pytest.fail(
                    f"CLI-generated LaTeX failed to compile:\n"
                    f"STDOUT:\n{stdout}\n"
                    f"STDERR:\n{stderr}"
                )

            # Check that PDF was created
            pdf_file = temp_path / "document.pdf"  # compile_latex creates document.pdf
            assert pdf_file.exists(), "PDF file was not created"
            assert pdf_file.stat().st_size > 0, "PDF file is empty"

    def test_cli_adventure_to_pdf_compilation(self):
        """Test CLI adventure conversion with actual PDF compilation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / "test-adventure.tex"

            # Generate LaTeX using CLI
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "adventure",
                    "test",
                    "--output",
                    str(tex_file),
                ],
                capture_output=True,
                text=True,
                env=self._get_test_env(),
                timeout=60,
            )

            if result.returncode != 0:
                pytest.fail(
                    f"CLI adventure conversion failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )

            assert tex_file.exists(), "LaTeX file was not created by CLI"

            # Compile the generated LaTeX to PDF
            tex_content = tex_file.read_text(encoding="utf-8")
            success, stdout, stderr = compile_latex(tex_content, temp_path)

            if not success:
                pytest.fail(
                    f"CLI-generated LaTeX failed to compile:\n"
                    f"STDOUT:\n{stdout}\n"
                    f"STDERR:\n{stderr}"
                )

            # Check that PDF was created
            pdf_file = temp_path / "document.pdf"  # compile_latex creates document.pdf
            assert pdf_file.exists(), "PDF file was not created"
            assert pdf_file.stat().st_size > 0, "PDF file is empty"
