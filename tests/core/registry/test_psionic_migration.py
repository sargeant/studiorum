"""Tests for Psionic content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestPsionicMigration:
    """Test Psionic content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_psionic_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Psionic automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "PSIONIC")
        assert ContentType.PSIONIC == "psionic"

    def test_psionic_content_factory_integration(self) -> None:
        """Test Psionic works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an Adaptive Body discipline
        adaptive_body_data = {
            "name": "Adaptive Body",
            "source": {"abbreviation": "UATheMysticClass", "full": "The Mystic Class"},
            "page": 10,
            "type": "D",
            "order": "Immortal",
            "entries": [
                "You can alter your body to match your surroundings, allowing you to withstand punishing environments."
            ],
            "focus": "While focused on this discipline, you don't need to eat, breathe, or sleep.",
            "modes": [
                {
                    "cost": {"min": 2, "max": 2},
                    "name": "Environmental Adaptation",
                    "entries": [
                        "As an action, you or a creature you touch ignores the effects of extreme heat or cold for the next hour."
                    ],
                },
                {
                    "cost": {"min": 3, "max": 3},
                    "name": "Adaptive Shield",
                    "entries": [
                        "When you take damage, you can use your reaction to gain resistance to that damage type."
                    ],
                },
            ],
        }

        content = factory.create_content(adaptive_body_data, ContentType.PSIONIC)

        assert content.name == "Adaptive Body"
        assert content.source.abbreviation == "UATheMysticClass"
        assert content.is_discipline() is True
        assert content.is_talent() is False
        assert content.get_order_description() == "Order of the Immortal"
        assert content.has_focus_effect() is True
        assert content.has_modes() is True
        assert content.get_mode_count() == 2

    def test_psionic_talent_data(self) -> None:
        """Test Psionic with talent data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.psionic import PsionicType

        factory = ContentFactory()

        # Test creating a psionic talent
        talent_data = {
            "name": "Mind Reading",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "T",
            "entries": ["You can read surface thoughts of nearby creatures."],
            "cost": {"min": 1, "max": 1},
            "concentration": {"duration": 1, "unit": "minute"},
        }

        content = factory.create_content(talent_data, ContentType.PSIONIC)

        assert content.name == "Mind Reading"
        assert content.get_psionic_type() == PsionicType.TALENT
        assert content.is_talent() is True
        assert content.is_discipline() is False
        assert content.has_cost() is True
        assert content.requires_concentration() is True
        assert content.get_min_cost() == 1
        assert content.get_max_cost() == 1
        assert content.get_cost_range() == "1 psi points"
        assert content.get_concentration_duration() == "1 minute"

    def test_psionic_order_validation(self) -> None:
        """Test Psionic order validation and description."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.psionic import PsionicOrder

        factory = ContentFactory()

        # Test different orders
        orders_data = [
            ("immortal", PsionicOrder.IMMORTAL, "Order of the Immortal"),
            ("avatar", PsionicOrder.AVATAR, "Order of the Avatar"),
            ("awakened", PsionicOrder.AWAKENED, "Order of the Awakened"),
            ("nomad", PsionicOrder.NOMAD, "Order of the Nomad"),
            ("wu jen", PsionicOrder.WU_JEN, "Order of the Wu Jen"),
            ("soul knife", PsionicOrder.SOUL_KNIFE, "Order of the Soul Knife"),
            ("unknown", PsionicOrder.UNKNOWN, "Unknown Order"),
        ]

        for order_value, expected_enum, expected_desc in orders_data:
            order_data = {
                "name": f"Test {order_value.title()} Discipline",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": "D",
                "order": order_value,
                "entries": [f"A {order_value} discipline."],
            }

            content = factory.create_content(order_data, ContentType.PSIONIC)
            assert content.get_order() == expected_enum
            assert content.get_order_description() == expected_desc
            assert content.belongs_to_order(order_value) is True

    def test_psionic_modes_and_submodes(self) -> None:
        """Test Psionic modes and submodes functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test discipline with modes and submodes
        complex_data = {
            "name": "Complex Discipline",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "D",
            "order": "awakened",
            "entries": ["A complex psionic discipline with multiple modes."],
            "modes": [
                {
                    "cost": {"min": 1, "max": 3},
                    "name": "Basic Mode",
                    "entries": ["Basic mode effect."],
                },
                {
                    "cost": {"min": 5, "max": 7},
                    "name": "Advanced Mode",
                    "entries": ["Advanced mode effect."],
                },
            ],
            "submodes": [
                {
                    "cost": {"min": 2, "max": 2},
                    "name": "Submode A",
                    "entries": ["Submode A effect."],
                },
            ],
        }

        content = factory.create_content(complex_data, ContentType.PSIONIC)

        assert content.has_modes() is True
        assert content.has_submodes() is True
        assert content.get_mode_count() == 2
        assert content.get_submode_count() == 1

        # Test getting modes by cost
        low_cost_modes = content.get_modes_by_cost(2)
        assert len(low_cost_modes) == 1
        assert low_cost_modes[0]["name"] == "Basic Mode"

        high_cost_modes = content.get_modes_by_cost(6)
        assert len(high_cost_modes) == 1
        assert high_cost_modes[0]["name"] == "Advanced Mode"

    def test_psionic_cost_range_functionality(self) -> None:
        """Test Psionic cost range calculations."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test fixed cost
        fixed_cost_data = {
            "name": "Fixed Cost Talent",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "T",
            "entries": ["A talent with fixed cost."],
            "cost": {"min": 3, "max": 3},
        }

        fixed_content = factory.create_content(fixed_cost_data, ContentType.PSIONIC)
        assert fixed_content.get_cost_range() == "3 psi points"

        # Test variable cost
        variable_cost_data = {
            "name": "Variable Cost Discipline",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "D",
            "entries": ["A discipline with variable cost."],
            "cost": {"min": 2, "max": 7},
        }

        variable_content = factory.create_content(
            variable_cost_data, ContentType.PSIONIC
        )
        assert variable_content.get_cost_range() == "2-7 psi points"

        # Test no cost
        no_cost_data = {
            "name": "Free Talent",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "T",
            "entries": ["A talent with no cost."],
        }

        no_cost_content = factory.create_content(no_cost_data, ContentType.PSIONIC)
        assert no_cost_content.get_cost_range() == "No cost"

    def test_psionic_level_and_prerequisites(self) -> None:
        """Test Psionic level requirements and prerequisites."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test high-level discipline with prerequisites
        advanced_data = {
            "name": "Master's Discipline",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "D",
            "order": "immortal",
            "level": 11,
            "prerequisites": ["Know 3 other immortal disciplines", "Mystic level 11+"],
            "entries": ["An advanced discipline for master mystics."],
            "cost": {"min": 9, "max": 9},
        }

        content = factory.create_content(advanced_data, ContentType.PSIONIC)

        assert content.has_level_requirement() is True
        assert content.has_prerequisites() is True
        assert content.get_minimum_level() == 11
        assert len(content.get_prerequisites_list()) == 2
        assert "Know 3 other immortal disciplines" in content.get_prerequisites_list()

    def test_psionic_complexity_rating(self) -> None:
        """Test Psionic complexity rating system."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test simple psionic
        simple_data = {
            "name": "Simple Talent",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "T",
            "entries": ["A simple psionic talent."],
        }

        simple_content = factory.create_content(simple_data, ContentType.PSIONIC)
        assert simple_content.get_complexity_rating() == "Simple"

        # Test complex psionic
        complex_data = {
            "name": "Master Discipline",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "D",
            "order": "wu jen",
            "entries": ["A very complex discipline."],
            "concentration": {"duration": 1, "unit": "hour"},
            "prerequisites": ["Prerequisite 1", "Prerequisite 2", "Prerequisite 3"],
            "modes": [
                {"name": "Mode 1", "cost": {"min": 1, "max": 1}},
                {"name": "Mode 2", "cost": {"min": 2, "max": 2}},
                {"name": "Mode 3", "cost": {"min": 3, "max": 3}},
            ],
            "submodes": [
                {"name": "Submode 1", "cost": {"min": 1, "max": 1}},
                {"name": "Submode 2", "cost": {"min": 2, "max": 2}},
            ],
        }

        complex_content = factory.create_content(complex_data, ContentType.PSIONIC)
        assert complex_content.get_complexity_rating() == "Complex"

    def test_psionic_summary_functionality(self) -> None:
        """Test Psionic summary generation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive summary
        summary_data = {
            "name": "Comprehensive Discipline",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "D",
            "order": "nomad",
            "cost": {"min": 3, "max": 7},
            "concentration": {"duration": 10, "unit": "minutes"},
            "modes": [
                {"name": "Mode 1", "cost": {"min": 3, "max": 3}},
                {"name": "Mode 2", "cost": {"min": 5, "max": 5}},
                {"name": "Mode 3", "cost": {"min": 7, "max": 7}},
            ],
            "entries": ["A discipline with all features."],
        }

        content = factory.create_content(summary_data, ContentType.PSIONIC)

        summary = content.get_psionic_summary()
        assert "Psionic Discipline" in summary
        assert "Order of the Nomad" in summary
        assert "3-7 psi points" in summary
        assert "3 modes" in summary
        assert "concentration 10 minutes" in summary
        assert "moderate complexity" in summary

    def test_psionic_minimal_data(self) -> None:
        """Test Psionic with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Psionic",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "T",
            "entries": ["A minimal psionic talent."],
        }

        content = factory.create_content(minimal_data, ContentType.PSIONIC)

        assert content.name == "Minimal Psionic"
        assert content.is_talent() is True
        assert content.get_order() is None
        assert content.get_order_description() == "No order"
        assert content.has_focus_effect() is False
        assert content.has_modes() is False
        assert content.has_cost() is False
        assert content.requires_concentration() is False

    def test_psionic_validation_errors(self) -> None:
        """Test Psionic validation errors."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty name
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "",  # Empty name should fail
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": "T",
                "entries": ["Test entry."],
            }
            factory.create_content(invalid_data, ContentType.PSIONIC)

    def test_psionic_omnidexer_integration(self) -> None:
        """Test Psionic integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Psionic is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.PSIONIC in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.PSIONIC in json_types

    def test_psionic_file_patterns(self) -> None:
        """Test Psionic file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Psionic patterns are registered
        assert ContentType.PSIONIC in content_patterns
        patterns = content_patterns[ContentType.PSIONIC]
        assert "psionic" in patterns
        assert "psionics" in patterns

    def test_psionic_registry_consistency(self) -> None:
        """Test that Psionic registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Psionic
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        psionic_registration = registrations.get("psionic")
        assert psionic_registration is not None
        assert psionic_registration.enum_value == "psionic"

        # Check ContentFactory has Psionic
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.PSIONIC in supported_factory_types

        # Check Omnidexer has Psionic
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.PSIONIC in supported_omnidexer_types
