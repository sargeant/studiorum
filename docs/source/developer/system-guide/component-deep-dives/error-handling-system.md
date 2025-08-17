# Error Handling System

The Error Handling System provides a comprehensive, type-safe approach to error management through the `Result[T, E]` pattern, structured error types, and standardized logging patterns that eliminate common error handling pitfalls.

## Overview

The error handling system addresses common issues in error management by providing:

- **Type-Safe Error Handling**: `Result[T, E]` pattern eliminates mixed return patterns and provides compile-time error checking
- **Structured Error Types**: Rich error context with suggestions, severity levels, and categorization
- **Consistent Logging**: Standardized logging patterns with rich error context and formatting
- **Error Chaining**: Monadic operations for complex processing pipelines without nested try-catch blocks
- **Backward Compatibility**: Seamless integration with existing validation systems and exception patterns
- **Batch Processing**: Efficient handling of multiple operations with error collection and reporting

```mermaid
graph TD
    A[Operation] --> B{Success/Error?}
    B -->|Success| C[Success[T, E]]
    B -->|Error| D[Error[T, E]]

    C --> E[Result[T, E]]
    D --> E

    E --> F[map/and_then Operations]
    F --> G[Error Chaining]
    G --> H[Structured Error Types]

    H --> I[ValidationError]
    H --> J[ProcessingError]
    H --> K[IOOperationError]
    H --> L[UnknownTypeError]

    I --> M[Standardized Logging]
    J --> M
    K --> M
    L --> M

    M --> N[Error Context & Suggestions]
    N --> O[Final Error Handling]
```

## Core Architecture

### Result[T, E] Pattern

The foundation of the error handling system is the `Result[T, E]` type that represents operations that can either succeed with a value of type `T` or fail with an error of type `E`:

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Callable

T = TypeVar("T")  # Success value type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped success type

class Result[T, E](ABC):
    """Abstract base class for Result types."""

    @abstractmethod
    def is_success(self) -> bool:
        """Return True if this is a Success result."""

    @abstractmethod
    def is_error(self) -> bool:
        """Return True if this is an Error result."""

    @abstractmethod
    def unwrap(self) -> T:
        """Return the success value or raise RuntimeError."""

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """Return the success value or a default if error."""

    @abstractmethod
    def unwrap_or_else(self, default_fn: Callable[[E], T]) -> T:
        """Return success value or result of calling default_fn with error."""

    @abstractmethod
    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform the success value using the given function."""

    @abstractmethod
    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another Result-returning operation on success."""
```

### Success and Error Types

The system provides concrete implementations for success and error cases:

```python
@dataclass(frozen=True)
class Success[T, E](Result[T, E]):
    """Represents a successful result containing a value."""
    value: T

    def is_success(self) -> bool:
        return True

    def unwrap(self) -> T:
        return self.value

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        return Success(fn(self.value))

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return fn(self.value)

@dataclass(frozen=True)
class Error[T, E](Result[T, E]):
    """Represents a failed result containing an error."""
    error: E

    def is_success(self) -> bool:
        return False

    def unwrap(self) -> T:
        raise RuntimeError(f"Called unwrap() on Error result: {self.error}")

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        return self  # Propagate error

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return self  # Propagate error
```

## Structured Error Types

The system provides a hierarchy of structured error types with rich context and suggestions:

### Base Error Structure

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any

class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # System cannot continue
    ERROR = "error"        # Operation failed but system can continue
    WARNING = "warning"    # Potential issue but operation succeeded
    INFO = "info"         # Informational message

class ErrorCategory(Enum):
    """Error categorization for analysis and handling."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    IO_OPERATION = "io_operation"
    UNKNOWN_TYPE = "unknown_type"
    CONFIGURATION = "configuration"

class BaseError(BaseModel):
    """Base class for all structured errors."""

    message: str = Field(description="Human-readable error message")
    category: ErrorCategory = Field(description="Error category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.ERROR)
    suggestions: list[str] | None = Field(None, description="Suggestions for resolution")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    timestamp: datetime = Field(default_factory=datetime.now)
```

### Specialized Error Types

