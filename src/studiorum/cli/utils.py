"""
CLI utility functions for accessing shared services.

This module delegates to the new CLI services module for proper separation of concerns.
Maintains backwards compatibility for existing CLI commands.
"""

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.protocols.progress import ProgressCallback
from studiorum.core.text.tag_resolver import TagResolver


def get_omnidexer(*, progress_callback: ProgressCallback | None = None) -> Omnidexer:
    """Get omnidexer instance for CLI commands.

    Delegates to CLI services module for proper service access patterns.

    Args:
        progress_callback: Optional progress callback for data loading

    Returns:
        Omnidexer instance ready for use
    """
    from studiorum.cli.services import get_cli_omnidexer

    return get_cli_omnidexer(progress_callback=progress_callback)


def get_tag_resolver() -> TagResolver:
    """Get tag resolver instance for CLI commands.

    Delegates to CLI services module for proper service access patterns.

    Returns:
        TagResolver instance ready for use
    """
    from studiorum.cli.services import get_cli_tag_resolver

    return get_cli_tag_resolver()


def reset_cli_services() -> None:
    """Reset CLI service instances for command isolation."""
    from studiorum.cli.services import reset_cli_services

    reset_cli_services()
