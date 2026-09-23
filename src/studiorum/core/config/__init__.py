"""Configuration management for studiorum."""

from .dynamic_manager import (
    ConfigurationManager,
    get_config_manager,
    reset_config_manager,
    set_config_manager,
)
from .loader import ConfigLoader, ConfigValidationError
from .unified_config import ApplicationConfig, MCPConfig, get_app_config, set_app_config

# New unified configuration (recommended)
__all__ = [
    # New unified configuration (recommended)
    "ApplicationConfig",
    "MCPConfig",
    "get_app_config",
    "set_app_config",
    # Configuration loading
    "ConfigLoader",
    "ConfigValidationError",
    # Dynamic configuration management
    "ConfigurationManager",
    "get_config_manager",
    "reset_config_manager",
    "set_config_manager",
]
