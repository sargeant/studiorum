"""Tests for LaTeX tag system integration."""

from typing import Any

import pytest

from dnd5e.renderers.latex.tag_integration import (  # type: ignore
    DEFAULT_CONFIGS,
    LaTeXTagIntegration,
    create_latex_tag_integration,
)


class TestLaTeXTagIntegration:
    """Test LaTeX tag integration."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.integration = LaTeXTagIntegration()

    def test_integration_initialization(self) -> None:
        """Test integration initialization."""
        assert self.integration.cross_ref_manager is not None
        assert self.integration.hyperlink_manager is not None
        assert self.integration.content_tracker is not None
        assert self.integration.latex_renderer is not None
        assert self.integration.tag_resolver is not None

    def test_initialization_with_disabled_features(self) -> None:
        """Test initialization with disabled features."""
        integration: Any = LaTeXTagIntegration(
            enable_hyperlinks=False,
            enable_cross_refs=False,
        )

        assert integration.cross_ref_manager is None
        assert integration.hyperlink_manager is None
        assert integration.content_tracker is not None

    def test_process_text(self) -> None:
        """Test text processing."""
        # Simple test - would need actual tag content for full test
        result = self.integration.process_text("Plain text without tags")
        assert result == "Plain text without tags"

    def test_get_required_latex_packages(self) -> None:
        """Test getting required LaTeX packages."""
        packages = self.integration.get_required_latex_packages()

        expected_packages = [
            "hyperref",
            "xcolor",
            "nameref",
            "footmisc",
            "graphicx",
            "longtable",
            "booktabs",
            "footnote",
        ]

        for package in expected_packages:
            assert package in packages

    def test_get_latex_preamble_commands(self) -> None:
        """Test getting LaTeX preamble commands."""
        commands = self.integration.get_latex_preamble_commands()

        assert len(commands) > 0
        assert any("\\hypersetup{" in cmd for cmd in commands)
        assert any("Cross-reference setup" in cmd for cmd in commands)

    def test_create_content_label(self) -> None:
        """Test creating content labels."""
        label = self.integration.create_content_label("creature", "Dragon")

        assert label == "\\label{creature:dragon}"

    def test_create_content_reference(self) -> None:
        """Test creating content references."""
        ref = self.integration.create_content_reference(
            content_type="spell",
            name="Fireball",
            display_text="the fireball spell",
        )

        assert "the fireball spell" in ref or "Fireball" in ref

    def test_export_appendix_data(self) -> None:
        """Test exporting appendix data."""
        # First add some content
        self.integration.create_content_label("creature", "Dragon")
        self.integration.create_content_reference("spell", "Fireball")

        appendix_data = self.integration.export_appendix_data()

        assert "content_by_type" in appendix_data
        assert "statistics" in appendix_data

    def test_export_cross_reference_data(self) -> None:
        """Test exporting cross-reference data."""
        # Add some content
        self.integration.create_content_label("item", "Sword of Sharpness")

        cross_ref_data = self.integration.export_cross_reference_data()

        assert "references" in cross_ref_data
        assert "labels" in cross_ref_data
        assert "by_type" in cross_ref_data

    def test_get_tag_statistics(self) -> None:
        """Test getting tag statistics."""
        stats = self.integration.get_tag_statistics()

        assert "content_tracker" in stats
        assert "cross_references" in stats

    def test_validate_tags_and_references(self) -> None:
        """Test validating tags and references."""
        content = "Some content with tags"
        issues = self.integration.validate_tags_and_references(content)

        # Should return a list (may be empty)
        assert isinstance(issues, list)

    def test_clear_tracking_data(self) -> None:
        """Test clearing tracking data."""
        # Add some content
        self.integration.create_content_label("feat", "Great Weapon Master")

        # Clear and verify
        self.integration.clear_tracking_data()

        stats = self.integration.get_tag_statistics()
        assert stats["content_tracker"]["total_unique_content"] == 0

    def test_configure_hyperlink_styles(self) -> None:
        """Test configuring hyperlink styles."""
        styles = {
            "creature": {"color": "red", "font_style": "bold"},
            "spell": {"color": "blue", "font_style": "italic"},
        }

        self.integration.configure_hyperlink_styles(styles)

        # Verify styles were applied
        assert self.integration.hyperlink_manager is not None
        creature_style = self.integration.hyperlink_manager.content_styles["creature"]
        assert creature_style.color == "red"
        assert creature_style.font_style == "bold"


class TestLaTeXTagIntegrationFactory:
    """Test tag integration factory functions."""

    def test_create_latex_tag_integration_default(self) -> None:
        """Test creating integration with default config."""
        integration: Any = create_latex_tag_integration()

        assert integration is not None
        assert integration.cross_ref_manager is not None
        assert integration.hyperlink_manager is not None

    def test_create_latex_tag_integration_with_config(self) -> None:
        """Test creating integration with custom config."""
        config = {
            "enable_hyperlinks": False,
            "enable_cross_refs": True,
            "auto_page_refs": False,
            "cross_ref_format": "section",
        }

        integration: Any = create_latex_tag_integration(config=config)

        assert integration.cross_ref_manager is not None
        assert integration.hyperlink_manager is None
        assert integration.cross_ref_manager.reference_format == "section"

    def test_create_with_hyperlink_styles(self) -> None:
        """Test creating integration with hyperlink styles."""
        config = {
            "hyperlink_styles": {
                "creature": {"color": "purple", "font_style": "bold"},
            }
        }

        integration: Any = create_latex_tag_integration(config=config)

        creature_style = integration.hyperlink_manager.content_styles["creature"]
        assert creature_style.color == "purple"
        assert creature_style.font_style == "bold"


class TestDefaultConfigs:
    """Test default configurations."""

    def test_default_configs_exist(self) -> None:
        """Test that default configs exist."""
        assert "adventure" in DEFAULT_CONFIGS
        assert "reference" in DEFAULT_CONFIGS
        assert "supplement" in DEFAULT_CONFIGS

    def test_adventure_config(self) -> None:
        """Test adventure configuration."""
        config = DEFAULT_CONFIGS["adventure"]

        assert config["enable_hyperlinks"] is True
        assert config["enable_cross_refs"] is True
        assert config["auto_page_refs"] is True
        assert config["cross_ref_format"] == "page"
        assert "hyperlink_styles" in config
        assert "appendix_organization" in config

    def test_reference_config(self) -> None:
        """Test reference configuration."""
        config = DEFAULT_CONFIGS["reference"]

        assert config["enable_hyperlinks"] is True
        assert config["enable_cross_refs"] is True
        assert config["auto_page_refs"] is False
        assert config["cross_ref_format"] == "section"

    def test_supplement_config(self) -> None:
        """Test supplement configuration."""
        config = DEFAULT_CONFIGS["supplement"]

        assert config["enable_hyperlinks"] is True
        assert config["enable_cross_refs"] is True
        assert config["auto_page_refs"] is True
        assert config["cross_ref_format"] == "page"

    def test_create_integration_with_default_config(self) -> None:
        """Test creating integration with default config."""
        integration: Any = create_latex_tag_integration(
            config=DEFAULT_CONFIGS["adventure"]
        )

        assert integration is not None
        assert integration.cross_ref_manager.reference_format == "page"

        # Check hyperlink styles were applied
        creature_style = integration.hyperlink_manager.content_styles["creature"]
        assert creature_style.color == "red"
        assert creature_style.font_style == "bold"


class TestLaTeXTagResolverFacade:
    """Test LaTeX tag resolver facade."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.integration = LaTeXTagIntegration()
        self.facade = self.integration.tag_resolver

    def test_facade_initialization(self) -> None:
        """Test facade initialization."""
        assert self.facade is not None
        assert hasattr(self.facade, "process_text")
        assert hasattr(self.facade, "get_latex_content_tracker")

    def test_get_latex_content_tracker(self) -> None:
        """Test getting LaTeX content tracker."""
        tracker = self.facade.get_latex_content_tracker()
        assert tracker is not None

    def test_get_managers(self) -> None:
        """Test getting managers from facade."""
        cross_ref_mgr = self.facade.get_cross_reference_manager()
        hyperlink_mgr = self.facade.get_hyperlink_manager()

        assert cross_ref_mgr is not None
        assert hyperlink_mgr is not None


