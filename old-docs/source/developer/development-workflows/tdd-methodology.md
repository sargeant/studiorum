# Test-Driven Development (TDD) Methodology

The systematic approach to TDD used in the 5e2pdf project.

## TDD Workflow Overview

5e2pdf follows a five-stage TDD process: Explore → Plan → Tests → Code → Validate.

### Stage 1: Explore

Use parallel subagents to find relevant files (examples, edit targets). Return file paths and key insights.

**Key Activities:**
- Examine existing similar implementations
- Identify affected components
- Understand current test patterns
- Locate relevant documentation

**Example:**
```bash
# Find existing spell-related tests
rg "class.*Spell.*Test" tests/
# Look for similar parsing implementations
rg "from_json" src/dnd5e/core/models/
```

### Stage 2: Plan

Create detailed implementation plan including tests and sphinx docs. Use subagents for web research if needed. Ask questions before proceeding if uncertain.

**Planning Checklist:**
- [ ] Define clear success criteria
- [ ] Identify test cases (happy path, edge cases, errors)
- [ ] Plan implementation approach
- [ ] Consider performance implications
- [ ] Document API changes if applicable

### Stage 3: Tests

Write unit tests first with expected behavior. Use subagents to run tests. If issues arise, return to planning.

**Test Structure:**
```python
class TestNewFeature:
    def test_happy_path(self):
        """Test the main use case."""
        # Arrange
        input_data = create_test_data()

        # Act
        result = new_feature(input_data)

        # Assert
        assert result.is_valid()
        assert result.output == expected_output

    def test_edge_case(self):
        """Test boundary conditions."""
        pass

    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ExpectedError):
            new_feature(invalid_data)
```

### Stage 4: Code

Implement with thorough plan and passing tests. Follow existing style and `ruff` defaults. Fix linter warnings.

**Implementation Guidelines:**
- Follow existing code patterns
- Use type hints throughout
- Add docstrings for public methods
- Handle errors gracefully
- Optimize for readability first

### Stage 5: Validate

Ensure all new tests pass. Run full pytest suite before merging to develop.

**Validation Checklist:**
- [ ] All new tests pass
- [ ] Existing tests still pass
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Documentation updated
- [ ] Performance acceptable

## TDD Best Practices

### Test Organization

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── models/             # Model validation tests
│   ├── parsers/            # Parser logic tests
│   └── utils/              # Utility function tests
├── integration/            # Component interaction tests
│   ├── loading/            # Data loading workflows
│   └── rendering/          # End-to-end rendering
└── performance/            # Performance regression tests
```

### Test Naming Conventions

```python
class TestSpellParser:
    def test_parse_valid_spell_creates_spell_object(self):
        """Test name describes: method_scenario_expected_result"""
        pass

    def test_parse_missing_name_raises_validation_error(self):
        """Clear description of error conditions"""
        pass
```

### Fixture Patterns

```python
@pytest.fixture
def sample_spell_data():
    """Provide consistent test data."""
    return {
        "name": "Fireball",
        "level": 3,
        "school": "Evocation",
        "entries": ["A bright streak..."]
    }

@pytest.fixture
def spell_parser():
    """Provide configured parser instance."""
    return SpellParser(config=test_config)
```

### Mock Usage

```python
def test_loader_with_network_failure(mock_requests):
    """Test error handling with external dependencies."""
    mock_requests.get.side_effect = ConnectionError("Network down")

    loader = ContentLoader()
    with pytest.raises(LoadingError):
        loader.fetch_remote_content()
```

### Test Isolation and Global State Management

**CRITICAL**: The #1 cause of test instability is global state contamination. ALL new tests MUST follow this pattern:

#### Mandatory Test Setup

```python
from tests.test_helpers import reset_test_environment  # Import LAST

class TestYourFeature:
    def setup_method(self) -> None:
        reset_test_environment()  # Only this call needed
        # Your test-specific setup here
