#!/usr/bin/env python3
"""
Simple MCP test that maintains a persistent connection.
"""

import json
import subprocess
import sys


def test_mcp_session():
    """Test MCP with persistent session."""
    print("🎲 Testing MCP with persistent session...")

    # Start the MCP server process
    process = subprocess.Popen(
        ["uv", "run", "python", "-m", "dnd5e.cli.main", "mcp", "run"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,  # Unbuffered
    )

    def send_request(request):
        """Send a request and get response."""
        request_str = json.dumps(request) + "\n"
        process.stdin.write(request_str)
        process.stdin.flush()

        # Read response line
        response_line = process.stdout.readline()
        try:
            return json.loads(response_line.strip())
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON: {response_line}"}

    try:
        # 1. Initialize
        print("1. Initializing...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        init_response = send_request(init_request)
        if "result" in init_response:
            print(f"✅ Initialized: {init_response['result']['serverInfo']['name']}")
        else:
            print(f"❌ Initialization failed: {init_response}")
            return False

        # 2. List tools
        print("2. Listing tools...")
        tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        tools_response = send_request(tools_request)
        if "result" in tools_response:
            tools = tools_response["result"]["tools"]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools[:3]:
                print(f"   • {tool['name']}")
            if len(tools) > 3:
                print(f"   ... and {len(tools) - 3} more")
        else:
            print(f"❌ Tools list failed: {tools_response}")
            return False

        # 3. Test a tool call - search spells
        print("3. Testing spell search...")
        search_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "search_spells", "arguments": {"query": "fireball"}},
        }

        search_response = send_request(search_request)
        if "result" in search_response:
            print("✅ Spell search successful!")
            content = search_response["result"]["content"]
            if content and len(content) > 0:
                try:
                    result_text = content[0]["text"]
                    result_data = json.loads(result_text)
                    spells = result_data.get("content", [])
                    print(f"   Found {len(spells)} spells")
                    if spells:
                        first_spell = spells[0]
                        print(
                            f"   First: {first_spell.get('name', 'Unknown')} (Level {first_spell.get('level', '?')})"
                        )

                    # Check performance
                    performance = result_data.get("performance", {})
                    if performance:
                        duration = performance.get("duration_ms", 0)
                        target_met = performance.get("target_met", False)
                        print(
                            f"   Performance: {duration:.1f}ms (Target met: {target_met})"
                        )

                except json.JSONDecodeError:
                    print(f"   Raw response: {result_text[:100]}...")
        else:
            print(f"❌ Spell search failed: {search_response}")

        return True

    finally:
        # Clean up
        process.terminate()
        process.wait()


if __name__ == "__main__":
    success = test_mcp_session()
    print("\n" + "=" * 50)
    if success:
        print("🎉 MCP testing completed successfully!")
    else:
        print("❌ MCP testing failed")
    sys.exit(0 if success else 1)
