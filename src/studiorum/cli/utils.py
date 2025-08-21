"""
CLI utility functions for accessing shared services.

This module provides access to commonly used services in CLI commands
using the modern async service container with sync bridge utilities.
"""

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.text.tag_resolver import TagResolver


def get_omnidexer() -> Omnidexer:
    """Get the omnidexer instance from the modern service container.

    Uses async/sync bridge to maintain backward compatibility while
    leveraging the modern async service infrastructure.
    """
    from studiorum.cli.async_bridge import get_omnidexer_sync

    return get_omnidexer_sync()


def get_tag_resolver() -> TagResolver:
    """Get the tag resolver instance from the modern service container.

    Uses async/sync bridge to maintain backward compatibility while
    leveraging the modern async service infrastructure.
    """
    from studiorum.cli.async_bridge import get_tag_resolver_sync

    return get_tag_resolver_sync()
