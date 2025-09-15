"""Token image resolver service for 5e creatures."""

from pathlib import Path
from typing import TYPE_CHECKING

from studiorum.core.config.unified_config import get_app_config
from studiorum.core.logging import get_logger
from studiorum.latex_engine.core.images.format_converter import (
    PIL_AVAILABLE,
    FormatConverter,
)

if TYPE_CHECKING:
    from ..models.creatures import Creature

logger = get_logger(__name__)


class TokenImageResolver:
    """Resolves token images from 5etools image directories."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize token image resolver.

        Args:
            base_path: Base path to 5etools-img directory. If None, uses app config.
        """
        if base_path is None:
            # Get from app configuration
            _ = get_app_config()  # Future: use app config for base path
            # Assume 5etools image base path is configured
            self.base_path = Path.home() / "Code" / "5etools-img"
        else:
            self.base_path = base_path

        # Initialize format converter if PIL is available
        self._format_converter = FormatConverter() if PIL_AVAILABLE else None

        # Cache directory for converted images
        self._cache_dir = Path.home() / ".studiorum" / "cache" / "token_images"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"TokenImageResolver initialized with base_path: {self.base_path}")
        if not PIL_AVAILABLE:
            logger.warning("PIL not available - WebP conversion disabled")

    def resolve_token_image(self, creature: "Creature") -> Path | None:
        """Resolve token image for a creature with fallback strategy.

        Token images are stored in:
        - /5etools-img/bestiary/tokens/{SOURCE}/{CreatureName}.webp

        Falls back to main creature image if no token exists:
        - /5etools-img/bestiary/{SOURCE}/{CreatureName}.webp

        Args:
            creature: Creature to resolve image for

        Returns:
            Path to image file, or None if not found
        """
        # Extract source abbreviation
        source = "MM"  # Default source
        if hasattr(creature, "source"):
            if hasattr(creature.source, "abbreviation"):
                source = creature.source.abbreviation
            elif hasattr(creature.source, "source"):
                source = creature.source.source
            elif isinstance(creature.source, str):
                source = creature.source

        # Clean creature name for file path
        creature_name = self._clean_name_for_path(creature.name)

        # Try dedicated token image first (PNG preferred for LaTeX compatibility)
        token_png_path = (
            self.base_path / "bestiary" / "tokens" / source / f"{creature_name}.png"
        )
        if token_png_path.exists():
            logger.debug(f"Found token image (PNG): {token_png_path}")
            return token_png_path

        token_path = (
            self.base_path / "bestiary" / "tokens" / source / f"{creature_name}.webp"
        )
        if token_path.exists():
            logger.debug(f"Found token image (WebP): {token_path}")
            # Convert WebP to PNG for LaTeX compatibility
            converted_path = self._convert_webp_to_png(token_path)
            return converted_path if converted_path else token_path

        # Fallback to main creature image (PNG preferred)
        main_png_path = self.base_path / "bestiary" / source / f"{creature_name}.png"
        if main_png_path.exists():
            logger.debug(
                f"Using main artwork (PNG) for {creature.name}: {main_png_path}"
            )
            return main_png_path

        main_path = self.base_path / "bestiary" / source / f"{creature_name}.webp"
        if main_path.exists():
            logger.debug(f"Using main artwork (WebP) for {creature.name}: {main_path}")
            # Convert WebP to PNG for LaTeX compatibility
            converted_path = self._convert_webp_to_png(main_path)
            return converted_path if converted_path else main_path

        # No image available
        logger.warning(
            f"No image found for creature: {creature.name} (source: {source})"
        )
        return None

    def _clean_name_for_path(self, name: str) -> str:
        """Clean creature name for use in file paths.

        Args:
            name: Raw creature name

        Returns:
            Cleaned name suitable for file paths
        """
        # Remove special characters that might cause file system issues
        # Keep basic alphanumeric, spaces, hyphens, and apostrophes
        import re

        # Replace problematic characters
        cleaned = re.sub(r"[^\w\s\-\']", "", name)

        # Replace spaces with underscores or keep as-is based on 5etools convention
        # 5etools typically uses spaces in filenames
        return cleaned.strip()

    def _convert_webp_to_png(self, webp_path: Path) -> Path | None:
        """Convert WebP image to PNG using cached conversion.

        Args:
            webp_path: Path to WebP image file

        Returns:
            Path to converted PNG file, or None if conversion fails
        """
        if not self._format_converter:
            logger.debug("Format converter not available, skipping WebP conversion")
            return None

        # Create cache key based on file path and modification time
        try:
            file_stat = webp_path.stat()
            cache_key = f"{webp_path.stem}_{file_stat.st_mtime_ns}"
            cached_png_path = self._cache_dir / f"{cache_key}.png"

            # Return cached version if it exists
            if cached_png_path.exists():
                logger.debug(f"Using cached PNG conversion: {cached_png_path}")
                return cached_png_path

            # Convert WebP to PNG
            logger.debug(f"Converting WebP to PNG: {webp_path} -> {cached_png_path}")
            conversion_result = self._format_converter.convert_webp_to_png(
                webp_path, output_dir=self._cache_dir
            )

            # Rename to cache key format to include timestamp
            final_path = cached_png_path
            if conversion_result.converted_path != final_path:
                conversion_result.converted_path.rename(final_path)

            logger.debug(
                f"WebP conversion successful: {conversion_result.file_size_before} -> "
                f"{conversion_result.file_size_after} bytes"
            )
            return final_path

        except Exception as e:
            logger.error(
                f"Failed to convert WebP image {webp_path}: {e}", exc_info=True
            )
            return None

    def get_available_sources(self) -> list[str]:
        """Get list of available source directories.

        Returns:
            List of source abbreviations that have image directories
        """
        sources = []
        bestiary_path = self.base_path / "bestiary"

        if bestiary_path.exists():
            for source_dir in bestiary_path.iterdir():
                if source_dir.is_dir() and source_dir.name != "tokens":
                    sources.append(source_dir.name)

        return sorted(sources)

    def get_available_token_sources(self) -> list[str]:
        """Get list of available token source directories.

        Returns:
            List of source abbreviations that have token directories
        """
        sources = []
        tokens_path = self.base_path / "bestiary" / "tokens"

        if tokens_path.exists():
            for source_dir in tokens_path.iterdir():
                if source_dir.is_dir():
                    sources.append(source_dir.name)

        return sorted(sources)

    def has_token_image(self, creature: "Creature") -> bool:
        """Check if creature has a dedicated token image (not fallback).

        Args:
            creature: Creature to check

        Returns:
            True if dedicated token image exists
        """
        # Extract source abbreviation
        source = "MM"  # Default source
        if hasattr(creature, "source"):
            if hasattr(creature.source, "abbreviation"):
                source = creature.source.abbreviation
            elif hasattr(creature.source, "source"):
                source = creature.source.source
            elif isinstance(creature.source, str):
                source = creature.source

        # Clean creature name for file path
        creature_name = self._clean_name_for_path(creature.name)

        # Check for dedicated token image
        token_path = (
            self.base_path / "bestiary" / "tokens" / source / f"{creature_name}.webp"
        )
        token_png_path = (
            self.base_path / "bestiary" / "tokens" / source / f"{creature_name}.png"
        )

        return token_path.exists() or token_png_path.exists()

    def get_image_stats(self) -> dict[str, int]:
        """Get statistics about available images.

        Returns:
            Dictionary with counts of token images, main images, and total creatures
        """
        stats = {
            "token_images": 0,
            "main_images": 0,
            "token_sources": 0,
            "main_sources": 0,
        }

        # Count token images
        tokens_path = self.base_path / "bestiary" / "tokens"
        if tokens_path.exists():
            for source_dir in tokens_path.iterdir():
                if source_dir.is_dir():
                    stats["token_sources"] += 1
                    for image_file in source_dir.glob("*.webp"):
                        stats["token_images"] += 1
                    for image_file in source_dir.glob("*.png"):
                        stats["token_images"] += 1

        # Count main images
        bestiary_path = self.base_path / "bestiary"
        if bestiary_path.exists():
            for source_dir in bestiary_path.iterdir():
                if source_dir.is_dir() and source_dir.name != "tokens":
                    stats["main_sources"] += 1
                    for image_file in source_dir.glob("*.webp"):
                        stats["main_images"] += 1
                    for image_file in source_dir.glob("*.png"):
                        stats["main_images"] += 1

        return stats

    def get_latex_compatible_path(self, image_path: Path | None) -> Path | None:
        """Get LaTeX-compatible image path, converting WebP to PNG if needed.

        This method is now deprecated in favor of the integrated conversion
        in resolve_token_image(), but maintained for backward compatibility.

        Args:
            image_path: Original image path

        Returns:
            Path to LaTeX-compatible image file, or None if conversion fails
        """
        if image_path is None:
            return None

        # If already PNG or JPG, return as-is
        if image_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".pdf"]:
            return image_path

        # For WebP files, convert using the integrated converter
        if image_path.suffix.lower() == ".webp":
            converted_path = self._convert_webp_to_png(image_path)
            if converted_path:
                logger.debug(f"Converted WebP to PNG: {converted_path}")
                return converted_path
            else:
                # Look for PNG equivalent as fallback
                png_path = image_path.with_suffix(".png")
                if png_path.exists():
                    logger.debug(f"Using PNG equivalent: {png_path}")
                    return png_path
                else:
                    logger.warning(
                        f"WebP conversion failed and no PNG equivalent found: {image_path}"
                    )
                    return image_path

        return image_path

    def clear_conversion_cache(self) -> int:
        """Clear the WebP conversion cache.

        Returns:
            Number of files removed from cache
        """
        if not self._cache_dir.exists():
            return 0

        removed_count = 0
        for cache_file in self._cache_dir.glob("*.png"):
            try:
                cache_file.unlink()
                removed_count += 1
            except OSError as e:
                logger.warning(f"Failed to remove cache file {cache_file}: {e}")

        logger.info(f"Cleared {removed_count} files from token image conversion cache")
        return removed_count

    def get_cache_stats(self) -> dict[str, int]:
        """Get statistics about the conversion cache.

        Returns:
            Dictionary with cache statistics
        """
        if not self._cache_dir.exists():
            return {"cached_files": 0, "cache_size_bytes": 0}

        cached_files = list(self._cache_dir.glob("*.png"))
        total_size = sum(f.stat().st_size for f in cached_files if f.exists())

        return {
            "cached_files": len(cached_files),
            "cache_size_bytes": total_size,
        }
