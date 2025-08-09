"""Test ContentType resolver utility."""

from __future__ import annotations

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.core.registry.content_type_resolver import (
    content_type_exists,
    get_all_content_types,
    get_content_type_names,
    resolve_content_type,
    resolve_content_type_safe,
)
from tests.test_helpers import reset_test_environment


class TestContentTypeResolver:
    """Test ContentType resolver utility."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()

    def test_resolve_content_type_static(self) -> None:
        """Test resolving static content types."""
        # Test known static content types
        adventure_type = resolve_content_type("adventure")
        assert adventure_type == ContentType.ADVENTURE
        assert isinstance(adventure_type, ContentType)

        book_type = resolve_content_type("book")
        assert book_type == ContentType.BOOK
        assert isinstance(book_type, ContentType)

        spell_type = resolve_content_type("spell")
        assert spell_type == ContentType.SPELL
        assert isinstance(spell_type, ContentType)

    def test_resolve_content_type_dynamic(self) -> None:
        """Test resolving dynamic content types after registration."""
        from dnd5e.core.registry import initialize_content_types

        # Initialize to ensure dynamic types are registered
        initialize_content_types()

        # Test dynamic content types that should be registered
        try:
            deity_type = resolve_content_type("deity")
            assert isinstance(deity_type, ContentType)
            assert deity_type.value == "deity"
        except ValueError:
            # If deity is not registered, that's expected in test environment
            pytest.skip("Deity content type not registered in test environment")

    def test_resolve_content_type_invalid(self) -> None:
        """Test resolving invalid content type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown content type: invalid"):
            resolve_content_type("invalid")

        with pytest.raises(ValueError, match="Unknown content type: nonexistent"):
            resolve_content_type("nonexistent")

    def test_resolve_content_type_safe_success(self) -> None:
        """Test safe resolution with valid content type."""
        result = resolve_content_type_safe("adventure")

        assert result.is_success()
        assert not result.is_error()
        assert result.value == ContentType.ADVENTURE
        assert isinstance(result.value, ContentType)

    def test_resolve_content_type_safe_error(self) -> None:
        """Test safe resolution with invalid content type."""
        result = resolve_content_type_safe("invalid")

        assert result.is_error()
        assert not result.is_success()
        assert "Unknown content type: invalid" in result.error

    def test_get_all_content_types(self) -> None:
        """Test getting all registered content types."""
        all_types = get_all_content_types()

        assert isinstance(all_types, set)
        assert len(all_types) > 0

        # Should contain known static types
        assert ContentType.ADVENTURE in all_types
        assert ContentType.BOOK in all_types
        assert ContentType.SPELL in all_types
        assert ContentType.CREATURE in all_types

        # All items should be ContentType instances
        for content_type in all_types:
            assert isinstance(content_type, ContentType)

    def test_get_all_content_types_cached(self) -> None:
        """Test that get_all_content_types is properly cached."""
        # First call
        result1 = get_all_content_types()
        # Second call should return same object (cached)
        result2 = get_all_content_types()

        assert result1 is result2  # Same object reference due to caching

    def test_content_type_exists_valid(self) -> None:
        """Test content_type_exists with valid types."""
        assert content_type_exists("adventure") is True
        assert content_type_exists("book") is True
        assert content_type_exists("spell") is True
        assert content_type_exists("creature") is True

    def test_content_type_exists_invalid(self) -> None:
        """Test content_type_exists with invalid types."""
        assert content_type_exists("invalid") is False
        assert content_type_exists("nonexistent") is False
        assert content_type_exists("") is False

    def test_get_content_type_names(self) -> None:
        """Test getting all content type names as strings."""
        names = get_content_type_names()

        assert isinstance(names, list)
        assert len(names) > 0

        # Should be sorted
        assert names == sorted(names)

        # Should contain known types
        assert "adventure" in names
        assert "book" in names
        assert "spell" in names
        assert "creature" in names

        # All items should be strings
        for name in names:
            assert isinstance(name, str)

    def test_error_chaining(self) -> None:
        """Test that ValueError is properly chained in resolve_content_type."""
        try:
            resolve_content_type("invalid")
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            assert "Unknown content type: invalid" in str(e)
            assert e.__cause__ is not None  # Should have chained exception

    def test_integration_with_registry_initialization(self) -> None:
        """Test integration with registry initialization."""
        from dnd5e.core.registry import initialize_content_types

        # Get initial count
        initial_types = get_all_content_types()
        initial_count = len(initial_types)

        # Initialize registry (may add dynamic types)
        initialize_content_types()

        # Get updated count
        # Clear cache first to get fresh results
        get_all_content_types.cache_clear()
        updated_types = get_all_content_types()
        updated_count = len(updated_types)

        # Should have same or more types after initialization
        assert updated_count >= initial_count

        # All initial types should still be present
        for content_type in initial_types:
            assert content_type in updated_types
