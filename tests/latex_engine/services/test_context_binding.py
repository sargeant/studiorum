"""Tests for context binding functionality in template services."""

import pytest

from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.factories import (
    create_context_bound_template_service,
    create_latex_formatter_service,
    create_template_service_with_components,
    create_text_extractor_service,
)
from studiorum.latex_engine.services.context_bound_template_service import (
    ContextBoundTemplateService,
)
from studiorum.latex_engine.services.protocols import ContextBoundTemplateProtocol
from studiorum.renderers.core.interfaces import RenderingContext


class TestContextBinding:
    """Test context binding functionality."""

    @pytest.fixture
    def content_tracker(self):
        """Create a ContentTracker for testing."""
        return ContentTracker()

    @pytest.fixture
    def mock_template_service(self):
        """Create a mock template service for testing."""

        class MockTemplateService:
            def __init__(self):
                # Add required attributes for RenderingContext creation
                self.omnidexer = type("MockOmnidexer", (), {})()
                self.tag_resolver = type("MockTagResolver", (), {})()

            def get_service_name(self) -> str:
                return "MockTemplateService"

            def render_entry_description(self, entry, content_tracker):
                # Simple mock that returns entry name + tracker status
                entry_name = (
                    entry.get("name", "unknown")
                    if isinstance(entry, dict)
                    else str(entry)
                )
                return f"Rendered: {entry_name} (tracker: {id(content_tracker)})"

            # Legacy content-only API intentionally not implemented in mock

            def bind_context(self, content_tracker):
                return ContextBoundTemplateService(self, content_tracker)

        return MockTemplateService()

    def test_context_binding_creation(self, mock_template_service, content_tracker):
        """Test that context binding creates bound service correctly."""
        bound_service = mock_template_service.bind_context(content_tracker)

        assert isinstance(bound_service, ContextBoundTemplateService)
        assert bound_service._tracker is content_tracker
        assert bound_service._service is mock_template_service

    def test_bound_service_clean_apis(self, mock_template_service, content_tracker):
        """Test that bound service provides clean APIs without tracker parameter."""
        bound_service = mock_template_service.bind_context(content_tracker)

        # Test clean API without tracker parameter
        test_entry = {"name": "Fireball", "content": "A bright flame"}

        result_description = bound_service.render_entry(test_entry)

        # Verify results contain expected content
        assert "Fireball" in result_description

        # Verify the same tracker was used (ID should match)
        tracker_id_str = str(id(content_tracker))
        assert tracker_id_str in result_description

    def test_bound_service_tracker_access(self, mock_template_service, content_tracker):
        """Test that bound service provides access to the bound ContentTracker."""
        bound_service = mock_template_service.bind_context(content_tracker)

        assert bound_service.content_tracker is content_tracker

    def test_context_binding_factory(self, mock_template_service, content_tracker):
        """Test the factory function for creating context-bound services."""
        bound_service = create_context_bound_template_service(
            mock_template_service, content_tracker
        )

        assert isinstance(bound_service, ContextBoundTemplateProtocol)
        assert bound_service.content_tracker is content_tracker

    def test_rendering_context_creation(self, mock_template_service, content_tracker):
        """Test that bound service can create RenderingContext with bound tracker."""
        bound_service = mock_template_service.bind_context(content_tracker)

        context = bound_service.create_rendering_context(
            output_format="latex", debug_mode=True, test_metadata="value"
        )

        assert isinstance(context, RenderingContext)
        assert context.output_format == "latex"
        assert context.debug_mode is True
        assert context.content_tracker is content_tracker
        assert context.metadata["test_metadata"] == "value"


class TestContextFlowValidation:
    """Test that ContentTracker context flows correctly through bound services."""

    @pytest.fixture
    def content_tracker(self):
        """Create a ContentTracker for testing."""
        return ContentTracker()

    def test_context_flows_through_bound_service(self, content_tracker):
        """Test that context flows correctly through bound service operations."""
        # Create real services for integration testing
        text_extractor = create_text_extractor_service()
        latex_formatter = create_latex_formatter_service()

        # Create a minimal mock for dependencies
        class MockTagResolver:
            def process_text(self, text, context):
                # Verify context contains our tracker
                assert context.content_tracker is content_tracker
                return f"processed:{text}"

        class MockOmnidexer:
            pass

        # Create template service with real components
        template_service = ContextBoundTemplateService(
            base_service=type(
                "MockService",
                (),
                {
                    "text_extractor": text_extractor,
                    "latex_formatter": latex_formatter,
                    "tag_resolver": MockTagResolver(),
                    "omnidexer": MockOmnidexer(),
                    "render_entry_description": lambda self,
                    entry,
                    tracker: f"rendered:{entry}",
                },
            )(),
            content_tracker=content_tracker,
        )

        # Test that context flows correctly
        test_entry = {"name": "Test Entry"}

        result_description = template_service.render_entry(test_entry)

        assert "rendered:" in result_description
        # content-only path removed; description rendering remains


class TestPerformanceValidation:
    """Test that context binding doesn't impact performance."""

    def test_context_binding_overhead_minimal(self):
        """Test that context binding creation overhead is minimal."""
        import time

        # Create mock services
        class MockTemplateService:
            def bind_context(self, tracker):
                return ContextBoundTemplateService(self, tracker)

        template_service = MockTemplateService()
        tracker = ContentTracker()

        # Benchmark binding creation
        start_time = time.time()
        for _ in range(1000):
            bound_service = template_service.bind_context(tracker)
            # Simulate a simple operation
            _ = bound_service.content_tracker
        end_time = time.time()

        # Should complete 1000 bindings in well under 1 second
        total_time = end_time - start_time
        assert total_time < 1.0, (
            f"Context binding too slow: {total_time:.3f}s for 1000 operations"
        )

        # Average per-operation should be under 1ms
        avg_time_ms = (total_time / 1000) * 1000
        assert avg_time_ms < 1.0, (
            f"Per-operation overhead too high: {avg_time_ms:.3f}ms"
        )

    def test_bound_service_memory_usage_stable(self):
        """Test that bound services don't create excessive memory overhead."""
        import gc
        import sys

        template_service = type(
            "MockService",
            (),
            {
                "bind_context": lambda self, tracker: ContextBoundTemplateService(
                    self, tracker
                )
            },
        )()

        # Create multiple bound services
        trackers = [ContentTracker() for _ in range(100)]
        bound_services = [template_service.bind_context(t) for t in trackers]

        # Force garbage collection and check that services are manageable
        gc.collect()

        # Each bound service should have minimal overhead
        assert len(bound_services) == 100
        assert all(service.content_tracker in trackers for service in bound_services)

        # Memory usage should be reasonable (no retained references to large objects)
        total_size = sum(sys.getsizeof(service) for service in bound_services)
        avg_size = total_size / len(bound_services)

        # Each bound service should be small (< 1KB overhead)
        assert avg_size < 1024, (
            f"Bound service memory overhead too high: {avg_size} bytes"
        )