```

**Why This Matters:**
- **Test Contamination**: Tests pass individually but fail in `make test`
- **Global State Issues**: Services from previous tests affect new tests
- **Flaky Tests**: "Works first time, fails second time" problems
- **Registry Pollution**: ContentType registrations persist between tests

#### What `reset_test_environment()` Handles

The single function replaces complex manual resets:

```python
def reset_test_environment():
    """Comprehensive test environment reset."""
    # Service container reset (all singletons)
    reset_global_container()

    # Content type registry reset (preserves decorators)
    reset_content_type_registry()

    # ContentFactory reset (clears class-level state)
    ContentFactory._class_map = {}

    # Cache reset (disk cache cleared)
    CacheManager.reset()

    # CLI globals reset
    reset_cli_globals()

    # Garbage collection
    gc.collect()
```

#### Legacy vs. Modern Patterns

**❌ Legacy Pattern (NEVER use):**
```python
from dnd5e.core.container import reset_global_container
from dnd5e.core.cache import CacheManager
# ... 8+ more imports

class BadTestPattern:
    def setup_method(self) -> None:
        # Complex manual reset - easy to forget something
        reset_global_container()
        CacheManager.reset()
        reset_content_type_registry()
        reset_reference_manager()  # Deprecated
        reset_all_services()       # Deprecated
        # ... easy to miss one and cause contamination
```

**✅ Modern Pattern (ALWAYS use):**
```python
from tests.test_helpers import reset_test_environment

class TestYourFeature:
    def setup_method(self) -> None:
        reset_test_environment()  # Handles everything
        # Optional: test-specific setup
```

#### Test Failure Patterns

Common test failures indicating global state issues:

**ContentFactory Errors:**
```python
# Error: assert None is not None
# Cause: ContentFactory._class_map not reset
# Fix: Use reset_test_environment()
```

**ContentType Missing:**
```python
# Error: AttributeError: type object 'ContentType' has no attribute 'DISEASE'
# Cause: Registry not properly reset/initialized
# Fix: reset_test_environment() + initialize_content_types() in test
```

**Deep Indexing Failures:**
```python
# Error: AssertionError: Expected 5 items, got 12
# Cause: Omnidexer retaining data from previous test
# Fix: reset_test_environment() ensures fresh omnidexer
```

#### Testing Dynamic Content Types

When testing new content types with `@content_type` decorator:

```python
from tests.test_helpers import reset_test_environment
from dnd5e.core.registry import initialize_content_types

class TestNewContentType:
    def setup_method(self) -> None:
        reset_test_environment()  # Critical for registry reset

    def test_content_type_registration(self) -> None:
        # Import triggers @content_type decorator registration
        from dnd5e.core.models.my_content import MyContent

        # Initialize to apply registrations
        initialize_content_types()

        # Now can test dynamic content type
        from dnd5e.core.models.content import ContentType
        assert hasattr(ContentType, 'MY_CONTENT')
        assert ContentType.MY_CONTENT == "my_content"
```

#### Performance Impact

**Test Setup Time:**
- `reset_test_environment()`: ~10-15ms per test
- Manual resets: ~25-40ms per test (when done correctly)
- **Recommendation**: Minimal performance impact for reliability benefit

#### Import Order Requirements

**CRITICAL**: Test helpers must be imported LAST to prevent contamination:

```python
# ✅ Correct import order
import pytest
from unittest.mock import Mock
from dnd5e.core.models.content import ContentType
from dnd5e.core.loaders.omnidexer import Omnidexer

from tests.test_helpers import reset_test_environment  # LAST

# ❌ Wrong import order - can cause contamination
from tests.test_helpers import reset_test_environment  # TOO EARLY
import pytest
from dnd5e.core.models.content import ContentType
```

## Red-Green-Refactor Cycle

### Red Phase (Failing Test)

Write a test that fails for the right reason:

```python
def test_new_feature_returns_expected_result():
    # This will fail because new_feature() doesn't exist yet
    result = new_feature("input")
    assert result == "expected"
