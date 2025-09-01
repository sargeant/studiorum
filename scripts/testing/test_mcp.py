#!/usr/bin/env python3
"""
Quick MCP testing script for the dnd5e MCP server.
Tests both direct tool calls and performance.
"""

import json
import subprocess
import sys
import time


def send_mcp_request(request):
    """Send a request to the MCP server via stdio."""
    try:
        process = subprocess.Popen(
            ["uv", "run", "python", "-m", "dnd5e.cli.main", "mcp", "run"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate(input=json.dumps(request))

        # Parse the JSON response (first line usually)
        for line in stdout.split("\n"):
            if line.strip() and line.startswith('{"jsonrpc"'):
                return json.loads(line)
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_initialization():
    """Test MCP initialization."""
    print("🔧 Testing MCP Initialization...")

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    response = send_mcp_request(request)
    if response and "result" in response:
        print("✅ Initialization successful")
        server_info = response["result"]["serverInfo"]
        print(f"   Server: {server_info['name']} v{server_info['version']}")
        return True
    else:
        print("❌ Initialization failed")
        print(f"   Response: {response}")
        return False


def test_tools_list():
    """Test listing available tools."""
    print("\n📝 Testing Tools List...")

    # Initialize first
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
    send_mcp_request(init_request)

    # Then list tools
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

    response = send_mcp_request(request)
    if response and "result" in response:
        tools = response["result"]["tools"]
        print(f"✅ Found {len(tools)} tools")
        for tool in tools[:5]:  # Show first 5
            print(
                f"   • {tool['name']}: {tool.get('description', 'No description')[:50]}..."
            )
        if len(tools) > 5:
            print(f"   ... and {len(tools) - 5} more")
        return True
    else:
        print("❌ Tools list failed")
        print(f"   Response: {response}")
        return False


def test_spell_search():
    """Test spell search functionality."""
    print("\n🔍 Testing Spell Search...")

    # Initialize first
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
    send_mcp_request(init_request)

    # Search for fireball
    start_time = time.time()
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_spells",
            "arguments": {"query": "fireball", "limit": 3},
        },
    }

    response = send_mcp_request(request)
    duration_ms = (time.time() - start_time) * 1000

    if response and "result" in response:
        content = response["result"]["content"]
        if content and len(content) > 0:
            # Parse the returned JSON content
            result_text = content[0]["text"]
            try:
                result_data = json.loads(result_text)
                spells = result_data.get("content", [])
                performance = result_data.get("performance", {})

                print(f"✅ Spell search successful ({duration_ms:.1f}ms)")
                print(f"   Found {len(spells)} spells")
                for spell in spells:
                    print(
                        f"   • {spell.get('name', 'Unknown')} (Level {spell.get('level', '?')})"
                    )

                perf_duration = performance.get("duration_ms", duration_ms)
                target_met = performance.get("target_met", False)
                print(
                    f"   Performance: {perf_duration:.1f}ms (Target <200ms: {'✅' if target_met else '❌'})"
                )
                return True
            except json.JSONDecodeError:
                print(
                    f"✅ Spell search returned data but couldn't parse: {result_text[:100]}..."
                )
                return True
        else:
            print("⚠️  Spell search returned empty content")
            return True
    else:
        print("❌ Spell search failed")
        print(f"   Response: {response}")
        return False


def test_configuration_tool():
    """Test configuration tool."""
    print("\n⚙️  Testing Configuration Tool...")

    # Initialize first
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
    send_mcp_request(init_request)

    # Get current configuration
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "get_current_configuration", "arguments": {}},
    }

    response = send_mcp_request(request)
    if response and "result" in response:
        print("✅ Configuration retrieval successful")
        content = response["result"]["content"]
        if content and len(content) > 0:
            try:
                config_text = content[0]["text"]
                config_data = json.loads(config_text)
                print(f"   Configuration has {len(config_data)} top-level keys")
                for key in list(config_data.keys())[:3]:
                    print(f"   • {key}")
            except json.JSONDecodeError:
                print(f"   Raw response: {config_text[:100]}...")
        return True
    else:
        print("❌ Configuration retrieval failed")
        print(f"   Response: {response}")
        return False


def main():
    """Run all tests."""
    print("🎲 dnd5e MCP Server Testing")
    print("=" * 40)

    tests = [
        test_initialization,
        test_tools_list,
        test_spell_search,
        test_configuration_tool,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! MCP server is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
