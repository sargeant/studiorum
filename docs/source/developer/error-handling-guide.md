# Error Handling Standardization Guide

This guide documents the standardized error handling patterns implemented in the D&D 5e PDF generator. The system uses a `Result[T, E]` pattern to provide consistent, type-safe error handling across all modules.

## Overview

The standardized error handling system provides:

- **Type-safe error handling** with `Result[T, E]` pattern
- **Structured error types** that integrate with existing exceptions
- **Consistent logging patterns** across all modules
- **Backward compatibility** with existing validation systems
- **Rich error context** for debugging and user guidance

## Core Components

### Result Pattern

The `Result[T, E]` pattern replaces mixed return patterns (None vs empty collections vs exceptions) with a consistent approach:

```python
from dnd5e.core.result import Result, Success, Error

def validate_spell(data: dict) -> Result[Spell, ValidationError]:
    if "name" not in data:
        return Error(create_validation_error("Missing required field 'name'"))

    try:
        spell = Spell.model_validate(data)
        return Success(spell)
    except ValidationError as e:
        return Error(create_validation_error(str(e)))
```

### Error Types

Structured error types provide rich context and suggestions:

```python
from dnd5e.core.error_types import ValidationError, ProcessingError, create_validation_error

# Validation errors
error = create_validation_error(
    message="Level must be between 1 and 9",
    field_name="level",
    entry_type="spell",
    source="phb.json",
    suggestions=["Check spell level value", "Valid levels are 1-9"]
)

# Processing errors
error = create_processing_error(
    message="Failed to process nested entries",
    entry_type="section",
    context={"nested_count": 5, "failed_at": 3}
)
```

### Standardized Logging

Consistent logging patterns ensure uniform error reporting:

```python
from dnd5e.core.logging_strategy import get_standardized_logger, error_logging_context

logger = get_standardized_logger(__name__)

with error_logging_context(logger, "spell_validation", content_name="Fireball") as context:
    result = validate_spell(spell_data)
    logger.log_result(result, "spell_validation", context=context)
```

## Migration Guide

### From Exception-Based to Result Pattern

**Before (Exception-based):**
```python
def validate_content(data: dict) -> Content:
    if not data:
        raise ValidationError("Data cannot be empty")

    try:
        return Content.model_validate(data)
    except ValidationError:
        raise
```

**After (Result pattern):**
```python
def validate_content(data: dict) -> Result[Content, ValidationError]:
    if not data:
        return Error(create_validation_error("Data cannot be empty"))

    return validate_model(Content, data)
```

### From None Returns to Result Pattern

**Before (None returns):**
```python
def find_spell(name: str) -> Spell | None:
    spell_data = lookup_spell(name)
    if spell_data is None:
        return None

    try:
        return Spell.model_validate(spell_data)
    except ValidationError:
        return None
```

**After (Result pattern):**
```python
def find_spell(name: str) -> Result[Spell, ProcessingError]:
    spell_data = lookup_spell(name)
    if spell_data is None:
        return Error(create_processing_error(f"Spell '{name}' not found"))

    return validate_model(Spell, spell_data)
```

### From Mixed Patterns to Consistent Results

**Before (Mixed patterns):**
```python
def process_entries(entries: list) -> tuple[list[Entry], list[str]]:
    """Returns (successful_entries, error_messages)"""
    successful = []
    errors = []

    for entry_data in entries:
        try:
            entry = validate_entry(entry_data)
            successful.append(entry)
        except Exception as e:
            errors.append(str(e))

    return successful, errors
```

**After (Consistent Result pattern):**
```python
def process_entries(entries: list) -> Result[list[Entry], list[ValidationError]]:
    """Returns Result with all entries or list of errors"""
    results = [validate_entry(entry_data) for entry_data in entries]
    return collect_results(results)
```

## Usage Patterns

### Basic Validation

```python
from dnd5e.core.model_validation import validate_model
from dnd5e.core.models.spells import Spell

result = validate_model(Spell, spell_data, source="phb.json")
if result.is_success():
    spell = result.unwrap()
    print(f"Validated spell: {spell.name}")
else:
    error = result.error
    logger.error(f"Validation failed: {error.message}")
    for suggestion in error.suggestions or []:
        print(f"Suggestion: {suggestion}")
```

### Batch Processing

```python
from dnd5e.core.result import collect_results

# Validate multiple items
results = [validate_spell(data) for data in spell_list]
batch_result = collect_results(results)

if batch_result.is_success():
    spells = batch_result.unwrap()
    logger.info(f"Successfully validated {len(spells)} spells")
else:
    errors = batch_result.error
    logger.error(f"Batch validation failed with {len(errors)} errors")
```

### Error Chaining

```python
def process_spell_data(data: dict) -> Result[ProcessedSpell, ValidationError]:
    return (
        validate_model(Spell, data)
        .and_then(lambda spell: enrich_spell_data(spell))
        .and_then(lambda enriched: create_processed_spell(enriched))
    )

# Usage
result = process_spell_data(raw_data)
processed_spell = result.unwrap_or_else(lambda error: create_default_spell())
```

### Context-Aware Error Handling

```python
from dnd5e.core.error_types import ErrorContext

def validate_with_context(data: dict, source: str) -> Result[Content, ValidationError]:
    context = ErrorContext(
        operation="content_validation",
        content_type="spell",
        file_path=source,
        additional_info={"data_keys": list(data.keys())}
    )

    with error_logging_context(logger, "validation", file_path=source) as log_context:
        result = validate_model(Content, data, source=source)
        logger.log_result(result, "validation", context=log_context)
        return result
```

