"""Tests for Deity content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestDeityMigration:
    """Test Deity content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_deity_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Deity automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "DEITY")
        assert ContentType.DEITY == "deity"

    def test_deity_content_factory_integration(self) -> None:
        """Test Deity works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a deity
        deity_data = {
            "name": "Moradin",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "pantheon": "Dwarven",
            "alignment": ["L", "G"],
            "title": "God of creation",
            "domains": ["Forge", "Knowledge"],
            "symbol": "Hammer and anvil",
            "entries": [
                "Moradin is the chief deity in the dwarven pantheon in the Dungeons & Dragons role-playing game."
            ],
        }

        content = factory.create_content(deity_data, ContentType.DEITY)

        assert content.name == "Moradin"
        assert content.pantheon == "Dwarven"
        assert content.alignment == ["L", "G"]
        assert content.title == "God of creation"
        assert content.domains == ["Forge", "Knowledge"]
        assert content.symbol == "Hammer and anvil"

    def test_deity_greek_pantheon_data(self) -> None:
        """Test Deity with Greek pantheon data structure."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a Greek deity
        zeus_data = {
            "name": "Zeus",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "pantheon": "Greek",
            "alignment": ["C", "G"],
            "title": "God of the sky, ruler of the gods",
            "domains": ["Tempest"],
            "symbol": "Fist full of lightning bolts",
            "province": ["Sky", "Thunder", "Justice"],
            "altNames": ["Jupiter"],
            "entries": [
                "As the ruler of the Olympian deities, Zeus is the god of the sky and weather, but he's also a mighty king."
            ],
        }

        content = factory.create_content(zeus_data, ContentType.DEITY)

        assert content.name == "Zeus"
        assert content.pantheon == "Greek"
        assert content.alignment == ["C", "G"]
        assert content.domains == ["Tempest"]
        assert content.province == ["Sky", "Thunder", "Justice"]
        assert content.alt_names == ["Jupiter"]

    def test_deity_true_neutral_alignment(self) -> None:
        """Test Deity with True Neutral alignment."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a neutral deity
        neutral_deity_data = {
            "name": "Oghma",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "pantheon": "Faerûnian",
            "alignment": ["N", "N"],  # True Neutral
            "title": "God of knowledge",
            "domains": ["Knowledge"],
            "symbol": "Blank scroll",
            "entries": ["Oghma is the god of knowledge and invention."],
        }

        content = factory.create_content(neutral_deity_data, ContentType.DEITY)

        assert content.name == "Oghma"
        assert content.alignment == ["N", "N"]
        # Test display method
        alignment_display = content.get_alignment_display()
        assert alignment_display == "True Neutral"

    def test_deity_alignment_validation(self) -> None:
        """Test deity alignment validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with invalid alignment components (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Invalid Deity",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "pantheon": "Test",
                "alignment": ["X", "Y"],  # Invalid components
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.DEITY)

        # Test with empty alignment (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Invalid Deity",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "pantheon": "Test",
                "alignment": [],  # Empty alignment
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.DEITY)

    def test_deity_pantheon_validation(self) -> None:
        """Test pantheon validation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty pantheon (should fail)
        with pytest.raises(ValidationError):  # Pydantic validation error
            invalid_data = {
                "name": "Invalid Deity",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "pantheon": "",  # Empty pantheon
                "alignment": ["L", "G"],
                "entries": [],
            }
            factory.create_content(invalid_data, ContentType.DEITY)

    def test_deity_helper_methods(self) -> None:
        """Test deity helper methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test helper methods
        deity_data = {
            "name": "Pelor",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "pantheon": "Greyhawk",
            "alignment": ["N", "G"],
            "title": "God of the sun",
            "domains": ["Life", "Light"],
            "symbol": "Sun face with rays",
            "entries": [],
        }

        content = factory.create_content(deity_data, ContentType.DEITY)

        # Test alignment display
        alignment_display = content.get_alignment_display()
        assert alignment_display == "Neutral Good"

        # Test pantheon display
        pantheon_display = content.get_pantheon_display()
        assert pantheon_display == "Greyhawk"  # No special formatting for this pantheon

        # Test primary domain
        primary_domain = content.get_primary_domain()
        assert primary_domain == "Life"

        # Test pantheon check
        assert content.is_from_pantheon("Greyhawk") is True
        assert content.is_from_pantheon("Dwarven") is False

        # Test domain check
        assert content.has_domain("Life") is True
        assert content.has_domain("Tempest") is False

    def test_deity_special_alignments(self) -> None:
        """Test deities with special alignment cases."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test unaligned deity
        unaligned_data = {
            "name": "Test Unaligned",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "pantheon": "Test",
            "alignment": ["U"],
            "entries": [],
        }

        content = factory.create_content(unaligned_data, ContentType.DEITY)
        alignment_display = content.get_alignment_display()
        assert alignment_display == "Unaligned"

        # Test single neutral
        neutral_data = {
            "name": "Test Neutral",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "pantheon": "Test",
            "alignment": ["N"],
            "entries": [],
        }

        content = factory.create_content(neutral_data, ContentType.DEITY)
        alignment_display = content.get_alignment_display()
        assert alignment_display == "Neutral"

    def test_deity_omnidexer_integration(self) -> None:
        """Test Deity integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Deity is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.DEITY in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.DEITY in json_types

    def test_deity_file_patterns(self) -> None:
        """Test Deity file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Deity patterns are registered
        assert ContentType.DEITY in content_patterns
        patterns = content_patterns[ContentType.DEITY]
        assert "deity" in patterns
        assert "deities" in patterns

    def test_deity_registry_consistency(self) -> None:
        """Test that Deity registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Deity
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        deity_registration = registrations.get("deity")
        assert deity_registration is not None
        assert deity_registration.enum_value == "deity"

        # Check ContentFactory has Deity
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.DEITY in supported_factory_types

        # Check Omnidexer has Deity
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.DEITY in supported_omnidexer_types
