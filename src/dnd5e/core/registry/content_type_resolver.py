"""ContentType resolution utilities for migration support."""

from __future__ import annotations

import logging
from functools import lru_cache

from ..models.content import ContentType
from ..result import Error, Result, Success

logger = logging.getLogger(__name__)


def resolve_content_type(type_name: str) -> ContentType:
    """Resolve ContentType by string name, supporting both static and dynamic types.

    Args:
        type_name: ContentType enum value string (e.g., "adventure", "deity")

    Returns:
        ContentType enum instance

    Raises:
        ValueError: If content type is not registered

    Example:
        >>> content_type = resolve_content_type("adventure")
        >>> isinstance(content_type, ContentType)
        True
    """
    try:
        return ContentType(type_name)
    except ValueError as e:
        raise ValueError(f"Unknown content type: {type_name}") from e


def resolve_content_type_safe(type_name: str) -> Result[ContentType, str]:
    """Safely resolve ContentType with structured error handling.

    Args:
        type_name: ContentType enum value string

    Returns:
        Success with ContentType or Error with message

    Example:
        >>> result = resolve_content_type_safe("adventure")
        >>> result.is_success()
        True
        >>> result = resolve_content_type_safe("invalid")
        >>> result.is_error()
        True
    """
    try:
        return Success(ContentType(type_name))
    except ValueError:
        return Error(f"Unknown content type: {type_name}")


@lru_cache(maxsize=1)  # Cache result since enum membership rarely changes
def get_all_content_types() -> set[ContentType]:
    """Get all registered content types (static + dynamic).

    Returns:
        Set of all ContentType enum instances
    """
    return set(ContentType)


def content_type_exists(type_name: str) -> bool:
    """Check if a content type is registered.

    Args:
        type_name: ContentType enum value string

    Returns:
        True if the content type exists, False otherwise
    """
    try:
        ContentType(type_name)
        return True
    except ValueError:
        return False


def get_content_type_names() -> list[str]:
    """Get all registered content type names as strings.

    Returns:
        Sorted list of content type names

    Example:
        >>> names = get_content_type_names()
        >>> "adventure" in names
        True
    """
    return sorted(ct.value for ct in get_all_content_types())
