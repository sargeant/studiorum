"""Abstract base classes for data loading."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from ..models.content import BaseContent, ContentType

T = TypeVar("T", bound=BaseContent)


class DataLoader[T: BaseContent](ABC):
    """Abstract base class for data loaders."""

    @abstractmethod
    async def load(self, path: Path) -> list[T]:
        """Load data from file and return validated content objects."""
        pass

    @abstractmethod
    def get_content_type(self) -> ContentType:
        """Return the content type this loader handles."""
        pass

    @abstractmethod
    def get_model_class(self) -> type[T]:
        """Return the Pydantic model class for validation."""
        pass


class SourceManager(ABC):
    """Abstract base class for managing multiple data sources."""

    @abstractmethod
    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Return paths to data files organized by content type.

        For adventures and books, this should return only metadata files to prevent
        duplicate loading. Content files are loaded on-demand by ContentResolver.
        """
        pass

    @abstractmethod
    def get_metadata_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to metadata files organized by content type.

        Metadata files contain lightweight index information (names, IDs, TOC)
        and are loaded by the omnidexer. Content files are excluded.

        Returns:
            Dictionary mapping content types to metadata file paths
        """
        pass

    @abstractmethod
    def get_content_files(self) -> dict[ContentType, list[Path]]:
        """Return paths to content files organized by content type.

        Content files contain the actual entry data for adventures and books.
        These are loaded on-demand and merged with metadata.

        Returns:
            Dictionary mapping content types to content file paths
        """
        pass

    @abstractmethod
    def resolve_source(self, source_abbrev: str) -> dict[str, Any] | None:
        """Resolve source abbreviation to full source information."""
        pass

    @abstractmethod
    def get_source_priority(self, source_abbrev: str) -> int:
        """Get priority for a source (lower numbers = higher priority)."""
        pass
