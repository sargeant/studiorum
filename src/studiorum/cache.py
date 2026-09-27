"""Unified caching system for improved performance, using diskcache."""

import os
from pathlib import Path
from typing import Any

from diskcache import Cache
from platformdirs import user_cache_dir

CACHE_SETTINGS: dict[str, Any] = {
    "size_limit": 100 * 1024 * 1024,  # 100MB
    "eviction_policy": "least-recently-used",
    "timeout": 1,  # Timeout for db connection
}


def cache_dir() -> Path:
    """Return $STUDIORUM_CACHE_DIR if set, else the platform's user cache directory."""
    return Path(os.environ.get("STUDIORUM_CACHE_DIR") or user_cache_dir("studiorum"))


class CacheManager:
    """
    A wrapper around diskcache.Cache to provide a unified interface.

    This class manages a singleton cache instance and provides methods
    for interacting with it, including a decorator for caching function calls.
    """

    _instance: Cache | None = None

    @classmethod
    def get_instance(cls) -> Cache:
        """Get the singleton cache instance, creating it if necessary."""
        if cls._instance is None:
            directory = cache_dir()
            directory.mkdir(parents=True, exist_ok=True)
            cls._instance = Cache(str(directory), **CACHE_SETTINGS)
        return cls._instance

    @classmethod
    def clear(cls) -> None:
        """Clear the entire cache."""
        cache = cls.get_instance()
        cache.clear()

    @classmethod
    def reset(cls) -> None:
        """Reset the cache instance completely (for testing)."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None

    @classmethod
    def get_stats(cls) -> dict[str, Any]:
        """Get cache statistics."""
        cache = cls.get_instance()
        return {
            "cache_dir": cache.directory,
            "total_entries": len(cache),
            "total_size_mb": cache.volume() / (1024 * 1024),
            "max_size_mb": cache.size_limit / (1024 * 1024),
        }


def get_cache() -> Cache:
    """Get the global cache instance."""
    return CacheManager.get_instance()
