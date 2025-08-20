"""Tests for AsyncRequestContext and context lifecycle management."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from dnd5e.core.context import (
    AsyncRequestContext,
    RequestContext,
    async_request_context,
    create_async_request_context,
    create_sync_request_context,
    performance_monitored_context,
    request_context,
)
from dnd5e.core.error_types import ContentNotFoundError, DND5eError
from dnd5e.core.services.protocols import (
    ConfigurationProtocol,
    OmnidexerProtocol,
    TagResolverProtocol,
)


class MockOmnidexer:
    """Mock omnidexer for testing."""

    def get_service_name(self) -> str:
        return "MockOmnidexer"

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass

    def is_initialized(self) -> bool:
        return True

    async def load_content_sources(self, sources: list[str]) -> None:
        pass

    def get_content(self, content_type: str, identifier: str) -> object:
        return {"type": content_type, "id": identifier}

    def search(self, query: str) -> list[object]:
        return [{"query": query, "name": f"Mock result for {query}"}]

    async def ensure_sources_ready(self) -> None:
        pass


class MockTagResolver:
    """Mock tag resolver for testing."""

    def get_service_name(self) -> str:
        return "MockTagResolver"

    async def reload_config(self, new_config) -> None:
        pass

    def supports_hot_reload(self) -> bool:
        return True

    def resolve_tag(self, tag: str, context) -> str:
        return f"resolved:{tag}"

    def supports_tag_type(self, tag_type: str) -> bool:
        return True


class MockConfiguration:
    """Mock configuration for testing."""

    def get_service_name(self) -> str:
        return "MockConfiguration"

    def get_config(self):
        return {"test": True}

    async def reload_config(self, new_config) -> None:
        pass

    def supports_hot_reload(self) -> bool:
        return True


@pytest.mark.asyncio
class TestAsyncRequestContext:
    """Test AsyncRequestContext functionality."""

    async def test_context_creation(self):
        """Test basic context creation and properties."""
        context = create_async_request_context()

        assert context.request_id is not None
        assert context.started_at is not None
        assert context.finished_at is None
        assert not context.is_closed
        assert context.sources == []
        assert context.metadata == {}

    async def test_context_with_config(self):
        """Test context creation with configuration override."""
        from dnd5e.core.config.unified_config import ApplicationConfig

        # Create a mock config
        mock_config = MagicMock(spec=ApplicationConfig)
        context = create_async_request_context(config_override=mock_config)

        assert context.user_config is mock_config

    async def test_context_manager_lifecycle(self):
        """Test async context manager lifecycle."""
        context = create_async_request_context()

        # Mock the container creation to avoid complex dependencies
        with patch.object(context, "_create_request_container") as mock_create:
            mock_container = AsyncMock()
            mock_create.return_value = mock_container

            with patch.object(context, "_initialize_async_resources") as mock_init:
                async with context as ctx:
                    assert ctx is context
                    assert not context.is_closed
                    mock_create.assert_called_once()
                    mock_init.assert_called_once()

                # Context should be closed after exiting
                assert context.is_closed
                assert context.finished_at is not None
                mock_container.cleanup.assert_called_once()

    async def test_error_collection(self):
        """Test error collection and retrieval."""
        context = create_async_request_context()

        error1 = ContentNotFoundError("Test error 1")
        error2 = DND5eError("Test error 2", error_code="TEST_ERROR")

        context.add_error(error1)
        await context.add_async_error(error2)

        assert context.has_errors()
        errors = context.get_errors()
        assert len(errors) == 2
        assert errors[0] is error1
        assert errors[1] is error2

        context.clear_errors()
        assert not context.has_errors()

    async def test_performance_metrics(self):
        """Test performance metrics collection."""
        context = create_async_request_context()

        # Test cache hit/miss recording
        context.record_cache_hit()
        context.record_cache_hit()
        context.record_cache_miss()

        assert context.metrics.cache_hits == 2
        assert context.metrics.cache_misses == 1

        # Test async operation recording
        context.record_async_operation()
        context.record_async_operation()

        assert context.metrics.async_operations_count == 2

    @patch("dnd5e.core.context.ModernServiceContainer")
    async def test_service_access_caching(self, mock_container_class):
        """Test service access with caching."""
        # Setup mock container and services
        mock_container = AsyncMock()
        mock_container_class.return_value = mock_container

        mock_omnidexer = MockOmnidexer()
        mock_container.get_service.return_value = mock_omnidexer

        context = create_async_request_context()

        async with context as ctx:
            # First access should call container
            omnidexer1 = await ctx.get_service(OmnidexerProtocol)
            assert isinstance(omnidexer1, MockOmnidexer)

            # Second access should use cache
            omnidexer2 = await ctx.get_service(OmnidexerProtocol)
            assert omnidexer2 is omnidexer1

            # Verify metrics
            assert ctx.metrics.cache_hits == 1  # Second access was cached
            assert ctx.metrics.cache_misses == 1  # First access was miss

    async def test_context_closed_error(self):
        """Test that closed context raises appropriate errors."""
        context = create_async_request_context()

        # Mock container to avoid complex setup
        with patch.object(context, "_create_request_container"):
            with patch.object(context, "_initialize_async_resources"):
                async with context:
                    pass  # Context closes here

        # Should raise error when accessing closed context
        with pytest.raises(RuntimeError, match="AsyncRequestContext .* is closed"):
            await context.get_service(OmnidexerProtocol)

    async def test_duration_calculation(self):
        """Test duration calculation."""
        context = create_async_request_context()

        # Duration should be None before context is finished
        assert context.duration_ms is None

        # Mock container to avoid complex setup
        with patch.object(context, "_create_request_container"):
            with patch.object(context, "_initialize_async_resources"):
                async with context:
                    # Small delay to ensure measurable duration
                    await asyncio.sleep(0.001)

        # Duration should be calculated after context finishes
        assert context.duration_ms is not None
        assert context.duration_ms > 0

    async def test_hot_reload_configuration(self):
        """Test hot-reload configuration functionality."""
        from dnd5e.core.config.unified_config import ApplicationConfig

        context = create_async_request_context()

        # Mock container and services
        mock_container = AsyncMock()
        # mock_service = MockConfiguration()  # Unused

        with patch.object(context, "_container", mock_container):
            # Test hot-reload
            new_config = MagicMock(spec=ApplicationConfig)
            await context.reload_configuration(new_config)

            assert context.user_config is new_config
            mock_container.register_instance.assert_called_once()


class TestSyncRequestContext:
    """Test sync RequestContext wrapper."""

    def test_sync_context_creation(self):
        """Test sync context wrapper creation."""
        context = create_sync_request_context()
        assert isinstance(context, RequestContext)
        assert isinstance(context._async_context, AsyncRequestContext)

    def test_sync_context_manager(self):
        """Test sync context manager functionality."""
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            context = create_sync_request_context()

            with context as ctx:
                assert ctx is context
                mock_loop.run_until_complete.assert_called()

    def test_sync_property_access(self):
        """Test sync property access delegation."""
        context = create_sync_request_context()

        with patch.object(context, "_loop") as mock_loop:
            mock_loop.run_until_complete.return_value = "test_value"

            # Test property access
            _ = context.request_id  # Should not call run_until_complete
            assert not mock_loop.run_until_complete.called

            # Test async property access
            with patch.object(context._async_context, "omnidexer"):
                mock_loop.run_until_complete.reset_mock()
                _ = context.omnidexer  # Should call run_until_complete
                mock_loop.run_until_complete.assert_called_once()


class TestContextFactories:
    """Test context factory functions and managers."""

    async def test_async_request_context_manager(self):
        """Test async_request_context factory function."""
        with patch("dnd5e.core.context.create_async_request_context") as mock_create:
            mock_context = AsyncMock()
            mock_create.return_value = mock_context

            async with async_request_context() as ctx:
                assert ctx is mock_context
                mock_context.__aenter__.assert_called_once()

            mock_context.__aexit__.assert_called_once()

    def test_sync_request_context_manager(self):
        """Test request_context factory function."""
        with patch("dnd5e.core.context.create_sync_request_context") as mock_create:
            mock_context = MagicMock()
            mock_create.return_value = mock_context

            with request_context() as ctx:
                assert ctx is mock_context
                mock_context.__enter__.assert_called_once()

            mock_context.__exit__.assert_called_once()

    async def test_performance_monitored_context(self):
        """Test performance_monitored_context factory."""
        with patch("dnd5e.core.context.create_async_request_context") as mock_create:
            mock_context = AsyncMock()
            mock_context.metrics = MagicMock()
            mock_create.return_value = mock_context

            async with performance_monitored_context(performance_tracking=True) as ctx:
                assert ctx is mock_context
                assert ctx.metadata["performance_tracking"] is True


@pytest.mark.asyncio
class TestConcurrentContexts:
    """Test concurrent context isolation."""

    async def test_concurrent_context_isolation(self):
        """Test that concurrent contexts are properly isolated."""

        async def create_context_with_id(context_id: str):
            context = create_async_request_context(metadata={"id": context_id})

            with patch.object(context, "_create_request_container"):
                with patch.object(context, "_initialize_async_resources"):
                    async with context as ctx:
                        # Add a unique error to each context
                        error = DND5eError(f"Error from context {context_id}")
                        ctx.add_error(error)

                        # Simulate some async work
                        await asyncio.sleep(0.001)

                        return ctx.get_errors()

        # Create multiple concurrent contexts
        tasks = [
            create_context_with_id("ctx1"),
            create_context_with_id("ctx2"),
            create_context_with_id("ctx3"),
        ]

        results = await asyncio.gather(*tasks)

        # Verify each context has only its own error
        for i, errors in enumerate(results):
            assert len(errors) == 1
            assert f"Error from context ctx{i + 1}" in errors[0].message

    async def test_performance_isolation(self):
        """Test that performance metrics are isolated between contexts."""

        async def context_with_metrics(cache_hits: int):
            context = create_async_request_context()

            with patch.object(context, "_create_request_container"):
                with patch.object(context, "_initialize_async_resources"):
                    async with context as ctx:
                        # Record different numbers of cache hits
                        for _ in range(cache_hits):
                            ctx.record_cache_hit()

                        return ctx.metrics.cache_hits

        # Create contexts with different metric values
        tasks = [
            context_with_metrics(1),
            context_with_metrics(3),
            context_with_metrics(5),
        ]

        results = await asyncio.gather(*tasks)

        # Verify metrics are isolated
        assert results == [1, 3, 5]
