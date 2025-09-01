"""Tests for enhanced GalleryProcessor with decorative elements.

This module tests the decorative enhancements to the GalleryProcessor,
including showcase layouts with decorative LaTeX elements and chapter openers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from studiorum.core.result import Error, Success
from studiorum.latex_engine.core.images.gallery_processor import (
    GalleryConfig,
    GalleryLayout,
    GalleryProcessor,
    ProcessedGallery,
)
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


class TestGalleryConfigDecorative:
    """Test enhanced GalleryConfig with decorative options."""

    def setup_method(self):
        reset_test_environment()

    def test_decorative_config_defaults(self):
        """Test decorative configuration defaults."""
        config = GalleryConfig()

        # Test new decorative fields
        assert config.enable_decorative_elements is True
        assert config.showcase_decorative_style == "elegant"
        assert config.enable_featured_borders is True
        assert config.decorative_color_scheme == "dndred"
        assert config.chapter_opener_enhancements is True

    def test_custom_decorative_config(self):
        """Test custom decorative configuration."""
        config = GalleryConfig(
            enable_decorative_elements=False,
            showcase_decorative_style="gothic",
            decorative_color_scheme="blue",
            chapter_opener_enhancements=False,
        )

        assert config.enable_decorative_elements is False
        assert config.showcase_decorative_style == "gothic"
        assert config.decorative_color_scheme == "blue"
        assert config.chapter_opener_enhancements is False

    def test_decorative_style_options(self):
        """Test different decorative style options."""
        styles = ["elegant", "gothic", "modern"]

        for style in styles:
            config = GalleryConfig(showcase_decorative_style=style)
            assert config.showcase_decorative_style == style

    def test_color_scheme_options(self):
        """Test different color scheme options."""
        colors = ["dndred", "blue", "green", "purple"]

        for color in colors:
            config = GalleryConfig(decorative_color_scheme=color)
            assert config.decorative_color_scheme == color


class TestGalleryProcessorDecorative:
    """Test enhanced GalleryProcessor with decorative elements."""

    def setup_method(self):
        reset_test_environment()

        # Create processor with decorative elements enabled
        self.config = GalleryConfig(
            enable_decorative_elements=True,
            showcase_decorative_style="elegant",
            decorative_color_scheme="dndred",
        )
        self.processor = GalleryProcessor(config=self.config)

    def test_enhanced_showcase_layout_generation(self):
        """Test enhanced showcase layout with decorative elements."""
        processed_images = [
            {
                "latex_command": "\\includegraphics[width=\\textwidth]{main_image.jpg}",
                "title": "Main Featured Image",
                "index": 0,
            },
            {
                "latex_command": "\\includegraphics[width=\\textwidth]{thumb1.jpg}",
                "title": "Thumbnail 1",
                "index": 1,
            },
            {
                "latex_command": "\\includegraphics[width=\\textwidth]{thumb2.jpg}",
                "title": "Thumbnail 2",
                "index": 2,
            },
        ]

        gallery_entry = {
            "title": "Featured Gallery",
            "caption": "A collection of featured images",
        }

        result = self.processor._generate_showcase_layout(
            processed_images, gallery_entry
        )

        assert isinstance(result, Success)
        latex = result.value

        # Check for decorative elements
        assert "tikzpicture" in latex
        assert "dndred" in latex  # Color scheme
        assert "Featured image with decorative border" in latex
        assert "Decorative thumbnail separator" in latex
        assert "textcolor" in latex  # Decorative caption

    def test_showcase_without_decorative_elements(self):
        """Test showcase layout without decorative elements."""
        config_no_decorative = GalleryConfig(enable_decorative_elements=False)
        processor_no_decorative = GalleryProcessor(config=config_no_decorative)

        processed_images = [
            {
                "latex_command": "\\includegraphics[width=\\textwidth]{main_image.jpg}",
                "title": "Main Image",
                "index": 0,
            }
        ]

        gallery_entry = {"title": "Simple Gallery"}

        result = processor_no_decorative._generate_showcase_layout(
            processed_images, gallery_entry
        )

        assert isinstance(result, Success)
        latex = result.value

        # Should not contain decorative elements
        assert "tikzpicture" not in latex
        assert "decorative" not in latex.lower()

    def test_decorative_header_generation(self):
        """Test decorative header generation."""
        gallery_entry = {
            "title": "Test Gallery",
        }

        # Test elegant style
        self.config.showcase_decorative_style = "elegant"
        header_lines = self.processor._generate_showcase_decorative_header(
            gallery_entry
        )

        assert len(header_lines) > 0
        assert any("tikzpicture" in line for line in header_lines)
        assert any("dndred" in line for line in header_lines)
        assert any("Test Gallery" in line for line in header_lines)

        # Test fallback when no title
        gallery_entry_no_title = {}
        header_lines_fallback = self.processor._generate_showcase_decorative_header(
            gallery_entry_no_title
        )
        assert any("Featured Gallery" in line for line in header_lines_fallback)

    def test_decorative_header_styles(self):
        """Test different decorative header styles."""
        gallery_entry = {"title": "Style Test Gallery"}

        styles = ["elegant", "gothic", "modern"]

        for style in styles:
            self.config.showcase_decorative_style = style
            header_lines = self.processor._generate_showcase_decorative_header(
                gallery_entry
            )

            assert len(header_lines) > 0
            assert any("tikzpicture" in line for line in header_lines)

            if style == "elegant":
                assert any("Large\\bfseries" in line for line in header_lines)
            elif style == "gothic":
                assert any("zigzag" in line for line in header_lines)
            elif style == "modern":
                assert any("fill[color=" in line for line in header_lines)

    def test_decorative_footer_generation(self):
        """Test decorative footer generation."""
        gallery_entry = {}

        # Test elegant style
        self.config.showcase_decorative_style = "elegant"
        footer_lines = self.processor._generate_showcase_decorative_footer(
            gallery_entry
        )

        assert len(footer_lines) > 0
        assert any("tikzpicture" in line for line in footer_lines)
        assert any("foreach" in line for line in footer_lines)  # Elegant style dots

    def test_decorative_footer_styles(self):
        """Test different decorative footer styles."""
        gallery_entry = {}

        styles = ["elegant", "gothic", "modern"]

        for style in styles:
            self.config.showcase_decorative_style = style
            footer_lines = self.processor._generate_showcase_decorative_footer(
                gallery_entry
            )

            assert len(footer_lines) > 0
            assert any("tikzpicture" in line for line in footer_lines)

            if style == "elegant":
                assert any("foreach" in line for line in footer_lines)
            elif style == "gothic":
                assert any("coil" in line for line in footer_lines)
            elif style == "modern":
                assert any("fill[color=" in line for line in footer_lines)

    def test_required_packages_with_decorative(self):
        """Test required packages include decorative packages."""
        packages = self.processor._get_required_packages(GalleryLayout.SHOWCASE)

        # Should include standard packages
        assert "graphicx" in packages
        assert "subcaption" in packages
        assert "calc" in packages

        # Should include decorative packages
        assert "tikz" in packages
        assert "xcolor" in packages

    def test_required_packages_without_decorative(self):
        """Test required packages without decorative elements."""
        config_no_decorative = GalleryConfig(enable_decorative_elements=False)
        processor = GalleryProcessor(config=config_no_decorative)

        packages = processor._get_required_packages(GalleryLayout.SHOWCASE)

        # Should include standard packages
        assert "graphicx" in packages
        assert "subcaption" in packages
        assert "calc" in packages

        # Should not include decorative packages
        assert "tikz" not in packages
        assert "xcolor" not in packages

    def test_extract_image_path(self):
        """Test image path extraction from LaTeX commands."""
        # Test with options
        latex_cmd = "\\includegraphics[width=\\textwidth]{test_image.jpg}"
        path = self.processor._extract_image_path(latex_cmd)
        assert path == "test_image.jpg"

        # Test without options
        latex_cmd = "\\includegraphics{simple_image.png}"
        path = self.processor._extract_image_path(latex_cmd)
        assert path == "simple_image.png"

        # Test fallback
        latex_cmd = "\\someothercommand{not_an_image}"
        path = self.processor._extract_image_path(latex_cmd)
        assert path == "placeholder_chapter_opener"


class TestChapterOpenerShowcase:
    """Test chapter opener showcase functionality."""

    def setup_method(self):
        reset_test_environment()

        self.config = GalleryConfig(
            chapter_opener_enhancements=True,
            enable_decorative_elements=True,
        )
        self.processor = GalleryProcessor(config=self.config)

    def test_chapter_opener_showcase_creation(self):
        """Test chapter opener showcase creation."""
        opener_image = {
            "href": {"path": "chapter_opener.jpg"},
            "title": "Chapter 1 Opener",
            "altText": "Opening art for Chapter 1",
        }

        chapter_context = {
            "chapter_name": "Chapter 1: Into the Mists",
            "adventure_name": "Curse of Strahd",
        }

        rendering_context = Mock(spec=RenderingContext)

        with patch.object(self.processor, "_process_gallery_image") as mock_process:
            mock_process.return_value = Success(
                {
                    "latex_command": "\\includegraphics[width=\\textwidth]{chapter_opener.jpg}",
                    "title": "Chapter 1 Opener",
                    "index": 0,
                }
            )

            result = self.processor.create_chapter_opener_showcase(
                opener_image, chapter_context, rendering_context
            )

            assert isinstance(result, Success)
            processed_gallery = result.value
            assert isinstance(processed_gallery, ProcessedGallery)
            assert processed_gallery.layout_used == GalleryLayout.SHOWCASE
            assert "shadowtext" in processed_gallery.required_packages

    def test_chapter_opener_with_decorative_elements(self):
        """Test chapter opener with decorative elements enabled."""
        opener_image = {
            "href": {"path": "fancy_opener.jpg"},
            "title": "Fancy Chapter Opener",
        }

        chapter_context = {
            "chapter_name": "Chapter 2: The Lands of Barovia",
            "adventure_name": "Curse of Strahd",
        }

        rendering_context = Mock(spec=RenderingContext)

        with patch.object(self.processor, "_process_gallery_image") as mock_process:
            mock_process.return_value = Success(
                {
                    "latex_command": "\\includegraphics[width=\\textwidth]{fancy_opener.jpg}",
                    "title": "Fancy Chapter Opener",
                    "index": 0,
                }
            )

            result = self.processor.create_chapter_opener_showcase(
                opener_image, chapter_context, rendering_context
            )

            assert isinstance(result, Success)
            processed_gallery = result.value

            # Check for decorative elements in LaTeX
            latex = processed_gallery.latex_command
            assert "tikzpicture" in latex
            assert "remember picture,overlay" in latex
            assert "Chapter 2: The Lands of Barovia" in latex
            assert "clearpage" in latex  # Should start new page

    def test_chapter_opener_without_decorative_elements(self):
        """Test chapter opener without decorative elements."""
        config_no_decorative = GalleryConfig(
            chapter_opener_enhancements=True,
            enable_decorative_elements=False,
        )
        processor = GalleryProcessor(config=config_no_decorative)

        opener_image = {
            "href": {"path": "simple_opener.jpg"},
            "title": "Simple Opener",
        }

        chapter_context = {
            "chapter_name": "Simple Chapter",
            "adventure_name": "Simple Adventure",
        }

        rendering_context = Mock(spec=RenderingContext)

        with patch.object(processor, "_process_gallery_image") as mock_process:
            mock_process.return_value = Success(
                {
                    "latex_command": "\\includegraphics[width=\\textwidth]{simple_opener.jpg}",
                    "title": "Simple Opener",
                    "index": 0,
                }
            )

            result = processor.create_chapter_opener_showcase(
                opener_image, chapter_context, rendering_context
            )

            assert isinstance(result, Success)
            processed_gallery = result.value

            # Should not contain decorative elements
            latex = processed_gallery.latex_command
            assert "tikzpicture" not in latex
            assert "remember picture,overlay" not in latex

    def test_chapter_opener_disabled_enhancements(self):
        """Test chapter opener with enhancements disabled."""
        config_no_enhancements = GalleryConfig(
            chapter_opener_enhancements=False,
        )
        processor = GalleryProcessor(config=config_no_enhancements)

        opener_image = {
            "href": {"path": "basic_opener.jpg"},
            "title": "Basic Opener",
        }

        chapter_context = {
            "chapter_name": "Basic Chapter",
            "adventure_name": "Basic Adventure",
        }

        rendering_context = Mock(spec=RenderingContext)

        with patch.object(processor, "process_gallery") as mock_process:
            mock_process.return_value = Success(
                ProcessedGallery(
                    latex_command="\\basic gallery",
                    layout_used=GalleryLayout.SHOWCASE,
                    image_count=1,
                )
            )

            result = processor.create_chapter_opener_showcase(
                opener_image, chapter_context, rendering_context
            )

            # Should fall back to standard gallery processing
            mock_process.assert_called_once()
            assert isinstance(result, Success)

    def test_chapter_opener_processing_failure(self):
        """Test handling of chapter opener processing failure."""
        opener_image = {
            "href": {"path": "broken_opener.jpg"},
        }

        chapter_context = {
            "chapter_name": "Failed Chapter",
            "adventure_name": "Failed Adventure",
        }

        rendering_context = Mock(spec=RenderingContext)

        with patch.object(self.processor, "_process_gallery_image") as mock_process:
            mock_process.return_value = Error("Image processing failed")

            result = self.processor.create_chapter_opener_showcase(
                opener_image, chapter_context, rendering_context
            )

            assert isinstance(result, Error)
            assert "Failed to process chapter opener" in str(result.error)


class TestDecorativeElementIntegration:
    """Test integration of decorative elements across gallery layouts."""

    def setup_method(self):
        reset_test_environment()

    def test_decorative_elements_in_grid_layout(self):
        """Test that decorative elements don't interfere with grid layout."""
        config = GalleryConfig(enable_decorative_elements=True)
        processor = GalleryProcessor(config=config)

        processed_images = [
            {
                "latex_command": "\\includegraphics[width=\\textwidth]{img1.jpg}",
                "title": "Image 1",
                "index": 0,
            },
            {
                "latex_command": "\\includegraphics[width=\\textwidth]{img2.jpg}",
                "title": "Image 2",
                "index": 1,
            },
        ]

        gallery_entry = {"columns": 2}

        result = processor._generate_grid_layout(processed_images, gallery_entry)

        assert isinstance(result, Success)
        latex = result.value

        # Grid layout should not contain decorative elements
        assert "tikzpicture" not in latex
        assert "decorative" not in latex.lower()

        # But should contain standard grid elements
        assert "subfigure" in latex
        assert "hfill" in latex

    def test_decorative_elements_required_packages(self):
        """Test that decorative elements add required packages correctly."""
        config = GalleryConfig(enable_decorative_elements=True)
        processor = GalleryProcessor(config=config)

        # Only showcase layout should get decorative packages
        showcase_packages = processor._get_required_packages(GalleryLayout.SHOWCASE)
        grid_packages = processor._get_required_packages(GalleryLayout.GRID)

        assert "tikz" in showcase_packages
        assert "xcolor" in showcase_packages
        assert "tikz" not in grid_packages
        assert "xcolor" not in grid_packages

    def test_color_scheme_consistency(self):
        """Test that color scheme is used consistently across decorative elements."""
        config = GalleryConfig(
            enable_decorative_elements=True,
            decorative_color_scheme="testcolor",
        )
        processor = GalleryProcessor(config=config)

        gallery_entry = {"title": "Color Test"}

        # Test header
        header_lines = processor._generate_showcase_decorative_header(gallery_entry)
        header_text = "\n".join(header_lines)
        assert "testcolor" in header_text

        # Test footer
        footer_lines = processor._generate_showcase_decorative_footer(gallery_entry)
        footer_text = "\n".join(footer_lines)
        assert "testcolor" in footer_text

        # Test showcase layout
        processed_images = [
            {
                "latex_command": "\\includegraphics{test.jpg}",
                "title": "Test Image",
                "index": 0,
            }
        ]

        result = processor._generate_showcase_layout(processed_images, gallery_entry)
        assert isinstance(result, Success)
        assert "testcolor" in result.value

    def test_decorative_elements_with_empty_gallery(self):
        """Test decorative elements behavior with empty gallery."""
        config = GalleryConfig(enable_decorative_elements=True)
        processor = GalleryProcessor(config=config)

        processed_images = []
        gallery_entry = {"title": "Empty Gallery"}

        result = processor._generate_showcase_layout(processed_images, gallery_entry)

        assert isinstance(result, Success)
        latex = result.value

        # Should still contain decorative header/footer
        assert "tikzpicture" in latex
        # But no image-specific decorative elements
        assert "Featured image with decorative border" not in latex


@pytest.mark.requires_data
class TestGalleryDecorativeIntegration:
    """Integration tests for decorative gallery functionality (slower, marked for optional execution)."""

    def setup_method(self):
        reset_test_environment()

    def test_realistic_adventure_gallery_with_decorations(self):
        """Test realistic adventure gallery with full decorative elements."""
        pytest.skip("Requires realistic adventure data")

    def test_performance_with_decorative_elements(self):
        """Test performance impact of decorative elements."""
        pytest.skip("Requires performance benchmarking")
