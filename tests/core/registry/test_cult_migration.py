"""Tests for Cult content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestCultMigration:
    """Test Cult content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_cult_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Cult automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "CULT")
        assert ContentType.CULT == "cult"

    def test_cult_content_factory_integration(self) -> None:
        """Test Cult works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Cult of Asmodeus
        cult_data = {
            "name": "Cult of Asmodeus",
            "source": {"abbreviation": "MTF", "full": "Mordenkainen's Tome of Foes"},
            "page": 21,
            "type": "Diabolical",
            "entries": [
                "{@deity Asmodeus|Faerûnian|scag} demands the loyalty of all cultists who gain power and leadership in the cults of the Nine. His cult subsumes all the others.",
                "Any NPC who leads a diabolical cult must acknowledge the power of Asmodeus. In return, the most worthy of those leaders gain the Demands of Nessus trait.",
                {
                    "type": "entries",
                    "name": "Demands of Nessus",
                    "entries": [
                        "At the start of each of this creature's turns, this creature can choose one ally it can see within 30 feet of it. The chosen ally loses 10 hit points, and this creature regains the same number of hit points. If the creature is {@condition incapacitated}, it makes no choice; instead, the closest ally within 30 feet is the chosen ally."
                    ],
                },
            ],
        }

        content = factory.create_content(cult_data, ContentType.CULT)

        assert content.name == "Cult of Asmodeus"
        assert content.source.abbreviation == "MTF"
        assert content.cult_type == "Diabolical"
        assert content.is_diabolical() is True
        assert content.get_cult_type() == "Diabolical"
        assert len(content.entries) == 3

    def test_cult_elder_evil_data(self) -> None:
        """Test Cult with elder evil data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an elder evil cult
        elder_evil_data = {
            "name": "Cult of Atropus, the World Born Dead",
            "source": {"abbreviation": "MTF", "full": "Mordenkainen's Tome of Foes"},
            "page": 237,
            "otherSources": [{"source": "MPMM", "page": 226}],
            "type": "Elder Evil",
            "goal": "Bring about the end of all life and creation",
            "entries": [
                {
                    "type": "entries",
                    "name": "The Cult of Atropus",
                    "entries": [
                        "Atropus is a primordial evil, a force of absolute entropy and death that seeks to end all existence.",
                        "His cultists work to weaken the barriers between life and death, preparing the way for their master's return.",
                    ],
                }
            ],
            "signatureSpells": [
                {
                    "1st": ["cause fear", "inflict wounds"],
                    "2nd": ["detect thoughts", "suggestion"],
                    "3rd": ["animate dead", "speak with dead"],
                    "4th": ["confusion", "death ward"],
                    "5th": ["cloudkill", "scrying"],
                }
            ],
        }

        content = factory.create_content(elder_evil_data, ContentType.CULT)

        assert content.name == "Cult of Atropus, the World Born Dead"
        assert content.cult_type == "Elder Evil"
        assert content.is_elder_evil() is True
        assert content.has_goal() is True
        assert content.goal == "Bring about the end of all life and creation"
        assert content.has_signature_spells() is True
        assert content.get_signature_spell_count() == 1

    def test_cult_with_cultists_data(self) -> None:
        """Test Cult with cultists data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating cult with cultists
        cult_with_cultists_data = {
            "name": "Cult of the Dragon",
            "source": {"abbreviation": "HotDQ", "full": "Hoard of the Dragon Queen"},
            "type": "Dragon Cult",
            "cultists": [
                {"name": "Dragon Cultist", "source": "HotDQ", "cr": "1/8"},
                {"name": "Dragonwing", "source": "HotDQ", "cr": "2"},
                {"name": "Dragonclaw", "source": "HotDQ", "cr": "2"},
            ],
            "goal": "Bring Tiamat back to the Material Plane",
            "entries": [
                "The Cult of the Dragon seeks to transform the world into a realm where dragons rule supreme.",
                "Led by powerful dragon priests, the cult works to free their goddess Tiamat from her prison in Avernus.",
            ],
        }

        content = factory.create_content(cult_with_cultists_data, ContentType.CULT)

        assert content.name == "Cult of the Dragon"
        assert content.cult_type == "Dragon Cult"
        assert content.has_cultists() is True
        assert content.get_cultist_count() == 3
        assert content.has_goal() is True
        assert content.goal == "Bring Tiamat back to the Material Plane"

    def test_cult_minimal_data(self) -> None:
        """Test Cult with minimal data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating cult with minimal data
        minimal_data = {
            "name": "Minor Cult",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "entries": ["A small, local cult with limited influence."],
        }

        content = factory.create_content(minimal_data, ContentType.CULT)

        assert content.name == "Minor Cult"
        assert content.source.abbreviation == "TEST"
        assert content.get_cult_type() == "Unknown"  # Default when no type specified
        assert content.has_goal() is False
        assert content.has_cultists() is False
        assert content.has_signature_spells() is False
        assert content.get_cultist_count() == 0
        assert content.get_signature_spell_count() == 0

    def test_cult_helper_methods(self) -> None:
        """Test Cult helper methods and type checking."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test various cult types
        test_cases = [
            ("Diabolical", True, False),
            ("Elder Evil", False, True),
            ("DIABOLICAL", True, False),  # Case insensitive
            ("ELDER EVIL", False, True),  # Case insensitive
            ("Other Type", False, False),
        ]

        for cult_type, is_diabolical, is_elder_evil in test_cases:
            cult_data = {
                "name": f"Test Cult - {cult_type}",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": cult_type,
                "entries": ["Test cult entry."],
            }

            content = factory.create_content(cult_data, ContentType.CULT)

            assert content.is_diabolical() == is_diabolical
            assert content.is_elder_evil() == is_elder_evil

    def test_cult_validation_with_complex_data(self) -> None:
        """Test Cult validation with complex nested data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with reprinted content
        reprinted_data = {
            "name": "Reprinted Cult",
            "source": {"abbreviation": "MTF", "full": "Mordenkainen's Tome of Foes"},
            "type": "Fiendish",
            "reprintedAs": [{"source": "MPMM", "page": 150}],
            "entries": ["This cult was reprinted in a later book."],
        }

        content = factory.create_content(reprinted_data, ContentType.CULT)

        assert content.name == "Reprinted Cult"
        assert content.reprinted_as is not None
        assert len(content.reprinted_as) == 1
        assert content.reprinted_as[0]["source"] == "MPMM"

    def test_cult_validation_errors(self) -> None:
        """Test Cult validation with invalid data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty name (should fail)
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "",  # Empty name should fail
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": "Test",
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.CULT)

    def test_cult_omnidexer_integration(self) -> None:
        """Test Cult integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Cult is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.CULT in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.CULT in json_types

    def test_cult_file_patterns(self) -> None:
        """Test Cult file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Cult patterns are registered
        assert ContentType.CULT in content_patterns
        patterns = content_patterns[ContentType.CULT]
        assert "cult" in patterns
        assert "cults" in patterns
        assert "cultsboons" in patterns

    def test_cult_registry_consistency(self) -> None:
        """Test that Cult registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Cult
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        cult_registration = registrations.get("cult")
        assert cult_registration is not None
        assert cult_registration.enum_value == "cult"

        # Check ContentFactory has Cult
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.CULT in supported_factory_types

        # Check Omnidexer has Cult
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.CULT in supported_omnidexer_types
