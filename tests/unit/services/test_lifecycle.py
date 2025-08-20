"""Tests for service lifecycle management system."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from dnd5e.core.services.lifecycle import (
    AsyncServiceFactory,
    CleanupPriority,
    ServiceDescriptor,
    ServiceLifecycle,
    optimize_lifecycle_for_service,
    validate_service_descriptor,
)
from dnd5e.core.services.protocols import ServiceProtocol


class MockProtocol(ServiceProtocol):
    """Mock protocol for testing."""

    def get_service_name(self) -> str:
        return "MockProtocol"


class MockAsyncFactory(AsyncServiceFactory[MockProtocol]):
    """Mock async factory for testing."""

    async def create(self, container) -> MockProtocol:
        return MagicMock(spec=MockProtocol)

    async def cleanup(self, instance: MockProtocol) -> None:
        pass


class TestServiceLifecycle:
    """Test service lifecycle enum and behaviors."""

    def test_lifecycle_enum_values(self):
        """Test that lifecycle enum has expected values."""
        assert ServiceLifecycle.SINGLETON.value == "singleton"
        assert ServiceLifecycle.SCOPED.value == "scoped"
        assert ServiceLifecycle.TRANSIENT.value == "transient"
        assert ServiceLifecycle.ASYNC_RESOURCE.value == "async_resource"
        assert ServiceLifecycle.HOT_RELOADABLE.value == "hot_reloadable"

    def test_lifecycle_enum_completeness(self):
        """Test that we have all expected lifecycle types."""
        expected_lifecycles = {
            "singleton",
            "scoped",
            "transient",
            "async_resource",
            "hot_reloadable",
        }
        actual_lifecycles = {lifecycle.value for lifecycle in ServiceLifecycle}
        assert actual_lifecycles == expected_lifecycles


class TestServiceDescriptor:
    """Test service descriptor functionality."""

    def test_service_descriptor_creation(self):
        """Test basic service descriptor creation."""

        def simple_factory():
            return MagicMock(spec=MockProtocol)

        descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=simple_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
            dependencies=(),
            hot_reloadable=False,
            cleanup_priority=100,
        )

        assert descriptor.protocol == MockProtocol
        assert descriptor.factory == simple_factory
        assert descriptor.lifecycle == ServiceLifecycle.SINGLETON
        assert descriptor.dependencies == ()
        assert descriptor.hot_reloadable is False
        assert descriptor.cleanup_priority == 100

    def test_is_async_factory_detection(self):
        """Test detection of async factories."""

        def sync_factory():
            return MagicMock(spec=MockProtocol)

        async def async_factory():
            return MagicMock(spec=MockProtocol)

        sync_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=sync_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        async_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=async_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        async_factory_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=MockAsyncFactory(),
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        assert not sync_descriptor.is_async_factory()
        assert async_descriptor.is_async_factory()
        assert async_factory_descriptor.is_async_factory()

    def test_requires_container_detection(self):
        """Test detection of container-requiring factories."""

        def no_params_factory():
            return MagicMock(spec=MockProtocol)

        def container_factory(container):
            return MagicMock(spec=MockProtocol)

        async_factory = MockAsyncFactory()

        no_params_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=no_params_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        container_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=container_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        async_factory_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=async_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        assert not no_params_descriptor.requires_container()
        assert container_descriptor.requires_container()
        assert async_factory_descriptor.requires_container()

    def test_lifecycle_compatibility_validation(self):
        """Test lifecycle compatibility validation."""

        def simple_factory():
            return MagicMock(spec=MockProtocol)

        # Valid combination
        valid_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=simple_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
            hot_reloadable=True,
        )

        errors = valid_descriptor.validate_lifecycle_compatibility()
        assert len(errors) == 0

        # Invalid combination: hot-reloadable transient
        invalid_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=simple_factory,
            lifecycle=ServiceLifecycle.TRANSIENT,
            hot_reloadable=True,
        )

        errors = invalid_descriptor.validate_lifecycle_compatibility()
        assert len(errors) > 0
        assert "Hot-reloadable" in errors[0]
        assert "TRANSIENT" in errors[0]

    def test_async_resource_validation(self):
        """Test async resource lifecycle validation."""

        def sync_factory():
            return MagicMock(spec=MockProtocol)

        async def async_factory():
            return MagicMock(spec=MockProtocol)

        # Invalid: async resource with sync factory
        invalid_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=sync_factory,
            lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
        )

        errors = invalid_descriptor.validate_lifecycle_compatibility()
        assert len(errors) > 0
        assert "ASYNC_RESOURCE" in errors[0]
        assert "async factory" in errors[0]

        # Valid: async resource with async factory
        valid_descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=async_factory,
            lifecycle=ServiceLifecycle.ASYNC_RESOURCE,
        )

        errors = valid_descriptor.validate_lifecycle_compatibility()
        # Should only have dependency-related errors, not async factory errors
        async_factory_errors = [e for e in errors if "async factory" in e]
        assert len(async_factory_errors) == 0


class TestLifecycleOptimization:
    """Test lifecycle optimization helper functions."""

    def test_optimize_for_expensive_stateless(self):
        """Test optimization for expensive, stateless services."""
        lifecycle = optimize_lifecycle_for_service(
            service_type=MockProtocol,
            is_stateless=True,
            is_expensive_to_create=True,
            needs_request_isolation=False,
            supports_hot_reload=False,
            requires_async_init=False,
        )

        assert lifecycle == ServiceLifecycle.SINGLETON

    def test_optimize_for_request_isolation(self):
        """Test optimization for services needing request isolation."""
        lifecycle = optimize_lifecycle_for_service(
            service_type=MockProtocol,
            is_stateless=False,
            is_expensive_to_create=False,
            needs_request_isolation=True,
            supports_hot_reload=False,
            requires_async_init=False,
        )

        assert lifecycle == ServiceLifecycle.SCOPED

    def test_optimize_for_async_init(self):
        """Test optimization for services requiring async init."""
        lifecycle = optimize_lifecycle_for_service(
            service_type=MockProtocol,
            is_stateless=True,
            is_expensive_to_create=False,
            needs_request_isolation=False,
            supports_hot_reload=False,
            requires_async_init=True,
        )

        assert lifecycle == ServiceLifecycle.ASYNC_RESOURCE

    def test_optimize_for_cheap_no_reload(self):
        """Test optimization for cheap services without hot-reload."""
        lifecycle = optimize_lifecycle_for_service(
            service_type=MockProtocol,
            is_stateless=True,
            is_expensive_to_create=False,
            needs_request_isolation=False,
            supports_hot_reload=False,
            requires_async_init=False,
        )

        assert lifecycle == ServiceLifecycle.TRANSIENT

    def test_optimize_for_cheap_with_reload(self):
        """Test optimization for cheap services with hot-reload."""
        lifecycle = optimize_lifecycle_for_service(
            service_type=MockProtocol,
            is_stateless=True,
            is_expensive_to_create=False,
            needs_request_isolation=False,
            supports_hot_reload=True,
            requires_async_init=False,
        )

        assert lifecycle == ServiceLifecycle.SINGLETON


class TestCleanupPriority:
    """Test cleanup priority constants."""

    def test_priority_ordering(self):
        """Test that cleanup priorities are in expected order."""
        assert CleanupPriority.CONFIGURATION < CleanupPriority.CORE_RESOURCES
        assert CleanupPriority.CORE_RESOURCES < CleanupPriority.INFRASTRUCTURE
        assert CleanupPriority.INFRASTRUCTURE < CleanupPriority.BUSINESS_LOGIC
        assert CleanupPriority.BUSINESS_LOGIC < CleanupPriority.REQUEST_SCOPED
        assert CleanupPriority.REQUEST_SCOPED < CleanupPriority.DISPLAY_OUTPUT
        assert CleanupPriority.DISPLAY_OUTPUT < CleanupPriority.DEFAULT

    def test_priority_values(self):
        """Test that priority values are reasonable."""
        assert CleanupPriority.CONFIGURATION == 10
        assert CleanupPriority.DEFAULT == 100


class TestServiceDescriptorValidation:
    """Test service descriptor validation function."""

    def test_valid_descriptor_passes(self):
        """Test that valid descriptors pass validation."""

        def simple_factory():
            return MagicMock(spec=MockProtocol)

        descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=simple_factory,
            lifecycle=ServiceLifecycle.SINGLETON,
        )

        # Should not raise
        validate_service_descriptor(descriptor)

    def test_invalid_descriptor_raises(self):
        """Test that invalid descriptors raise ValueError."""

        def simple_factory():
            return MagicMock(spec=MockProtocol)

        descriptor = ServiceDescriptor(
            protocol=MockProtocol,
            factory=simple_factory,
            lifecycle=ServiceLifecycle.TRANSIENT,
            hot_reloadable=True,  # Invalid combination
        )

        with pytest.raises(ValueError) as exc_info:
            validate_service_descriptor(descriptor)

        assert "validation failed" in str(exc_info.value)
        assert "Hot-reloadable" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])
