"""Tests for DND-5e-LaTeX-Template integration."""

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from studiorum.latex_engine.core.dnd_template import (  # type: ignore
    DNDTemplateManager,
    check_dnd_template_status,
    get_dnd_document_class_options,
    get_recommended_class_options,
)


@pytest.mark.rendering
class TestDNDTemplateManager:
    """Tests for DNDTemplateManager class."""

    def test_init(self) -> None:
        """Test DNDTemplateManager initialization."""
        manager: Any = DNDTemplateManager()
        assert manager.template_files
        assert manager.required_packages
        assert "dndbook.cls" in manager.template_files
        assert "dnd.sty" in manager.template_files
        assert "expl3" in manager.required_packages

    @patch("subprocess.run")
    @patch("studiorum.latex_engine.core.dnd_template.get_latex_utility")
    def test_find_template_file_found(
        self, mock_get_utility: Any, mock_run: Any
    ) -> None:
        """Test finding template file when it exists."""
        mock_get_utility.return_value = "kpsewhich"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="/usr/local/texlive/2023/texmf-dist/tex/latex/dnd/dndbook.cls\n",
        )

        manager: Any = DNDTemplateManager()
        result = manager._find_template_file("dndbook.cls")

        assert result is not None
        assert result.name == "dndbook.cls"
        mock_get_utility.assert_called_once_with("kpsewhich")
        mock_run.assert_called_once_with(
            ["kpsewhich", "dndbook.cls"], capture_output=True, text=True, timeout=30
        )

    @patch("subprocess.run")
    def test_find_template_file_not_found(self, mock_run: Any) -> None:
        """Test finding template file when it doesn't exist."""
        mock_run.return_value = Mock(returncode=1, stdout="")

        manager: Any = DNDTemplateManager()
        result = manager._find_template_file("nonexistent-template.cls")

        assert result is None

    @patch("subprocess.run")
    def test_find_template_file_timeout(self, mock_run: Any) -> None:
        """Test finding template file with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("kpsewhich", 30)

        manager: Any = DNDTemplateManager()
        result = manager._find_template_file("dndbook.cls")

        assert result is None

    @patch("subprocess.run")
    def test_find_template_file_no_kpsewhich(self, mock_run: Any) -> None:
        """Test finding template file when kpsewhich is not available."""
        mock_run.side_effect = FileNotFoundError()

        manager: Any = DNDTemplateManager()
        result = manager._find_template_file("dndbook.cls")

        assert result is None

    @patch.object(DNDTemplateManager, "_find_template_file")
    def test_check_template_availability_all_found(self, mock_find: Any) -> None:
        """Test template availability when all files are found."""
        mock_find.return_value = Path("/usr/local/texlive/template.cls")

        manager: Any = DNDTemplateManager()
        available, missing = manager.check_template_availability()

        assert available is True
        assert missing == []

    @patch.object(DNDTemplateManager, "_find_template_file")
    def test_check_template_availability_some_missing(self, mock_find: Any) -> None:
        """Test template availability when some files are missing."""

        def mock_find_side_effect(filename: Any) -> Any:
            if filename == "dndbook.cls":
                return Path("/usr/local/texlive/dndbook.cls")
            pass

        mock_find.side_effect = mock_find_side_effect

        manager: Any = DNDTemplateManager()
        available, missing = manager.check_template_availability()

        assert available is False
        assert "dnd.sty" in missing
        assert "dndbook.cls" not in missing

    @patch("subprocess.run")
    def test_check_latex_installation_available(self, mock_run: Any) -> None:
        """Test LaTeX installation check when available."""
        mock_run.return_value = Mock(
            returncode=0, stdout="pdfTeX 3.141592653-2.6-1.40.24 (TeX Live 2022)\n"
        )

        manager: Any = DNDTemplateManager()
        available, version = manager.check_latex_installation()

        assert available is True
        assert "pdfTeX" in version

    @patch("subprocess.run")
    def test_check_latex_installation_not_available(self, mock_run: Any) -> None:
        """Test LaTeX installation check when not available."""
        mock_run.side_effect = FileNotFoundError()

        manager: Any = DNDTemplateManager()
        available, version = manager.check_latex_installation()

        assert available is False
        assert version == "LaTeX not found"

    @patch.object(DNDTemplateManager, "_check_package_available")
    def test_check_required_packages_all_available(self, mock_check: Any) -> None:
        """Test required packages check when all are available."""
        mock_check.return_value = True

        manager: Any = DNDTemplateManager()
        available, missing = manager.check_required_packages()

        assert available is True
        assert missing == []

    @patch.object(DNDTemplateManager, "_check_package_available")
    def test_check_required_packages_some_missing(self, mock_check: Any) -> None:
        """Test required packages check when some are missing."""

        def mock_check_side_effect(package: Any) -> bool:
            return bool(package != "expl3")

        mock_check.side_effect = mock_check_side_effect

        manager: Any = DNDTemplateManager()
        available, missing = manager.check_required_packages()

        assert available is False
        assert "expl3" in missing

    @patch("subprocess.run")
    def test_check_package_available_found(self, mock_run: Any) -> None:
        """Test package availability check when package is found."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="/usr/local/texlive/2023/texmf-dist/tex/latex/expl3/expl3.sty\n",
        )

        manager: Any = DNDTemplateManager()
        result = manager._check_package_available("expl3")

        assert result is True

    @patch("subprocess.run")
    def test_check_package_available_not_found(self, mock_run: Any) -> None:
        """Test package availability check when package is not found."""
        mock_run.return_value = Mock(returncode=1, stdout="")

        manager: Any = DNDTemplateManager()
        result = manager._check_package_available("nonexistent")

        assert result is False

    @patch("subprocess.run")
    def test_get_texmf_paths_with_kpsewhich(self, mock_run: Any) -> None:
        """Test getting TEXMF paths when kpsewhich is available."""
        mock_run.return_value = Mock(returncode=0, stdout="/home/user/texmf\n")

        manager: Any = DNDTemplateManager()
        paths = manager.get_texmf_paths()

        assert len(paths) > 0
        assert any("texmf" in str(path) for path in paths)

    @patch("subprocess.run")
    def test_get_texmf_paths_fallback(self, mock_run: Any) -> None:
        """Test getting TEXMF paths when kpsewhich fails."""
        mock_run.side_effect = FileNotFoundError()

        manager: Any = DNDTemplateManager()
        paths = manager.get_texmf_paths()

        assert len(paths) > 0
        assert any("texmf" in str(path) for path in paths)

    @patch.object(DNDTemplateManager, "check_latex_installation")
    def test_get_system_info(self, mock_check_latex: Any) -> None:
        """Test getting system information."""
        mock_check_latex.return_value = (True, "pdfTeX 3.141592653")

        manager: Any = DNDTemplateManager()
        info = manager.get_system_info()

        assert "platform" in info
        assert "python_version" in info
        assert "latex_available" in info
        assert "latex_version" in info

    def test_create_installation_guide(self) -> None:
        """Test creating installation guide."""
        manager: Any = DNDTemplateManager()
        guide = manager.create_installation_guide()

        assert "Installation Guide" in guide
        assert "Prerequisites" in guide
        assert "Method 1" in guide
        assert "Method 2" in guide
        assert "Verification" in guide

    @patch.object(DNDTemplateManager, "check_template_availability")
    @patch.object(DNDTemplateManager, "check_latex_installation")
    @patch.object(DNDTemplateManager, "check_required_packages")
    def test_print_status_report(
        self, mock_packages: Any, mock_latex: Any, mock_template: Any
    ) -> None:
        """Test printing status report."""
        mock_template.return_value = (True, [])
        mock_latex.return_value = (True, "pdfTeX 3.141592653")
        mock_packages.return_value = (True, [])

        manager: Any = DNDTemplateManager()

        # This should not raise any exceptions
        manager.print_status_report()


