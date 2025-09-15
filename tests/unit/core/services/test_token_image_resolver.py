"""Tests for token image resolver with WebP conversion integration."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from studiorum.core.services.token_image_resolver import TokenImageResolver


class TestTokenImageResolver:
    """Test token image resolver functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        from studiorum.core.services.container import ServiceContainer

        ServiceContainer.reset_global_instance()

    def test_initialization_with_pil_available(self) -> None:
        """Test resolver initialization when PIL is available."""
        with patch("studiorum.core.services.token_image_resolver.PIL_AVAILABLE", True):
            with tempfile.TemporaryDirectory() as temp_dir:
                base_path = Path(temp_dir)
                resolver = TokenImageResolver(base_path)

                assert resolver.base_path == base_path
                assert resolver._format_converter is not None
                assert resolver._cache_dir.exists()

    def test_initialization_without_pil(self) -> None:
        """Test resolver initialization when PIL is not available."""
        with patch("studiorum.core.services.token_image_resolver.PIL_AVAILABLE", False):
            with tempfile.TemporaryDirectory() as temp_dir:
                base_path = Path(temp_dir)
                resolver = TokenImageResolver(base_path)

                assert resolver.base_path == base_path
                assert resolver._format_converter is None
                assert resolver._cache_dir.exists()

    def test_resolve_token_image_png_preferred(self) -> None:
        """Test that PNG images are preferred over WebP."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create directory structure
            tokens_dir = base_path / "bestiary" / "tokens" / "MM"
            tokens_dir.mkdir(parents=True)

            # Create both PNG and WebP files
            png_file = tokens_dir / "Ancient Red Dragon.png"
            webp_file = tokens_dir / "Ancient Red Dragon.webp"
            png_file.touch()
            webp_file.touch()

            resolver = TokenImageResolver(base_path)
            mock_creature = Mock()
            mock_creature.name = "Ancient Red Dragon"
            mock_creature.source = Mock()
            mock_creature.source.abbreviation = "MM"
            # Ensure new token properties are not present
            mock_creature.tokenHref = None
            mock_creature.token = None

            result = resolver.resolve_token_image(mock_creature)

            # Should prefer PNG over WebP
            assert result == png_file

    def test_resolve_token_image_webp_conversion(self) -> None:
        """Test that WebP images are converted to PNG."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create directory structure
            tokens_dir = base_path / "bestiary" / "tokens" / "MM"
            tokens_dir.mkdir(parents=True)

            # Create WebP file
            webp_file = tokens_dir / "Ancient Red Dragon.webp"
            webp_file.touch()

            resolver = TokenImageResolver(base_path)

            # Mock the conversion process
            mock_converted_path = resolver._cache_dir / "converted_image.png"
            with patch.object(
                resolver, "_convert_webp_to_png", return_value=mock_converted_path
            ) as mock_convert:
                mock_creature = Mock()
                mock_creature.name = "Ancient Red Dragon"
                mock_creature.source = Mock()
                mock_creature.source.abbreviation = "MM"
                # Ensure new token properties are not present
                mock_creature.tokenHref = None
                mock_creature.token = None

                result = resolver.resolve_token_image(mock_creature)

                # Should call conversion and return converted path
                mock_convert.assert_called_once_with(webp_file)
                assert result == mock_converted_path

    def test_convert_webp_to_png_success(self) -> None:
        """Test successful WebP to PNG conversion."""
        with patch("studiorum.core.services.token_image_resolver.PIL_AVAILABLE", True):
            with tempfile.TemporaryDirectory() as temp_dir:
                base_path = Path(temp_dir)
                resolver = TokenImageResolver(base_path)

                # Create a test WebP file
                test_webp = Path(temp_dir) / "test.webp"
                test_webp.touch()
                _ = test_webp.stat().st_mtime_ns  # Ensure we have mtime

                # Mock the format converter
                mock_converter = Mock()
                mock_result = Mock()
                mock_result.converted_path = resolver._cache_dir / "test_123.png"
                mock_result.file_size_before = 1000
                mock_result.file_size_after = 800
                mock_converter.convert_webp_to_png.return_value = mock_result
                resolver._format_converter = mock_converter

                # Create expected output file
                mock_result.converted_path.touch()

                result = resolver._convert_webp_to_png(test_webp)

                assert result is not None
                assert result.exists()
                mock_converter.convert_webp_to_png.assert_called_once()

    def test_convert_webp_to_png_cached(self) -> None:
        """Test that cached conversions are reused."""
        with patch("studiorum.core.services.token_image_resolver.PIL_AVAILABLE", True):
            with tempfile.TemporaryDirectory() as temp_dir:
                base_path = Path(temp_dir)
                resolver = TokenImageResolver(base_path)

                # Create a test WebP file
                test_webp = Path(temp_dir) / "test.webp"
                test_webp.touch()
                mtime_ns = test_webp.stat().st_mtime_ns

                # Create cached file
                cache_key = f"test_{mtime_ns}"
                cached_file = resolver._cache_dir / f"{cache_key}.png"
                cached_file.touch()

                # Mock the format converter (should not be called)
                mock_converter = Mock()
                resolver._format_converter = mock_converter

                result = resolver._convert_webp_to_png(test_webp)

                assert result == cached_file
                mock_converter.convert_webp_to_png.assert_not_called()

    def test_convert_webp_to_png_failure(self) -> None:
        """Test WebP conversion failure handling."""
        with patch("studiorum.core.services.token_image_resolver.PIL_AVAILABLE", True):
            with tempfile.TemporaryDirectory() as temp_dir:
                base_path = Path(temp_dir)
                resolver = TokenImageResolver(base_path)

                # Create a test WebP file
                test_webp = Path(temp_dir) / "test.webp"
                test_webp.touch()

                # Mock the format converter to raise exception
                mock_converter = Mock()
                mock_converter.convert_webp_to_png.side_effect = Exception(
                    "Conversion failed"
                )
                resolver._format_converter = mock_converter

                result = resolver._convert_webp_to_png(test_webp)

                assert result is None

    def test_convert_webp_to_png_without_converter(self) -> None:
        """Test WebP conversion when converter is not available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            resolver = TokenImageResolver(base_path)
            resolver._format_converter = None  # Simulate no PIL

            test_webp = Path(temp_dir) / "test.webp"
            test_webp.touch()

            result = resolver._convert_webp_to_png(test_webp)

            assert result is None

    def test_clear_conversion_cache(self) -> None:
        """Test clearing the conversion cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            resolver = TokenImageResolver(base_path)

            # Clear any existing files first
            resolver.clear_conversion_cache()

            # Create some cached files
            cached_files = [
                resolver._cache_dir / "file1.png",
                resolver._cache_dir / "file2.png",
                resolver._cache_dir / "file3.png",
            ]
            for f in cached_files:
                f.touch()

            removed_count = resolver.clear_conversion_cache()

            assert removed_count == 3
            for f in cached_files:
                assert not f.exists()

    def test_get_cache_stats(self) -> None:
        """Test getting cache statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            resolver = TokenImageResolver(base_path)

            # Create some cached files with content
            cached_files = [
                resolver._cache_dir / "file1.png",
                resolver._cache_dir / "file2.png",
            ]
            for i, f in enumerate(cached_files):
                f.write_text("x" * (100 * (i + 1)))  # Different sizes

            stats = resolver.get_cache_stats()

            assert stats["cached_files"] == 2
            assert stats["cache_size_bytes"] == 300  # 100 + 200 bytes

    def test_fallback_to_main_artwork_webp_conversion(self) -> None:
        """Test that main artwork WebP images are also converted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create directory structure - no token image, but main artwork exists
            bestiary_dir = base_path / "bestiary" / "MM"
            bestiary_dir.mkdir(parents=True)

            # Create WebP main artwork file
            webp_file = bestiary_dir / "Ancient Red Dragon.webp"
            webp_file.touch()

            resolver = TokenImageResolver(base_path)

            # Mock the conversion process
            mock_converted_path = resolver._cache_dir / "converted_main_artwork.png"
            with patch.object(
                resolver, "_convert_webp_to_png", return_value=mock_converted_path
            ) as mock_convert:
                mock_creature = Mock()
                mock_creature.name = "Ancient Red Dragon"
                mock_creature.source = Mock()
                mock_creature.source.abbreviation = "MM"
                # Ensure new token properties are not present
                mock_creature.tokenHref = None
                mock_creature.token = None

                result = resolver.resolve_token_image(mock_creature)

                # Should call conversion and return converted path
                mock_convert.assert_called_once_with(webp_file)
                assert result == mock_converted_path
