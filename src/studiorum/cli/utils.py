"""
CLI utility functions for accessing shared services.

This module provides direct instantiation of services for CLI commands,
ensuring test compatibility and avoiding complex async/sync bridging.
Uses singleton pattern to avoid redundant data loading within a CLI session.
"""

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.text.tag_resolver import TagResolver

# Global instances for CLI session (reset per command)
_cli_omnidexer: Omnidexer | None = None
_cli_tag_resolver: TagResolver | None = None


def get_omnidexer() -> Omnidexer:
    """Get omnidexer instance for CLI commands.

    Uses singleton pattern to avoid loading data multiple times per CLI session.
    Creates and loads data only once, subsequent calls return cached instance.

    Returns:
        Omnidexer instance ready for use
    """
    global _cli_omnidexer
    if _cli_omnidexer is None:
        _cli_omnidexer = Omnidexer()
        _cli_omnidexer.load_all_data()
    return _cli_omnidexer


def get_tag_resolver() -> TagResolver:
    """Get tag resolver instance for CLI commands.

    Uses cached omnidexer instance to avoid redundant data loading.

    Returns:
        TagResolver instance ready for use
    """
    global _cli_tag_resolver
    if _cli_tag_resolver is None:
        # Pass the singleton omnidexer to avoid creating a second one
        omnidexer = get_omnidexer()
        _cli_tag_resolver = TagResolver(omnidexer=omnidexer)
    return _cli_tag_resolver


def reset_cli_services() -> None:
    """Reset CLI service instances.

    Used for testing and to ensure clean state between CLI commands.
    """
    global _cli_omnidexer, _cli_tag_resolver
    _cli_omnidexer = None
    _cli_tag_resolver = None
