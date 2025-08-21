"""Content type registration system with decorator support."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from studiorum.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class ContentTypeMetadata:
    """Metadata for content type registration."""

    enum_value: str
    model_class: type[BaseModel]
    file_patterns: list[str]
    statblock_tags: list[str] | None = None
    loader_type: Literal["json", "fluff"] = "json"
    module_name: str | None = None

    def __post_init__(self) -> None:
        """Validate metadata after initialization."""
        # Allow both snake_case (new) and camelCase (existing enum values) patterns
        if not re.match(r"^[a-z][a-zA-Z0-9_]*$", self.enum_value):
            raise ValueError(f"Invalid enum_value format: {self.enum_value}")
        if not self.file_patterns:
            raise ValueError("file_patterns cannot be empty")


class ContentTypeRegistry:
    """Global registry for content type metadata."""

    __slots__ = ("_metadata", "_finalized", "_last_finalized_count")

    def __init__(self) -> None:
        self._metadata: dict[str, ContentTypeMetadata] = {}
        self._finalized: bool = False
        self._last_finalized_count: int = 0

    def register(self, metadata: ContentTypeMetadata) -> None:
        """Register content type metadata."""
        if self._finalized:
            raise RuntimeError("Registry already finalized")

        if metadata.enum_value in self._metadata:
            existing = self._metadata[metadata.enum_value]
            if existing.model_class != metadata.model_class:
                raise ValueError(
                    f"Duplicate content type '{metadata.enum_value}' with different classes: "
                    f"{existing.model_class} vs {metadata.model_class}"
                )

        self._metadata[metadata.enum_value] = metadata
        logger.debug(f"Registered content type: {metadata.enum_value}")

    def get_all(self) -> dict[str, ContentTypeMetadata]:
        """Get all registered metadata."""
        return self._metadata.copy()

    def get(self, enum_value: str) -> ContentTypeMetadata | None:
        """Get metadata for specific content type."""
        return self._metadata.get(enum_value)

    def finalize(self) -> None:
        """Finalize registry and apply all registrations."""
        current_count = len(self._metadata)

        # Check if we need to re-finalize due to new registrations
        if self._finalized and current_count == self._last_finalized_count:
            return

        logger.info(f"Finalizing content type registry with {current_count} types")

        # Apply all registrations
        from .registry_manager import RegistryManager

        RegistryManager().apply_registrations(self._metadata)

        self._finalized = True
        self._last_finalized_count = current_count

    def reset(self) -> None:
        """Reset registry for testing.

        This resets only the finalization state, preserving existing
        decorator registrations. Use this for test isolation without
        losing decorator-based registrations that only happen at module
        import time.
        """
        # Don't clear metadata - decorator registrations only happen once per process
        # self._metadata.clear()  # This would lose decorator registrations!
        self._finalized = False
        self._last_finalized_count = 0  # Reset count to force re-finalization

    def clear_all_registrations(self) -> None:
        """Clear all registrations for test isolation.

        WARNING: This method completely clears all decorator registrations!
        Only use this in test environments where you need complete isolation
        and are willing to lose all decorator-based registrations.

        After calling this, you'll need to re-import modules to get decorator
        registrations back, or manually register content types.
        """
        self._metadata.clear()
        self._finalized = False
        self._last_finalized_count = 0


# Module-level registry instance
_registry_instance: ContentTypeRegistry | None = None


def get_content_type_registry() -> ContentTypeRegistry:
    """Get the global content type registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ContentTypeRegistry()
    return _registry_instance


def reset_content_type_registry() -> None:
    """Reset the global content type registry for testing.

    This resets the registry instance while preserving the singleton behavior.
    After calling this, the next call to get_content_type_registry() will
    return a fresh registry instance.

    This is safer than setting _registry_instance to None directly because
    it ensures proper cleanup of any resources and maintains the singleton pattern.
    """
    global _registry_instance
    if _registry_instance is not None:
        _registry_instance.reset()
    # Don't set to None - just reset the existing instance
    # This allows decorator registrations to work properly


def content_type(
    enum_value: str,
    file_patterns: list[str],
    statblock_tags: list[str] | None = None,
    loader_type: Literal["json", "fluff"] = "json",
) -> Callable[[type[T]], type[T]]:
    """
    Register content type metadata.

    Note: enum_value must match a ContentType enum value.

    Args:
        enum_value: String value for ContentType enum
        file_patterns: List of filename patterns to match
        statblock_tags: List of statblock tag names (optional)
        loader_type: Type of loader to use (default: "json")

    Returns:
        The decorated class, unchanged

    Raises:
        TypeError: If decorated class doesn't inherit from BaseContent
        ValueError: If parameters are invalid or enum_value doesn't match ContentType
    """
    # Validate inputs before creating decorator
    if not enum_value.strip():
        raise ValueError("enum_value cannot be empty")
    if not file_patterns:
        raise ValueError("file_patterns cannot be empty")

    def decorator(cls: type[T]) -> type[T]:
        # Import here to avoid circular imports
        from ..models.content import BaseContent, ContentType

        if not issubclass(cls, BaseContent):
            raise TypeError(f"Class {cls.__name__} must inherit from BaseContent")

        # Validate that enum_value exists in ContentType
        try:
            ContentType(enum_value)
        except ValueError:
            raise ValueError(
                f"Invalid enum_value '{enum_value}' - must match ContentType enum"
            )

        try:
            # Register metadata only (no enum extension)
            metadata = ContentTypeMetadata(
                enum_value=enum_value,
                model_class=cls,
                file_patterns=file_patterns,
                statblock_tags=statblock_tags,
                loader_type=loader_type,
                module_name=cls.__module__,
            )

            registry = get_content_type_registry()
            registry.register(metadata)
        except Exception as e:
            logger.error(f"Failed to register content type {cls.__name__}: {e}")
            raise

        return cls

    return decorator
