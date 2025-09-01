# Comprehensive Data Validation Test Suite

This directory contains a comprehensive test suite designed to stress test data validation across the entire 5etools dataset.

## Test Structure

### Unit Tests

#### `test_data_validation_stress.py`
- **Purpose**: Stress test data validation with real dataset
- **Features**:
  - Load all spell, creature, and item data
  - Test omnidexer with full dataset
  - Validate complex data structures
  - Test file format detection accuracy
  - Memory usage monitoring
  - Concurrent loading tests
  - Validation error categorization

#### `test_model_validation_edge_cases.py`
- **Purpose**: Test specific edge cases and complex data structures
- **Features**:
  - Complex spell entry structures (nested lists, tables, quotes)
  - Spell higher level variations
  - Creature type variations (choice formats, complex tags)
  - Creature alignment variations (nested structures)
  - HP and AC special formats
  - Damage resistance/immunity formats
  - Skill bonus formats
  - Challenge rating formats

#### `test_liberal_parsing.py`
- **Purpose**: Test liberal parsing capabilities
- **Features**:
  - Foundry VTT file detection and skip
  - Template file detection and skip
  - Copy-template detection and skip
  - Fluff file detection and liberal parsing
  - Missing required fields default handling
  - Complex text extraction from nested structures
  - Stress test with ultra-complex data structures

### Integration Tests

#### `test_full_dataset_validation.py`
- **Purpose**: Full dataset integration testing
- **Features**:
  - Complete spell dataset validation
  - Complete creature dataset validation
  - Complete item dataset validation
  - Omnidexer full dataset load
  - Data consistency across loaders
  - Memory efficiency testing
  - Concurrent dataset loading
  - Validation warning categorization

## Running Tests

### Quick Tests (Unit tests only)
```bash
# Run quick validation tests
python scripts/run_validation_stress_tests.py --quick

# Run specific test file
uv run python -m pytest tests/unit/test_model_validation_edge_cases.py -v

# Run liberal parsing tests
uv run python -m pytest tests/unit/test_liberal_parsing.py -v
```

### Full Stress Tests (Including slow integration tests)
```bash
# Run all validation stress tests
python scripts/run_validation_stress_tests.py

# Run with coverage
python scripts/run_validation_stress_tests.py --coverage --verbose

# Run only integration tests
uv run python -m pytest tests/integration/ -v -m slow
```

### Generate Validation Report
```bash
# Generate comprehensive validation report
uv run python scripts/generate_validation_report.py
```

## Test Markers

- `@pytest.mark.slow` - Marks tests that take significant time (integration tests)
- `@pytest.mark.integration` - Integration tests that test end-to-end functionality
- `@pytest.mark.stress` - Stress tests for validation

## Validation Thresholds

The tests use adaptive thresholds based on dataset size:

- **Spell validation warnings**: ≤ 1% of total spells (minimum 10)
- **Creature validation warnings**: ≤ 1.5% of total creatures (minimum 15)
- **Item validation warnings**: ≤ 0.5% of total items (minimum 5)
- **Overall validation warnings**: ≤ 1% of total items (minimum 20)
- **Memory usage**: ≤ 1GB increase, ≤ 100KB per item
- **Unknown structure errors**: ≤ 10% of total validation warnings

## Expected Results

### Successful Validation Indicators
- ✅ All core content types load successfully
- ✅ Liberal parsing handles complex structures
- ✅ File format detection works accurately
- ✅ Memory usage stays within bounds
- ✅ Validation warnings stay under thresholds
- ✅ No unknown data structure errors

### Common Legitimate Warnings
- Dynamic passive perception formulas (e.g., `'10 + (PB × 2)'`)
- Incomplete NPC data (missing creature stats)
- Variable challenge ratings (e.g., `'1-4'` or `'Equal to summoner level'`)
- Missing content in index/sources files

## Architecture

### Log Capture System
Tests use a custom log capture system to analyze validation warnings and errors:

```python
class LogCapture:
    def __init__(self, level=logging.WARNING):
        self.records = []
        self.level = level
```

### Validation Report Generation
The `ValidationReport` class provides comprehensive analysis:
- Content statistics by type
- File analysis and suspicious file detection
- Performance metrics
- Validation issue categorization
- Automated recommendations

### Liberal Parsing Testing
Tests verify that the system gracefully handles:
- Complex nested entry structures
- Missing required fields (with defaults)
- File format variations (Foundry, templates, fluff)
- Inconsistent data structures
- Choice formats and special values

## Performance Benchmarks

Based on typical 5etools dataset:
- **Loading speed**: ~1000-5000 items/second
- **Memory usage**: ~10-50 MB for full dataset
- **Validation warnings**: <1% of total items
- **File processing**: >95% success rate

## Maintenance

### Adding New Tests
1. Add test methods to appropriate test class
2. Use descriptive names: `test_specific_feature_description`
3. Include both positive and negative test cases
4. Add appropriate pytest markers

### Updating Thresholds
Adjust validation thresholds in test files based on:
- Dataset size changes
- New content type additions
- Model validation improvements
- Performance requirements

### Monitoring
Run validation tests regularly to catch:
- New data structure patterns
- Performance regressions
- Validation rule changes
- Dataset quality issues
