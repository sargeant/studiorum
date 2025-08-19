# Performance Optimization Guide

This guide covers performance optimization strategies for 5e2pdf, including profiling, caching, memory management, and parallel processing.

## Performance Characteristics

### Current Benchmarks

| Operation | Small (Spell) | Medium (Adventure) | Large (Book) |
|-----------|--------------|-------------------|--------------|
| Load Time | < 0.1s | 2-5s | 10-20s |
| Parse Time | < 0.01s | 0.5-1s | 2-5s |
| Render Time | < 0.1s | 5-10s | 30-60s |
| Memory Usage | ~10MB | ~100MB | ~500MB |
| PDF Compilation | 1-2s | 10-20s | 30-60s |

### Bottlenecks

1. **I/O**: Loading large JSON files from disk
2. **Parsing**: Tag resolution and recursive entry processing
3. **LaTeX Compilation**: External process overhead
4. **Memory**: Large adventures/books in memory

## Profiling Tools

### Using cProfile

```python
# Profile a conversion
python -m cProfile -o profile.stats \
    -m dnd5e.cli convert spell "magic missile" --output test.tex

# Analyze results
python -m pstats profile.stats
>>> sort cumulative
>>> stats 20
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def convert_adventure(name: str):
    omnidexer = Omnidexer()
    omnidexer.load_all_data()  # Memory spike here

    adventure = omnidexer.find_one("adventure", name)
    renderer = LaTeXDocumentRenderer()

    return renderer.render(adventure)  # Another spike

# Run with: python -m memory_profiler script.py
```

### Line Profiling

```python
# Install: pip install line_profiler

@profile
def process_entries(entries, context):
    results = []
    for entry in entries:  # Line-by-line timing
        if isinstance(entry, str):
            result = process_string(entry, context)
        else:
            result = process_typed(entry, context)
        results.append(result)
    return results

# Run with: kernprof -l -v script.py
```

## Caching Strategies

### LRU Cache for Hot Data

```python
from functools import lru_cache

class OptimizedOmnidexer:
    @lru_cache(maxsize=1024)
    def find_by_name(self, content_type: str, name: str):
        """Cache frequently accessed content."""
        return self._do_find(content_type, name)

    @lru_cache(maxsize=256)
    def resolve_source(self, abbreviation: str):
        """Cache source lookups."""
        return self._sources.get(abbreviation)
```

### TTL Cache for Merged Content

```python
from datetime import datetime, timedelta

class ContentCache:
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._timestamps = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key):
        if key in self._cache:
            if datetime.now() - self._timestamps[key] < self._ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key, value):
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
```

### Disk Cache for Compiled LaTeX

```python
import hashlib
from pathlib import Path

class LaTeXCache:
    def __init__(self, cache_dir=".latex_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cached_pdf(self, content_hash: str) -> Optional[Path]:
        pdf_path = self.cache_dir / f"{content_hash}.pdf"
        if pdf_path.exists():
            return pdf_path
        return None

    def cache_pdf(self, content: str, pdf_path: Path):
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        cached_path = self.cache_dir / f"{content_hash}.pdf"
        shutil.copy(pdf_path, cached_path)
        return content_hash
```

## Memory Management

### Lazy Loading

```python
class LazyContent:
    """Load content only when accessed."""

    def __init__(self, loader_func):
        self._loader = loader_func
        self._content = None

    @property
    def content(self):
        if self._content is None:
            self._content = self._loader()
        return self._content

    def unload(self):
        """Free memory when done."""
        self._content = None

# Usage
adventure = LazyContent(
    lambda: omnidexer.load_adventure("LMoP")
)
# Content not loaded yet
print(adventure.content.name)  # Loads here
adventure.unload()  # Free memory
```

### Streaming Processing

```python
import ijson

def stream_process_entries(filepath: Path):
    """Process large JSON files without loading entirely."""
    with open(filepath, 'rb') as f:
        # Parse JSON incrementally
        parser = ijson.items(f, 'entries.item')

        for entry in parser:
            # Process one entry at a time
            result = process_entry(entry)
            yield result

            # Explicit garbage collection for large entries
            if sys.getsizeof(entry) > 1_000_000:
                gc.collect()
```

