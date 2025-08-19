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

from dnd5e.core.error_types import (
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    MCPErrorCode,
)
from dnd5e.core.result import Error, Result, Success

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

    def load_from_file(
        self, path: Path
    ) -> Result[ApplicationConfig, ConfigurationError]:
        """
        Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Success with ApplicationConfig instance, or Error with configuration details

        Examples:
            ```python
            loader = ConfigLoader()
            result = loader.load_from_file(Path("config.yaml"))

            if result.is_success():
                config = result.unwrap()
                print(f"Loaded config: {config.project.name}")
            else:
                error = result.error
                print(f"Config load failed: {error.message}")
                for suggestion in error.suggestions:
                    print(f"  - {suggestion}")
            ```
        """
        if not path.exists():
            return Error(
                ConfigurationError(
                    message=f"Configuration file not found: {path}",
                    error_code=MCPErrorCode.CONFIGURATION_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source=str(path),
                    suggestions=[
                        f"Create configuration file at {path}",
                        "Check file path and permissions",
                        "Use --config flag to specify different location",
                    ],
                    data={"file_path": str(path), "file_exists": False},
                )
            )

        try:
            with path.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                config_data = {}

            # Create ApplicationConfig from YAML data
            config = ApplicationConfig(**config_data)
            return Success(config)

        except yaml.YAMLError as e:
            return Error(
                ConfigurationError(
                    message=f"Failed to parse YAML file {path}: {e}",
                    error_code=MCPErrorCode.CONFIGURATION_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    source=str(path),
                    suggestions=[
                        "Check YAML syntax and formatting",
                        "Verify proper indentation and quoting",
                        "Use a YAML validator to identify issues",
                    ],
                    data={"file_path": str(path), "yaml_error": str(e)},
                )
            )
        except ValidationError as e:
            error_messages = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return Error(
                ConfigurationError(
                    message=f"Configuration validation failed for {path}",
                    error_code=MCPErrorCode.VALIDATION_FAILED,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    source=str(path),
                    suggestions=[
                        "Check required configuration fields",
                        "Verify field types and values",
                        "Review configuration documentation",
                        "Use configuration schema for validation",
                    ],
                    data={
                        "file_path": str(path),
                        "validation_errors": error_messages,
                        "error_count": len(error_messages),
                    },
                )
            )
        except Exception as e:
            return Error(
                ConfigurationError(
                    message=f"Unexpected error loading config from {path}: {e}",
                    error_code=MCPErrorCode.INTERNAL_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.CRITICAL,
                    source=str(path),
                    suggestions=[
                        "Check file permissions",
                        "Verify file is not corrupted",
                        "Try loading with a different user account",
                        "Report this error if problem persists",
                    ],
                    data={"file_path": str(path), "exception_type": type(e).__name__},
                )
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

    def validate_config(
        self, config: ApplicationConfig
    ) -> Result[ApplicationConfig, ConfigurationError]:
        """
        Validate configuration and return validated instance.

        Args:
            config: Configuration to validate

        Returns:
            Success with validated ApplicationConfig instance, or Error with validation details

        Examples:
            ```python
            result = loader.validate_config(config)
            if result.is_success():
                validated_config = result.unwrap()
            else:
                error = result.error
                print(f"Validation failed: {error.message}")
            ```
        """
        try:
            # Re-parse the config data to trigger all validation
            config_data = config.model_dump()
            validated_config = ApplicationConfig(**config_data)
            return Success(validated_config)
        except ValidationError as e:
            error_messages = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return Error(
                ConfigurationError(
                    message="Configuration validation failed",
                    error_code=MCPErrorCode.VALIDATION_FAILED,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    suggestions=[
                        "Check configuration field types and values",
                        "Review required vs optional fields",
                        "Use configuration schema for reference",
                    ],
                    data={
                        "validation_errors": error_messages,
                        "error_count": len(error_messages),
                    },
                )
            )

    def load_with_overrides(
        self, config_file: Path | None = None, env_overrides: bool = True
    ) -> Result[ApplicationConfig, ConfigurationError]:
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
            Success with merged configuration, or Error with loading/merging details

        Examples:
            ```python
            result = loader.load_with_overrides(
                config_file=Path("config.yaml"),
                env_overrides=True
            )
            if result.is_success():
                config = result.unwrap()
            else:
                error = result.error
                print(f"Config loading failed: {error.message}")
            ```
        """
        configs = []

        # Start with defaults (empty config uses default values)
        configs.append(ApplicationConfig())

        # Add file config if provided
        if config_file:
            file_result = self.load_from_file(config_file)
            if file_result.is_error():
                return file_result  # Return the file loading error
            configs.append(file_result.unwrap())

        # Add environment overrides if enabled
        if env_overrides:
            # Create a fresh instance that will pick up env vars
            configs.append(self.load_from_env())

        try:
            merged_config = self.merge_configs(*configs)
            return Success(merged_config)
        except ConfigValidationError as e:
            return Error(
                ConfigurationError(
                    message=f"Configuration merge failed: {e.message}",
                    error_code=MCPErrorCode.CONFIGURATION_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    suggestions=[
                        "Check for conflicting configuration values",
                        "Verify environment variable formats",
                        "Review configuration hierarchy",
                    ],
                    data={
                        "merge_errors": e.errors,
                        "config_sources": [
                            "defaults",
                            f"file:{config_file}" if config_file else None,
                            "environment" if env_overrides else None,
                        ],
                    },
                )
            )

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
