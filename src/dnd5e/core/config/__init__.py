"""Configuration management for 5e2pdf."""

from .paths import PathConfig, get_path_config
from .settings import Settings, get_settings
from .unified_config import ApplicationConfig, get_app_config

# New unified configuration (recommended)
__all__ = [
    # Legacy configuration (backward compatibility)
    "Settings",
    "get_settings",
    "PathConfig",
    "get_path_config",
    # New unified configuration (recommended)
    "ApplicationConfig",
    "get_app_config",
]
