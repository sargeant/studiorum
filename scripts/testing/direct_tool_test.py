#!/usr/bin/env python3
"""
Test MCP tools directly using the internal functions.
This tests the actual tool logic without MCP protocol overhead.
"""

import asyncio
import json
import time

from dnd5e.mcp.server import get_mcp_app, list_registered_tools
from dnd5e.mcp.tools.content import search_content_performant


def test_tool_listing():
    """Test tool listing directly."""
    print("🔧 Testing tool listing...")

    tools = list_registered_tools()
    print(f"✅ Found {len(tools)} registered tools:")

    # Group by category
    config_tools = [t for t in tools if "config" in t or "preference" in t]
    search_tools = [
        t for t in tools if any(word in t for word in ["search", "list", "resolve"])
    ]

    print(f"   Configuration tools ({len(config_tools)}):")
    for tool in sorted(config_tools):
        print(f"     • {tool}")

    print(f"   Search tools ({len(search_tools)}):")
    for tool in sorted(search_tools):
        print(f"     • {tool}")

    return len(tools) >= 15


async def test_spell_search_performance():
    """Test spell search performance directly."""
    print("\n🔍 Testing spell search performance...")

    try:
        start_time = time.time()
        result = await search_content_performant(
            content_type="spells", query="fireball", limit=5
        )
        duration_ms = (time.time() - start_time) * 1000

        print(f"✅ Spell search completed in {duration_ms:.1f}ms")

        # Check result structure
        if "content" in result:
            spells = result["content"]
            print(f"   Found {len(spells)} spells:")
            for spell in spells[:3]:
                if hasattr(spell, "name"):
                    print(f"     • {spell.name} (Level {getattr(spell, 'level', '?')})")
                elif isinstance(spell, dict):
                    print(
                        f"     • {spell.get('name', 'Unknown')} (Level {spell.get('level', '?')})"
                    )
                else:
                    print(f"     • {spell}")

        # Check performance metrics
        if "performance" in result:
            perf = result["performance"]
            target_met = perf.get("target_met", False)
            cached = perf.get("cached", False)
            print(f"   Performance: {perf.get('duration_ms', duration_ms):.1f}ms")
            print(f"   Target <200ms: {'✅' if target_met else '❌'}")
            print(f"   Cached: {'✅' if cached else '❌'}")

        return True

    except Exception as e:
        print(f"❌ Spell search failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_mcp_server_creation():
    """Test MCP server creation."""
    print("\n🖥️  Testing MCP server creation...")

    try:
        server = get_mcp_app()
        print("✅ MCP server created successfully")

        # Check server attributes
        print(f"   Server name: {getattr(server, 'name', 'Unknown')}")
        print(f"   Server version: {getattr(server, 'version', 'Unknown')}")

        # Check tool manager
        if hasattr(server, "_tool_manager"):
            tool_manager = server._tool_manager
            if hasattr(tool_manager, "_tools"):
                registered_count = len(tool_manager._tools)
                print(f"   Registered tools: {registered_count}")

        return True

    except Exception as e:
        print(f"❌ MCP server creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all direct tests."""
    print("🎲 dnd5e MCP Direct Tool Testing")
    print("=" * 50)

    tests = [
        ("Tool Listing", test_tool_listing),
        ("MCP Server Creation", test_mcp_server_creation),
        ("Spell Search Performance", test_spell_search_performance),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            if result:
                passed += 1
                print(f"✅ {name} passed")
            else:
                print(f"❌ {name} failed")
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All direct tests passed! MCP tools are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
