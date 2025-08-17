"""Content source abstraction for unified content loading.

This module provides a unified interface for loading content from various sources:
- Standard 5etools dual-file system (metadata + content)
- Single JSON files (homebrew content)
- Inline content embedded in adventures
- stdin/pipe input
- Future: Remote URLs, databases, etc.

All sources provide consistent error handling, validation, and content discovery.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from ..models.content import BaseContent, ContentType


class ValidationResult(BaseModel):
    """Result of content source validation."""

    is_valid: bool = Field(description="Whether the source is valid")
    errors: list[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)


class ContentSourceMetadata(BaseModel):
    """Metadata about a content source."""

    source_type: str = Field(description="Type of content source")
    location: str = Field(description="Source location (file path, URL, etc.)")
    description: str = Field(description="Human-readable description")
    content_count: int = Field(
        default=0, description="Number of content items available"
    )
    estimated_size: str = Field(default="unknown", description="Estimated content size")


class ContentSource(Protocol):
    """Protocol for content sources."""

    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about this content source."""
        ...

    def validate(self) -> ValidationResult:
        """Validate the content source."""
        ...

    def load(self) -> list[BaseContent]:
        """Load content from the source."""
        ...

    def supports_streaming(self) -> bool:
        """Whether this source supports streaming/lazy loading."""
        ...


class BaseContentSource(ABC):
    """Base implementation for content sources."""

    def __init__(self, location: str, description: str = "") -> None:
        self.location = location
        self.description = description or f"Content from {location}"

    @abstractmethod
    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about this content source."""
        pass

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Validate the content source."""
        pass

    @abstractmethod
    def load(self) -> list[BaseContent]:
        """Load content from the source."""
        pass

    def supports_streaming(self) -> bool:
        """Whether this source supports streaming/lazy loading."""
        return False


