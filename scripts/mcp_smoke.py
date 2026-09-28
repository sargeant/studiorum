"""Start `studiorum mcp run --transport http` and call it as a client would.

Usage: uv run python scripts/mcp_smoke.py [--url URL]

Without --url it starts the server on a free local port with the current
config (STUDIORUM_CONFIG_FILE, else ~/.studiorum/config.yaml) and stops it
afterwards. With --url it only checks a server already running there. Exits
non-zero on the first failed check.
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fastmcp import Client

TOOLS = 13


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def _wait_for(port: int, server: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            sys.exit(f"FAIL server exited with {server.returncode} before listening")
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    sys.exit(f"FAIL server not listening after {timeout:g} s")


def _check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        sys.exit(1)


async def _smoke(url: str) -> None:
    async with Client(url) as client:
        tools = await client.list_tools()
        _check(len(tools) == TOOLS, f"tools/list: {len(tools)} tools")

        goblin = await client.call_tool(
            "get_content",
            {"content_type": "creature", "name": "Goblin", "source": "MM"},
        )
        data: dict[str, Any] = goblin.structured_content or {}
        _check("Goblin" in data.get("text", ""), "get_content: Goblin (MM)")

        spells = await client.call_tool(
            "search_spells", {"spell_class": "wizard", "level": 3, "limit": 1}
        )
        found: dict[str, Any] = spells.structured_content or {}
        _check(found.get("total", 0) > 0, "search_spells: wizard spells of level 3")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", help="check a running server's /mcp URL instead")
    parser.add_argument("--timeout", type=float, default=60, help="seconds to start")
    args = parser.parse_args()

    if args.url:
        asyncio.run(_smoke(args.url))
        return

    port = _free_port()
    server = subprocess.Popen(  # noqa: S603 - our own CLI, fixed arguments
        [
            str(Path(sys.executable).with_name("studiorum")),
            "mcp",
            "run",
            "--transport",
            "http",
            "--port",
            str(port),
            "--all-content",
        ]
    )
    try:
        _wait_for(port, server, args.timeout)
        asyncio.run(_smoke(f"http://127.0.0.1:{port}/mcp"))
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    main()
