# Testing Guide

This guide covers Studiorum's comprehensive testing framework, from unit tests to integration testing with real 5e content.

## Testing Philosophy

Studiorum follows a multi-layered testing approach:

- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Real 5etools data with mocked external services
- **LaTeX Tests**: Full pipeline testing with PDF generation
- **Property-Based Testing**: Automated edge case discovery

## Test Categories

### Unit Tests (`tests/unit/`)

Fast tests that run without external dependencies:

```bash
# Run all unit tests (< 30 seconds)
make test

# Run unit tests with coverage
uv run pytest tests/unit/ --cov=src/studiorum --cov-report=html

# Run specific test module
uv run pytest tests/unit/core/test_omnidexer.py -v
```

**Characteristics:**
- No LaTeX compilation required
- Mocked external services
- Fast execution (< 1ms per test)
- Run on every commit

### Integration Tests (`tests/integration/`)

Tests with real 5etools data but controlled environment:

```bash
# Run integration tests (requires test data)
uv run pytest tests/integration/ -v

# Run with real data marker
uv run pytest -m "requires_data" --tb=short
```

**Characteristics:**
- Uses real 5etools content
- Mocked LaTeX compilation
- Slower execution (1-5 seconds per test)
- Required for content processing changes

### LaTeX Tests (`tests/latex/`)

Full pipeline testing with PDF generation:

```bash
# Run LaTeX integration tests (requires LaTeX installation)
make test-latex-integration

# Single LaTeX test
uv run pytest tests/latex/test_pdf_generation.py::test_adventure_compilation -v
```

**Characteristics:**
- Real LaTeX compilation
- PDF output validation
- Slowest execution (10-60 seconds per test)
- Required for rendering changes

## Test Setup and Configuration

### Development Environment Setup

```python
# tests/conftest.py - Global test configuration
import pytest
from studiorum.core.container import reset_global_container

@pytest.fixture(autouse=True)
def reset_container():
    """Reset global container for each test."""
    reset_global_container()
    yield
    reset_global_container()

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        "data_sources": {
            "srd": {"enabled": True},
            "primary_override": {"enabled": False}
        },
        "rendering": {
            "include_images": False,
            "output_format": "latex"
        }
    }
```

### Test Method Setup Pattern

```python
class TestOmnidexer:
    """Test class following Studiorum patterns."""

    def setup_method(self):
        """Reset container before each test."""
        from studiorum.core.container import reset_global_container
        reset_global_container()  # Required for parallel tests

    def test_loads_creature_data_successfully(self):
        """Test creature data loading with descriptive name."""
        from studiorum.cli.utils import get_omnidexer

        omnidexer = get_omnidexer()
        creatures = list(omnidexer.get_all_by_type('creature'))

        assert len(creatures) > 0
        assert all(hasattr(c, 'name') for c in creatures)
```

## Testing Patterns and Best Practices

### Service Container Testing

Always reset the global container for test isolation:

```python
def setup_method(self):
    from studiorum.core.container import reset_global_container
    reset_global_container()
```

### Result Type Testing

Test both success and error paths with Result types:

```python
def test_content_resolution_success():
    """Test successful content resolution."""
    result = resolver.resolve_adventure("cos")

    assert isinstance(result, Success)
    adventure = result.unwrap()
    assert adventure.name == "Curse of Strahd"

def test_content_resolution_failure():
    """Test failed content resolution."""
    result = resolver.resolve_adventure("nonexistent")

    assert isinstance(result, Error)
    assert "not found" in result.error.lower()
```

### Async/Sync Testing

Test both CLI (sync) and MCP (async) code paths:

```python
# CLI sync pattern
def test_cli_creature_lookup():
    omnidexer = get_omnidexer()  # Sync access
    creatures = omnidexer.find_all('creature', 'Ancient Red Dragon')
    assert len(creatures) > 0

# MCP async pattern
@pytest.mark.asyncio
async def test_mcp_creature_lookup():
    async with create_mcp_request_container(config) as ctx:
        omnidexer = await ctx.get_service(OmnidexerProtocol)
        creatures = omnidexer.find_all('creature', 'Ancient Red Dragon')
        assert len(creatures) > 0
```

### Property-Based Testing

Use Hypothesis for automated edge case discovery:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_creature_name_validation(creature_name):
    """Test creature name validation with generated inputs."""
    # Test that validation doesn't crash on any string input
    result = validate_creature_name(creature_name)
    assert isinstance(result, (Success, Error))
