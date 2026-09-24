"""MCP tools reach the data set through one Services per process."""

import pytest
from fastmcp import Client

from studiorum.mcp.context import get_mcp_services
from studiorum.mcp.server import mcp


@pytest.mark.asyncio
async def test_tools_share_one_loaded_services() -> None:
    async with Client(mcp) as client:
        books = await client.call_tool("list_books", {})
        creatures = await client.call_tool("search_creatures", {"query": "Goblin"})

    assert not books.is_error
    assert "Test Sourcebook" in books.content[0].text
    assert not creatures.is_error
    assert get_mcp_services() is get_mcp_services()
