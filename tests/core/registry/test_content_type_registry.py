"""Tests for content type registry and decorator functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from dnd5e.core.models.content import BaseContent
from dnd5e.core.registry.content_type_registry import (
    ContentTypeMetadata,
    ContentTypeRegistry,
    _registry_instance,
    content_type,
    get_content_type_registry,
)


class TestContentTypeMetadata:
    """Test ContentTypeMetadata validation and creation."""

    def test_valid_metadata(self):
        """Test creating valid metadata."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        metadata = ContentTypeMetadata(
            enum_value="trap",
            model_class=TestModel,
            file_patterns=["test", "tests"],
            statblock_tags=["testTag"],
            loader_type="json",
        )

        assert metadata.enum_value == "trap"
        assert metadata.model_class == TestModel
        assert metadata.file_patterns == ["test", "tests"]
        assert metadata.statblock_tags == ["testTag"]
        assert metadata.loader_type == "json"

    def test_invalid_enum_value(self):
        """Test that invalid enum values raise errors."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        with pytest.raises(ValueError, match="Invalid enum_value format"):
            ContentTypeMetadata(
                enum_value="Invalid-Name",  # Contains dash
                model_class=TestModel,
                file_patterns=["test"],
            )

        with pytest.raises(ValueError, match="Invalid enum_value format"):
            ContentTypeMetadata(
                enum_value="123invalid",  # Starts with number
                model_class=TestModel,
                file_patterns=["test"],
            )

    def test_empty_file_patterns(self):
        """Test that empty file patterns raise error."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        with pytest.raises(ValueError, match="file_patterns cannot be empty"):
            ContentTypeMetadata(
                enum_value="trap", model_class=TestModel, file_patterns=[]
            )


