"""Tests for ConfigLoader class."""

import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from dnd5e.core.config.loader import ConfigLoader, ConfigValidationError
from dnd5e.core.config.unified_config import ApplicationConfig, MCPConfig


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.loader = ConfigLoader()

    def test_load_from_env_default(self) -> None:
        """Test loading default configuration from environment."""
        config = self.loader.load_from_env()

        assert isinstance(config, ApplicationConfig)
        assert isinstance(config.mcp, MCPConfig)
        assert config.mcp.enabled is False  # Default value
        assert config.mcp.host == "localhost"  # Default value
        assert config.mcp.port == 8080  # Default value

    def test_load_from_file_success(self) -> None:
        """Test successful loading from YAML file."""
        test_config = {
            "mcp": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 3000,
                "max_concurrent_requests": 20,
                "cache_size_mb": 512,
                "preload_content_types": ["creatures", "spells"],
                "enable_hot_reload": True,
            },
            "rendering": {"debug": True},
            "logging": {"level": "DEBUG"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            config = self.loader.load_from_file(config_path)

            assert config.mcp.enabled is True
            assert config.mcp.host == "0.0.0.0"
            assert config.mcp.port == 3000
            assert config.mcp.max_concurrent_requests == 20
            assert config.mcp.cache_size_mb == 512
            assert config.mcp.preload_content_types == ["creatures", "spells"]
            assert config.mcp.enable_hot_reload is True
            assert config.rendering.debug is True
            assert config.logging.level == "DEBUG"
        finally:
            config_path.unlink()

    def test_load_from_file_not_found(self) -> None:
        """Test loading from non-existent file."""
        non_existent_path = Path("/tmp/non_existent_config.yaml")

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            self.loader.load_from_file(non_existent_path)

    def test_load_from_file_invalid_yaml(self) -> None:
        """Test loading from file with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [unclosed bracket")
            invalid_path = Path(f.name)

        try:
            with pytest.raises(
                ConfigValidationError, match="Failed to parse YAML file"
            ):
                self.loader.load_from_file(invalid_path)
        finally:
            invalid_path.unlink()

    def test_load_from_file_validation_error(self) -> None:
        """Test loading from file with validation errors."""
        invalid_config = {
            "mcp": {
                "port": "not_a_number",  # Should be int
                "max_concurrent_requests": -1,  # Should be positive
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(
                ConfigValidationError, match="Configuration validation failed"
            ):
                self.loader.load_from_file(config_path)
        finally:
            config_path.unlink()

    def test_load_from_file_empty_file(self) -> None:
        """Test loading from empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            config_path = Path(f.name)

        try:
            config = self.loader.load_from_file(config_path)
            # Should load with default values
            assert isinstance(config, ApplicationConfig)
            assert config.mcp.enabled is False  # Default value
        finally:
            config_path.unlink()

    def test_merge_configs_empty(self) -> None:
        """Test merging with no configs provided."""
        result = self.loader.merge_configs()
        assert isinstance(result, ApplicationConfig)

    def test_merge_configs_single(self) -> None:
        """Test merging with single config."""
        config = ApplicationConfig()
        result = self.loader.merge_configs(config)
        assert result == config

    def test_merge_configs_multiple(self) -> None:
        """Test merging multiple configurations."""
        # Create base config with some values
        base_data = {"mcp": {"enabled": False, "port": 8080}}
        base_config = ApplicationConfig(**base_data)

        # Create override config with different values
        override_data = {"mcp": {"enabled": True, "host": "0.0.0.0"}}
        override_config = ApplicationConfig(**override_data)

        # Merge configs
        result = self.loader.merge_configs(base_config, override_config)

        # Override values should take precedence
        assert result.mcp.enabled is True  # From override
        assert result.mcp.host == "0.0.0.0"  # From override
        assert result.mcp.port == 8080  # From base (not overridden)

    def test_merge_configs_deep_merge(self) -> None:
        """Test deep merging of nested configurations."""
        # Base config with nested structure
        config1 = ApplicationConfig(
            mcp=MCPConfig(enabled=False, port=8080, max_concurrent_requests=5),
            logging={"level": "INFO"},
        )

        # Override config with partial nested updates
        config2 = ApplicationConfig(
            mcp=MCPConfig(enabled=True, cache_size_mb=1024),  # Only some MCP fields
            logging={"level": "DEBUG"},  # Different logging level
        )

        result = self.loader.merge_configs(config1, config2)

        # MCP config should be merged
        assert result.mcp.enabled is True  # From config2
        assert result.mcp.port == 8080  # From config1 (preserved)
        assert (
            result.mcp.max_concurrent_requests == 10
        )  # Default (config2 used defaults)
        assert result.mcp.cache_size_mb == 1024  # From config2

        # Logging should be overridden
        assert result.logging.level == "DEBUG"  # From config2

    def test_validate_config_valid(self) -> None:
        """Test validation of valid configuration."""
        config = ApplicationConfig()
        result = self.loader.validate_config(config)
        assert result == config

    def test_validate_config_invalid(self) -> None:
        """Test validation of invalid configuration."""
        # Create config with invalid data by bypassing normal validation
        config_data = {
            "mcp": {
                "port": -1,  # Invalid port
                "max_concurrent_requests": 0,  # Invalid value
            }
        }

        # Create config bypassing validation temporarily
        config = ApplicationConfig.model_construct(**config_data)

        with pytest.raises(
            ConfigValidationError, match="Configuration validation failed"
        ):
            self.loader.validate_config(config)

    def test_load_with_overrides_defaults_only(self) -> None:
        """Test loading with default values only."""
        config = self.loader.load_with_overrides()

        assert isinstance(config, ApplicationConfig)
        assert config.mcp.enabled is False
        assert config.mcp.host == "localhost"
        assert config.mcp.port == 8080

    def test_load_with_overrides_file_only(self) -> None:
        """Test loading with file override only."""
        test_config = {"mcp": {"enabled": True, "port": 9000}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            config = self.loader.load_with_overrides(
                config_file=config_path, env_overrides=False
            )

            assert config.mcp.enabled is True
            assert config.mcp.port == 9000
            assert config.mcp.host == "localhost"  # Default value preserved
        finally:
            config_path.unlink()

    def test_load_with_overrides_env_variables(self) -> None:
        """Test loading with environment variable overrides."""
        # Set environment variables with DND5E_ prefix
        test_env = {
            "DND5E_MCP__ENABLED": "true",
            "DND5E_MCP__PORT": "7777",
            "DND5E_LOGGING__LEVEL": "WARNING",
        }

        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = self.loader.load_with_overrides(env_overrides=True)

            assert config.mcp.enabled is True
            assert config.mcp.port == 7777
            assert config.logging.level == "WARNING"
        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    def test_load_with_overrides_precedence(self) -> None:
        """Test precedence order: defaults < file < env."""
        # Create config file
        file_config = {"mcp": {"enabled": True, "port": 9000, "host": "file-host"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(file_config, f)
            config_path = Path(f.name)

        # Set environment variables (should override file)
        env_vars = {
            "DND5E_MCP__ENABLED": "true",  # Override file enabled to test precedence
            "DND5E_MCP__PORT": "8888",
            "DND5E_MCP__MAX_CONCURRENT_REQUESTS": "25",
            "DND5E_MCP__HOST": "env-host",  # Override file host to test precedence
        }

        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = self.loader.load_with_overrides(
                config_file=config_path, env_overrides=True
            )

            # From env: host overrides file value
            assert config.mcp.host == "env-host"  # From env (overrides file)
            # From env: enabled overrides file value
            assert config.mcp.enabled is True  # From env (overrides file)
            # From env: port overrides file value
            assert config.mcp.port == 8888  # From env (overrides file)
            # From env: max_concurrent_requests overrides default
            assert config.mcp.max_concurrent_requests == 25  # From env
        finally:
            config_path.unlink()
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    def test_deep_merge_dicts(self) -> None:
        """Test deep dictionary merging functionality."""
        base = {
            "level1": {
                "level2": {"keep": "original", "override": "original"},
                "keep_dict": {"keep": "value"},
            },
            "keep_top": "value",
        }

        override = {
            "level1": {
                "level2": {"override": "new", "new": "added"},
                "new_dict": {"new": "value"},
            },
            "new_top": "value",
        }

        result = self.loader._deep_merge_dicts(base, override)

        # Check that deep merge preserves and overrides correctly
        assert result["level1"]["level2"]["keep"] == "original"  # Preserved
        assert result["level1"]["level2"]["override"] == "new"  # Overridden
        assert result["level1"]["level2"]["new"] == "added"  # Added
        assert result["level1"]["keep_dict"]["keep"] == "value"  # Preserved nested dict
        assert result["level1"]["new_dict"]["new"] == "value"  # Added nested dict
        assert result["keep_top"] == "value"  # Preserved top level
        assert result["new_top"] == "value"  # Added top level