## Error Severity Levels

The system uses consistent severity levels:

- **CRITICAL**: System cannot continue, immediate attention required
- **ERROR**: Operation failed but system can continue
- **WARNING**: Potential issue but operation succeeded
- **INFO**: Informational message about processing

```python
from dnd5e.core.error_types import ErrorSeverity

# Adjust error severity based on context
if validation_mode == "strict":
    severity = ErrorSeverity.ERROR
elif validation_mode == "permissive":
    severity = ErrorSeverity.WARNING
else:
    severity = ErrorSeverity.INFO
```

## Logging Guidelines

### When to Log

1. **Always log** CRITICAL and ERROR severity issues
2. **Log in normal mode** WARNING issues
3. **Log in verbose mode** INFO issues
4. **Include context** for all error logs
5. **Provide suggestions** when possible

### Log Message Format

Standard format includes:
- Error message
- Source location
- Category and severity
- Suggestions for resolution
- Context information

```python
# Good logging
logger.log_error(
    error=validation_error,
    context=ErrorContext(
        operation="spell_validation",
        content_name="Fireball",
        file_path="spells.json"
    )
)

# Output: "Missing required field 'name' | Source: spells.json | Category: validation |
#          Severity: error | Suggestions: Add 'name' field to spell data |
#          Context: Operation: spell_validation | Content: Fireball | File: spells.json"
```

## Integration with Existing Code

### Backward Compatibility

The system maintains compatibility with existing validation patterns:

```python
from dnd5e.core.entry_validation import migrate_validation_result

# Convert legacy ValidationResult to Result pattern
legacy_result = entry_registry.validate_entry_structure(context)
standardized_result = migrate_validation_result(legacy_result)

# Now use Result methods
entry = standardized_result.unwrap_or_else(
    lambda error: ValidatedEntry(type="error", content=error.message)
)
```

### Gradual Migration

Use compatibility wrappers for gradual migration:

```python
from dnd5e.core.entry_validation import create_compatibility_wrapper

# Wrap new validator with legacy interface
new_validator = StandardizedEntryValidator()
legacy_interface = create_compatibility_wrapper(new_validator)

# Existing code continues to work
result = legacy_interface.validate_entry_structure(context)
```

## Testing Error Handling

### Testing Success Cases

```python
def test_successful_validation():
    result = validate_spell(valid_spell_data)
    assert result.is_success()

    spell = result.unwrap()
    assert spell.name == "Fireball"
    assert spell.level == 3
```

### Testing Error Cases

```python
def test_validation_errors():
    result = validate_spell(invalid_spell_data)
    assert result.is_error()

    error = result.error
    assert "Missing required field" in error.message
    assert error.field_name == "name"
    assert error.severity == ErrorSeverity.ERROR
```

### Testing Error Suggestions

```python
def test_error_suggestions():
    result = validate_spell({"type": "unknown_type"})
    error = result.error

    assert error.suggestions is not None
    assert any("Did you mean" in suggestion for suggestion in error.suggestions)
```

## Best Practices

### Error Design

1. **Be specific** - Include context about what failed and why
2. **Provide suggestions** - Help users understand how to fix issues
3. **Use appropriate severity** - Don't overuse ERROR/CRITICAL levels
4. **Include source context** - File paths, line numbers, content names
5. **Chain errors properly** - Maintain error context through processing pipeline

### Result Usage

1. **Handle both cases** - Always check `is_success()` and `is_error()`
2. **Use appropriate unwrap method** - `unwrap()`, `unwrap_or()`, `unwrap_or_else()`
3. **Chain operations** - Use `and_then()` and `map()` for pipeline processing
4. **Collect batch results** - Use `collect_results()` for multiple operations
5. **Log results consistently** - Use standardized logging patterns

### Performance Considerations

1. **Lazy error creation** - Only create detailed errors when needed
2. **Efficient error chaining** - Use `and_then()` to avoid intermediate allocations
3. **Cache error contexts** - Reuse context objects in batch operations
4. **Limit suggestion generation** - Don't generate excessive suggestions

## Common Pitfalls

### Antipatterns to Avoid

```python
# DON'T: Mix Result pattern with exceptions
def bad_validation(data: dict) -> Result[Content, ValidationError]:
    if not data:
        raise ValueError("Data is empty")  # Should return Error instead
    return Success(Content.model_validate(data))

# DON'T: Ignore error information
result = validate_content(data)
if result.is_error():
    return None  # Loses all error context

# DON'T: Create generic errors
return Error("Something went wrong")  # Not helpful

# DO: Use Result pattern consistently
def good_validation(data: dict) -> Result[Content, ValidationError]:
    if not data:
        return Error(create_validation_error("Data cannot be empty"))
    return validate_model(Content, data)

# DO: Preserve error information
result = validate_content(data)
return result.unwrap_or_else(lambda error: create_fallback_content(error))

# DO: Create informative errors
return Error(create_validation_error(
    message="Missing required field 'name'",
    field_name="name",
    suggestions=["Add 'name' field to content data"]
))
```

## Future Enhancements

The error handling system is designed for future extensibility:

- **Structured error codes** - Machine-readable error classification
- **Internationalization** - Multi-language error messages
- **Error recovery** - Automatic retry and fallback strategies
- **Metrics integration** - Error tracking and monitoring

This standardized approach provides a solid foundation for consistent, maintainable error handling across the entire codebase.
