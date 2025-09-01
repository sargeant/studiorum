"""Protocols for text processing components."""

from typing import Any, Protocol


class TextExtractionProtocol(Protocol):
    """Protocol for text extraction from 5etools entry structures."""

    def extract_from_entry(self, entry: Any) -> str:
        """Extract full text including entry names.

        Args:
            entry: Entry object in various 5etools formats

        Returns:
            Extracted text content with names included
        """
        ...

    def extract_content_only_from_entry(self, entry: Any) -> str:
        """Extract content text excluding entry names.

        Args:
            entry: Entry object in various 5etools formats

        Returns:
            Extracted text content without entry names
        """
        ...
