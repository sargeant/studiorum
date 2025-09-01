# Test Performance Monitoring

This document outlines the test performance monitoring infrastructure, performance budgets, and monitoring procedures for the 5e2pdf project.

## Overview

The 5e2pdf project uses comprehensive test performance monitoring to:

- **Track execution time trends** over time
- **Monitor memory usage** during test execution
- **Detect performance regressions** early
- **Maintain performance budgets** for different test categories
- **Provide actionable insights** for optimization

## Performance Budgets

Performance budgets define acceptable limits for test execution to maintain developer productivity and CI efficiency.

### Test Execution Time Budgets

| Test Category | Budget | Rationale |
|---------------|--------|-----------|
| **Fast Tests** | 30 seconds | Should complete quickly during development |
| **All Tests** | 5 minutes | Maximum acceptable CI time for full test suite |
| **Individual Unit Test** | 1 second | Keep feedback loop tight |
| **Individual Integration Test** | 10 seconds | Allow for setup/teardown of real data |
| **Property-Based Tests** | 5 seconds | Hypothesis tests with reasonable example count |

### Memory Usage Budgets

| Metric | Budget | Rationale |
|--------|--------|-----------|
| **Memory Increase** | 100 MB | Prevent memory leaks in test suite |
| **Peak Memory Usage** | 500 MB | Reasonable limit for development machines |
| **Per-Test Memory** | 10 MB | Individual test should not consume excessive memory |

### Test Count Budgets

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| **Total Tests** | ~1,600 | Stable | Focus on quality over quantity |
| **Fast Test Ratio** | 80% | >75% | Most tests should be fast unit tests |
| **Property Tests** | 35+ | 50+ | Expand property-based testing coverage |

## Monitoring Infrastructure

### Performance Monitoring Script

The `scripts/test_performance_monitor.py` script provides comprehensive performance tracking:

```bash
# Run tests with performance monitoring
make test-perf

# Run all tests with performance monitoring
make test-perf-all

# Create performance baseline
make test-baseline

# Generate performance report
make test-perf-report
```

### Metrics Collected

#### Execution Metrics
- **Total Duration**: Complete test run time
- **Individual Test Times**: Per-test execution duration
- **Slowest Tests**: Top 10 slowest tests with timings
- **Test Outcomes**: Pass/fail/skip counts

#### Memory Metrics
- **Initial Memory**: Memory usage before test execution
- **Peak Memory**: Maximum memory during execution
- **Memory Increase**: Net memory growth during tests
- **Garbage Collection**: Object creation/cleanup patterns

#### System Metrics
- **CPU Usage**: Processor utilization during tests
- **Disk I/O**: File system operations
- **Network Activity**: For integration tests
- **Process Count**: Parallel test execution monitoring

### Historical Tracking

Performance metrics are stored in `tests/performance_metrics.json` with:

- **Rolling History**: Last 50 test runs to track trends
- **Timestamp Tracking**: When each run occurred
- **Git Context**: Commit hash and branch information
- **Environment Data**: Python version, OS, CI vs local

## Performance Baselines

### Creating Baselines

Performance baselines establish reference points for regression detection:

```bash
# Create new baseline (run this after major optimizations)
make test-baseline
```

Baselines capture:
- **Fast test performance** (development workflow)
- **Full test suite performance** (CI workflow)
- **Memory usage patterns**
- **Test reliability metrics**

### When to Update Baselines

Update baselines when:

1. **Major Performance Improvements**: After significant optimizations
2. **Test Suite Changes**: Adding/removing substantial test categories
3. **Infrastructure Changes**: New test framework versions, CI updates
4. **Hardware Changes**: Different CI runners or development environments

### Baseline Storage

Baselines are stored in `tests/performance_baseline.json` and should be:
- **Version controlled** to track baseline evolution
- **Documented** with reasons for baseline changes
- **Validated** by running performance checks after updates

## Regression Detection

### Regression Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Execution Time** | +5 seconds | Warning |
| **Execution Time** | +10 seconds | Failure |
| **Memory Usage** | +50 MB | Warning |
| **Memory Usage** | +100 MB | Failure |
| **Test Failures** | Any increase | Failure |

### Regression Analysis

When regressions are detected:

1. **Identify Root Cause**
   - Compare current vs baseline metrics
   - Review recent commits for performance-affecting changes
   - Check for new test additions or modifications

2. **Investigate Specific Tests**
   - Examine slowest tests list
   - Profile individual test execution
   - Check for resource leaks or inefficient operations

3. **Take Corrective Action**
   - Optimize slow tests
   - Improve test isolation
   - Update test infrastructure
   - Consider moving slow tests to different category

## CI Integration

### GitHub Actions Integration

The CI pipeline automatically:

- **Monitors Performance** on every pull request
- **Compares Against Baseline** to detect regressions
- **Posts Performance Reports** as PR comments
- **Fails Builds** if critical thresholds are exceeded

### Performance Reporting

Performance reports include:

```markdown
## 📊 Test Performance Report

### Latest Test Run
- **Duration**: 25.3 seconds
- **Tests**: 1,574 passed, 0 failed, 12 skipped
- **Memory Usage**: 45.2MB increase

### Slowest Tests
1. **test_large_dataset_processing**: 2.341s
2. **test_full_adventure_conversion**: 1.892s
3. **test_complex_latex_rendering**: 1.203s

### Performance Budget Status
- **Duration Budget**: ✅ 25.3s / 30s
- **Memory Budget**: ✅ 45.2MB / 100MB
```

