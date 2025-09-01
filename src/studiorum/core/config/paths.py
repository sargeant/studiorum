"""Path utilities and helper functions.

This module provides utility functions for working with paths in the studiorum
application. The main path configuration is now handled by ApplicationConfig
in the unified_config module.
"""

from pathlib import Path

from .unified_config import get_app_config


def ensure_output_directories() -> None:
    """Ensure all required output directories exist.

    This is a utility function that creates the standard output directory
    structure based on the current application configuration.
    """
    config = get_app_config()

    # Determine root path for relative path resolution
    root_path = Path.cwd()
    # Try to detect root path by looking for pyproject.toml or CLAUDE.md
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / "CLAUDE.md").exists():
            root_path = parent
            break

    # Create main directories
    output_path = root_path / config.paths.output_path
    build_path = root_path / config.paths.build_path

    output_path.mkdir(parents=True, exist_ok=True)
    build_path.mkdir(parents=True, exist_ok=True)

    # Create output subdirectories
    for subdir in ["books", "adventures", "supplements"]:
        (output_path / subdir).mkdir(exist_ok=True)


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to the project root directory, detected by looking for
        pyproject.toml or CLAUDE.md files.
    """
    current = Path.cwd()
    # Look for pyproject.toml or CLAUDE.md to identify project root
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / "CLAUDE.md").exists():
            return parent
    return current
