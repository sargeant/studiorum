"""Service access utilities for dependency injection migration.

This module provides utility functions to access services through the
dependency injection container, replacing the old global singleton pattern.

These functions provide a migration path from global singletons to proper
dependency injection while maintaining backward compatibility.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success

if TYPE_CHECKING:
    from studiorum.core.config.unified_config import ApplicationConfig
    from studiorum.core.interfaces import ContentTypeRegistry
    from studiorum.core.services.container import ServiceContainer

from .protocols import (
    CacheProtocol,
    ConfigurationProtocol,
    ContentTypeRegistryProtocol,
)

logger = get_logger(__name__)


def get_app_config() -> ApplicationConfig:
    """Get application configuration for CLI and synchronous contexts.

    WARNING: Cannot be called from async contexts. For MCP and async code,
    use AsyncRequestContext.get_service(ConfigurationProtocol) instead.

    This function maintains backward compatibility while using the modern
    service container architecture internally.

    Returns:
        Application configuration instance

    Raises:
        RuntimeError: If called from async context
    """
    # Check async context to provide helpful error message
    # Allow bypass for test environments
    import os

    if not os.getenv("PYTEST_CURRENT_TEST"):
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "get_app_config() cannot be called from async context. "
                "Use AsyncRequestContext.get_service(ConfigurationProtocol) instead."
            )
        except RuntimeError as e:
            if "get_app_config" in str(e):
                raise

    # Direct container access - eliminate bridge function
    from studiorum.core.container import get_global_container

    container = get_global_container()
    config_service = container.get_service_sync(ConfigurationProtocol)  # type: ignore[type-abstract]
    return config_service.get_config()


def get_cache_service() -> CacheProtocol:
    """Get the cache service from the container.

    This replaces get_cache() global singleton calls.

    Returns:
        Cache service instance

    Raises:
        RuntimeError: If called from async context
        ServiceNotRegisteredError: If service not registered
    """
    # Check if we're in an async context
    # Allow bypass for test environments
    import os

    if not os.getenv("PYTEST_CURRENT_TEST"):
        try:
            asyncio.get_running_loop()
            # In async context, caller should use await container.get_service() directly
            raise RuntimeError(
                "get_cache_service() cannot be called from async context. "
                "Use 'await container.get_service(CacheProtocol)' instead."
            )
        except RuntimeError as e:
            # Re-raise if it's our error message
            if "get_cache_service" in str(e):
                raise

    # Get service from container using modern sync access
    from studiorum.core.container import get_global_container

    container = get_global_container()
    return container.get_service_sync(CacheProtocol)  # type: ignore[type-abstract]


def get_cache() -> CacheProtocol:
    """Get the cache instance.

    This is a backward compatibility function that maintains the same
    interface as the old global singleton, but returns the service protocol.

    Returns:
        Cache service that can be used like the old cache
    """
    return get_cache_service()


def get_content_type_registry_service() -> ContentTypeRegistryProtocol:
    """Get the content type registry service from the container.

    This replaces get_content_type_registry() global singleton calls.

    Returns:
        Content type registry service instance

    Raises:
        RuntimeError: If called from async context
        ServiceNotRegisteredError: If service not registered
    """
    # Check if we're in an async context
    # Allow bypass for test environments
    import os

    if not os.getenv("PYTEST_CURRENT_TEST"):
        try:
            asyncio.get_running_loop()
            # In async context, caller should use await container.get_service() directly
            raise RuntimeError(
                "get_content_type_registry_service() cannot be called from async context. "
                "Use 'await container.get_service(ContentTypeRegistryProtocol)' instead."
            )
        except RuntimeError as e:
            # Re-raise if it's our error message
            if "get_content_type_registry_service" in str(e):
                raise

    # Get service from container using modern sync access
    from studiorum.core.container import get_global_container

    container = get_global_container()
    return container.get_service_sync(ContentTypeRegistryProtocol)  # type: ignore[type-abstract]


def get_content_type_registry() -> ContentTypeRegistry:
    """Get the content type registry instance.

    This is a backward compatibility function that maintains the same
    interface as the old global singleton.

    Returns:
        Content type registry instance
    """
    registry_service = get_content_type_registry_service()
    # Access the legacy registry through the service
    return registry_service.get_legacy_registry()


# NOTE: Async configuration access should use AsyncRequestContext.get_service(Protocol)
# instead of standalone async wrapper functions. This provides proper request
# isolation and follows the established MCP architecture patterns.
