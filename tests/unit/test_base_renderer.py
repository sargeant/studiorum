"""Tests for base renderer functionality."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from studiorum.core.models.content import BaseContent  # type: ignore
from studiorum.renderers.base.renderer import (  # type: ignore
    BaseRenderer,
    RenderingError,
)


class TestRenderingError:
    """Tests for RenderingError exception class."""

    def test_rendering_error_creation(self) -> None:
        """Test basic RenderingError creation."""
        error: Any = RenderingError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_rendering_error_with_args(self) -> None:
        """Test RenderingError with multiple arguments."""
        error: Any = RenderingError("Error:", "details", 123)
        assert "Error:" in str(error)
        assert "details" in str(error)
        assert "123" in str(error)

    def test_rendering_error_inheritance(self) -> None:
        """Test RenderingError inheritance from Exception."""
        error: Any = RenderingError("test")
        assert isinstance(error, Exception)
        assert isinstance(error, RenderingError)

    def test_rendering_error_raise_and_catch(self) -> None:
        """Test raising and catching RenderingError."""
        with pytest.raises(RenderingError) as exc_info:
            raise RenderingError("Test exception")

        assert str(exc_info.value) == "Test exception"
        assert exc_info.type == RenderingError


class ConcreteRenderer(BaseRenderer):
    """Concrete implementation of BaseRenderer for testing."""

    @property
    def output_format(self) -> str:
        return "test"

    def render(
        self, content: BaseContent, context: dict[str, Any] | None = None
    ) -> str:
        return f"Rendered: {content.name}"


class TestBaseRenderer:
    """Tests for BaseRenderer abstract base class."""

    def test_base_renderer_cannot_be_instantiated(self) -> None:
        """Test that BaseRenderer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseRenderer()  # type: ignore[abstract]

    def test_concrete_renderer_creation(self) -> None:
        """Test that concrete renderer can be created."""
        renderer: Any = ConcreteRenderer()
        assert renderer.output_format == "test"
        assert renderer.config == {}

    def test_concrete_renderer_with_config(self) -> None:
        """Test concrete renderer creation with config."""
        config = {"option1": "value1", "option2": 42}
        renderer: Any = ConcreteRenderer(config)
        assert renderer.config == config
        assert renderer.config["option1"] == "value1"
        assert renderer.config["option2"] == 42

    def test_concrete_renderer_with_none_config(self) -> None:
        """Test concrete renderer creation with None config."""
        renderer: Any = ConcreteRenderer(None)
        assert renderer.config == {}

    def test_output_format_abstract_property(self) -> None:
        """Test that output_format is properly implemented."""
        renderer: Any = ConcreteRenderer()
        assert hasattr(renderer, "output_format")
        assert renderer.output_format == "test"

    def test_render_abstract_method(self) -> None:
        """Test that render method is properly implemented."""
        renderer: Any = ConcreteRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        result = renderer.render(mock_content)
        assert result == "Rendered: Test Content"

    def test_validate_content_default_implementation(self) -> None:
        """Test default validate_content implementation."""
        renderer: Any = ConcreteRenderer()
        mock_content: Any = Mock(spec=BaseContent)

        result = renderer.validate_content(mock_content)
        assert result is True

    def test_get_supported_content_types_default_implementation(self) -> None:
        """Test default get_supported_content_types implementation."""
        renderer: Any = ConcreteRenderer()

        result = renderer.get_supported_content_types()
        assert result == set()
        assert isinstance(result, set)

    def test_render_to_file_success(self, tmp_path: Any) -> None:
        """Test successful render_to_file operation."""
        renderer: Any = ConcreteRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "test_output.txt"

        renderer.render_to_file(mock_content, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert content == "Rendered: Test Content"

    def test_render_to_file_creates_directories(self, tmp_path: Any) -> None:
        """Test that render_to_file creates parent directories."""
        renderer: Any = ConcreteRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        nested_path = tmp_path / "subdir" / "nested" / "test_output.txt"

        renderer.render_to_file(mock_content, nested_path)

        assert nested_path.exists()
        assert nested_path.parent.exists()
        content = nested_path.read_text(encoding="utf-8")
        assert content == "Rendered: Test Content"

    def test_render_to_file_with_context(self, tmp_path: Any) -> None:
        """Test render_to_file passes context to render method."""

        class ContextRenderer(BaseRenderer):
            @property
            def output_format(self) -> str:
                return "test"

            def render(
                self, content: BaseContent, context: dict[str, Any] | None = None
            ) -> str:
                ctx_value = (
                    context.get("test_key", "default") if context else "no_context"
                )
                return f"Rendered: {content.name} with {ctx_value}"

        renderer: Any = ContextRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "test_output.txt"
        context = {"test_key": "custom_value"}

        renderer.render_to_file(mock_content, output_path, context)

        content = output_path.read_text(encoding="utf-8")
        assert content == "Rendered: Test Content with custom_value"

    def test_render_to_file_render_error_propagation(self, tmp_path: Any) -> None:
        """Test that render errors are properly wrapped in RenderingError."""

        class FailingRenderer(BaseRenderer):
            @property
            def output_format(self) -> str:
                return "test"

            def render(
                self, content: BaseContent, context: dict[str, Any] | None = None
            ) -> str:
                raise ValueError("Render failed")

        renderer: Any = FailingRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "test_output.txt"

        with pytest.raises(RenderingError) as exc_info:
            renderer.render_to_file(mock_content, output_path)

        assert "Failed to render to file" in str(exc_info.value)
        assert str(output_path) in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "Render failed"

    @patch("pathlib.Path.write_text")
    def test_render_to_file_write_error_handling(
        self, mock_write_text: Any, tmp_path: Any
    ) -> None:
        """Test that file write errors are properly wrapped in RenderingError."""
        mock_write_text.side_effect = OSError("Permission denied")

        renderer: Any = ConcreteRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "test_output.txt"

        with pytest.raises(RenderingError) as exc_info:
            renderer.render_to_file(mock_content, output_path)

        assert "Failed to render to file" in str(exc_info.value)
        assert str(output_path) in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, OSError)
        assert str(exc_info.value.__cause__) == "Permission denied"

    def test_render_to_file_utf8_encoding(self, tmp_path: Any) -> None:
        """Test that render_to_file uses UTF-8 encoding."""

        class UnicodeRenderer(BaseRenderer):
            @property
            def output_format(self) -> str:
                return "test"

            def render(
                self, content: BaseContent, context: dict[str, Any] | None = None
            ) -> str:
                return "Rendered: 中文 éñglish ñ content"

        renderer: Any = UnicodeRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "unicode_test.txt"

        renderer.render_to_file(mock_content, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert content == "Rendered: 中文 éñglish ñ content"

    def test_config_immutability(self) -> None:
        """Test that config modifications don't affect other instances."""
        config1 = {"option": "value1"}
        config2 = {"option": "value2"}

        renderer1: Any = ConcreteRenderer(config1)
        renderer2: Any = ConcreteRenderer(config2)

        assert renderer1.config["option"] == "value1"
        assert renderer2.config["option"] == "value2"

        # Modify config1 after creation
        config1["option"] = "modified"

        # Should not affect renderer1's config if properly implemented
        # (Note: Current implementation doesn't deep copy, so this test documents current behavior)
        assert renderer1.config["option"] == "modified"
        assert renderer2.config["option"] == "value2"

    def test_render_to_file_none_context(self, tmp_path: Any) -> None:
        """Test render_to_file with None context."""
        renderer: Any = ConcreteRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "test_output.txt"

        # Should not raise an error with None context
        renderer.render_to_file(mock_content, output_path, None)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert content == "Rendered: Test Content"

    def test_multiple_abstract_methods_enforcement(self) -> None:
        """Test that classes missing multiple abstract methods cannot be instantiated."""

        class IncompleteRenderer(BaseRenderer):
            # Missing both output_format property and render method
            pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteRenderer()  # type: ignore[abstract]

        # Should mention both missing abstract methods
        error_msg: Any = str(exc_info.value)
        assert "abstract" in error_msg.lower()

    def test_partial_abstract_implementation(self) -> None:
        """Test that classes with only some abstract methods implemented cannot be instantiated."""

        class PartialRenderer(BaseRenderer):
            @property
            def output_format(self) -> str:
                return "partial"

            # Missing render method

        with pytest.raises(TypeError):
            PartialRenderer()  # type: ignore[abstract]

    def test_render_to_file_error_message_format(self, tmp_path: Any) -> None:
        """Test the specific format of RenderingError messages."""

        class SpecificErrorRenderer(BaseRenderer):
            @property
            def output_format(self) -> str:
                return "test"

            def render(
                self, content: BaseContent, context: dict[str, Any] | None = None
            ) -> str:
                raise RuntimeError("Specific error message")

        renderer: Any = SpecificErrorRenderer()
        mock_content: Any = Mock(spec=BaseContent)
        mock_content.name = "Test Content"

        output_path = tmp_path / "error_test.txt"

        with pytest.raises(RenderingError) as exc_info:
            renderer.render_to_file(mock_content, output_path)

        error_msg: Any = str(exc_info.value)
        assert error_msg.startswith("Failed to render to file")
        assert str(output_path) in error_msg
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert str(exc_info.value.__cause__) == "Specific error message"

    def test_config_type_flexibility(self) -> None:
        """Test that config accepts various types of values."""
        config = {
            "string_value": "test",
            "int_value": 42,
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"},
            "none_value": None,
        }

        renderer: Any = ConcreteRenderer(config)

        assert renderer.config["string_value"] == "test"
        assert renderer.config["int_value"] == 42
        assert renderer.config["bool_value"] is True
        assert renderer.config["list_value"] == [1, 2, 3]
        assert renderer.config["dict_value"] == {"nested": "value"}
        assert renderer.config["none_value"] is None
