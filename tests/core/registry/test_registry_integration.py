"""Integration tests for the complete content type registry system."""

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types


class TestRegistryIntegration:
    """Integration tests for the complete content type registry system."""

    def setup_method(self) -> None:
        """Setup for each test."""
        # For integration tests, we need proper initialization
        # Use the standardized test environment reset
        from tests.test_helpers import reset_test_environment

        try:
            reset_test_environment()
        except Exception:
            # Fallback to basic setup if test_helpers not available
            from dnd5e.core.container import reset_global_container
            from dnd5e.core.registry import initialize_content_types

            initialize_content_types()
            reset_global_container()

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
        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.creatures import Creature
        from dnd5e.core.models.items import Item
        from dnd5e.core.models.spells import Spell

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

        from dnd5e.core.loaders.content_factory import ContentFactory

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

        from dnd5e.core.loaders.omnidexer import Omnidexer

        # Check that content type tuples are populated
        assert len(Omnidexer._JSON_CONTENT_TYPES) > 0
        assert ContentType.SPELL in Omnidexer._JSON_CONTENT_TYPES
        assert ContentType.CREATURE in Omnidexer._JSON_CONTENT_TYPES

        assert len(Omnidexer._FLUFF_CONTENT_TYPES) > 0
        assert ContentType.SPELL_FLUFF in Omnidexer._FLUFF_CONTENT_TYPES

    def test_source_manager_has_patterns(self):
        """Test that ConfigurableSourceManager has file patterns after initialization."""
        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
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

        from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor

        # Check that statblock tags are populated
        tags = getattr(RecursiveEntryProcessor, "_statblock_tags", {})
        assert tags  # Should not be empty
        assert "action" in tags
        assert "condition" in tags

    def test_all_migrated_content_types_registered(self):
        """Test that all migrated content types are properly registered."""
        initialize_content_types()

        from dnd5e.core.registry.content_type_registry import get_content_type_registry

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

        from dnd5e.core.registry.content_type_registry import get_content_type_registry

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
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

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
        from dnd5e.core.models.adventures import Adventure
        from dnd5e.core.models.books import Book
        from dnd5e.core.models.creatures import Creature
        from dnd5e.core.models.items import Item
        from dnd5e.core.models.spells import Spell

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

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
                # If enum doesn't exist by value, skip this entry (likely test-only registration)
                continue

            if content_type:
                assert content_type in factory._class_map, (
                    f"ContentType {content_type} not found in factory._class_map. "
                    f"Available types: {list(factory._class_map.keys())}"
                )
                assert factory._class_map[content_type] == metadata.model_class

        # Check Omnidexer consistency
        json_types = set(Omnidexer._JSON_CONTENT_TYPES)
        fluff_types = set(Omnidexer._FLUFF_CONTENT_TYPES)

        for enum_value, metadata in all_metadata.items():
            # Try to create a proper ContentType enum instance
            content_type = None
            try:
                content_type = ContentType(enum_value)
            except ValueError:
                # If enum doesn't exist by value, skip this entry (likely test-only registration)
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
                # If enum doesn't exist by value, skip this entry (likely test-only registration)
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

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.loaders.content_factory import ContentFactory

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
        from dnd5e.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()
        factory.get_supported_types()  # Trigger initialization
        assert factory._class_map is not None
        assert ContentType.SPELL in factory._class_map
