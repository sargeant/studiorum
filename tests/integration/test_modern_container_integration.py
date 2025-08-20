"""Integration tests for modern service container functionality.

These tests focus on container behavior and service lifecycle management,
using lightweight mocks to avoid heavy data loading operations.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from dnd5e.core.services.container import ModernServiceContainer, RequestScopedContainer
from dnd5e.core.services.lifecycle import ServiceLifecycle
from dnd5e.core.services.protocols import (
    AsyncResourceProtocol,
    ConfigurableServiceProtocol,
    OmnidexerProtocol,
    ServiceProtocol,
    TagResolverProtocol,
)


class TestProtocol(ServiceProtocol):
    """Test protocol for integration testing."""

    def get_service_name(self) -> str:
        return "TestService"


class TestAsyncProtocol(ServiceProtocol, AsyncResourceProtocol):
    """Test async protocol for integration testing."""

    def get_service_name(self) -> str:
        return "TestAsyncService"

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass

    def is_initialized(self) -> bool:
        return True


class MockService:
    """Mock service implementation."""

    def __init__(self, name: str = "MockService"):
        self.name = name
        self.initialized = False
        self.cleaned_up = False

    def get_service_name(self) -> str:
        return self.name


class MockAsyncService(AsyncResourceProtocol):
    """Mock async service implementation."""

    def __init__(self, name: str = "MockAsyncService"):
        self.name = name
        self.initialized = False
        self.cleaned_up = False

    def get_service_name(self) -> str:
        return self.name

    async def initialize(self) -> None:
        self.initialized = True

    async def cleanup(self) -> None:
        self.cleaned_up = True

    def is_initialized(self) -> bool:
        return self.initialized


class TestModernServiceContainer:
    """Test modern service container integration."""

    @pytest.mark.asyncio
    async def test_container_creation(self):
        """Test basic container creation and registration."""
        container = ModernServiceContainer()

        # Register a simple service
        container.register_service(
            TestProtocol,
            lambda: MockService("test"),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Get the service
        service = await container.get_service(TestProtocol)
        assert service.get_service_name() == "test"

        # Cleanup
        await container.cleanup()

    @pytest.mark.asyncio
    async def test_singleton_lifecycle(self):
        """Test singleton lifecycle behavior."""
        container = ModernServiceContainer()

        container.register_service(
            TestProtocol,
            lambda: MockService("singleton"),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Get service twice
        service1 = await container.get_service(TestProtocol)
        service2 = await container.get_service(TestProtocol)

        # Should be the same instance
        assert service1 is service2

        await container.cleanup()

    @pytest.mark.asyncio
    async def test_scoped_lifecycle(self):
        """Test scoped lifecycle behavior."""
        container = ModernServiceContainer()

        container.register_service(
            TestProtocol,
            lambda: MockService("scoped"),
            lifecycle=ServiceLifecycle.SCOPED,
        )

        # Get service in same scope
        service1 = await container.get_service(TestProtocol)
        service2 = await container.get_service(TestProtocol)

        # Should be the same instance within scope
        assert service1 is service2

        await container.cleanup()

    @pytest.mark.asyncio
    async def test_transient_lifecycle(self):
        """Test transient lifecycle behavior."""
        container = ModernServiceContainer()

        container.register_service(
            TestProtocol,
            lambda: MockService("transient"),
            lifecycle=ServiceLifecycle.TRANSIENT,
        )

        # Get service twice
        service1 = await container.get_service(TestProtocol)
        service2 = await container.get_service(TestProtocol)

        # Should be different instances
        assert service1 is not service2
        assert service1.get_service_name() == service2.get_service_name()

        await container.cleanup()

    @pytest.mark.asyncio
    async def test_async_resource_lifecycle(self):
        """Test async resource lifecycle behavior."""
        container = ModernServiceContainer()

        async def async_factory():
            service = MockAsyncService("async")
            await service.initialize()
            return service

        container.register_service(
            TestAsyncProtocol, async_factory, lifecycle=ServiceLifecycle.ASYNC_RESOURCE
        )

        # Get the service
        service = await container.get_service(TestAsyncProtocol)
        assert service.get_service_name() == "async"
        assert service.is_initialized()

        # Cleanup should call service cleanup
        await container.cleanup()
        assert service.cleaned_up

    @pytest.mark.asyncio
    async def test_dependency_injection(self):
        """Test dependency injection between services."""
        container = ModernServiceContainer()

        # Register dependency first
        container.register_service(
            TestProtocol,
            lambda: MockService("dependency"),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Register service that depends on first service
        class DependentProtocol(ServiceProtocol):
            def get_service_name(self) -> str:
                return "DependentService"

        async def async_dependent_factory(dependency):
            # Dependency is injected by the container
            service = MockService(f"dependent-{dependency.get_service_name()}")
            return service

        container.register_service(
            DependentProtocol,
            async_dependent_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
            dependencies=(TestProtocol,),
        )

        # Get dependent service
        service = await container.get_service(DependentProtocol)
        assert "dependency" in service.get_service_name()

        await container.cleanup()

    @pytest.mark.asyncio
    async def test_container_performance_with_realistic_services(self):
        """Test container performance with realistic service patterns."""
        container = ModernServiceContainer()

        # Mock lightweight omnidexer that doesn't load data
        class MockOmnidexer(AsyncResourceProtocol):
            def __init__(self):
                self._initialized = False

            def get_service_name(self) -> str:
                return "MockOmnidexer"

            async def initialize(self) -> None:
                # Simulate lightweight initialization
                await asyncio.sleep(0.001)  # 1ms
                self._initialized = True

            async def cleanup(self) -> None:
                self._initialized = False

            def is_initialized(self) -> bool:
                return self._initialized

            async def load_content_sources(self, sources: list[str]) -> None:
                pass

            def get_content(self, content_type: str, identifier: str) -> object:
                return {"type": content_type, "id": identifier}

            def search(self, query: str) -> list[object]:
                return [{"query": query}]

            async def ensure_sources_ready(self) -> None:
                pass

        # Mock tag resolver that depends on omnidexer
        class MockTagResolver:
            def __init__(self, omnidexer: OmnidexerProtocol):
                self._omnidexer = omnidexer

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

        # Register services with realistic dependencies
        async def omnidexer_factory():
            omnidexer = MockOmnidexer()
            await omnidexer.initialize()
            return omnidexer

        container.register_service(
            OmnidexerProtocol,
            omnidexer_factory,
            lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
        )

        async def tag_resolver_factory(omnidexer):
            # Omnidexer is injected as a dependency
            return MockTagResolver(omnidexer)

        container.register_service(
            TagResolverProtocol,
            tag_resolver_factory,
            lifecycle=ServiceLifecycle.SCOPED,
            dependencies=(OmnidexerProtocol,),
        )

        # Test performance of multiple service resolutions
        import time

        start_time = time.time()

        # Get services multiple times to test caching
        for _ in range(10):
            omnidexer = await container.get_service(OmnidexerProtocol)
            tag_resolver = await container.get_service(TagResolverProtocol)

            # Verify they work
            assert omnidexer.get_service_name() == "MockOmnidexer"
            assert tag_resolver.get_service_name() == "MockTagResolver"

        elapsed = time.time() - start_time

        # Should complete within reasonable time (much less than 2 minutes!)
        assert elapsed < 1.0, f"Container operations too slow: {elapsed:.3f}s"

        await container.cleanup()

    @pytest.mark.asyncio
    async def test_request_scoped_container(self):
        """Test request-scoped container creation and isolation."""
        parent_container = ModernServiceContainer()

        # Register singleton in parent
        parent_container.register_service(
            TestProtocol,
            lambda: MockService("parent-singleton"),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Create request scope
        async with await parent_container.create_request_scope() as request_scope:
            # Register scoped service in request scope
            request_scope.register_service(
                TestAsyncProtocol,
                lambda: MockAsyncService("request-scoped"),
                lifecycle=ServiceLifecycle.SCOPED,
            )

            # Get services
            singleton_service = await request_scope.get_service(TestProtocol)
            scoped_service = await request_scope.get_service(TestAsyncProtocol)

            assert singleton_service.get_service_name() == "parent-singleton"
            assert scoped_service.get_service_name() == "request-scoped"

        # Request scope should be cleaned up automatically
        await parent_container.cleanup()

    @pytest.mark.asyncio
    async def test_container_closure(self):
        """Test container closure prevents further operations."""
        container = ModernServiceContainer()

        container.register_service(
            TestProtocol,
            lambda: MockService("test"),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Get service before closure
        service = await container.get_service(TestProtocol)
        assert service is not None

        # Close container
        await container.cleanup()

        # Should not be able to get services after closure
        with pytest.raises(RuntimeError):
            await container.get_service(TestProtocol)

        # Should not be able to create request scope after closure
        with pytest.raises(RuntimeError):
            await container.create_request_scope()

    @pytest.mark.asyncio
    async def test_container_repr(self):
        """Test container string representation."""
        container = ModernServiceContainer()

        # Check initial state
        repr_str = repr(container)
        assert "ModernServiceContainer" in repr_str
        assert "open" in repr_str

        # Register and get service
        container.register_service(
            TestProtocol,
            lambda: MockService("test"),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        await container.get_service(TestProtocol)

        # Check with services
        repr_str = repr(container)
        assert "singletons=1" in repr_str

        # Check after cleanup
        await container.cleanup()
        repr_str = repr(container)
        assert "closed" in repr_str


class TestRequestScopedContainer:
    """Test request-scoped container specific functionality."""

    @pytest.mark.asyncio
    async def test_request_container_properties(self):
        """Test request container has proper properties."""
        parent = ModernServiceContainer()

        async with await parent.create_request_scope() as request_scope:
            assert isinstance(request_scope, RequestScopedContainer)
            assert hasattr(request_scope, "request_id")
            assert hasattr(request_scope, "created_at")
            assert len(request_scope.request_id) > 0

        await parent.cleanup()

    @pytest.mark.asyncio
    async def test_request_container_isolation(self):
        """Test that request containers are isolated from each other."""
        parent = ModernServiceContainer()

        # Create two request scopes
        async with await parent.create_request_scope() as scope1:
            async with await parent.create_request_scope() as scope2:
                # Register different services in each scope
                scope1.register_service(
                    TestProtocol,
                    lambda: MockService("scope1"),
                    lifecycle=ServiceLifecycle.SCOPED,
                )

                scope2.register_service(
                    TestProtocol,
                    lambda: MockService("scope2"),
                    lifecycle=ServiceLifecycle.SCOPED,
                )

                # Services should be different
                service1 = await scope1.get_service(TestProtocol)
                service2 = await scope2.get_service(TestProtocol)

                assert service1.get_service_name() == "scope1"
                assert service2.get_service_name() == "scope2"
                assert service1 is not service2

        await parent.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])
