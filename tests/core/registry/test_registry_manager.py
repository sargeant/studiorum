"""Tests for registry manager functionality."""

from unittest.mock import Mock, patch

from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.registry.content_type_registry import ContentTypeMetadata
from studiorum.core.registry.registry_manager import RegistryManager


class MockBaseContent(BaseContent):
    """Mock content class for testing."""


class TestRegistryManager:
    """Test RegistryManager functionality."""

    def test_apply_registrations_calls_all_updates(self):
        """Test that apply_registrations calls all update methods."""
        manager = RegistryManager()
        metadata = {}

        with patch.multiple(
            manager,
            _update_source_manager=Mock(),
            _update_omnidexer=Mock(),
            _update_content_factory=Mock(),
            _update_content_type_resolver=Mock(),
        ):
            manager.apply_registrations(metadata)

            manager._update_source_manager.assert_called_once_with(metadata)
            manager._update_omnidexer.assert_called_once_with(metadata)
            manager._update_content_factory.assert_called_once_with(metadata)
            manager._update_content_type_resolver.assert_called_once_with(metadata)

    def test_update_source_manager(self):
        """Test updating source manager patterns."""
        manager = RegistryManager()

        # Use existing enum value instead of creating a fake one
        metadata = {
            "spell": ContentTypeMetadata(
                enum_value="spell",
                model_class=MockBaseContent,
                file_patterns=["test", "tests"],
            )
        }

        # Create mock class with content_patterns attribute
        mock_source_manager_class = Mock()
        mock_source_manager_class.content_patterns = {}

        with patch(
            "studiorum.core.loaders.unified_source_manager.UnifiedSourceManager",
            mock_source_manager_class,
        ):
            manager._update_source_manager(metadata)

            # Check that patterns were replaced using ContentType constructor
            spell_content_type = ContentType("spell")
            assert spell_content_type in mock_source_manager_class.content_patterns
            assert mock_source_manager_class.content_patterns[spell_content_type] == [
                "test",
                "tests",
            ]

    def test_update_source_manager_import_error(self):
        """Test handling of import error in source manager update."""
        manager = RegistryManager()

        # Patch the actual import location to raise ImportError
        with patch(
            "studiorum.core.loaders.unified_source_manager.UnifiedSourceManager",
            side_effect=ImportError,
        ):
            # Should not raise, just log warning
            manager._update_source_manager({})

    def test_update_omnidexer(self):
        """Test updating omnidexer - dynamic system requires no static updates."""
        manager = RegistryManager()

        # Use existing enum values
        metadata = {
            "spell": ContentTypeMetadata(
                enum_value="spell",
                model_class=MockBaseContent,
                file_patterns=["json"],
                loader_type="json",
            ),
            "spellFluff": ContentTypeMetadata(
                enum_value="spellFluff",
                model_class=MockBaseContent,
                file_patterns=["fluff"],
                loader_type="fluff",
            ),
        }

        # In the dynamic system, omnidexer update should complete without errors
        # and not modify any static attributes (since dynamic resolution is used)
        with patch(
            "studiorum.core.loaders.omnidexer.Omnidexer"
        ) as mock_omnidexer_class:
            manager._update_omnidexer(metadata)

            # The update should complete successfully - no static updates needed
            # because dynamic resolution happens automatically
            mock_omnidexer_class.assert_not_called()

    def test_update_omnidexer_import_error(self):
        """Test handling of import error in omnidexer update."""
        manager = RegistryManager()

        # Patch the actual import location to raise ImportError
        with patch(
            "studiorum.core.loaders.omnidexer.Omnidexer", side_effect=ImportError
        ):
            # Should not raise, just log warning
            manager._update_omnidexer({})

    def test_update_content_factory(self):
        """Test updating content factory class map."""
        manager = RegistryManager()

        # Use existing enum value
        metadata = {
            "creature": ContentTypeMetadata(
                enum_value="creature",
                model_class=MockBaseContent,
                file_patterns=["test"],
            )
        }

        # Create mock class with _class_map attribute
        mock_factory_class = Mock()
        mock_factory_class._class_map = {}

        with patch(
            "studiorum.core.loaders.content_factory.ContentFactory", mock_factory_class
        ):
            manager._update_content_factory(metadata)

            # Check that class map was replaced using ContentType constructor
            creature_content_type = ContentType("creature")
            assert creature_content_type in mock_factory_class._class_map
            assert (
                mock_factory_class._class_map[creature_content_type] == MockBaseContent
            )

    def test_update_content_factory_import_error(self):
        """Test handling of import error in content factory update."""
        manager = RegistryManager()

        # Patch the actual import location to raise ImportError
        with patch(
            "studiorum.core.loaders.content_factory.ContentFactory",
            side_effect=ImportError,
        ):
            # Should not raise, just log warning
            manager._update_content_factory({})

    def test_update_content_type_resolver(self):
        """Test updating content type resolver registrations."""
        manager = RegistryManager()

        # Use existing enum value
        metadata = {
            "item": ContentTypeMetadata(
                enum_value="item",
                model_class=MockBaseContent,
                file_patterns=["test"],
            )
        }

        # Mock the interface registry that's actually used
        mock_interface_registry = Mock()
        mock_interface_registry.register = Mock()

        with patch(
            "studiorum.core.interfaces.get_content_type_registry",
            return_value=mock_interface_registry,
        ):
            manager._update_content_type_resolver(metadata)

            # Check that the interface registry was called with the correct parameters
            item_content_type = ContentType("item")
            mock_interface_registry.register.assert_called_once_with(
                MockBaseContent, item_content_type
            )

    def test_update_content_type_resolver_successful_registration(self):
        """Test successful resolver registration with valid metadata."""
        manager = RegistryManager()

        # Use existing static enum value
        metadata = {
            "spell": ContentTypeMetadata(
                enum_value="spell",
                model_class=MockBaseContent,
                file_patterns=["test"],
            )
        }

        # Mock the interface registry for successful registration
        mock_interface_registry = Mock()
        mock_interface_registry.register = Mock()

        with patch(
            "studiorum.core.interfaces.get_content_type_registry",
            return_value=mock_interface_registry,
        ):
            manager._update_content_type_resolver(metadata)

            # Check that register was called with correct parameters
            spell_content_type = ContentType("spell")
            mock_interface_registry.register.assert_called_once_with(
                MockBaseContent, spell_content_type
            )

    def test_update_content_type_resolver_import_error(self):
        """Test handling of import error in resolver update."""
        manager = RegistryManager()

        # Patch the interface import to raise ImportError
        with patch(
            "studiorum.core.interfaces.get_content_type_registry",
            side_effect=ImportError,
        ):
            # Should not raise, just log warning
            manager._update_content_type_resolver({})
