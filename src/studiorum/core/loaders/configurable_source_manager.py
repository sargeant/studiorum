"""Compatibility module for ConfigurableSourceManager.

This module maintains backward compatibility for existing imports while
transitioning to the new service-based architecture. The ConfigurableSourceManager
is now implemented as a compatibility wrapper around UnifiedSourceManager.

MIGRATION PATH:
1. Existing code continues to work unchanged (imports ConfigurableSourceManager)
2. New code should use service-based architecture (SourceManagerProtocol, ContentAttributionProtocol)
3. Eventually migrate existing code to use UnifiedSourceManager directly
"""

from __future__ import annotations

import warnings

# Also provide the new classes for migration
from .content_attribution_manager import ContentAttributionManager
from .data_source_manager import DataSourceManager

# Import the compatibility class and alias it as ConfigurableSourceManager
# This ensures all existing imports continue to work without changes
from .unified_source_manager import (
    ConfigurableSourceManagerCompat as ConfigurableSourceManager,
    UnifiedSourceManager,
)

# Export the main compatibility class and new classes
__all__ = [
    "ConfigurableSourceManager",  # Backward compatibility (deprecated)
    "UnifiedSourceManager",  # New unified interface
    "DataSourceManager",  # Data repository management
    "ContentAttributionManager",  # Content source attribution
]

# Issue module-level deprecation warning
warnings.warn(
    "The configurable_source_manager module is deprecated. "
    "Migrate to service-based architecture using SourceManagerProtocol and "
    "ContentAttributionProtocol, or use UnifiedSourceManager directly.",
    DeprecationWarning,
    stacklevel=2,
)
