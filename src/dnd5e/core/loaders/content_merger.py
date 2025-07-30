"""Content merger for combining metadata and content files."""

import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from ..config.settings import get_settings
from ..models.content import ContentType

logger = logging.getLogger(__name__)


class ContentMerger:
    """Merges metadata and content files for adventures/books.

    This class implements the 5etools dual-file architecture where:
    - Metadata files (adventures.json, books.json) provide structure and catalog info
    - Content files (adventure-*.json, book-*.json) provide actual entry data
    - Merging combines metadata structure with content data at resolution time
    """

    def __init__(self, source_manager: Any, max_cache_size: int = 100) -> None:
        """Initialize ContentMerger with source manager.

        Args:
            source_manager: SourceManager instance for file discovery
            max_cache_size: Maximum number of items to cache (LRU eviction)
        """
        self.source_manager = source_manager
        self.settings = get_settings()
        self.max_cache_size = max_cache_size

        # LRU cache using OrderedDict
        self._content_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        # Cache metadata: {cache_key: {"mtime": float, "file_path": Path, "access_time": float}}
        self._cache_metadata: dict[str, dict[str, Any]] = {}
        # Cache statistics
        self._cache_stats = {"hits": 0, "misses": 0, "evictions": 0, "invalidations": 0}

    def load_content_file(
        self, content_type: ContentType, content_id: str
    ) -> dict[str, Any] | None:
        """Load content file by ID pattern with enhanced caching.

        Args:
            content_type: Type of content (ADVENTURE or BOOK)
            content_id: Content identifier (e.g., "CoS", "DrDe-ACfaS")

        Returns:
            Parsed content file data or None if not found

        Raises:
            ValueError: If content_type is not supported for dual-file pattern
        """
        if content_type not in [ContentType.ADVENTURE, ContentType.BOOK]:
            raise ValueError(
                f"Content type {content_type} not supported for dual-file loading"
            )

        # Skip caching if disabled
        if not self.settings.enable_caching:
            return self._load_content_from_disk(content_type, content_id)

        # Generate cache key
        cache_key = f"{content_type.value}:{content_id}"

        # Check if cached content is still valid
        if self._is_cache_valid(cache_key):
            # Move to end (most recently used) for LRU
            content_data = self._content_cache.pop(cache_key)
            self._content_cache[cache_key] = content_data
            self._cache_metadata[cache_key]["access_time"] = time.time()
            self._cache_stats["hits"] += 1
            logger.debug(f"Cache hit for {cache_key}")
            return content_data

        # Load content from disk
        self._cache_stats["misses"] += 1
        content_data = self._load_content_from_disk(content_type, content_id)  # type: ignore[assignment]

        if content_data is not None:
            # Find the actual file path for cache metadata
            normalized_filename = self._normalize_id_to_filename(
                content_type, content_id
            )
            content_files = self.source_manager.get_content_files().get(
                content_type, []
            )
            matching_file = None
            for file_path in content_files:
                if file_path.name.lower() == normalized_filename.lower():
                    matching_file = file_path
                    break

            if matching_file:
                # Store in cache with metadata
                self._store_in_cache(cache_key, content_data, matching_file)
                logger.debug(f"Cached content for {cache_key}")

        return content_data

    def _normalize_id_to_filename(
        self, content_type: ContentType, content_id: str
    ) -> str:
        """Normalize content ID to expected filename pattern.

        Args:
            content_type: Type of content (ADVENTURE or BOOK)
            content_id: Content identifier from metadata

        Returns:
            Expected filename (e.g., "adventure-cos.json", "book-phb.json")
        """
        # Convert ID to lowercase and handle special characters
        normalized_id = content_id.lower()

        # Remove or replace special characters that appear in 5etools IDs
        # Examples: "DrDe-ACfaS" -> "drde-acfas", "CoS" -> "cos"
        normalized_id = normalized_id.replace("-", "-")  # Keep hyphens as-is

        # Build filename based on content type
        if content_type == ContentType.ADVENTURE:
            return f"adventure-{normalized_id}.json"
        elif content_type == ContentType.BOOK:
            return f"book-{normalized_id}.json"
        else:
            raise ValueError(
                f"Unsupported content type for filename normalization: {content_type}"
            )

    def merge_metadata_content(
        self, metadata_entry: dict[str, Any], content_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Merge metadata structure with content data.

        Args:
            metadata_entry: Adventure/book metadata entry from metadata file
            content_data: Parsed content data from content file (optional)

        Returns:
            Unified content object with metadata structure and content data
        """
        if content_data is None:
            # If no content data available, return metadata with empty content entries
            logger.warning(
                "No content data provided for merging, returning metadata-only"
            )
            return self._create_metadata_only_result(metadata_entry)

        # Extract content sections from data array
        content_sections = content_data.get("data", [])
        if not isinstance(content_sections, list):
            logger.error("Content data format invalid - 'data' field is not a list")
            return self._create_metadata_only_result(metadata_entry)

        # Start with metadata as base structure
        merged_result = dict(metadata_entry)

        # Create merged contents array that combines metadata structure with content data
        metadata_contents = metadata_entry.get("contents", [])
        merged_contents = []

        # Create mapping of content sections by name for lookup
        content_by_name = {}
        for section in content_sections:
            if isinstance(section, dict) and section.get("type") == "section":
                section_name = section.get("name", "")
                content_by_name[section_name] = section

        # Process each metadata content entry and merge with actual content
        for metadata_content in metadata_contents:
            if not isinstance(metadata_content, dict):
                continue

            content_name = metadata_content.get("name", "")

            # Look for matching content section
            matching_content = content_by_name.get(content_name)

            if matching_content:
                # Merge metadata structure with content entries
                merged_content = dict(metadata_content)
                merged_content["entries"] = matching_content.get("entries", [])

                # Add content-specific fields if present
                if "id" in matching_content:
                    merged_content["ordinal"] = {
                        "type": "section",
                        "identifier": matching_content["id"],
                    }

                merged_contents.append(merged_content)
                logger.debug(f"Merged content for section: {content_name}")
            else:
                # Keep metadata structure but with empty entries
                empty_content = dict(metadata_content)
                empty_content["entries"] = []
                merged_contents.append(empty_content)
                logger.warning(f"No content found for metadata section: {content_name}")

        # Add any content sections that don't have corresponding metadata
        for section_name, content_section in content_by_name.items():
            # Check if this section was already processed
            if not any(mc.get("name") == section_name for mc in merged_contents):
                content_entry = {
                    "name": section_name,
                    "entries": content_section.get("entries", []),
                }
                if "id" in content_section:
                    content_entry["ordinal"] = {
                        "type": "section",
                        "identifier": content_section["id"],
                    }
                merged_contents.append(content_entry)
                logger.warning(
                    f"Added content section without metadata: {section_name}"
                )

        # Update the merged result with the combined contents
        merged_result["contents"] = merged_contents

        logger.debug(
            f"Successfully merged metadata and content: {len(merged_contents)} sections"
        )
        return merged_result

    def _create_metadata_only_result(
        self, metadata_entry: dict[str, Any]
    ) -> dict[str, Any]:
        """Create result with metadata structure but empty content entries.

        Args:
            metadata_entry: Adventure/book metadata entry

        Returns:
            Metadata structure with empty content entries
        """
        result = dict(metadata_entry)

        # Ensure contents array exists with empty entries
        metadata_contents = metadata_entry.get("contents", [])
        empty_contents = []

        for content in metadata_contents:
            if isinstance(content, dict):
                empty_content = dict(content)
                empty_content["entries"] = []
                empty_contents.append(empty_content)

        result["contents"] = empty_contents
        return result

    def _load_content_from_disk(
        self, content_type: ContentType, content_id: str
    ) -> dict[str, Any] | None:
        """Load content file from disk without caching.

        Args:
            content_type: Type of content (ADVENTURE or BOOK)
            content_id: Content identifier

        Returns:
            Parsed content file data or None if not found
        """
        # Normalize ID to filename pattern
        normalized_filename = self._normalize_id_to_filename(content_type, content_id)

        # Find content file
        content_files = self.source_manager.get_content_files()
        content_type_files = content_files.get(content_type, [])

        matching_file = None
        for file_path in content_type_files:
            if file_path.name.lower() == normalized_filename.lower():
                matching_file = file_path
                break

        if not matching_file:
            logger.warning(
                f"Content file not found for {content_type.value} ID '{content_id}' (expected: {normalized_filename})"
            )
            return None

        # Load and parse content file
        try:
            with open(matching_file, "r", encoding="utf-8") as f:
                content_data = json.load(f)

            logger.debug(f"Loaded content file: {matching_file}")
            return content_data  # type: ignore[no-any-return]

        except (OSError, FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading content file {matching_file}: {e}")
            return None

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached content is still valid.

        Args:
            cache_key: Cache key to check

        Returns:
            True if cache entry is valid, False otherwise
        """
        if cache_key not in self._content_cache:
            return False

        cache_meta = self._cache_metadata.get(cache_key)
        if not cache_meta:
            # No metadata, assume invalid
            return False

        # Check TTL expiration
        if time.time() - cache_meta["access_time"] > self.settings.cache_ttl:
            self._invalidate_cache_entry(cache_key)
            return False

        # Check file modification time
        try:
            file_path = cache_meta["file_path"]
            current_mtime = file_path.stat().st_mtime
            if current_mtime != cache_meta["mtime"]:
                self._invalidate_cache_entry(cache_key)
                return False
        except (OSError, FileNotFoundError):
            # File doesn't exist anymore, invalidate
            self._invalidate_cache_entry(cache_key)
            return False

        return True

    def _store_in_cache(
        self, cache_key: str, content_data: dict[str, Any], file_path: Path
    ) -> None:
        """Store content in cache with metadata.

        Args:
            cache_key: Cache key
            content_data: Content data to cache
            file_path: Path to the source file
        """
        # Ensure cache size limit
        while len(self._content_cache) >= self.max_cache_size:
            # Remove least recently used item (first item in OrderedDict)
            oldest_key = next(iter(self._content_cache))
            self._content_cache.pop(oldest_key)
            self._cache_metadata.pop(oldest_key, None)
            self._cache_stats["evictions"] += 1
            logger.debug(f"Evicted cache entry: {oldest_key}")

        # Store content and metadata
        self._content_cache[cache_key] = content_data
        self._cache_metadata[cache_key] = {
            "mtime": file_path.stat().st_mtime,
            "file_path": file_path,
            "access_time": time.time(),
        }

    def _invalidate_cache_entry(self, cache_key: str) -> None:
        """Invalidate a specific cache entry.

        Args:
            cache_key: Cache key to invalidate
        """
        self._content_cache.pop(cache_key, None)
        self._cache_metadata.pop(cache_key, None)
        self._cache_stats["invalidations"] += 1
        logger.debug(f"Invalidated cache entry: {cache_key}")

    def clear_cache(self) -> None:
        """Clear the content cache."""
        self._content_cache.clear()
        self._cache_metadata.clear()
        logger.debug("Content cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics including hit/miss ratios
        """
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (
            self._cache_stats["hits"] / total_requests if total_requests > 0 else 0.0
        )

        return {
            "cached_items": len(self._content_cache),
            "cache_keys": list(self._content_cache.keys()),
            "memory_usage_estimate": sum(
                len(str(content)) for content in self._content_cache.values()
            ),
            "max_cache_size": self.max_cache_size,
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "evictions": self._cache_stats["evictions"],
            "invalidations": self._cache_stats["invalidations"],
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_enabled": self.settings.enable_caching,
            "cache_ttl": self.settings.cache_ttl,
        }
