"""Protocols for LaTeX formatting components."""

from typing import Any, Protocol


class LaTeXFormattingProtocol(Protocol):
    """Protocol for LaTeX formatting operations."""

    def format_text(self, text: str, original_entry: Any = None) -> str:
        """Apply LaTeX formatting to processed text.

        Args:
            text: Text content to format
            original_entry: Original entry object for structure-based formatting

        Returns:
            LaTeX-formatted text
        """
        ...

    def escape_latex_chars(self, text: str) -> str:
        """Escape LaTeX special characters.

        Args:
            text: Text to escape

        Returns:
            Text with LaTeX special characters escaped
        """
        ...
