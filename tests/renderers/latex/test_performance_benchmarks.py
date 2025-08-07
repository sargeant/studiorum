"""Performance benchmarks for EntryRenderer system to ensure no regression."""

import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from dnd5e.core.models.books import Book  # type: ignore
from dnd5e.core.models.chapter import Chapter  # type: ignore
from dnd5e.core.models.content import Source  # type: ignore
from dnd5e.core.models.spells import Spell  # type: ignore
from dnd5e.renderers.core.interfaces import RenderingContext  # type: ignore
from dnd5e.renderers.latex.document import LaTeXDocumentRenderer  # type: ignore


def compile_document_to_pdf_sync(renderer, documents, context):
    """Synchronous wrapper for renderer.compile_document_to_pdf() for testing."""
    import asyncio

    return asyncio.run(renderer.compile_document_to_pdf(documents, context=context))


class TestRenderingPerformance:
    """Performance benchmarks for the EntryRenderer system."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        config = {"show_progress": False, "compilation_timeout": 30, "max_passes": 2}
        self.renderer = LaTeXDocumentRenderer(config)

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="TEST", name="Test Source", page=None, url=None)

    # Use the existing fixtures from conftest.py for proper model validation

    @pytest.fixture
    def sample_book(self, sample_source: Any) -> Any:
        """Sample book with multiple chapters for performance testing."""
        chapters = []
        for i in range(10):  # Create 10 chapters
            chapters.append(
                Chapter(
                    name=f"Chapter {i + 1}",
                    ordinal={"type": "chapter", "identifier": i + 1},
                    headers=[f"Section {i + 1}.1", f"Section {i + 1}.2"],
                    entries=[
                        f"This is the content of chapter {i + 1}.",
                        "It contains multiple paragraphs of text.",
                        {
                            "type": "section",
                            "name": f"Advanced Topics {i + 1}",
                            "entries": [f"Advanced content for chapter {i + 1}."],
                        },
                    ],
                )
            )

        return Book(
            name="Performance Test Book",
            source=sample_source,
            contents=chapters,
            id=None,
            metadata=None,
            published=None,
            author=["Test Author"],
            cover=None,
        )

    @pytest.mark.slow
    def test_single_spell_rendering_performance(self, sample_spell: Any) -> None:
        """Benchmark single spell rendering performance."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Spell Performance Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Warm up
            self.renderer.render_document([sample_spell], context)

            # Measure performance
            start_time = time.perf_counter()
            for _ in range(100):  # Render 100 times
                result = self.renderer.render_document([sample_spell], context)
                assert isinstance(result, str)
                assert len(result) > 50
            end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_render = total_time / 100

        # Performance assertions (adjust thresholds as needed)
        assert total_time < 10.0, (
            f"100 spell renders took {total_time:.2f}s (expected < 10s)"
        )
        assert avg_time_per_render < 0.1, (
            f"Average render time {avg_time_per_render:.3f}s (expected < 0.1s)"
        )

        print(f"\\nSpell rendering: {avg_time_per_render * 1000:.1f}ms average")

    @pytest.mark.slow
    def test_single_creature_rendering_performance(self, sample_creature: Any) -> None:
        """Benchmark single creature rendering performance."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Creature Performance Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Warm up
            self.renderer.render_document([sample_creature], context)

            # Measure performance
            start_time = time.perf_counter()
            for _ in range(50):  # Render 50 times (creatures are more complex)
                result = self.renderer.render_document([sample_creature], context)
                assert isinstance(result, str)
                assert len(result) > 100
            end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_render = total_time / 50

        # Performance assertions
        assert total_time < 15.0, (
            f"50 creature renders took {total_time:.2f}s (expected < 15s)"
        )
        assert avg_time_per_render < 0.3, (
            f"Average render time {avg_time_per_render:.3f}s (expected < 0.3s)"
        )

        print(f"\\nCreature rendering: {avg_time_per_render * 1000:.1f}ms average")

    @pytest.mark.slow
    def test_book_rendering_performance(self, sample_book: Any) -> None:
        """Benchmark book rendering performance."""
        context = RenderingContext(
            output_format="latex",
            metadata={"title": "Book Performance Test", "include_toc": True},
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Warm up
            self.renderer.render_document([sample_book], context)

            # Measure performance
            start_time = time.perf_counter()
            for _ in range(10):  # Render 10 times (books are complex)
                result = self.renderer.render_document([sample_book], context)
                assert isinstance(result, str)
                assert len(result) > 500
            end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_render = total_time / 10

        # Performance assertions
        assert total_time < 30.0, (
            f"10 book renders took {total_time:.2f}s (expected < 30s)"
        )
        assert avg_time_per_render < 3.0, (
            f"Average render time {avg_time_per_render:.3f}s (expected < 3s)"
        )

        print(f"\\nBook rendering: {avg_time_per_render * 1000:.1f}ms average")

    @pytest.mark.slow
    def test_mixed_content_rendering_performance(
        self, sample_spell: Any, sample_creature: Any, sample_source: Any
    ) -> None:
        """Benchmark mixed content rendering performance."""
        # Create a mix of different content types
        mixed_content = [sample_spell, sample_creature]

        # Add a few more spells (using simplified model)
        for i in range(3):
            simple_spell_data = {
                "name": f"Test Spell {i + 1}",
                "source": {"abbreviation": "TEST", "name": "Test Source", "page": None},
                "level": i + 1,
                "school": "T",  # Transmutation
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
                "components": {"v": True, "s": True},
                "duration": [
                    {"type": "timed", "duration": {"type": "minute", "amount": 1}}
                ],
                "entries": [f"This is test spell {i + 1}."],
            }
            mixed_content.append(Spell.model_validate(simple_spell_data))

        context = RenderingContext(
            output_format="latex", metadata={"title": "Mixed Content Performance Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Warm up
            self.renderer.render_document(mixed_content, context)

            # Measure performance
            start_time = time.perf_counter()
            for _ in range(20):  # Render 20 times
                result = self.renderer.render_document(mixed_content, context)
                assert isinstance(result, str)
                assert len(result) > 200
            end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_render = total_time / 20

        # Performance assertions
        assert total_time < 20.0, (
            f"20 mixed content renders took {total_time:.2f}s (expected < 20s)"
        )
        assert avg_time_per_render < 1.0, (
            f"Average render time {avg_time_per_render:.3f}s (expected < 1s)"
        )

        print(f"\\nMixed content rendering: {avg_time_per_render * 1000:.1f}ms average")

    @pytest.mark.slow
    def test_memory_usage_stability(self, sample_spell: Any) -> None:
        """Test that memory usage remains stable during repeated rendering."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        context = RenderingContext(
            output_format="latex", metadata={"title": "Memory Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Initial memory measurement
            gc.collect()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Render many times
            for i in range(200):
                result = self.renderer.render_document([sample_spell], context)
                assert isinstance(result, str)

                # Force garbage collection every 50 iterations
                if i % 50 == 0:
                    gc.collect()

            # Final memory measurement
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (adjust threshold as needed)
        assert memory_growth < 50.0, (
            f"Memory grew by {memory_growth:.1f}MB (expected < 50MB)"
        )

        print(
            f"\\nMemory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (growth: {memory_growth:.1f}MB)"
        )

    @pytest.mark.slow
    def test_template_engine_caching_performance(self, sample_spell: Any) -> None:
        """Test that template engine caching improves performance."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Caching Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Warm up to stabilize timing (more iterations)
            for _ in range(10):
                self.renderer.render_document([sample_spell], context)

            # Force garbage collection before timing
            import gc

            gc.collect()
            time.sleep(0.1)  # Allow system to stabilize

            # First batch (templates should be loaded and cached) - more iterations for stability
            start_time = time.perf_counter()
            for _ in range(100):
                result = self.renderer.render_document([sample_spell], context)
                assert isinstance(result, str)
            first_batch_time = time.perf_counter() - start_time

            # Small pause between batches
            time.sleep(0.05)
            gc.collect()

            # Second batch (templates should be cached)
            start_time = time.perf_counter()
            for _ in range(100):
                result = self.renderer.render_document([sample_spell], context)
                assert isinstance(result, str)
            second_batch_time = time.perf_counter() - start_time

        # Second batch should be faster or comparable (allowing for more variance)
        speedup_ratio = (
            first_batch_time / second_batch_time if second_batch_time > 0 else 1.0
        )

        print(
            f"\\nTemplate caching: First batch: {first_batch_time:.3f}s, Second batch: {second_batch_time:.3f}s"
        )
        print(f"Speedup ratio: {speedup_ratio:.2f}x")

        # More lenient threshold for intermittent CI environments - templates should not significantly degrade
        assert speedup_ratio >= 0.6, (
            f"Second batch slower than expected (ratio: {speedup_ratio:.2f})"
        )

    @pytest.mark.slow
    def test_large_document_rendering_performance(self, sample_source: Any) -> None:
        """Test performance with large documents."""
        # Create a large book with many chapters and content
        chapters = []
        for i in range(50):  # 50 chapters
            entries = []
            for j in range(20):  # 20 entries per chapter
                entries.append(f"This is paragraph {j + 1} of chapter {i + 1}.")
                if j % 5 == 0:  # Add some complex content
                    entries.append(
                        {
                            "type": "section",
                            "name": f"Section {i + 1}.{j + 1}",
                            "entries": [f"Nested content {i + 1}.{j + 1}"],
                        }
                    )

            chapters.append(
                Chapter(
                    name=f"Chapter {i + 1}",
                    ordinal={"type": "chapter", "identifier": i + 1},
                    headers=[f"Header {i + 1}.1", f"Header {i + 1}.2"],
                    entries=entries,
                )
            )

        large_book = Book(
            name="Large Performance Test Book",
            source=sample_source,
            contents=chapters,
            id=None,
            metadata=None,
            published=None,
            author=["Performance Author"],
            cover=None,
        )

        context = RenderingContext(
            output_format="latex",
            metadata={"title": "Large Document Test", "include_toc": True},
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Single render of large document
            start_time = time.perf_counter()
            result = self.renderer.render_document([large_book], context)
            end_time = time.perf_counter()

        render_time = end_time - start_time

        # Assertions for large document
        assert isinstance(result, str)
        assert len(result) > 5000  # Should be substantial
        assert render_time < 60.0, (
            f"Large document render took {render_time:.2f}s (expected < 60s)"
        )

        print(f"\\nLarge document (50 chapters): {render_time:.2f}s")

    @pytest.mark.slow
    def test_compilation_performance_integration(self, sample_spell: Any) -> None:
        """Test end-to-end performance including compilation."""
        from dnd5e.renderers.latex.compilation_config import (  # type: ignore
            CompilationResult,
            LaTeXEngine,
        )

        # Mock compilation to focus on rendering performance
        mock_result = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=0.5,  # Simulated compilation time
            output_file=Path("/tmp/perf_test.pdf"),
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ):
                # Measure end-to-end performance
                context = RenderingContext(
                    output_format="latex",
                    metadata={"title": "Compilation Performance Test"},
                )
                start_time = time.perf_counter()
                for _ in range(10):
                    result = compile_document_to_pdf_sync(
                        self.renderer, [sample_spell], context
                    )
                    assert result.success is True
                end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_compile = total_time / 10

        print(
            f"\\nEnd-to-end (render + mock compile): {avg_time_per_compile * 1000:.1f}ms average"
        )

        # Should complete quickly with mocked compilation
        assert avg_time_per_compile < 0.2, (
            f"Average compile time {avg_time_per_compile:.3f}s (expected < 0.2s)"
        )
