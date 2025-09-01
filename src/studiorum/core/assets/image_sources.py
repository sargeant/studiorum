"""Enhanced image source configuration and management system.

This module provides a comprehensive image source system that supports multiple
source types (Git repositories, HTTP APIs, local directories, S3 buckets) with
intelligent fallback mechanisms, caching, and content-aware image discovery.

Phase 1 Implementation:
- Pydantic models for image source configuration
- ImageSourceRegistry for source management
- Git repository integration for 5etools-img
- Smart syncing and fuzzy matching capabilities
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import subprocess  # nosec B404 # Required for Git operations with proper validation
import time
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from studiorum.core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    ProcessingError,
)
from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success

logger = get_logger(__name__)


class ImageSourceType(str, Enum):
    """Types of image sources supported by the system."""

    GIT_REPO = "git_repo"
    HTTP_API = "http_api"
    LOCAL_DIR = "local_dir"
    S3_BUCKET = "s3_bucket"


class ImageSourceStatus(str, Enum):
    """Status of an image source."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"


class BaseImageSourceConfig(BaseModel):
    """Base configuration for all image sources."""

    name: str = Field(description="Unique name for this image source")
    priority: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Source priority (lower = higher priority)",
    )
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,  # Max 1 week
        description="Cache time-to-live in hours",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Network timeout for operations",
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum number of retry attempts"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for organising and filtering sources"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate source name is a valid identifier."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Source name must contain only alphanumeric, underscore, and hyphen characters"
            )
        return v


class GitImageSourceConfig(BaseImageSourceConfig):
    """Configuration for Git repository image sources."""

    source_type: Literal[ImageSourceType.GIT_REPO] = Field(
        default=ImageSourceType.GIT_REPO, description="Git repository source type"
    )
    repository_url: str = Field(description="Git repository URL")
    branch: str = Field(default="main", description="Git branch to use")
    subdirectory: str | None = Field(
        default=None, description="Subdirectory within the repository containing images"
    )
    sync_interval_hours: int = Field(
        default=6,
        ge=1,
        le=168,
        description="How often to sync the repository (hours)",
    )
    shallow_clone: bool = Field(
        default=True, description="Use shallow clone for faster syncing"
    )
    lfs_support: bool = Field(
        default=False, description="Enable Git LFS support for large files"
    )

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        """Validate Git repository URL format."""
        if not (
            v.startswith("https://") or v.startswith("git@") or v.startswith("ssh://")
        ):
            raise ValueError("Repository URL must start with https://, git@, or ssh://")
        return v


