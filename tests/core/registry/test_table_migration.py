"""Tests for Table content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestTableMigration:
    """Test Table content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_table_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Table automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "TABLE")
        assert ContentType.TABLE == "table"

    def test_table_content_factory_integration(self) -> None:
        """Test Table works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a treasure table
        treasure_data = {
            "name": "Treasure Hoard: Challenge 5—10",
            "source": {"abbreviation": "DMG", "full": "Dungeon Master's Guide"},
            "page": 137,
            "caption": "Treasure Hoard: Challenge 5—10",
            "colLabels": ["d100", "Coins", "Art Objects", "Magic Items"],
            "colStyles": ["col-2 text-center", "col-3", "col-3", "col-4"],
            "rollableColLabels": ["d100"],
            "rows": [
                ["01–60", "2d6 × 100 gp, 3d6 × 10 pp", "—", "—"],
                [
                    "61–65",
                    "2d6 × 100 gp, 3d6 × 10 pp",
                    "2d4 art objects (250 gp each)",
                    "—",
                ],
                [
                    "66–70",
                    "2d6 × 100 gp, 3d6 × 10 pp",
                    "2d4 art objects (250 gp each)",
                    "1d6 {@filter magic items|items|rarity=uncommon}",
                ],
                [
                    "71–95",
                    "2d6 × 100 gp, 3d6 × 10 pp",
                    "2d4 art objects (250 gp each)",
                    "1d4 {@filter magic items|items|rarity=uncommon}",
                ],
                [
                    "96–00",
                    "2d6 × 100 gp, 3d6 × 10 pp",
                    "2d4 art objects (250 gp each)",
                    "1 {@filter magic item|items|rarity=rare}",
                ],
            ],
        }

        content = factory.create_content(treasure_data, ContentType.TABLE)

        assert content.name == "Treasure Hoard: Challenge 5—10"
        assert content.source.abbreviation == "DMG"
        assert content.get_column_count() == 4
        assert content.get_row_count() == 5
        assert content.has_column_styles() is True
        assert content.has_caption() is True
        assert content.is_rollable() is True
        assert content.get_rollable_column_indices() == [0]

    def test_table_simple_lookup_data(self) -> None:
        """Test Table with simple lookup table data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating a simple lookup table
        lookup_data = {
            "name": "Condition Summary",
            "source": {"abbreviation": "PHB", "full": "Player's Handbook"},
            "page": 290,
            "colLabels": ["Condition", "Effect"],
            "rows": [
                [
                    "Blinded",
                    "A blinded creature can't see and automatically fails any ability check that requires sight.",
                ],
                [
                    "Charmed",
                    "A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects.",
                ],
                [
                    "Deafened",
                    "A deafened creature can't hear and automatically fails any ability check that requires hearing.",
                ],
                [
                    "Frightened",
                    "A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight.",
                ],
            ],
        }

        content = factory.create_content(lookup_data, ContentType.TABLE)

        assert content.name == "Condition Summary"
        assert content.get_column_count() == 2
        assert content.get_row_count() == 4
        assert content.has_column_styles() is False
        assert content.has_caption() is False
        assert content.is_rollable() is False
        assert content.is_rectangular() is True

    def test_table_with_introduction_and_outro(self) -> None:
        """Test Table with introduction and conclusion text."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test table with intro/outro
        intro_outro_data = {
            "name": "Random Encounters",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "intro": [
                "Use this table to generate random encounters in the wilderness.",
                "Roll a d20 and consult the appropriate row.",
            ],
            "colLabels": ["d20", "Encounter"],
            "rows": [
                ["1-5", "Pack of wolves"],
                ["6-10", "Traveling merchant"],
                ["11-15", "Bandit patrol"],
                ["16-20", "Ancient ruins"],
            ],
            "outro": [
                "Modify the encounters based on the party's level and location.",
                "Remember to consider the time of day and weather conditions.",
            ],
        }

        content = factory.create_content(intro_outro_data, ContentType.TABLE)

        assert content.name == "Random Encounters"
        assert content.has_introduction() is True
        assert content.has_conclusion() is True
        assert len(content.intro) == 2
        assert len(content.outro) == 2

    def test_table_data_access_methods(self) -> None:
        """Test Table data access methods."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test data access methods
        access_data = {
            "name": "Test Access Table",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "colLabels": ["A", "B", "C"],
            "rows": [
                ["A1", "B1", "C1"],
                ["A2", "B2", "C2"],
                ["A3", "B3"],  # Shorter row for testing
            ],
        }

        content = factory.create_content(access_data, ContentType.TABLE)

        # Test row access
        assert content.get_row_data(0) == ["A1", "B1", "C1"]
        assert content.get_row_data(1) == ["A2", "B2", "C2"]
        assert content.get_row_data(2) == ["A3", "B3"]
        assert content.get_row_data(5) is None  # Out of bounds

        # Test column access
        assert content.get_column_data(0) == ["A1", "A2", "A3"]
        assert content.get_column_data(1) == ["B1", "B2", "B3"]
        assert content.get_column_data(2) == ["C1", "C2", ""]  # Empty for short row
        assert content.get_column_data(5) == []  # Out of bounds

        # Test cell access
        assert content.get_cell_data(0, 0) == "A1"
        assert content.get_cell_data(1, 2) == "C2"
        assert content.get_cell_data(2, 2) is None  # Missing cell
        assert content.get_cell_data(5, 0) is None  # Out of bounds

        # Test column index lookup
        assert content.get_column_index("A") == 0
        assert content.get_column_index("B") == 1
        assert content.get_column_index("C") == 2
        assert content.get_column_index("D") is None

        # Test structure validation
        assert content.is_rectangular() is False  # Row 3 is shorter
        assert content.validate_structure() is True

    def test_table_rollable_columns(self) -> None:
        """Test Table rollable column functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test rollable columns
        rollable_data = {
            "name": "Random Events",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "colLabels": ["d100", "Time", "Event", "d6"],
            "rollableColLabels": ["d100", "d6"],
            "rows": [
                ["01-25", "Dawn", "Peaceful morning", "1-2"],
                ["26-50", "Noon", "Merchant encounter", "3-4"],
                ["51-75", "Dusk", "Bandit ambush", "5-6"],
                ["76-00", "Night", "Monster attack", "6"],
            ],
        }

        content = factory.create_content(rollable_data, ContentType.TABLE)

        assert content.is_rollable() is True
        rollable_indices = content.get_rollable_column_indices()
        assert rollable_indices == [0, 3]
        assert len(content.rollable_col_labels) == 2

    def test_table_include_reference(self) -> None:
        """Test Table that includes other tables."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test table include
        include_data = {
            "name": "Master Treasure Table",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "colLabels": ["Level Range", "See Table"],
            "rows": [
                ["1-4", "See {@table Individual Treasure: Challenge 0—4|DMG}"],
                ["5-10", "See {@table Individual Treasure: Challenge 5—10|DMG}"],
                ["11-16", "See {@table Individual Treasure: Challenge 11—16|DMG}"],
                ["17-20", "See {@table Individual Treasure: Challenge 17+|DMG}"],
            ],
            "tableInclude": {
                "name": "Individual Treasure: Challenge 5—10",
                "source": "DMG",
            },
        }

        content = factory.create_content(include_data, ContentType.TABLE)

        assert content.includes_other_table() is True
        assert content.get_referenced_table() == "Individual Treasure: Challenge 5—10"

    def test_table_summary_functionality(self) -> None:
        """Test Table summary generation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive table features
        summary_data = {
            "name": "Feature Test Table",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "caption": "Test Table Caption",
            "colLabels": ["d20", "Result"],
            "rollableColLabels": ["d20"],
            "intro": ["Introduction text"],
            "outro": ["Conclusion text"],
            "rows": [["1-10", "Low result"], ["11-20", "High result"]],
        }

        content = factory.create_content(summary_data, ContentType.TABLE)

        summary = content.get_table_summary()
        assert "2 rows" in summary
        assert "2 columns" in summary
        assert "1 rollable columns" in summary
        assert "with caption" in summary
        assert "with introduction" in summary
        assert "with conclusion" in summary

    def test_table_minimal_data(self) -> None:
        """Test Table with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Table",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "colLabels": ["Column"],
            "rows": [["Value"]],
        }

        content = factory.create_content(minimal_data, ContentType.TABLE)

        assert content.name == "Minimal Table"
        assert content.get_column_count() == 1
        assert content.get_row_count() == 1
        assert content.has_column_styles() is False
        assert content.has_caption() is False
        assert content.is_rollable() is False
        assert content.has_introduction() is False
        assert content.has_conclusion() is False
        assert content.includes_other_table() is False

    def test_table_validation_errors(self) -> None:
        """Test Table validation errors."""
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
                "colLabels": ["Column"],
                "rows": [["Value"]],
            }
            factory.create_content(invalid_data, ContentType.TABLE)

        # Test with empty column labels
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Test Table",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "colLabels": [],  # Empty colLabels should fail
                "rows": [["Value"]],
            }
            factory.create_content(invalid_data, ContentType.TABLE)

        # Test with empty rows
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Test Table",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "colLabels": ["Column"],
                "rows": [],  # Empty rows should fail
            }
            factory.create_content(invalid_data, ContentType.TABLE)

    def test_table_omnidexer_integration(self) -> None:
        """Test Table integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Table is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.TABLE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.TABLE in json_types

    def test_table_file_patterns(self) -> None:
        """Test Table file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Table patterns are registered
        assert ContentType.TABLE in content_patterns
        patterns = content_patterns[ContentType.TABLE]
        assert "table" in patterns
        assert "tables" in patterns

    def test_table_registry_consistency(self) -> None:
        """Test that Table registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Table
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        table_registration = registrations.get("table")
        assert table_registration is not None
        assert table_registration.enum_value == "table"

        # Check ContentFactory has Table
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.TABLE in supported_factory_types

        # Check Omnidexer has Table
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.TABLE in supported_omnidexer_types
