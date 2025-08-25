"""Path configuration and management."""

from pathlib import Path

from pydantic import BaseModel, Field

from ..models.content import ContentType
from .unified_config import get_app_config


class PathConfig(BaseModel):
    """Configuration for data file paths."""

    root_path: Path = Field(..., description="Root project directory")
    data_path: Path | None = Field(None, description="External data directory")
    assets_path: Path = Field(..., description="Assets directory")
    output_path: Path = Field(..., description="Output directory")
    build_path: Path = Field(..., description="Build artifacts directory")

    @classmethod
    def from_settings(cls, root_path: Path) -> "PathConfig":
        """Create PathConfig from current settings."""
        settings = get_app_config()

        return cls(
            root_path=root_path,
            data_path=settings.paths.data_path,
            assets_path=root_path / settings.paths.assets_path,
            output_path=root_path / settings.paths.output_path,
            build_path=root_path / settings.paths.build_path,
        )

    def get_data_paths(self) -> dict[ContentType, list[Path]]:
        """Get data file paths organized by content type."""
        paths = {}

        # Try multiple data source locations
        data_dirs = []
        if self.data_path and self.data_path.exists():
            data_dirs.append(self.data_path)

        # Check for srd-data directory
        srd_data = self.root_path / "srd-data"
        if srd_data.exists():
            data_dirs.append(srd_data)

        # Use string-based mappings and only convert to ContentType if they exist
        # This avoids the chicken-and-egg problem with dynamic ContentTypes
        string_mappings = {
            "spell": ["spells", "spell"],
            "creature": ["bestiary", "monster", "creatures"],
            "item": ["items", "item"],
            "adventure": ["adventure", "adventures"],
            "book": ["book", "books"],
            "class": ["class", "classes"],
            "background": ["background", "backgrounds"],
            "feat": ["feat", "feats"],
            "race": ["race", "races"],
        }

        # Convert to ContentType only if the enum member exists
        content_mappings = {}
        for type_str, subdirs in string_mappings.items():
            try:
                content_type = ContentType(type_str)
                content_mappings[content_type] = subdirs
            except ValueError:
                # Skip content types that don't exist as enum members yet
                # They will be handled by UnifiedSourceManager after registry initialization
                continue

        for content_type, subdirs in content_mappings.items():
            type_paths = []

            for data_dir in data_dirs:
                # Check each possible subdirectory
                for subdir in subdirs:
                    subdir_path = data_dir / subdir
                    if subdir_path.exists():
                        # Find JSON files in this directory
                        json_files = list(subdir_path.glob("*.json"))
                        type_paths.extend(json_files)

                # Also check for files in root data directory using string comparisons
                if content_type.value == "spell":
                    type_paths.extend(data_dir.glob("spells*.json"))
                elif content_type.value == "creature":
                    type_paths.extend(data_dir.glob("bestiary*.json"))
                    type_paths.extend(data_dir.glob("*monster*.json"))
                elif content_type.value == "item":
                    type_paths.extend(data_dir.glob("items*.json"))
                elif content_type.value == "background":
                    type_paths.extend(data_dir.glob("background*.json"))
                elif content_type.value == "feat":
                    type_paths.extend(data_dir.glob("feat*.json"))
                elif content_type.value == "race":
                    type_paths.extend(data_dir.glob("race*.json"))
                elif content_type.value == "class":
                    # Classes have a directory structure, already handled above
                    pass

            if type_paths:
                paths[content_type] = type_paths

        return paths

    def get_asset_paths(self) -> dict[str, Path]:
        """Get asset file paths."""
        return {
            "fonts": self.assets_path / "fonts",
            "images": self.assets_path / "images",
            "packages": self.assets_path / "packages",
        }

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.build_path.mkdir(parents=True, exist_ok=True)

        # Create output subdirectories
        for subdir in ["books", "adventures", "supplements"]:
            (self.output_path / subdir).mkdir(exist_ok=True)


# Global path config instance
_path_config: PathConfig | None = None


def get_path_config(root_path: Path | None = None) -> PathConfig:
    """Get global path configuration."""
    global _path_config
    if _path_config is None:
        if root_path is None:
            # Try to detect root path
            current = Path.cwd()
            # Look for pyproject.toml or CLAUDE.md to identify project root
            for parent in [current] + list(current.parents):
                if (parent / "pyproject.toml").exists() or (
                    parent / "CLAUDE.md"
                ).exists():
                    root_path = parent
                    break
            else:
                root_path = current

        _path_config = PathConfig.from_settings(root_path)
        _path_config.ensure_directories()

    return _path_config


def reset_path_config() -> None:
    """Reset global path configuration for testing.

    This function clears the global path configuration instance to ensure
    clean test isolation and prevent path configurations from persisting
    across test runs.
    """
    global _path_config
    _path_config = None