class FileContentSource(BaseContentSource):
    """Load content from a JSON file."""

    def __init__(
        self, file_path: Path, content_type: ContentType | None = None
    ) -> None:
        super().__init__(str(file_path), f"JSON file: {file_path.name}")
        self.file_path = file_path
        self.content_type = content_type
        self._cached_data: dict[str, Any] | None = None
        self._cached_content: list[BaseContent] | None = None
        self._last_modified: float | None = None

    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about this file source."""
        content_count = 0
        size_str = "unknown"

        if self.file_path.exists():
            size_bytes = self.file_path.stat().st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes // 1024} KB"
            else:
                size_str = f"{size_bytes // (1024 * 1024)} MB"

            # Try to count content items
            try:
                data = self._load_json_data()
                content_count = self._count_content_items(data)
            except Exception:
                pass

        return ContentSourceMetadata(
            source_type="file",
            location=str(self.file_path),
            description=self.description,
            content_count=content_count,
            estimated_size=size_str,
        )

    def validate(self) -> ValidationResult:
        """Validate the file source."""
        result = ValidationResult(is_valid=True)

        # Check file existence
        if not self.file_path.exists():
            result.add_error(f"File does not exist: {self.file_path}")
            return result

        # Check file is readable
        if not self.file_path.is_file():
            result.add_error(f"Path is not a file: {self.file_path}")
            return result

        # Check JSON format
        try:
            data = self._load_json_data()
            if not isinstance(data, dict):
                result.add_error("JSON file must contain an object")
                return result
        except Exception as e:
            result.add_error(f"Invalid JSON format: {e}")
            return result

        return result

    def load(self) -> list[BaseContent]:
        """Load content from the JSON file."""
        # Performance optimization: Check cache first
        current_modified = (
            self.file_path.stat().st_mtime if self.file_path.exists() else 0
        )

        if (
            self._cached_content is not None
            and self._last_modified is not None
            and current_modified <= self._last_modified
        ):
            return self._cached_content

        from .content_factory import ContentFactory

        data = self._load_json_data()
        content_items = []
        factory = ContentFactory()

        # Handle different JSON structures
        if self.content_type:
            # Single content type specified
            items = data.get(self.content_type.value, [])

            # Special handling for direct content objects (backward compatibility)
            if (
                self.content_type == ContentType.BOOK
                and not items
                and isinstance(data, dict)
            ):
                # Treat the entire data as a book object
                book_data = dict(data)

                # Add default name and source if missing (for backward compatibility)
                if "name" not in book_data:
                    book_data["name"] = f"Book: {self.file_path.stem}"
                if "source" not in book_data:
                    book_data["source"] = {
                        "abbreviation": "FILE",
                        "name": f"File: {self.file_path.name}",
                    }

                try:
                    content_items.append(
                        factory.create_content(book_data, self.content_type)
                    )
                except ValidationError as e:
                    # Log validation error but continue
                    from ..logging import get_logger

                    logger = get_logger(__name__)
                    logger.warning(f"Failed to load book: {e}")
            elif (
                self.content_type == ContentType.ADVENTURE
                and not items
                and isinstance(data, dict)
            ):
                # Treat the entire data as an adventure object
                adventure_data = dict(data)

                # Add default name and source if missing (for backward compatibility)
                if "name" not in adventure_data:
                    adventure_data["name"] = f"Adventure: {self.file_path.stem}"
                if "source" not in adventure_data:
                    adventure_data["source"] = {
                        "abbreviation": "FILE",
                        "name": f"File: {self.file_path.name}",
                    }

                try:
                    content_items.append(
                        factory.create_content(adventure_data, self.content_type)
                    )
                except ValidationError as e:
                    # Log validation error but continue
                    from ..logging import get_logger

                    logger = get_logger(__name__)
                    logger.warning(f"Failed to load adventure: {e}")
            else:
                # Normal case: process items array
                for item_data in items:
                    try:
                        content_items.append(
                            factory.create_content(item_data, self.content_type)
                        )
                    except ValidationError as e:
                        # Log validation error but continue
                        from ..logging import get_logger

                        logger = get_logger(__name__)
                        logger.warning(f"Failed to load {self.content_type} item: {e}")
        else:
            # Auto-detect content types
            type_handlers = {
                "spell": ContentType.SPELL,
                "spells": ContentType.SPELL,
                "monster": ContentType.CREATURE,
                "monsters": ContentType.CREATURE,
                "creature": ContentType.CREATURE,
                "creatures": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "items": ContentType.ITEM,
            }

            for key, items in data.items():
                if isinstance(items, list) and key in type_handlers:
                    content_type = type_handlers[key]
                    for item_data in items:
                        try:
                            content_items.append(
                                factory.create_content(item_data, content_type)
                            )
                        except ValidationError as e:
                            # Log validation error but continue
                            from ..logging import get_logger

                            logger = get_logger(__name__)
                            logger.warning(f"Failed to load {key} item: {e}")

        # Cache the results
        self._cached_content = content_items
        self._last_modified = current_modified

        return content_items

    def _load_json_data(self) -> dict[str, Any]:
        """Load and cache JSON data."""
        if self._cached_data is None:
            import json

            with open(self.file_path, encoding="utf-8") as f:
                self._cached_data = json.load(f)

        # Type guard to ensure we return the expected type
        if self._cached_data is None:
            raise ValueError("Failed to load JSON data from file")

        return self._cached_data

    def _count_content_items(self, data: dict[str, Any]) -> int:
        """Count content items in the JSON data."""
        count = 0
        for value in data.values():
            if isinstance(value, list):
                count += len(value)
        return count


class OmnidexerContentSource(BaseContentSource):
    """Load content from the omnidexer."""

    def __init__(self, omnidexer: Any, content_type: ContentType) -> None:
        super().__init__(
            f"omnidexer:{content_type.value}",
            f"Omnidexer content: {content_type.value}",
        )
        self.omnidexer = omnidexer
        self.content_type = content_type

    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about this omnidexer source."""
        content_count = 0
        try:
            # Get count from omnidexer
            all_content = self.omnidexer.find_all(self.content_type)
            content_count = len(all_content)
        except Exception:
            pass

        return ContentSourceMetadata(
            source_type="omnidexer",
            location=self.location,
            description=self.description,
            content_count=content_count,
            estimated_size=f"~{content_count} items",
        )

    def validate(self) -> ValidationResult:
        """Validate the omnidexer source."""
        result = ValidationResult(is_valid=True)

        if self.omnidexer is None:
            result.add_error("Omnidexer is not available")
            return result

        # Check if content type is supported
        try:
            self.omnidexer.find_all(self.content_type)
        except Exception as e:
            result.add_error(f"Omnidexer error for {self.content_type}: {e}")

        return result

    def load(self) -> Any:  # type: ignore[override]
        """Load content from the omnidexer."""
        return self.omnidexer.find_all(self.content_type)

    def supports_streaming(self) -> bool:
        """Omnidexer supports efficient access patterns."""
        return True