**ValidationError - Content validation failures:**
```python
class ValidationError(BaseError):
    """Error during content validation."""

    category: ErrorCategory = ErrorCategory.VALIDATION
    field_name: str | None = Field(None, description="Field that failed validation")
    entry_type: str | None = Field(None, description="Type of entry being validated")
    source: str | None = Field(None, description="Source file or identifier")

    def add_suggestion(self, suggestion: str) -> "ValidationError":
        """Add a suggestion for fixing this error."""
        if self.suggestions is None:
            self.suggestions = []
        self.suggestions.append(suggestion)
        return self
```

**ProcessingError - Content processing failures:**
```python
class ProcessingError(BaseError):
    """Error during content processing."""

    category: ErrorCategory = ErrorCategory.PROCESSING
    entry_type: str | None = Field(None, description="Type of entry being processed")
    operation: str | None = Field(None, description="Processing operation that failed")

    def with_context(self, key: str, value: Any) -> "ProcessingError":
        """Add context information to the error."""
        self.context[key] = value
        return self
```

**IOOperationError - File system and network errors:**
```python
class IOOperationError(BaseError):
    """Error during I/O operations."""

    category: ErrorCategory = ErrorCategory.IO_OPERATION
    file_path: str | None = Field(None, description="File path involved in operation")
    operation_type: str | None = Field(None, description="Type of I/O operation")
```

**UnknownTypeError - Unknown content type handling:**
```python
class UnknownTypeError(BaseError):
    """Error when encountering unknown content types."""

    category: ErrorCategory = ErrorCategory.UNKNOWN_TYPE
    unknown_type: str = Field(description="The unknown type encountered")
    expected_types: list[str] | None = Field(None, description="Expected type options")

    def suggest_alternatives(self, alternatives: list[str]) -> "UnknownTypeError":
        """Suggest alternative types based on similarity."""
        suggestions = [f"Did you mean '{alt}'?" for alt in alternatives]
        self.suggestions = (self.suggestions or []) + suggestions
        return self
```

### Error Factory Functions

Convenient factory functions for creating structured errors:

```python
def create_validation_error(
    message: str,
    field_name: str | None = None,
    entry_type: str | None = None,
    source: str | None = None,
    suggestions: list[str] | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR
) -> ValidationError:
    """Create a validation error with structured information."""
    return ValidationError(
        message=message,
        field_name=field_name,
        entry_type=entry_type,
        source=source,
        suggestions=suggestions,
        severity=severity
    )

def create_processing_error(
    message: str,
    entry_type: str | None = None,
    operation: str | None = None,
    context: dict[str, Any] | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR
) -> ProcessingError:
    """Create a processing error with context information."""
    return ProcessingError(
        message=message,
        entry_type=entry_type,
        operation=operation,
        context=context or {},
        severity=severity
    )
```

## Error Chaining and Monadic Operations

The Result pattern enables clean error chaining without nested try-catch blocks:

### Basic Chaining

```python
def process_spell_data(data: dict) -> Result[ProcessedSpell, ValidationError]:
    """Process spell data through multiple validation steps."""
    return (
        validate_required_field(data, "name")
        .and_then(lambda name: validate_spell_level(data.get("level", 1)))
        .and_then(lambda level: validate_spell_school(data.get("school")))
        .and_then(lambda school: create_processed_spell(data))
    )

# Usage - any step failure stops the chain
result = process_spell_data(spell_data)
spell = result.unwrap_or_else(lambda error: create_fallback_spell(error))
```

### Value Transformation

```python
def enrich_spell_data(spell: Spell) -> Result[EnrichedSpell, ProcessingError]:
    """Transform successful results without handling errors."""
    return (
        validate_spell(spell)
        .map(lambda s: add_metadata(s))
        .map(lambda s: calculate_dependencies(s))
        .map(lambda s: EnrichedSpell.from_spell(s))
    )
```

### Error Transformation

```python
def convert_validation_to_processing_error(
    result: Result[T, ValidationError]
) -> Result[T, ProcessingError]:
    """Convert error types while preserving success values."""
    return result.map_error(lambda validation_error:
        create_processing_error(
            message=f"Processing failed: {validation_error.message}",
            context={"original_error": validation_error}
        )
    )
```

## Batch Processing and Error Collection

The system provides efficient batch processing with comprehensive error collection:

### Collect Results Pattern

```python
def collect_results[T, E](results: list[Result[T, E]]) -> Result[list[T], list[E]]:
    """
    Collect multiple Results into a single Result.

    If all Results are successful, returns Success with list of all values.
    If any Results are errors, returns Error with list of all errors.
    """
    successes: list[T] = []
    errors: list[E] = []

    for result in results:
        if result.is_success():
            successes.append(result.unwrap())
        else:
            errors.append(result.error)

    if errors:
        return Error(errors)
    return Success(successes)
```

