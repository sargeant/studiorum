"""Image Registry System for batch processing and cataloging.

This module provides comprehensive image registry capabilities for organizing,
cataloging, and batch processing images for complete adventures and books.
"""

from .adventure_registry import (
    AdventureImageRegistry,
    BatchResult,
    ImageCatalog,
    RegistryStats,
)

__all__ = ["AdventureImageRegistry", "ImageCatalog", "BatchResult", "RegistryStats"]
