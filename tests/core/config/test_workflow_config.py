"""Tests for workflow configuration helpers."""

from __future__ import annotations

import pytest

from dnd5e.core.config.workflow_config import (
    get_adventure_creation_workflow_config,
    get_available_workflows,
    get_character_sheet_workflow_config,
    get_dm_reference_workflow_config,
    get_encounter_printing_workflow_config,
    get_homebrew_workflow_config,
    get_spellbook_workflow_config,
)


class TestSpellbookWorkflow:
    """Test spellbook workflow configuration."""

    def test_default_spellbook_config(self) -> None:
        """Test default spellbook configuration."""
        config = get_spellbook_workflow_config()

        # Check structure exists
        assert "rendering" in config
        assert "validation" in config

        # Check content settings
        content = config["rendering"]["content"]
        assert content["appendix_spells"] is True
        assert "xphb" in content["default_sources"]
        assert "brew" in content["default_sources"]

        # Check document settings
        doc = config["rendering"]["latex"]["document"]
        assert doc["document_class"] == "dndarticle"
        assert doc["background"] == "full"
        assert doc["two_column"] is True

    def test_spellbook_print_optimization(self) -> None:
        """Test spellbook configuration optimized for printing."""
        config = get_spellbook_workflow_config(optimize_for_print=True)

        doc = config["rendering"]["latex"]["document"]
        rendering = config["rendering"]["latex"]["rendering"]
        content = config["rendering"]["content"]

        assert doc["background"] == "none"
        assert doc["high_contrast"] is True
        assert content["include_images"] is False
        assert rendering["enable_hyperlinks"] is False

    def test_spellbook_no_homebrew(self) -> None:
        """Test spellbook configuration without homebrew sources."""
        config = get_spellbook_workflow_config(include_homebrew=False)

        sources = config["rendering"]["content"]["default_sources"]
        assert "brew" not in sources
        assert "homebrew" not in sources
        assert "xphb" in sources

    def test_spellbook_non_cleric_focused(self) -> None:
        """Test spellbook configuration not focused on cleric."""
        config = get_spellbook_workflow_config(cleric_focused=False)

        sources = config["rendering"]["content"]["default_sources"]
        # Should not include extended cleric sources
        assert "tce" not in sources or "xge" not in sources


class TestEncounterPrintingWorkflow:
    """Test encounter printing workflow configuration."""

    def test_default_encounter_config(self) -> None:
        """Test default encounter printing configuration."""
        config = get_encounter_printing_workflow_config()

        doc = config["rendering"]["latex"]["document"]
        content = config["rendering"]["content"]

        assert doc["paper_size"] == "a4"
        assert doc["background"] == "none"
        assert doc["high_contrast"] is True
        assert doc["two_column"] is False
        assert doc["show_toc"] is False
        assert content["appendix_creatures"] is True
        assert content["include_images"] is False

    def test_encounter_custom_paper_size(self) -> None:
        """Test encounter printing with custom paper size."""
        config = get_encounter_printing_workflow_config(paper_size="letter")

        doc = config["rendering"]["latex"]["document"]
        assert doc["paper_size"] == "letter"

    def test_encounter_with_images(self) -> None:
        """Test encounter printing with images enabled."""
        config = get_encounter_printing_workflow_config(include_images=True)

        content = config["rendering"]["content"]
        assert content["include_images"] is True


class TestAdventureCreationWorkflow:
    """Test adventure creation workflow configuration."""

    def test_default_adventure_config(self) -> None:
        """Test default adventure creation configuration."""
        config = get_adventure_creation_workflow_config()

        content = config["rendering"]["content"]
        doc = config["rendering"]["latex"]["document"]

        assert content["appendix_spells"] is True
        assert content["appendix_items"] is True
        assert content["appendix_creatures"] is True
        assert doc["document_class"] == "dndbook"
        assert doc["show_toc"] is True

    def test_adventure_source_limit(self) -> None:
        """Test adventure creation with source limitations."""
        sources = ["xphb", "xmm"]
        config = get_adventure_creation_workflow_config(source_limit=sources)

        content_sources = config["rendering"]["content"]["default_sources"]
        assert content_sources == sources

    def test_adventure_screen_optimization(self) -> None:
        """Test adventure creation optimized for screen."""
        config = get_adventure_creation_workflow_config(optimize_for_screen=True)

        doc = config["rendering"]["latex"]["document"]
        assert doc["background"] == "full"


class TestCharacterSheetWorkflow:
    """Test character sheet workflow configuration."""

    def test_default_character_sheet_config(self) -> None:
        """Test default character sheet configuration."""
        config = get_character_sheet_workflow_config()

        content = config["rendering"]["content"]
        doc = config["rendering"]["latex"]["document"]

        assert content["appendix_creatures"] is False
        assert doc["document_class"] == "dndarticle"
        assert doc["background"] == "print"

        # Player-focused sources
        sources = content["default_sources"]
        assert "xphb" in sources
        assert "xge" in sources

    def test_character_sheet_compact_layout(self) -> None:
        """Test character sheet with compact layout."""
        config = get_character_sheet_workflow_config(compact_layout=True)

        doc = config["rendering"]["latex"]["document"]
        content = config["rendering"]["content"]

        assert "twocolumn" in doc["class_options"]
        assert doc["two_column"] is True
        assert content["include_images"] is False

    def test_character_sheet_no_references(self) -> None:
        """Test character sheet without references."""
        config = get_character_sheet_workflow_config(include_references=False)

        content = config["rendering"]["content"]
        doc = config["rendering"]["latex"]["document"]
        rendering = config["rendering"]["latex"]["rendering"]

        assert content["appendix_spells"] is False
        assert doc["show_toc"] is False
        assert rendering["enable_cross_refs"] is False


