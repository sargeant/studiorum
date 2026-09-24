"""Per-request state for MCP tools, over Services built once per process.

This is the minimum that keeps the current tools working without the service
container. Restructure step 9 replaces it with a FastMCP lifespan and
``Depends``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from studiorum.core.config.unified_config import ApplicationConfig, get_app_config
from studiorum.core.error_types import MCPError
from studiorum.core.logging import get_logger
from studiorum.services import Services, build_services

logger = get_logger(__name__)

_services: Services | None = None


def get_mcp_services() -> Services:
    """The process-wide Services, built on first use from get_app_config()."""
    global _services
    if _services is None:
        _services = build_services(get_app_config())
    return _services


def reset_mcp_services() -> None:
    """Forget the process-wide Services (for tests)."""
    global _services
    _services = None


class RequestMetrics(BaseModel):
    """Counters a request collects for its response metadata."""

    service_access_count: dict[str, int] = Field(default_factory=dict)
    async_operations_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_peak_mb: float | None = None


class AsyncRequestContext:
    """One MCP request: its Services, sources filter, errors and metrics.

    A request with ``user_config`` gets Services built for that configuration;
    every other request shares the process-wide Services.
    """

    def __init__(
        self,
        user_config: ApplicationConfig | None = None,
        sources: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.user_config = user_config
        self.sources: list[str] = sources if sources is not None else []
        self.metadata: dict[str, Any] = metadata if metadata is not None else {}
        self.request_id: UUID = uuid4()
        self.started_at = datetime.now()
        self.finished_at: datetime | None = None
        self.metrics = RequestMetrics()
        self._errors: list[MCPError] = []
        self._services: Services | None = None

    @property
    def services(self) -> Services:
        if self._services is None:
            self._services = (
                build_services(self.user_config)
                if self.user_config is not None
                else get_mcp_services()
            )
        return self._services

    async def __aenter__(self) -> AsyncRequestContext:
        # Load in a worker thread: the source managers only build their index
        # synchronously when no event loop is running, and it keeps the loop free.
        await asyncio.to_thread(self.services.load_omnidexer)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()
        if exc_type:
            logger.error(
                f"Request {self.request_id} failed: {exc_type.__name__}: {exc_val}"
            )

    def close(self) -> None:
        if self.finished_at is None:
            self.finished_at = datetime.now()
            logger.debug(f"Request {self.request_id} completed in {self.duration_ms}ms")

    @property
    def is_closed(self) -> bool:
        return self.finished_at is not None

    @property
    def duration_ms(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds() * 1000

    def add_error(self, error: MCPError) -> None:
        self._errors.append(error)
        logger.warning(f"Request {self.request_id} error: {error.message}")

    async def add_async_error(self, error: MCPError) -> None:
        self.add_error(error)

    def has_errors(self) -> bool:
        return bool(self._errors)

    def get_errors(self) -> list[MCPError]:
        return self._errors.copy()

    def clear_errors(self) -> None:
        self._errors.clear()

    def record_cache_hit(self) -> None:
        self.metrics.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.metrics.cache_misses += 1

    def record_async_operation(self) -> None:
        self.metrics.async_operations_count += 1


@asynccontextmanager
async def async_request_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncIterator[AsyncRequestContext]:
    """Context for one MCP request."""
    async with AsyncRequestContext(
        user_config=config_override, sources=sources or [], metadata=metadata or {}
    ) as context:
        yield context


@asynccontextmanager
async def performance_monitored_context(
    config_override: ApplicationConfig | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    enable_hot_reload: bool = False,
    performance_tracking: bool = True,
) -> AsyncIterator[AsyncRequestContext]:
    """async_request_context() that logs the request's metrics on exit."""
    async with async_request_context(config_override, sources, metadata) as context:
        if performance_tracking:
            context.metadata["performance_tracking"] = True
        if enable_hot_reload and config_override:
            context.metadata["hot_reload_enabled"] = True
        try:
            yield context
        finally:
            if performance_tracking:
                logger.debug(
                    f"Request {context.request_id} performance metrics: {context.metrics}"
                )
