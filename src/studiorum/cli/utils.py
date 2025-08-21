"""
CLI utility functions for accessing shared services.

This module provides access to commonly used services in CLI commands
without creating circular import dependencies with the main CLI module.
"""

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.text.tag_resolver import TagResolver


def get_omnidexer() -> Omnidexer:
    """Get the omnidexer instance from the service container."""
    from studiorum.core.container import get_global_container

    container = get_global_container()
    omnidexer_result = container.get_omnidexer()
    if omnidexer_result.is_error():
        raise RuntimeError(f"Failed to get omnidexer: {omnidexer_result.error.message}")  # type: ignore[attr-defined]
    return omnidexer_result.unwrap()


def get_tag_resolver() -> TagResolver:
    """Get the tag resolver instance from the service container."""
    from studiorum.core.container import get_global_container

    container = get_global_container()
    tag_resolver_result = container.get_tag_resolver()
    if tag_resolver_result.is_error():
        raise RuntimeError(
            f"Failed to get tag resolver: {tag_resolver_result.error.message}"  # type: ignore[attr-defined]
        )
    return tag_resolver_result.unwrap()