class TestDMReferenceWorkflow:
    """Test DM reference workflow configuration."""

    def test_default_dm_reference_config(self) -> None:
        """Test default DM reference configuration."""
        config = get_dm_reference_workflow_config()

        content = config["rendering"]["content"]
        doc = config["rendering"]["latex"]["document"]

        assert content["appendix_spells"] is True
        assert content["appendix_creatures"] is True
        assert doc["background"] == "full"
        assert doc["show_toc"] is True

    def test_dm_reference_quick_mode(self) -> None:
        """Test DM reference in quick reference mode."""
        config = get_dm_reference_workflow_config(quick_reference=True)

        doc = config["rendering"]["latex"]["document"]
        content = config["rendering"]["content"]

        assert doc["class_options"] == []
        assert doc["two_column"] is False
        assert content["include_images"] is False

    def test_dm_reference_print_optimization(self) -> None:
        """Test DM reference optimized for print."""
        config = get_dm_reference_workflow_config(screen_optimized=False)

        doc = config["rendering"]["latex"]["document"]
        assert doc["background"] == "none"


class TestHomebrewWorkflow:
    """Test homebrew workflow configuration."""

    def test_default_homebrew_config(self) -> None:
        """Test default homebrew configuration."""
        config = get_homebrew_workflow_config()

        content = config["rendering"]["content"]
        validation = config["validation"]

        sources = content["default_sources"]
        assert "homebrew" in sources
        assert "xphb" in sources
        assert validation["strictness"] == "lenient"

    def test_homebrew_no_official(self) -> None:
        """Test homebrew configuration without official sources."""
        config = get_homebrew_workflow_config(include_official=False)

        sources = config["rendering"]["content"]["default_sources"]
        assert "homebrew" in sources
        assert "xphb" not in sources

    def test_homebrew_strict_validation(self) -> None:
        """Test homebrew configuration with strict validation."""
        config = get_homebrew_workflow_config(strict_validation=True)

        validation = config["validation"]
        assert validation["strictness"] == "strict"

    def test_homebrew_print_optimization(self) -> None:
        """Test homebrew configuration optimized for print."""
        config = get_homebrew_workflow_config(optimize_for_sharing=False)

        doc = config["rendering"]["latex"]["document"]
        rendering = config["rendering"]["latex"]["rendering"]

        assert doc["background"] == "print"
        assert rendering["enable_hyperlinks"] is False


class TestWorkflowUtilities:
    """Test workflow utility functions."""

    def test_available_workflows(self) -> None:
        """Test getting available workflows."""
        workflows = get_available_workflows()

        expected_workflows = {
            "get_spellbook_workflow_config",
            "get_encounter_printing_workflow_config",
            "get_adventure_creation_workflow_config",
            "get_character_sheet_workflow_config",
            "get_dm_reference_workflow_config",
            "get_homebrew_workflow_config",
        }

        assert set(workflows.keys()) == expected_workflows

        # Check all have descriptions
        for name, description in workflows.items():
            assert isinstance(description, str)
            assert len(description) > 0


class TestWorkflowConfigStructure:
    """Test that all workflow configs return valid structure."""

    @pytest.mark.parametrize(
        "workflow_func",
        [
            get_spellbook_workflow_config,
            get_encounter_printing_workflow_config,
            get_adventure_creation_workflow_config,
            get_character_sheet_workflow_config,
            get_dm_reference_workflow_config,
            get_homebrew_workflow_config,
        ],
    )
    def test_workflow_config_structure(self, workflow_func) -> None:
        """Test that workflow configs return valid nested dictionary structure."""
        config = workflow_func()

        assert isinstance(config, dict)

        # All should have rendering config
        assert "rendering" in config
        assert isinstance(config["rendering"], dict)

        # Should have nested structure for LaTeX
        if "latex" in config["rendering"]:
            latex_config = config["rendering"]["latex"]
            assert isinstance(latex_config, dict)

            # Should have document and/or rendering sections
            if "document" in latex_config:
                assert isinstance(latex_config["document"], dict)
            if "rendering" in latex_config:
                assert isinstance(latex_config["rendering"], dict)

    def test_config_override_application(self) -> None:
        """Test that workflow configs can be applied as overrides."""
        from dnd5e.core.config.unified_config import ApplicationConfig

        # Create base config
        base_config = ApplicationConfig()

        # Get workflow config
        workflow_config = get_spellbook_workflow_config()

        # Test that we can access the nested structure that would be overridden
        assert hasattr(base_config, "rendering")
        assert hasattr(base_config.rendering, "content")
        assert hasattr(base_config.rendering.content, "appendix_spells")
        assert hasattr(base_config.rendering.latex.document, "background")

        # The workflow config should have the structure to override these
        assert "rendering" in workflow_config
        assert "content" in workflow_config["rendering"]
        assert "latex" in workflow_config["rendering"]
        assert "document" in workflow_config["rendering"]["latex"]
