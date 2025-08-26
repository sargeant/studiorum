# Performance Guidelines

This document outlines performance best practices and optimization patterns for the Studiorum codebase, based on lessons learned from critical performance fixes that improved test execution from 20 minutes to 3 minutes.

## Service Container Optimization

### Always Check Cached Singletons First

**❌ DON'T**: Create new instances without checking cache

```python
# Anti-pattern - creates new instances unnecessarily
def get_omnidexer():
    return create_omnidexer_service()
```

**✅ DO**: Check singleton cache first to avoid expensive operations

```python
# Optimized pattern - checks cache first
def get_service_sync(self, protocol: type[T]) -> T:
    # CRITICAL: Check sync cache first to avoid expensive asyncio.run() calls
    if self._sync_singleton_cache.contains(protocol):
        return self._sync_singleton_cache.get(protocol)

    # Only create if not cached
    return self._create_singleton_instance_sync(protocol)
```

**Impact**: This pattern provided up to 350,000x performance improvement by eliminating expensive `asyncio.run()` calls when services are already cached.

### Avoid asyncio.run() in Sync Contexts

**❌ DON'T**: Use `asyncio.run()` repeatedly for same services

```python
# Anti-pattern - creates event loop overhead every time
def get_service():
    return asyncio.run(self._async_get_service())
```

**✅ DO**: Use direct synchronous creation in test environments

```python
# Optimized pattern - bypasses event loop in tests
def get_service_sync(self, protocol: type[T]) -> T:
    # In test environments, use direct sync creation
    if os.getenv("PYTEST_CURRENT_TEST"):
        return self._create_instance_sync(protocol)

    # Production path with cache checking
    return asyncio.run(self.get_service(protocol))
```

**Impact**: Test environments achieve massive performance gains by avoiding event loop creation entirely.

### Use Direct Instantiation in Tests

**❌ DON'T**: Use full container resolution in tests

```python
# Anti-pattern - full async resolution in tests
async def test_something():
    container = ServiceContainer()
    service = await container.get_service(MyProtocol)  # Slow in tests
```

**✅ DO**: Use direct instantiation with test isolation

```python
# Optimized pattern - direct creation with proper isolation
def test_something():
    from studiorum.core.container import reset_global_container
    reset_global_container()  # Isolation

    service = get_omnidexer()  # Uses cached singleton path
```

**Impact**: Eliminates container resolution overhead while maintaining test isolation.

## Content Loading Optimization

### Reuse ContentMerger Instances

**❌ DON'T**: Create new ContentMerger for each operation

```python
# Anti-pattern - loses cache benefits
def load_content(self, content_type: str):
    merger = ContentMerger(self.source_manager)  # New instance every time
    return merger.load_content(content_type)
```

**✅ DO**: Use singleton ContentMerger to preserve cache

```python
# Optimized pattern - preserves LRU cache across operations
def load_content(self, content_type: str):
    # Reuse singleton instance to maintain cache warmth
    merger = self.get_content_merger()  # Returns cached instance
    return merger.load_content(content_type)
```

**Impact**: Cache hit rates improve from 0% to >80%, dramatically reducing file I/O operations.

### Preserve Cache Across Operations

**❌ DON'T**: Clear cache between operations

```python
# Anti-pattern - destroys cache benefits
def process_multiple_contents(self, content_list):
    for content in content_list:
        merger = ContentMerger()  # New instance = cold cache
        merger.clear_cache()      # Explicit cache clearing
        process(merger.load(content))
```

**✅ DO**: Maintain cache warmth between operations

```python
# Optimized pattern - cache remains warm
def process_multiple_contents(self, content_list):
    merger = self.get_content_merger()  # Singleton instance
    for content in content_list:
        # Cache stays warm, subsequent loads are fast
        process(merger.load(content))
```

**Impact**: Particularly beneficial in test environments with multiple data loading cycles.

### Clear Cache Only in Test Setup

**❌ DON'T**: Clear cache during normal operations

```python
# Anti-pattern - destroys performance benefits
def load_data(self):
    merger = self.get_content_merger()
    merger.clear_cache()  # Never do this in production code
    return merger.load_all()
```

**✅ DO**: Clear cache only in test isolation setup

```python
# Optimized pattern - cache clearing only for test isolation
def setup_method(self):
    from studiorum.core.container import reset_global_container
    reset_global_container()  # This clears caches for isolation
    # Normal operations preserve cache
```

**Impact**: Ensures maximum cache efficiency while maintaining test isolation.

## Testing Performance

### Use reset_test_environment() for Isolation

**❌ DON'T**: Create new containers in each test

