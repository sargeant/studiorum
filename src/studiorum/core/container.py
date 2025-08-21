"""Dependency injection container for managing application services.

This module provides a centralized service container that manages the lifecycle
of core application components, replacing global singletons with proper
dependency injection.

This is now a minimal compatibility layer that delegates to the modern service container.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.services.container import ModernServiceContainer

from studiorum.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
    ServiceError,
)
from studiorum.core.result import Error, Result, Success

logger = get_logger(__name__)


# Global container instance
_global_container: ModernServiceContainer | None = None


def get_global_container() -> ModernServiceContainer:
    """Get the global service container instance.

    This provides a global container for CLI usage while still allowing
    dependency injection in tests and other contexts.

    Returns:
        The global service container instance
    """
    global _global_container
    if _global_container is None:
        from studiorum.core.services.container import ModernServiceContainer

        _global_container = ModernServiceContainer()
    return _global_container


def reset_global_container() -> None:
    """Reset the global service container for testing.

    This properly closes the existing container and creates a new one,
    ensuring complete cleanup of all cached services and their resources.
    Used primarily for test isolation.
    """
    global _global_container
    if _global_container is not None:
        try:
            # Try to clean up async container
            if hasattr(asyncio, "get_running_loop"):
                try:
                    loop = asyncio.get_running_loop()
                    # Schedule cleanup task
                    loop.create_task(_global_container.cleanup())
                except RuntimeError:
                    # No running loop, run cleanup synchronously
                    asyncio.run(_global_container.cleanup())
            else:
                asyncio.run(_global_container.cleanup())
        except Exception as e:
            logger.warning(f"Error during container cleanup: {e}")
    _global_container = None


def reset_all_services() -> None:
    """Reset all services managed by the container and other global state.

    This is a comprehensive reset function for tests that ensures complete
    isolation by resetting both container services and other global singletons.
    """
    reset_global_container()

    # Reset other global state that may not be in the container yet
    try:
        from studiorum.core.config.paths import reset_path_config

        reset_path_config()
    except ImportError:
        pass

    try:
        from studiorum.core.config.unified_config import reset_app_config

        reset_app_config()
    except ImportError:
        pass

    # Reset any other global state
    try:
        from studiorum.core.cache import get_cache

        # Try to reset cache if it has a reset method
        cache = get_cache()
        if hasattr(cache, "clear"):
            cache.clear()
    except (ImportError, AttributeError):
        # Cache system may not exist in all configurations
        pass


async def create_mcp_request_container(
    base_config: Any, request_overrides: dict | None = None
) -> Any:
    """Create MCP request container with configuration overrides.

    Args:
        base_config: Base application configuration
        request_overrides: Request-specific configuration overrides

    Returns:
        Request-scoped container with configuration overrides
    """
    from studiorum.core.services.container import (
        create_mcp_request_container as _create_mcp_container,
    )

    return await _create_mcp_container(base_config, request_overrides)


def reload_global_configuration() -> None:
    """Reload global configuration and recreate container."""
    reset_global_container()


def cleanup_global_container() -> None:
    """Clean up the global container."""
    reset_global_container()


@contextmanager
def service_container_for_testing() -> Iterator[ModernServiceContainer]:
    """Context manager that provides a fresh container for testing.

    This ensures test isolation by creating a new container instance
    and properly cleaning up afterward.

    Yields:
        A fresh service container instance
    """
    # Store current container
    global _global_container
    original_container = _global_container

    # Create fresh container
    from studiorum.core.services.container import ModernServiceContainer

    _global_container = ModernServiceContainer()

    try:
        yield _global_container
    finally:
        # Clean up test container
        if _global_container is not None:
            try:
                asyncio.run(_global_container.cleanup())
            except Exception as e:
                logger.warning(f"Error during test container cleanup: {e}")

        # Restore original container
        _global_container = original_container
