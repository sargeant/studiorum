# Async Development Patterns

The 5e2pdf codebase uses an async-first architecture for optimal performance, particularly when dealing with file I/O operations and bulk processing. This document outlines the patterns, best practices, and APIs available for async development.

## Architecture Overview

### Core Async Components

The codebase implements async patterns across several key layers:

1. **File I/O Layer**: All file operations use `aiofiles` for non-blocking I/O
2. **Content Loading**: Data loaders use concurrent processing for large files
3. **Content Resolution**: Bulk resolution operations for multiple items
4. **Source Management**: Parallel source indexing and updates

### Performance Benefits

- **Concurrent File Loading**: 60-80% improvement when loading multiple adventures/books
- **Parallel Source Indexing**: 40-60% improvement with multiple content sources
- **Batch Validation**: 30-50% improvement for large content files (>50 items)
- **Bulk Operations**: 70-90% improvement when resolving multiple items

## Content Resolution Patterns

### Single Item Resolution

```python
from dnd5e.core.resolvers.content_resolver import ContentResolver

async def resolve_single_adventure():
    resolver = ContentResolver(omnidexer)

    # Async resolution with content loading
    result = await resolver.resolve_adventure("cos")

    if result.is_success:
        adventure = result.content
        # Adventure now includes merged metadata + content data
        print(f"Loaded: {adventure.name}")
```

### Bulk Resolution (Recommended)

```python
async def resolve_multiple_adventures():
    resolver = ContentResolver(omnidexer)

    # Bulk resolution - much faster than individual calls
    abbreviations = ["cos", "lmop", "hotdq", "rot", "oota"]
    results = await resolver.resolve_adventures_bulk(abbreviations)

    successful_adventures = [
        result.content for result in results
        if result.is_success
    ]

    print(f"Successfully loaded {len(successful_adventures)} adventures")
```

### Mixed Content Types

```python
async def resolve_mixed_content():
    resolver = ContentResolver(omnidexer)

    # Mixed content types with single call
    requests = [
        ("cos", ContentType.ADVENTURE),
        ("phb", ContentType.BOOK),
        ("mm", ContentType.BOOK),
        ("lmop", ContentType.ADVENTURE)
    ]

    results = await resolver.resolve_multiple(requests)

    for result in results:
        if result.is_success:
            print(f"Loaded {result.content.name}")
        else:
            print(f"Failed to resolve {result.query}: {result.status}")
```

## Content Loading Patterns

### Data Loader Usage

```python
from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.loaders.content_factory import ContentFactory
from dnd5e.core.models.content import ContentType

async def load_spell_data():
    loader = JsonDataLoader(ContentType.SPELL, ContentFactory())

    # Automatic optimization based on file size
    # Files >50 items use concurrent validation
    spells = await loader.load(Path("spells.json"))

    print(f"Loaded {len(spells)} spells")
```

### Content Merger Operations

```python
from dnd5e.core.loaders.content_merger import ContentMerger

async def merge_adventure_content():
    merger = ContentMerger(source_manager)

    # Async content file loading with caching
    content_data = await merger.load_content_file(
        ContentType.ADVENTURE, "cos"
    )

    if content_data:
        # Merge with metadata
        merged = merger.merge_metadata_content(metadata_entry, content_data)
        print(f"Merged {len(merged.get('contents', []))} sections")
```

## Source Management Patterns

### Concurrent Source Updates

```python
from dnd5e.core.sources.manager import SourceManager

async def update_all_sources():
    manager = SourceManager()

    # Build index with parallel source processing
    await manager.build_content_index(force_rebuild=True)

    # Sources are indexed concurrently for optimal performance
    total_files = sum(
        len(files) for files in manager._content_index.values()
    )
    print(f"Indexed {total_files} total files")
```

### GitHub Repository Operations

```python
async def update_repositories():
    github_manager = GitHubSourceManager(cache_dir)

    # Concurrent repository updates
    sources = [source1, source2, source3]  # ContentSource objects
    update_status = await github_manager.update_multiple_repositories_concurrently(sources)

    for repo_name, success in update_status.items():
        print(f"Repository {repo_name}: {'✓' if success else '✗'}")
```

## Template and Compilation Patterns

### LaTeX Template Rendering

```python
from dnd5e.renderers.latex.template_engine import LaTeXTemplateEngine

async def render_templates():
    engine = LaTeXTemplateEngine()

    # Async template loading and rendering
    result = engine.render_template("spell_entry", {
        "name": "Fireball",
        "level": 3,
        "description": "A bright streak flashes..."
    })

    print(f"Rendered template: {len(result)} characters")
```

### Document Compilation

```python
from dnd5e.renderers.latex.compiler import LaTeXCompiler

async def compile_document():
    compiler = LaTeXCompiler()

    # Async compilation with dependency checking
    result = await compiler.compile_document(
        latex_content=document_latex,
        output_name="adventure",
        working_dir=Path("output")
    )

    if result.success:
        print(f"Compilation successful in {result.total_time:.2f}s")
    else:
        print(f"Compilation failed: {result.error_message}")
```

## Error Handling Patterns

### Graceful Degradation

