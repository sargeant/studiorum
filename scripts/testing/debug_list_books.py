#!/usr/bin/env python3
"""
Debug script specifically for list_books timeout issue.
Tests both direct function calls and MCP protocol calls.
"""

import asyncio
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


async def test_direct_omnidexer_loading():
    """Test omnidexer loading directly like CLI does."""
    print("🔧 Testing direct omnidexer loading (CLI-style)...")

    try:
        start_time = time.time()

        # Import and test like CLI does
        from dnd5e.core.loaders.omnidexer import Omnidexer

        omnidexer = Omnidexer()
        print(f"   Omnidexer created in {(time.time() - start_time) * 1000:.1f}ms")

        load_start = time.time()
        omnidexer.load_all_data()
        load_duration = (time.time() - load_start) * 1000

        print(f"✅ Omnidexer loaded all data in {load_duration:.1f}ms")

        # Test getting books
        books = omnidexer.get_all_by_type("book")
        print(f"   Found {len(books)} books")

        if books:
            for i, book in enumerate(books[:3]):
                print(f"     • {book.name} ({book.source.abbreviation})")

        total_duration = (time.time() - start_time) * 1000
        print(f"   Total direct test: {total_duration:.1f}ms")

        return True

    except Exception as e:
        print(f"❌ Direct omnidexer test failed: {e}")
        traceback.print_exc()
        return False


async def test_mcp_content_search_direct():
    """Test MCP content search function directly."""
    print("\n🔍 Testing MCP content search function directly...")

    try:
        start_time = time.time()

        # Import MCP content search function
        from dnd5e.mcp.tools.content import search_content_performant

        print("   Starting async content search...")
        result = await search_content_performant(
            content_type="books", query="", limit=10
        )

        duration_ms = (time.time() - start_time) * 1000
        print(f"✅ MCP content search completed in {duration_ms:.1f}ms")

        if "content" in result:
            books = result["content"]
            print(f"   Found {len(books)} books")

            for i, book in enumerate(books[:3]):
                if hasattr(book, "name"):
                    name = book.name
                    source = getattr(book, "source", None)
                    source_abbr = (
                        getattr(source, "abbreviation", "Unknown")
                        if source
                        else "Unknown"
                    )
                    print(f"     • {name} ({source_abbr})")
                else:
                    print(f"     • {book}")

        # Check performance info
        if "performance" in result:
            perf = result["performance"]
            print(f"   Performance: {perf.get('duration_ms', duration_ms):.1f}ms")
            print(f"   Target met: {perf.get('target_met', False)}")
            print(f"   Cached: {perf.get('cached', False)}")

        return True

    except Exception as e:
        print(f"❌ MCP content search direct test failed: {e}")
        traceback.print_exc()
        return False