@pytest.mark.rendering
class TestUtilityFunctions:
    """Tests for utility functions."""

    @patch.object(DNDTemplateManager, "check_latex_installation")
    @patch.object(DNDTemplateManager, "check_template_availability")
    @patch.object(DNDTemplateManager, "check_required_packages")
    def test_check_dnd_template_status_all_good(
        self, mock_packages: Any, mock_template: Any, mock_latex: Any
    ) -> None:
        """Test status check when everything is available."""
        mock_latex.return_value = (True, "pdfTeX 3.141592653")
        mock_template.return_value = (True, [])
        mock_packages.return_value = (True, [])

        result: Any = check_dnd_template_status()
        assert result is True

    @patch.object(DNDTemplateManager, "check_latex_installation")
    def test_check_dnd_template_status_no_latex(self, mock_latex: Any) -> None:
        """Test status check when LaTeX is not available."""
        mock_latex.return_value = (False, "LaTeX not found")

        result: Any = check_dnd_template_status()
        assert result is False

    @patch.object(DNDTemplateManager, "check_latex_installation")
    @patch.object(DNDTemplateManager, "check_template_availability")
    def test_check_dnd_template_status_no_template(
        self, mock_template: Any, mock_latex: Any
    ) -> None:
        """Test status check when template is not available."""
        mock_latex.return_value = (True, "pdfTeX 3.141592653")
        mock_template.return_value = (False, ["dndbook.cls"])

        result: Any = check_dnd_template_status()
        assert result is False

    @patch.object(DNDTemplateManager, "check_latex_installation")
    @patch.object(DNDTemplateManager, "check_template_availability")
    @patch.object(DNDTemplateManager, "check_required_packages")
    def test_check_dnd_template_status_missing_packages(
        self, mock_packages: Any, mock_template: Any, mock_latex: Any
    ) -> None:
        """Test status check when required packages are missing."""
        mock_latex.return_value = (True, "pdfTeX 3.141592653")
        mock_template.return_value = (True, [])
        mock_packages.return_value = (False, ["expl3"])

        result: Any = check_dnd_template_status()
        assert result is False

    def test_get_dnd_document_class_options(self) -> None:
        """Test getting document class options."""
        options: Any = get_dnd_document_class_options()

        assert "dndbook" in options
        assert "dndarticle" in options
        assert "bg" in options["dndbook"]
        assert "justified" in options["dndbook"]
        assert "bg" in options["dndarticle"]

    def test_get_recommended_class_options(self) -> None:
        """Test getting recommended class options for content types."""
        # Test book recommendations
        book_options: Any = get_recommended_class_options("book")
        assert "bg" in book_options
        assert "justified" not in book_options  # justified_text is False by default
        assert "twocolumn" in book_options

        # Test article recommendations
        article_options: Any = get_recommended_class_options("article")
        assert "bg" in article_options
        assert "justified" not in article_options  # justified_text is False by default
        assert "onecolumn" in article_options

        # Test adventure recommendations
        adventure_options: Any = get_recommended_class_options("adventure")
        assert "bg" in adventure_options
        assert (
            "justified" not in adventure_options
        )  # justified_text is False by default
        assert "twocolumn" in adventure_options
        assert "fancy" in adventure_options

        # Test unknown content type
        unknown_options: Any = get_recommended_class_options("unknown")
        assert "bg" in unknown_options
        assert "justified" not in unknown_options  # justified_text is False by default