### Batch Validation Example

```python
def validate_spell_batch(spell_data_list: list[dict]) -> Result[list[Spell], list[ValidationError]]:
    """Validate multiple spells, collecting all errors."""
    results = [validate_spell_data(data) for data in spell_data_list]
    return collect_results(results)

# Usage - get either all spells or all errors
batch_result = validate_spell_batch(spell_data_list)
if batch_result.is_success():
    spells = batch_result.unwrap()
    logger.info(f"Successfully validated {len(spells)} spells")
else:
    errors = batch_result.error
    logger.error(f"Batch validation failed with {len(errors)} errors")
    for error in errors[:5]:  # Log first 5 errors
        logger.error(f"  {error.message}")
```

### Partial Success Handling

```python
def process_content_with_fallbacks(
    content_list: list[dict]
) -> tuple[list[ProcessedContent], list[ValidationError]]:
    """Process content, separating successes and failures."""
    successes = []
    failures = []

    for content_data in content_list:
        result = process_content(content_data)
        if result.is_success():
            successes.append(result.unwrap())
        else:
            failures.append(result.error)

    return successes, failures

# Usage - continue processing with partial success
processed_content, errors = process_content_with_fallbacks(content_list)
logger.info(f"Processed {len(processed_content)} items, {len(errors)} failed")
```

## Standardized Logging Integration

The error handling system integrates with simple logging for consistent error reporting:

### Simple Logging Pattern

```python
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

def log_result_pattern[T, E](
    result: Result[T, E],
    operation: str,
    content_name: str | None = None
) -> None:
    """Log a Result with simple formatting."""
    if result.is_success():
        logger.info(f"{operation} completed successfully" +
                   (f" for {content_name}" if content_name else ""))
    else:
        error = result.error
        logger.error(f"{operation} failed" +
                    (f" for {content_name}" if content_name else "") +
                    f": {error.message}")

    def log_error(self, error: BaseError, context: ErrorContext | None = None) -> None:
        """Log a structured error with full context."""
        message_parts = [
            f"Error: {error.message}",
            f"Category: {error.category.value}",
            f"Severity: {error.severity.value}"
        ]

        if error.suggestions:
            message_parts.append(f"Suggestions: {', '.join(error.suggestions)}")

        if context:
            message_parts.append(f"Context: {context}")

        log_message = " | ".join(message_parts)

        if error.severity == ErrorSeverity.CRITICAL:
            self.critical(log_message)
        elif error.severity == ErrorSeverity.ERROR:
            self.error(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            self.warning(log_message)
        else:
            self.info(log_message)
```

### Error Logging Context

#### Simple Context Pattern

```python
def log_with_context(
    logger: Logger,
    operation: str,
    content_name: str | None = None,
    file_path: str | None = None
) -> None:
    """Log with context information included in message."""
    context_parts = []
    if content_name:
        context_parts.append(f"content={content_name}")
    if file_path:
        context_parts.append(f"file={file_path}")

    context_str = f" ({', '.join(context_parts)})" if context_parts else ""
    logger.info(f"Starting {operation}{context_str}")
        additional_info=additional_info
    )

    try:
        yield context
    except Exception as e:
        error = create_processing_error(
            message=f"Unexpected error in {operation}: {e}",
            operation=operation,
            context={"exception_type": type(e).__name__}
        )
        logger.log_error(error, context)
        raise
```

### Usage Example

```python
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

def process_spell_with_logging(spell_data: dict, source: str) -> Result[Spell, ValidationError]:
    """Process spell with error logging."""
    spell_name = spell_data.get("name", "unknown")
    logger.info(f"Starting spell_processing for {spell_name} from {source}")

    result = validate_spell_data(spell_data)

    if result.is_success():
        logger.info(f"spell_processing completed successfully for {spell_name}")
    else:
        error = result.error
        logger.error(f"spell_processing failed for {spell_name}: {error.message}")

    return result
```

## Advanced Error Handling Patterns

### Try Result Pattern

Convert exception-based code to Result pattern:

```python
def try_result[T](fn: Callable[[], T]) -> Result[T, Exception]:
    """Execute a function and wrap result/exception in Result."""
    try:
        return Success(fn())
    except Exception as e:
        return Error(e)

# Usage
result = try_result(lambda: parse_json_file(file_path))
parsed_data = result.unwrap_or_else(lambda e: {})
```

