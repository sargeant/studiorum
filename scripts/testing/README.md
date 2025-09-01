# MCP Testing Scripts

This directory contains testing scripts for the dnd5e MCP server implementation.

## Scripts

- **`direct_tool_test.py`** - Tests MCP tools directly using internal functions (bypasses JSON-RPC protocol)
- **`simple_mcp_test.py`** - Tests MCP using persistent stdio session
- **`debug_mcp.py`** - Debug script for testing different MCP request formats
- **`test_mcp.py`** - Comprehensive MCP test suite with multiple requests

## Usage

```bash
# Test tools directly (recommended for debugging tool logic)
python scripts/testing/direct_tool_test.py

# Test via MCP protocol
python scripts/testing/simple_mcp_test.py

# Debug MCP request formats
python scripts/testing/debug_mcp.py
```

## Notes

- The `direct_tool_test.py` script is most useful for debugging actual tool functionality
- Protocol-based tests may fail if 5etools data is not available
- Timeout errors are expected when no content data is loaded
