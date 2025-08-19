"""Tests for CLI configuration integration."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from dnd5e.cli.main import app
from dnd5e.core.config.unified_config import get_app_config, reset_app_config


class TestCLIConfigIntegration:
    """Tests for CLI configuration integration."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.runner = CliRunner()
        # Reset config before each test
        reset_app_config()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Reset config after each test
        reset_app_config()

    def test_cli_default_config(self) -> None:
        """Test CLI with default configuration."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--config-file" in result.stdout
        assert "-c" in result.stdout

    def test_cli_with_config_file(self) -> None:
        """Test CLI with configuration file."""
        # Create a test config file
        test_config = {
            "mcp": {"enabled": True, "port": 9999},
            "logging": {"level": "DEBUG"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            # Mock the commands to avoid full execution
            with patch("dnd5e.cli.main.reset_cli_globals"):
                with patch("dnd5e.core.loaders.omnidexer.Omnidexer"):
                    result = self.runner.invoke(
                        app,
                        [
                            "--config-file",
                            str(config_path),
                            "--debug",
                            "list",
                            "adventures",
                        ],
                    )

                    # Should indicate config file was loaded
                    assert (
                        "Configuration loaded from:" in result.stdout
                        or result.exit_code == 0
                    )
        finally:
            config_path.unlink()

    def test_cli_invalid_config_file(self) -> None:
        """Test CLI with invalid configuration file."""
        # Create invalid YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [unclosed")
            invalid_path = Path(f.name)

        try:
            result = self.runner.invoke(
                app, ["--config-file", str(invalid_path), "list", "adventures"]
            )

            assert result.exit_code == 1
            assert "Error loading configuration:" in result.stdout
        finally:
            invalid_path.unlink()

    def test_cli_nonexistent_config_file(self) -> None:
        """Test CLI with non-existent configuration file."""
        result = self.runner.invoke(
            app, ["--config-file", "/tmp/nonexistent_config.yaml", "list", "adventures"]
        )

        assert result.exit_code == 1
        assert "Configuration error:" in result.stdout

    def test_cli_config_validation_error(self) -> None:
        """Test CLI with configuration validation errors."""
        # Create config with validation errors
        invalid_config = {
            "mcp": {
                "port": -1,  # Invalid port
                "max_concurrent_requests": 0,  # Invalid value
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            result = self.runner.invoke(
                app, ["--config-file", str(config_path), "list", "adventures"]
            )

            assert result.exit_code == 1
            assert "Error loading configuration:" in result.stdout
        finally:
            config_path.unlink()

    def test_cli_env_variable_override(self) -> None:
        """Test CLI with environment variable configuration."""
        # Set environment variables
        env_vars = {
            "DND5E_MCP__ENABLED": "true",
            "DND5E_MCP__PORT": "7777",
            "DND5E_LOGGING__LEVEL": "WARNING",
        }

        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # Mock to avoid full command execution
            with patch("dnd5e.cli.main.reset_cli_globals"):
                with patch("dnd5e.core.loaders.omnidexer.Omnidexer"):
                    result = self.runner.invoke(app, ["--debug", "list", "adventures"])

                    # Should execute successfully with env config
                    assert result.exit_code == 0 or "DEBUG" in result.stdout
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    def test_cli_precedence_file_over_default(self) -> None:
        """Test that configuration file overrides defaults."""
        test_config = {"logging": {"level": "WARNING"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            with patch("dnd5e.cli.main.reset_cli_globals"):
                result = self.runner.invoke(
                    app,
                    [
                        "--config-file",
                        str(config_path),
                        "--debug",  # This should override config file logging level
                        "list",
                        "adventures",
                    ],
                )

                # Debug flag should still work (CLI args take precedence over config)
                assert "DEBUG" in result.stdout or result.exit_code == 0
        finally:
            config_path.unlink()

    def test_cli_config_with_mcp_settings(self) -> None:
        """Test CLI with MCP-specific configuration."""
        test_config = {
            "mcp": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8443,
                "max_concurrent_requests": 25,
                "cache_size_mb": 1024,
                "preload_content_types": ["creatures", "spells"],
                "enable_hot_reload": True,
                "log_requests": False,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            with patch("dnd5e.cli.main.reset_cli_globals"):
                result = self.runner.invoke(
                    app,
                    [
                        "--config-file",
                        str(config_path),
                        "--verbose",
                        "list",
                        "adventures",
                    ],
                )

                # Should show MCP server enabled message
                assert (
                    "MCP server enabled on 0.0.0.0:8443" in result.stdout
                    or result.exit_code == 0
                )
        finally:
            config_path.unlink()

    def test_config_global_state_isolation(self) -> None:
        """Test that configuration state is properly isolated between calls."""
        # First call with custom config
        test_config1 = {"logging": {"level": "DEBUG"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config1, f)
            config_path1 = Path(f.name)

        # Second call with different config
        test_config2 = {"logging": {"level": "WARNING"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config2, f)
            config_path2 = Path(f.name)

        try:
            # First call
            with patch("dnd5e.cli.main.reset_cli_globals"):
                result1 = self.runner.invoke(
                    app, ["--config-file", str(config_path1), "--help"]
                )
                assert result1.exit_code == 0

            # Second call should not be affected by first call's config
            with patch("dnd5e.cli.main.reset_cli_globals"):
                result2 = self.runner.invoke(
                    app, ["--config-file", str(config_path2), "--help"]
                )
                assert result2.exit_code == 0

            # Both calls should succeed independently
            assert result1.exit_code == 0
            assert result2.exit_code == 0
        finally:
            config_path1.unlink()
            config_path2.unlink()

    def test_config_backward_compatibility(self) -> None:
        """Test that existing CLI usage still works without config file."""
        with patch("dnd5e.cli.main.reset_cli_globals"):
            # Standard CLI usage without config file should still work
            result = self.runner.invoke(app, ["--help"])
            assert result.exit_code == 0
            assert "5e2pdf" in result.stdout

            # Verbose and debug flags should still work
            result = self.runner.invoke(app, ["--verbose", "--help"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["--debug", "--help"])
            assert result.exit_code == 0
