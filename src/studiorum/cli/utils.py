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

    Uses service container to ensure consistent configuration management.
    Returns cached instance from global container.

    Returns:
        Omnidexer instance ready for use
    """
    from studiorum.core.container import get_global_container
    from studiorum.core.services.protocols import OmnidexerProtocol

    container = get_global_container()
    return container.get_service_sync(OmnidexerProtocol)  # type: ignore[type-abstract]


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