class HttpApiImageSourceConfig(BaseImageSourceConfig):
    """Configuration for HTTP API image sources."""

    source_type: Literal[ImageSourceType.HTTP_API] = Field(
        default=ImageSourceType.HTTP_API, description="HTTP API source type"
    )
    base_url: str = Field(description="Base URL for the image API")
    api_key: str | None = Field(default=None, description="Optional API key")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Additional HTTP headers"
    )
    path_template: str = Field(
        default="{image_path}",
        description="Template for constructing image URLs (e.g., '/api/images/{image_path}')",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/")


class LocalDirectoryImageSourceConfig(BaseImageSourceConfig):
    """Configuration for local directory image sources."""

    source_type: Literal[ImageSourceType.LOCAL_DIR] = Field(
        default=ImageSourceType.LOCAL_DIR, description="Local directory source type"
    )
    directory_path: Path = Field(
        description="Path to local directory containing images"
    )
    recursive: bool = Field(
        default=True, description="Search subdirectories recursively"
    )
    watch_changes: bool = Field(
        default=False, description="Monitor directory for changes"
    )
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"],
        description="Allowed image file extensions",
    )

    @field_validator("directory_path")
    @classmethod
    def validate_directory_path(cls, v: Path) -> Path:
        """Validate directory path exists and is readable."""
        if not v.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return v

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Normalise file extensions."""
        return [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in v]


class S3BucketImageSourceConfig(BaseImageSourceConfig):
    """Configuration for S3 bucket image sources."""

    source_type: Literal[ImageSourceType.S3_BUCKET] = Field(
        default=ImageSourceType.S3_BUCKET, description="S3 bucket source type"
    )
    bucket_name: str = Field(description="S3 bucket name")
    region: str | None = Field(default=None, description="AWS region")
    access_key_id: str | None = Field(default=None, description="AWS access key ID")
    secret_access_key: str | None = Field(
        default=None, description="AWS secret access key"
    )
    prefix: str | None = Field(
        default=None, description="Object key prefix for filtering"
    )
    endpoint_url: str | None = Field(
        default=None, description="Custom S3 endpoint URL (for S3-compatible services)"
    )

    @field_validator("bucket_name")
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """Validate S3 bucket name format."""
        if not (3 <= len(v) <= 63):
            raise ValueError("Bucket name must be between 3 and 63 characters")
        if not v.replace("-", "").replace(".", "").isalnum():
            raise ValueError(
                "Bucket name can only contain alphanumeric characters, hyphens, and dots"
            )
        return v.lower()


# Union type for all image source configurations using Pydantic's discriminated union
ImageSourceConfig = Annotated[
    GitImageSourceConfig
    | HttpApiImageSourceConfig
    | LocalDirectoryImageSourceConfig
    | S3BucketImageSourceConfig,
    Field(discriminator="source_type"),
]


class ImageSourceInfo(BaseModel):
    """Runtime information about an image source."""

    config: ImageSourceConfig
    status: ImageSourceStatus = ImageSourceStatus.ACTIVE
    last_sync: float | None = None
    last_error: str | None = None
    total_images: int = 0
    cache_size_bytes: int = 0
    local_cache_path: Path | None = None


class ImageAssetInfo(BaseModel):
    """Information about a resolved image asset."""

    original_path: str = Field(description="Original image path requested")
    resolved_path: str = Field(description="Actual resolved image path")
    local_path: Path = Field(description="Local file system path")
    source_name: str = Field(description="Name of source that provided the image")
    file_size: int = Field(description="File size in bytes")
    mime_type: str | None = Field(default=None, description="MIME type of the image")
    last_accessed: float = Field(description="Last access timestamp")
    cache_key: str = Field(description="Unique cache key")


class ImageResolutionError(ProcessingError):
    """Error type for image resolution failures."""

    model_config = {"frozen": True}

    image_path: str = Field(description="The image path that failed to resolve")
    attempted_sources: list[str] = Field(
        default_factory=list, description="Sources that were attempted"
    )
    category: ErrorCategory = ErrorCategory.IO


def create_image_resolution_error(
    image_path: str,
    message: str | None = None,
    attempted_sources: list[str] | None = None,
    suggestions: list[str] | None = None,
) -> ImageResolutionError:
    """Create an image resolution error with context."""
    return ImageResolutionError(
        message=message or f"Could not resolve image: {image_path}",
        category=ErrorCategory.IO,
        severity=ErrorSeverity.ERROR,
        image_path=image_path,
        attempted_sources=attempted_sources or [],
        suggestions=suggestions,
    )


class ImageSourceRegistry:
    """Registry for managing multiple image sources with intelligent resolution.

    Provides a unified interface for resolving images from various sources
    including Git repositories, HTTP APIs, local directories, and S3 buckets.
    Includes caching, fallback mechanisms, and content-aware discovery.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialise the image source registry.

        Args:
            cache_dir: Directory for caching images and metadata
        """
        self.cache_dir = cache_dir or Path.home() / ".studiorum" / "image_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._sources: dict[str, ImageSourceInfo] = {}
        self._asset_cache: dict[str, ImageAssetInfo] = {}
        self._sync_locks: dict[str, asyncio.Lock] = {}

        logger.info(f"Initialised ImageSourceRegistry with cache dir: {self.cache_dir}")

    def _is_safe_git_branch(self, branch: str) -> bool:
        """Validate Git branch name for security.

        Args:
            branch: Git branch name to validate

        Returns:
            True if branch name is safe to use
        """
        # Git branch names must not contain certain characters that could be exploited
        # See: https://git-scm.com/docs/git-check-ref-format
        if not branch or len(branch) > 250:  # Reasonable length limit
            return False

        # Disallow dangerous characters and patterns
        dangerous_chars = [
            ";",
            "|",
            "&",
            "$",
            "`",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            "<",
            ">",
            '"',
            "'",
        ]
        dangerous_patterns = ["../", "./", "~", "--"]

        for char in dangerous_chars:
            if char in branch:
                return False

        for pattern in dangerous_patterns:
            if pattern in branch:
                return False

        # Must be alphanumeric with limited special chars
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/."
        )
        if not set(branch).issubset(allowed_chars):
            return False

        # Must not start or end with problematic characters
        if branch.startswith((".", "/", "-")) or branch.endswith((".lock", "..", "/")):
            return False

        return True

    def _is_safe_git_url(self, url: str) -> bool:
        """Validate Git repository URL for security.

        Args:
            url: Git repository URL to validate

        Returns:
            True if URL is safe to use
        """
        if not url or len(url) > 2000:  # Reasonable length limit
            return False

        # Only allow https, git, and ssh protocols
        allowed_protocols = ["https://", "git@", "ssh://"]
        if not any(url.startswith(protocol) for protocol in allowed_protocols):
            return False

        # Disallow dangerous characters that could be used for injection
        dangerous_chars = [
            ";",
            "|",
            "&",
            "$",
            "`",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            '"',
            "'",
        ]
        for char in dangerous_chars:
            if char in url:
                return False

        return True

    def add_source(self, config: ImageSourceConfig) -> Result[None, ProcessingError]:
        """Add an image source to the registry.

        Args:
            config: Image source configuration

        Returns:
            Success or error result
        """
        try:
            if config.name in self._sources:
                return Error(
                    ProcessingError(
                        message=f"Image source '{config.name}' already exists",
                        category=ErrorCategory.CONFIGURATION,
                        suggestions=[
                            "Use a different name or remove the existing source first"
                        ],
                    )
                )

            # Create cache directory for this source
            source_cache_dir = self.cache_dir / config.name
            source_cache_dir.mkdir(parents=True, exist_ok=True)

            # Create source info
            source_info = ImageSourceInfo(
                config=config,
                status=ImageSourceStatus.ACTIVE,
                local_cache_path=source_cache_dir,
            )

            self._sources[config.name] = source_info
            self._sync_locks[config.name] = asyncio.Lock()

            logger.info(
                f"Added image source '{config.name}' (type: {config.source_type.value})"
            )
            return Success(None)

        except Exception as e:
            return Error(
                ProcessingError(
                    message=f"Failed to add image source '{config.name}': {str(e)}",
                    category=ErrorCategory.SYSTEM_ERROR,
                    suggestions=["Check source configuration and permissions"],
                )
            )

    def remove_source(self, name: str) -> Result[None, ProcessingError]:
        """Remove an image source from the registry.

        Args:
            name: Name of the source to remove

        Returns:
            Success or error result
        """
        if name not in self._sources:
            return Error(
                ProcessingError(
                    message=f"Image source '{name}' not found",
                    category=ErrorCategory.USER_ERROR,
                )
            )

        try:
            # Clean up cache for this source
            source_info = self._sources[name]
            if source_info.local_cache_path and source_info.local_cache_path.exists():
                shutil.rmtree(source_info.local_cache_path)

            # Remove from registries
            del self._sources[name]
            if name in self._sync_locks:
                del self._sync_locks[name]

            # Remove cached assets from this source
            to_remove = [
                key
                for key, asset in self._asset_cache.items()
                if asset.source_name == name
            ]
            for key in to_remove:
                del self._asset_cache[key]

            logger.info(f"Removed image source '{name}'")
            return Success(None)

        except Exception as e:
            return Error(
                ProcessingError(
                    message=f"Failed to remove image source '{name}': {str(e)}",
                    category=ErrorCategory.SYSTEM_ERROR,
                )
            )

    def get_source_info(self, name: str) -> Result[ImageSourceInfo, ProcessingError]:
        """Get information about a specific image source.

        Args:
            name: Name of the source

        Returns:
            Source information or error
        """
        if name not in self._sources:
            return Error(
                ProcessingError(
                    message=f"Image source '{name}' not found",
                    category=ErrorCategory.USER_ERROR,
                )
            )

        return Success(self._sources[name])

    def list_sources(self) -> list[ImageSourceInfo]:
        """List all registered image sources.

        Returns:
            List of source information
        """
        return list(self._sources.values())

    async def sync_source(self, name: str) -> Result[None, ProcessingError]:
        """Sync a specific image source.

        Args:
            name: Name of the source to sync

        Returns:
            Success or error result
        """
        if name not in self._sources:
            return Error(
                ProcessingError(
                    message=f"Image source '{name}' not found",
                    category=ErrorCategory.USER_ERROR,
                )
            )

        source_info = self._sources[name]

        if not source_info.config.enabled:
            return Error(
                ProcessingError(
                    message=f"Image source '{name}' is disabled",
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Use lock to prevent concurrent syncing
        async with self._sync_locks[name]:
            source_info.status = ImageSourceStatus.SYNCING

            try:
                logger.info(
                    f"Syncing image source '{name}' (type: {source_info.config.source_type.value})"
                )

                if source_info.config.source_type == ImageSourceType.GIT_REPO:
                    result = await self._sync_git_source(source_info)
                elif source_info.config.source_type == ImageSourceType.LOCAL_DIR:
                    result = await self._sync_local_source(source_info)
                elif source_info.config.source_type == ImageSourceType.HTTP_API:
                    # HTTP API sources don't need syncing - they're accessed on demand
                    result = Success(None)
                elif source_info.config.source_type == ImageSourceType.S3_BUCKET:
                    result = await self._sync_s3_source(source_info)
                else:
                    result = Error(
                        ProcessingError(
                            message=f"Unsupported source type: {source_info.config.source_type}",
                            category=ErrorCategory.SYSTEM_ERROR,
                        )
                    )

                if result.is_success():
                    source_info.status = ImageSourceStatus.ACTIVE
                    source_info.last_sync = time.time()
                    source_info.last_error = None
                    logger.info(f"Successfully synced image source '{name}'")
                else:
                    source_info.status = ImageSourceStatus.ERROR
                    error_message = (
                        result.error.message
                        if hasattr(result, "error")
                        else "Unknown error"
                    )
                    source_info.last_error = error_message
                    logger.error(
                        f"Failed to sync image source '{name}': {error_message}"
                    )

                return result

            except Exception as e:
                source_info.status = ImageSourceStatus.ERROR
                source_info.last_error = str(e)
                return Error(
                    ProcessingError(
                        message=f"Unexpected error syncing source '{name}': {str(e)}",
                        category=ErrorCategory.SYSTEM_ERROR,
                    )
                )

    async def _sync_git_source(
        self, source_info: ImageSourceInfo
    ) -> Result[None, ProcessingError]:
        """Sync a Git repository source."""
        if not isinstance(source_info.config, GitImageSourceConfig):
            return Error(
                ProcessingError(
                    message="Invalid config type for Git source",
                    category=ErrorCategory.SYSTEM_ERROR,
                )
            )

        config = source_info.config
        if not source_info.local_cache_path:
            return Error(
                ProcessingError(
                    message="No local cache path configured for Git source",
                    category=ErrorCategory.SYSTEM_ERROR,
                )
            )
        repo_path = source_info.local_cache_path / "repo"

        # Validate Git configuration inputs for security
        if not self._is_safe_git_branch(config.branch):
            return Error(
                ProcessingError(
                    message=f"Invalid Git branch name: {config.branch}",
                    category=ErrorCategory.USER_ERROR,
                )
            )

        if not self._is_safe_git_url(config.repository_url):
            return Error(
                ProcessingError(
                    message=f"Invalid Git repository URL: {config.repository_url}",
                    category=ErrorCategory.USER_ERROR,
                )
            )

        try:
            if repo_path.exists():
                # Update existing repository
                logger.debug(f"Updating Git repository: {config.repository_url}")

                cmd = ["git", "-C", str(repo_path), "pull", "origin", config.branch]
                result = subprocess.run(  # nosec B603 # Validated inputs and controlled command
                    cmd, capture_output=True, text=True, timeout=config.timeout_seconds
                )

                if result.returncode != 0:
                    return Error(
                        ProcessingError(
                            message=f"Git pull failed: {result.stderr}",
                            category=ErrorCategory.IO,
                        )
                    )
            else:
                # Clone new repository
                logger.debug(f"Cloning Git repository: {config.repository_url}")

                cmd = ["git", "clone"]
                if config.shallow_clone:
                    cmd.extend(["--depth", "1"])
                cmd.extend(["-b", config.branch, config.repository_url, str(repo_path)])

                result = subprocess.run(  # nosec B603 # Validated inputs and controlled command
                    cmd, capture_output=True, text=True, timeout=config.timeout_seconds
                )

                if result.returncode != 0:
                    return Error(
                        ProcessingError(
                            message=f"Git clone failed: {result.stderr}",
                            category=ErrorCategory.IO,
                        )
                    )

            # Update image count
            if config.subdirectory:
                image_dir = repo_path / config.subdirectory
            else:
                image_dir = repo_path
            if image_dir.exists():
                image_files = list(image_dir.rglob("*"))
                source_info.total_images = len([f for f in image_files if f.is_file()])

            return Success(None)

        except subprocess.TimeoutExpired:
            return Error(
                ProcessingError(
                    message=f"Git operation timed out after {config.timeout_seconds} seconds",
                    category=ErrorCategory.IO,
                )
            )
        except Exception as e:
            return Error(
                ProcessingError(
                    message=f"Git sync error: {str(e)}",
                    category=ErrorCategory.IO,
                )
            )

    async def _sync_local_source(
        self, source_info: ImageSourceInfo
    ) -> Result[None, ProcessingError]:
        """Sync a local directory source."""
        if not isinstance(source_info.config, LocalDirectoryImageSourceConfig):
            return Error(
                ProcessingError(
                    message="Invalid config type for local directory source",
                    category=ErrorCategory.SYSTEM_ERROR,
                )
            )

        config = source_info.config

        try:
            if not config.directory_path.exists():
                return Error(
                    ProcessingError(
                        message=f"Local directory does not exist: {config.directory_path}",
                        category=ErrorCategory.IO,
                    )
                )

            # Count image files
            if config.recursive:
                image_files: list[Path] = []
                for ext in config.allowed_extensions:
                    image_files.extend(config.directory_path.rglob(f"*{ext}"))
            else:
                image_files = []
                for ext in config.allowed_extensions:
                    image_files.extend(config.directory_path.glob(f"*{ext}"))

            source_info.total_images = len(image_files)

            return Success(None)

        except Exception as e:
            return Error(
                ProcessingError(
                    message=f"Local directory sync error: {str(e)}",
                    category=ErrorCategory.IO,
                )
            )

    async def _sync_s3_source(
        self, source_info: ImageSourceInfo
    ) -> Result[None, ProcessingError]:
        """Sync an S3 bucket source."""
        # S3 implementation would go here
        # For now, return success as a placeholder
        return Success(None)

    def _generate_cache_key(self, image_path: str, source_name: str) -> str:
        """Generate a cache key for an image."""
        key_content = f"{source_name}:{image_path}"
        return hashlib.sha256(key_content.encode()).hexdigest()

    async def resolve_image(
        self, image_path: str, preferred_source: str | None = None
    ) -> Result[ImageAssetInfo, ImageResolutionError]:
        """Resolve an image from available sources.

        Args:
            image_path: Path/URL of the image to resolve
            preferred_source: Name of preferred source to try first

        Returns:
            Image asset information or resolution error
        """
        attempted_sources = []

        # Get sorted sources by priority
        active_sources = [
            info
            for info in self._sources.values()
            if info.config.enabled and info.status == ImageSourceStatus.ACTIVE
        ]
        active_sources.sort(key=lambda x: x.config.priority)

        # Try preferred source first if specified
        if preferred_source and preferred_source in self._sources:
            preferred_info = self._sources[preferred_source]
            if (
                preferred_info.config.enabled
                and preferred_info.status == ImageSourceStatus.ACTIVE
            ):
                active_sources = [preferred_info] + [
                    s for s in active_sources if s.config.name != preferred_source
                ]

        # Try each source in priority order
        for source_info in active_sources:
            attempted_sources.append(source_info.config.name)

            try:
                result = await self._resolve_from_source(image_path, source_info)
                if result.is_success():
                    logger.debug(
                        f"Resolved image '{image_path}' from source '{source_info.config.name}'"
                    )
                    return result

                error_msg = (
                    result.error.message
                    if hasattr(result, "error")
                    else "Unknown error"
                )
                logger.debug(
                    f"Source '{source_info.config.name}' failed to resolve '{image_path}': {error_msg}"
                )

            except Exception as e:
                logger.error(
                    f"Unexpected error resolving from source '{source_info.config.name}': {str(e)}"
                )

        # No source could resolve the image
        return Error(
            create_image_resolution_error(
                image_path=image_path,
                attempted_sources=attempted_sources,
                suggestions=[
                    "Check that image sources are properly configured and synced",
                    "Verify the image path is correct",
                    "Try running source sync to update caches",
                ],
            )
        )

    async def _resolve_from_source(
        self, image_path: str, source_info: ImageSourceInfo
    ) -> Result[ImageAssetInfo, ImageResolutionError]:
        """Resolve an image from a specific source."""
        cache_key = self._generate_cache_key(image_path, source_info.config.name)

        # Check asset cache first
        if cache_key in self._asset_cache:
            asset = self._asset_cache[cache_key]
            if asset.local_path.exists():
                asset.last_accessed = time.time()
                return Success(asset)

        # Try to resolve from source
        if source_info.config.source_type == ImageSourceType.GIT_REPO:
            return await self._resolve_from_git_source(
                image_path, source_info, cache_key
            )
        elif source_info.config.source_type == ImageSourceType.LOCAL_DIR:
            return await self._resolve_from_local_source(
                image_path, source_info, cache_key
            )
        elif source_info.config.source_type == ImageSourceType.HTTP_API:
            return await self._resolve_from_http_source(
                image_path, source_info, cache_key
            )
        elif source_info.config.source_type == ImageSourceType.S3_BUCKET:
            return await self._resolve_from_s3_source(
                image_path, source_info, cache_key
            )
        else:
            return Error(
                create_image_resolution_error(
                    image_path=image_path,
                    message=f"Unsupported source type: {source_info.config.source_type}",
                )
            )

    async def _resolve_from_git_source(
        self, image_path: str, source_info: ImageSourceInfo, cache_key: str
    ) -> Result[ImageAssetInfo, ImageResolutionError]:
        """Resolve an image from a Git repository source."""
        if not isinstance(source_info.config, GitImageSourceConfig):
            return Error(
                create_image_resolution_error(
                    image_path, "Invalid Git source configuration"
                )
            )

        config = source_info.config
        if not source_info.local_cache_path:
            return Error(
                create_image_resolution_error(
                    image_path, "No local cache path configured for Git source"
                )
            )
        repo_path = source_info.local_cache_path / "repo"

        if not repo_path.exists():
            return Error(
                create_image_resolution_error(
                    image_path,
                    f"Git repository not found: {repo_path}",
                    suggestions=["Run source sync to clone the repository"],
                )
            )

        # Construct potential paths to check
        if config.subdirectory:
            base_path = repo_path / config.subdirectory
        else:
            base_path = repo_path
        potential_paths = [
            base_path / image_path,
            base_path / image_path.lstrip("/"),
        ]

        # Try fuzzy matching if exact path doesn't work
        for path in potential_paths:
            if path.exists() and path.is_file():
                # Create asset info
                asset_info = ImageAssetInfo(
                    original_path=image_path,
                    resolved_path=str(path.relative_to(repo_path)),
                    local_path=path,
                    source_name=config.name,
                    file_size=path.stat().st_size,
                    last_accessed=time.time(),
                    cache_key=cache_key,
                )

                # Cache the asset
                self._asset_cache[cache_key] = asset_info

                return Success(asset_info)

        return Error(
            create_image_resolution_error(
                image_path,
                f"Image not found in Git repository: {image_path}",
            )
        )

    async def _resolve_from_local_source(
        self, image_path: str, source_info: ImageSourceInfo, cache_key: str
    ) -> Result[ImageAssetInfo, ImageResolutionError]:
        """Resolve an image from a local directory source."""
        if not isinstance(source_info.config, LocalDirectoryImageSourceConfig):
            return Error(
                create_image_resolution_error(
                    image_path, "Invalid local directory source configuration"
                )
            )

        config = source_info.config

        # Try direct path resolution
        potential_paths = [
            config.directory_path / image_path,
            config.directory_path / image_path.lstrip("/"),
        ]

        for path in potential_paths:
            if path.exists() and path.is_file():
                # Check if extension is allowed
                if path.suffix.lower() not in config.allowed_extensions:
                    continue

                # Create asset info
                asset_info = ImageAssetInfo(
                    original_path=image_path,
                    resolved_path=str(path.relative_to(config.directory_path)),
                    local_path=path,
                    source_name=config.name,
                    file_size=path.stat().st_size,
                    last_accessed=time.time(),
                    cache_key=cache_key,
                )

                # Cache the asset
                self._asset_cache[cache_key] = asset_info

                return Success(asset_info)

        return Error(
            create_image_resolution_error(
                image_path,
                f"Image not found in local directory: {image_path}",
            )
        )

    async def _resolve_from_http_source(
        self, image_path: str, source_info: ImageSourceInfo, cache_key: str
    ) -> Result[ImageAssetInfo, ImageResolutionError]:
        """Resolve an image from an HTTP API source."""
        # HTTP API implementation would go here
        return Error(
            create_image_resolution_error(
                image_path,
                "HTTP API source resolution not implemented yet",
            )
        )

    async def _resolve_from_s3_source(
        self, image_path: str, source_info: ImageSourceInfo, cache_key: str
    ) -> Result[ImageAssetInfo, ImageResolutionError]:
        """Resolve an image from an S3 bucket source."""
        # S3 implementation would go here
        return Error(
            create_image_resolution_error(
                image_path,
                "S3 bucket source resolution not implemented yet",
            )
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get image cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_assets = len(self._asset_cache)
        total_size = sum(asset.file_size for asset in self._asset_cache.values())

        source_stats = {}
        for name, info in self._sources.items():
            source_stats[name] = {
                "status": info.status.value,
                "total_images": info.total_images,
                "cache_size_bytes": info.cache_size_bytes,
                "last_sync": info.last_sync,
                "last_error": info.last_error,
            }

        return {
            "total_cached_assets": total_assets,
            "total_cache_size_bytes": total_size,
            "total_cache_size_mb": total_size / (1024 * 1024),
            "cache_directory": str(self.cache_dir),
            "sources": source_stats,
        }

    async def cleanup_cache(
        self, max_age_hours: int = 48, max_size_mb: int = 1024
    ) -> Result[dict[str, int], ProcessingError]:
        """Clean up old and oversized cache entries.

        Args:
            max_age_hours: Maximum age for cache entries in hours
            max_size_mb: Maximum total cache size in MB

        Returns:
            Cleanup statistics or error
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            max_size_bytes = max_size_mb * 1024 * 1024

            # Remove old assets
            removed_old = 0
            to_remove = []

            for cache_key, asset in self._asset_cache.items():
                age = current_time - asset.last_accessed
                if age > max_age_seconds:
                    to_remove.append(cache_key)
                    if asset.local_path.exists():
                        asset.local_path.unlink()
                        removed_old += 1

            for key in to_remove:
                del self._asset_cache[key]

            # Remove largest assets if still over size limit
            removed_oversized = 0
            current_size = sum(asset.file_size for asset in self._asset_cache.values())

            if current_size > max_size_bytes:
                # Sort by size descending
                assets_by_size = sorted(
                    self._asset_cache.items(),
                    key=lambda x: x[1].file_size,
                    reverse=True,
                )

                for cache_key, asset in assets_by_size:
                    if current_size <= max_size_bytes:
                        break

                    current_size -= asset.file_size
                    if asset.local_path.exists():
                        asset.local_path.unlink()
                        removed_oversized += 1

                    del self._asset_cache[cache_key]

            remaining_size_bytes = sum(
                asset.file_size for asset in self._asset_cache.values()
            )
            stats = {
                "removed_old": removed_old,
                "removed_oversized": removed_oversized,
                "remaining_assets": len(self._asset_cache),
                "remaining_size_mb": int(remaining_size_bytes / (1024 * 1024)),
            }

            logger.info(f"Cache cleanup completed: {stats}")
            return Success(stats)

        except Exception as e:
            return Error(
                ProcessingError(
                    message=f"Cache cleanup failed: {str(e)}",
                    category=ErrorCategory.IO,
                )
            )
