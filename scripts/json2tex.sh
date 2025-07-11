#!/bin/bash

# Wrapper script for json2tex.py that matches the workflow from CLAUDE.md
# Usage: ./json2tex.sh [json2tex.py options] <json_file>

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"

# Change to project directory
cd "$PROJECT_DIR"

# Run json2tex.py with all provided arguments using uv
uv run python "$SRC_DIR/json2tex.py" "$@"