### Memory Pools

```python
from multiprocessing import Pool

class MemoryBoundedProcessor:
    def __init__(self, max_workers=4, max_memory_mb=500):
        self.max_workers = max_workers
        self.max_memory = max_memory_mb * 1024 * 1024

    def process_batch(self, items):
        # Estimate memory per item
        sample_size = sys.getsizeof(items[0]) if items else 0
        batch_size = min(
            len(items),
            self.max_memory // (sample_size or 1)
        )

        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            with Pool(self.max_workers) as pool:
                batch_results = pool.map(process_item, batch)
                results.extend(batch_results)

            # Force garbage collection between batches
            gc.collect()

        return results
```

## Parallel Processing

### Parallel Test Execution

```python
# pytest.ini
[tool:pytest]
addopts = -n auto  # Use all CPU cores

# Or explicitly
pytest -n 4  # Use 4 workers
```

### Parallel Content Loading

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

class ParallelOmnidexer:
    def load_all_sources_parallel(self, sources):
        """Load multiple sources in parallel."""
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for source in sources:
                future = executor.submit(self._load_source, source)
                futures.append((source, future))

            results = {}
            for source, future in futures:
                try:
                    results[source] = future.result(timeout=30)
                except Exception as e:
                    logger.error(f"Failed to load {source}: {e}")
                    results[source] = None

            return results
```

### Async Tag Resolution

```python
import asyncio

class AsyncTagResolver:
    async def resolve_tags_batch(self, texts: List[str]):
        """Resolve tags in parallel."""
        tasks = [
            self.resolve_tags_in_text(text)
            for text in texts
        ]
        return await asyncio.gather(*tasks)

    async def resolve_tags_in_text(self, text: str):
        # Extract tags
        tags = self.extract_tags(text)

        # Resolve in parallel
        resolutions = await asyncio.gather(*[
            self.resolve_single_tag(tag)
            for tag in tags
        ])

        # Replace in text
        result = text
        for tag, resolution in zip(tags, resolutions):
            result = result.replace(tag, resolution)

        return result
```

## Optimization Techniques

### Pre-computation

```python
class PrecomputedIndexes:
    """Build indexes at startup for fast lookups."""

    def __init__(self):
        self.name_index = {}
        self.source_index = {}
        self.cr_index = {}
        self.spell_level_index = {}

    def build_indexes(self, content):
        """One-time index building."""
        for item in content:
            # Name index
            self.name_index[item.name.lower()] = item

            # Source index
            if item.source not in self.source_index:
                self.source_index[item.source] = []
            self.source_index[item.source].append(item)

            # Specialized indexes
            if hasattr(item, 'cr'):
                if item.cr not in self.cr_index:
                    self.cr_index[item.cr] = []
                self.cr_index[item.cr].append(item)

    def find_by_cr(self, cr: str) -> List:
        """O(1) lookup by CR."""
        return self.cr_index.get(cr, [])
```

### String Interning

```python
import sys

class StringOptimizer:
    """Reduce memory for repeated strings."""

    def __init__(self):
        self.interned = {}

    def intern(self, s: str) -> str:
        """Return canonical instance of string."""
        if s not in self.interned:
            self.interned[s] = sys.intern(s)
        return self.interned[s]

    def process_entry(self, entry):
        """Intern common strings in entries."""
        if isinstance(entry, dict):
            # Intern type strings
            if 'type' in entry:
                entry['type'] = self.intern(entry['type'])

            # Intern source abbreviations
            if 'source' in entry:
                entry['source'] = self.intern(entry['source'])
