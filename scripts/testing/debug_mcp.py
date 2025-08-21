#!/usr/bin/env python3
"""
Debug MCP requests to see what's expected.
"""

import json
import subprocess


def test_different_requests():
    """Try different request formats."""

    process = subprocess.Popen(
        ["uv", "run", "python", "-m", "dnd5e.cli.main", "mcp", "run"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
    )

    def send_request(request):
        request_str = json.dumps(request) + "\n"
        process.stdin.write(request_str)
        process.stdin.flush()
        response_line = process.stdout.readline()
        try:
            return json.loads(response_line.strip())
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON: {response_line}"}

    try:
        # Initialize first
        init_response = send_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
            }
        )
        print(
            "Init:",
            init_response.get("result", {}).get("serverInfo", {}).get("name", "failed"),
        )

        # Try tools/list with empty params
        response1 = send_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        print(
            "tools/list with empty params:",
            response1.get("error", response1.get("result", "success")),
        )

        # Try tools/list with no params at all
        response2 = send_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        print(
            "tools/list with no params:",
            response2.get("error", response2.get("result", "success")),
        )

        # Try just "list" method
        response3 = send_request(
            {"jsonrpc": "2.0", "id": 4, "method": "list", "params": {}}
        )
        print(
            "list method:", response3.get("error", response3.get("result", "success"))
        )

        # Check what methods are available by looking at server capabilities
        capabilities = init_response.get("result", {}).get("capabilities", {})
        print("Server capabilities:", capabilities)

    finally:
        process.terminate()


if __name__ == "__main__":
    test_different_requests()
