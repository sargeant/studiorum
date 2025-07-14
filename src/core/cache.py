"""Caching system for improved performance."""

import hashlib
import json
import logging
import pickle
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Simple disk-based cache manager for expensive operations.

    Provides caching for omnidexer data loading, rendered content,
    and other expensive computations to improve performance.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files. Defaults to .cache
        """
        self.cache_dir = cache_dir or Path.cwd() / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()

        # Cache settings
        self.default_ttl = timedelta(hours=24)  # 24 hour default TTL
        self.max_cache_size = 100 * 1024 * 1024  # 100MB max cache

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Create hash of key for filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for a key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found or expired

        Returns:
            Cached value or default
        """
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)

            if not cache_path.exists() or not meta_path.exists():
                return default

            try:
                # Check metadata
                with open(meta_path) as f:
                    metadata = json.load(f)

                # Check if expired
                created_at = datetime.fromisoformat(metadata["created_at"])
                ttl = timedelta(
                    seconds=metadata.get("ttl", self.default_ttl.total_seconds())
                )

                if datetime.now() > created_at + ttl:
                    # Expired, remove files
                    cache_path.unlink(missing_ok=True)
                    meta_path.unlink(missing_ok=True)
                    return default

                # Load cached data
                with open(cache_path, "rb") as f:
                    return pickle.load(f)

            except (pickle.PickleError, EOFError) as e:
                logger.warning("Cache corruption detected for key '%s': %s", key, e)
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return default
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.debug("Cache file access error for key '%s': %s", key, e)
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return default
            except Exception as e:
                logger.error("Unexpected cache read error for key '%s': %s", key, e)
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return default

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live for cached value
        """
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)

            try:
                # Save data
                with open(cache_path, "wb") as f:
                    pickle.dump(value, f)

                # Save metadata
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "ttl": (ttl or self.default_ttl).total_seconds(),
                    "key": key,
                    "size": cache_path.stat().st_size,
                }

                with open(meta_path, "w") as f:
                    json.dump(metadata, f)

                # Clean up cache if too large
                self._cleanup_if_needed()

            except (pickle.PickleError, OSError, PermissionError) as e:
                logger.warning("Failed to write cache for key '%s': %s", key, e)
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
            except Exception as e:
                logger.error("Unexpected cache write error for key '%s': %s", key, e)
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)

    def cached_call(
        self, key: str, func: Callable, *args, ttl: Optional[timedelta] = None, **kwargs
    ) -> Any:
        """
        Call function with caching.

        Args:
            key: Cache key
            func: Function to call
            *args: Function arguments
            ttl: Cache TTL
            **kwargs: Function keyword arguments

        Returns:
            Function result (cached or fresh)
        """
        # Check cache first
        result = self.get(key)
        if result is not None:
            return result

        # Call function and cache result
        result = func(*args, **kwargs)
        self.set(key, result, ttl)
        return result

    def invalidate(self, key: str) -> None:
        """Remove item from cache."""
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)

            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
            for meta_file in self.cache_dir.glob("*.meta"):
                meta_file.unlink(missing_ok=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            cache_files = list(self.cache_dir.glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "cache_dir": str(self.cache_dir),
                "total_entries": len(cache_files),
                "total_size_mb": total_size / (1024 * 1024),
                "max_size_mb": self.max_cache_size / (1024 * 1024),
            }

    def _cleanup_if_needed(self) -> None:
        """Clean up cache if it exceeds size limit."""
        try:
            # Get all cache files with metadata
            cache_info = []
            for meta_file in self.cache_dir.glob("*.meta"):
                try:
                    with open(meta_file) as f:
                        metadata = json.load(f)

                    cache_file = self.cache_dir / meta_file.name.replace(
                        ".meta", ".cache"
                    )
                    if cache_file.exists():
                        cache_info.append(
                            {
                                "meta_file": meta_file,
                                "cache_file": cache_file,
                                "created_at": datetime.fromisoformat(
                                    metadata["created_at"]
                                ),
                                "size": cache_file.stat().st_size,
                            }
                        )
                except (json.JSONDecodeError, ValueError, KeyError, OSError) as e:
                    logger.debug("Invalid cache metadata file '%s': %s", meta_file, e)
                    meta_file.unlink(missing_ok=True)

            # Check total size
            total_size = sum(info["size"] for info in cache_info)

            if total_size > self.max_cache_size:
                # Remove oldest entries until under limit
                cache_info.sort(key=lambda x: x["created_at"])

                for info in cache_info:
                    info["cache_file"].unlink(missing_ok=True)
                    info["meta_file"].unlink(missing_ok=True)

                    total_size -= info["size"]
                    if total_size <= self.max_cache_size * 0.8:  # Leave some headroom
                        break

        except OSError as e:
            logger.warning("Cache cleanup failed due to file system error: %s", e)
        except Exception as e:
            logger.error("Unexpected error during cache cleanup: %s", e)


# Global cache instance
_cache_manager = None


def get_cache() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(key_func: Optional[Callable] = None, ttl: Optional[timedelta] = None):
    """
    Decorator for caching function results.

    Args:
        key_func: Function to generate cache key from args
        ttl: Cache time to live

    Example:
        @cached(lambda name, source: f"spell:{name}:{source}")
        def find_spell(name, source):
            # expensive operation
            return result
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key from function name and args
                key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            cache = get_cache()
            return cache.cached_call(key, func, *args, ttl=ttl, **kwargs)

        return wrapper

    return decorator
