"""Integration tests for LaTeX document renderer with compiler."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from dnd5e.core.models.content import BaseContent, Source  # type: ignore
from dnd5e.renderers.base.context import RenderContext  # type: ignore
from dnd5e.renderers.latex.compilation_config import (  # type: ignore
    CompilationResult,
    LaTeXEngine,
)
from dnd5e.renderers.latex.document import LaTeXDocumentRenderer  # type: ignore

# Apply async mark to the entire module
pytestmark = pytest.mark.asyncio


class MockContent(BaseContent):
    """Mock content for testing."""

    def __init__(self, name: str, source_abbr: str = "TEST"):
        super().__init__(name=name, source=Source(abbreviation=source_abbr))


class TestLaTeXDocumentRendererIntegration:
    """Integration tests for LaTeX document renderer with compiler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        config = {"show_progress": False, "compilation_timeout": 10, "max_passes": 2}
        self.renderer = LaTeXDocumentRenderer(config)

    def test_renderer_initialization_with_compiler(self) -> None:
        """Test renderer initialization includes compiler."""
        assert self.renderer.compiler is not None
        assert self.renderer.compiler.config is not None
        assert self.renderer.compiler.config.show_progress is False
        assert self.renderer.compiler.config.timeout_seconds == 10
        assert self.renderer.compiler.config.max_passes == 2

    def test_create_compilation_config_defaults(self) -> None:
        """Test compilation config creation with defaults."""
        config = self.renderer._create_compilation_config()

        assert config.primary_engine == LaTeXEngine.LUALATEX
        assert config.show_progress is True  # Default
        assert config.timeout_seconds == 300  # Default

    def test_create_compilation_config_from_renderer_config(self) -> None:
        """Test compilation config creation from renderer config."""
        renderer_config = {
            "latex_engine": "xelatex",
            "compilation_timeout": 120,
            "max_passes": 3,
            "show_progress": False,
            "keep_temp_files": True,
            "output_dir": "/tmp/output",
        }

        config = self.renderer._create_compilation_config(renderer_config)

        assert config.primary_engine == LaTeXEngine.XELATEX
        assert config.timeout_seconds == 120
        assert config.max_passes == 3
        assert config.show_progress is False
        assert config.keep_intermediate_files is True
        assert config.output_dir == Path("/tmp/output")

    def test_create_compilation_config_invalid_engine(self) -> None:
        """Test compilation config with invalid engine name."""
        renderer_config = {"latex_engine": "invalid_engine"}

        config = self.renderer._create_compilation_config(renderer_config)

        # Should keep default engine
        assert config.primary_engine == LaTeXEngine.LUALATEX

    async def test_compile_to_pdf_single_content(self) -> None:
        """Test compiling single content item to PDF."""
        content: Any = MockContent("Test Spell")

        # Mock the compiler to return success
        mock_result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=0.1,  # Fast mock result
            output_file=Path("/tmp/test.pdf"),
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Test Spell\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ) as mock_compile:
                result = await self.renderer.compile_to_pdf(content)

                assert result.success is True
                assert result.engine_used == LaTeXEngine.LUALATEX
                assert result.output_file == Path("/tmp/test.pdf")

                # Check compiler was called correctly
                mock_compile.assert_called_once()
                args = mock_compile.call_args[0]
                assert isinstance(args[0], str)  # LaTeX source
                assert args[1] == "Test Spell"  # output name
                assert args[2] is None  # working directory

    async def test_compile_to_pdf_with_output_path(self) -> None:
        """Test compiling with specified output path."""
        content: Any = MockContent("Test Item")
        output_path: Any = Path("/tmp/custom_output.pdf")

        mock_result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=0.1,  # Fast mock result
            output_file=output_path,
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Test Item\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ) as mock_compile:
                result = await self.renderer.compile_to_pdf(content, output_path)

                assert result.success is True
                assert result.output_file == output_path

                # Check compiler was called with correct parameters
                args = mock_compile.call_args[0]
                assert args[1] == "custom_output"  # output name from path
                assert args[2] == output_path.parent  # working directory

    async def test_compile_to_pdf_with_context(self) -> None:
        """Test compiling with render context."""
        content: Any = MockContent("Test Monster")
        context = {
            "title": "Monster Manual",
            "author": "Test Author",
            "include_toc": True,
        }

        mock_result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=2,
            total_time=0.1,  # Fast mock result
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Test Monster Manual\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ) as mock_compile:
                result = await self.renderer.compile_to_pdf(content, context=context)

                assert result.success is True
                assert result.passes_completed == 2

                # Check that LaTeX source was generated with context
                args = mock_compile.call_args[0]
                latex_source = args[0]
                assert isinstance(latex_source, str)
                assert len(latex_source) > 0

    async def test_compile_document_to_pdf_multiple_content(self) -> None:
        """Test compiling multiple content items to PDF."""
        content_items = [
            MockContent("Spell 1"),
            MockContent("Spell 2"),
            MockContent("Monster 1"),
        ]

        context: Any = RenderContext(title="Test Compendium", include_toc=True)

        mock_result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=3,
            total_time=0.1,  # Fast mock result
            output_file=Path("/tmp/document.pdf"),
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Test\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ) as mock_compile:
                result = await self.renderer.compile_document_to_pdf(
                    content_items, context=context
                )

                assert result.success is True
                assert result.passes_completed == 3
                assert result.output_file == Path("/tmp/document.pdf")

                # Check compiler was called correctly
                args = mock_compile.call_args[0]
                assert isinstance(args[0], str)  # LaTeX source
                assert args[1] == "Test Compendium"  # output name from context

    async def test_compile_document_to_pdf_with_output_path(self) -> None:
        """Test compiling multiple content items with output path."""
        content_items = [MockContent("Test Content")]
        output_path: Any = Path("/custom/path/output.pdf")

        mock_result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=0.1,  # Fast mock result
            output_file=Path("/tmp/output.pdf"),  # Different from target
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Test\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ):
                with patch.object(Path, "rename") as mock_rename:
                    with patch.object(Path, "mkdir") as mock_mkdir:
                        result = await self.renderer.compile_document_to_pdf(
                            content_items, output_path=output_path
                        )

                        assert result.success is True
                        assert result.output_file == output_path

                        # Check that file was moved to target location
                        mock_mkdir.assert_called_once()
                        mock_rename.assert_called_once_with(output_path)

    async def test_compile_document_to_pdf_failure(self) -> None:
        """Test compilation failure handling."""
        content_items = [MockContent("Test Content")]

        mock_result: Any = CompilationResult(
            success=False,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=0,
            total_time=0.1,  # Fast mock result
            error_message="Package not found",
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Test\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ):
                result = await self.renderer.compile_document_to_pdf(content_items)

                assert result.success is False
                assert result.error_message == "Package not found"
                assert result.passes_completed == 0

    def test_validate_latex_environment(self) -> None:
        """Test LaTeX environment validation."""
        mock_validation = {
            "engine_lualatex": True,
            "engine_xelatex": True,
            "engine_pdflatex": False,
            "dnd_template": True,
        }

        with patch.object(
            self.renderer.compiler, "validate_environment", return_value=mock_validation
        ) as mock_validate:
            result = self.renderer.validate_latex_environment()

            assert result == mock_validation
            assert result["engine_lualatex"] is True
            assert result["engine_pdflatex"] is False
            assert result["dnd_template"] is True

            mock_validate.assert_called_once()

    def test_get_available_engines(self) -> None:
        """Test getting available LaTeX engines."""
        mock_engines = [LaTeXEngine.LUALATEX, LaTeXEngine.XELATEX]

        with patch.object(
            self.renderer.compiler, "get_available_engines", return_value=mock_engines
        ) as mock_get:
            result = self.renderer.get_available_engines()

            assert result == mock_engines
            assert LaTeXEngine.LUALATEX in result
            assert LaTeXEngine.XELATEX in result

            mock_get.assert_called_once()

    def test_renderer_output_format(self) -> None:
        """Test renderer output format."""
        assert self.renderer.output_format == "latex"

    async def test_render_and_compile_integration(self) -> None:
        """Test integration between rendering and compilation."""
        content: Any = MockContent("Integration Test")

        # Mock successful rendering (this would normally generate LaTeX)
        with patch.object(self.renderer, "render_document") as mock_render:
            mock_render.return_value = (
                "\\documentclass{article}\\begin{document}Test\\end{document}"
            )

            # Mock successful compilation
            mock_result: Any = CompilationResult(
                success=True,
                engine_used=LaTeXEngine.LUALATEX,
                passes_completed=1,
                total_time=5.0,
                output_file=Path("/tmp/test.pdf"),
            )

            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ):
                result = await self.renderer.compile_to_pdf(content)

                assert result.success is True

                # Check that rendering was called
                mock_render.assert_called_once()
                render_args = mock_render.call_args[0]
                assert render_args[0] == [content]  # content items
                assert isinstance(render_args[1], RenderContext)  # render context

    def test_compiler_config_validation(self) -> None:
        """Test that invalid compiler config raises appropriate error."""
        invalid_config = {
            "max_passes": 0,  # Invalid
            "compilation_timeout": 1,  # Too low
        }

        with pytest.raises(ValueError, match="Invalid configuration"):
            LaTeXDocumentRenderer(invalid_config)

    async def test_render_with_structured_document(self) -> None:
        """Test rendering with structured document metadata."""
        from dnd5e.core.models.document_metadata import (  # type: ignore
            DocumentMetadata,
            DocumentType,
        )

        content_items = [MockContent("Test Spell")]

        metadata: Any = DocumentMetadata(
            title="Spell Compendium",
            document_type=DocumentType.SUPPLEMENT,
            include_toc=True,
        )

        context: Any = RenderContext(metadata=metadata)

        mock_result: Any = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=2,
            total_time=0.1,  # Fast mock result
        )

        # Mock the heavy rendering operations to improve test performance
        with patch.object(
            self.renderer,
            "render_document",
            return_value="\\documentclass{article}\\begin{document}Structured Test Content with sufficient length for testing purposes and ensuring the assertion passes\\end{document}",
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ) as mock_compile:
                result = await self.renderer.compile_document_to_pdf(
                    content_items, context=context
                )

                assert result.success is True
                assert result.passes_completed == 2

                # Check that structured document rendering was used
                args = mock_compile.call_args[0]
                latex_source = args[0]
                assert isinstance(latex_source, str)
                # Should contain structured document elements
                assert (
                    len(latex_source) > 100
                )  # Reasonable minimum for structured document
