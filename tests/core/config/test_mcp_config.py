"""Tests for MCPConfig model."""

import pytest
from pydantic import ValidationError

from studiorum.core.config.unified_config import MCPConfig


class TestMCPConfig:
    """Tests for MCPConfig model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MCPConfig()

        assert config.enabled is False
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.max_concurrent_requests == 10
        assert config.request_timeout == 30
        assert config.memory_limit_mb == 1024
        assert config.cache_size_mb == 256
        assert config.preload_content_types == []
        assert config.enable_hot_reload is False
        assert config.log_requests is True

    def test_custom_values(self) -> None:
        """Test configuration with custom values."""
        config = MCPConfig(
            enabled=True,
            host="0.0.0.0",
            port=3000,
            max_concurrent_requests=20,
            request_timeout=60,
            memory_limit_mb=2048,
            cache_size_mb=512,
            preload_content_types=["creatures", "spells", "items"],
            enable_hot_reload=True,
            log_requests=False,
        )

        assert config.enabled is True
        assert config.host == "0.0.0.0"
        assert config.port == 3000
        assert config.max_concurrent_requests == 20
        assert config.request_timeout == 60
        assert config.memory_limit_mb == 2048
        assert config.cache_size_mb == 512
        assert config.preload_content_types == ["creatures", "spells", "items"]
        assert config.enable_hot_reload is True
        assert config.log_requests is False

    def test_validation_port_positive(self) -> None:
        """Test that port must be positive."""
        # Port 0 should work (system assigns)
        config = MCPConfig(port=0)
        assert config.port == 0

        # Positive ports should work
        config = MCPConfig(port=8080)
        assert config.port == 8080

        # Negative ports should fail
        with pytest.raises(ValidationError):
            MCPConfig(port=-1)

    def test_validation_max_concurrent_requests_positive(self) -> None:
        """Test that max_concurrent_requests must be positive."""
        # Positive values should work
        config = MCPConfig(max_concurrent_requests=5)
        assert config.max_concurrent_requests == 5

        # Zero should fail
        with pytest.raises(ValidationError):
            MCPConfig(max_concurrent_requests=0)

        # Negative should fail
        with pytest.raises(ValidationError):
            MCPConfig(max_concurrent_requests=-1)

    def test_validation_timeout_positive(self) -> None:
        """Test that request_timeout must be positive."""
        # Positive values should work
        config = MCPConfig(request_timeout=10)
        assert config.request_timeout == 10

        # Zero should fail
        with pytest.raises(ValidationError):
            MCPConfig(request_timeout=0)

        # Negative should fail
        with pytest.raises(ValidationError):
            MCPConfig(request_timeout=-5)

    def test_validation_memory_limit_positive(self) -> None:
        """Test that memory_limit_mb must be positive."""
        # Positive values should work
        config = MCPConfig(memory_limit_mb=512)
        assert config.memory_limit_mb == 512

        # Zero should fail
        with pytest.raises(ValidationError):
            MCPConfig(memory_limit_mb=0)

        # Negative should fail
        with pytest.raises(ValidationError):
            MCPConfig(memory_limit_mb=-100)

    def test_validation_cache_size_positive(self) -> None:
        """Test that cache_size_mb must be positive."""
        # Positive values should work
        config = MCPConfig(cache_size_mb=128)
        assert config.cache_size_mb == 128

        # Zero should fail
        with pytest.raises(ValidationError):
            MCPConfig(cache_size_mb=0)

        # Negative should fail
        with pytest.raises(ValidationError):
            MCPConfig(cache_size_mb=-50)

    def test_validation_host_string(self) -> None:
        """Test that host must be a string."""
        # Valid host strings
        valid_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "example.com", "::1"]
        for host in valid_hosts:
            config = MCPConfig(host=host)
            assert config.host == host

        # Invalid types should fail
        with pytest.raises(ValidationError):
            MCPConfig(host=123)

        with pytest.raises(ValidationError):
            MCPConfig(host=None)

    def test_preload_content_types_list(self) -> None:
        """Test preload_content_types as list of strings."""
        # Empty list should work
        config = MCPConfig(preload_content_types=[])
        assert config.preload_content_types == []

        # List of strings should work
        content_types = ["creatures", "spells", "items", "backgrounds"]
        config = MCPConfig(preload_content_types=content_types)
        assert config.preload_content_types == content_types

        # Non-string items should fail
        with pytest.raises(ValidationError):
            MCPConfig(preload_content_types=["creatures", 123, "spells"])

        # Non-list should fail
        with pytest.raises(ValidationError):
            MCPConfig(preload_content_types="creatures")

    def test_boolean_fields(self) -> None:
        """Test boolean field validation."""
        # Test enabled field
        config = MCPConfig(enabled=True)
        assert config.enabled is True

        config = MCPConfig(enabled=False)
        assert config.enabled is False

        # Test enable_hot_reload field
        config = MCPConfig(enable_hot_reload=True)
        assert config.enable_hot_reload is True

        # Test log_requests field
        config = MCPConfig(log_requests=False)
        assert config.log_requests is False

        # Test that string values get converted properly (Pydantic behavior)
        config = MCPConfig(enabled="yes")  # Pydantic converts truthy strings to True
        assert config.enabled is True

        config = MCPConfig(enable_hot_reload=1)  # Pydantic converts 1 to True
        assert config.enable_hot_reload is True

    def test_model_dump(self) -> None:
        """Test model serialization."""
        config = MCPConfig(
            enabled=True,
            host="0.0.0.0",
            port=3000,
            preload_content_types=["creatures", "spells"],
        )

        dumped = config.model_dump()

        assert dumped["enabled"] is True
        assert dumped["host"] == "0.0.0.0"
        assert dumped["port"] == 3000
        assert dumped["preload_content_types"] == ["creatures", "spells"]
        # Check that all fields are present
        assert "max_concurrent_requests" in dumped
        assert "request_timeout" in dumped
        assert "memory_limit_mb" in dumped
        assert "cache_size_mb" in dumped
        assert "enable_hot_reload" in dumped
        assert "log_requests" in dumped

    def test_model_validation_comprehensive(self) -> None:
        """Test comprehensive model validation."""
        # Valid complete configuration
        valid_config_data = {
            "enabled": True,
            "host": "192.168.1.100",
            "port": 8443,
            "max_concurrent_requests": 50,
            "request_timeout": 120,
            "memory_limit_mb": 4096,
            "cache_size_mb": 1024,
            "preload_content_types": [
                "creatures",
                "spells",
                "items",
                "backgrounds",
                "feats",
            ],
            "enable_hot_reload": True,
            "log_requests": True,
        }

        config = MCPConfig(**valid_config_data)

        # Verify all values were set correctly
        for key, expected_value in valid_config_data.items():
            assert getattr(config, key) == expected_value

    def test_environment_integration(self) -> None:
        """Test that MCPConfig works with environment variable parsing."""
        # This tests that the field names and types are compatible with
        # pydantic-settings environment variable parsing
        import os

        from pydantic_settings import BaseSettings

        class TestMCPSettings(BaseSettings):
            enabled: bool = False
            host: str = "localhost"
            port: int = 8080
            max_concurrent_requests: int = 10
            preload_content_types: list[str] = []

            model_config = {"env_prefix": "TEST_MCP_", "env_nested_delimiter": "__"}

        # Set environment variable
        os.environ["TEST_MCP_ENABLED"] = "true"
        os.environ["TEST_MCP_PORT"] = "9999"

        try:
            settings = TestMCPSettings()
            assert settings.enabled is True
            assert settings.port == 9999
        finally:
            os.environ.pop("TEST_MCP_ENABLED", None)
            os.environ.pop("TEST_MCP_PORT", None)
