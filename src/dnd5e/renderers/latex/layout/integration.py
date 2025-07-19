"""Integration layer for adding layout capabilities to existing content renderers."""

from typing import Any, Optional

from ....core.models.content import ContentType
from ..base import RenderContext
from .base import LayoutHint, LayoutStrategy
from .layout_engine import LayoutEngine


class LayoutIntegrationMixin:
    """Mixin class that adds layout capabilities to content renderers."""

    def __init__(self, *args, **kwargs):
        """Initialize the mixin with layout engine."""
        super().__init__(*args, **kwargs)

        # Get layout configuration from renderer config
        layout_config = getattr(self, "config", {}).get("layout", {})
        self._layout_engine = LayoutEngine(layout_config)

        # Layout preferences for this renderer
        self._layout_enabled = layout_config.get("enabled", True)
        self._layout_strategy = layout_config.get("strategy")
        self._layout_hints = layout_config.get("hints", {})

    def apply_layout(
        self,
        content: str,
        content_type: ContentType,
        context: RenderContext | None = None,
    ) -> str:
        """Apply layout processing to rendered content."""
        if not self._layout_enabled or not content.strip():
            return content

        # Create layout hints from configuration and context
        hints = self._create_layout_hints(content_type, context)

        # Determine layout strategy
        strategy = self._determine_layout_strategy(content_type, context)

        # Process through layout engine
        return self._layout_engine.process_content(
            content=content, content_type=content_type, hints=hints, strategy=strategy
        )

    def _create_layout_hints(
        self, content_type: ContentType, context: RenderContext | None
    ) -> LayoutHint:
        """Create layout hints based on content type and context."""
        hint = LayoutHint()

        # Apply configured hints
        if content_type.name.lower() in self._layout_hints:
            type_hints = self._layout_hints[content_type.name.lower()]
            for key, value in type_hints.items():
                if hasattr(hint, key):
                    setattr(hint, key, value)

        # Apply context-specific hints
        if context:
            hint = self._enhance_hints_from_context(hint, context)

        return hint

    def _enhance_hints_from_context(
        self, hint: LayoutHint, context: RenderContext
    ) -> LayoutHint:
        """Enhance layout hints based on rendering context."""
        # Check for layout-related context flags
        if hasattr(context, "layout_preferences"):
            prefs = context.layout_preferences

            if "float_position" in prefs:
                hint.float_position = prefs["float_position"]

            if "use_sidebar" in prefs:
                hint.sidebar_type = prefs.get("sidebar_type")
                hint.sidebar_position = prefs.get("sidebar_position")

            if "span_columns" in prefs:
                hint.span_columns = prefs["span_columns"]

        return hint

    def _determine_layout_strategy(
        self, content_type: ContentType, context: RenderContext | None
    ) -> LayoutStrategy | None:
        """Determine layout strategy for this content."""
        # Use configured strategy first
        if self._layout_strategy:
            return LayoutStrategy(self._layout_strategy)

        # Use context strategy if available
        if context and hasattr(context, "layout_strategy"):
            return context.layout_strategy

        # Let layout engine decide
        return None

    def set_layout_strategy(self, strategy: LayoutStrategy) -> None:
        """Set the layout strategy for this renderer."""
        self._layout_strategy = strategy.value

    def set_layout_hints(
        self, content_type: ContentType, hints: dict[str, Any]
    ) -> None:
        """Set layout hints for a specific content type."""
        if content_type.name.lower() not in self._layout_hints:
            self._layout_hints[content_type.name.lower()] = {}

        self._layout_hints[content_type.name.lower()].update(hints)

    def enable_layout(self, enabled: bool = True) -> None:
        """Enable or disable layout processing."""
        self._layout_enabled = enabled

    def get_layout_engine(self) -> LayoutEngine:
        """Get the layout engine instance."""
        return self._layout_engine


