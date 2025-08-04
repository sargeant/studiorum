"""Tests for the image format converter."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dnd5e.renderers.latex.images.format_converter import (
    ConversionResult,
    FormatConverter,
)


class TestConversionResult:
    """Test the conversion result model."""

    def test_conversion_result_creation(self):
        """Test creating a conversion result."""
        result = ConversionResult(
            original_path=Path("test.webp"),
            converted_path=Path("test.png"),
            original_format="WebP",
            target_format="PNG",
            file_size_before=1000,
            file_size_after=800,
        )

        assert result.original_path == Path("test.webp")
        assert result.converted_path == Path("test.png")
        assert result.original_format == "WebP"
        assert result.target_format == "PNG"
        assert result.file_size_before == 1000
        assert result.file_size_after == 800


@pytest.mark.skipif(
    not pytest.importorskip("PIL", None),
    reason="Pillow not available for image processing tests",
)
class TestFormatConverter:
    """Test the format converter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = FormatConverter()

    def test_is_conversion_needed_webp(self):
        """Test conversion detection for WebP files."""
        webp_path = Path("test.webp")

        result = self.converter.is_conversion_needed(webp_path)

        assert result is True

    def test_is_conversion_needed_png(self):
        """Test conversion detection for PNG files."""
        png_path = Path("test.png")

        result = self.converter.is_conversion_needed(png_path)

        assert result is False

    def test_is_conversion_needed_jpg(self):
        """Test conversion detection for JPEG files."""
        jpg_path = Path("test.jpg")

        result = self.converter.is_conversion_needed(jpg_path)

        assert result is False

    def test_is_conversion_needed_pdf(self):
        """Test conversion detection for PDF files."""
        pdf_path = Path("test.pdf")

        result = self.converter.is_conversion_needed(pdf_path)

        assert result is False

    def test_is_conversion_needed_unknown(self):
        """Test conversion detection for unknown formats."""
        unknown_path = Path("test.xyz")

        result = self.converter.is_conversion_needed(unknown_path)

        assert result is True

    @pytest.mark.asyncio
    async def test_convert_webp_to_png_file_not_found(self):
        """Test WebP conversion when file doesn't exist."""
        nonexistent_path = Path("nonexistent.webp")

        with pytest.raises(FileNotFoundError):
            await self.converter.convert_webp_to_png(nonexistent_path)

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    @patch.object(FormatConverter, "_convert_webp_sync")
    async def test_convert_webp_to_png_success(
        self, mock_convert, mock_stat, mock_exists
    ):
        """Test successful WebP to PNG conversion."""
        # Setup mocks
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=1000)
        mock_convert.return_value = None

        webp_path = Path("test.webp")

        # Create output path mock
        with patch("pathlib.Path.stat") as mock_out_stat:
            mock_out_stat.return_value = Mock(st_size=800)

            result = await self.converter.convert_webp_to_png(webp_path)

            assert isinstance(result, ConversionResult)
            assert result.original_path == webp_path
            assert result.converted_path == Path("test.png")
            assert result.original_format == "WebP"
            assert result.target_format == "PNG"
            assert result.file_size_before == 1000
            assert result.file_size_after == 800

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    @patch.object(FormatConverter, "_convert_webp_sync")
    async def test_convert_webp_to_png_custom_output(
        self, mock_convert, mock_stat, mock_exists
    ):
        """Test WebP conversion with custom output directory."""
        # Setup mocks
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=1000)
        mock_convert.return_value = None

        webp_path = Path("input/test.webp")
        output_dir = Path("output")

        with patch("pathlib.Path.stat") as mock_out_stat:
            mock_out_stat.return_value = Mock(st_size=800)

            result = await self.converter.convert_webp_to_png(webp_path, output_dir)

            assert result.converted_path == output_dir / "test.png"

    @pytest.mark.asyncio
    async def test_convert_to_compatible_format_webp(self):
        """Test compatible format conversion for WebP."""
        webp_path = Path("test.webp")

        with patch.object(self.converter, "convert_webp_to_png") as mock_convert:
            mock_result = ConversionResult(
                original_path=webp_path,
                converted_path=Path("test.png"),
                original_format="WebP",
                target_format="PNG",
                file_size_before=1000,
                file_size_after=800,
            )
            mock_convert.return_value = mock_result

            result = await self.converter.convert_to_compatible_format(webp_path)

            assert result == mock_result
            mock_convert.assert_called_once_with(webp_path, None)

    @pytest.mark.asyncio
    async def test_convert_to_compatible_format_png(self):
        """Test compatible format conversion for PNG (no conversion needed)."""
        png_path = Path("test.png")

        result = await self.converter.convert_to_compatible_format(png_path)

        assert result is None

    @pytest.mark.asyncio
    async def test_convert_to_compatible_format_unknown(self):
        """Test compatible format conversion for unknown format."""
        unknown_path = Path("test.xyz")

        with patch.object(self.converter, "_convert_unknown_format") as mock_convert:
            mock_result = ConversionResult(
                original_path=unknown_path,
                converted_path=Path("test.png"),
                original_format="XYZ",
                target_format="PNG",
                file_size_before=1000,
                file_size_after=800,
            )
            mock_convert.return_value = mock_result

            result = await self.converter.convert_to_compatible_format(unknown_path)

            assert result == mock_result
            mock_convert.assert_called_once_with(unknown_path, None)