```

## Test Data Management

### Using Test Configuration

```python
# tests/test_helpers.py
def reset_test_environment():
    """Reset environment for testing."""
    import os
    os.environ['STUDIORUM_CONFIG_FILE'] = 'test-config.yaml'
    reset_global_container()

# In tests
def test_with_test_config():
    reset_test_environment()
    # Test using test configuration
```

### Real Data Testing

Mark tests that require real 5etools data:

```python
@pytest.mark.requires_data
def test_creature_rendering_with_real_data():
    """Test creature rendering with actual Monster Manual data."""
    omnidexer = get_omnidexer()
    ancient_dragon = next(omnidexer.find_all('creature', 'Ancient Red Dragon'))

    # Test with real creature data
    latex_output = renderer.render_creature(ancient_dragon)
    assert '\\DndMonster' in latex_output
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

@patch('studiorum.latex_engine.core.images.image_processor.ImageProcessor')
def test_image_processing_mock(mock_image_processor):
    """Test with mocked image processor."""
    mock_processor = Mock()
    mock_processor.process_image.return_value = Success("processed_image.png")
    mock_image_processor.return_value = mock_processor

    # Test logic without actual image processing
    result = process_content_with_images(content)
    assert isinstance(result, Success)
```

## Running Tests

### Make Targets

```bash
# Fast unit tests only
make test

# All tests including integration
make test-all

# LaTeX tests (requires LaTeX installation)
make test-latex-integration

# Tests with coverage report
make test-coverage
```

### Pytest Command Examples

```bash
# Run specific test file
uv run pytest tests/unit/core/test_omnidexer.py -v

# Run tests matching pattern
uv run pytest -k "test_creature" -v

# Run with markers
uv run pytest -m "not requires_data" -v  # Skip data-dependent tests
uv run pytest -m "requires_data" -v      # Only data-dependent tests

# Run with coverage
uv run pytest tests/unit/ --cov=src/studiorum --cov-report=html

# Run in parallel (faster)
uv run pytest tests/unit/ -n auto

# Stop on first failure
uv run pytest tests/unit/ -x

# Show slowest tests
uv run pytest tests/unit/ --durations=10
```

### Environment-Specific Testing

```bash
# Test with specific configuration
STUDIORUM_CONFIG_FILE=test-config.yaml uv run pytest tests/integration/

# Test with debug logging
STUDIORUM_LOGGING_LEVEL=DEBUG uv run pytest tests/unit/ -v -s

# Test without progress bars
STUDIORUM_PROGRESS=false uv run pytest tests/integration/

# Test with specific data directory
STUDIORUM_DATA_DIRECTORY=/path/to/test/data uv run pytest tests/
```

## Writing Effective Tests

### Test Naming Conventions

```python
# ✅ Good - Descriptive test names that explain behavior
def test_omnidexer_loads_creature_data_successfully():
def test_adventure_conversion_includes_appendices_when_requested():
def test_mcp_tool_returns_error_for_invalid_creature_name():
def test_latex_renderer_handles_missing_images_gracefully():

# ❌ Bad - Generic test names
def test_omnidexer():
def test_conversion():
def test_mcp():
```

### Test Structure (Arrange-Act-Assert)

```python
def test_creature_challenge_rating_calculation():
    """Test CR calculation for creature encounters."""
    # Arrange
    creatures = [
        create_test_creature("Goblin", cr=0.25),
        create_test_creature("Orc", cr=0.5),
        create_test_creature("Ogre", cr=2)
    ]

    # Act
    total_cr = calculate_encounter_cr(creatures)

    # Assert
    assert total_cr == 3.75  # Expected combined CR
    assert isinstance(total_cr, float)
```

### Error Testing

```python
def test_content_resolver_handles_missing_files():
    """Test graceful handling of missing content files."""
    # Test that missing files don't crash the system
    result = resolver.resolve_content("nonexistent-file")

    assert isinstance(result, Error)
    assert "not found" in result.error.lower()
    assert "nonexistent-file" in result.error
```

### Integration Test Patterns

```python
@pytest.mark.integration
def test_full_adventure_conversion_pipeline():
    """Test complete adventure conversion from JSON to LaTeX."""
    # This test covers the full pipeline
    adventure_name = "cos"

    # Load from omnidexer
    omnidexer = get_omnidexer()
    adventure_result = omnidexer.resolve_adventure(adventure_name)
    assert isinstance(adventure_result, Success)

    # Convert to LaTeX
    renderer = get_latex_renderer()
    latex_result = renderer.render_adventure(adventure_result.value)
    assert isinstance(latex_result, Success)

    # Validate LaTeX content
    latex_content = latex_result.value
    assert "\\chapter{" in latex_content  # Has chapters
    assert "\\DndMonster{" in latex_content  # Has creatures
    assert "\\begin{document}" in latex_content  # Valid LaTeX
