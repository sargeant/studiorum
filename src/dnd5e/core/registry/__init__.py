"""Content type registry system for automatic registration of D&D content types."""

from .content_type_registry import ContentTypeMetadata, content_type
from .initialization import initialize_content_types
from .registry_manager import RegistryManager

__all__ = [
    "content_type",
    "ContentTypeMetadata",
    "RegistryManager",
    "initialize_content_types",
]