@pytest.mark.skipif(
    pytest.importorskip("PIL", None) is None,
    reason="Pillow not available for image processing tests",
)
class TestFormatConverterSync:
    """Test synchronous conversion methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = FormatConverter()

    @patch("PIL.Image.open")
    def test_convert_webp_sync_success(self, mock_open):
        """Test synchronous WebP conversion."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.mode = "RGB"
        mock_img.save = Mock()
        mock_open.return_value.__enter__.return_value = mock_img

        webp_path = Path("test.webp")
        png_path = Path("test.png")

        self.converter._convert_webp_sync(webp_path, png_path)

        mock_open.assert_called_once_with(webp_path)
        mock_img.save.assert_called_once_with(png_path, "PNG", optimize=True)

    @patch("PIL.Image.open")
    def test_convert_webp_sync_rgba(self, mock_open):
        """Test synchronous WebP conversion with transparency."""
        # Mock PIL Image with RGBA mode
        mock_img = Mock()
        mock_img.mode = "RGBA"
        mock_img.size = (100, 100)
        mock_img.split.return_value = [Mock(), Mock(), Mock(), Mock()]  # R, G, B, A

        mock_background = Mock()
        mock_background.paste = Mock()

        mock_open.return_value.__enter__.return_value = mock_img

        with patch("PIL.Image.new", return_value=mock_background):
            webp_path = Path("test.webp")
            png_path = Path("test.png")

            self.converter._convert_webp_sync(webp_path, png_path)

            mock_background.save.assert_called_once_with(png_path, "PNG", optimize=True)

    @patch("PIL.Image.open")
    def test_convert_webp_sync_error(self, mock_open):
        """Test synchronous WebP conversion error handling."""
        mock_open.side_effect = Exception("PIL error")

        webp_path = Path("test.webp")
        png_path = Path("test.png")

        with pytest.raises(ValueError, match="Failed to convert WebP to PNG"):
            self.converter._convert_webp_sync(webp_path, png_path)

    @patch("PIL.Image.open")
    def test_convert_to_png_sync_success(self, mock_open):
        """Test synchronous conversion to PNG."""
        mock_img = Mock()
        mock_img.mode = "RGB"
        mock_img.save = Mock()
        mock_open.return_value.__enter__.return_value = mock_img

        input_path = Path("test.bmp")
        output_path = Path("test.png")

        self.converter._convert_to_png_sync(input_path, output_path)

        mock_open.assert_called_once_with(input_path)
        mock_img.save.assert_called_once_with(output_path, "PNG", optimize=True)


class TestFormatConverterWithoutPIL:
    """Test format converter behavior when PIL is not available."""

    def test_init_without_pil(self):
        """Test initialization when PIL is not available."""
        with patch.dict("sys.modules", {"PIL": None}):
            with patch(
                "dnd5e.renderers.latex.images.format_converter.PIL_AVAILABLE", False
            ):
                with pytest.raises(ImportError, match="Pillow is required"):
                    FormatConverter()
