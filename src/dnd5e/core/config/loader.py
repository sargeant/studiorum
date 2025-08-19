"""
Configuration loader for hierarchical config merging and file loading.

This module provides the ConfigLoader class that enables loading configuration
from YAML files, environment variables, and provides hierarchical merging
capabilities for the unified configuration system.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from .unified_config import ApplicationConfig

T = TypeVar("T", bound=BaseModel)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None):
        self.message = message
        self.errors = errors or []
        super().__init__(message)


class ConfigLoader:
    """
    Unified configuration loader with YAML support and hierarchical merging.

    Supports loading configuration from:
    - YAML files
    - Environment variables (via existing pydantic-settings support)
    - Default values
    - Hierarchical merging with precedence order
    """

    def __init__(self) -> None:
        """Initialize the configuration loader."""
        pass

    def load_from_file(self, path: Path) -> ApplicationConfig:
        """
        Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            ApplicationConfig instance loaded from file

        Raises:
            ConfigValidationError: If file loading or validation fails
            FileNotFoundError: If the config file doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                config_data = {}

            # Create ApplicationConfig from YAML data
            return ApplicationConfig(**config_data)

        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Failed to parse YAML file {path}: {e}")
        except ValidationError as e:
            error_messages = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise ConfigValidationError(
                f"Configuration validation failed for {path}", errors=error_messages
            )
        except Exception as e:
            raise ConfigValidationError(
                f"Unexpected error loading config from {path}: {e}"
            )

    def load_from_env(self) -> ApplicationConfig:
        """
        Load configuration from environment variables.

        Uses the existing pydantic-settings support with DND5E_ prefix.

        Returns:
            ApplicationConfig instance with environment variable overrides
        """
        return ApplicationConfig()

    def merge_configs(self, *configs: ApplicationConfig) -> ApplicationConfig:
        """
        Merge multiple configurations with precedence order.

        Later configurations in the argument list override earlier ones.
        This enables hierarchical configuration like:
        defaults < file config < environment variables

        Args:
            *configs: Configuration objects to merge in precedence order

        Returns:
            Merged ApplicationConfig instance
        """
        if not configs:
            return ApplicationConfig()

        if len(configs) == 1:
            return configs[0]

        # Start with the first config as base
        merged_dict = configs[0].model_dump()

        # Merge subsequent configs, with later ones taking precedence
        for config in configs[1:]:
            config_dict = config.model_dump()
            merged_dict = self._deep_merge_dicts(merged_dict, config_dict)

        # Create new config from merged data
        try:
            return ApplicationConfig(**merged_dict)
        except ValidationError as e:
            error_messages = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise ConfigValidationError(
                "Configuration merge resulted in invalid config", errors=error_messages
            )

    def validate_config(self, config: ApplicationConfig) -> ApplicationConfig:
        """
        Validate configuration and return validated instance.

        Args:
            config: Configuration to validate

        Returns:
            Validated ApplicationConfig instance (same as input if valid)

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            # Re-parse the config data to trigger all validation
            config_data = config.model_dump()
            return ApplicationConfig(**config_data)
        except ValidationError as e:
            error_messages = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise ConfigValidationError(
                "Configuration validation failed", errors=error_messages
            )

    def load_with_overrides(
        self, config_file: Path | None = None, env_overrides: bool = True
    ) -> ApplicationConfig:
        """
        Load configuration with hierarchical precedence.

        Precedence order (later overrides earlier):
        1. Default values
        2. Configuration file (if provided)
        3. Environment variables (if enabled)

        Args:
            config_file: Optional path to YAML config file
            env_overrides: Whether to apply environment variable overrides

        Returns:
            Merged configuration with all overrides applied
        """
        configs = []

        # Start with defaults (empty config uses default values)
        configs.append(ApplicationConfig())

        # Add file config if provided
        if config_file:
            configs.append(self.load_from_file(config_file))

        # Add environment overrides if enabled
        if env_overrides:
            # Create a fresh instance that will pick up env vars
            configs.append(self.load_from_env())

        return self.merge_configs(*configs)

    def _deep_merge_dicts(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Deep merge two dictionaries, with override values taking precedence.

        Args:
            base: Base dictionary
            override: Dictionary with override values

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                # Override the value
                result[key] = value

        return result
