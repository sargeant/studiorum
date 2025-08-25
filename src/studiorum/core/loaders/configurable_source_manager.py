"""Direct access to UnifiedSourceManager.

This module provides direct access to UnifiedSourceManager and related classes
for content source management. The legacy ConfigurableSourceManager compatibility
layer has been removed.

Recommended usage:
- Use UnifiedSourceManager directly for unified source management
- Use service-based architecture with SourceManagerProtocol and ContentAttributionProtocol
  for new code requiring dependency injection
"""

from __future__ import annotations

# Import the main classes for direct usage
from .content_attribution_manager import ContentAttributionManager
from .data_source_manager import DataSourceManager
from .unified_source_manager import UnifiedSourceManager

# ConfigurableSourceManager now maps directly to UnifiedSourceManager
ConfigurableSourceManager = UnifiedSourceManager

# Export the classes
__all__ = [
    "ConfigurableSourceManager",  # Direct alias to UnifiedSourceManager
    "UnifiedSourceManager",  # Main unified interface
    "DataSourceManager",  # Data repository management
    "ContentAttributionManager",  # Content source attribution
]