class LayoutAwareContentRenderer:
    """Base class for content renderers that are layout-aware."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize layout-aware renderer."""
        self.config = config or {}

        # Initialize layout integration
        layout_config = self.config.get("layout", {})
        self.layout_engine = LayoutEngine(layout_config)
        self.layout_enabled = layout_config.get("enabled", True)

    def render_with_layout(
        self,
        content: Any,
        content_type: ContentType,
        context: RenderContext | None = None,
    ) -> str:
        """Render content and apply layout processing."""
        # First render the content using the specific renderer
        rendered_content = self.render_content(content, context)

        # Then apply layout if enabled
        if self.layout_enabled and rendered_content.strip():
            hints = self._get_content_layout_hints(content, content_type, context)
            rendered_content = self.layout_engine.process_content(
                content=rendered_content, content_type=content_type, hints=hints
            )

        return rendered_content

    def _get_content_layout_hints(
        self,
        content: Any,
        content_type: ContentType,
        context: RenderContext | None,
    ) -> LayoutHint | None:
        """Get layout hints specific to this content and renderer."""
        # Override in subclasses to provide content-specific hints
        return None

    def render_content(self, content: Any, context: RenderContext | None) -> str:
        """Render content without layout processing. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement render_content")


class LayoutConfigurationHelper:
    """Helper class for configuring layout settings."""

    @staticmethod
    def create_adventure_layout_config() -> dict[str, Any]:
        """Create layout configuration optimized for adventure content."""
        return {
            "enabled": True,
            "strategy": LayoutStrategy.ADVENTURE.value,
            "multi_column": {
                "default_columns": 1,
                "balance_columns": False,
            },
            "float": {
                "max_floats_per_page": 2,
            },
            "sidebar": {
                "max_sidebars_per_page": 3,
            },
            "typography": {
                "use_drop_caps": True,
                "emphasis_style": "strong",
            },
            "hints": {
                "adventure": {
                    "use_drop_cap": True,
                    "sidebar_type": "DndReadAloud",
                    "emphasis_level": 2,
                }
            },
        }

    @staticmethod
    def create_reference_layout_config() -> dict[str, Any]:
        """Create layout configuration optimized for reference content."""
        return {
            "enabled": True,
            "strategy": LayoutStrategy.REFERENCE.value,
            "multi_column": {
                "default_columns": 2,
                "balance_columns": True,
            },
            "float": {
                "max_floats_per_page": 4,
            },
            "sidebar": {
                "max_sidebars_per_page": 2,
            },
            "hints": {
                "spell": {
                    "avoid_column_break": True,
                    "group_with_next": True,
                },
                "item": {
                    "allow_float": True,
                    "group_with_next": True,
                },
                "creature": {
                    "span_columns": True,
                    "float_position": "FULL_WIDTH_BOTTOM",
                },
            },
        }

    @staticmethod
    def create_supplement_layout_config() -> dict[str, Any]:
        """Create layout configuration optimized for supplement content."""
        return {
            "enabled": True,
            "strategy": LayoutStrategy.SUPPLEMENT.value,
            "multi_column": {
                "default_columns": 2,
                "balance_columns": True,
            },
            "float": {
                "max_floats_per_page": 3,
            },
            "sidebar": {
                "max_sidebars_per_page": 2,
            },
            "typography": {
                "emphasis_style": "medium",
            },
            "hints": {
                "class": {
                    "span_columns": True,
                    "use_drop_cap": False,
                },
                "race": {
                    "allow_float": True,
                    "sidebar_type": "DndSidebar",
                },
            },
        }

    @staticmethod
    def create_minimal_layout_config() -> dict[str, Any]:
        """Create minimal layout configuration."""
        return {
            "enabled": True,
            "strategy": LayoutStrategy.SINGLE_COLUMN.value,
            "multi_column": {
                "default_columns": 1,
            },
            "float": {
                "max_floats_per_page": 1,
            },
            "sidebar": {
                "max_sidebars_per_page": 1,
            },
        }
