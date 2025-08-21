"""Sync proxy classes for legacy service compatibility.

This module provides proxy classes that directly instantiate legacy services
to avoid deadlock issues with async/sync bridging.

Phase 2 implementation simplified: Use direct instantiation instead of
complex async/sync bridging to avoid event loop conflicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from studiorum.core.services.container import ModernServiceContainer

logger = get_logger(__name__)


def create_omnidexer_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create an omnidexer proxy using direct instantiation."""
    from studiorum.core.loaders.omnidexer import Omnidexer

    # Create omnidexer directly to avoid async/sync bridging issues
    omnidexer = Omnidexer()
    omnidexer.load_all_data()

    # Resolve copy references
    try:
        from studiorum.core.resolvers.copy_resolver import CopyResolver

        copy_resolver = CopyResolver(omnidexer)
        copy_resolver.resolve_copies_in_omnidexer()
    except Exception as e:
        logger.warning(f"Failed to resolve copy references: {e}")

    return omnidexer


def create_tag_resolver_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create a tag resolver proxy using direct instantiation."""
    from studiorum.core.text.tag_resolver import TagResolver

    # Get omnidexer first
    omnidexer = create_omnidexer_proxy(modern_container)

    # Create tag resolver directly
    return TagResolver(omnidexer=omnidexer)


def create_content_type_registry_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create a content type registry proxy using direct instantiation."""
    from studiorum.core.interfaces import ContentTypeRegistry

    # Create content type registry directly
    return ContentTypeRegistry()


def create_display_manager_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create a display manager proxy using direct instantiation."""
    from studiorum.cli.display_manager import DisplayManager

    # Create display manager directly
    return DisplayManager()


def create_content_factory_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create a content factory proxy using direct instantiation."""
    from studiorum.core.loaders.content_factory import ContentFactory

    # Create content factory directly
    return ContentFactory()


def create_entry_registry_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create an entry registry proxy using direct instantiation."""
    from studiorum.core.entry_registry import EntryTypeRegistry

    # Create entry registry directly (this is the actual class with validate_entry_type)
    return EntryTypeRegistry()


def create_reference_manager_proxy(modern_container: ModernServiceContainer) -> Any:
    """Create a reference manager proxy using direct instantiation."""
    from studiorum.core.unified_references import ReferenceManager

    # Create reference manager directly
    return ReferenceManager()
