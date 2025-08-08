"""Tests for VariantRule content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestVariantRuleMigration:
    """Test VariantRule content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_variantrule_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers VariantRule automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "VARIANTRULE")
        assert ContentType.VARIANTRULE == "variantrule"

    def test_variantrule_content_factory_integration(self) -> None:
        """Test VariantRule works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a core rule
        ability_check_data = {
            "name": "Ability Check",
            "source": {"abbreviation": "XPHB", "full": "Player's Handbook 2024"},
            "page": 360,
            "srd52": True,
            "basicRules2024": True,
            "ruleType": "C",
            "entries": [
                "An ability check is a {@variantrule D20 Test|XPHB} that represents using one of the six abilities—or a specific skill associated with an ability—to overcome a challenge."
            ],
        }

        content = factory.create_content(ability_check_data, ContentType.VARIANTRULE)

        assert content.name == "Ability Check"
        assert content.source.abbreviation == "XPHB"
        assert content.is_core_rule() is True
        assert content.is_variant_rule() is False
        assert content.is_srd_content() is True
        assert content.is_basic_rules_content() is True
        assert content.get_rule_type_description() == "Core Rule"

    def test_variantrule_optional_rule_data(self) -> None:
        """Test VariantRule with optional rule data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an optional rule
        accelerated_rest_data = {
            "name": "Accelerated Rests",
            "source": {
                "abbreviation": "TDCSR",
                "full": "Tal'Dorei Campaign Setting Reborn",
            },
            "page": 213,
            "ruleType": "O",
            "entries": [
                "Certain adventures thrive on the adrenaline of the chase or the ever-present fear of ambush.",
                "One way to make {@quickref resting|PHB|2|0|short rests} less intrusive is to let characters take one in a reduced amount of time.",
                "In a campaign that implements this option, a character must finish a {@quickref resting|PHB|2|0|long rest} before they can take an accelerated {@quickref resting|PHB|2|0|short rest} again.",
            ],
        }

        content = factory.create_content(accelerated_rest_data, ContentType.VARIANTRULE)

        assert content.name == "Accelerated Rests"
        assert content.is_optional_rule() is True
        assert content.is_core_rule() is False
        assert content.get_rule_type_description() == "Optional Rule"
        assert content.has_content() is True
        assert content.get_entry_count() == 3

    def test_variantrule_with_prerequisites_and_implementation(self) -> None:
        """Test VariantRule with prerequisites and implementation details."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test rule with prerequisites and implementation
        complex_rule_data = {
            "name": "Advanced Combat Options",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "ruleType": "V",
            "prerequisites": [
                "Characters must be at least 3rd level.",
                "DM must approve use of these rules.",
            ],
            "implements": ["Combat Maneuvers", "Called Shots"],
            "replaces": ["Basic Attack Rules"],
            "entries": [
                "These advanced combat options provide more tactical depth to combat encounters.",
                "Players can choose to use these options instead of standard attack actions.",
            ],
        }

        content = factory.create_content(complex_rule_data, ContentType.VARIANTRULE)

        assert content.name == "Advanced Combat Options"
        assert content.is_variant_rule() is True
        assert content.has_prerequisites() is True
        assert content.implements_rules() is True
        assert content.replaces_rules() is True
        assert len(content.get_implemented_rules()) == 2
        assert len(content.get_replaced_rules()) == 1
        assert "Combat Maneuvers" in content.get_implemented_rules()
        assert "Basic Attack Rules" in content.get_replaced_rules()

    def test_variantrule_availability_summary(self) -> None:
        """Test VariantRule availability summary functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test SRD content
        srd_data = {
            "name": "SRD Rule",
            "source": {"abbreviation": "SRD", "full": "System Reference Document"},
            "srd": True,
            "basicRules": True,
            "ruleType": "C",
            "entries": ["This is an SRD rule."],
        }

        content = factory.create_content(srd_data, ContentType.VARIANTRULE)
        availability = content.get_availability_summary()
        assert "SRD" in availability
        assert "Basic Rules" in availability

        # Test 2024 content
        srd52_data = {
            "name": "SRD 5.2 Rule",
            "source": {"abbreviation": "XPHB", "full": "Player's Handbook 2024"},
            "srd52": True,
            "basicRules2024": True,
            "ruleType": "C",
            "entries": ["This is a 2024 rule."],
        }

        content2 = factory.create_content(srd52_data, ContentType.VARIANTRULE)
        availability2 = content2.get_availability_summary()
        assert "SRD 5.2" in availability2
        assert "Basic Rules 2024" in availability2

        # Test legacy content
        legacy_data = {
            "name": "Legacy Rule",
            "source": {"abbreviation": "OLD", "full": "Old Source"},
            "legacy": True,
            "ruleType": "V",
            "entries": ["This is a legacy rule."],
        }

        content3 = factory.create_content(legacy_data, ContentType.VARIANTRULE)
        availability3 = content3.get_availability_summary()
        assert "Legacy" in availability3

    def test_variantrule_rule_type_enum(self) -> None:
        """Test VariantRule rule type enum functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.variantrule import RuleType

        factory = ContentFactory()

        # Test different rule types
        rule_types = [
            ("C", RuleType.CORE, "Core Rule"),
            ("O", RuleType.OPTIONAL, "Optional Rule"),
            ("V", RuleType.VARIANT, "Variant Rule"),
            ("LA", RuleType.LAIR_ACTION, "Lair Action"),
            ("RE", RuleType.REGIONAL_EFFECT, "Regional Effect"),
            ("INVALID", RuleType.UNKNOWN, "Unknown Rule Type"),
        ]

        for rule_type_code, expected_enum, expected_desc in rule_types:
            rule_data = {
                "name": f"Test {rule_type_code} Rule",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "ruleType": rule_type_code,
                "entries": [f"This is a {rule_type_code} rule."],
            }

            content = factory.create_content(rule_data, ContentType.VARIANTRULE)
            assert content.get_rule_type() == expected_enum
            assert content.get_rule_type_description() == expected_desc

    def test_variantrule_lair_action_and_regional_effect(self) -> None:
        """Test VariantRule lair action and regional effect types."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test lair action rule
        lair_action_data = {
            "name": "Dragon Lair Action",
            "source": {"abbreviation": "MM", "full": "Monster Manual"},
            "ruleType": "LA",
            "entries": [
                "On initiative count 20 (losing initiative ties), the dragon takes a lair action to cause one of the following effects."
            ],
        }

        content = factory.create_content(lair_action_data, ContentType.VARIANTRULE)
        assert content.is_lair_action() is True
        assert content.is_regional_effect() is False

        # Test regional effect rule
        regional_effect_data = {
            "name": "Dragon Regional Effect",
            "source": {"abbreviation": "MM", "full": "Monster Manual"},
            "ruleType": "RE",
            "entries": [
                "The region containing a legendary dragon's lair is warped by the dragon's magic."
            ],
        }

        content2 = factory.create_content(regional_effect_data, ContentType.VARIANTRULE)
        assert content2.is_regional_effect() is True
        assert content2.is_lair_action() is False

    def test_variantrule_modification_summary(self) -> None:
        """Test VariantRule modification summary functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive modification rule
        complex_data = {
            "name": "Complex Modification Rule",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "ruleType": "V",
            "prerequisites": ["Level 5+", "Fighter class"],
            "implements": [
                "Advanced Maneuvers",
                "Tactical Options",
                "Combat Expertise",
            ],
            "replaces": ["Basic Combat", "Simple Attacks"],
            "entries": ["This rule modifies many aspects of combat."],
        }

        content = factory.create_content(complex_data, ContentType.VARIANTRULE)
        modification_summary = content.get_modification_summary()

        assert "implements 3 rules" in modification_summary
        assert "replaces 2 rules" in modification_summary
        assert "has prerequisites" in modification_summary

        # Test standalone rule
        standalone_data = {
            "name": "Standalone Rule",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "ruleType": "O",
            "entries": ["This rule stands alone."],
        }

        content2 = factory.create_content(standalone_data, ContentType.VARIANTRULE)
        modification_summary2 = content2.get_modification_summary()
        assert modification_summary2 == "standalone rule"

    def test_variantrule_classification_summary(self) -> None:
        """Test VariantRule classification summary."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test classification with type and availability
        classified_data = {
            "name": "Combat Rule",
            "source": {"abbreviation": "XPHB", "full": "Player's Handbook 2024"},
            "type": "Combat Enhancement",
            "ruleType": "V",
            "srd52": True,
            "entries": ["Enhanced combat rules."],
        }

        content = factory.create_content(classified_data, ContentType.VARIANTRULE)
        classification = content.get_rule_classification()

        assert "Variant Rule (Combat Enhancement)" in classification
        assert "SRD 5.2" in classification

    def test_variantrule_minimal_data(self) -> None:
        """Test VariantRule with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Rule",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "entries": ["This is a minimal rule."],
        }

        content = factory.create_content(minimal_data, ContentType.VARIANTRULE)

        assert content.name == "Minimal Rule"
        assert content.is_variant_rule() is True  # Default rule type
        assert content.has_prerequisites() is False
        assert content.implements_rules() is False
        assert content.replaces_rules() is False
        assert content.is_srd_content() is False
        assert content.is_basic_rules_content() is False
        assert content.is_legacy_content() is False
        assert content.has_content() is True
        assert content.get_entry_count() == 1

    def test_variantrule_validation_errors(self) -> None:
        """Test VariantRule validation errors."""
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
                "entries": ["Rule content."],
            }
            factory.create_content(invalid_data, ContentType.VARIANTRULE)

    def test_variantrule_list_validation(self) -> None:
        """Test VariantRule list field validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test string to list conversion
        string_data = {
            "name": "String Test Rule",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "implements": "Single Rule",  # String should convert to list
            "replaces": "Old Rule",  # String should convert to list
            "entries": ["Rule content."],
        }

        content = factory.create_content(string_data, ContentType.VARIANTRULE)
        assert content.get_implemented_rules() == ["Single Rule"]
        assert content.get_replaced_rules() == ["Old Rule"]

    def test_variantrule_omnidexer_integration(self) -> None:
        """Test VariantRule integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify VariantRule is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.VARIANTRULE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.VARIANTRULE in json_types

    def test_variantrule_file_patterns(self) -> None:
        """Test VariantRule file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify VariantRule patterns are registered
        assert ContentType.VARIANTRULE in content_patterns
        patterns = content_patterns[ContentType.VARIANTRULE]
        assert "variantrule" in patterns
        assert "variantrules" in patterns

    def test_variantrule_registry_consistency(self) -> None:
        """Test that VariantRule registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has VariantRule
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        variantrule_registration = registrations.get("variantrule")
        assert variantrule_registration is not None
        assert variantrule_registration.enum_value == "variantrule"

        # Check ContentFactory has VariantRule
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.VARIANTRULE in supported_factory_types

        # Check Omnidexer has VariantRule
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.VARIANTRULE in supported_omnidexer_types