### Result Validation Pattern

Integrate with Pydantic model validation:

```python
def validate_model[T](
    model_class: type[T],
    data: dict[str, Any],
    source: str | None = None
) -> Result[T, ValidationError]:
    """Validate data against Pydantic model."""
    try:
        model = model_class.model_validate(data)
        return Success(model)
    except PydanticValidationError as e:
        validation_error = create_validation_error(
            message=f"Model validation failed: {e}",
            entry_type=model_class.__name__,
            source=source,
            suggestions=["Check required fields", "Verify data types"]
        )
        return Error(validation_error)

# Usage
result = validate_model(Spell, spell_data, "spells.json")
spell = result.unwrap_or_else(lambda error: create_default_spell())
```

### Error Recovery Patterns

```python
def with_fallback[T, E](
    primary: Result[T, E],
    fallback_fn: Callable[[E], Result[T, E]]
) -> Result[T, E]:
    """Try primary operation, fall back on error."""
    if primary.is_success():
        return primary
    return fallback_fn(primary.error)

def retry_with_backoff[T, E](
    operation: Callable[[], Result[T, E]],
    max_attempts: int = 3,
    backoff_seconds: float = 1.0
) -> Result[T, E]:
    """Retry operation with exponential backoff."""
    for attempt in range(max_attempts):
        result = operation()
        if result.is_success():
            return result

        if attempt < max_attempts - 1:
            time.sleep(backoff_seconds * (2 ** attempt))

    return result  # Return last failure

# Usage
result = retry_with_backoff(
    lambda: load_data_from_network(url),
    max_attempts=3,
    backoff_seconds=1.0
)
```

## Legacy Integration and Migration

### Backward Compatibility

The system provides seamless integration with existing validation patterns:

```python
def migrate_validation_result(legacy_result: Any) -> Result[Any, ValidationError]:
    """Convert legacy ValidationResult to Result pattern."""
    if hasattr(legacy_result, 'is_valid') and legacy_result.is_valid:
        return Success(legacy_result.value)
    else:
        error = create_validation_error(
            message=getattr(legacy_result, 'error_message', 'Validation failed'),
            suggestions=getattr(legacy_result, 'suggestions', None)
        )
        return Error(error)

def create_compatibility_wrapper(new_validator: Any) -> Any:
    """Create wrapper for gradual migration."""
    class CompatibilityWrapper:
        def __init__(self, validator):
            self.validator = validator

        def validate_entry_structure(self, context):
            result = self.validator.validate(context)
            # Convert Result back to legacy format
            if result.is_success():
                return LegacyValidationResult(is_valid=True, value=result.unwrap())
            else:
                return LegacyValidationResult(
                    is_valid=False,
                    error_message=result.error.message
                )

    return CompatibilityWrapper(new_validator)
```

### Exception Bridge Pattern

Bridge between Result pattern and exception-based code:

```python
def result_to_exception[T, E](result: Result[T, E]) -> T:
    """Convert Result to exception-based pattern."""
    if result.is_success():
        return result.unwrap()
    else:
        error = result.error
        if isinstance(error, BaseError):
            raise Exception(f"{error.category.value}: {error.message}")
        else:
            raise Exception(str(error))

def exception_to_result[T](fn: Callable[[], T]) -> Result[T, Exception]:
    """Convert exception-based function to Result."""
    return try_result(fn)

# Usage for gradual migration
def legacy_function_wrapper(data: dict) -> dict:
    """Wrapper that maintains legacy interface."""
    result = validate_content_new(data)
    return result_to_exception(result)  # Maintains existing interface
```

## Testing Error Handling

### Testing Success Cases

```python
def test_successful_validation():
    """Test successful validation path."""
    valid_data = {"name": "Fireball", "level": 3, "school": "Evocation"}
    result = validate_spell_data(valid_data)

    assert result.is_success()
    assert not result.is_error()

    spell = result.unwrap()
    assert spell.name == "Fireball"
    assert spell.level == 3

def test_success_chaining():
    """Test chaining operations on success."""
    result = (
        Success(5)
        .map(lambda x: x * 2)
        .and_then(lambda x: Success(x + 1))
    )

    assert result.is_success()
    assert result.unwrap() == 11
```