class TestIntegrationEdgeCases:
    """Test edge cases and error conditions."""

    def test_integration_without_omnidexer(self) -> None:
        """Test integration without omnidexer."""
        integration: Any = LaTeXTagIntegration(omnidexer=None)

        assert integration is not None
        assert integration.omnidexer is None

    def test_process_empty_text(self) -> None:
        """Test processing empty text."""
        integration: Any = LaTeXTagIntegration()

        result = integration.process_text("")
        assert result == ""

        result = integration.process_text(None)
        assert result is None or result == ""

    def test_create_reference_with_empty_names(self) -> None:
        """Test creating references with empty names."""
        integration: Any = LaTeXTagIntegration()

        # Should handle gracefully
        label = integration.create_content_label("creature", "")
        ref = integration.create_content_reference("spell", "")

        assert label is not None
        assert ref is not None

    def test_disabled_features_graceful_degradation(self) -> None:
        """Test graceful degradation when features are disabled."""
        integration: Any = LaTeXTagIntegration(
            enable_hyperlinks=False,
            enable_cross_refs=False,
        )

        # Should still work, just without enhancements
        result = integration.process_text("Some text")
        assert result == "Some text"

        # Methods should handle None managers gracefully
        label = integration.create_content_label("creature", "Dragon")
        assert label == ""  # No cross-ref manager


if __name__ == "__main__":
    pytest.main([__file__])
