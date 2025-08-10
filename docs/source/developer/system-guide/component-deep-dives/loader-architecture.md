# Loader Architecture Implementation Guide

This guide provides comprehensive information for implementing and extending the
sophisticated dual-file loader architecture that forms the foundation of the
5e2pdf system.

## Overview

The loader architecture implements a 5etools-compatible dual-file system that
separates metadata from content files, enabling efficient on-demand loading
with intelligent caching and runtime merging.

### Key Benefits

- **Performance**: On-demand loading reduces memory usage and startup time
- **Scalability**: LRU caching with TTL handles large datasets efficiently
- **Compatibility**: Works seamlessly with 5etools data format
- **Reliability**: Graceful fallback when content files are unavailable

## Architecture Components

### Registry-Based Content Type Detection

**Location**: `src/dnd5e/core/loaders/configurable_source_manager.py`

The loader architecture uses a dynamic registry system for content type detection:

#### File Pattern Matching

```python
from dnd5e.core.registry import initialize_content_types
from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager

# Initialize content types to load file patterns
initialize_content_types()

# Source manager automatically detects content types by file patterns
manager = ConfigurableSourceManager()
file_paths = manager.get_data_paths()

# Each content type registered with @content_type decorator
# contributes its file patterns automatically
for content_type, paths in file_paths.items():
    print(f"{content_type}: {len(paths)} files")
```

#### Dynamic Content Loading

```python
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType

# Omnidexer uses registry to load all registered content types
omnidexer = Omnidexer()
stats = omnidexer.load_all_data()

# Registry provides available content types dynamically
available_types = omnidexer.get_all_content_types()
print(f"Loaded types: {[ct.value for ct in available_types]}")
```

### ContentMerger

**Location**: `src/dnd5e/core/loaders/content_merger.py`

The ContentMerger is the heart of the dual-file architecture, responsible for:

- Loading and merging metadata with content files
- Implementing LRU cache with TTL and file modification tracking
- Supporting three input formats: unified, metadata-only, content-only
- Providing graceful fallback mechanisms

#### Core Implementation

```python
from dnd5e.core.loaders.content_merger import ContentMerger

# Initialize with cache configuration
merger = ContentMerger(
    cache_size=100,
    ttl_seconds=3600,
    enable_file_tracking=True
)

# Load and merge content
merged_data = merger.get_merged_content(
    metadata_path="adventures.json",
    content_id="cos",
    content_directory="adventure-content/"
)
```

#### Key Features

```python
class ContentMerger:
    """Advanced content merging with caching and file tracking."""

    def get_merged_content(
        self,
        metadata_path: Path,
        content_id: str,
        content_directory: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Merge metadata with content file on-demand."""

    def invalidate_cache(self, content_id: str) -> bool:
        """Invalidate specific cache entry."""

    def get_cache_statistics(self) -> CacheStatistics:
        """Get comprehensive cache performance metrics."""
```

### Omnidexer

**Location**: `src/dnd5e/core/loaders/omnidexer.py`

The Omnidexer provides comprehensive content indexing with deep search capabilities:

#### Implementation Example

```python
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.registry import initialize_content_types

# Initialize content types before using
initialize_content_types()

# Initialize omnidexer
indexer = Omnidexer(enable_deep_indexing=True)

# Load all data with registry-driven content type detection
stats = indexer.load_all_data()

# Query specific content types
adventures = indexer.get_all_by_type(ContentType.ADVENTURE)
spells = indexer.get_all_by_type(ContentType.SPELL)

# Find specific content
fireball = indexer.find(ContentType.SPELL, "Fireball", "PHB")
```

#### Key Capabilities

- **SHA256 content hashing** for change detection
- **Deep indexing** via `DeepIndexable` protocol
- **Synchronous loading** with efficient file handling
- **Performance monitoring** with detailed metrics

### ContentResolver

**Location**: `src/dnd5e/core/resolvers/content_resolver.py`

The ContentResolver provides intelligent content resolution with fuzzy matching:

#### Usage Pattern

