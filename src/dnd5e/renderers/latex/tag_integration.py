"""Integration layer between enhanced tag system and LaTeX renderers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from dnd5e.core.logging import get_logger

from ...core.indexer.cross_reference_manager import CrossReferenceManager
from ...core.indexer.hyperlink_manager import HyperlinkManager
from ...core.indexer.latex_content_tracker import LaTeXContentTracker
from ...core.indexer.latex_tag_handlers import get_latex_enhanced_handlers
from ...core.indexer.latex_tag_renderer import LaTeXTagRenderer
from ...core.indexer.new_tag_resolver import TagResolverFacade

logger = get_logger(__name__)

if TYPE_CHECKING:
    from ...core.loaders.omnidexer import Omnidexer


class LaTeXTagIntegration:
    """Integration layer for LaTeX-enhanced tag processing."""

    def __init__(
        self,
        omnidexer: Omnidexer | None = None,
        enable_hyperlinks: bool = True,
        enable_cross_refs: bool = True,
        auto_page_refs: bool = True,
    ):
        """Initialize LaTeX tag integration."""
        self.omnidexer = omnidexer

        # Create managers
        self.cross_ref_manager = CrossReferenceManager() if enable_cross_refs else None
        self.hyperlink_manager = HyperlinkManager() if enable_hyperlinks else None
        self.content_tracker = LaTeXContentTracker()

        # Configure hyperlink manager
        if self.hyperlink_manager:
            self.hyperlink_manager.enable_hyperlinks(enable_hyperlinks)
            self.hyperlink_manager.enable_auto_page_refs(auto_page_refs)

        # Create enhanced tag renderer
        self.latex_renderer = LaTeXTagRenderer(
            omnidexer=self.omnidexer,
            cross_ref_manager=self.cross_ref_manager,
            hyperlink_manager=self.hyperlink_manager,
        )

        # Create facade for backward compatibility
        self.tag_resolver = LaTeXTagResolverFacade(
            latex_renderer=self.latex_renderer,
            omnidexer=self.omnidexer,
        )

        # Register enhanced handlers
        self._register_enhanced_handlers()

    def _register_enhanced_handlers(self) -> None:
        """Register LaTeX-enhanced tag handlers."""
        handlers = get_latex_enhanced_handlers()
        for handler in handlers:
            self.latex_renderer.register_handler(handler)

        logger.info(f"Registered {len(handlers)} LaTeX-enhanced tag handlers")

    def process_text(self, text: str) -> str:
        """Process text with LaTeX-enhanced tag resolution."""
        return self.tag_resolver.process_text(text)

    def get_required_latex_packages(self) -> list[str]:
        """Get LaTeX packages required for tag features."""
        packages = []

        if self.hyperlink_manager:
            packages.extend(self.hyperlink_manager.get_latex_packages())

        # Add other required packages
        packages.extend(
            [
                "graphicx",  # For figures
                "longtable",  # For long tables
                "booktabs",  # For professional tables
                "footnote",  # For footnotes
            ]
        )

        return list(set(packages))  # Remove duplicates

    def get_latex_preamble_commands(self) -> list[str]:
        """Get LaTeX preamble commands for tag features."""
        commands = []

        if self.hyperlink_manager:
            commands.extend(self.hyperlink_manager.get_latex_setup_commands())

        # Add cross-reference setup
        if self.cross_ref_manager:
            commands.extend(
                [
                    "% Cross-reference setup",
                    "\\newcommand{\\ContentRef}[2]{\\hyperref[#1]{#2}}",
                    "\\newcommand{\\PageRef}[1]{\\pageref{#1}}",
                ]
            )

        return commands

    def create_content_label(self, content_type: str, name: str) -> str:
        """Create a LaTeX label for content definition."""
        if not self.cross_ref_manager:
            return ""

        ref_id = self.cross_ref_manager.register_content(content_type, name)
        return self.cross_ref_manager.create_latex_label(ref_id)

    def create_content_reference(
        self,
        content_type: str,
        name: str,
        display_text: str | None = None,
        include_page_ref: bool | None = None,
    ) -> str:
        """Create a LaTeX reference to content."""
        if not self.cross_ref_manager:
            return display_text or name

        ref_id = self.cross_ref_manager.generate_reference_id(content_type, name)
        return self.cross_ref_manager.create_latex_reference(
            ref_id=ref_id,
            display_text=display_text,
            include_page_ref=include_page_ref,
        )

    def export_appendix_data(self) -> dict[str, Any]:
        """Export data for appendix generation."""
        return self.content_tracker.export_for_latex_appendix()

    def export_cross_reference_data(self) -> dict[str, Any]:
        """Export cross-reference data for document processing."""
        if not self.cross_ref_manager:
            return {}

        return self.cross_ref_manager.export_for_latex_document()

    def get_tag_statistics(self) -> dict[str, Any]:
        """Get comprehensive tag processing statistics."""
        stats = {
            "content_tracker": self.content_tracker.get_latex_statistics(),
        }

        if self.cross_ref_manager:
            stats["cross_references"] = (
                self.cross_ref_manager.get_reference_statistics()
            )

        return stats

    def validate_tags_and_references(self, content: str) -> list[dict[str, str | None]]:
        """Validate tags and cross-references in content."""
        issues: list[dict[str, str | None]] = []

        # Validate content tracker
        content_issues = self.content_tracker.validate_cross_references()
        issues.extend(content_issues)  # type: ignore[arg-type]

        # Validate cross-references
        if self.cross_ref_manager:
            cross_ref_issues = self.cross_ref_manager.validate_references()
            issues.extend(cross_ref_issues)

        # Validate hyperlinks
        if self.hyperlink_manager:
            hyperlink_issues = self.hyperlink_manager.validate_hyperlinks(content)
            issues.extend(hyperlink_issues)  # type: ignore[arg-type]

        return issues

    def clear_tracking_data(self) -> None:
        """Clear all tracking data for fresh processing."""
        self.content_tracker.clear()
        if self.cross_ref_manager:
            self.cross_ref_manager.clear_references()

    def configure_hyperlink_styles(self, styles: dict[str, dict[str, Any]]) -> None:
        """Configure hyperlink styles for different content types."""
        if not self.hyperlink_manager:
            return

        from ...core.indexer.hyperlink_manager import HyperlinkStyle

        for content_type, style_config in styles.items():
            style = HyperlinkStyle(
                color=style_config.get("color", "black"),
                border=style_config.get("border", False),
                underline=style_config.get("underline", False),
                font_style=style_config.get("font_style", "normal"),
            )
            self.hyperlink_manager.set_content_style(content_type, style)

    def set_appendix_organization(self, organization: dict[str, list[str]]) -> None:
        """Set organization for appendix sections."""
        # Update appendix sections in content tracker
        for section, content_types in organization.items():
            for content_type in content_types:
                # This would be used during content tracking
                pass


class LaTeXTagResolverFacade(TagResolverFacade):
    """Enhanced facade that provides LaTeX-specific tag resolution."""

    def __init__(
        self, latex_renderer: LaTeXTagRenderer, omnidexer: Omnidexer | None = None
    ):
        # Don't call super().__init__ to avoid creating a separate renderer
        self.omnidexer = omnidexer
        self.renderer = latex_renderer
        self.parser: Any = (
            latex_renderer.parser if hasattr(latex_renderer, "parser") else None
        )

        # For backward compatibility
        self._custom_handlers: dict[str, Any] = {}

    def get_latex_content_tracker(self) -> LaTeXContentTracker:
        """Get the LaTeX-enhanced content tracker."""
        if hasattr(self.renderer, "latex_content_tracker"):
            return self.renderer.latex_content_tracker  # type: ignore[no-any-return]
        else:
            # Fallback to regular content tracker (should be LaTeX type in this context)
            return self.renderer.content_tracker  # type: ignore[return-value]

    def get_cross_reference_manager(self) -> CrossReferenceManager | None:
        """Get the cross-reference manager."""
        return getattr(self.renderer, "cross_ref_manager", None)

    def get_hyperlink_manager(self) -> HyperlinkManager | None:
        """Get the hyperlink manager."""
        return getattr(self.renderer, "hyperlink_manager", None)


def create_latex_tag_integration(
    omnidexer: Omnidexer | None = None,
    config: dict[str, Any] | None = None,
) -> LaTeXTagIntegration:
    """Factory function to create configured LaTeX tag integration."""
    config = config or {}

    integration = LaTeXTagIntegration(
        omnidexer=omnidexer,
        enable_hyperlinks=config.get("enable_hyperlinks", True),
        enable_cross_refs=config.get("enable_cross_refs", True),
        auto_page_refs=config.get("auto_page_refs", True),
    )

    # Configure hyperlink styles if provided
    if "hyperlink_styles" in config:
        integration.configure_hyperlink_styles(config["hyperlink_styles"])

    # Set up cross-reference format
    if "cross_ref_format" in config and integration.cross_ref_manager:
        integration.cross_ref_manager.set_reference_format(config["cross_ref_format"])

    # Set up appendix organization
    if "appendix_organization" in config:
        integration.set_appendix_organization(config["appendix_organization"])

    return integration


def integrate_with_latex_renderer(
    latex_content_renderer: Any,
    omnidexer: Omnidexer | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Integrate LaTeX tag system with existing content renderer."""
    # Create integration
    integration = create_latex_tag_integration(omnidexer, config)

    # Replace tag resolver in content renderer
    if hasattr(latex_content_renderer, "context"):
        latex_content_renderer.context.tag_resolver = integration.tag_resolver
    elif hasattr(latex_content_renderer, "tag_resolver"):
        latex_content_renderer.tag_resolver = integration.tag_resolver
    else:
        # Add tag resolver to renderer
        latex_content_renderer.tag_resolver = integration.tag_resolver

    logger.info("Integrated LaTeX tag system with content renderer")


# Default configuration for different document types
DEFAULT_CONFIGS = {
    "adventure": {
        "enable_hyperlinks": True,
        "enable_cross_refs": True,
        "auto_page_refs": True,
        "cross_ref_format": "page",
        "hyperlink_styles": {
            "creature": {"color": "red", "font_style": "bold"},
            "spell": {"color": "blue", "font_style": "italic"},
            "item": {"color": "purple", "font_style": "italic"},
            "condition": {"color": "orange", "font_style": "italic"},
        },
        "appendix_organization": {
            "Creatures": ["creature"],
            "Spells": ["spell"],
            "Magic Items": ["item"],
            "Reference": ["condition", "feat"],
        },
    },
    "reference": {
        "enable_hyperlinks": True,
        "enable_cross_refs": True,
        "auto_page_refs": False,
        "cross_ref_format": "section",
        "hyperlink_styles": {
            "creature": {"color": "black", "font_style": "bold"},
            "spell": {"color": "black", "font_style": "italic"},
            "item": {"color": "black", "font_style": "italic"},
        },
    },
    "supplement": {
        "enable_hyperlinks": True,
        "enable_cross_refs": True,
        "auto_page_refs": True,
        "cross_ref_format": "page",
    },
}
