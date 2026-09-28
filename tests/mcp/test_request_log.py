"""The request log: one record per MCP request, with the client from a trusted header."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from studiorum.mcp import request_log
from studiorum.mcp.server import mcp

pytestmark = pytest.mark.usefixtures("mcp_data")


def _records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "studiorum.mcp.request_log"]


@pytest.mark.asyncio
async def test_each_request_is_one_record(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    async with Client(mcp) as client:
        await client.call_tool("search_spells", {"query": "fire"})
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_content", {"content_type": "creature", "name": "Nobody"}
            )

    calls: list[Any] = [
        r for r in _records(caplog) if r.getMessage().startswith("tools/call")
    ]
    assert [(r.getMessage(), r.status) for r in calls] == [
        ("tools/call search_spells", "ok"),
        ("tools/call get_content", "error"),
    ]
    assert calls[1].levelno == logging.INFO
    assert "No creature named 'Nobody'" in calls[1].error
    assert all(r.duration_ms >= 0 for r in calls)


@pytest.mark.asyncio
async def test_a_bad_call_is_not_an_error_from_fastmcp(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_content", {"content_type": "creature", "name": "Nobody"}
            )

    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def _request(headers: dict[str, str], host: str = "10.0.0.5") -> SimpleNamespace:
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))


def test_the_trusted_header_wins_over_the_peer() -> None:
    request = _request({"CF-Connecting-IP": "203.0.113.7"})
    with patch.object(request_log, "get_http_request", return_value=request):
        assert request_log.client_ip("CF-Connecting-IP") == "203.0.113.7"
        assert request_log.client_ip(None) == "10.0.0.5"


def test_without_the_header_the_peer_is_logged() -> None:
    request = _request({"X-Forwarded-For": "198.51.100.1"})
    with patch.object(request_log, "get_http_request", return_value=request):
        assert request_log.client_ip("CF-Connecting-IP") == "10.0.0.5"


def test_stdio_has_no_client_ip() -> None:
    with patch.object(request_log, "get_http_request", side_effect=RuntimeError):
        assert request_log.client_ip("CF-Connecting-IP") is None