class InlineContentSource(BaseContentSource):
    """Extract inline content from adventure JSON."""

    def __init__(
        self, adventure_data: dict[str, Any], content_type: ContentType
    ) -> None:
        super().__init__(
            f"inline:{content_type.value}",
            f"Inline {content_type.value} content from adventure",
        )
        self.adventure_data = adventure_data
        self.content_type = content_type

    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about inline content."""
        content_count = self._count_inline_content()

        return ContentSourceMetadata(
            source_type="inline",
            location=self.location,
            description=self.description,
            content_count=content_count,
            estimated_size=f"{content_count} inline items",
        )

    def validate(self) -> ValidationResult:
        """Validate the inline content source."""
        result = ValidationResult(is_valid=True)

        if not isinstance(self.adventure_data, dict):
            result.add_error("Adventure data must be a dictionary")
            return result

        return result

    def load(self) -> list[BaseContent]:
        """Extract inline content from adventure data."""
        # This is a simplified implementation
        # In reality, would need sophisticated parsing of adventure structure
        from .content_factory import ContentFactory

        content_items = []
        factory = ContentFactory()

        # Look for inline statblocks in adventure chapters
        try:
            if "data" in self.adventure_data:
                chapters = self.adventure_data["data"]
                if isinstance(chapters, list):
                    for chapter in chapters:
                        if isinstance(chapter, dict) and "entries" in chapter:
                            inline_items = self._extract_from_entries(
                                chapter["entries"]
                            )
                            for item_data in inline_items:
                                try:
                                    content_items.append(
                                        factory.create_content(
                                            item_data, self.content_type
                                        )
                                    )
                                except ValidationError as e:
                                    # Log but continue
                                    from ..logging import get_logger

                                    logger = get_logger(__name__)
                                    logger.warning(
                                        f"Failed to load inline {self.content_type}: {e}"
                                    )
        except Exception as e:
            from ..logging import get_logger

            logger = get_logger(__name__)
            logger.warning(f"Error extracting inline content: {e}")

        return content_items

    def _count_inline_content(self) -> int:
        """Count inline content items."""
        count = 0
        try:
            if "data" in self.adventure_data:
                chapters = self.adventure_data["data"]
                if isinstance(chapters, list):
                    for chapter in chapters:
                        if isinstance(chapter, dict) and "entries" in chapter:
                            count += len(self._extract_from_entries(chapter["entries"]))
        except Exception:
            pass
        return count

    def _extract_from_entries(self, entries: list[Any]) -> list[dict[str, Any]]:
        """Extract content from adventure entries."""
        # Simplified implementation - would need more sophisticated parsing
        # to handle various inline content formats in 5etools adventures
        extracted = []

        for entry in entries:
            if isinstance(entry, dict):
                # Look for statblock entries
                if (
                    entry.get("type") == "statblock"
                    and self.content_type == ContentType.CREATURE
                ):
                    if "data" in entry:
                        extracted.append(entry["data"])
                # Look for spell entries
                elif (
                    entry.get("type") == "spell"
                    and self.content_type == ContentType.SPELL
                ):
                    if "data" in entry:
                        extracted.append(entry["data"])
                # Recursively search nested entries
                elif "entries" in entry:
                    extracted.extend(self._extract_from_entries(entry["entries"]))

        return extracted


class NameListFileSource(BaseContentSource):
    """Load content names from a text file (one name per line)."""

    def __init__(self, file_path: Path, content_type: ContentType) -> None:
        super().__init__(str(file_path), f"Name list: {file_path.name}")
        self.file_path = file_path
        self.content_type = content_type
        self._cached_names: list[str] | None = None

    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about this name list source."""
        content_count = 0
        size_str = "unknown"

        if self.file_path.exists():
            size_bytes = self.file_path.stat().st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes // 1024} KB"
            else:
                size_str = f"{size_bytes // (1024 * 1024)} MB"

            try:
                names = self._load_names()
                content_count = len(names)
            except Exception:
                pass

        return ContentSourceMetadata(
            source_type="name_list",
            location=str(self.file_path),
            description=self.description,
            content_count=content_count,
            estimated_size=size_str,
        )

    def validate(self) -> ValidationResult:
        """Validate the name list file."""
        result = ValidationResult(is_valid=True)

        if not self.file_path.exists():
            result.add_error(f"File does not exist: {self.file_path}")
            return result

        if not self.file_path.is_file():
            result.add_error(f"Path is not a file: {self.file_path}")
            return result

        try:
            names = self._load_names()
            if not names:
                result.add_warning(f"No names found in file: {self.file_path}")
        except Exception as e:
            result.add_error(f"Failed to read file: {e}")

        return result

    def load(self) -> list[str]:  # type: ignore[override]
        """Load names from the file."""
        return self._load_names()

    def _load_names(self) -> list[str]:
        """Load and parse names from file."""
        if self._cached_names is not None:
            return self._cached_names

        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except PermissionError:
            raise PermissionError(f"Cannot read file: {self.file_path}")

        names = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Handle inline comments
            if "#" in line:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue

            names.append(line)

        if not names:
            raise ValueError(f"No names found in file: {self.file_path}")

        self._cached_names = names
        return names