### Testing Error Cases

```python
def test_validation_errors():
    """Test error case handling."""
    invalid_data = {"level": 10}  # Missing name, invalid level
    result = validate_spell_data(invalid_data)

    assert result.is_error()
    assert not result.is_success()

    error = result.error
    assert isinstance(error, ValidationError)
    assert "name" in error.message.lower()
    assert error.severity == ErrorSeverity.ERROR

def test_error_chaining():
    """Test that errors propagate through chains."""
    error = create_validation_error("Initial error")
    result = (
        Error(error)
        .map(lambda x: x * 2)  # Should not execute
        .and_then(lambda x: Success(x + 1))  # Should not execute
    )

    assert result.is_error()
    assert result.error.message == "Initial error"
```

### Testing Error Context and Suggestions

```python
def test_error_suggestions():
    """Test error suggestion generation."""
    result = validate_spell_school("Evokation")  # Typo
    error = result.error

    assert error.suggestions is not None
    assert any("Did you mean 'Evocation'?" in suggestion
              for suggestion in error.suggestions)

def test_batch_error_collection():
    """Test batch processing error collection."""
    data_list = [
        {"name": "Valid", "level": 1},
        {"name": "Invalid", "level": 10},  # Invalid level
        {"level": 2}  # Missing name
    ]

    result = validate_spell_batch(data_list)
    assert result.is_error()

    errors = result.error
    assert len(errors) == 2
    assert any("level" in error.message for error in errors)
    assert any("name" in error.message for error in errors)
```

### Testing Logging Integration

```python
def test_error_logging(caplog):
    """Test error logging integration."""
    logger = get_logger("test")
    error = create_validation_error(
        message="Test error",
        field_name="test_field",
        suggestions=["Fix the test"]
    )

    # Log error with context
    logger.error(f"test_operation failed: {error.message}")
    if error.suggestions:
        logger.error(f"Suggestions: {'; '.join(error.suggestions)}")

    assert "Test error" in caplog.text
    assert "validation" in caplog.text
    assert "Fix the test" in caplog.text
```

## Best Practices

### Error Message Design

```python
# Good: Specific, actionable error messages
error = create_validation_error(
    message="Spell level 10 is invalid for PHB spells",
    field_name="level",
    entry_type="spell",
    source="phb.json",
    suggestions=[
        "Use a level between 1 and 9 for standard spells",
        "Check if this is a homebrew spell requiring custom handling"
    ]
)

# Avoid: Generic or unhelpful messages
error = create_validation_error("Invalid value")  # Too generic
error = create_validation_error("Error occurred")  # No context
```

### Result Chain Design

```python
# Good: Clear, focused operations
def process_spell_data(data: dict) -> Result[ProcessedSpell, ValidationError]:
    return (
        validate_required_fields(data)
        .and_then(lambda d: validate_spell_level(d))
        .and_then(lambda d: validate_spell_school(d))
        .and_then(lambda d: create_processed_spell(d))
    )

# Avoid: Complex, unclear chains
def bad_processing(data: dict) -> Result[Any, Any]:
    return (
        process_something(data)
        .map(lambda x: complex_transformation(x, another_param))
        .and_then(lambda y: maybe_do_something_else(y) if condition else Success(y))
    )  # Too complex, unclear intent
```

### Error Handling Strategy

```python
# Good: Handle both cases explicitly
result = validate_spell(data)
if result.is_success():
    spell = result.unwrap()
    return process_spell(spell)
else:
    error = result.error
    logger.error(f"Validation failed: {error.message}")
    return create_fallback_spell(error)

# Good: Use appropriate unwrap method
spell = result.unwrap_or_else(lambda error: create_default_spell())

# Avoid: Unsafe unwrapping
spell = result.unwrap()  # May crash if error
```

### Performance Considerations

```python
# Good: Lazy error creation
def validate_complex_data(data: dict) -> Result[ValidData, ValidationError]:
    if not data:
        return Error(create_validation_error("Data cannot be empty"))

    # Only create expensive error context if needed
    if "required_field" not in data:
        return Error(create_validation_error(
            message="Missing required field",
            context=create_expensive_context(data)  # Only called on error
        ))

    return Success(ValidData(data))

# Good: Efficient batch processing
def process_large_batch(items: list[dict]) -> Result[list[ProcessedItem], list[ValidationError]]:
    # Process in chunks to manage memory
    chunk_size = 100
    all_results = []

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        chunk_results = [process_item(item) for item in chunk]
        all_results.extend(chunk_results)

    return collect_results(all_results)
```

