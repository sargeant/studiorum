# Image Processing Observability

Comprehensive observability system for Phase 4 image processing operations,
providing real-time monitoring, performance tracking, and operational
intelligence through Logfire integration.

## Overview

The image observability system provides:

- **Performance Metrics**: Pipeline timing, throughput, and resource usage
- **Quality Monitoring**: Success rates, confidence scores, and fallback tracking
- **Operational Intelligence**: Real-time status, error tracking, and trends
- **Logfire Integration**: Structured logging and dashboard visualization

## Quick Start

### Basic Usage

```python
from studiorum.core.logging.image_observability import (
    track_image_operation,
    ImageProcessingStage,
    get_image_observer,
)
from studiorum.latex_engine.core.images.placement_models import ContentType

# Context manager for operation tracking
with track_image_operation(
    stage=ImageProcessingStage.PLACEMENT,
    content_type=ContentType.BESTIARY,
    content_id="ancient-red-dragon"
) as tracking:
    # Your image processing code here
    result = place_dragon_image(image_data)

    # Update tracking with results
    tracking["set_confidence"](result.confidence)
    tracking["set_fallback"](result.used_fallback)
    tracking["add_metadata"]("placement_type", result.placement_type)
```

### Decorator-Based Instrumentation

```python
@observe_image_processing(
    stage=ImageProcessingStage.OPTIMIZATION,
    content_type=ContentType.ADVENTURE,
)
async def optimize_adventure_images(images, context):
    # Automatic tracking of timing, success/failure, and confidence
    optimized = await image_optimizer.process_batch(images)
    return optimized
```

### Cache Operation Monitoring

```python
@observe_cache_operation("image_placement_cache")
def get_cached_placement(self, cache_key):
    # Automatic cache hit/miss tracking
    return self._cache.get(cache_key)
```

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                Image Observability System                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ ImageProcessing │  │ AsyncResource   │  │ Performance  │ │
│  │ Observer        │  │ Monitor         │  │ Reporter     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Logfire Integration                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Context         │  │ Decorators      │  │ Service      │ │
│  │ Managers        │  │                 │  │ Integration  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Service Integration

The observability system integrates with the ModernServiceContainer:

```python
from studiorum.core.services.observability_integration import (
    register_observability_services,
    register_enhanced_image_services,
)

# Register observability services
register_observability_services(container)

# Or register enhanced versions with automatic observability
register_enhanced_image_services(container)
```

## Features

### 1. Performance Metrics

**Pipeline Timing**:
- Discovery duration and success rates
- Placement decision timing and confidence
- Optimization processing time
- Rendering pipeline performance

**Resource Monitoring**:
- Memory usage during operations
- CPU utilization tracking
- Resource leak detection
- Peak usage identification

**Throughput Analysis**:
- Operations per second
- Batch processing efficiency
- Concurrent operation scaling
- Bottleneck identification

### 2. Quality & Success Monitoring

**Success Rates**:
- Overall operation success/failure rates
- Success rates by content type
- Success rates by processing stage
- Trending analysis over time

**Placement Quality**:
- Confidence scores for placement decisions
- Fallback usage tracking
- Alternative placement analysis
- Content-aware effectiveness

**Error Tracking**:
- Categorized error types and frequencies
- Error context preservation
- Root cause analysis data
- Recovery success rates

### 3. Cache Effectiveness

**Hit/Miss Tracking**:
- Cache hit ratios by cache type
- Miss pattern analysis
- Cache effectiveness by content type
- Performance impact of caching

**Cache Operations**:
- Store/evict operation timing
- Cache size and growth patterns
- Memory usage by cache
- Optimal cache sizing recommendations

### 4. Logfire Integration

**Structured Logging**:
- Operation lifecycle events
- Performance metrics as structured data
- Error events with full context
- Cache operation tracking

**Dashboard Data**:
- Real-time performance metrics
- Historical trend data
- Alert threshold monitoring
- Custom dashboard creation

## Configuration

### Basic Configuration

```yaml
# config/observability.yaml
observability:
  enable_observability: true
  debug_mode: false

  metrics:
    enable_performance_tracking: true
    enable_cache_monitoring: true
    performance_warning_threshold_ms: 5000.0
    cache_hit_ratio_warning_threshold: 0.7

  logfire:
    enable_logfire_integration: true
    log_operation_details: true
    min_operation_duration_to_log_ms: 100.0

  cli_reporting:
    enable_progress_reporting: true
    show_eta_estimates: true

  mcp:
    enable_request_isolation: true
    monitor_async_resource_usage: true
```

### Advanced Configuration

```python
from studiorum.core.config.observability_config import ImageObservabilityConfig

config = ImageObservabilityConfig(
    metrics=ObservabilityMetricsConfig(
        performance_warning_threshold_ms=3000.0,
        memory_warning_threshold_mb=500.0,
    ),
    enabled_stages=[
        "discovery",
        "placement",
        "optimization",
    ],
    monitored_content_types=[
        "bestiary",
        "adventure",
    ],
)
```

## Usage Patterns

### CLI Operations

```python
from studiorum.core.logging.image_observability import ProgressReporter

def process_bestiary(creatures, quiet=False):
    reporter = ProgressReporter(quiet=quiet)
    successful = 0

    for i, creature in enumerate(creatures):
        reporter.report_progress(i, len(creatures), "Processing creatures")

        with track_image_operation(
            stage=ImageProcessingStage.DISCOVERY,
            content_type=ContentType.BESTIARY,
            content_id=creature.name,
        ) as tracking:
            try:
                images = discover_creature_images(creature)
                tracking["add_metadata"]("image_count", len(images))
                successful += 1
            except Exception as e:
                # Error automatically tracked
                pass

    reporter.report_completion("Creature processing", len(creatures), successful)
```

