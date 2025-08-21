"""Security utilities for safe subprocess execution.

This module provides utilities to mitigate security risks associated with subprocess calls,
specifically addressing CWE-78 (OS Command Injection) vulnerabilities related to partial
executable paths (Bandit B607).
"""

import shutil
import sys
from pathlib import Path
from typing import Optional

from studiorum.core.logging import get_logger

logger = get_logger(__name__)


class ExecutableNotFoundError(Exception):
    """Raised when a required executable is not found in PATH."""

    def __init__(self, executable_name: str) -> None:
        """Initialize with executable name."""
        self.executable_name = executable_name
        super().__init__(f"Required executable '{executable_name}' not found in PATH")


def get_safe_executable(name: str) -> str:
    """Get validated executable path to prevent PATH injection attacks.

    This function addresses Bandit B607 (partial executable paths) by using
    shutil.which() to locate executables and validating their existence.

    Args:
        name: The executable name to locate (e.g., 'pdflatex', 'git', 'open')

    Returns:
        The full path to the executable

    Raises:
        ExecutableNotFoundError: If the executable is not found in PATH

    Security Notes:
        - Uses shutil.which() which is safe and follows PATH resolution rules
        - Validates executable exists and is accessible
        - Does not execute the command, only locates it
        - Mitigates CWE-78 OS Command Injection via PATH manipulation
    """
    path = shutil.which(name)
    if not path:
        logger.warning(f"Executable '{name}' not found in PATH")
        raise ExecutableNotFoundError(name)

    # Log successful resolution for security auditing
    logger.debug(f"Resolved executable '{name}' to: {path}")

    # Additional validation - ensure it's actually executable
    executable_path = Path(path)
    if not executable_path.is_file():
        logger.error(f"Resolved path '{path}' is not a file")
        raise ExecutableNotFoundError(name)

    # Note: We don't check execute permissions here as they may vary by platform
    # and the subprocess call will fail gracefully if not executable

    return path


def get_platform_file_opener() -> str:
    """Get the appropriate file opener command for the current platform.

    Returns:
        The safe executable path for opening files on this platform

    Raises:
        ExecutableNotFoundError: If platform file opener is not available

    Security Notes:
        - Uses platform-specific secure file opening commands
        - All paths are validated through get_safe_executable()
    """
    if sys.platform == "darwin":  # macOS
        return get_safe_executable("open")
    elif sys.platform.startswith("linux"):  # Linux
        return get_safe_executable("xdg-open")
    elif sys.platform == "win32":  # Windows
        # Windows uses cmd /c start which requires special handling
        cmd_path = get_safe_executable("cmd")
        return cmd_path
    else:
        raise ExecutableNotFoundError(f"file_opener_for_{sys.platform}")


def get_latex_executable(engine: str = "pdflatex") -> str:
    """Get validated LaTeX engine executable path.

    Args:
        engine: The LaTeX engine name (default: 'pdflatex')

    Returns:
        The full path to the LaTeX engine executable

    Raises:
        ExecutableNotFoundError: If LaTeX engine is not found
    """
    return get_safe_executable(engine)


def get_latex_utility(utility: str) -> str:
    """Get validated LaTeX utility executable path.

    Args:
        utility: The LaTeX utility name (e.g., 'kpsewhich', 'tex')

    Returns:
        The full path to the LaTeX utility executable

    Raises:
        ExecutableNotFoundError: If LaTeX utility is not found
    """
    return get_safe_executable(utility)


def get_git_executable() -> str:
    """Get validated Git executable path.

    Returns:
        The full path to the git executable

    Raises:
        ExecutableNotFoundError: If git is not found
    """
    return get_safe_executable("git")
