"""One log record per MCP request: method, tool, status, duration, session and client."""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any

from fastmcp.exceptions import FastMCPError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from pydantic import ValidationError

from studiorum.log import get_logger

logger = get_logger(__name__)


def client_ip(header: str | None) -> str | None:
    """The trusted header's value if set and present, else the TCP peer; None over stdio."""
    try:
        request = get_http_request()
    except RuntimeError:
        return None
    if header and (value := request.headers.get(header)):
        return value.strip()
    return request.client.host if request.client else None


class RequestLog(Middleware):
    """Logs each request once it finishes; a bad call is INFO, a crash ERROR.

    ``client_ip_header`` names a header the proxy in front sets and a client
    can't (Cloudflare's CF-Connecting-IP); without it the TCP peer is logged.
    """

    def __init__(self, client_ip_header: str | None = None) -> None:
        self.client_ip_header = client_ip_header

    async def on_request(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        fields: dict[str, Any] = {"method": context.method}
        tool = getattr(context.message, "name", None)
        if context.method == "tools/call" and tool:
            fields["tool"] = tool
        if context.fastmcp_context is not None:
            with contextlib.suppress(RuntimeError):
                fields["session"] = context.fastmcp_context.session_id
        if (ip := client_ip(self.client_ip_header)) is not None:
            fields["client_ip"] = ip

        message = " ".join(str(v) for v in (context.method, fields.get("tool")) if v)
        start = time.perf_counter()
        try:
            result = await call_next(context)
        except (FastMCPError, ValidationError) as e:
            self._log(logging.INFO, message, fields, start, "error", str(e))
            raise
        except Exception as e:
            self._log(logging.ERROR, message, fields, start, "failed", repr(e))
            raise
        self._log(logging.INFO, message, fields, start, "ok")
        return result

    @staticmethod
    def _log(
        level: int,
        message: str,
        fields: dict[str, Any],
        start: float,
        status: str,
        error: str | None = None,
    ) -> None:
        extra = {
            **fields,
            "status": status,
            "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        }
        if error is not None:
            extra["error"] = error
        logger.log(level, message, extra=extra)
