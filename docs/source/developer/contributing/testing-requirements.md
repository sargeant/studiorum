# Testing Guidelines

This document provides comprehensive guidelines for writing, maintaining, and reviewing tests in the 5e2pdf project. These guidelines are based on modern pytest best practices and lessons learned from implementing property-based testing with Hypothesis.

## Overview

The 5e2pdf project uses a multi-layered testing approach combining:

- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests that verify component interactions with real data
- **Performance Tests**: Benchmarks that ensure system scalability
- **Property-Based Tests**: Hypothesis-powered tests that automatically discover edge cases

## Testing Architecture

### Directory Structure

```
tests/
├── unit/               # Fast, isolated tests for single components
├── integration/        # Component interaction tests with real data
├── performance/        # Memory and execution time benchmarks
├── property_based/     # Hypothesis-powered property testing
├── cli/               # Command-line interface testing
├── renderers/         # LaTeX and other output format tests
└── conftest.py        # Shared fixtures and configuration
```

### Test Categories and Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.slow          # Tests taking >5 seconds
@pytest.mark.integration   # Component interaction tests
@pytest.mark.performance   # Memory/time benchmarks
@pytest.mark.property      # Hypothesis property tests
```

## Core Testing Principles

### 1. Test Behavior, Not Implementation

**❌ Bad - Testing Implementation Details:**
```python
def test_omnidexer_internal_state():
    omnidexer = Omnidexer()
    assert omnidexer._depth == 0  # Testing private attribute
    assert len(omnidexer._loaders) > 0  # Internal structure
```

**✅ Good - Testing Behavior:**
```python
def test_omnidexer_initialization():
    omnidexer = Omnidexer()
    assert omnidexer.is_ready_for_indexing()
    assert omnidexer.get_loader_count() > 0
```

### 2. Write Meaningful Assertions

**❌ Bad - False Positive Assertions:**
```python
def test_content_processing():
    content = process_content(data)
    assert len(content) >= 0  # Always passes - len() never negative
    assert content is not None  # Weak assertion
```

**✅ Good - Specific Assertions:**
```python
def test_content_processing():
    content = process_content(data)
    assert len(content) > 0, f"Expected processed content, got empty result"
    assert isinstance(content, list), f"Expected list, got {type(content)}"
    assert all(item.is_valid() for item in content), "All items should be valid"
```

### 3. Use Modern Fixture Patterns

**❌ Bad - Session-Scoped Mutable State:**
```python
@pytest.fixture(scope="session")
def shared_omnidexer():
    omnidexer = Omnidexer()
    omnidexer.load_data()  # Shared mutable state
    return omnidexer
```

**✅ Good - Factory Pattern for Isolation:**
```python
@pytest.fixture
def make_omnidexer():
    def _make_omnidexer(config_overrides=None):
        config = default_config()
        if config_overrides:
            config.update(config_overrides)
        return Omnidexer(config)
    return _make_omnidexer

def test_with_custom_config(make_omnidexer):
    omnidexer = make_omnidexer({"strict_mode": True})
    # Test gets fresh, isolated instance
```

## Testing Patterns by Component Type

### D&D Content Models (Spells, Creatures, etc.)

Use property-based testing for rule validation:

```python
from hypothesis import given, strategies as st

@given(level=st.integers(min_value=0, max_value=9))
def test_spell_level_constraints(level):
    spell = create_spell(level=level)
    assert 0 <= spell.level <= 9
    assert isinstance(spell.level, int)

@given(valid_spells())  # Custom strategy
def test_spell_serialization_roundtrip(spell):
    serialized = spell.model_dump()
    deserialized = Spell.model_validate(serialized)
    assert spell == deserialized
```

### LaTeX Rendering

Focus on semantic validation, not string matching:

```python
def test_spell_latex_structure(sample_spell):
    latex_output = render_spell_to_latex(sample_spell)

    # Test semantic structure, not exact strings
    assert latex_has_section("Spell Name", latex_output)
    assert latex_has_field("Level", latex_output)
    assert is_valid_latex(latex_output)

    # Avoid brittle string matching
    # BAD: assert "\\section{Fireball}" in latex_output
