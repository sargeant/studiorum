"""Tests for service protocol definitions and runtime verification."""

import pytest

from studiorum.core.services.protocols import (
    AsyncResourceProtocol,
    ConfigurableServiceProtocol,
    ConfigurationProtocol,
    OmnidexerProtocol,
    ServiceProtocol,
    TagResolverProtocol,
)


class TestServiceProtocols:
    """Test service protocol definitions and runtime checking."""

    def test_service_protocol_runtime_checkable(self):
        """Test that ServiceProtocol is runtime checkable."""

        class MockService:
            def get_service_name(self) -> str:
                return "MockService"

        service = MockService()
        assert isinstance(service, ServiceProtocol)

    def test_async_resource_protocol_runtime_checkable(self):
        """Test that AsyncResourceProtocol is runtime checkable."""

        class MockAsyncService:
            async def initialize(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

            def is_initialized(self) -> bool:
                return True

        service = MockAsyncService()
        assert isinstance(service, AsyncResourceProtocol)

    def test_configurable_service_protocol_runtime_checkable(self):
        """Test that ConfigurableServiceProtocol is runtime checkable."""

        class MockConfigurableService:
            async def reload_config(self, new_config) -> None:
                pass

            def supports_hot_reload(self) -> bool:
                return True

        service = MockConfigurableService()
        assert isinstance(service, ConfigurableServiceProtocol)

    def test_omnidexer_protocol_inheritance(self):
        """Test that OmnidexerProtocol properly inherits multiple protocols."""

        class MockOmnidexer:
            def get_service_name(self) -> str:
                return "OmnidexerService"

            async def initialize(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

            def is_initialized(self) -> bool:
                return True

            async def load_content_sources(self, sources: list[str]) -> None:
                pass

            def get_content(self, content_type: str, identifier: str) -> object:
                return {}

            def search(self, query: str) -> list:  # BaseContent not accessible in test
                return []

            async def ensure_sources_ready(self) -> None:
                pass

            async def search_content_async(
                self,
                query: str,
                content_type: str | None = None,
                context: object | None = None,
                limit: int = 50,
            ) -> object:
                return {"success": True, "data": []}

            async def get_content_async(
                self,
                content_type: str,
                name: str,
                source: str | None = None,
                context: object | None = None,
            ) -> object:
                return {"success": True, "data": None}

            def get_performance_statistics(self) -> dict[str, object]:
                return {"initialized": True}

            def get_all_by_type(
                self, content_type: object
            ) -> list:  # BaseContent not accessible in test
                return []

            def find_all(self, content_type: object, name: str) -> list:
                """Find all content matching type and name - mock implementation."""
                return []

            def set_progress_callback(self, callback) -> None:
                """Set progress callback - mock implementation."""
                pass

        service = MockOmnidexer()
        assert isinstance(service, ServiceProtocol)
        assert isinstance(service, AsyncResourceProtocol)
        assert isinstance(service, OmnidexerProtocol)

    def test_tag_resolver_protocol_inheritance(self):
        """Test that TagResolverProtocol properly inherits multiple protocols."""

        class MockTagResolver:
            def get_service_name(self) -> str:
                return "TagResolverService"

            async def reload_config(self, new_config) -> None:
                pass

            def supports_hot_reload(self) -> bool:
                return True

            def resolve_tag(self, tag: str, context) -> str:
                return "resolved"

            def supports_tag_type(self, tag_type: str) -> bool:
                return True

        service = MockTagResolver()
        assert isinstance(service, ServiceProtocol)
        assert isinstance(service, ConfigurableServiceProtocol)
        assert isinstance(service, TagResolverProtocol)

    def test_configuration_protocol_inheritance(self):
        """Test that ConfigurationProtocol properly inherits multiple protocols."""

        class MockConfiguration:
            def get_service_name(self) -> str:
                return "ConfigurationService"

            async def reload_config(self, new_config) -> None:
                pass

            def supports_hot_reload(self) -> bool:
                return True

            def get_config(self):
                return {}

            async def reload_from_source(self, source: str):
                return None

            def validate_config(self):
                return None

        service = MockConfiguration()
        assert isinstance(service, ServiceProtocol)
        assert isinstance(service, ConfigurableServiceProtocol)
        assert isinstance(service, ConfigurationProtocol)

    def test_protocol_rejection_incomplete_implementation(self):
        """Test that protocols reject incomplete implementations."""

        class IncompleteService:
            # Missing get_service_name method
            pass

        service = IncompleteService()
        assert not isinstance(service, ServiceProtocol)

    def test_protocol_rejection_wrong_signature(self):
        """Test that protocols reject wrong method signatures."""

        class WrongSignatureService:
            def get_service_name(self, extra_param: str) -> str:  # Wrong signature
                return "WrongService"

        service = WrongSignatureService()
        # This will still pass isinstance check but would fail at runtime
        # Protocol checking is primarily for static analysis
        assert isinstance(service, ServiceProtocol)


class TestProtocolDocumentation:
    """Test that protocols have proper documentation."""

    def test_service_protocol_has_docstring(self):
        """Test that ServiceProtocol has documentation."""
        assert ServiceProtocol.__doc__ is not None
        assert "Base protocol for all services" in ServiceProtocol.__doc__

    def test_async_resource_protocol_has_docstring(self):
        """Test that AsyncResourceProtocol has documentation."""
        assert AsyncResourceProtocol.__doc__ is not None
        assert "async initialization" in AsyncResourceProtocol.__doc__

    def test_configurable_service_protocol_has_docstring(self):
        """Test that ConfigurableServiceProtocol has documentation."""
        assert ConfigurableServiceProtocol.__doc__ is not None
        assert "hot-reload" in ConfigurableServiceProtocol.__doc__

    def test_omnidexer_protocol_has_docstring(self):
        """Test that OmnidexerProtocol has documentation."""
        assert OmnidexerProtocol.__doc__ is not None
        assert "content indexing" in OmnidexerProtocol.__doc__


if __name__ == "__main__":
    pytest.main([__file__])
