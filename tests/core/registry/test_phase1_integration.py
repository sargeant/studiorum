"""Integration tests for all Phase 1 content types working together."""

import pytest

from tests.test_helpers import reset_test_environment


class TestPhase1Integration:
    """Test all Phase 1 content types working together in the registry system."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_all_phase1_content_types_registered(self) -> None:
        """Test that all Phase 1 content types are registered automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.models.content import ContentType

        # Verify all Phase 1 content types are registered
        expected_types = ["OPTIONALFEATURE", "SUBCLASS", "SUBRACE", "DEITY"]

        for type_name in expected_types:
            assert hasattr(ContentType, type_name)
            enum_value = getattr(ContentType, type_name)
            assert enum_value == type_name.lower()

    def test_phase1_content_factory_completeness(self) -> None:
        """Test that ContentFactory supports all Phase 1 content types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()
        supported_types = factory.get_supported_types()

        # Verify all Phase 1 types are supported
        phase1_types = [
            ContentType.OPTIONALFEATURE,
            ContentType.SUBCLASS,
            ContentType.SUBRACE,
            ContentType.DEITY,
        ]

        for content_type in phase1_types:
            assert content_type in supported_types

    def test_phase1_omnidexer_completeness(self) -> None:
        """Test that Omnidexer supports all Phase 1 content types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()
        supported_types = omnidexer.get_supported_types()

        # Verify all Phase 1 types are supported
        phase1_types = [
            ContentType.OPTIONALFEATURE,
            ContentType.SUBCLASS,
            ContentType.SUBRACE,
            ContentType.DEITY,
        ]

        for content_type in phase1_types:
            assert content_type in supported_types

        # Verify all Phase 1 types are in JSON content types
        json_types = omnidexer._JSON_CONTENT_TYPES
        for content_type in phase1_types:
            assert content_type in json_types

    def test_phase1_file_pattern_coverage(self) -> None:
        """Test that all Phase 1 content types have file patterns registered."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify all Phase 1 types have file patterns
        expected_patterns = {
            ContentType.OPTIONALFEATURE: ["optionalfeature", "optionalfeatures"],
            ContentType.SUBCLASS: ["class", "classes"],
            ContentType.SUBRACE: ["race", "races"],
            ContentType.DEITY: ["deity", "deities"],
        }

        for content_type, expected in expected_patterns.items():
            assert content_type in content_patterns
            patterns = content_patterns[content_type]
            for pattern in expected:
                assert pattern in patterns

    def test_phase1_registry_entries_exist(self) -> None:
        """Test that registry has entries for all Phase 1 content types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        registry = get_content_type_registry()
        all_registrations = registry.get_all()

        # Check that we have registrations for all Phase 1 types
        # all_registrations is a dict[str, ContentTypeMetadata]
        registered_enum_values = set(all_registrations.keys())

        expected_enum_values = {"optionalfeature", "subclass", "subrace", "deity"}

        for enum_value in expected_enum_values:
            assert enum_value in registered_enum_values

    def test_phase1_cross_content_type_functionality(self) -> None:
        """Test creating instances of all Phase 1 content types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Create sample data for each Phase 1 content type
        test_data = {
            ContentType.OPTIONALFEATURE: {
                "name": "Test Fighting Style",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "featureType": ["FS:F"],
                "entries": ["Test fighting style entry"],
            },
            ContentType.SUBCLASS: {
                "name": "Test Subclass",
                "shortName": "Test",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "className": "TestClass",
                "classSource": "TEST",
                "subclassFeatures": ["Feature|TestClass|TEST|Test||1"],
                "entries": [],
            },
            ContentType.SUBRACE: {
                "name": "Test Subrace",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "raceName": "TestRace",
                "raceSource": "TEST",
                "ability": [{"str": 1}],
                "entries": [],
            },
            ContentType.DEITY: {
                "name": "Test Deity",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "pantheon": "Test Pantheon",
                "alignment": ["L", "G"],
                "domains": ["Life"],
                "entries": [],
            },
        }

        # Verify we can create instances of all Phase 1 content types
        created_content = {}
        for content_type, data in test_data.items():
            content = factory.create_content(data, content_type)
            created_content[content_type] = content

            # Basic validation
            assert content.name.startswith("Test")
            assert content.source.abbreviation == "TEST"

        # Verify we got all expected content types
        assert len(created_content) == 4
        for content_type in test_data.keys():
            assert content_type in created_content

    def test_phase1_statblock_tag_coverage(self) -> None:
        """Test that Phase 1 content types have statblock tags where applicable."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.models.content import ContentType
        from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor

        # Get statblock tags from entry processor
        processor = RecursiveEntryProcessor({})
        statblock_tags = getattr(processor.__class__, "_statblock_tags", {})

        # Check that statblock tags exist for Phase 1 content types
        # statblock_tags maps tag -> enum_name (e.g., "optionalfeature" -> "OPTIONALFEATURE")
        expected_tags = ["optionalfeature", "subclass", "subrace", "deity"]

        for tag in expected_tags:
            # The tag should be mapped to the uppercase enum name
            assert tag in statblock_tags
            enum_name = statblock_tags[tag]
            assert enum_name == tag.upper()

    def test_phase1_coverage_percentage(self) -> None:
        """Test that Phase 1 achieves expected content type coverage."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.models.content import ContentType

        # Count all content types (both enum values and dynamically added ones)
        all_content_types = set()

        # Add base enum values
        for attr_name in dir(ContentType):
            if not attr_name.startswith("_") and attr_name.isupper():
                all_content_types.add(attr_name)

        # Phase 1 adds 4 new content types
        phase1_additions = {"OPTIONALFEATURE", "SUBCLASS", "SUBRACE", "DEITY"}

        # Verify Phase 1 content types are present
        for content_type in phase1_additions:
            assert content_type in all_content_types

        # With Phase 1 complete, we should have significantly more content types
        # than the original ~24 base types
        total_types = len(all_content_types)
        assert total_types >= 28  # Original ~24 + Phase 1 additions

    def test_phase1_system_consistency(self) -> None:
        """Test that all Phase 1 content types are consistently registered across all systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        phase1_types = [
            ContentType.OPTIONALFEATURE,
            ContentType.SUBCLASS,
            ContentType.SUBRACE,
            ContentType.DEITY,
        ]

        # Get registrations from each system
        registry = get_content_type_registry()
        factory = ContentFactory()
        omnidexer = Omnidexer()

        registry_types = set(registry.get_all().keys())
        factory_types = set(factory.get_supported_types())
        omnidexer_types = set(omnidexer.get_supported_types())
        source_manager_types = set(
            getattr(ConfigurableSourceManager, "content_patterns", {}).keys()
        )

        # Verify each Phase 1 type is registered in all systems
        for content_type in phase1_types:
            enum_value = content_type.value

            # Check registry
            assert enum_value in registry_types

            # Check content factory
            assert content_type in factory_types

            # Check omnidexer
            assert content_type in omnidexer_types

            # Check source manager
            assert content_type in source_manager_types

    def test_phase1_backwards_compatibility(self) -> None:
        """Test that Phase 1 additions don't break existing content types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test that existing content types still work
        existing_spell_data = {
            "name": "Test Spell",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "level": 1,
            "school": "A",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "instant"}],
            "entries": ["Test spell description"],
        }

        # This should still work with Phase 1 additions
        spell_content = factory.create_content(existing_spell_data, ContentType.SPELL)
        assert spell_content.name == "Test Spell"
        assert spell_content.level == 1

        # Verify we still have the expected number of supported types
        supported_types = factory.get_supported_types()
        # Should be original types + Phase 1 additions
        assert len(supported_types) >= 25  # Conservative estimate