## Future Enhancements

### Planned Features

**Error Code System:**
```python
class ErrorCode(Enum):
    """Machine-readable error codes for automated handling."""
    VALIDATION_MISSING_FIELD = "V001"
    VALIDATION_INVALID_TYPE = "V002"
    PROCESSING_UNKNOWN_ENTRY = "P001"
    IO_FILE_NOT_FOUND = "I001"

class ValidationError(BaseError):
    error_code: ErrorCode = Field(description="Machine-readable error code")
```

**Internationalization Support:**
```python
class LocalizedError(BaseError):
    """Error with internationalization support."""
    message_key: str = Field(description="Message key for translation")
    message_params: dict[str, Any] = Field(default_factory=dict)

    def get_localized_message(self, locale: str = "en") -> str:
        """Get localized error message."""
        return translate(self.message_key, self.message_params, locale)
```

**Error Recovery Strategies:**
```python
class RecoverableError(BaseError):
    """Error with automatic recovery suggestions."""
    recovery_strategies: list[Callable[[], Result[Any, BaseError]]] = Field(default_factory=list)

    def attempt_recovery(self) -> Result[Any, BaseError]:
        """Attempt automatic error recovery."""
        for strategy in self.recovery_strategies:
            result = strategy()
            if result.is_success():
                return result
        return Error(self)
```

## Enhanced Architecture Error Handling

### Overview

The enhanced architecture error handling provides structured exceptions with rich context for the new architectural components introduced in Phase 4. This system complements the Result[T, E] pattern with traditional exception handling where appropriate.

**Location**: `src/dnd5e/core/errors/architecture_errors.py`

### Architecture Error Hierarchy

```python
class ArchitectureError(Exception):
    """Base exception for architecture-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        base_message = super().__str__()
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base_message} (Context: {context_str})"
        return base_message
```

### Specific Error Types

**Content Source Errors:**
```python
class ContentSourceError(ArchitectureError):
    """Errors related to content source operations."""

    def __init__(self, message: str, source_location: str = "unknown",
                 source_type: str = "unknown", **context):
        context.update({
            "source_location": source_location,
            "source_type": source_type
        })
        super().__init__(message, context)

class ContentValidationError(ContentSourceError):
    """Errors during content validation."""

    def __init__(self, message: str, validation_errors: list[str] | None = None, **context):
        if validation_errors:
            context["validation_errors"] = validation_errors
        super().__init__(message, **context)

class ContentLoadingError(ContentSourceError):
    """Errors during content loading."""

    def __init__(self, message: str, items_processed: int = 0,
                 items_failed: int = 0, **context):
        context.update({
            "items_processed": items_processed,
            "items_failed": items_failed
        })
        super().__init__(message, **context)
```

**Reference System Errors:**
```python
class ReferenceTrackingError(ArchitectureError):
    """Errors related to reference tracking operations."""

    def __init__(self, message: str, reference_type: str = "unknown",
                 reference_name: str = "unknown", **context):
        context.update({
            "reference_type": reference_type,
            "reference_name": reference_name
        })
        super().__init__(message, context)
```

**Configuration Errors:**
```python
class ConfigurationError(ArchitectureError):
    """Errors related to configuration hierarchy."""

    def __init__(self, message: str, config_key: str = "unknown",
                 config_source: str = "unknown", **context):
        context.update({
            "config_key": config_key,
            "config_source": config_source
        })
        super().__init__(message, context)
```

**Template System Errors:**
```python
class TemplateCompositionError(ArchitectureError):
    """Errors related to template composition."""

    def __init__(self, message: str, template_name: str = "unknown",
                 component_name: str = "unknown", **context):
        context.update({
            "template_name": template_name,
            "component_name": component_name
        })
        super().__init__(message, context)
```

### Error Handling Decorators

**Automatic Error Wrapping:**
```python
def handle_content_source_error(func):
    """Decorator to handle content source errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ContentSourceError:
            # Re-raise architecture errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions in ContentSourceError
            source_location = getattr(args[0], 'location', 'unknown') if args else 'unknown'
            source_type = type(args[0]).__name__ if args else 'unknown'

            raise ContentSourceError(
                f"Unexpected error in content source operation: {e}",
                source_location=source_location,
                source_type=source_type,
                original_error=str(e),
                original_type=type(e).__name__
            ) from e
    return wrapper

@handle_content_source_error
def load_content_from_file(self, file_path: Path) -> list[BaseContent]:
    """Load content with automatic error wrapping."""
    return self._parse_file(file_path)
```

