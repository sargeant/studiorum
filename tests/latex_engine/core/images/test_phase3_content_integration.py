"""Comprehensive tests for Phase 3 Content Integration components.

This test module covers:
- GalleryProcessor multi-image layout functionality
- RecursiveEntryProcessor gallery entry handling
- BestiaryImageIntegration creature statblock integration
- ItemImageIntegration magic item collection processing
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from studiorum.core.models.entry_types import GalleryEntry
from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
from studiorum.latex_engine.core.images.gallery_processor import (
    GalleryConfig,
    GalleryLayout,
    GalleryProcessor,
    ProcessedGallery,
)
from studiorum.latex_engine.core.images.image_processor import (
    ImageProcessor,
)
from studiorum.renderers.core.interfaces import RenderingContext


class TestGalleryEntry:
    """Test the GalleryEntry Pydantic model."""

    def test_gallery_entry_creation(self):
        """Test creating a gallery entry with proper validation."""
        gallery_data = {
            "type": "gallery",
            "images": [
                {
                    "href": {"type": "external", "path": "image1.webp"},
                    "title": "First Image",
                },
                {
                    "href": {"type": "external", "path": "image2.webp"},
                    "title": "Second Image",
                },
            ],
            "layout": "grid",
            "caption": "Test gallery",
            "columns": 2,
        }

        gallery = GalleryEntry(**gallery_data)

        assert gallery.type == "gallery"
        assert len(gallery.images) == 2
        assert gallery.layout == "grid"
        assert gallery.caption == "Test gallery"
        assert gallery.columns == 2

    def test_gallery_entry_defaults(self):
        """Test gallery entry with default values."""
        gallery = GalleryEntry()

        assert gallery.type == "gallery"
        assert gallery.images == []
        assert gallery.layout is None
        assert gallery.caption is None
        assert gallery.columns is None

    def test_gallery_entry_validation(self):
        """Test gallery entry field validation."""
        with pytest.raises(ValueError):
            # Invalid columns (too high)
            GalleryEntry(columns=10)

        with pytest.raises(ValueError):
            # Invalid columns (too low)
            GalleryEntry(columns=0)


class TestGalleryProcessor:
    """Test the GalleryProcessor functionality."""

    def setup_method(self):
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.config = GalleryConfig()
        self.processor = GalleryProcessor(
            config=self.config, image_processor=self.mock_image_processor
        )
        self.context = RenderingContext(
            output_format="latex",
            metadata={"include_images": True},
        )

    def test_gallery_processor_initialization(self):
        """Test gallery processor initialization."""
        processor = GalleryProcessor()

        assert processor.config.default_layout == GalleryLayout.GRID
        assert processor.config.default_columns == 2
        assert processor._image_processor is None

    def test_process_empty_gallery(self):
        """Test processing empty gallery returns error."""
        gallery_entry = {"type": "gallery", "images": []}

        result = self.processor.process_gallery(gallery_entry, self.context)

        assert result.is_error()
        assert "contains no images" in str(result.error)  # type: ignore[attr-defined]

    def test_process_gallery_basic(self):
        """Test basic gallery processing with mock image processor."""
        # Mock image processor to return LaTeX
        self.mock_image_processor.process_image_entry.return_value = (
            "\\includegraphics[width=\\textwidth]{test.png}"
        )

        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "image1.png"}, "title": "Image 1"},
                {"href": {"path": "image2.png"}, "title": "Image 2"},
            ],
            "layout": "grid",
            "caption": "Test Gallery",
        }

        result = self.processor.process_gallery(gallery_entry, self.context)

        assert result.is_success()
        processed = result.unwrap()
        assert isinstance(processed, ProcessedGallery)
        assert processed.layout_used == GalleryLayout.GRID
        assert processed.image_count == 2
        assert "\\begin{figure}" in processed.latex_command
        assert "Test Gallery" in processed.latex_command

    def test_determine_layout(self):
        """Test layout determination logic."""
        # Test known layouts
        assert (
            self.processor._determine_layout({"layout": "grid"}) == GalleryLayout.GRID
        )
        assert (
            self.processor._determine_layout({"layout": "showcase"})
            == GalleryLayout.SHOWCASE
        )
        assert (
            self.processor._determine_layout({"layout": "sequential"})
            == GalleryLayout.SEQUENTIAL
        )
        assert (
            self.processor._determine_layout({"layout": "comparison"})
            == GalleryLayout.COMPARISON
        )

        # Test unknown layout falls back to default
        assert (
            self.processor._determine_layout({"layout": "unknown"})
            == GalleryLayout.GRID
        )
        assert self.processor._determine_layout({}) == GalleryLayout.GRID

    def test_process_gallery_image_success(self):
        """Test successful individual image processing."""
        self.mock_image_processor.process_image_entry.return_value = (
            "\\includegraphics[width=\\textwidth]{test.png}"
        )

        image_data = {"href": {"path": "test.png"}, "title": "Test Image"}

        result = self.processor._process_gallery_image(image_data, self.context, 0)

        assert result.is_success()
        processed = result.unwrap()
        assert processed["title"] == "Test Image"
        assert processed["index"] == 0

    def test_process_gallery_image_fallback(self):
        """Test image processing fallback when no image processor available."""
        processor = GalleryProcessor()  # No image processor
        image_data = {"href": {"path": "test.png"}, "title": "Test Image"}

        result = processor._process_gallery_image(image_data, self.context, 0)

        assert result.is_success()
        processed = result.unwrap()
        assert "subfigure" in processed["latex_command"]

    def test_generate_grid_layout(self):
        """Test grid layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{img1.png}", "title": "Image 1"},
            {"latex_command": "\\includegraphics{img2.png}", "title": "Image 2"},
        ]
        gallery_entry = {"columns": 2, "caption": "Grid Gallery"}

        # Set placement_mode to automatic to get figure environments
        self.context.metadata["placement_mode"] = "automatic"

        result = self.processor._generate_grid_layout(
            processed_images, gallery_entry, self.context
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "\\begin{figure}[htbp]" in latex
        assert "Grid Gallery" in latex
        assert "subfigure" in latex

    def test_generate_showcase_layout(self):
        """Test showcase layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{main.png}", "title": "Main Image"},
            {"latex_command": "\\includegraphics{thumb1.png}", "title": "Thumb 1"},
            {"latex_command": "\\includegraphics{thumb2.png}", "title": "Thumb 2"},
        ]
        gallery_entry = {"caption": "Showcase Gallery"}

        # Set placement_mode to automatic to get figure environments
        self.context.metadata["placement_mode"] = "automatic"

        result = self.processor._generate_showcase_layout(
            processed_images, gallery_entry, self.context
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "0.7\\textwidth" in latex  # Main image width
        assert "0.15\\textwidth" in latex  # Thumbnail width
        assert "Showcase Gallery" in latex

    def test_generate_sequential_layout(self):
        """Test sequential layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{img1.png}", "title": "Image 1"},
            {"latex_command": "\\includegraphics{img2.png}", "title": "Image 2"},
        ]
        gallery_entry = {"caption": "Sequential Gallery"}

        # Set placement_mode to automatic to get figure environments
        self.context.metadata["placement_mode"] = "automatic"

        result = self.processor._generate_sequential_layout(
            processed_images, gallery_entry, self.context
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "0.8\\textwidth" in latex  # Sequential image width
        assert "Sequential Gallery" in latex
        assert latex.count("\\begin{subfigure}") == 2

    def test_generate_comparison_layout(self):
        """Test comparison layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{before.png}", "title": "Before"},
            {"latex_command": "\\includegraphics{after.png}", "title": "After"},
        ]
        gallery_entry = {"caption": "Comparison Gallery"}

        # Set placement_mode to automatic to get figure environments
        self.context.metadata["placement_mode"] = "automatic"

        result = self.processor._generate_comparison_layout(
            processed_images, gallery_entry, self.context
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "\\hfill" in latex  # Images side by side
        assert "Comparison Gallery" in latex

    def test_extract_image_command(self):
        """Test extracting includegraphics command from LaTeX."""
        latex_with_figure = """\\begin{figure}[htbp]
    \\centering
    \\includegraphics[width=0.5\\textwidth]{image.png}
    \\caption{Test}
\\end{figure}"""

        result = self.processor._extract_image_command(latex_with_figure)
        assert result == "\\includegraphics[width=0.5\\textwidth]{image.png}"

        # Test with just includegraphics
        just_includegraphics = "\\includegraphics[width=0.8\\textwidth]{test.png}"
        result = self.processor._extract_image_command(just_includegraphics)
        assert result == just_includegraphics

    def test_get_required_packages(self):
        """Test required LaTeX packages identification."""
        packages = self.processor._get_required_packages(GalleryLayout.GRID)
        assert "graphicx" in packages
        assert "subcaption" in packages
        assert "calc" in packages  # For grid layout


class TestRecursiveEntryProcessorGallery:
    """Test gallery processing integration in RecursiveEntryProcessor."""

    def setup_method(self):
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.processor = RecursiveEntryProcessor(
            image_processor=self.mock_image_processor
        )
        self.context = RenderingContext(
            output_format="latex",
            metadata={"include_images": True},
        )

    def test_process_gallery_entry(self):
        """Test processing gallery entry through entry processor."""
        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "img1.png"}, "title": "Image 1"},
                {"href": {"path": "img2.png"}, "title": "Image 2"},
            ],
            "layout": "grid",
        }

        result = self.processor.process_entry_dict(gallery_entry, self.context)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain LaTeX gallery structure
        assert "\\begin{figure}" in result or "subfigure" in result

    def test_process_gallery_images_disabled(self):
        """Test gallery processing when images are disabled."""
        context_no_images = RenderingContext(
            output_format="latex",
            metadata={"include_images": False},
        )

        gallery_entry = {
            "type": "gallery",
            "images": [{"href": {"path": "img.png"}, "title": "Image"}],
            "title": "Test Gallery",
        }

        result = self.processor.process_entry_dict(gallery_entry, context_no_images)

        assert "% Gallery placeholder: Test Gallery" in result

    def test_process_gallery_basic_fallback(self):
        """Test basic gallery processing fallback."""
        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "img1.png"}, "title": "Image 1"},
                {"href": {"path": "img2.png"}, "title": "Image 2"},
            ],
            "caption": "Fallback Gallery",
        }

        # Mock gallery processor to fail, forcing fallback
        with patch.object(self.processor, "_get_gallery_processor", return_value=None):
            result = self.processor._process_gallery_basic(gallery_entry, self.context)

        assert "\\begin{figure}[htbp]" in result
        assert "Fallback Gallery" in result
        assert "subfigure" in result

    def test_get_gallery_processor(self):
        """Test gallery processor lazy initialization."""
        # First call should create processor
        processor = self.processor._get_gallery_processor()
        assert processor is not None

        # Second call should return same instance
        processor2 = self.processor._get_gallery_processor()
        assert processor is processor2


class TestPhase3Integration:
    """Integration tests for Phase 3 components working together."""

    def setup_method(self):
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.context = RenderingContext(
            output_format="latex",
            metadata={"include_images": True},
        )

    def test_end_to_end_gallery_processing(self):
        """Test complete gallery processing from entry to LaTeX."""
        # Create entry processor with image processor
        entry_processor = RecursiveEntryProcessor(
            image_processor=self.mock_image_processor
        )

        # Mock image processor responses
        self.mock_image_processor.process_image_entry.return_value = (
            "\\includegraphics[width=\\textwidth]{test.png}"
        )

        # Create gallery entry
        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "dragon1.png"}, "title": "Ancient Dragon"},
                {"href": {"path": "dragon2.png"}, "title": "Young Dragon"},
            ],
            "layout": "comparison",
            "caption": "Dragon Age Comparison",
        }

        # Process the gallery
        result = entry_processor.process_entry_dict(gallery_entry, self.context)

        assert isinstance(result, str)
        assert "\\begin{figure}" in result
        assert "Dragon Age Comparison" in result
        assert "subfigure" in result
