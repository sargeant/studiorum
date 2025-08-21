"""Configuration management for studiorum."""

from .dynamic_manager import (
    ConfigurationManager,
    get_config_manager,
    reset_config_manager,
    set_config_manager,
)
from .loader import ConfigLoader, ConfigValidationError
from .paths import PathConfig, get_path_config
from .settings import Settings, get_settings
from .unified_config import ApplicationConfig, MCPConfig, get_app_config, set_app_config
from .workflow_config import (
    get_adventure_creation_workflow_config,
    get_available_workflows,
    get_character_sheet_workflow_config,
    get_dm_reference_workflow_config,
    get_encounter_printing_workflow_config,
    get_homebrew_workflow_config,
    get_spellbook_workflow_config,
)

# New unified configuration (recommended)
__all__ = [
    # Legacy configuration (backward compatibility)
    "Settings",
    "get_settings",
    "PathConfig",
    "get_path_config",
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
    # Workflow configuration helpers
    "get_spellbook_workflow_config",
    "get_encounter_printing_workflow_config",
    "get_adventure_creation_workflow_config",
    "get_character_sheet_workflow_config",
    "get_dm_reference_workflow_config",
    "get_homebrew_workflow_config",
    "get_available_workflows",
]