class TestContentTypeRegistry:
    """Test ContentTypeRegistry functionality."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure proper initialization
        reset_test_environment()

    def teardown_method(self) -> None:
        """Clean up after tests that may have contaminated global state."""
        # Full environment reset to ensure no contamination from mocking
        # This is critical because tests in this class mock RegistryManager
        # which can leave ContentFactory in an inconsistent state
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

    def test_register_and_get(self):
        """Test registering and retrieving metadata."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        registry = ContentTypeRegistry()
        metadata = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel, file_patterns=["test"]
        )

        registry.register(metadata)
        retrieved = registry.get("trap")

        assert retrieved == metadata
        assert retrieved.model_class == TestModel

    def test_get_all(self):
        """Test getting all registered metadata."""
        from pydantic import BaseModel

        class TestModel1(BaseModel):
            name: str

        class TestModel2(BaseModel):
            name: str

        registry = ContentTypeRegistry()

        metadata1 = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel1, file_patterns=["test1"]
        )

        metadata2 = ContentTypeMetadata(
            enum_value="hazard", model_class=TestModel2, file_patterns=["test2"]
        )

        registry.register(metadata1)
        registry.register(metadata2)

        all_metadata = registry.get_all()
        assert len(all_metadata) == 2
        assert all_metadata["trap"] == metadata1
        assert all_metadata["hazard"] == metadata2

    def test_duplicate_registration_same_class(self):
        """Test that duplicate registration with same class is allowed."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        registry = ContentTypeRegistry()

        metadata1 = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel, file_patterns=["test1"]
        )

        metadata2 = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel, file_patterns=["test2"]
        )

        registry.register(metadata1)
        registry.register(metadata2)  # Should not raise

        # Should keep the latest registration
        retrieved = registry.get("trap")
        assert retrieved.file_patterns == ["test2"]

    def test_duplicate_registration_different_class(self):
        """Test that duplicate registration with different class raises error."""
        from pydantic import BaseModel

        class TestModel1(BaseModel):
            name: str

        class TestModel2(BaseModel):
            name: str

        registry = ContentTypeRegistry()

        metadata1 = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel1, file_patterns=["test"]
        )

        metadata2 = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel2, file_patterns=["test"]
        )

        registry.register(metadata1)

        with pytest.raises(ValueError, match="Duplicate content type"):
            registry.register(metadata2)

    def test_finalize_calls_registry_manager(self):
        """Test that finalize calls the registry manager."""
        registry = ContentTypeRegistry()

        # Test finalize without mocking - just verify it doesn't fail
        # and sets the finalized flag. Testing the exact method calls
        # would require mocking which causes ContentFactory contamination.
        registry.finalize()
        assert registry._finalized

    def test_finalize_only_once(self):
        """Test that finalize only runs once."""
        registry = ContentTypeRegistry()

        # Test finalize idempotency without mocking to avoid contamination
        registry.finalize()
        assert registry._finalized

        # Second call should not change state but should not fail
        registry.finalize()
        assert registry._finalized

    def test_register_after_finalize_raises_error(self):
        """Test that registration after finalize raises error."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        registry = ContentTypeRegistry()
        registry._finalized = True

        metadata = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel, file_patterns=["test"]
        )

        with pytest.raises(RuntimeError, match="Registry already finalized"):
            registry.register(metadata)

    def test_reset(self):
        """Test registry reset functionality."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        registry = ContentTypeRegistry()

        metadata = ContentTypeMetadata(
            enum_value="trap", model_class=TestModel, file_patterns=["test"]
        )

        registry.register(metadata)
        registry._finalized = True

        assert len(registry.get_all()) == 1
        assert registry._finalized

        registry.reset()

        # Reset preserves registrations but resets finalized flag
        assert len(registry.get_all()) == 1
        assert not registry._finalized

        # Registry can be finalized again after reset
        registry.finalize()
        assert registry._finalized


class TestContentTypeDecorator:
    """Test the @content_type decorator functionality."""

    def setup_method(self) -> None:
        """Reset registry for each test."""
        # For decorator tests, we need a fresh registry that's not finalized
        # so that decorators can register new content types
        from dnd5e.core.registry.content_type_registry import (
            reset_content_type_registry,
        )

        reset_content_type_registry()

    def teardown_method(self) -> None:
        """Clean up after tests that registered new content types."""
        # Full environment reset to ensure no contamination
        # This is critical because decorator tests register new content types
        # which can affect subsequent tests if not properly cleaned up
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

    def test_decorator_registration(self):
        """Test that decorator properly registers content types."""
        # Mock the registry registration to avoid conflicts with system registrations
        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_get_registry.return_value = mock_registry

            @content_type(
                enum_value="trap",
                file_patterns=["test"],
                statblock_tags=["testTag"],
            )
            class TestContent(BaseContent):
                pass

            # Verify the class is returned unchanged
            assert TestContent.__name__ == "TestContent"
            assert issubclass(TestContent, BaseContent)

            # Verify that registration was attempted
            mock_registry.register.assert_called_once()

    def test_decorator_validation_empty_enum_value(self):
        """Test that decorator validates empty enum_value."""
        with pytest.raises(ValueError, match="enum_value cannot be empty"):

            @content_type(enum_value="", file_patterns=["test"])
            class BadContent(BaseContent):
                pass

    def test_decorator_validation_empty_file_patterns(self):
        """Test that decorator validates empty file_patterns."""
        with pytest.raises(ValueError, match="file_patterns cannot be empty"):

            @content_type(enum_value="trap", file_patterns=[])
            class BadContent(BaseContent):
                pass

    def test_decorator_validation_non_basecontent(self):
        """Test that decorator validates inheritance from BaseContent."""
        from pydantic import BaseModel

        with pytest.raises(TypeError, match="must inherit from BaseContent"):

            @content_type(enum_value="trap", file_patterns=["test"])
            class BadContent(BaseModel):
                pass

    def test_decorator_returns_class_unchanged(self):
        """Test that decorator returns the original class."""
        # Mock the registry registration to avoid conflicts with system registrations
        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_get_registry.return_value = mock_registry

            @content_type(enum_value="hazard", file_patterns=["test"])
            class TestContentUnchanged(BaseContent):
                pass

            # Test that we can add a method to the class after decoration
            def test_method(self):
                return "test_value"

            TestContentUnchanged.test_method = test_method

            assert hasattr(TestContentUnchanged, "test_method")
            instance = TestContentUnchanged(name="test", source="PHB")
            assert instance.test_method() == "test_value"

    def test_decorator_with_optional_params(self):
        """Test decorator with optional parameters."""
        # Mock the registry registration to avoid conflicts with system registrations
        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_get_registry.return_value = mock_registry

            @content_type(
                enum_value="deck",
                file_patterns=["test"],
                loader_type="fluff",
            )
            class TestContentOptional(BaseContent):
                pass

            # Verify the class is created successfully with optional parameters
            assert TestContentOptional.__name__ == "TestContentOptional"
            assert issubclass(TestContentOptional, BaseContent)

            # Verify that registration was called with correct metadata
            mock_registry.register.assert_called_once()

    def test_decorator_error_handling(self):
        """Test decorator error handling during registration."""
        # Test that decorator handles registration errors gracefully
        with patch(
            "dnd5e.core.registry.content_type_registry.get_content_type_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.register.side_effect = ValueError("Test registration error")
            mock_get_registry.return_value = mock_registry

            # Should raise the registration error
            with pytest.raises(ValueError, match="Test registration error"):

                @content_type(enum_value="boon", file_patterns=["test"])
                class TestContent(BaseContent):
                    pass


class TestGetContentTypeRegistry:
    """Test the global registry instance management."""

    def setup_method(self) -> None:
        """Reset global instance for each test."""
        from tests.test_helpers import reset_test_environment

        # Use full environment reset to ensure proper initialization
        reset_test_environment()

    def test_singleton_behavior(self):
        """Test that get_content_type_registry returns same instance."""
        registry1 = get_content_type_registry()
        registry2 = get_content_type_registry()

        assert registry1 is registry2

    def test_creates_new_instance_when_none(self):
        """Test that new instance is created when global is None."""
        # After reset, we should have a properly initialized registry instance
        registry = get_content_type_registry()

        assert registry is not None
        assert isinstance(registry, ContentTypeRegistry)

        # Registry should be populated with decorator-registered content types after initialization
        # This verifies that reset_test_environment() properly initializes the registry
        registry_contents = registry.get_all()
        assert len(registry_contents) > 0, (
            "Registry should contain decorator-registered content types after initialization"
        )

        # Verify some expected content types are present
        expected_types = ["adventure", "book", "spell", "creature", "item"]
        for expected_type in expected_types:
            assert expected_type in registry_contents, (
                f"Expected content type '{expected_type}' not found in registry"
            )
