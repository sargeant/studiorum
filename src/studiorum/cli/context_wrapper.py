"""CLI context wrapper and decorators for async-safe request context integration.

This module provides decorators and utilities for integrating async request contexts
with existing CLI commands while maintaining backward compatibility and async safety.

Key Features:
- @with_request_context decorator for automatic context injection
- Async-safe context management for CLI commands
- Zero breaking changes for existing CLI code
- Performance optimization through context reuse
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from ..core.config.unified_config import ApplicationConfig

from ..core.context import RequestContext, create_sync_request_context
from ..core.error_types import ErrorCategory, MCPError, MCPErrorCode
from ..core.exceptions import DnD5eError

logger = get_logger(__name__)


def with_request_context[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to add request context to CLI commands.

    This decorator automatically injects a request context into CLI commands,
    enabling them to use context-aware services while maintaining backward
    compatibility with existing code.

    The decorator:
    1. Creates a request context for the CLI command
    2. Injects it as a 'ctx' parameter
    3. Handles context cleanup automatically
    4. Preserves async safety for nested operations

    Args:
        func: CLI command function to wrap

    Returns:
        Wrapped function with automatic context injection

    Examples:
        @app.command()
        @with_request_context
        def convert_adventure(
            adventure_name: str,
            output: str = "output.tex",
            ctx: RequestContext = None  # Injected by decorator
        ):
            result = ContextualAPI.resolve_adventure(adventure_name)
            # ... rest of command
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Check if context already provided (for nested calls or testing)
        if "ctx" in kwargs and kwargs["ctx"] is not None:
            return func(*args, **kwargs)

        # Get configuration for context
        try:
            from ..core.config.unified_config import get_app_config

            config = get_app_config()  # Use existing global config for CLI
        except Exception as e:
            logger.warning(f"Failed to get app config for context: {e}")
            config = None

        # Create context for CLI command
        with create_sync_request_context(config_override=config) as ctx:
            kwargs["ctx"] = ctx
            try:
                result = func(*args, **kwargs)

                # Check for errors in context and log them
                if ctx.has_errors():
                    logger.warning(
                        f"CLI command completed with {len(ctx.get_errors())} errors"
                    )
                    for error in ctx.get_errors():
                        logger.error(f"Context error: {error.message}")

                return result
            except Exception as e:
                # Add exception to context for error tracking
                error = MCPError(
                    message=f"CLI command failed: {e}",
                    error_code=MCPErrorCode.INTERNAL_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                )
                ctx.add_error(error)
                raise

    return wrapper


def with_async_request_context[**P, T](
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """Decorator for async CLI commands that need request context.

    This decorator is for CLI commands that are defined as async functions
    and need access to async request contexts.

    Args:
        func: Async CLI command function to wrap

    Returns:
        Wrapped async function with automatic context injection
    """

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Check if context already provided
        if "ctx" in kwargs and kwargs["ctx"] is not None:
            return await func(*args, **kwargs)

        # Import here to avoid circular imports
        from ..core.context import async_request_context

        # Get configuration for context
        try:
            from ..core.config.unified_config import get_app_config

            config = get_app_config()
        except Exception as e:
            logger.warning(f"Failed to get app config for async context: {e}")
            config = None

        # Create async context for CLI command
        async with async_request_context(config_override=config) as ctx:
            kwargs["ctx"] = ctx
            try:
                result = await func(*args, **kwargs)

                # Check for errors in context
                if ctx.has_errors():
                    logger.warning(
                        f"Async CLI command completed with {len(ctx.get_errors())} errors"
                    )
                    for error in ctx.get_errors():
                        logger.error(f"Context error: {error.message}")

                return result
            except Exception as e:
                # Add exception to context for error tracking
                error = MCPError(
                    message=f"Async CLI command failed: {e}",
                    error_code=MCPErrorCode.INTERNAL_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                )
                await ctx.add_async_error(error)
                raise

    return async_wrapper


def with_performance_context[**P, T](
    enable_monitoring: bool = True, log_metrics: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for CLI commands that need performance monitoring.

    This decorator wraps CLI commands with performance-monitored request
    contexts for detailed performance analysis.

    Args:
        enable_monitoring: Whether to enable performance monitoring
        log_metrics: Whether to log performance metrics after completion

    Returns:
        Decorator function
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check if context already provided
            if "ctx" in kwargs and kwargs["ctx"] is not None:
                return func(*args, **kwargs)

            # Import here to avoid circular imports
            from ..core.context import performance_monitored_context

            # Get configuration for context
            try:
                from ..core.config.unified_config import get_app_config

                config = get_app_config()
            except Exception as e:
                logger.warning(f"Failed to get app config for performance context: {e}")
                config = None

            # Create performance-monitored context
            async def run_with_performance_context() -> T:
                async with performance_monitored_context(
                    config_override=config,
                    performance_tracking=enable_monitoring,
                ) as ctx:
                    # Convert to sync context for CLI compatibility
                    from ..core.context import RequestContext

                    sync_ctx = RequestContext(ctx)
                    kwargs["ctx"] = sync_ctx

                    try:
                        result = func(*args, **kwargs)

                        # Log performance metrics if enabled
                        if log_metrics and ctx.metrics:
                            logger.debug(
                                f"Performance metrics for {func.__name__}: {ctx.metrics}"
                            )

                        return result
                    except Exception as e:
                        error = MCPError(
                            message=f"Performance-monitored CLI command failed: {e}",
                            error_code=MCPErrorCode.INTERNAL_ERROR,
                            category=ErrorCategory.SYSTEM_ERROR,
                        )
                        await ctx.add_async_error(error)
                        raise

            # Run async context in sync environment
            return asyncio.run(run_with_performance_context())

        return wrapper

    return decorator


class CLIContextManager:
    """Context manager for CLI commands that need manual context control.

    This class provides manual context management for CLI commands that need
    more control over context lifecycle or want to share contexts across
    multiple operations.

    Examples:
        with CLIContextManager() as ctx_mgr:
            ctx = ctx_mgr.get_context()
            result1 = some_operation(ctx=ctx)
            result2 = another_operation(ctx=ctx)
            # Context is automatically cleaned up
    """

    def __init__(
        self,
        config_override: ApplicationConfig | None = None,
        enable_performance_monitoring: bool = False,
    ):
        """Initialize CLI context manager.

        Args:
            config_override: Optional configuration override
            enable_performance_monitoring: Whether to enable performance tracking
        """
        self.config_override = config_override
        self.enable_performance_monitoring = enable_performance_monitoring
        self._context: RequestContext | None = None

    def __enter__(self) -> CLIContextManager:
        """Enter context manager and create request context."""
        # Get configuration if not provided
        if self.config_override is None:
            try:
                from ..core.config.unified_config import get_app_config

                self.config_override = get_app_config()
            except Exception as e:
                logger.warning(f"Failed to get app config for CLI context manager: {e}")

        # Create appropriate context
        self._context = create_sync_request_context(
            config_override=self.config_override
        )
        self._context.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context manager and clean up context."""
        if self._context:
            self._context.__exit__(exc_type, exc_val, exc_tb)

            # Log any errors that occurred
            if self._context.has_errors():
                logger.warning(
                    f"CLI context completed with {len(self._context.get_errors())} errors"
                )
                for error in self._context.get_errors():
                    logger.error(f"Context error: {error.message}")

    def get_context(self) -> RequestContext:
        """Get the managed request context.

        Returns:
            Active request context

        Raises:
            RuntimeError: If called outside context manager
        """
        if self._context is None:
            raise RuntimeError("CLIContextManager must be used as a context manager")
        return self._context


# Utility functions for CLI integration


def create_cli_context(
    config_override: ApplicationConfig | None = None,
) -> RequestContext:
    """Create a request context suitable for CLI usage.

    Args:
        config_override: Optional configuration override

    Returns:
        RequestContext ready for CLI usage
    """
    if config_override is None:
        try:
            from ..core.config.unified_config import get_app_config

            config_override = get_app_config()
        except Exception as e:
            logger.warning(f"Failed to get app config for CLI context: {e}")

    return create_sync_request_context(config_override=config_override)


def ensure_context_in_kwargs(kwargs: dict[str, Any]) -> RequestContext:
    """Ensure kwargs has a request context, creating one if needed.

    This utility function checks if kwargs contains a 'ctx' parameter
    and creates one if it doesn't exist.

    Args:
        kwargs: Keyword arguments dictionary to check/modify

    Returns:
        The request context (existing or newly created)
    """
    if "ctx" not in kwargs or kwargs["ctx"] is None:
        kwargs["ctx"] = create_cli_context()
    return cast(RequestContext, kwargs["ctx"])
