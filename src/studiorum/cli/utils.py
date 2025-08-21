"""
CLI utility functions for accessing shared services.

This module provides direct instantiation of services for CLI commands,
ensuring test compatibility and avoiding complex async/sync bridging.
"""

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.text.tag_resolver import TagResolver


def get_omnidexer() -> Omnidexer:
    """Get omnidexer instance for CLI commands.

    Uses direct instantiation for simplicity and test compatibility.

    Returns:
        Omnidexer instance ready for use
    """
    # Direct instantiation for CLI simplicity and test compatibility
    omnidexer = Omnidexer()
    omnidexer.load_all_data()
    return omnidexer


def get_tag_resolver() -> TagResolver:
    """Get tag resolver instance for CLI commands.

    Uses direct instantiation for simplicity and test compatibility.

    Returns:
        TagResolver instance ready for use
    """
    # Direct instantiation for CLI simplicity and test compatibility
    return TagResolver()
