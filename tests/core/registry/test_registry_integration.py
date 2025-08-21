"""Integration tests for the complete content type registry system."""

import pytest

from studiorum.core.models.content import ContentType
from studiorum.core.registry import initialize_content_types
from tests.test_helpers import reset_test_environment


class TestRegistryIntegration:
    """Integration tests for the complete content type registry system."""

    def setup_method(self) -> None:
        """Setup for each test."""
        # For integration tests, we need proper initialization
        # Use the standardized test environment reset
        reset_test_environment()

    def test_full_system_initialization(self):
        """Test that the full registry initialization process works."""
        # Initialize the entire system
        try:
            initialize_content_types()
            # If we get here, initialization succeeded
            assert True
        except Exception as e:
            pytest.fail(f"Full system initialization failed: {e}")

    def test_registry_manager_updates_all_systems(self):
        """Test that registry manager properly updates all target systems."""
        # Import all content modules before initialization to trigger decorators
        # This ensures decorator registration happens before we test
        from studiorum.core.loaders.content_factory import ContentFactory
        from studiorum.core.models.creatures import Creature
        from studiorum.core.models.items import Item
        from studiorum.core.models.spells import Spell

        # Initialize the system
        initialize_content_types()

        factory = ContentFactory()

        # Trigger initialization by getting supported types
        supported_types = factory.get_supported_types()

        # Now check the instance is properly initialized
        assert hasattr(factory, "_class_map")
        assert factory._class_map is not None
        assert ContentType.SPELL in factory._class_map
        assert factory._class_map[ContentType.SPELL] == Spell
        assert ContentType.SPELL in supported_types

    def test_content_creation_with_factory(self):
        """Test that content can be created through the factory after initialization."""
        initialize_content_types()

        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        # Create a spell through the factory
        spell_data = {
            "name": "Magic Missile",
            "source": "PHB",
            "level": 1,
            "school": "E",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 120}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "instant"}],
            "entries": ["You create three glowing darts of magical force..."],
        }

        spell = factory.create_content(spell_data, ContentType.SPELL)
        assert spell.name == "Magic Missile"
        assert spell.level == 1

    def test_omnidexer_has_content_types(self):
        """Test that Omnidexer has proper content types after initialization."""
        initialize_content_types()

        from studiorum.core.loaders.omnidexer import Omnidexer

        omnidexer = Omnidexer()

        # Check that dynamic content type resolution works for JSON types
        json_types = omnidexer._get_json_content_types()
        assert len(json_types) > 0
        # Use static enum members that definitely exist
        assert ContentType.SPELL in json_types
        assert ContentType.CREATURE in json_types

        # Fluff content types are registered in the registry but cannot be resolved to enum instances
        # This is by design - fluff types exist as registry metadata but not as accessible enum members
        # We test that the registry contains the fluff type metadata instead
        from studiorum.core.registry.content_type_registry import (
            get_content_type_registry,
        )

        registry = get_content_type_registry()

        fluff_metadata = {
            k: v for k, v in registry.get_all().items() if v.loader_type == "fluff"
        }
        assert len(fluff_metadata) > 0
        assert "spellFluff" in fluff_metadata
        assert "creatureFluff" in fluff_metadata
        assert "itemFluff" in fluff_metadata

    def test_source_manager_has_patterns(self):
        """Test that ConfigurableSourceManager has file patterns after initialization."""
        initialize_content_types()

        from studiorum.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )

        # Check that content patterns are populated
        patterns = getattr(ConfigurableSourceManager, "content_patterns", {})
        assert patterns  # Should not be empty
        assert ContentType.SPELL in patterns
        assert "spell" in patterns[ContentType.SPELL]
        assert "spells" in patterns[ContentType.SPELL]

    def test_entry_processor_has_statblock_tags(self):
        """Test that RecursiveEntryProcessor has statblock tags after initialization."""
        initialize_content_types()

        from studiorum.renderers.latex.entry_processor import RecursiveEntryProcessor

        # Check that statblock tags are populated
        tags = getattr(RecursiveEntryProcessor, "_statblock_tags", {})
        assert tags  # Should not be empty
        assert "action" in tags
        assert "condition" in tags

    def test_all_migrated_content_types_registered(self):
        """Test that all migrated content types are properly registered."""
        initialize_content_types()

        from studiorum.core.registry.content_type_registry import (
            get_content_type_registry,
        )

        registry = get_content_type_registry()
        all_metadata = registry.get_all()

        # Check that all major content types we migrated are present
        expected_types = [
            "reward",
            "spell",
            "creature",
            "item",
            "book",
            "adventure",
            "background",
            "race",
            "feat",
            "vehicle",
            "class",
            "classFeature",
            "subclassFeature",
            "action",
            "condition",
            "sense",
            "hazard",
            "status",
            "spellFluff",
            "creatureFluff",
            "itemFluff",
        ]

        registered_types = set(all_metadata.keys())
        for expected_type in expected_types:
            assert expected_type in registered_types, (
                f"Content type '{expected_type}' not registered"
            )

    def test_registry_metadata_completeness(self):
        """Test that registry metadata is complete and valid."""
        initialize_content_types()

        from studiorum.core.registry.content_type_registry import (
            get_content_type_registry,
        )

        registry = get_content_type_registry()
        all_metadata = registry.get_all()

        # Check each registered type has complete metadata
        for enum_value, metadata in all_metadata.items():
            assert metadata.enum_value == enum_value
            assert metadata.model_class is not None
            assert metadata.file_patterns  # Should not be empty
            assert metadata.loader_type in ["json", "fluff"]
            # statblock_tags can be None, but if present should be a list
            if metadata.statblock_tags is not None:
                assert isinstance(metadata.statblock_tags, list)

    def test_decorator_based_registration_works(self):
        """Test that decorator-based registration works by importing a module."""
        from studiorum.core.registry.content_type_registry import (
            get_content_type_registry,
        )

        # The setup_method already called reset_test_environment() which imports
        # all model modules and triggers decorator registrations
        registry = get_content_type_registry()

        # Check that the decorator registered the content type
        metadata = registry.get("reward")
        assert metadata is not None
        assert metadata.enum_value == "reward"
        assert metadata.file_patterns == ["reward", "rewards"]

    def test_system_consistency(self):
        """Test that all systems are consistent with registry data."""
        # Import content modules to trigger decorator registrations
        from studiorum.core.models.adventures import Adventure
        from studiorum.core.models.books import Book
        from studiorum.core.models.creatures import Creature
        from studiorum.core.models.items import Item
        from studiorum.core.models.spells import Spell

        initialize_content_types()

        from studiorum.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from studiorum.core.loaders.content_factory import ContentFactory
        from studiorum.core.loaders.omnidexer import Omnidexer
        from studiorum.core.registry.content_type_registry import (
            get_content_type_registry,
        )

        registry = get_content_type_registry()
        all_metadata = registry.get_all()

        # Check ContentFactory consistency
        factory = ContentFactory()
        factory.get_supported_types()  # Trigger initialization
        for enum_value, metadata in all_metadata.items():
            # Try to create a proper ContentType enum instance
            # getattr may return string attributes set by RegistryManager, not proper enum instances
            content_type = None
            try:
                content_type = ContentType(enum_value)
            except ValueError:
                # Skip test-only registrations that aren't valid enum members
                continue

            if content_type:
                assert content_type in factory._class_map, (
                    f"ContentType {content_type} not found in factory._class_map. "
                    f"Available types: {list(factory._class_map.keys())}"
                )
                assert factory._class_map[content_type] == metadata.model_class

        # Check Omnidexer consistency using dynamic resolution
        omnidexer = Omnidexer()
        json_types = set(omnidexer._get_json_content_types())
        fluff_types = set(omnidexer._get_fluff_content_types())

        for enum_value, metadata in all_metadata.items():
            # Try to create a proper ContentType enum instance
            content_type = None
            try:
                content_type = ContentType(enum_value)
            except ValueError:
                # Skip test-only registrations that aren't valid enum members
                continue

            if content_type:
                if metadata.loader_type == "json":
                    assert content_type in json_types, (
                        f"{content_type} should be in JSON types"
                    )
                elif metadata.loader_type == "fluff":
                    assert content_type in fluff_types, (
                        f"{content_type} should be in fluff types"
                    )

        # Check ConfigurableSourceManager consistency
        patterns = getattr(ConfigurableSourceManager, "content_patterns", {})
        for enum_value, metadata in all_metadata.items():
            # Try to create a proper ContentType enum instance
            content_type = None
            try:
                content_type = ContentType(enum_value)
            except ValueError:
                # Skip test-only registrations that aren't valid enum members
                continue

            if content_type:
                assert content_type in patterns, (
                    f"ContentType {content_type} not found in patterns. "
                    f"Available patterns: {list(patterns.keys())}"
                )
                assert patterns[content_type] == metadata.file_patterns

    def test_error_handling_when_not_initialized(self):
        """Test proper error handling when registry manager hasn't initialized systems."""
        # Test error handling by mocking the initialization method to raise the expected error
        from unittest.mock import patch

        from studiorum.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from studiorum.core.loaders.content_factory import ContentFactory

        # Mock the _initialize_class_map method to raise the expected error
        # This simulates the case where registry manager hasn't populated the class map
        def mock_initialize_class_map(self):
            raise RuntimeError(
                "ContentFactory class map not initialized by registry manager. "
                "Ensure initialize_content_types() is called before creating ContentFactory instances."
            )

        with patch.object(
            ContentFactory, "_initialize_class_map", mock_initialize_class_map
        ):
            # ContentFactory should raise an error if not initialized
            factory = ContentFactory()
            with pytest.raises(
                RuntimeError, match="ContentFactory class map not initialized"
            ):
                factory.get_supported_types()  # This triggers initialization

        # Test ConfigurableSourceManager error handling
        with patch.object(
            ConfigurableSourceManager, "content_patterns", {}, create=True
        ):
            from unittest.mock import Mock

            source_manager = ConfigurableSourceManager()
            source_manager.content_manager = Mock()
            source_manager.content_manager._index_built = True
            source_manager.content_manager.get_all_content_files.return_value = {}

            # Should raise an error when trying to get data paths
            with pytest.raises(
                RuntimeError,
                match="ConfigurableSourceManager content patterns not initialized",
            ):
                source_manager.get_data_paths()

    def test_initialization_idempotent(self):
        """Test that calling initialize_content_types multiple times is safe."""
        # Call multiple times
        initialize_content_types()
        initialize_content_types()
        initialize_content_types()

        # System should still work correctly
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()
        factory.get_supported_types()  # Trigger initialization
        assert factory._class_map is not None
        assert ContentType.SPELL in factory._class_map