async def test_mcp_via_protocol():
    """Test list_books via MCP protocol."""
    print("\n📡 Testing list_books via MCP protocol...")

    process = None
    try:
        # Start MCP server
        print("   Starting MCP server...")
        process = subprocess.Popen(
            ["uv", "run", "python", "-m", "dnd5e.cli.main", "mcp", "run"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
        )

        def send_request(request, timeout=10):
            """Send request with timeout."""
            request_str = json.dumps(request) + "\n"
            process.stdin.write(request_str)
            process.stdin.flush()

            # Use select/polling to implement timeout
            import select
            import sys

            if sys.platform != "win32":
                ready, _, _ = select.select([process.stdout], [], [], timeout)
                if not ready:
                    raise TimeoutError(f"MCP request timed out after {timeout}s")

            response_line = process.stdout.readline()
            if not response_line:
                raise Exception("No response from MCP server")

            try:
                return json.loads(response_line.strip())
            except json.JSONDecodeError:
                raise Exception(f"Invalid JSON response: {response_line}")

        # Initialize
        print("   Initializing MCP connection...")
        init_response = send_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "debug-client", "version": "1.0.0"},
                },
            },
            timeout=5,
        )

        if "result" not in init_response:
            print(f"❌ MCP initialization failed: {init_response}")
            return False

        print("   ✅ MCP initialized successfully")

        # Test list_books with extended timeout
        print("   Calling list_books (60s timeout)...")
        start_time = time.time()

        books_response = send_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_books", "arguments": {"limit": 5}},
            },
            timeout=60,
        )  # 60 second timeout

        duration_ms = (time.time() - start_time) * 1000

        if "result" in books_response:
            print(f"✅ list_books succeeded in {duration_ms:.1f}ms")

            content = books_response["result"]["content"]
            if content and len(content) > 0:
                try:
                    result_text = content[0]["text"]
                    result_data = json.loads(result_text)
                    books = result_data.get("content", [])

                    print(f"   Found {len(books)} books")
                    for book in books[:3]:
                        if isinstance(book, dict):
                            name = book.get("name", "Unknown")
                            source = book.get("source", {})
                            source_abbr = (
                                source.get("abbreviation", "Unknown")
                                if isinstance(source, dict)
                                else "Unknown"
                            )
                            print(f"     • {name} ({source_abbr})")
                        else:
                            print(f"     • {book}")

                    # Performance info
                    performance = result_data.get("performance", {})
                    if performance:
                        perf_duration = performance.get("duration_ms", duration_ms)
                        target_met = performance.get("target_met", False)
                        cached = performance.get("cached", False)
                        print(
                            f"   Performance: {perf_duration:.1f}ms (Target: {'✅' if target_met else '❌'}, Cached: {'✅' if cached else '❌'})"
                        )

                except json.JSONDecodeError:
                    print(f"   Raw response: {result_text[:200]}...")

            return True
        else:
            print(f"❌ list_books failed: {books_response}")
            return False

    except TimeoutError as e:
        print(f"❌ MCP protocol test timed out: {e}")
        return False
    except Exception as e:
        print(f"❌ MCP protocol test failed: {e}")
        traceback.print_exc()
        return False
    finally:
        if process:
            process.terminate()
            process.wait()


async def test_service_container_in_async_context():
    """Test service container behavior in async context."""
    print("\n🔧 Testing service container in async context...")

    try:
        start_time = time.time()

        # Import service container and registration
        from dnd5e.core.services.container import ModernServiceContainer
        from dnd5e.core.services.protocols import OmnidexerProtocol
        from dnd5e.core.services.registration import register_modern_services

        print("   Creating and registering services...")
        container = ModernServiceContainer()
        await register_modern_services(container)

        print("   Resolving omnidexer service...")
        omnidexer = await container.get_service(OmnidexerProtocol)

        resolution_time = (time.time() - start_time) * 1000
        print(f"   Service resolved in {resolution_time:.1f}ms")

        # Test omnidexer operations
        print("   Testing omnidexer.is_loaded()...")
        is_loaded = omnidexer.is_loaded()
        print(f"   Is loaded: {is_loaded}")

        if not is_loaded:
            print("   Loading all data...")
            load_start = time.time()
            omnidexer.load_all_data()
            load_time = (time.time() - load_start) * 1000
            print(f"   Data loaded in {load_time:.1f}ms")

        # Get books
        print("   Getting books...")
        books = omnidexer.get_all_by_type("book")
        print(f"   Found {len(books)} books")

        total_time = (time.time() - start_time) * 1000
        print(f"✅ Service container async test completed in {total_time:.1f}ms")

        return True

    except Exception as e:
        print(f"❌ Service container async test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all debugging tests."""
    print("🎲 Debugging list_books timeout issue")
    print("=" * 60)

    tests = [
        ("Direct Omnidexer Loading", test_direct_omnidexer_loading),
        ("Service Container Async", test_service_container_in_async_context),
        ("MCP Content Search Direct", test_mcp_content_search_direct),
        ("MCP Protocol", test_mcp_via_protocol),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {name} passed")
            else:
                print(f"❌ {name} failed")
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")

    print(f"\n📊 Debug Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! No deadlock detected.")
    else:
        print("⚠️ Some tests failed. Check output above for deadlock indicators.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