```

## Performance Testing

### Benchmarking

```python
import time
import pytest

def test_omnidexer_performance_benchmark():
    """Benchmark omnidexer loading performance."""
    start_time = time.time()

    omnidexer = get_omnidexer()
    omnidexer.load_all_content_types()

    load_time = time.time() - start_time

    # Performance assertion (adjust based on test environment)
    assert load_time < 5.0, f"Content loading took {load_time:.2f}s, expected < 5s"

@pytest.mark.slow
def test_large_adventure_conversion_performance():
    """Test performance with large adventure conversion."""
    start_time = time.time()

    # Convert large adventure
    result = convert_adventure("wdmm")  # Waterdeep: Dungeon of the Mad Mage

    conversion_time = time.time() - start_time

    assert isinstance(result, Success)
    assert conversion_time < 120.0, f"Conversion took {conversion_time:.2f}s, expected < 120s"
```

### Memory Testing

```python
import psutil
import os

def test_memory_usage_during_conversion():
    """Test memory usage doesn't exceed reasonable limits."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Perform memory-intensive operation
    result = convert_large_bestiary()

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    assert isinstance(result, Success)
    assert memory_increase < 500, f"Memory increased by {memory_increase:.1f}MB, expected < 500MB"
```

## Continuous Integration

### GitHub Actions Testing

Tests run automatically on:
- Pull requests to `main` or `develop`
- Pushes to `main` and `develop` branches
- Nightly scheduled runs

**Test matrix:**
- Python 3.12+ on Ubuntu, macOS, Windows
- With and without LaTeX installation
- Unit tests on all platforms
- Integration tests on Ubuntu only
- LaTeX tests only when LaTeX is available

### Pre-commit Hooks

Quality checks run before each commit:

```yaml
# .pre-commit-config.yaml (excerpt)
repos:
  - repo: local
    hooks:
      - id: tests
        name: run-tests
        entry: make test
        language: system
        pass_filenames: false
```

## Debugging Test Failures

### Common Test Issues

**Container not reset:**
```python
# Add to setup_method
def setup_method(self):
    reset_global_container()  # Essential for test isolation
```

**Async/sync mismatch:**
```python
# For CLI tests, use sync patterns
omnidexer = get_omnidexer()

# For MCP tests, use async patterns
async with create_mcp_request_container(config) as ctx:
    omnidexer = await ctx.get_service(OmnidexerProtocol)
```

**Test data not available:**
```python
# Mark tests that need real data
@pytest.mark.requires_data
def test_with_real_content():
    # Skip if no test data available
    pytest.importorskip("test_data_available")
```

### Debug Test Output

```bash
# Show full output including print statements
uv run pytest tests/unit/test_example.py -v -s

# Show full traceback on failures
uv run pytest tests/unit/test_example.py --tb=long

# Stop on first failure for easier debugging
uv run pytest tests/unit/test_example.py -x

# Run single test with maximum verbosity
uv run pytest tests/unit/test_example.py::test_specific_function -vvv -s
```

## Test Fixtures and Utilities

### Common Fixtures

```python
# tests/conftest.py
@pytest.fixture
def sample_creature():
    """Provide a sample creature for testing."""
    return Creature(
        name="Test Dragon",
        size=CreatureSize.LARGE,
        creature_type=CreatureType.DRAGON,
        challenge_rating=ChallengeRating(5),
        # ... other required fields
    )

@pytest.fixture
def mock_omnidexer():
    """Provide a mocked omnidexer."""
    mock = Mock(spec=OmnidexerProtocol)
    mock.find_all.return_value = [sample_creature()]
    return mock
```

### Test Utilities

```python
# tests/test_helpers.py
def create_test_creature(name: str, cr: float = 1) -> Creature:
    """Create a minimal creature for testing."""
    return Creature(
        name=name,
        challenge_rating=ChallengeRating(cr),
        # Set minimal required fields with sensible defaults
    )

def assert_latex_valid(latex_content: str) -> None:
    """Assert that LaTeX content is structurally valid."""
    assert "\\begin{document}" in latex_content
    assert "\\end{document}" in latex_content
    assert latex_content.count("\\begin{") == latex_content.count("\\end{")
```

---

For more development information, see [Getting Started](getting-started.md) and [Contributing](contributing.md).
