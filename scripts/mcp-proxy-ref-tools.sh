#!/usr/bin/env bash
set -euo pipefail

# mcp-proxy launcher for ref.tools MCP server over HTTP
# Usage:
#   export REF_TOOLS_API_KEY=ref-...
#   scripts/mcp-proxy-ref-tools.sh
# This script requires REF_TOOLS_API_KEY in the environment (no defaults).

if [[ -z "${REF_TOOLS_API_KEY:-}" ]]; then
  echo "ERROR: REF_TOOLS_API_KEY is not set" >&2
  echo "Please export REF_TOOLS_API_KEY=ref-... before running." >&2
  exit 1
fi

API_KEY="${REF_TOOLS_API_KEY}"
URL="https://api.ref.tools/mcp?apiKey=${API_KEY}"

exec uv run --group llm mcp-proxy \
  --server-name ref-tools \
  --url "${URL}" \
  --stdio