class StdinContentSource(BaseContentSource):
    """Load content from stdin/pipe input."""

    def __init__(self, content_type: ContentType | None = None) -> None:
        super().__init__("stdin", "Standard input")
        self.content_type = content_type
        self._cached_data: str | None = None

    def get_metadata(self) -> ContentSourceMetadata:
        """Get metadata about stdin source."""
        return ContentSourceMetadata(
            source_type="stdin",
            location="stdin",
            description="Standard input stream",
            content_count=0,  # Can't determine without reading
            estimated_size="unknown",
        )

    def validate(self) -> ValidationResult:
        """Validate stdin source."""
        result = ValidationResult(is_valid=True)

        # Check if stdin has data
        import sys

        if sys.stdin.isatty():
            result.add_warning("No data available on stdin")

        return result

    def load(self) -> list[BaseContent]:
        """Load content from stdin."""
        import json
        import sys

        from .content_factory import ContentFactory

        factory = ContentFactory()

        if self._cached_data is None:
            self._cached_data = sys.stdin.read()

        # Type guard to ensure _cached_data is not None
        if self._cached_data is None:
            raise ValueError("Failed to read data from stdin")

        try:
            data = json.loads(self._cached_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from stdin: {e}")

        # Use similar logic to FileContentSource
        content_items = []

        if self.content_type:
            items = data.get(self.content_type.value, [])
            for item_data in items:
                try:
                    content_items.append(
                        factory.create_content(item_data, self.content_type)
                    )
                except ValidationError as e:
                    from ..logging import get_logger

                    logger = get_logger(__name__)
                    logger.warning(
                        f"Failed to load {self.content_type} from stdin: {e}"
                    )
        else:
            # Auto-detect like FileContentSource
            type_handlers = {
                "spell": ContentType.SPELL,
                "spells": ContentType.SPELL,
                "monster": ContentType.CREATURE,
                "monsters": ContentType.CREATURE,
                "creature": ContentType.CREATURE,
                "creatures": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "items": ContentType.ITEM,
            }

            for key, items in data.items():
                if isinstance(items, list) and key in type_handlers:
                    content_type = type_handlers[key]
                    for item_data in items:
                        try:
                            content_items.append(
                                factory.create_content(item_data, content_type)
                            )
                        except ValidationError as e:
                            from ..logging import get_logger

                            logger = get_logger(__name__)
                            logger.warning(f"Failed to load {key} from stdin: {e}")

        return content_items


class ContentLoader:
    """Unified loader for all content sources."""

    def __init__(self) -> None:
        self._sources: list[ContentSource] = []

    def add_source(self, source: ContentSource) -> None:
        """Add a content source."""
        self._sources.append(source)

    def validate_all(self) -> dict[str, ValidationResult]:
        """Validate all sources."""
        results = {}
        for i, source in enumerate(self._sources):
            results[f"source_{i}"] = source.validate()
        return results

    def load_all(self) -> list[BaseContent]:
        """Load content from all sources."""
        all_content = []

        for source in self._sources:
            try:
                content = source.load()
                all_content.extend(content)
            except Exception as e:
                from ..logging import get_logger

                logger = get_logger(__name__)
                logger.error(
                    f"Failed to load from source {source.get_metadata().location}: {e}"
                )

        return all_content

    def get_source_metadata(self) -> list[ContentSourceMetadata]:
        """Get metadata for all sources."""
        return [source.get_metadata() for source in self._sources]

    def clear(self) -> None:
        """Clear all sources."""
        self._sources.clear()


def create_file_source(
    file_path: Path, content_type: ContentType | None = None
) -> FileContentSource:
    """Factory function to create a file content source."""
    return FileContentSource(file_path, content_type)


def create_omnidexer_source(
    omnidexer: Any, content_type: ContentType
) -> OmnidexerContentSource:
    """Factory function to create an omnidexer content source."""
    return OmnidexerContentSource(omnidexer, content_type)


def create_stdin_source(content_type: ContentType | None = None) -> StdinContentSource:
    """Factory function to create a stdin content source."""
    return StdinContentSource(content_type)


def create_inline_source(
    adventure_data: dict[str, Any], content_type: ContentType
) -> InlineContentSource:
    """Factory function to create an inline content source."""
    return InlineContentSource(adventure_data, content_type)


def create_name_list_source(
    file_path: Path, content_type: ContentType
) -> NameListFileSource:
    """Factory function to create a name list source."""
    return NameListFileSource(file_path, content_type)
