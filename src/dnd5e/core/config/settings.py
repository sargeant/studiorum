"""Application settings and configuration."""

import logging
from pathlib import Path
from typing import Any

import colorlog
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Logging configuration
    log_level: str = Field(default="WARNING", env="LOG_LEVEL")
    log_format: str = Field(
        default=(
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(blue)s%(name)s%(reset)s: %(message)s"
        )
    )

    # Data paths
    data_path: Path | None = Field(default=None, env="DATA_PATH")
    assets_path: Path = Field(default=Path("assets"), env="ASSETS_PATH")
    output_path: Path = Field(default=Path("output"), env="OUTPUT_PATH")
    build_path: Path = Field(default=Path("build"), env="BUILD_PATH")

    # Processing options
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # seconds

    # LaTeX options
    latex_engine: str = Field(default="xelatex", env="LATEX_ENGINE")
    font_dir: Path | None = Field(default=None, env="FONT_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def model_post_init(self, __context: Any) -> None:
        """Post-process settings after parsing."""
        pass


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
