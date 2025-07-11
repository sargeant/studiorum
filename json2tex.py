#!/usr/bin/env python3
"""
Legacy json2tex.py wrapper for backwards compatibility.

This script maintains compatibility with the original json2tex.py
while using the modern 5e2pdf architecture underneath.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Execute legacy command using modern CLI."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    
    # Path to modern CLI
    cli_path = script_dir / "bin" / "5e2pdf"
    
    if not cli_path.exists():
        print("Error: Modern CLI not found. Please ensure 5e2pdf is properly installed.", file=sys.stderr)
        sys.exit(1)
    
    # Execute modern CLI in legacy mode
    cmd = [str(cli_path), "legacy"] + sys.argv[1:]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output to stdout (for redirection)
        if result.stdout:
            print(result.stdout, end="")
        
        # Print errors to stderr
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"Error executing modern CLI: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()