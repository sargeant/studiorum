"""Application settings and configuration."""

import logging
from pathlib import Path
from typing import Any

import colorlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Logging configuration
    log_level: str = Field(
        default="WARNING",
        description="Logging level for the application",
        alias="LOG_LEVEL",
    )
    log_format: str = Field(
        default=(
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(blue)s%(name)s%(reset)s: %(message)s"
        ),
        description="Log format string for colorlog",
    )

    # Data paths
    data_path: Path | None = Field(
        default=None, description="Path to D&D 5e data files", alias="DATA_PATH"
    )
    assets_path: Path = Field(
        default=Path("assets"), description="Path to asset files", alias="ASSETS_PATH"
    )
    output_path: Path = Field(
        default=Path("output"),
        description="Path for generated output files",
        alias="OUTPUT_PATH",
    )
    build_path: Path = Field(
        default=Path("build"),
        description="Path for build artifacts",
        alias="BUILD_PATH",
    )

    # Processing options
    max_workers: int = Field(
        default=4, description="Maximum number of worker processes", alias="MAX_WORKERS"
    )
    enable_caching: bool = Field(
        default=True, description="Enable content caching", alias="ENABLE_CACHING"
    )
    cache_ttl: int = Field(
        default=3600, description="Cache time-to-live in seconds", alias="CACHE_TTL"
    )

    # LaTeX options
    latex_engine: str = Field(
        default="xelatex",
        description="LaTeX engine to use for compilation",
        alias="LATEX_ENGINE",
    )
    font_dir: Path | None = Field(
        default=None, description="Directory containing custom fonts", alias="FONT_DIR"
    )

    # Validation options
    validation_strictness: str = Field(
        default="normal",
        description="Validation strictness level: strict, normal, or lenient",
        alias="VALIDATION_STRICTNESS",
    )
    validation_summary: bool = Field(
        default=False,
        description="Enable validation error summary reporting",
        alias="VALIDATION_SUMMARY",
    )
    max_duplicate_errors: int = Field(
        default=1,
        description="Maximum times to log identical validation errors",
        alias="MAX_DUPLICATE_ERRORS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
    )

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
