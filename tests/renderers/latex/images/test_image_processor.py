"""Tests for the image processor core functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from studiorum.latex_engine.core.images.image_processor import (
    ImageProcessingConfig,
    ImageProcessor,
    ProcessedImage,
)
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


@pytest.mark.rendering
class TestImageProcessingConfig:
    """Test the image processing configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ImageProcessingConfig()

        assert config.enable_webp_conversion is True
        assert config.enable_optimization is True
        assert config.enable_placement_optimization is True
        assert config.cache_processed_images is True
        assert config.max_image_width == 1200
        assert config.jpeg_quality == 85
        assert config.png_compression == 6

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ImageProcessingConfig(
            enable_webp_conversion=False,
            max_image_width=800,
            jpeg_quality=90,
        )

        assert config.enable_webp_conversion is False
        assert config.max_image_width == 800
        assert config.jpeg_quality == 90
        # Other values should remain default
        assert config.enable_optimization is True

    def test_invalid_config(self):
        """Test validation of configuration values."""
        with pytest.raises(ValidationError):
            ImageProcessingConfig(jpeg_quality=150)  # Should be 1-100

        with pytest.raises(ValidationError):
            ImageProcessingConfig(png_compression=15)  # Should be 0-9


@pytest.mark.rendering
class TestProcessedImage:
    """Test the processed image result model."""

    def test_processed_image_creation(self):
        """Test creating a processed image result."""
        result = ProcessedImage(
            original_path=Path("test.webp"),
            processed_path=Path("test.png"),
            latex_command="\\includegraphics{test.png}",
            width_specification="0.8\\textwidth",
        )

        assert result.original_path == Path("test.webp")
        assert result.processed_path == Path("test.png")
        assert result.latex_command == "\\includegraphics{test.png}"
        assert result.width_specification == "0.8\\textwidth"
        assert result.placement_hint is None
        assert result.caption is None

    def test_processed_image_with_caption(self):
        """Test processed image with caption and placement hint."""
        result = ProcessedImage(
            original_path=Path("test.png"),
            processed_path=Path("test_opt.png"),
            latex_command="\\begin{figure}...",
            width_specification="0.5\\textwidth",
            placement_hint="wrap-right",
            caption="Test Image",
        )

        assert result.placement_hint == "wrap-right"
        assert result.caption == "Test Image"