@pytest.mark.rendering
class TestIntegration:
    """Integration tests for DND template system."""

    @patch.object(DNDTemplateManager, "check_template_availability")
    @patch.object(DNDTemplateManager, "check_latex_installation")
    @patch.object(DNDTemplateManager, "check_required_packages")
    def test_full_system_check(
        self, mock_packages: Any, mock_latex: Any, mock_template: Any
    ) -> None:
        """Test full system check integration."""
        mock_latex.return_value = (True, "pdfTeX 3.141592653")
        mock_template.return_value = (True, [])
        mock_packages.return_value = (True, [])

        manager: Any = DNDTemplateManager()

        # All checks should pass
        latex_ok, _ = manager.check_latex_installation()
        template_ok, _ = manager.check_template_availability()
        packages_ok, _ = manager.check_required_packages()

        assert latex_ok
        assert template_ok
        assert packages_ok

        # Overall status should be good
        assert check_dnd_template_status()

    def test_get_class_options_comprehensive(self) -> None:
        """Test comprehensive class options functionality."""
        options: Any = get_dnd_document_class_options()

        # Check that all expected options are present
        for class_name in ["dndbook", "dndarticle"]:
            assert class_name in options
            class_options = options[class_name]

            # Check for expected option types
            assert "bg" in class_options
            assert "justified" in class_options
            assert "highcontrast" in class_options
            assert "10pt" in class_options
            assert "11pt" in class_options
            assert "12pt" in class_options
            assert "a4paper" in class_options
            assert "letterpaper" in class_options

            # Check that descriptions are provided
            for option, description in class_options.items():
                assert isinstance(description, str)
                assert len(description) > 0

        # Test all content types have recommendations
        content_types = [
            "book",
            "supplement",
            "reference",
            "article",
            "adventure",
            "homebrew",
        ]
        for content_type in content_types:
            recommendations: Any = get_recommended_class_options(content_type)
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0
            assert "bg" in recommendations  # All should have bg
            # "justified" is not included by default since justified_text defaults to False
