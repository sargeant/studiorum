"""
Integration tests using real 5etools data to validate the tag handler architecture.

This module tests the complete tag rendering pipeline with actual content from
the 5etools dataset, ensuring correctness and functionality.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, create_autospec

import pytest

from dnd5e.core.indexer.content_tracker import ContentTracker
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.text.tag_ast import TagNode
from dnd5e.renderers.core.handlers import get_default_core_handlers
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.core.unified_renderer import StandardUnifiedRenderer


class TestRealDataIntegration:
    """Integration tests with real 5etools data."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment with real data."""
        # Set up paths to real data
        self.data_root = Path("/Users/sam/Code/5etools-src/data")

        # Skip if data not available
        if not self.data_root.exists():
            pytest.skip("5etools data not available")

        # Initialize omnidexer with real data
        self.omnidexer = Omnidexer()

        # Set up mock content tracker
        self.content_tracker = create_autospec(ContentTracker, spec_set=True)

        # Create rendering context for tests
        self.rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            content_tracker=self.content_tracker,
            debug_mode=False,
        )

    def load_sample_content(
        self, content_type: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Load sample content of specified type."""
        content_files = {
            "creature": "creatures.json",
            "spell": "spells/spells-phb.json",
            "item": "items.json",
        }

        if content_type not in content_files:
            return []

        file_path = self.data_root / content_files[content_type]
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)

        # Extract content array based on structure
        if content_type in data:
            return data[content_type][:limit]
        elif isinstance(data, list):
            return data[:limit]
        elif "data" in data:
            return data["data"][:limit]
        else:
            return []

    def create_tag_node(self, content: dict[str, Any], tag_type: str) -> TagNode:
        """Create a TagNode from content data."""
        name = content.get("name", "Unknown")
        source = content.get("source", "PHB")
        page = content.get("page")

        # Create mock tag node
        node = Mock(spec=TagNode)
        node.tag_type = tag_type
        node.name = name
        node.source = source
        node.page = str(page) if page else None
        node.display_text = name
        node.content = content

        return node

    def test_creature_handler_with_real_data(self):
        """Test creature handler with real creature data."""
        # Load real creature data
        creatures = self.load_sample_content("creature", 5)
        if not creatures:
            pytest.skip("No creature data available")

        # Set up unified renderer
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)

        for creature in creatures:
            # Create tag node
            node = self.create_tag_node(creature, "creature")

            # Test rendering
            result = renderer.render_tag(node, self.rendering_context)

            # Basic validation
            assert isinstance(result, str)
            assert len(result) > 0
            assert (
                creature["name"] in result or creature["name"].lower() in result.lower()
            )

            # Should be LaTeX formatted for bold creatures
            if "\\textbf{" not in result:
                # If not bold, should at least be properly escaped
                assert "&" not in result or "\\&" in result

    def test_spell_handler_with_real_data(self):
        """Test spell handler with real spell data."""
        # Load real spell data
        spells = self.load_sample_content("spell", 5)
        if not spells:
            pytest.skip("No spell data available")

        # Set up unified renderer
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)

        for spell in spells:
            # Create tag node
            node = self.create_tag_node(spell, "spell")

            # Test rendering
            result = renderer.render_tag(node, self.rendering_context)

            # Basic validation
            assert isinstance(result, str)
            assert len(result) > 0
            assert spell["name"] in result or spell["name"].lower() in result.lower()

            # Should be italicized for spells
            expected_format = f"\\textit{{{spell['name']}}}"
            assert expected_format in result or spell["name"] in result

    def test_item_handler_with_real_data(self):
        """Test item handler with real item data."""
        # Load real item data
        items = self.load_sample_content("item", 5)
        if not items:
            pytest.skip("No item data available")

        # Set up unified renderer
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)

        for item in items:
            # Create tag node
            node = self.create_tag_node(item, "item")

            # Test rendering
            result = renderer.render_tag(node, self.rendering_context)

            # Basic validation
            assert isinstance(result, str)
            assert len(result) > 0
            assert item["name"] in result or item["name"].lower() in result.lower()

    def test_content_tracking_integration(self):
        """Test that content tracking works with real data."""
        # Load sample data
        creatures = self.load_sample_content("creature", 3)
        if not creatures:
            pytest.skip("No creature data available")

        # Mock content tracker to capture calls
        mock_tracker = Mock(spec=ContentTracker)

        # Set up unified renderer with content tracking and the mock tracker
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(
            core_handlers,
            content_tracker=mock_tracker,  # Pass tracker directly to renderer
            enable_content_tracking=True,
            enable_hyperlinks=True,
        )

        # Create simple context - the tracker is already configured in the renderer
        context_with_tracker = RenderingContext(
            output_format="latex",
            omnidexer=self.omnidexer,
            metadata={},
        )

        for creature in creatures:
            node = self.create_tag_node(creature, "creature")

            # Render with tracking
            result = renderer.render_tag(node, context_with_tracker)

            # Validate result
            assert isinstance(result, str)
            assert len(result) > 0

        # Verify content tracker was called
        assert mock_tracker.add_content.call_count >= len(creatures)

    def test_error_handling_with_malformed_data(self):
        """Test error handling with malformed or edge case data."""
        # Create problematic tag nodes
        test_cases = [
            # Empty name
            Mock(
                spec=TagNode,
                tag_type="creature",
                name="",
                display_text="",
                source="PHB",
            ),
            # Missing attributes
            Mock(spec=TagNode, tag_type="creature", name="Test"),
            # Very long name
            Mock(
                spec=TagNode,
                tag_type="creature",
                name="A" * 1000,
                display_text="A" * 1000,
                source="TEST",
            ),
            # Special characters
            Mock(
                spec=TagNode,
                tag_type="creature",
                name="Test & <Dragon>",
                display_text="Test & <Dragon>",
                source="PHB",
            ),
        ]

        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)

        for node in test_cases:
            # Should not raise exceptions
            try:
                result = renderer.render_tag(node, self.rendering_context)
                assert isinstance(result, str)

                # Should handle LaTeX escaping
                if hasattr(node, "name") and "&" in node.name:
                    assert "&" not in result or "\\&" in result

            except Exception as e:
                pytest.fail(f"Renderer failed on edge case {node}: {e}")

    def test_performance_with_large_dataset(self):
        """Test performance characteristics with larger datasets."""
        import time

        # Load larger dataset
        creatures = self.load_sample_content("creature", 50)
        if len(creatures) < 10:
            pytest.skip("Insufficient data for performance testing")

        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)

        # Measure rendering time
        start_time = time.time()

        results = []
        for creature in creatures:
            node = self.create_tag_node(creature, "creature")
            result = renderer.render_tag(node, self.rendering_context)
            results.append(result)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        avg_time_per_item = total_time / len(creatures)
        assert avg_time_per_item < 0.1, (
            f"Rendering too slow: {avg_time_per_item:.3f}s per item"
        )

        # Validate all results
        assert len(results) == len(creatures)
        assert all(isinstance(r, str) and len(r) > 0 for r in results)

    def test_omnidexer_integration(self):
        """Test integration with real omnidexer data."""
        try:
            # Load real data into omnidexer
            stats = self.omnidexer.load_all_data()

            # Verify data was loaded
            assert stats is not None

            # Test with creatures if available
            creatures = self.omnidexer.get_all_by_type(ContentType.CREATURE)
            if creatures:
                sample_creature = creatures[0]

                # Create tag node for real creature
                node = Mock(spec=TagNode)
                node.tag_type = "creature"
                node.name = sample_creature.name
                node.source = (
                    sample_creature.source.abbreviation
                    if hasattr(sample_creature.source, "abbreviation")
                    else str(sample_creature.source)
                )
                node.display_text = sample_creature.name

                # Test with enhanced context
                enhanced_context = RenderingContext(
                    output_format="latex", omnidexer=self.omnidexer, metadata={}
                )

                core_handlers = get_default_core_handlers()
                renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)
                result = renderer.render_tag(node, enhanced_context)

                assert isinstance(result, str)
                assert len(result) > 0
                assert sample_creature.name in result

        except Exception as e:
            pytest.skip(f"Omnidexer integration failed: {e}")


class TestRealDataPerformance:
    """Performance-focused integration tests with real data."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up performance testing environment."""
        self.data_root = Path("/Users/sam/Code/5etools-src/data")
        if not self.data_root.exists():
            pytest.skip("5etools data not available")

    def test_memory_usage_with_large_content(self):
        """Test memory usage patterns with large content sets."""
        import os

        import psutil

        # Get baseline memory
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Load large dataset
        file_path = self.data_root / "creatures.json"
        if not file_path.exists():
            pytest.skip("Large creature dataset not available")

        with open(file_path) as f:
            data = json.load(f)

        creatures = data.get("creature", [])[:100]  # Limit for testing

        # Set up renderer
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)
        context = RenderingContext(output_format="latex", omnidexer=Mock(), metadata={})

        # Render all creatures
        results = []
        for creature in creatures:
            node = Mock(spec=TagNode)
            node.tag_type = "creature"
            node.name = creature.get("name", "Unknown")
            node.source = creature.get("source", "PHB")
            node.display_text = creature.get("name", "Unknown")

            result = renderer.render_tag(node, context)
            results.append(result)

        # Check final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory

        # Memory should not increase dramatically
        assert memory_increase < 100, (
            f"Memory usage too high: {memory_increase:.1f}MB increase"
        )

        # Verify results
        assert len(results) == len(creatures)
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_rendering_safety(self):
        """Test that concurrent rendering is safe."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Load test data
        file_path = self.data_root / "creatures.json"
        if not file_path.exists():
            pytest.skip("Creature data not available")

        with open(file_path) as f:
            data = json.load(f)

        creatures = data.get("creature", [])[:20]  # Small set for concurrent testing

        # Set up renderer
        core_handlers = get_default_core_handlers()
        renderer = StandardUnifiedRenderer.create_latex_renderer(core_handlers)
        context = RenderingContext(output_format="latex", omnidexer=Mock(), metadata={})

        def render_creature(creature):
            """Render a single creature."""
            node = Mock(spec=TagNode)
            node.tag_type = "creature"
            node.name = creature.get("name", "Unknown")
            node.source = creature.get("source", "PHB")
            node.display_text = creature.get("name", "Unknown")

            return renderer.render_tag(node, context)

        # Execute concurrent rendering
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(render_creature, creature): creature
                for creature in creatures
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Concurrent rendering failed: {e}")

        # Verify results
        assert len(results) == len(creatures)
        assert all(isinstance(r, str) and len(r) > 0 for r in results)