```

### Batch Operations

```python
class BatchProcessor:
    """Process items in batches for efficiency."""

    def process_spells(self, spells: List[Spell]):
        # Batch database queries
        all_components = self.fetch_components_batch(
            [s.id for s in spells]
        )

        # Batch template rendering
        template = self.env.get_template("spell.tex.j2")
        contexts = [self.build_context(s) for s in spells]

        results = []
        for context in contexts:
            # Reuse compiled template
            result = template.render(context)
            results.append(result)

        return results
```

## Configuration for Performance

### Environment Variables

```bash
# Increase parallelism
export DND5E_MAX_WORKERS=8

# Adjust cache sizes
export DND5E_CACHE_SIZE=2048
export DND5E_CACHE_TTL=600

# Memory limits
export DND5E_MAX_MEMORY_MB=1024

# Disable expensive features
export DND5E_DISABLE_DEEP_INDEXING=1
export DND5E_DISABLE_VALIDATION=1  # Dangerous!
```

### Config File Settings

```yaml
# .5e2pdf.yml
performance:
  cache:
    enabled: true
    size: 2048
    ttl_seconds: 600
    disk_cache: true
    cache_dir: .cache

  parallel:
    enabled: true
    max_workers: 4
    chunk_size: 100

  memory:
    max_memory_mb: 1024
    lazy_loading: true
    streaming: true

  optimization:
    precompute_indexes: true
    intern_strings: true
    batch_size: 50
```

## Monitoring Performance

### Performance Metrics

```python
import time
from contextlib import contextmanager

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}

    @contextmanager
    def measure(self, operation: str):
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            memory_delta = self._get_memory_usage() - start_memory

            if operation not in self.metrics:
                self.metrics[operation] = []

            self.metrics[operation].append({
                'time': elapsed,
                'memory': memory_delta
            })

    def report(self):
        for op, measurements in self.metrics.items():
            times = [m['time'] for m in measurements]
            memory = [m['memory'] for m in measurements]

            print(f"{op}:")
            print(f"  Time: avg={np.mean(times):.3f}s, "
                  f"p99={np.percentile(times, 99):.3f}s")
            print(f"  Memory: avg={np.mean(memory)/1e6:.1f}MB")
```

### Continuous Profiling

```python
# In production
import pyflame

class ProductionProfiler:
    def __init__(self, sample_rate=0.01):
        self.sample_rate = sample_rate
        self.enabled = random.random() < sample_rate

    def profile_request(self, func):
        if not self.enabled:
            return func()

        # Sample this request
        with pyflame.profile(f"profile_{time.time()}.flame"):
            return func()
```

## Common Performance Issues

### Issue: Slow Adventure Loading

**Symptoms**: Loading adventures takes 10+ seconds

**Solution**:
```python
# Before: Loading everything
omnidexer.load_all_data()

# After: Load only needed sources
omnidexer.load_sources(["PHB", "MM", "LMoP"])
```

### Issue: Memory Explosion

**Symptoms**: Memory usage grows to GBs

**Solution**:
```python
# Clear caches periodically
def process_large_book(book):
    for i, chapter in enumerate(book.chapters):
        result = process_chapter(chapter)

        # Clear caches every 10 chapters
        if i % 10 == 0:
            clear_caches()
            gc.collect()
```

### Issue: Slow Tag Resolution

**Symptoms**: Tag-heavy content renders slowly

**Solution**:
```python
# Batch resolve all tags upfront
tags = extract_all_tags(content)
resolutions = batch_resolve_tags(tags)
tag_cache.update(resolutions)

# Then process with cache
process_with_cache(content, tag_cache)
```

## Best Practices

1. **Profile before optimizing** - Measure, don't guess
2. **Cache aggressively** - But invalidate appropriately
3. **Lazy load when possible** - Don't load until needed
4. **Batch operations** - Reduce overhead
5. **Use parallelism wisely** - Not everything benefits
6. **Monitor production** - Real-world usage differs from tests
7. **Document performance** - Track improvements/regressions

## See Also

- {doc}`/developer/contributing/test-performance-monitoring` - Test performance
- {doc}`architecture-diagrams` - System architecture
- {doc}`/user-guide/configuration-reference` - Performance settings