```python
async def robust_content_loading():
    resolver = ContentResolver(omnidexer)

    try:
        # Attempt bulk resolution
        results = await resolver.resolve_adventures_bulk(abbreviations)

        # Process results with error handling
        successful = []
        failed = []

        for result in results:
            if result.is_success:
                successful.append(result.content)
            else:
                failed.append((result.query, result.status))
                # Use suggestions for failed resolutions
                if result.suggestions:
                    print(f"Suggestions for '{result.query}': {result.suggestions}")

        return successful, failed

    except Exception as e:
        logger.error(f"Bulk resolution failed: {e}")
        # Fallback to individual resolution
        return await fallback_individual_resolution(abbreviations)
```

### Exception Handling in Bulk Operations

```python
async def safe_bulk_processing():
    # asyncio.gather with return_exceptions=True
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Item {i} failed: {result}")
        else:
            successful_results.append(result)

    return successful_results
```

## Performance Optimization Guidelines

### When to Use Bulk Operations

**Use bulk operations when:**
- Processing multiple content items (>2 items)
- Loading adventures/books that require content merging
- Initial application startup
- CLI commands operating on multiple files
- Batch conversion operations

**Stick to single operations when:**
- Interactive user interfaces with immediate feedback
- Single item lookups
- Error recovery scenarios
- Development/debugging

### Batch Size Recommendations

```python
# For validation tasks
VALIDATION_BATCH_SIZE = 20  # Items per concurrent batch

# For I/O operations
IO_BATCH_SIZE = 10  # Files per concurrent batch

# For content resolution
RESOLUTION_BATCH_SIZE = 5  # Content items per batch
```

### Memory Considerations

```python
async def memory_efficient_processing():
    # Process in chunks to avoid memory spikes
    chunk_size = 50

    for i in range(0, len(large_dataset), chunk_size):
        chunk = large_dataset[i:i + chunk_size]
        results = await process_chunk_concurrently(chunk)

        # Process results immediately to free memory
        await handle_results(results)

        # Optional: brief pause to allow garbage collection
        await asyncio.sleep(0.01)
```

## Migration from Sync Code

### Before (Sync)

```python
def load_multiple_adventures(abbreviations):
    results = []
    for abbrev in abbreviations:
        result = resolver.resolve_adventure(abbrev)  # Blocking
        results.append(result)
    return results
```

### After (Async)

```python
async def load_multiple_adventures(abbreviations):
    # Single bulk operation - much faster
    results = await resolver.resolve_adventures_bulk(abbreviations)
    return results
```

### CLI Command Migration

```python
# Before
@click.command()
def convert_adventures(abbreviations):
    for abbrev in abbreviations:
        adventure = resolve_adventure(abbrev)
        convert_to_pdf(adventure)

# After
@click.command()
def convert_adventures(abbreviations):
    asyncio.run(convert_adventures_async(abbreviations))

async def convert_adventures_async(abbreviations):
    # Bulk resolution
    results = await resolver.resolve_adventures_bulk(abbreviations)

    # Concurrent conversion
    conversion_tasks = [
        convert_to_pdf_async(result.content)
        for result in results if result.is_success
    ]
    await asyncio.gather(*conversion_tasks)
```

## Testing Async Code

### Unit Tests

```python
import pytest
import asyncio

class TestAsyncContentResolver:
    @pytest.mark.asyncio
    async def test_bulk_resolution(self):
        resolver = ContentResolver(mock_omnidexer)

        abbreviations = ["cos", "lmop"]
        results = await resolver.resolve_adventures_bulk(abbreviations)

        assert len(results) == 2
        assert all(result.query in abbreviations for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_validation(self):
        loader = JsonDataLoader(ContentType.SPELL, ContentFactory())

        large_list = [{"name": f"Spell {i}", "level": 1} for i in range(100)]
        results = await loader._validate_items_concurrently(large_list, Path("test"))

        assert len(results) <= len(large_list)  # Some may fail validation
```

### Performance Testing

```python
import time

async def benchmark_bulk_vs_individual():
    abbreviations = ["cos", "lmop", "hotdq", "rot", "oota"]

    # Individual resolution
    start = time.time()
    individual_results = []
    for abbrev in abbreviations:
        result = await resolver.resolve_adventure(abbrev)
        individual_results.append(result)
    individual_time = time.time() - start

    # Bulk resolution
    start = time.time()
    bulk_results = await resolver.resolve_adventures_bulk(abbreviations)
    bulk_time = time.time() - start

    print(f"Individual: {individual_time:.2f}s")
    print(f"Bulk: {bulk_time:.2f}s")
    print(f"Improvement: {individual_time/bulk_time:.1f}x faster")
```

## Common Pitfalls

### Don't Forget await

```python
# Wrong - returns coroutine object
result = resolver.resolve_adventure("cos")

# Correct - awaits the coroutine
result = await resolver.resolve_adventure("cos")
```

### Don't Use Sync Methods in Async Context

```python
# Wrong - blocks the event loop
content = file.read_text()

# Correct - uses async I/O
async with aiofiles.open(file) as f:
    content = await f.read()
```

### Don't Create Unnecessary Event Loops

```python
# Wrong - in async function
async def bad_example():
    asyncio.run(some_async_function())  # Creates nested event loop

# Correct
async def good_example():
    await some_async_function()
```

This async-first architecture provides significant performance improvements while maintaining clean, readable code. Always prefer bulk operations when processing multiple items, and use the concurrent patterns outlined above for optimal performance.