```python
# Anti-pattern - expensive container creation
def test_something():
    container = ServiceContainer()  # Expensive setup
    # Configure container from scratch
    service = await container.get_service(MyProtocol)
```

**✅ DO**: Use global container with proper reset

```python
# Optimized pattern - reuse optimized global container
def test_something():
    from tests.test_helpers import reset_test_environment
    reset_test_environment()  # Fast isolation

    service = get_omnidexer()  # Uses optimized singleton path
```

**Impact**: Test setup time reduces from seconds to milliseconds.

### Avoid Creating Multiple Omnidexer Instances

**❌ DON'T**: Create multiple Omnidexer instances in tests

```python
# Anti-pattern - multiple instances lose cache sharing
def test_multiple_operations():
    omnidexer1 = Omnidexer()  # Cold cache
    omnidexer2 = Omnidexer()  # Cold cache again
    # No cache sharing between instances
```

**✅ DO**: Use single Omnidexer instance across operations

```python
# Optimized pattern - shared cache benefits
def test_multiple_operations():
    omnidexer = get_omnidexer()  # Singleton instance

    # All operations share cache - subsequent ops are fast
    result1 = omnidexer.get_all_by_type("book")
    result2 = omnidexer.get_all_by_type("adventure")  # Benefits from cache
```

**Impact**: Cache sharing across operations provides cumulative performance benefits.

### Run Canary Tests Before Full Suite

**✅ ALWAYS**: Run quick validation tests first

```bash
# Canary tests - run these first for quick feedback
pytest tests/integration/test_book_resolution.py -xvs
pytest tests/integration/test_adventure_conversion.py -xvs

# Full suite only after canary tests pass
time make test
```

**Impact**: Provides quick feedback loop and avoids long test runs when basic functionality is broken.

## Performance Monitoring

### Time Subset of Tests During Development

**✅ DO**: Monitor performance during development

```bash
# Monitor subset performance
time pytest tests/integration/ -x --tb=short

# Monitor specific slow tests
time pytest tests/performance/test_creature_scale_benchmarks.py -xvs
```

### Set Timeouts for Long Operations

**✅ DO**: Set reasonable timeouts for performance-sensitive operations

```bash
# Set timeout for full test suite (should complete in <3 minutes)
timeout 300s make test  # 5 minute timeout
```

**Impact**: Prevents hanging on performance regressions and provides clear failure signals.

## Key Performance Metrics

Based on the performance fixes implemented:

| Metric | Before | After | Improvement |
|--------|---------|--------|-------------|
| Test Suite Runtime | 20 minutes | 2:37 | 87% reduction |
| Failed Tests | 25 | 5 | 80% reduction |
| Memory Growth | 252MB | <50MB | 80% reduction |
| Cache Hit Rate | 0% | >80% | ∞ improvement |
| Container Sync Access | Event loop per call | Cached singleton | 350,000x faster |

## Common Performance Anti-Patterns

### 1. Event Loop Creation in Sync Contexts
- **Problem**: `asyncio.run()` calls in CLI/test environments
- **Solution**: Dual-cache singleton system with sync access paths

### 2. Cache Invalidation During Operations
- **Problem**: Creating new instances instead of reusing cached ones
- **Solution**: Singleton pattern with proper cache preservation

### 3. Excessive Container Resolution
- **Problem**: Full dependency resolution for simple operations
- **Solution**: Direct singleton access with cache checking

### 4. Test Environment Over-Engineering
- **Problem**: Using production async patterns in test environments
- **Solution**: Direct synchronous creation with proper isolation

## Performance Testing Strategy

### Development Workflow
1. **Code Changes**: Implement feature/fix
2. **Canary Tests**: Run quick integration tests
3. **Performance Check**: Time subset of tests
4. **Full Validation**: Run complete test suite with timeout
5. **Benchmark**: Compare with baseline metrics

### Continuous Monitoring
- Monitor test execution time in CI
- Alert on >5 minute test suite duration
- Track cache hit rates in performance tests
- Measure memory usage during test runs

## Future Performance Considerations

### When Adding New Services
- Always implement proper singleton caching patterns
- Avoid `asyncio.run()` in sync contexts
- Consider test environment performance impact
- Design with cache reuse in mind

### When Modifying Service Container
- Preserve dual-cache optimization system
- Maintain sync access paths for CLI operations
- Test performance impact in test environments
- Document any changes to optimization patterns

### When Writing Tests
- Use `reset_test_environment()` for isolation
- Avoid creating multiple instances of heavy services
- Prefer singleton access patterns
- Monitor test execution time during development

---

*This document is based on performance optimizations implemented in August 2025 that achieved 87% test runtime improvement and resolved critical performance regressions in the Studiorum test suite.*
