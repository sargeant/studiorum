"""Tests for layout integration components."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.content import ContentType
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex.layout.base import LayoutHint, LayoutStrategy
from dnd5e.renderers.latex.layout.integration import (
    LayoutAwareContentRenderer,
    LayoutConfigurationHelper,
    LayoutIntegrationMixin,
)


class TestLayoutIntegrationMixin:
    """Test cases for LayoutIntegrationMixin."""

    def test_init_default_config(self) -> None:
        """Test initialization with default configuration."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        assert renderer._layout_enabled is True
        assert renderer._layout_strategy is None
        assert renderer._layout_hints == {}
        assert renderer._layout_engine is not None

    def test_init_with_config(self) -> None:
        """Test initialization with custom configuration."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {
                    "layout": {
                        "enabled": False,
                        "strategy": "multi_column",
                        "hints": {"spell": {"use_drop_cap": True}},
                    }
                }
                super().__init__()

        renderer = TestRenderer()
        assert renderer._layout_enabled is False
        assert renderer._layout_strategy == "multi_column"
        assert renderer._layout_hints == {"spell": {"use_drop_cap": True}}

    def test_apply_layout_disabled(self) -> None:
        """Test layout application when disabled."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {"layout": {"enabled": False}}
                super().__init__()

        renderer = TestRenderer()
        content = "Test content"
        result = renderer.apply_layout(content, ContentType.SPELL)
        assert result == content

    def test_apply_layout_empty_content(self) -> None:
        """Test layout application with empty content."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        result = renderer.apply_layout("", ContentType.SPELL)
        assert result == ""

        result = renderer.apply_layout("   ", ContentType.SPELL)
        assert result == "   "

    @patch("dnd5e.renderers.latex.layout.integration.LayoutEngine")
    def test_apply_layout_with_content(self, mock_layout_engine_class: Mock) -> None:
        """Test layout application with actual content."""
        mock_engine = Mock()
        mock_engine.process_content.return_value = "Processed content"
        mock_layout_engine_class.return_value = mock_engine

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        content = "Test content"
        result = renderer.apply_layout(content, ContentType.SPELL)

        assert result == "Processed content"
        mock_engine.process_content.assert_called_once()
        call_args = mock_engine.process_content.call_args
        assert call_args[1]["content"] == content
        assert call_args[1]["content_type"] == ContentType.SPELL

    def test_create_layout_hints_basic(self) -> None:
        """Test layout hints creation."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        hints = renderer._create_layout_hints(ContentType.SPELL, None)
        assert isinstance(hints, LayoutHint)

    def test_create_layout_hints_with_config(self) -> None:
        """Test layout hints creation with configuration."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {
                    "layout": {
                        "hints": {
                            "spell": {
                                "use_drop_cap": True,
                                "allow_float": False,
                            }
                        }
                    }
                }
                super().__init__()

        renderer = TestRenderer()
        hints = renderer._create_layout_hints(ContentType.SPELL, None)
        assert hints.use_drop_cap is True
        assert hints.allow_float is False

    def test_create_layout_hints_with_context(self) -> None:
        """Test layout hints creation with context."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()

        # Create mock context with layout preferences
        context = Mock(spec=RenderingContext)
        context.layout_preferences = {
            "float_position": "top",
            "use_sidebar": True,
            "sidebar_type": "DndComment",
            "span_columns": True,
        }

        hints = renderer._create_layout_hints(ContentType.SPELL, context)
        assert hints.float_position == "top"
        assert hints.sidebar_type == "DndComment"
        assert hints.span_columns is True

    def test_determine_layout_strategy_configured(self) -> None:
        """Test strategy determination with configured strategy."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {"layout": {"strategy": "reference"}}
                super().__init__()

        renderer = TestRenderer()
        strategy = renderer._determine_layout_strategy(ContentType.SPELL, None)
        assert strategy == LayoutStrategy.REFERENCE

    def test_determine_layout_strategy_from_context(self) -> None:
        """Test strategy determination from context."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()

        context = Mock()
        context.layout_strategy = LayoutStrategy.ADVENTURE

        strategy = renderer._determine_layout_strategy(ContentType.SPELL, context)
        assert strategy == LayoutStrategy.ADVENTURE

    def test_determine_layout_strategy_default(self) -> None:
        """Test strategy determination with no configuration."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        strategy = renderer._determine_layout_strategy(ContentType.SPELL, None)
        assert strategy is None

    def test_set_layout_strategy(self) -> None:
        """Test setting layout strategy."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        renderer.set_layout_strategy(LayoutStrategy.MAGAZINE)
        assert renderer._layout_strategy == LayoutStrategy.MAGAZINE.value

    def test_set_layout_hints(self) -> None:
        """Test setting layout hints for content type."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        hints = {"use_drop_cap": True, "allow_float": False}
        renderer.set_layout_hints(ContentType.SPELL, hints)

        assert "spell" in renderer._layout_hints
        assert renderer._layout_hints["spell"]["use_drop_cap"] is True
        assert renderer._layout_hints["spell"]["allow_float"] is False

    def test_set_layout_hints_update_existing(self) -> None:
        """Test updating existing layout hints."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {"layout": {"hints": {"spell": {"existing": True}}}}
                super().__init__()

        renderer = TestRenderer()
        new_hints = {"use_drop_cap": True}
        renderer.set_layout_hints(ContentType.SPELL, new_hints)

        assert renderer._layout_hints["spell"]["existing"] is True
        assert renderer._layout_hints["spell"]["use_drop_cap"] is True

    def test_enable_layout(self) -> None:
        """Test enabling/disabling layout."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()

        renderer.enable_layout(False)
        assert renderer._layout_enabled is False

        renderer.enable_layout(True)
        assert renderer._layout_enabled is True

    def test_get_layout_engine(self) -> None:
        """Test getting layout engine instance."""

        class TestRenderer(LayoutIntegrationMixin):
            def __init__(self) -> None:
                self.config = {}
                super().__init__()

        renderer = TestRenderer()
        engine = renderer.get_layout_engine()
        assert engine is renderer._layout_engine


class TestLayoutAwareContentRenderer:
    """Test cases for LayoutAwareContentRenderer."""

    def test_init_default(self) -> None:
        """Test initialization with default config."""
        renderer = LayoutAwareContentRenderer()
        assert renderer.config == {}
        assert renderer.layout_enabled is True
        assert renderer.layout_engine is not None

    def test_init_with_config(self) -> None:
        """Test initialization with custom config."""
        config = {
            "layout": {
                "enabled": False,
                "strategy": "reference",
            }
        }
        renderer = LayoutAwareContentRenderer(config)
        assert renderer.config == config
        assert renderer.layout_enabled is False

    @patch("dnd5e.renderers.latex.layout.integration.LayoutEngine")
    def test_render_with_layout_enabled(self, mock_layout_engine_class: Mock) -> None:
        """Test rendering with layout enabled."""
        mock_engine = Mock()
        mock_engine.process_content.return_value = "Layout processed content"
        mock_layout_engine_class.return_value = mock_engine

        class TestRenderer(LayoutAwareContentRenderer):
            def render_content(self, content: Any, context: Any) -> str:
                return f"Rendered: {content}"

        renderer = TestRenderer()
        result = renderer.render_with_layout("test", ContentType.SPELL)

        assert result == "Layout processed content"
        mock_engine.process_content.assert_called_once()

    def test_render_with_layout_disabled(self) -> None:
        """Test rendering with layout disabled."""

        class TestRenderer(LayoutAwareContentRenderer):
            def render_content(self, content: Any, context: Any) -> str:
                return f"Rendered: {content}"

        config = {"layout": {"enabled": False}}
        renderer = TestRenderer(config)
        result = renderer.render_with_layout("test", ContentType.SPELL)

        assert result == "Rendered: test"

    def test_render_with_layout_empty_content(self) -> None:
        """Test rendering with empty rendered content."""

        class TestRenderer(LayoutAwareContentRenderer):
            def render_content(self, content: Any, context: Any) -> str:
                return ""

        renderer = TestRenderer()
        result = renderer.render_with_layout("test", ContentType.SPELL)

        assert result == ""

    def test_get_content_layout_hints_default(self) -> None:
        """Test default content layout hints."""
        renderer = LayoutAwareContentRenderer()
        hints = renderer._get_content_layout_hints("content", ContentType.SPELL, None)
        assert hints is None

    def test_render_content_not_implemented(self) -> None:
        """Test that render_content raises NotImplementedError."""
        renderer = LayoutAwareContentRenderer()
        with pytest.raises(NotImplementedError):
            renderer.render_content("content", None)


class TestLayoutConfigurationHelper:
    """Test cases for LayoutConfigurationHelper."""

    def test_create_adventure_layout_config(self) -> None:
        """Test adventure layout configuration creation."""
        config = LayoutConfigurationHelper.create_adventure_layout_config()

        assert config["enabled"] is True
        assert config["strategy"] == LayoutStrategy.ADVENTURE.value
        assert config["multi_column"]["default_columns"] == 1
        assert config["multi_column"]["balance_columns"] is False
        assert config["float"]["max_floats_per_page"] == 2
        assert config["sidebar"]["max_sidebars_per_page"] == 3
        assert config["typography"]["use_drop_caps"] is True
        assert config["hints"]["adventure"]["use_drop_cap"] is True

    def test_create_reference_layout_config(self) -> None:
        """Test reference layout configuration creation."""
        config = LayoutConfigurationHelper.create_reference_layout_config()

        assert config["enabled"] is True
        assert config["strategy"] == LayoutStrategy.REFERENCE.value
        assert config["multi_column"]["default_columns"] == 2
        assert config["multi_column"]["balance_columns"] is True
        assert config["float"]["max_floats_per_page"] == 4
        assert config["sidebar"]["max_sidebars_per_page"] == 2
        assert config["hints"]["spell"]["avoid_column_break"] is True
        assert config["hints"]["creature"]["span_columns"] is True

    def test_create_supplement_layout_config(self) -> None:
        """Test supplement layout configuration creation."""
        config = LayoutConfigurationHelper.create_supplement_layout_config()

        assert config["enabled"] is True
        assert config["strategy"] == LayoutStrategy.SUPPLEMENT.value
        assert config["multi_column"]["default_columns"] == 2
        assert config["multi_column"]["balance_columns"] is True
        assert config["float"]["max_floats_per_page"] == 3
        assert config["sidebar"]["max_sidebars_per_page"] == 2
        assert config["typography"]["emphasis_style"] == "medium"
        assert config["hints"]["class"]["span_columns"] is True
        assert config["hints"]["race"]["allow_float"] is True

    def test_create_minimal_layout_config(self) -> None:
        """Test minimal layout configuration creation."""
        config = LayoutConfigurationHelper.create_minimal_layout_config()

        assert config["enabled"] is True
        assert config["strategy"] == LayoutStrategy.SINGLE_COLUMN.value
        assert config["multi_column"]["default_columns"] == 1
        assert config["float"]["max_floats_per_page"] == 1
        assert config["sidebar"]["max_sidebars_per_page"] == 1
