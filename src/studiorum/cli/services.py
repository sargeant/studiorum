"""
CLI service access patterns for the studiorum command line interface.

This module provides dedicated service access for CLI commands, replacing
the global container pattern with explicit CLI-focused service management.
Maintains performance optimizations while enabling proper dependency injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from studiorum.core.protocols.progress import ProgressCallback

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.services.protocols import SourceManagerProtocol
    from studiorum.core.text.tag_resolver import TagResolver

# Global instances for CLI session performance
_cli_omnidexer: Omnidexer | None = None
_cli_tag_resolver: TagResolver | None = None
_cli_source_manager: SourceManagerProtocol | None = None


def get_cli_omnidexer(
    *, progress_callback: ProgressCallback | None = None
) -> Omnidexer:
    """Get omnidexer instance for CLI commands.

    Uses modern service container with CLI-optimized caching patterns.
    Returns cached instance unless progress callback is provided.

    Args:
        progress_callback: Optional progress callback for data loading

    Returns:
        Omnidexer instance ready for use
    """
    from studiorum.core.services.container import ServiceContainer
    from studiorum.core.services.factories import create_omnidexer_service_sync
    from studiorum.core.services.protocols import (
        ConfigurationProtocol,
        OmnidexerProtocol,
    )

    container = ServiceContainer.get_global_instance()

    # If progress callback provided, create new service instance with progress
    if progress_callback:
        config_service = container.get_service_sync(ConfigurationProtocol)  # type: ignore[type-abstract]
        omnidexer_service = create_omnidexer_service_sync(
            config_service, progress_callback=progress_callback
        )
        return omnidexer_service  # type: ignore[return-value]

    # Otherwise use cached singleton
    global _cli_omnidexer
    if _cli_omnidexer is None:
        _cli_omnidexer = container.get_service_sync(OmnidexerProtocol)  # type: ignore[type-abstract,assignment]
    if _cli_omnidexer is None:
        raise RuntimeError("Failed to initialize CLI omnidexer service")
    return _cli_omnidexer


def get_cli_tag_resolver() -> TagResolver:
    """Get tag resolver instance for CLI commands.

    Uses cached omnidexer instance to avoid redundant data loading.

    Returns:
        TagResolver instance ready for use
    """
    global _cli_tag_resolver
    if _cli_tag_resolver is None:
        from studiorum.core.text.tag_resolver import TagResolver

        # Pass the singleton omnidexer to avoid creating a second one
        omnidexer = get_cli_omnidexer()
        _cli_tag_resolver = TagResolver(omnidexer=omnidexer)
    return _cli_tag_resolver


def get_cli_source_manager() -> SourceManagerProtocol:
    """Get source manager instance for CLI commands.

    Returns:
        SourceManagerProtocol instance for data source management
    """
    from studiorum.core.services.container import ServiceContainer
    from studiorum.core.services.protocols import SourceManagerProtocol

    global _cli_source_manager
    if _cli_source_manager is None:
        container = ServiceContainer.get_global_instance()
        _cli_source_manager = container.get_service_sync(SourceManagerProtocol)  # type: ignore[type-abstract,assignment]
    return _cli_source_manager


def reset_cli_services() -> None:
    """Reset all CLI service instances for command isolation.

    Called between CLI commands to ensure clean state.
    """
    global _cli_omnidexer, _cli_tag_resolver, _cli_source_manager
    _cli_omnidexer = None
    _cli_tag_resolver = None
    _cli_source_manager = None
