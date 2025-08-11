# Error Handling API Reference

The error handling API provides standardized Result[T, E] patterns and structured error types for consistent error handling across the codebase.

## Core Classes

### Result[T, E]

```{eval-rst}
.. autoclass:: dnd5e.core.result.Result
   :members:
   :show-inheritance:
```

### Success[T, E]

```{eval-rst}
.. autoclass:: dnd5e.core.result.Success
   :members:
   :show-inheritance:
```

### Error[T, E]

```{eval-rst}
.. autoclass:: dnd5e.core.result.Error
   :members:
   :show-inheritance:
```

## Error Types

### BaseError

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.BaseError
   :members:
   :show-inheritance:
```

### ValidationError

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.ValidationError
   :members:
   :show-inheritance:
```

### ProcessingError

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.ProcessingError
   :members:
   :show-inheritance:
```

### UnknownTypeError

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.UnknownTypeError
   :members:
   :show-inheritance:
```

### IOOperationError

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.IOOperationError
   :members:
   :show-inheritance:
```

## Error Context

### ErrorContext

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.ErrorContext
   :members:
   :show-inheritance:
```

## Enumerations

### ErrorSeverity

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.ErrorSeverity
   :members:
   :show-inheritance:
```

### ErrorCategory

```{eval-rst}
.. autoclass:: dnd5e.core.error_types.ErrorCategory
   :members:
   :show-inheritance:
```

## Logging

### Logger Functions

```{eval-rst}
.. autofunction:: dnd5e.core.logging.get_logger

.. autofunction:: dnd5e.core.logging.setup_logging
```

## Validation

### Validation Functions

```{eval-rst}
.. autofunction:: dnd5e.core.validation_result.validate_model

.. autofunction:: dnd5e.core.validation_result.validate_required_field
```

### StandardizedEntryValidator

```{eval-rst}
.. autoclass:: dnd5e.core.standardized_validation.StandardizedEntryValidator
   :members:
   :show-inheritance:
```

## Utility Functions

### Result Utilities

```{eval-rst}
.. autofunction:: dnd5e.core.result.collect_results

.. autofunction:: dnd5e.core.result.try_result
```

### Error Creation

```{eval-rst}
.. autofunction:: dnd5e.core.error_types.create_validation_error

.. autofunction:: dnd5e.core.error_types.create_processing_error

.. autofunction:: dnd5e.core.error_types.create_unknown_type_error
```


## Migration Utilities

### Compatibility Functions

```{eval-rst}
.. autofunction:: dnd5e.core.standardized_validation.migrate_validation_result

.. autofunction:: dnd5e.core.standardized_validation.create_compatibility_wrapper
```

## Usage Examples

### Basic Result Pattern

```python
from dnd5e.core.result import Result, Success, Error
from dnd5e.core.error_types import create_validation_error

def validate_spell_level(level: int) -> Result[int, ValidationError]:
    if not 1 <= level <= 9:
        return Error(create_validation_error(
            message=f"Spell level {level} is invalid",
            field_name="level",
            suggestions=["Use a level between 1 and 9"]
        ))
    return Success(level)

# Usage
result = validate_spell_level(3)
if result.is_success():
    level = result.unwrap()
    print(f"Valid level: {level}")
else:
    error = result.error
    print(f"Error: {error.message}")
```

### Error Chaining

```python
def process_spell_data(data: dict) -> Result[ProcessedSpell, ValidationError]:
    return (
        validate_required_field(data, "name")
        .and_then(lambda name: validate_spell_level(data.get("level", 1)))
        .and_then(lambda level: create_processed_spell(data))
    )
```

### Batch Processing

```python
from dnd5e.core.result import collect_results

spell_data_list = [{"name": "Fireball", "level": 3}, {"name": "Magic Missile", "level": 1}]
results = [validate_spell_data(data) for data in spell_data_list]
batch_result = collect_results(results)

if batch_result.is_success():
    spells = batch_result.unwrap()
    print(f"Validated {len(spells)} spells")
else:
    errors = batch_result.error
    print(f"Found {len(errors)} validation errors")
```

### Logging Integration

```python
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

# Log validation process for Fireball
logger.info("Starting spell_validation for Fireball")
result = validate_spell_data(spell_data)
if result.is_success():
    logger.info("spell_validation completed successfully for Fireball")
else:
    error = result.error
    logger.error(f"spell_validation failed for Fireball: {error.message}")
```

## Type Safety

The error handling API is fully type-safe with Python 3.12+ support:

```python
# Type hints are preserved through the Result chain
def typed_validation(data: dict[str, Any]) -> Result[ValidatedSpell, ValidationError]:
    # Type checker knows this returns Result[ValidatedSpell, ValidationError]
    return validate_model(Spell, data).and_then(enrich_spell_data)

# Batch operations maintain type safety
def batch_validation(data_list: list[dict]) -> Result[list[ValidatedSpell], list[ValidationError]]:
    results: list[Result[ValidatedSpell, ValidationError]] = [
        validate_spell_data(data) for data in data_list
    ]
    return collect_results(results)
```

## Best Practices

### Error Construction

Always provide helpful error messages with context:

```python
# Good: Specific error with suggestions
error = create_validation_error(
    message="Spell level must be between 1 and 9",
    field_name="level",
    entry_type="spell",
    source="phb.json",
    suggestions=["Check spell level value", "Valid levels are 1-9"]
)

# Avoid: Generic errors without context
error = create_validation_error("Invalid level")
```

### Result Handling

Always handle both success and error cases:

```python
# Good: Handle both cases
result = validate_spell(data)
if result.is_success():
    spell = result.unwrap()
    process_spell(spell)
else:
    error = result.error
    logger.error(f"Validation failed: {error.message}")
    return create_fallback_spell()

# Avoid: Only handling success case
spell = validate_spell(data).unwrap()  # May crash on error
```

### Error Propagation

Use appropriate unwrap methods based on your needs:

```python
# When you need the value or want to crash
spell = result.unwrap()

# When you have a reasonable default
spell = result.unwrap_or(create_default_spell())

# When you need to handle the error
spell = result.unwrap_or_else(lambda error: create_error_spell(error))
```
