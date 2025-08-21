"""
Content processing module with service-aware processors.

This module provides high-level processing services that work with
dependency injection patterns, enabling clean separation between
core models and service dependencies.
"""

from .content_processor import ContentProcessingService

__all__ = ["ContentProcessingService"]