```python
from dnd5e.core.resolvers.content_resolver import ContentResolver

# Initialize resolver with merger
resolver = ContentResolver(
    content_merger=merger,
    fuzzy_threshold=0.6
)

# Resolve content with fuzzy matching
adventure = resolver.resolve_adventure("CoS")  # "Curse of Strahd"
```

#### Multi-Tier Resolution

1. **Exact Match**: Direct ID or name matching
2. **Fuzzy Match**: difflib-based similarity scoring
3. **Suggestions**: Alternative matches for failed resolution

## Implementation Patterns

### Protocol-Based Design

The architecture uses Python protocols for loose coupling:

```python
from typing import Protocol

class ContentLoader(Protocol):
    """Protocol for content loading implementations."""

    def load_content(
        self,
        identifier: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Load content by identifier."""
        ...

class DeepIndexable(Protocol):
    """Protocol for deep indexing support."""

    def get_deep_index_entries(self) -> List[IndexEntry]:
        """Return entries for deep indexing."""
        ...
```

### Caching Strategy

#### LRU Cache Implementation

```python
from collections import OrderedDict
from typing import Optional, Dict, Any
import time

class LRUCache:
    """LRU cache with TTL and file modification tracking."""

    def __init__(self, max_size: int, ttl_seconds: int):
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.file_times: Dict[str, float] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, key: str, file_path: Optional[Path] = None) -> Any:
        """Get item with TTL and file modification checking."""
        if not self._is_valid(key, file_path):
            return None

        # Move to end (most recently used)
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def _is_valid(self, key: str, file_path: Optional[Path]) -> bool:
        """Check if cache entry is still valid."""
        if key not in self.cache:
            return False

        # Check TTL
        if time.time() - self.timestamps[key] > self.ttl_seconds:
            self._evict(key)
            return False

        # Check file modification time
        if file_path and self._file_modified(key, file_path):
            self._evict(key)
            return False

        return True
```

### Error Handling Patterns

#### Graceful Degradation

```python
def load_with_fallback(
    self,
    metadata_path: Path,
    content_id: str
) -> Dict[str, Any]:
    """Load content with graceful fallback to metadata-only."""

    try:
        # Try to load merged content
        return self.get_merged_content(metadata_path, content_id)
    except ContentNotFoundError:
        # Fall back to metadata-only
        logger.warning(f"Content file not found for {content_id}, using metadata only")
        return self.get_metadata_only(metadata_path, content_id)
    except Exception as e:
        # Log error and provide minimal fallback
        logger.error(f"Error loading content for {content_id}: {e}")
        return {"id": content_id, "error": str(e)}
```

## Testing Strategies

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, mock_open
from dnd5e.core.loaders.content_merger import ContentMerger

class TestContentMerger:
    """Comprehensive test suite for ContentMerger."""

    def test_successful_merge(self):
        """Test successful metadata-content merging."""
        merger = ContentMerger()

        with patch('builtins.open', mock_open(
            read_data='{"adventures": [{"id": "cos"}]}'
        )):
            result = merger.get_merged_content(
                Path("adventures.json"),
                "cos"
            )

            assert result["id"] == "cos"
            assert merger.get_cache_statistics().hits == 0

    def test_cache_eviction(self):
        """Test LRU cache eviction behavior."""
        merger = ContentMerger(cache_size=2)

        # Fill cache beyond capacity
        merger._cache_set("key1", {"data": 1})
        merger._cache_set("key2", {"data": 2})
        merger._cache_set("key3", {"data": 3})  # Should evict key1

        assert "key1" not in merger.cache
        assert merger.get_cache_statistics().evictions == 1
```

### Integration Testing

```python
@pytest.mark.integration
def test_end_to_end_loading():
    """Test complete loading workflow."""

    # Setup test data
    test_data_dir = Path("tests/fixtures/5etools-data")

    # Initialize components
    merger = ContentMerger()
    indexer = Omnidexer()
    resolver = ContentResolver(merger)

    # Initialize content types
    from dnd5e.core.registry import initialize_content_types
    initialize_content_types()

    # Load all content with automatic type detection
    stats = indexer.load_all_data()

    # Find specific adventure using content type system
    cos = indexer.find(ContentType.ADVENTURE, "Curse of Strahd", "CoS")

    # Verify content is merged
    assert cos.has_content()
    assert len(cos.chapters) > 0
    assert cos.source == "CoS"
