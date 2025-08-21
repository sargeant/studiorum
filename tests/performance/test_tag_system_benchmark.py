"""Performance benchmarks for tag resolution systems."""

import time
from typing import Any

import pytest

from studiorum.core.text.tag_resolver import TagResolver


class TestTagSystemPerformance:
    """Performance tests for the AST-based tag system."""

    @pytest.fixture
    def sample_text(self) -> str:
        """Generate sample text with various tag types for testing."""
        return """
        The {@creature Ancient Red Dragon|MM|great wyrm} breathes fire dealing
        {@dice 26d6} fire damage. A DC {@dc 24} Dexterity saving throw reduces
        the damage by half. The {@spell Fireball|PHB} spell pales in comparison.

        The party explores {@adventure Chapter 3|CoS|Village of Barovia|42} where
        they encounter {@creature Strahd von Zarovich|CoS|the vampire lord} and
        his {@item Sunsword|CoS|legendary weapon}.

        {@b Bold text} and {@i italic text} can also be used for emphasis.
        The {@background Noble|PHB} character wields a {@item Longsword|PHB}.
        """

    @pytest.fixture
    def large_text(self) -> str:
        """Generate large text for stress testing."""
        base_tags = [
            "{@creature Ancient Red Dragon|MM}",
            "{@spell Fireball|PHB}",
            "{@item Longsword|PHB}",
            "{@dice 1d20+5}",
            "{@dc 15}",
        ]

        # Create a large document with many repeated tags
        parts = []
        for i in range(200):  # 200 repetitions
            for tag in base_tags:
                parts.append(f"Line {i}: {tag} appears in this text. ")

        return " ".join(parts)

    @pytest.mark.slow
    def test_tag_system_basic_performance(
        self, sample_text: str, loaded_omnidexer: Any
    ) -> None:
        """Test performance of AST-based tag system."""
        resolver = TagResolver(loaded_omnidexer)

        start_time = time.time()
        result = resolver.process_text(sample_text)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert processing_time < 1.0  # 1 second threshold
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tag_system_with_large_text(
        self, large_text: str, loaded_omnidexer: Any
    ) -> None:
        """Test performance with large documents."""
        resolver = TagResolver(loaded_omnidexer)

        start_time = time.time()
        result = resolver.process_text(large_text)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert processing_time < 1.0  # 1 second threshold
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.slow
    def test_memory_usage_basic(self, sample_text: str, loaded_omnidexer: Any) -> None:
        """Test that tag processing doesn't create excessive memory usage."""
        import gc

        resolver = TagResolver(loaded_omnidexer)

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Process text multiple times
        for _ in range(10):
            resolver.process_text(sample_text)

        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not create excessive permanent objects
        object_growth = final_objects - initial_objects
        # Increased threshold to account for Logfire telemetry overhead
        # Logfire creates spans, attributes, and other observability objects
        assert object_growth < 5000  # Allow reasonable growth with Logfire overhead