**Reference Tracking Error Handling:**
```python
def handle_reference_tracking_error(func):
    """Decorator to handle reference tracking errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ReferenceTrackingError:
            raise
        except Exception as e:
            reference_type = kwargs.get('content_type', 'unknown')
            reference_name = kwargs.get('name', 'unknown')

            raise ReferenceTrackingError(
                f"Unexpected error in reference tracking: {e}",
                reference_type=reference_type,
                reference_name=reference_name,
                original_error=str(e),
                original_type=type(e).__name__
            ) from e
    return wrapper
```

### User-Friendly Error Formatting

```python
def format_error_for_user(error: ArchitectureError) -> str:
    """Format an architecture error for user-friendly display."""
    if isinstance(error, ContentValidationError):
        return f"Content validation failed: {error}"
    elif isinstance(error, ContentLoadingError):
        return f"Content loading failed: {error}"
    elif isinstance(error, ContentSourceError):
        return f"Content source error: {error}"
    elif isinstance(error, ReferenceTrackingError):
        return f"Reference tracking error: {error}"
    elif isinstance(error, ConfigurationError):
        return f"Configuration error: {error}"
    elif isinstance(error, TemplateCompositionError):
        return f"Template error: {error}"
    else:
        return f"Architecture error: {error}"

# Usage
try:
    content = source.load()
except ArchitectureError as e:
    user_message = format_error_for_user(e)
    print(user_message)

    # Log with full context
    log_architecture_error(e, logger)
```

### Structured Logging Integration

```python
def log_architecture_error(error: ArchitectureError, logger=None):
    """Log an architecture error with full context."""
    if logger is None:
        from ..logging import get_logger
        logger = get_logger(__name__)

    # Log the error with full context
    error_type = type(error).__name__
    logger.error(f"{error_type}: {error}")

    if error.context:
        logger.error(f"Error context: {error.context}")

    # Log the original exception if available
    if hasattr(error, '__cause__') and error.__cause__:
        logger.error(f"Original exception: {error.__cause__}")
```

### Best Practices

**Error Context Enrichment:**
```python
# Provide rich context for debugging
raise ContentSourceError(
    "Failed to parse JSON file",
    source_location=str(file_path),
    source_type="file",
    file_size=file_path.stat().st_size,
    encoding_detected="utf-8",
    line_number=42,
    suggested_fix="Check JSON syntax around line 42"
)
```

**Graceful Degradation:**
```python
try:
    primary_content = primary_source.load()
except ContentSourceError as e:
    logger.warning(f"Primary source failed: {e}")
    log_architecture_error(e, logger)

    # Attempt fallback
    try:
        fallback_content = fallback_source.load()
        logger.info("Successfully loaded from fallback source")
        return fallback_content
    except ContentSourceError as fallback_error:
        # Chain errors for full context
        raise ContentSourceError(
            "Both primary and fallback sources failed",
            primary_error=str(e),
            fallback_error=str(fallback_error),
            suggested_action="Check source configurations and file permissions"
        ) from e
```

### Integration Roadmap

**Metrics and Monitoring:**
- Error rate tracking and alerting
- Performance impact monitoring
- Error pattern analysis and reporting

**Advanced Logging:**
- Structured logging with JSON output
- Error correlation and tracing
- Log aggregation and analysis

**IDE Integration:**
- Enhanced type hints and IntelliSense support
- Error suggestion plugins
- Debugging tools for Result chains

## Conclusion

The Error Handling System provides a comprehensive foundation for reliable error management in the 5e2pdf codebase. Its key advantages include:

- **Type Safety**: Compile-time error checking prevents common runtime errors
- **Consistency**: Standardized patterns across all modules and operations
- **Rich Context**: Detailed error information with suggestions and categorization
- **Composability**: Clean error chaining without nested exception handling
- **Maintainability**: Clear error propagation and handling patterns
- **Performance**: Efficient batch processing and lazy error creation

The system's monadic design enables sophisticated error handling workflows while maintaining simplicity and type safety. This foundation ensures reliable error management across the entire application lifecycle, from content validation to PDF generation.