```

### Performance Testing

```python
@pytest.mark.performance
def test_cache_performance():
    """Benchmark cache performance under load."""

    merger = ContentMerger(cache_size=1000)

    # Warm up cache
    for i in range(500):
        merger._cache_set(f"key{i}", {"data": i})

    # Benchmark access patterns
    start_time = time.time()

    for _ in range(10000):
        key = f"key{random.randint(0, 499)}"
        merger._cache_get(key)

    duration = time.time() - start_time

    # Performance assertions
    assert duration < 1.0  # Should complete in under 1 second
    assert merger.get_cache_statistics().hit_rate > 0.8
```

## Extension Points

### Custom Content Loaders

```python
from dnd5e.core.loaders.base import ContentLoader

class CustomContentLoader(ContentLoader):
    """Custom loader for specialized content formats."""

    def load_content(
        self,
        identifier: str,
        source_path: Path,
        **kwargs
    ) -> Dict[str, Any]:
        """Load content from custom format."""

        # Custom loading logic
        with open(source_path) as f:
            raw_data = f.read()

        # Transform to standard format
        return self._transform_format(raw_data)

    def _transform_format(self, raw_data: str) -> Dict[str, Any]:
        """Transform custom format to standard structure."""
        # Implementation specific to format
        pass
```

### Cache Backend Extensions

```python
from dnd5e.core.loaders.cache import CacheBackend

class RedisCache(CacheBackend):
    """Redis-based cache backend for distributed systems."""

    def __init__(self, redis_url: str):
        import redis
        self.redis = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        """Get item from Redis cache."""
        data = self.redis.get(key)
        return pickle.loads(data) if data else None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set item in Redis cache with TTL."""
        self.redis.setex(key, ttl, pickle.dumps(value))
```

## Performance Optimization

### Memory Usage

- **Lazy loading**: Only load content when specifically requested
- **Cache eviction**: LRU policy prevents unbounded memory growth
- **Weak references**: Use weak references for large objects when possible

### I/O Optimization

- **Efficient file operations**: Optimized file reading and writing patterns
- **Batch operations**: Load multiple items in single operations when possible
- **Resource management**: Proper file handle management and cleanup

### Profiling and Monitoring

```python
import cProfile
from dnd5e.core.loaders.content_merger import ContentMerger

def profile_loading_performance():
    """Profile loading performance for optimization."""

    profiler = cProfile.Profile()
    profiler.enable()

    # Execute loading operations
    merger = ContentMerger()
    # ... perform operations

    profiler.disable()
    profiler.dump_stats('loading_profile.prof')

    # Analyze with snakeviz or py-spy
```

## Migration Guide

### Implementation Migration

When implementing new loaders or updating existing ones:

1. **Identify current loading patterns**
2. **Map to dual-file architecture**
3. **Implement ContentMerger integration**
4. **Add caching where beneficial**
5. **Update tests** to reflect new patterns

### Version Compatibility

The loader architecture maintains compatibility with:

- **5etools data format**: Full compatibility with official 5etools JSON
- **Multiple formats**: Graceful handling of different content formats
- **Future extensions**: Protocol-based design enables easy extension

## Troubleshooting

### Common Issues

**Cache misses**:

- Verify file modification times are correct
- Check TTL configuration
- Monitor cache statistics for patterns

**Memory usage**:

- Adjust cache size based on available memory
- Use weak references for large objects
- Monitor with memory profiling tools

**Loading errors**:

- Check file permissions and paths
- Verify JSON format validity
- Enable debug logging for detailed error information

**Performance issues**:

- Profile with cProfile or py-spy
- Check I/O patterns and file handling efficiency
- Monitor cache hit rates

For additional implementation details, see the [API Documentation](../../api-reference/index.md)
and [Architecture Overview](../architecture-overview.md).
