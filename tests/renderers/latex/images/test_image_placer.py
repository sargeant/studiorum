"""Tests for the image placement and text wrapping functionality."""

from pathlib import Path

import pytest

from studiorum.renderers.latex.images.image_placer import (
    ImagePlacement,
    ImagePlacer,
    ImageSize,
    PlacementConfig,
    PlacementResult,
)
from tests.test_helpers import reset_test_environment


@pytest.mark.rendering
class TestPlacementConfig:
    """Test the placement configuration."""

    def test_default_config(self):
        """Test default placement configuration."""
        config = PlacementConfig()

        assert config.default_placement == ImagePlacement.FLOAT_HERE
        assert config.default_size == ImageSize.MEDIUM
        assert config.enable_text_wrapping is True
        assert config.enable_margin_images is False
        assert config.caption_position == "bottom"
        assert config.figure_separation == "12pt"
        assert config.wrap_lines == 10

    def test_custom_config(self):
        """Test custom placement configuration."""
        config = PlacementConfig(
            default_placement=ImagePlacement.WRAP_RIGHT,
            enable_margin_images=True,
            wrap_lines=15,
        )

        assert config.default_placement == ImagePlacement.WRAP_RIGHT
        assert config.enable_margin_images is True
        assert config.wrap_lines == 15


@pytest.mark.rendering
class TestPlacementResult:
    """Test the placement result model."""

    def test_placement_result_creation(self):
        """Test creating a placement result."""
        result = PlacementResult(
            latex_command="\\includegraphics{test.png}",
            placement=ImagePlacement.INLINE,
            size_spec="0.5\\textwidth",
            requires_packages=["graphicx"],
        )

        assert result.latex_command == "\\includegraphics{test.png}"
        assert result.placement == ImagePlacement.INLINE
        assert result.size_spec == "0.5\\textwidth"
        assert result.requires_packages == ["graphicx"]
        assert result.caption is None

    def test_placement_result_with_caption(self):
        """Test placement result with caption."""
        result = PlacementResult(
            latex_command="\\begin{figure}...",
            placement=ImagePlacement.FLOAT_HERE,
            size_spec="0.8\\textwidth",
            requires_packages=["graphicx", "float"],
            caption="Test Caption",
        )

        assert result.caption == "Test Caption"