@pytest.mark.rendering
class TestImageProcessor:
    """Test the main image processor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.config = ImageProcessingConfig(
            enable_webp_conversion=True,
            enable_optimization=True,
            enable_placement_optimization=True,
        )
        self.processor = ImageProcessor(self.config)

        # Create proper render context with metadata
        self.context = RenderingContext(
            output_format="latex",
            metadata={
                "include_images": True,
                "assets_dir": Path("/tmp/assets"),
                "images_dir": Path("/tmp/images"),
            },
        )

    def test_process_image_entry_disabled(self):
        """Test processing when images are disabled."""
        # Create context with images disabled
        context = RenderingContext(
            output_format="latex", metadata={"include_images": False}
        )
        image_entry = {"href": "test.png", "title": "Test Image"}

        result = self.processor.process_image_entry(image_entry, context)

        assert result == "% Image placeholder: Test Image"

    def test_process_image_entry_no_href(self):
        """Test processing image entry without href."""
        image_entry = {"title": "Test Image"}

        result = self.processor.process_image_entry(image_entry, self.context)

        assert result == "% Image placeholder: Test Image"

    def test_process_image_entry_no_title(self):
        """Test processing image entry without title."""
        image_entry = {}

        result = self.processor.process_image_entry(image_entry, self.context)

        assert result == "% Image placeholder"

    def test_process_image_pipeline_exception(self):
        """Test handling exceptions in image processing pipeline."""
        image_entry = {"href": "test.png", "title": "Test Image"}

        # Mock the pipeline to raise an exception
        with patch.object(
            self.processor,
            "_process_image_pipeline",
            side_effect=Exception("Test error"),
        ):
            result = self.processor.process_image_entry(image_entry, self.context)

            assert "Image processing failed" in result
            assert "Test Image" in result

    def test_resolve_image_path_local(self):
        """Test resolving local image paths."""
        # Mock assets directory to exist
        with patch.object(Path, "exists", return_value=True):
            result = self.processor._resolve_image_path("test.png", self.context)

            expected = self.context.metadata["assets_dir"] / "test.png"
            assert result == expected

    def test_resolve_image_path_url(self):
        """Test resolving URL image paths."""
        result = self.processor._resolve_image_path(
            "https://example.com/test.png", self.context
        )

        # URLs are not supported yet, should return None
        assert result is None

    def test_convert_format_disabled(self):
        """Test format conversion when disabled."""
        self.processor.config.enable_webp_conversion = False
        image_path = Path("test.webp")

        result = self.processor._convert_format_if_needed(image_path)

        assert result == image_path

    def test_convert_format_not_needed(self):
        """Test format conversion when not needed."""
        image_path = Path("test.png")

        result = self.processor._convert_format_if_needed(image_path)

        assert result == image_path

    def test_optimize_image_disabled(self):
        """Test image optimization when disabled."""
        self.processor.config.enable_optimization = False
        image_path = Path("test.png")

        result = self.processor._optimize_image(image_path, self.context)

        assert result == image_path

    def test_generate_latex_basic_with_title(self):
        """Basic generation uses StudiorumImage macro via template."""
        self.processor.config.enable_placement_optimization = False

        # Create a temporary test image file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            image_path = Path(temp_file.name)

        try:
            image_entry = {"title": "Test Image"}

            result = self.processor._generate_latex_command(
                image_path, image_entry, self.context
            )

            assert "\\StudiorumImage" in result
            assert str(image_path) in result
            assert "Test Image" in result
        finally:
            # Clean up temp file
            image_path.unlink(missing_ok=True)

    def test_generate_latex_basic_no_title(self):
        """Basic generation without title returns StudiorumImage macro."""
        self.processor.config.enable_placement_optimization = False

        # Create a temporary test image file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            image_path = Path(temp_file.name)

        try:
            image_entry = {}

            result = self.processor._generate_latex_command(
                image_path, image_entry, self.context
            )

            assert "\\StudiorumImage" in result
            assert str(image_path) in result
        finally:
            # Clean up temp file
            image_path.unlink(missing_ok=True)

    def test_calculate_width_spec_default(self):
        """Test default width specification calculation."""
        image_entry = {}

        result = self.processor._calculate_width_spec(image_entry)

        assert result == "width=0.8\\columnwidth,height=0.3\\textheight,keepaspectratio"


@pytest.mark.integration
@pytest.mark.rendering
class TestImageProcessorIntegration:
    """Integration tests for image processor with real components."""

    def setup_method(self):
        """Set up integration test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.processor = ImageProcessor()
        self.context = RenderingContext(
            output_format="latex",
            metadata={
                "include_images": True,
                "assets_dir": Path("/tmp/test_assets"),
            },
        )

    def test_full_pipeline_mock(self):
        """Test full processing pipeline with mocked components."""
        image_entry = {
            "href": "test.webp",
            "title": "Test Creature",
            "placement": "wrap-right",
        }

        # Mock all the pipeline steps
        with (
            patch.object(
                self.processor, "_resolve_image_path", return_value=Path("test.webp")
            ),
            patch.object(
                self.processor,
                "_convert_format_if_needed",
                return_value=Path("test.png"),
            ),
            patch.object(
                self.processor, "_optimize_image", return_value=Path("test_opt.png")
            ),
            patch.object(
                self.processor,
                "_generate_latex_command",
                return_value="\\includegraphics{test_opt.png}",
            ),
        ):
            result = self.processor.process_image_entry(image_entry, self.context)

            assert result == "\\includegraphics{test_opt.png}"
