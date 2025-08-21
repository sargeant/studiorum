#!/usr/bin/env python3
"""
Get the current version from pyproject.toml and validate it matches __init__.py.

This script safely extracts the version number for use in git workflows
and other automation scripts.
"""

import re
import sys
from pathlib import Path


def get_version() -> str:
    """
    Read version from pyproject.toml and validate it matches __init__.py.

    Returns:
        str: The version string (e.g., "0.3.1")

    Raises:
        SystemExit: If versions don't match or files are missing/malformed
    """
    pyproject_path = Path("pyproject.toml")
    init_py_path = Path("src/studiorum/__init__.py")

    # Check files exist
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found", file=sys.stderr)
        sys.exit(1)

    if not init_py_path.exists():
        print("Error: src/studiorum/__init__.py not found", file=sys.stderr)
        sys.exit(1)

    # Read version from pyproject.toml
    pyproject_content = pyproject_path.read_text()
    pyproject_version_match = re.search(
        r'^version = "(\d+\.\d+\.\d+)"', pyproject_content, re.MULTILINE
    )

    if not pyproject_version_match:
        print("Error: Version not found in pyproject.toml", file=sys.stderr)
        sys.exit(1)

    pyproject_version = pyproject_version_match.group(1)

    # Read version from __init__.py
    init_py_content = init_py_path.read_text()
    init_py_version_match = re.search(
        r'__version__ = "(\d+\.\d+\.\d+)"', init_py_content
    )

    if not init_py_version_match:
        print(
            "Error: __version__ not found in src/studiorum/__init__.py", file=sys.stderr
        )
        sys.exit(1)

    init_py_version = init_py_version_match.group(1)

    # Validate versions match
    if pyproject_version != init_py_version:
        print("Error: Version mismatch!", file=sys.stderr)
        print(f"  pyproject.toml: {pyproject_version}", file=sys.stderr)
        print(f"  __init__.py:    {init_py_version}", file=sys.stderr)
        sys.exit(1)

    return pyproject_version


if __name__ == "__main__":
    try:
        version = get_version()
        print(version)
    except KeyboardInterrupt:
        sys.exit(1)
