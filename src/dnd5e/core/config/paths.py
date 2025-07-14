"""Path configuration and management."""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..models.content import ContentType
from .settings import get_settings


class PathConfig(BaseModel):
    """Configuration for data file paths."""

    root_path: Path = Field(..., description="Root project directory")
    data_path: Optional[Path] = Field(
        None, description="External data directory (5etools-src)"
    )
    assets_path: Path = Field(..., description="Assets directory")
    output_path: Path = Field(..., description="Output directory")
    build_path: Path = Field(..., description="Build artifacts directory")

    @classmethod
    def from_settings(cls, root_path: Path) -> "PathConfig":
        """Create PathConfig from current settings."""
        settings = get_settings()

        return cls(
            root_path=root_path,
            data_path=settings.data_path,
            assets_path=root_path / settings.assets_path,
            output_path=root_path / settings.output_path,
            build_path=root_path / settings.build_path,
        )

    def get_data_paths(self) -> Dict[ContentType, List[Path]]:
        """Get data file paths organized by content type."""
        paths = {}

        # Try multiple data source locations
        data_dirs = []
        if self.data_path and self.data_path.exists():
            data_dirs.append(self.data_path)

        # Check for symlinked data directory
        data_symlink = self.root_path / "data"
        if data_symlink.exists() and data_symlink.is_symlink():
            data_dirs.append(data_symlink)

        # Check for local json_data directory
        local_data = self.root_path / "json_data"
        if local_data.exists():
            data_dirs.append(local_data)

        # Map content types to subdirectories and file patterns
        content_mappings = {
            ContentType.SPELL: ["spells", "spell"],
            ContentType.CREATURE: ["bestiary", "monster", "creatures"],
            ContentType.ITEM: ["items", "item"],
            ContentType.ADVENTURE: ["adventure", "adventures"],
            ContentType.BOOK: ["book", "books"],
            ContentType.CLASS: ["class", "classes"],
            ContentType.BACKGROUND: ["background", "backgrounds"],
            ContentType.FEAT: ["feat", "feats"],
            ContentType.RACE: ["race", "races"],
        }

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

                # Also check for files in root data directory
                if content_type == ContentType.SPELL:
                    type_paths.extend(data_dir.glob("spells*.json"))
                elif content_type == ContentType.CREATURE:
                    type_paths.extend(data_dir.glob("bestiary*.json"))
                    type_paths.extend(data_dir.glob("*monster*.json"))
                elif content_type == ContentType.ITEM:
                    type_paths.extend(data_dir.glob("items*.json"))
                elif content_type == ContentType.BACKGROUND:
                    type_paths.extend(data_dir.glob("background*.json"))
                elif content_type == ContentType.FEAT:
                    type_paths.extend(data_dir.glob("feat*.json"))
                elif content_type == ContentType.RACE:
                    type_paths.extend(data_dir.glob("race*.json"))
                elif content_type == ContentType.CLASS:
                    # Classes have a directory structure, already handled above
                    pass

            if type_paths:
                paths[content_type] = type_paths

        return paths

    def get_asset_paths(self) -> Dict[str, Path]:
        """Get asset file paths."""
        return {
            "fonts": self.assets_path / "fonts",
            "images": self.assets_path / "images",
            "packages": self.assets_path / "packages",
        }

    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.build_path.mkdir(parents=True, exist_ok=True)

        # Create output subdirectories
        for subdir in ["books", "adventures", "supplements"]:
            (self.output_path / subdir).mkdir(exist_ok=True)


# Global path config instance
_path_config: Optional[PathConfig] = None


def get_path_config(root_path: Optional[Path] = None) -> PathConfig:
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
