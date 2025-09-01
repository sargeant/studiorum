"""Unified caching system for improved performance, using diskcache."""

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

from diskcache import Cache

# Default cache directory and settings
CACHE_DIR = Path.cwd() / ".cache"
CACHE_SETTINGS: dict[str, Any] = {
    "size_limit": 100 * 1024 * 1024,  # 100MB
    "eviction_policy": "least-recently-used",
    "timeout": 1,  # Timeout for db connection
}


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
            CACHE_DIR.mkdir(exist_ok=True)
            cls._instance = Cache(str(CACHE_DIR), **CACHE_SETTINGS)
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


def cached(
    key_func: Callable[..., str] | None = None,
    ttl: timedelta | None = None,
) -> Callable[..., Any]:
    """
    Decorator for caching function results using diskcache.

    Args:
        key_func: Function to generate a cache key from the decorated
                  function's arguments. If None, a default key is generated.
        ttl: Cache time-to-live. Converts timedelta to seconds for diskcache.

    Example:
        @cached(lambda name, source: f"spell:{name}:{source}", ttl=timedelta(hours=1))
        def find_spell(name, source):
            # Expensive operation
            return "some_spell_data"
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache = get_cache()

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key from function name and args
                key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # Convert timedelta to seconds for diskcache's 'expire'
            expire = ttl.total_seconds() if ttl else None

            # Use the memoize pattern manually
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(key, result, expire=expire)
            return result

        return wrapper

    return decorator
