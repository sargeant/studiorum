"""Image integration modules for content-specific image handling.

This package provides specialized image integration capabilities for different
types of D&D 5e content, building on the Phase 1 and Phase 2 image systems.
"""

from .adventure import AdventureImageIntegration
from .bestiary import BestiaryImageIntegration
from .items import ItemImageIntegration

__all__ = [
    "AdventureImageIntegration",
    "BestiaryImageIntegration",
    "ItemImageIntegration",
]
