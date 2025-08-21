"""
Async/sync bridge utilities for CLI commands.

This module provides utilities to bridge between the async ModernServiceContainer
and the synchronous CLI command interface, maintaining backward compatibility
while leveraging the modern async service infrastructure.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.logging import get_logger
from studiorum.core.services.container import ModernServiceContainer
from studiorum.core.services.protocols import OmnidexerProtocol, TagResolverProtocol
from studiorum.core.services.registration import register_modern_services
from studiorum.core.text.tag_resolver import TagResolver

logger = get_logger(__name__)

T = TypeVar("T")

# Global async container instance for CLI usage
_global_async_container: ModernServiceContainer | None = None
_container_initialization_lock = asyncio.Lock()


async def _initialize_global_async_container() -> ModernServiceContainer:
    """Initialize the global async service container."""
    global _global_async_container

    async with _container_initialization_lock:
        if _global_async_container is None:
            logger.debug("Initializing global async service container for CLI")

            # Create modern container
            container = ModernServiceContainer()

            # Register all services
            await register_modern_services(container)

            _global_async_container = container
            logger.info("Global async service container initialized")

    return _global_async_container


async def _get_global_async_container() -> ModernServiceContainer:
    """Get the global async service container, initializing if needed."""
    if _global_async_container is None:
        return await _initialize_global_async_container()
    return _global_async_container


def run_async[T](coro: Awaitable[T]) -> T:
    """Run an async coroutine in a sync context, handling event loop management.

    This function provides a safe way to run async code from sync CLI commands,
    handling various event loop scenarios:
    - No event loop: creates new loop and runs
    - Event loop running: runs in thread pool to avoid blocking
    - Event loop not running: uses existing loop

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of the coroutine execution
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()

        if loop.is_running():
            # We're already in an async context, need to run in a thread
            import concurrent.futures

            def run_in_thread() -> T:
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=30)
        else:
            # Safe to run in current loop
            return loop.run_until_complete(coro)

    except RuntimeError:
        # No event loop, create one
        # Convert Awaitable to Coroutine if needed
        import inspect

        if inspect.iscoroutine(coro):
            return asyncio.run(coro)  # type: ignore[return-value,no-any-return]
        else:
            # If it's not a coroutine, try to await it in a new loop
            async def wrapper() -> T:
                return await coro

            return asyncio.run(wrapper())


def get_omnidexer_sync() -> Omnidexer:
    """Get omnidexer instance synchronously from async container.

    This function bridges the async service container to provide a sync interface
    for CLI commands, maintaining backward compatibility.

    Returns:
        Omnidexer instance

    Raises:
        RuntimeError: If omnidexer cannot be retrieved
    """

    async def _get_omnidexer() -> Omnidexer:
        container = await _get_global_async_container()
        omnidexer: Omnidexer = await container.get_service(
            cast(type, OmnidexerProtocol)
        )
        # The protocol should return an Omnidexer instance
        assert isinstance(omnidexer, Omnidexer), (
            "Service container should return Omnidexer instance"
        )
        return omnidexer

    try:
        return run_async(_get_omnidexer())
    except Exception as e:
        raise RuntimeError(f"Failed to get omnidexer: {e}") from e


def get_tag_resolver_sync() -> TagResolver:
    """Get tag resolver instance synchronously from async container.

    This function bridges the async service container to provide a sync interface
    for CLI commands, maintaining backward compatibility.

    Returns:
        TagResolver instance

    Raises:
        RuntimeError: If tag resolver cannot be retrieved
    """

    async def _get_tag_resolver() -> TagResolver:
        container = await _get_global_async_container()
        tag_resolver: TagResolver = await container.get_service(
            cast(type, TagResolverProtocol)
        )
        # The protocol should return a TagResolver instance
        assert isinstance(tag_resolver, TagResolver), (
            "Service container should return TagResolver instance"
        )
        return tag_resolver

    try:
        return run_async(_get_tag_resolver())
    except Exception as e:
        raise RuntimeError(f"Failed to get tag resolver: {e}") from e


def reset_global_async_container() -> None:
    """Reset the global async container for testing.

    This function properly cleans up the existing async container and resets
    the global state, ensuring complete test isolation.
    """
    global _global_async_container

    if _global_async_container is not None:
        # Clean up the container asynchronously
        async def _cleanup() -> None:
            if _global_async_container is not None:
                await _global_async_container.cleanup()

        try:
            run_async(_cleanup())
        except Exception as e:
            logger.warning(f"Failed to cleanup global async container: {e}")
        finally:
            _global_async_container = None
            logger.debug("Global async container reset")


async def create_cli_request_container() -> Any:
    """Create a request-scoped container for CLI operations.

    This is useful for operations that need isolated service instances,
    such as handling multiple concurrent operations or testing scenarios.

    Returns:
        Request-scoped container with async context manager support
    """
    global_container = await _get_global_async_container()
    request_container = await global_container.create_request_scope()
    return request_container


def with_request_scope[T](
    func: Callable[[ModernServiceContainer], T],
) -> Callable[[], T]:
    """Decorator to run a function with a request-scoped container.

    This provides a convenient way to run CLI operations with isolated
    service instances, useful for testing or operations that should not
    affect global state.

    Args:
        func: Function that takes a ModernServiceContainer and returns T

    Returns:
        Decorated function that creates request scope automatically
    """

    def wrapper() -> T:
        async def _run_with_scope() -> T:
            async with await create_cli_request_container() as container:
                return func(container)

        return run_async(_run_with_scope())

    return wrapper
