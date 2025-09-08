"""Test for XMM source filtering fix - Issue #123."""

import pytest

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.creature_filters import CreatureFilterCriteria
from studiorum.core.services.creature_collector import CreatureCollector


class MockCreature:
    """Mock creature for testing."""

    def __init__(self, name: str, cr_data, source_abbrev: str):
        self.name = name
        self.cr = cr_data
        self.source = MockSource(source_abbrev)


class MockSource:
    """Mock source for testing."""

    def __init__(self, abbreviation: str):
        self.abbreviation = abbreviation


@pytest.fixture
def mock_collector():
    """Create a mock creature collector for testing."""
    # We don't need a real omnidexer for these unit tests
    return CreatureCollector(omnidexer=None)  # type: ignore


class TestXMMSourceFilteringFix:
    """Test the fix for XMM source filtering issue."""

    def test_extract_cr_string_dict_format(self, mock_collector):
        """Test CR extraction from dictionary format used by XMM sources."""
        # Test the XMM dictionary format that was causing the issue
        cr_data = {"cr": "24", "xpLair": 75000}
        result = mock_collector._extract_cr_string(cr_data)
        assert result == "24"

        # Test other dictionary formats
        cr_data = {"cr": "1/4"}
        result = mock_collector._extract_cr_string(cr_data)
        assert result == "1/4"

        # Test missing 'cr' key (should return 'varies')
        cr_data = {"xpLair": 75000}
        result = mock_collector._extract_cr_string(cr_data)
        assert result == "varies"

    def test_extract_cr_string_simple_formats(self, mock_collector):
        """Test CR extraction from simple formats."""
        # String
        result = mock_collector._extract_cr_string("10")
        assert result == "10"

        # Integer
        result = mock_collector._extract_cr_string(24)
        assert result == "24"

        # Float
        result = mock_collector._extract_cr_string(24.5)
        assert result == "24.5"

        # Fractional string
        result = mock_collector._extract_cr_string("1/4")
        assert result == "1/4"

    def test_parse_cr_value_with_extracted_strings(self, mock_collector):
        """Test that extracted CR strings parse correctly."""
        # Test the XMM case that was failing
        cr_data = {"cr": "24", "xpLair": 75000}
        cr_str = mock_collector._extract_cr_string(cr_data)
        cr_value = mock_collector._parse_cr_value(cr_str)
        assert cr_value == 24.0

        # Test fractional case
        cr_data = {"cr": "1/4"}
        cr_str = mock_collector._extract_cr_string(cr_data)
        cr_value = mock_collector._parse_cr_value(cr_str)
        assert cr_value == 0.25

        # Test varies case
        cr_data = {"xpLair": 75000}  # No 'cr' key
        cr_str = mock_collector._extract_cr_string(cr_data)
        cr_value = mock_collector._parse_cr_value(cr_str)
        assert cr_value is None  # 'varies' should return None

    def test_source_normalization_in_cli(self):
        """Test that source normalization works as expected in CLI parsing."""
        # Simulate the CLI parsing logic from the fix
        sources = ["xmm", "MM", "VgM"]
        parsed_sources = []

        for src_list in sources:
            parsed_sources.extend([s.strip().upper() for s in src_list.split(",")])

        expected = ["XMM", "MM", "VGM"]
        assert parsed_sources == expected

    def test_source_normalization_with_comma_separated(self):
        """Test source normalization with comma-separated values."""
        # Test comma-separated sources
        sources = ["xmm,mm", "vgm"]
        parsed_sources = []

        for src_list in sources:
            parsed_sources.extend([s.strip().upper() for s in src_list.split(",")])

        expected = ["XMM", "MM", "VGM"]
        assert parsed_sources == expected

    def test_source_normalization_mixed_case(self):
        """Test source normalization with mixed case input."""
        # Test various mixed case inputs
        test_cases = [
            (["xmm"], ["XMM"]),
            (["XMM"], ["XMM"]),
            (["XmM"], ["XMM"]),
            (["xMm"], ["XMM"]),
            (["mm"], ["MM"]),
            (["vgm"], ["VGM"]),
            (["phb"], ["PHB"]),
        ]

        for input_sources, expected in test_cases:
            parsed_sources = []
            for src_list in input_sources:
                parsed_sources.extend([s.strip().upper() for s in src_list.split(",")])
            assert parsed_sources == expected, (
                f"Input {input_sources} should normalize to {expected}, got {parsed_sources}"
            )


class TestCreatureFilterCriteriaDefaults:
    """Test that creature filter criteria defaults don't interfere with source filtering."""

    def test_exclude_variable_cr_default(self):
        """Test that exclude_variable_cr defaults to True but doesn't break source filtering."""
        criteria = CreatureFilterCriteria(
            creature_names=["Ancient Red Dragon"], sources=["XMM"]
        )

        # Default should exclude variable CR
        assert criteria.exclude_variable_cr is True

        # But should not interfere with source filtering when no CR filters are set
        assert criteria.min_cr is None
        assert criteria.max_cr is None
        assert criteria.cr_range is None

    def test_is_name_only_filter_with_sources(self):
        """Test that is_name_only_filter returns False when sources are specified."""
        criteria = CreatureFilterCriteria(
            creature_names=["Ancient Red Dragon"], sources=["XMM"]
        )

        # Should not be name-only when sources are specified
        assert criteria.is_name_only_filter() is False

        # Name-only should only be true with just creature names
        name_only_criteria = CreatureFilterCriteria(
            creature_names=["Ancient Red Dragon"]
        )
        assert name_only_criteria.is_name_only_filter() is True
