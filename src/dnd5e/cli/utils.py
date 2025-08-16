"""
CLI utility functions for accessing shared services.

This module provides access to commonly used services in CLI commands
without creating circular import dependencies with the main CLI module.
"""

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.text.tag_resolver import TagResolver


def get_omnidexer() -> Omnidexer:
    """Get the omnidexer instance from the service container."""
    from dnd5e.core.container import get_global_container

    container = get_global_container()
    return container.get_omnidexer()


def get_tag_resolver() -> TagResolver:
    """Get the tag resolver instance from the service container."""
    from dnd5e.core.container import get_global_container

    container = get_global_container()
    return container.get_tag_resolver()