### MCP Async Operations

```python
async def process_adventure_request(adventure_data):
    async with track_async_image_operation(
        stage=ImageProcessingStage.BATCH_PROCESSING,
        content_type=ContentType.ADVENTURE,
        content_id=adventure_data["id"],
    ) as tracking:

        # Start resource monitoring
        monitor = get_resource_monitor()
        await monitor.start_monitoring(tracking["operation_id"])

        # Process adventure
        result = await process_adventure_images(adventure_data)

        # Get resource usage
        resources = await monitor.stop_monitoring(tracking["operation_id"])
        tracking["set_resource_usage"](
            memory_mb=resources.get("memory_usage_mb"),
            cpu_percent=resources.get("cpu_usage_percent"),
        )

        return result
```

### Service Enhancement

```python
from studiorum.core.services.observability_integration import (
    enhance_service_with_observability
)

# Enhance existing service
original_service = ImageSourceRegistry()
observable_service = enhance_service_with_observability(original_service)

# All method calls now automatically tracked
images = await observable_service.resolve_image_path("dragon.jpg")
```

## Performance Reports

### Generate Reports

```python
from studiorum.core.logging.image_observability import (
    generate_performance_report,
    log_performance_summary,
)

# Generate detailed report
report = generate_performance_report()
print(f"Performance Grade: {report['performance_grade']}")
print(f"Recommendations: {report['recommendations']}")

# Log summary to Logfire
log_performance_summary()
```

### Example Report Output

```json
{
  "performance_grade": "A",
  "recommendations": [],
  "statistics": {
    "operation_count": 1250,
    "success_rate": 0.984,
    "avg_duration_ms": 245.7,
    "cache_hit_ratio": 0.847,
    "content_type_distribution": {
      "bestiary": 650,
      "adventure": 400,
      "item_collection": 200
    }
  },
  "health_indicators": {
    "success_rate_healthy": true,
    "cache_effective": true,
    "performance_acceptable": true
  }
}
```

## Dashboard Integration

### Logfire Dashboard Queries

**Operation Success Rate**:
```sql
SELECT
  COUNT(*) as total_ops,
  SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successful,
  AVG(duration_ms) as avg_duration
FROM image_operations
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY content_type
```

**Cache Performance**:
```sql
SELECT
  cache_name,
  COUNT(CASE WHEN operation = 'hit' THEN 1 END) as hits,
  COUNT(CASE WHEN operation = 'miss' THEN 1 END) as misses,
  ROUND(hits::float / (hits + misses) * 100, 2) as hit_ratio
FROM cache_operations
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY cache_name
```

### Custom Metrics

```python
# Custom metrics for specific business logic
observer = get_image_observer()

observer.record_batch_operation(
    operation_type="adventure_batch_processing",
    items_processed=50,
    duration_ms=12500,
    success_count=47,
    failure_count=3,
    metadata={
        "adventure_type": "published_module",
        "optimization_level": "high_quality",
    }
)
```

## Testing

### Unit Tests

```python
from studiorum.core.logging.image_observability import (
    reset_image_observer,
    get_image_observer,
)

def test_image_processing():
    # Reset for clean test
    reset_image_observer()

    with track_image_operation(
        stage=ImageProcessingStage.PLACEMENT,
        content_type=ContentType.BESTIARY,
    ) as tracking:
        # Test your code
        tracking["set_confidence"](0.9)

    observer = get_image_observer()
    stats = observer.get_statistics()
    assert stats["success_count"] == 1
```

### Integration Tests

```python
@pytest.mark.requires_logfire
async def test_full_observability_integration():
    # Test with real Logfire integration
    setup_logging(enable_telemetry=True)

    async with track_async_image_operation(
        stage=ImageProcessingStage.OPTIMIZATION,
        content_type=ContentType.ADVENTURE,
    ) as tracking:
        result = await optimize_images(test_images)
        tracking["set_confidence"](result.confidence)

    # Verify Logfire received data
    # (Implementation depends on test environment)
```

## Troubleshooting

### Common Issues

**High Memory Usage**:
- Check `memory_peak_mb` in statistics
- Review batch sizes for large operations
- Monitor resource usage with AsyncResourceMonitor

**Low Cache Hit Ratios**:
- Review cache key generation
- Check cache size limits
- Analyze cache eviction patterns

**Performance Degradation**:
- Use performance reports to identify bottlenecks
- Check for resource contention
- Review error patterns for systematic issues

### Debug Mode

```python
config = ImageObservabilityConfig(debug_mode=True)
# Enables verbose logging of all observability operations
```

## Best Practices

1. **Use Context Managers**: Always prefer context managers over manual tracking
2. **Set Meaningful Metadata**: Add context that helps with debugging
3. **Monitor Resource Usage**: Use AsyncResourceMonitor for long-running operations
4. **Regular Performance Reviews**: Generate reports regularly to identify trends
5. **Configure Appropriately**: Tune thresholds based on your performance requirements
6. **Test Observability**: Include observability in your test scenarios

## API Reference

### Core Classes

- **ImageProcessingObserver**: Central observability coordinator
- **AsyncResourceMonitor**: Resource usage tracking
- **ProgressReporter**: CLI progress reporting
- **ImageObservabilityConfig**: Configuration management

### Context Managers

- **track_image_operation**: Sync operation tracking
- **track_async_image_operation**: Async operation tracking

### Decorators

- **@observe_image_processing**: Automatic operation instrumentation
- **@observe_cache_operation**: Cache operation monitoring

### Enums

- **ImageProcessingStage**: Processing pipeline stages
- **ImageProcessingResult**: Operation results
- **CacheOperation**: Cache operation types

For complete API documentation, see the module docstrings in
`src/studiorum/core/logging/image_observability.py`.
