"""Tests for LaTeX document configuration."""

import pytest

from dnd5e.core.config.latex_config import LaTeXConfig, LaTeXDocumentConfig


class TestLaTeXDocumentConfig:
    """Tests for LaTeX document configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = LaTeXDocumentConfig()

        assert config.document_class == "dndbook"
        assert config.class_options == ["twocolumn"]
        assert config.font_scheme == "dmsguild"
        assert config.paper_size == "letterpaper"
        assert config.font_size == "11pt"
        assert config.background is None
        assert config.high_contrast is False
        assert config.justified_text is False
        assert config.fancy_headers is False
        assert config.two_column is True
        assert config.include_toc is True
        assert config.include_index is False
        assert config.custom_class_options == []
        assert config.fonts is None
        assert config.no_outline is False

    def test_background_validation_valid(self) -> None:
        """Test valid background values."""
        valid_backgrounds = ["print", "none", "full"]

        for bg in valid_backgrounds:
            config = LaTeXDocumentConfig(background=bg)
            assert config.background == bg

    def test_background_validation_none(self) -> None:
        """Test None background value."""
        config = LaTeXDocumentConfig(background=None)
        assert config.background is None

    def test_background_validation_invalid(self) -> None:
        """Test invalid background values."""
        with pytest.raises(ValueError, match="Background must be one of"):
            LaTeXDocumentConfig(background="invalid")

    def test_document_class_validation_valid(self) -> None:
        """Test valid document class values."""
        valid_classes = ["dndbook", "dndarticle"]

        for doc_class in valid_classes:
            config = LaTeXDocumentConfig(document_class=doc_class)
            assert config.document_class == doc_class

    def test_document_class_validation_invalid(self) -> None:
        """Test invalid document class values."""
        with pytest.raises(ValueError, match="Document class must be one of"):
            LaTeXDocumentConfig(document_class="invalid")

    def test_paper_size_validation_valid(self) -> None:
        """Test valid paper size values."""
        valid_sizes = ["letterpaper", "a4paper", "a5paper"]

        for size in valid_sizes:
            config = LaTeXDocumentConfig(paper_size=size)
            assert config.paper_size == size

    def test_paper_size_validation_invalid(self) -> None:
        """Test invalid paper size values."""
        with pytest.raises(ValueError, match="Paper size must be one of"):
            LaTeXDocumentConfig(paper_size="invalid")

    def test_font_size_validation_valid(self) -> None:
        """Test valid font size values."""
        valid_sizes = ["10pt", "11pt", "12pt"]

        for size in valid_sizes:
            config = LaTeXDocumentConfig(font_size=size)
            assert config.font_size == size

    def test_font_size_validation_invalid(self) -> None:
        """Test invalid font size values."""
        with pytest.raises(ValueError, match="Font size must be one of"):
            LaTeXDocumentConfig(font_size="invalid")

    def test_fonts_validation_valid(self) -> None:
        """Test valid fonts values."""
        valid_fonts = ["wotc", "dmsguild"]

        for fonts in valid_fonts:
            config = LaTeXDocumentConfig(fonts=fonts)
            assert config.fonts == fonts

    def test_fonts_validation_none(self) -> None:
        """Test None fonts value."""
        config = LaTeXDocumentConfig(fonts=None)
        assert config.fonts is None

    def test_fonts_validation_invalid(self) -> None:
        """Test invalid fonts values."""
        with pytest.raises(ValueError, match="Fonts must be one of"):
            LaTeXDocumentConfig(fonts="invalid")

    def test_get_class_options_list_default(self) -> None:
        """Test class options list generation with defaults."""
        config = LaTeXDocumentConfig()
        options = config.get_class_options_list()

        expected = ["letterpaper", "11pt", "twocolumn"]
        assert options == expected

    def test_get_class_options_list_with_background(self) -> None:
        """Test class options list with background setting."""
        config = LaTeXDocumentConfig(background="print")
        options = config.get_class_options_list()

        assert "bg=print" in options
        assert "bg" not in options  # Should not have plain bg

    def test_get_class_options_list_no_background(self) -> None:
        """Test class options list with no background."""
        config = LaTeXDocumentConfig(background=None)
        options = config.get_class_options_list()

        assert not any(opt.startswith("bg") for opt in options)

    def test_get_class_options_list_removes_existing_bg(self) -> None:
        """Test that existing bg options are removed when background is set."""
        config = LaTeXDocumentConfig(
            class_options=["justified", "bg", "twocolumn"], background="print"
        )
        options = config.get_class_options_list()

        assert "bg=print" in options
        assert "bg" not in options

    def test_get_class_options_list_high_contrast(self) -> None:
        """Test class options list with high contrast."""
        config = LaTeXDocumentConfig(high_contrast=True)
        options = config.get_class_options_list()

        assert "highcontrast" in options

    def test_get_class_options_list_not_justified(self) -> None:
        """Test class options list without justified text."""
        config = LaTeXDocumentConfig(justified_text=False)
        options = config.get_class_options_list()

        assert "justified" not in options

    def test_get_class_options_list_fancy_headers(self) -> None:
        """Test class options list with fancy headers."""
        config = LaTeXDocumentConfig(fancy_headers=True)
        options = config.get_class_options_list()

        assert "fancy" in options

    def test_get_class_options_list_one_column(self) -> None:
        """Test class options list with one column layout."""
        config = LaTeXDocumentConfig(two_column=False)
        options = config.get_class_options_list()

        assert "onecolumn" in options
        assert "twocolumn" not in options

    def test_get_class_options_list_custom_options(self) -> None:
        """Test class options list with custom options."""
        config = LaTeXDocumentConfig(custom_class_options=["custom1", "custom2"])
        options = config.get_class_options_list()

        assert "custom1" in options
        assert "custom2" in options

    def test_get_class_options_list_no_duplicates(self) -> None:
        """Test that class options list removes duplicates."""
        config = LaTeXDocumentConfig(
            class_options=["justified", "twocolumn"],
            custom_class_options=["justified", "custom"],
        )
        options = config.get_class_options_list()

        assert options.count("justified") == 1
        assert "custom" in options

    def test_get_class_options_list_fonts_wotc(self) -> None:
        """Test class options list with WOTC fonts."""
        config = LaTeXDocumentConfig(fonts="wotc")
        options = config.get_class_options_list()

        assert "fonts=wotc" in options

    def test_get_class_options_list_fonts_dmsguild(self) -> None:
        """Test class options list with DMs Guild fonts."""
        config = LaTeXDocumentConfig(fonts="dmsguild")
        options = config.get_class_options_list()

        assert "fonts=dmsguild" in options

    def test_get_class_options_list_no_fonts(self) -> None:
        """Test class options list without fonts option."""
        config = LaTeXDocumentConfig(fonts=None)
        options = config.get_class_options_list()

        assert not any(opt.startswith("fonts=") for opt in options)

    def test_get_class_options_list_no_outline(self) -> None:
        """Test class options list with no outline."""
        config = LaTeXDocumentConfig(no_outline=True)
        options = config.get_class_options_list()

        assert "nooutline" in options

    def test_get_class_options_list_with_outline(self) -> None:
        """Test class options list with outline (default)."""
        config = LaTeXDocumentConfig(no_outline=False)
        options = config.get_class_options_list()

        assert "nooutline" not in options

    def test_get_class_options_list_fonts_and_no_outline(self) -> None:
        """Test class options list with both fonts and no outline."""
        config = LaTeXDocumentConfig(fonts="wotc", no_outline=True)
        options = config.get_class_options_list()

        assert "fonts=wotc" in options
        assert "nooutline" in options


class TestLaTeXConfig:
    """Tests for complete LaTeX configuration."""

    def test_default_config(self) -> None:
        """Test default configuration creation."""
        config = LaTeXConfig()

        assert config.document is not None
        assert config.engine is not None
        assert config.template is not None

    def test_get_content_type_config_adventure(self) -> None:
        """Test configuration for adventure content type."""
        config = LaTeXConfig()
        content_config = config.get_content_type_config("adventure")

        assert content_config["document_class"] == "dndbook"
        assert content_config["template"] == "book"
        assert isinstance(content_config["class_options"], list)

    def test_get_content_type_config_article(self) -> None:
        """Test configuration for article content type."""
        config = LaTeXConfig()
        content_config = config.get_content_type_config("article")

        assert content_config["document_class"] == "dndarticle"
        # Should convert twocolumn to onecolumn for articles
        options = content_config["class_options"]
        assert "onecolumn" in options
        assert "twocolumn" not in options

    def test_get_content_type_config_supplement(self) -> None:
        """Test configuration for supplement content type."""
        config = LaTeXConfig()
        content_config = config.get_content_type_config("supplement")

        assert content_config["document_class"] == "dndbook"
        # Should not have fancy headers for supplements
        options = content_config["class_options"]
        assert "fancy" not in options