### Quality Gates

Performance quality gates ensure:
- **Fast tests complete within budget**
- **Memory usage stays within limits**
- **No significant regressions introduced**
- **Test reliability remains high**

## Local Development Workflow

### Daily Development

For regular development:

```bash
# Run fast tests with basic performance awareness
make test

# Check performance if tests feel slow
make test-perf
```

### Performance Investigation

When investigating performance issues:

```bash
# Run with detailed performance monitoring
make test-perf-all

# Generate comprehensive report
make test-perf-report

# Compare against baseline
make test-baseline  # If needed to update baseline
```

### Pre-Commit Performance Check

Before committing performance-sensitive changes:

```bash
# Full performance validation
make test-perf-all
make test-quality-check
```

## Optimization Strategies

### Test Speed Optimization

1. **Minimize I/O Operations**
   - Use in-memory test data when possible
   - Cache expensive setup operations
   - Prefer mocks for external dependencies

2. **Optimize Test Data**
   - Use smaller, focused test datasets
   - Generate minimal data needed for test validity
   - Share expensive fixture setup when safe

3. **Improve Test Isolation**
   - Avoid session-scoped mutable fixtures
   - Use factory patterns for customizable test data
   - Clean up resources promptly

4. **Leverage Parallelization**
   - Use `pytest-xdist` for parallel execution
   - Ensure tests are truly independent
   - Balance parallel worker count with resource usage

### Memory Optimization

1. **Resource Management**
   - Explicitly close files and connections
   - Use context managers for resource cleanup
   - Monitor object lifecycle in long-running tests

2. **Data Structure Efficiency**
   - Use generators instead of lists when appropriate
   - Prefer memory-efficient data structures
   - Avoid deep copying large objects unnecessarily

3. **Garbage Collection**
   - Force garbage collection after expensive operations
   - Monitor for circular references
   - Use memory profiling tools for investigation

## Monitoring Tools and Commands

### Make Targets

```bash
# Performance monitoring
make test-perf           # Fast tests with monitoring
make test-perf-all       # All tests with monitoring
make test-baseline       # Create performance baseline
make test-perf-report    # Generate performance report

# Quality monitoring
make test-quality        # Test quality analysis
make test-quality-check  # Quality gates validation
```

### Direct Script Usage

```bash
# Performance monitoring with custom options
python scripts/test_performance_monitor.py --test-type=fast --threshold=8.0

# Quality analysis with custom options
python scripts/test_quality_metrics.py --report --fail-on-issues
```

### Environment Variables

Control monitoring behavior:

```bash
# Skip performance monitoring in CI
export SKIP_PERF_MONITORING=1

# Custom performance thresholds
export PERF_THRESHOLD_SECONDS=15.0
export PERF_THRESHOLD_MEMORY_MB=150

# Enable verbose performance logging
export PERF_VERBOSE=1
```

## Troubleshooting Performance Issues

### Common Issues and Solutions

#### Slow Test Execution

**Symptoms**: Tests taking longer than expected

**Investigation**:
```bash
# Run with detailed timing
make test-perf-all

# Check slowest tests
pytest --durations=10
```

**Solutions**:
- Profile individual slow tests
- Optimize test data generation
- Review fixture scoping
- Consider moving to integration test category

#### Memory Growth

**Symptoms**: Memory usage increasing over time

**Investigation**:
```bash
# Monitor memory patterns
python scripts/test_performance_monitor.py --test-type=all

# Use memory profilers
pip install memory-profiler
python -m memory_profiler test_script.py
```

**Solutions**:
- Add explicit resource cleanup
- Check for fixture memory leaks
- Review object lifecycle management
- Use smaller test datasets

#### Flaky Performance

**Symptoms**: Inconsistent performance across runs

**Investigation**:
- Run multiple performance monitoring cycles
- Check for system resource contention
- Review test isolation issues
- Monitor CI vs local performance differences

**Solutions**:
- Improve test isolation
- Add resource cleanup
- Use more deterministic test data
- Adjust performance thresholds for variance

## Performance Culture

### Best Practices

1. **Performance Awareness**
   - Consider performance impact when writing tests
   - Use appropriate test categories (unit vs integration)
   - Monitor performance trends regularly

2. **Continuous Monitoring**
   - Run performance monitoring on significant changes
   - Review performance reports in code reviews
   - Update baselines thoughtfully

3. **Optimization Mindset**
   - Profile before optimizing
   - Measure impact of performance changes
   - Balance speed with test quality

4. **Team Collaboration**
   - Share performance insights
   - Document performance decisions
   - Collaborate on optimization strategies

### Performance Review Checklist

When reviewing performance-sensitive changes:

- [ ] Performance monitoring run completed
- [ ] No significant regressions detected
- [ ] Memory usage within acceptable limits
- [ ] Test execution time reasonable
- [ ] Performance budget compliance verified
- [ ] Baseline update considered if needed

## Conclusion

Effective test performance monitoring ensures:

- **Developer Productivity**: Fast feedback loops
- **CI Efficiency**: Reasonable build times
- **Quality Maintenance**: Consistent test reliability
- **Early Detection**: Performance regressions caught quickly
- **Informed Decisions**: Data-driven optimization choices

Regular monitoring and adherence to performance budgets maintain a healthy, efficient test suite that supports rapid development while ensuring comprehensive validation of the D&D 5e PDF generation system.
