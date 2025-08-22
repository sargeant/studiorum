"""Service access utilities for dependency injection migration.

This module provides utility functions to access services through the
dependency injection container, replacing the old global singleton pattern.

These functions provide a migration path from global singletons to proper
dependency injection while maintaining backward compatibility.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.config.unified_config import ApplicationConfig
    from studiorum.core.interfaces import ContentTypeRegistry

from .protocols import (
    CacheProtocol,
    ConfigurationProtocol,
    ContentTypeRegistryProtocol,
)

logger = get_logger(__name__)


def get_app_config_service() -> ConfigurationProtocol:
    """Get the application configuration service from the container.

    This replaces get_app_config() global singleton calls.

    Returns:
        Configuration service instance
    """
    try:
        from studiorum.core.container import get_global_container

        container = get_global_container()

        # Try to get the service synchronously if possible
        try:
            asyncio.get_running_loop()
            # In async context, caller should use await container.get_service() directly
            raise RuntimeError(
                "get_app_config_service() cannot be called from async context. "
                "Use 'await container.get_service(ConfigurationProtocol)' instead."
            )
        except RuntimeError:
            # No running loop, safe to create one
            service = asyncio.run(container.get_service(ConfigurationProtocol))  # type: ignore[type-abstract]
            return service

    except Exception as e:
        logger.warning(
            f"Failed to get configuration service, falling back to legacy: {e}"
        )
        # Fallback to legacy global singleton
        from studiorum.core.config.unified_config import get_app_config

        # Create a simple wrapper that implements the protocol
        class LegacyConfigWrapper:
            def __init__(self, config: ApplicationConfig) -> None:
                self._config = config

            def get_service_name(self) -> str:
                return "LegacyConfigWrapper"

            def get_config(self) -> ApplicationConfig:
                return self._config

            async def reload_config(self, new_config: ApplicationConfig) -> None:
                self._config = new_config

            def supports_hot_reload(self) -> bool:
                return False

            async def reload_from_source(self, source: str) -> object:
                return {"success": False, "error": "Not supported in legacy mode"}

            def validate_config(self) -> object:
                return {"success": True, "data": self._config}

        return LegacyConfigWrapper(get_app_config())  # type: ignore[return-value]


def get_app_config() -> ApplicationConfig:
    """Get the application configuration.

    This is a backward compatibility function that maintains the same
    interface as the old global singleton.

    Returns:
        Application configuration instance
    """
    config_service = get_app_config_service()
    return config_service.get_config()


def get_cache_service() -> CacheProtocol:
    """Get the cache service from the container.

    This replaces get_cache() global singleton calls.

    Returns:
        Cache service instance
    """
    try:
        from studiorum.core.container import get_global_container

        container = get_global_container()

        # Try to get the service synchronously if possible
        try:
            asyncio.get_running_loop()
            # In async context, caller should use await container.get_service() directly
            raise RuntimeError(
                "get_cache_service() cannot be called from async context. "
                "Use 'await container.get_service(CacheProtocol)' instead."
            )
        except RuntimeError:
            # No running loop, safe to create one
            return asyncio.run(container.get_service(CacheProtocol))  # type: ignore[type-abstract]

    except Exception as e:
        logger.warning(f"Failed to get cache service, falling back to legacy: {e}")
        # Fallback to legacy global singleton
        from studiorum.core.cache import get_cache

        # Create a simple wrapper that implements the protocol
        class LegacyCacheWrapper:
            def __init__(self) -> None:
                self._cache = get_cache()

            def get_service_name(self) -> str:
                return "LegacyCacheWrapper"

            def get(self, key: str, default: object = None) -> object:
                return self._cache.get(key, default)

            def set(self, key: str, value: object, expire: float | None = None) -> None:
                self._cache.set(key, value, expire=expire)

            def delete(self, key: str) -> bool:
                return self._cache.delete(key)

            def clear(self) -> None:
                self._cache.clear()

            def get_stats(self) -> dict[str, object]:
                # Legacy cache doesn't have stats
                return {"legacy_mode": True}

        return LegacyCacheWrapper()  # type: ignore[return-value]


def get_cache() -> object:
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
    """
    try:
        from studiorum.core.container import get_global_container

        container = get_global_container()

        # Try to get the service synchronously if possible
        try:
            asyncio.get_running_loop()
            # In async context, caller should use await container.get_service() directly
            raise RuntimeError(
                "get_content_type_registry_service() cannot be called from async context. "
                "Use 'await container.get_service(ContentTypeRegistryProtocol)' instead."
            )
        except RuntimeError:
            # No running loop, safe to create one
            return asyncio.run(container.get_service(ContentTypeRegistryProtocol))  # type: ignore[type-abstract]

    except Exception as e:
        logger.warning(
            f"Failed to get content type registry service, falling back to legacy: {e}"
        )
        # Fallback to legacy global singleton
        from studiorum.core.interfaces import get_content_type_registry

        # Create a simple wrapper that implements the protocol
        class LegacyRegistryWrapper:
            def __init__(self) -> None:
                self._registry = get_content_type_registry()

            def get_service_name(self) -> str:
                return "LegacyRegistryWrapper"

            def register_content_type(self, content_type: str, handler: type) -> None:
                # Legacy registry doesn't support string-based registration
                pass

            def get_content_handler(self, content_type: str) -> type | None:
                # Legacy registry doesn't provide handler lookup
                return None

            def get_registered_types(self) -> list[str]:
                # Return the content types from the legacy registry
                content_types = self._registry.get_all_types()
                return [ct.value for ct in content_types]

            def get_legacy_registry(self) -> ContentTypeRegistry:
                return self._registry

        return LegacyRegistryWrapper()  # type: ignore[return-value]


def get_content_type_registry() -> ContentTypeRegistry:
    """Get the content type registry instance.

    This is a backward compatibility function that maintains the same
    interface as the old global singleton.

    Returns:
        Content type registry instance
    """
    registry_service = get_content_type_registry_service()
    # Access the legacy registry through the service
    return registry_service.get_legacy_registry()  # type: ignore[return-value]


# Async service access functions for async contexts


async def get_app_config_service_async(
    container: object = None,
) -> ConfigurationProtocol:
    """Get the application configuration service from the container (async version).

    Args:
        container: Optional container instance. If None, uses global container.

    Returns:
        Configuration service instance
    """
    if container is None:
        from studiorum.core.container import get_global_container

        container = get_global_container()

    return await container.get_service(ConfigurationProtocol)  # type: ignore[attr-defined,type-abstract]


async def get_cache_service_async(container: object = None) -> CacheProtocol:
    """Get the cache service from the container (async version).

    Args:
        container: Optional container instance. If None, uses global container.

    Returns:
        Cache service instance
    """
    if container is None:
        from studiorum.core.container import get_global_container

        container = get_global_container()

    return await container.get_service(CacheProtocol)  # type: ignore[attr-defined,type-abstract]


async def get_content_type_registry_service_async(
    container: object = None,
) -> ContentTypeRegistryProtocol:
    """Get the content type registry service from the container (async version).

    Args:
        container: Optional container instance. If None, uses global container.

    Returns:
        Content type registry service instance
    """
    if container is None:
        from studiorum.core.container import get_global_container

        container = get_global_container()

    return await container.get_service(ContentTypeRegistryProtocol)  # type: ignore[attr-defined,type-abstract]