```

### Green Phase (Minimal Implementation)

Make the test pass with minimal code:

```python
def new_feature(input_data):
    # Simplest implementation that makes test pass
    return "expected"
```

### Refactor Phase (Improve Code)

Improve code quality while keeping tests green:

```python
def new_feature(input_data: str) -> str:
    """Process input and return expected result."""
    # Better implementation with proper logic
    processed = process_input(input_data)
    return format_output(processed)
```

## Testing Patterns by Component

### Model Testing

```python
class TestSpell:
    def test_from_json_with_valid_data(self, sample_spell_data):
        spell = Spell.from_json(sample_spell_data, "PHB")
        assert spell.name == "Fireball"
        assert spell.level == 3

    def test_from_json_with_invalid_level_raises_error(self):
        invalid_data = {"name": "Test", "level": "invalid"}
        with pytest.raises(ValidationError):
            Spell.from_json(invalid_data, "PHB")
```

### Parser Testing

```python
class TestContentParser:
    def test_parse_spell_list_returns_spell_objects(self, spell_list_data):
        parser = ContentParser()
        spells = parser.parse_spells(spell_list_data)

        assert len(spells) == 3
        assert all(isinstance(s, Spell) for s in spells)

    def test_parse_malformed_data_logs_warning_and_continues(self):
        mixed_data = [valid_spell_data, malformed_data, valid_spell_data]

        with LogCapture() as logs:
            spells = parser.parse_spells(mixed_data)

        assert len(spells) == 2  # Only valid spells
        assert "Failed to parse" in logs.records[0].getMessage()
```

### Integration Testing

```python
class TestOmnidexerIntegration:
    def test_full_loading_workflow(self):
        omnidexer = Omnidexer()
        omnidexer.load_all_data()

        # Test cross-component functionality
        spell = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        assert spell is not None
        assert spell.name == "Fireball"
```

## Continuous Integration

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: Run fast tests
        entry: uv run pytest tests/unit/
        language: system

      - id: mypy
        name: Type checking
        entry: uv run mypy src/
        language: system
```

### CI Pipeline Testing

```yaml
# GitHub Actions example
- name: Run test suite
  run: |
    uv run pytest tests/ --cov=src/dnd5e --cov-report=xml

- name: Type checking
  run: uv run mypy src/

- name: Linting
  run: uv run ruff check src/ tests/
```

## Performance Testing

### Benchmark Tests

```python
def test_spell_parsing_performance():
    """Ensure parsing performance doesn't regress."""
    large_spell_list = create_large_spell_dataset(1000)

    start_time = time.time()
    parser.parse_spells(large_spell_list)
    duration = time.time() - start_time

    assert duration < 5.0  # Should complete in under 5 seconds
```

### Memory Usage Tests

```python
def test_memory_usage_during_loading():
    """Monitor memory usage during large data loads."""
    import tracemalloc

    tracemalloc.start()
    omnidexer = Omnidexer()
    omnidexer.load_all_data()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 500 * 1024 * 1024  # Under 500MB peak usage
```

## Debugging Failed Tests

### Common Failure Patterns

1. **Assertion Errors**: Check expected vs actual values
2. **Type Errors**: Verify input data types match expectations
3. **Import Errors**: Ensure all dependencies are available
4. **Logic Errors**: Check for proper function call patterns and data flow

### Debugging Tools

```python
# Add debugging output to tests
def test_with_debug_output(capfd):
    result = function_under_test()
    print(f"Debug: result = {result}")  # Will be captured

    captured = capfd.readouterr()
    assert "expected_output" in captured.out
```

### Test Data Debugging

```python
def test_with_data_inspection():
    data = load_test_data()

    # Debug data structure
    import pprint
    pprint.pprint(data)

    # Continue with test
    result = process_data(data)
    assert result.is_valid()
```

This TDD methodology ensures high code quality, comprehensive test coverage, and maintainable code throughout the 5e2pdf project.