```

### CLI Commands

Use real test data with minimal mocking:

```python
def test_convert_adventure_command(tmp_path, sample_adventure_file):
    output_file = tmp_path / "output.tex"

    # Test with real data, minimal mocking
    result = runner.invoke(app, [
        "adventure",
        str(sample_adventure_file),
        "--output", str(output_file)
    ])

    assert result.exit_code == 0
    assert output_file.exists()
    assert output_file.stat().st_size > 0
```

### Content Loading and Processing

Use integration tests with real data:

```python
def test_spell_loading_integration(srd_spell_data):
    loader = SpellLoader()
    spells = loader.load_from_file(srd_spell_data)

    assert len(spells) > 0
    assert all(spell.name for spell in spells)
    assert all(0 <= spell.level <= 9 for spell in spells)
```

## Property-Based Testing Guidelines

### When to Use Hypothesis

Use property-based testing for:

1. **Domain Rule Validation**: D&D rules (spell levels, ability scores)
2. **Serialization/Deserialization**: Roundtrip testing
3. **Input Validation**: Testing parser robustness
4. **System Invariants**: Properties that should always hold

### Creating Custom Strategies

```python
from hypothesis import strategies as st
from hypothesis.strategies import composite

@composite
def valid_spells(draw):
    """Generate valid D&D spells following SRD rules."""
    name = draw(st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
    level = draw(st.integers(min_value=0, max_value=9))
    school = draw(st.sampled_from([
        "abjuration", "conjuration", "divination", "enchantment",
        "evocation", "illusion", "necromancy", "transmutation"
    ]))

    return Spell(
        name=name.strip(),
        level=level,
        school=school
    )

@given(valid_spells())
def test_spell_properties(spell):
    assert len(spell.name.strip()) > 0
    assert 0 <= spell.level <= 9
    assert spell.school in VALID_SCHOOLS
```

### Stateful Testing for Complex Interactions

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, Bundle

class ContentSystemMachine(RuleBasedStateMachine):
    omnidexers = Bundle("omnidexers")

    @rule(target=omnidexers)
    def create_omnidexer(self):
        return Omnidexer()

    @rule(omnidexer=omnidexers, content=valid_spells())
    def add_content(self, omnidexer, content):
        initial_count = omnidexer.content_count
        omnidexer.add_content(content)
        assert omnidexer.content_count == initial_count + 1
```

## Fixture Design Patterns

### Factory Fixtures

Use factory fixtures for customizable test data:

```python
@pytest.fixture
def make_spell_data():
    def _make_spell_data(count=5, **overrides):
        spells = []
        for i in range(count):
            spell_data = {
                "name": f"Test Spell {i}",
                "level": i % 10,
                "school": "V",
                **overrides
            }
            spells.append(spell_data)
        return spells
    return _make_spell_data

def test_bulk_spell_processing(make_spell_data):
    spell_data = make_spell_data(count=10, school="Evocation")
    # Test gets exactly what it needs
```

### Temporary File Fixtures

```python
@pytest.fixture
def make_temp_data_dir():
    def _make_temp_data_dir(content_files=None):
        temp_dir = tempfile.mkdtemp()
        if content_files:
            for filename, content in content_files.items():
                file_path = Path(temp_dir) / filename
                file_path.write_text(json.dumps(content))
        return Path(temp_dir)
    return _make_temp_data_dir
```

## Assertion Best Practices

### Specific Error Messages

```python
# Good - Specific error context
assert result.is_success(), f"Processing failed: {result.error_message}"
assert len(spells) == expected_count, f"Expected {expected_count} spells, got {len(spells)}"

# Good - Multiple assertions with context
with pytest.raises(ValidationError) as exc_info:
    Spell.model_validate(invalid_data)
assert "level" in str(exc_info.value)
assert "must be between 0 and 9" in str(exc_info.value)
```

### Pytest Check for Multiple Soft Assertions

```python
import pytest_check as check

def test_spell_collection_validity(spell_collection):
    for spell in spell_collection:
        check.greater_equal(spell.level, 0, f"Invalid level for {spell.name}")
        check.less_equal(spell.level, 9, f"Invalid level for {spell.name}")
        check.is_not_none(spell.name.strip(), f"Empty name for spell")
```

## Mock Usage Guidelines

### When to Mock

Mock only external dependencies:

- **Network requests** (GitHub API calls)
- **File system operations** (when testing logic, not I/O)
- **LaTeX compiler** (external process)
- **External services** (APIs, databases)

### When NOT to Mock

Don't mock domain objects or business logic:

```python
# BAD - Over-mocking
@mock.patch('dnd5e.models.Spell')
def test_spell_processing(mock_spell):
    # Testing mock interactions, not real behavior

# GOOD - Use real objects with test data
def test_spell_processing(sample_spell_data):
    spell = Spell.model_validate(sample_spell_data)
    result = process_spell(spell)
    # Testing real behavior with real objects
```

### Strategic Mocking Pattern

```python
def test_github_source_manager_with_network_error(make_source_manager):
    with mock.patch('requests.get') as mock_get:
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        manager = make_source_manager()
        result = manager.fetch_source_list()

        assert result.is_failure()
        assert "network" in result.error_message.lower()
```

## Test Organization

### Parametrized Tests for Multiple Scenarios

```python
@pytest.mark.parametrize("spell_level,expected_text", [
    (0, "Cantrip"),
    (1, "1st-level"),
    (2, "2nd-level"),
    (3, "3rd-level"),
    (4, "4th-level"),
])
def test_spell_level_formatting(spell_level, expected_text):
    spell = create_spell(level=spell_level)
    assert spell.level_text == expected_text
```

### Test Class Organization

```python
class TestSpellValidation:
    """Group related spell validation tests."""

    def test_valid_spell_creation(self, valid_spell_data):
        spell = Spell.model_validate(valid_spell_data)
        assert spell.is_valid()

    def test_invalid_level_rejection(self):
        with pytest.raises(ValidationError):
            Spell(name="Test", level=10)  # Invalid level

    @pytest.mark.parametrize("invalid_school", ["invalid", "", None])
    def test_invalid_school_rejection(self, invalid_school):
        with pytest.raises(ValidationError):
            Spell(name="Test", level=1, school=invalid_school)
```

## Performance Testing

### Memory Usage Monitoring

```python
import psutil
import pytest

def test_memory_usage_within_bounds():
    process = psutil.Process()
    initial_memory = process.memory_info().rss

    # Perform memory-intensive operation
    result = load_large_dataset()

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # Memory increase should be reasonable
    assert memory_increase < 100 * 1024 * 1024  # Less than 100MB
```

### Execution Time Budgets

```python
@pytest.mark.performance
def test_spell_loading_performance():
    start_time = time.time()

    spells = load_all_spells()

    execution_time = time.time() - start_time
    assert execution_time < 5.0, f"Spell loading too slow: {execution_time:.2f}s"
    assert len(spells) > 0
```

## Integration Test Patterns

### Real Data Integration

```python
def test_adventure_processing_with_real_data(srd_adventure_data):
    """Test complete adventure processing pipeline."""
    processor = AdventureProcessor()

    result = processor.process_adventure(srd_adventure_data)

    assert result.is_success()
    assert result.latex_output
    assert len(result.chapters) > 0
    assert all(chapter.has_content() for chapter in result.chapters)
```

### Multi-Component Integration

```python
def test_content_resolution_integration(omnidexer, tag_resolver):
    """Test that content loading and tag resolution work together."""
    # Load content through omnidexer
    omnidexer.load_all_data()

    # Resolve references through tag system
    resolved_content = tag_resolver.resolve_all_references()

    # Verify integration
    assert len(resolved_content) > 0
    assert all(content.is_resolved() for content in resolved_content)
```

## Global State Management

**Critical for parallel test execution stability and CI/CD reliability.**

The 5e2pdf project uses a service container architecture to manage dependencies, with simplified global state reset for tests.

### Service Container Reset Pattern (Recommended)

Any test that creates real `Omnidexer()` instances or other core system components should use the unified service container reset:

```python
def setup_method(self) -> None:
    """Reset global state for test isolation using service container."""
    from dnd5e.cli.main import reset_cli_globals
    from dnd5e.core.cache import CacheManager
    from dnd5e.core.container import reset_global_container

    # Reset the service container (handles most singletons now)
    reset_global_container()

    # Reset remaining legacy global state
    CacheManager.reset()
    reset_cli_globals()
```

### Legacy Reset Pattern (Deprecated)

For backward compatibility, individual singleton resets are still available but not recommended:

```python
def setup_method(self) -> None:
    """Reset global state for test isolation (legacy approach)."""
    from dnd5e.core.cache import CacheManager
    from dnd5e.core.config.sources import reset_config_manager
    from dnd5e.core.content_type_resolver import reset_content_type_resolver
    from dnd5e.core.entry_registry import reset_entry_registry
    from dnd5e.core.interfaces import reset_content_type_registry
    from dnd5e.core.loaders.content_factory import reset_content_factory

    # Complete isolation - reset ALL global singletons (legacy)
    CacheManager.reset()
    reset_content_factory()
    reset_content_type_registry()
    reset_content_type_resolver()
    reset_entry_registry()
    reset_config_manager()
```

### Service Container vs Legacy Singletons

| Component | Service Container | Legacy Reset | Status |
|-----------|------------------|--------------|--------|
| `EntryRegistry` | ✅ `reset_global_container()` | `reset_entry_registry()` | Migrated |
| `ReferenceManager` | ✅ `reset_global_container()` | `reset_reference_manager()` | Migrated |
| `Omnidexer` | ✅ `reset_global_container()` | N/A | Managed |
| `TagResolver` | ✅ `reset_global_container()` | N/A | Managed |
| `CacheManager` | ❌ Individual reset required | `CacheManager.reset()` | Legacy |
| `CLI Globals` | ❌ Individual reset required | `reset_cli_globals()` | Legacy |

### Mock vs Real Instance Strategy

**Use Mocks When Possible:**
```python
# Preferred: Avoid global state entirely
mock_omnidexer = Mock(spec=Omnidexer)  # Use spec for Pydantic validation
```

**Use Real Instances When Required:**
```python
# When testing deep integration, use full reset pattern above
def setup_method(self) -> None:
    # ... complete global state reset as shown above

def test_real_omnidexer_functionality(self):
    omnidexer = Omnidexer()  # Now safe to use real instance
```

### Common Global State Issues

- **"Works individually, fails in parallel"** → Missing global state reset
- **"Works first time, fails second"** → Persistent cache/config state
- **"Input should be an instance of Omnidexer"** → Use `Mock(spec=Omnidexer)`
- **"FileNotFoundError: config directory"** → Missing `reset_config_manager()`
- **"assert None is not None"** → Content factory corruption

### CI/CD Considerations

In CI environments like GitHub Actions, additional isolation is critical:

1. **Directory Creation**: Config manager may try to create directories that don't exist
2. **Parallel Workers**: pytest-xdist runs tests in separate workers that share nothing
3. **Shell Compatibility**: Ensure `SHELL := /bin/bash` in Makefiles for `-o pipefail` support

## Code Review Checklist

When reviewing test code, check for:

### Test Quality
- [ ] Tests focus on behavior, not implementation details
- [ ] Assertions are specific and meaningful
- [ ] No false positive tests (assertions that always pass)
- [ ] Error messages provide useful debugging context

### Test Isolation
- [ ] Tests don't depend on execution order
- [ ] No shared mutable state between tests
- [ ] Each test can run independently
- [ ] Proper cleanup of temporary resources

### Modern Patterns
- [ ] Factory fixtures instead of session-scoped mutable fixtures
- [ ] Parametrized tests instead of duplicate test methods
- [ ] Strategic mocking of only external dependencies
- [ ] Property-based testing for domain rules

### Performance
- [ ] Fast unit tests (< 1 second each)
- [ ] Slow tests properly marked with `@pytest.mark.slow`
- [ ] Performance tests have reasonable budgets
- [ ] No unnecessary data generation in fast tests

### Coverage
- [ ] Critical business logic is tested
- [ ] Edge cases are covered (especially with Hypothesis)
- [ ] Error conditions are tested
- [ ] Integration points are validated

## Common Anti-Patterns to Avoid

### 1. Testing Implementation Details

```python
# BAD
def test_internal_cache_structure():
    loader = JsonLoader()
    assert hasattr(loader, '_cache')
    assert isinstance(loader._cache, dict)

# GOOD
def test_loader_caching_behavior():
    loader = JsonLoader()
    data1 = loader.load(test_file)
    data2 = loader.load(test_file)  # Should use cache
    assert data1 == data2
    # Verify caching improved performance if needed
```

### 2. False Positive Assertions

```python
# BAD
assert len(results) >= 0  # Always passes
assert results is not None  # Weak assertion

# GOOD
assert len(results) > 0, "Expected non-empty results"
assert isinstance(results, list), f"Expected list, got {type(results)}"
```

### 3. Over-Mocking

```python
# BAD - Mocking domain objects
@mock.patch('dnd5e.models.Spell')
@mock.patch('dnd5e.loaders.JsonLoader')
def test_spell_processing(mock_loader, mock_spell):
    # Testing mock interactions, not real behavior

# GOOD - Use real objects with test data
def test_spell_processing(sample_spell):
    result = SpellProcessor().process(sample_spell)
    assert result.is_valid()
```

### 4. Brittle Assertions

```python
# BAD - Fragile string matching
assert "\\section{Fireball}" in latex_output
assert latex_output.count("\\item") == 5

# GOOD - Semantic validation
assert latex_has_section("Fireball", latex_output)
assert latex_item_count(latex_output) >= 3
```

## Test Performance Optimization

### Efficient Test Data Generation

```python
# Use sampled_from for better performance
@composite
def efficient_spell_strategy(draw):
    school = draw(st.sampled_from(VALID_SCHOOLS))  # Fast
    level = draw(st.integers(0, 9))  # Constrained range
    name = draw(st.sampled_from(SRD_SPELL_NAMES))  # Predefined list

    return Spell(name=name, level=level, school=school)
```

### Hypothesis Configuration

```python
from hypothesis import settings

@settings(max_examples=50, deadline=5000)  # Reasonable limits
@given(efficient_spell_strategy())
def test_spell_processing_properties(spell):
    # Property test with performance constraints
    result = process_spell(spell)
    assert result.is_valid()
```

## Continuous Integration Integration

### Test Quality Gates

```python
# In CI configuration
def test_quality_gate():
    """Ensure test suite maintains quality standards."""
    test_files = collect_test_files()

    # Check for anti-patterns
    assert no_false_positive_assertions(test_files)
    assert no_private_attribute_testing(test_files)
    assert reasonable_mock_usage(test_files)

    # Performance requirements
    assert fast_test_execution_time() < 30  # seconds
    assert memory_usage_reasonable()
```

### Test Result Analysis

Monitor test health with metrics:

- **Test execution time trends**
- **Flaky test detection**
- **Coverage quality assessment**
- **Property test effectiveness**

## Conclusion

These guidelines ensure that the 5e2pdf test suite remains maintainable, reliable, and effective at catching bugs while enabling confident refactoring. The combination of traditional unit tests, integration tests, and property-based testing provides comprehensive coverage that scales with project complexity.

Key takeaways:

1. **Test behavior, not implementation**
2. **Use modern pytest patterns** (factory fixtures, parametrization)
3. **Strategic mocking** of only external dependencies
4. **Property-based testing** for domain rules and edge cases
5. **Meaningful assertions** with specific error messages
6. **Performance awareness** in test design

Following these guidelines will help maintain the high-quality test suite that enables rapid, confident development of the D&D 5e PDF generation system.
