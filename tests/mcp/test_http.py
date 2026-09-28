"""What an HTTP deployment sees: the health route and the tools' annotations."""

from __future__ import annotations

import pytest
from fastmcp import Client
from starlette.testclient import TestClient

from studiorum.mcp.server import mcp

pytestmark = pytest.mark.usefixtures("mcp_data")


def test_healthz_answers_once_the_data_has_loaded() -> None:
    with TestClient(mcp.http_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.text == "ok"


@pytest.mark.asyncio
async def test_every_tool_is_read_only_and_idempotent() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

    for tool in tools:
        assert tool.annotations is not None, tool.name
        assert tool.annotations.readOnlyHint, tool.name
        assert tool.annotations.idempotentHint, tool.name
        assert tool.annotations.openWorldHint is False, tool.name