@pytest.mark.rendering
class TestImagePlacer:
    """Test the main image placement functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.config = PlacementConfig()
        self.placer = ImagePlacer(self.config)
        self.image_path = Path("test.png")

    def test_determine_placement_explicit(self):
        """Test placement determination with explicit hint."""
        image_entry = {"placement": "wrap-left"}

        placement = self.placer._determine_placement(image_entry, None)

        assert placement == ImagePlacement.WRAP_LEFT

    def test_determine_placement_creature_context(self):
        """Test placement determination for creature context."""
        image_entry = {}

        placement = self.placer._determine_placement(image_entry, "creature")

        assert placement == ImagePlacement.WRAP_RIGHT

    def test_determine_placement_item_context(self):
        """Test placement determination for item context."""
        image_entry = {}

        placement = self.placer._determine_placement(image_entry, "item")

        assert placement == ImagePlacement.WRAP_LEFT

    def test_determine_placement_chapter_art_context(self):
        """Test placement determination for chapter art context."""
        image_entry = {}

        placement = self.placer._determine_placement(image_entry, "chapter-art")

        assert placement == ImagePlacement.FULL_WIDTH

    def test_determine_placement_default(self):
        """Test default placement determination."""
        image_entry = {}

        placement = self.placer._determine_placement(image_entry, None)

        assert placement == self.config.default_placement

    def test_determine_size_spec_explicit(self):
        """Test size specification with explicit hint."""
        image_entry = {"size": "large"}

        size_spec = self.placer._determine_size_spec(
            image_entry, None, ImagePlacement.FLOAT_HERE
        )

        assert size_spec == "0.8\\textwidth"

    def test_determine_size_spec_creature_wrap(self):
        """Test size specification for wrapped creature image."""
        image_entry = {}

        size_spec = self.placer._determine_size_spec(
            image_entry, "creature", ImagePlacement.WRAP_RIGHT
        )

        assert size_spec == "0.4\\textwidth"

    def test_determine_size_spec_creature_float(self):
        """Test size specification for floating creature image."""
        image_entry = {}

        size_spec = self.placer._determine_size_spec(
            image_entry, "creature", ImagePlacement.FLOAT_HERE
        )

        assert size_spec == "0.6\\textwidth"

    def test_size_hint_to_spec_regular(self):
        """Test size hint conversion for regular placement."""
        size_spec = self.placer._size_hint_to_spec("medium", ImagePlacement.FLOAT_HERE)

        assert size_spec == "0.5\\textwidth"

    def test_size_hint_to_spec_wrapped(self):
        """Test size hint conversion for wrapped placement."""
        size_spec = self.placer._size_hint_to_spec("medium", ImagePlacement.WRAP_LEFT)

        assert size_spec == "0.35\\textwidth"

    def test_generate_inline_command(self):
        """Test inline image command generation."""
        command = self.placer._generate_inline_command(
            self.image_path, "0.3\\textwidth"
        )

        assert command == "\\includegraphics[width=0.3\\textwidth]{test.png}"

    def test_generate_wrap_command_right(self):
        """Test wrapped image command generation (right side)."""
        command = self.placer._generate_wrap_command(
            self.image_path,
            "Test Caption",
            ImagePlacement.WRAP_RIGHT,
            "0.4\\textwidth",
            "fig:test",
        )

        assert "\\begin{wrapfigure}{r}{0.4\\textwidth}" in command
        assert "\\includegraphics[width=0.4\\textwidth]{test.png}" in command
        assert "\\caption{Test Caption}" in command
        assert "\\label{fig:test}" in command
        assert "\\end{wrapfigure}" in command

    def test_generate_wrap_command_left(self):
        """Test wrapped image command generation (left side)."""
        command = self.placer._generate_wrap_command(
            self.image_path, "", ImagePlacement.WRAP_LEFT, "0.3\\textwidth"
        )

        assert "\\begin{wrapfigure}{l}{0.3\\textwidth}" in command
        assert "\\includegraphics[width=0.3\\textwidth]{test.png}" in command
        assert "\\caption" not in command
        assert "\\label" not in command

    def test_generate_margin_command(self):
        """Test margin image command generation."""
        command = self.placer._generate_margin_command(
            self.image_path, "Margin Note", "0.2\\textwidth"
        )

        assert (
            "\\marginpar{\\includegraphics[width=0.2\\textwidth]{test.png}" in command
        )
        assert "\\small Margin Note" in command

    def test_generate_margin_command_no_title(self):
        """Test margin image command without title."""
        command = self.placer._generate_margin_command(
            self.image_path, "", "0.2\\textwidth"
        )

        assert (
            "\\marginpar{\\includegraphics[width=0.2\\textwidth]{test.png}}" == command
        )

    def test_generate_full_width_command(self):
        """Test full-width image command generation."""
        command = self.placer._generate_full_width_command(
            self.image_path, "Full Width Caption", "fig:fullwidth"
        )

        assert "\\begin{figure*}[t]" in command
        assert "\\includegraphics[width=\\textwidth]{test.png}" in command
        assert "\\caption{Full Width Caption}" in command
        assert "\\label{fig:fullwidth}" in command
        assert "\\end{figure*}" in command

    def test_generate_float_command(self):
        """Test floating figure command generation."""
        command = self.placer._generate_float_command(
            self.image_path,
            "Float Caption",
            ImagePlacement.FLOAT_TOP,
            "0.8\\textwidth",
            "fig:float",
        )

        assert "\\begin{figure}[t]" in command
        assert "\\includegraphics[width=0.8\\textwidth]{test.png}" in command
        assert "\\caption{Float Caption}" in command
        assert "\\label{fig:float}" in command
        assert "\\end{figure}" in command

    def test_generate_label_from_id(self):
        """Test label generation from image ID."""
        image_entry = {"id": "dragon-image"}

        label = self.placer._generate_label(image_entry)

        assert label == "fig:dragon-image"

    def test_generate_label_from_title(self):
        """Test label generation from image title."""
        image_entry = {"title": "Ancient Red Dragon"}

        label = self.placer._generate_label(image_entry)

        assert label == "fig:ancient-red-dragon"

    def test_generate_label_none(self):
        """Test label generation with no ID or title."""
        image_entry = {}

        label = self.placer._generate_label(image_entry)

        assert label is None

    def test_get_required_packages_wrap(self):
        """Test required packages for wrapped images."""
        packages = self.placer._get_required_packages(ImagePlacement.WRAP_LEFT)

        assert "graphicx" in packages
        assert "wrapfig" in packages

    def test_get_required_packages_float(self):
        """Test required packages for floating images."""
        packages = self.placer._get_required_packages(ImagePlacement.FLOAT_HERE)

        assert "graphicx" in packages
        assert "float" in packages

    def test_get_required_packages_full_width(self):
        """Test required packages for full-width images."""
        packages = self.placer._get_required_packages(ImagePlacement.FULL_WIDTH)

        assert "graphicx" in packages
        assert "float" in packages

    def test_place_image_integration(self):
        """Test complete image placement integration."""
        image_entry = {
            "title": "Test Dragon",
            "placement": "wrap-right",
            "size": "medium",
        }

        result = self.placer.place_image(self.image_path, image_entry, "creature")

        assert isinstance(result, PlacementResult)
        assert result.placement == ImagePlacement.WRAP_RIGHT
        assert "wrapfigure" in result.latex_command
        assert "Test Dragon" in result.latex_command
        assert result.caption == "Test Dragon"
        assert "wrapfig" in result.requires_packages
