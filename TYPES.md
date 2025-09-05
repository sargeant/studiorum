# Type Safety Patterns & Legitimate Type Ignores

This document catalogs legitimate `# type: ignore` patterns in the Studiorum codebase and when they should be used vs fixed.

## Legitimate Type Ignore Patterns

### 1. Protocol Type Tokens (`type-abstract`)

**Pattern**: Using `@runtime_checkable` protocols as type tokens for service registration/resolution

**Example**:

```python
# Service registration
container.register_service(
    ConfigurationProtocol,  # type: ignore[type-abstract]
    create_configuration_service,
    lifecycle=ServiceLifecycle.SINGLETON,
)

# Service resolution
service = await container.get_service(ConfigurationProtocol)  # type: ignore[type-abstract]
```

**Why Legitimate**:

- Protocols are `@runtime_checkable` and work correctly at runtime
- MyPy sees protocols as abstract and unsuitable as type tokens
- This is a fundamental limitation when building protocol-based DI systems
- The service container pattern requires protocols as runtime type identifiers

**Files**: Throughout service registration and access patterns
**Count**: ~20+ instances across `registration.py`, `access.py`, `context.py`, `factories.py`

### 2. Legacy Compatibility Bridges

**Pattern**: Bridging between old global singleton patterns and new service-based patterns

**Example**:

```python
# Legacy global container access
request_container_raw = await global_container.create_request_scope()
request_container = cast(RequestScopedContainer, request_container_raw)
```

**Why Legitimate**:

- Provides backward compatibility during service container migration
- Old global container doesn't have full typing
- Runtime behavior is correct, type system can't verify the cast
- Temporary pattern during architectural transition

**Files**: `container.py` - global container bridge functions
**Count**: 1-2 instances in compatibility layers

## Type Ignore Anti-Patterns (SHOULD BE FIXED)

### 1. Dictionary Type Coercion (`return-value,no-any-return`)

**Anti-Pattern**:

```python
# BAD - Missing proper type safety
self._instances: dict[type[Any], Any] = {}
return self._instances[protocol]  # type: ignore[return-value,no-any-return]
```

**Correct Solution**:

```python
# GOOD - Type-safe service registry
class TypedServiceRegistry:
    def get[S](self, protocol: type[S]) -> S:
        instance = self._instances[protocol]
        return cast(S, instance)  # With runtime validation
```

**Why Fixed**: Proper typing provides actual type safety without losing information

### 2. Complex Union Factory Dispatch (`call-arg`)

**Anti-Pattern**:

```python
# BAD - Complex union type can't be narrowed
factory: Callable[[], T] | Callable[[Container], T] | AsyncFactory[T]
result = factory(*args)  # type: ignore[call-arg]
```

**Correct Solution**:

```python
# GOOD - Separate dispatch methods
if isinstance(factory, AsyncServiceFactory):
    return await factory.create(self)
elif descriptor.requires_container():
    return await self._call_factory_with_container(factory)
else:
    return await self._call_simple_factory(factory)
```

**Why Fixed**: Proper dispatch eliminates type ambiguity without losing runtime flexibility

### 3. Protocol Implementation Issues (`return-value`)

**Anti-Pattern**:

```python
# BAD - Missing protocol method implementations
def validate_config(self) -> object:  # Wrong return type
    return {"success": True}

return LegacyWrapper()  # type: ignore[return-value]
```

**Correct Solution**:

```python
# GOOD - Proper protocol implementation
def validate_config(self) -> Result[ApplicationConfig, Any]:
    return Success(self._config)

return LegacyWrapper()  # No type ignore needed
```

**Why Fixed**: Proper protocol implementation provides type safety and correctness

## Result Pattern Best Practices

### Recommended Pattern: `isinstance()` + `unwrap()`

**Use this pattern for 90% of Result handling cases**:

```python
# ✅ RECOMMENDED: Type-checker friendly, clean, efficient
result = some_operation()
if isinstance(result, Error):
    logger.warning(f"Operation failed: {result.error}")
    return Error(f"Failed to process: {result.error}")

value = result.unwrap()  # Type checker knows this is safe
process(value)
```

**Why this is best**:
- Type checker can track control flow and knows `unwrap()` is safe
- No type ignores needed
- Clear and readable
- IDE autocomplete works correctly

### Advanced Pattern: Match Statements

**Use for complex multi-case logic or destructuring**:

```python
# ✅ Use match for complex branching or pattern extraction
match result:
    case Success(value) if value > 0:
        return process_positive(value)
    case Success(value):
        return process_negative(value)
    case Error(error) if "network" in error:
        return retry_with_backoff()
    case Error(error):
        return handle_error(error)
```

**When to use match**:
- Multiple conditions on success/error values
- Need to destructure complex nested Results
- Pattern matching adds clarity to complex logic

### Anti-Pattern: `is_error()` + Cast

**AVOID this pattern - leads to type ignore issues**:

```python
# ❌ ANTI-PATTERN: Requires casting and type ignores
if result.is_error():
    error = cast(Error, result)  # type: ignore[attr-defined]
    return Error(f"Failed: {error.error}")  # Verbose and error-prone
```

**Why to avoid**:
- Type checker can't track `is_error()` for narrowing
- Requires manual casting
- Often needs `# type: ignore` comments
- More verbose than isinstance

### Error Context Preservation

**Always preserve error context when propagating errors**:

```python
# ✅ GOOD: Preserve error context
if isinstance(result, Error):
    return result.with_context(
        "Failed to load adventure content",
        adventure_id=adventure_id,
        source=source_name
    )

# ❌ BAD: Lose error context
if isinstance(result, Error):
    return Error("Operation failed")  # Original error details lost!
```

### Quick Reference

| Pattern | Use Case | Type Safety | Readability |
|---------|----------|-------------|-------------|
| `isinstance() + unwrap()` | Simple branching (90% of cases) | ✅ Excellent | ✅ Excellent |
| `match` statements | Complex logic, destructuring | ✅ Excellent | ✅ Good for complex |
| `is_error() + cast` | Never - anti-pattern | ❌ Poor | ❌ Verbose |

## Documentation Guidelines

### When Type Ignore is Acceptable

1. **Fundamental Type System Limitation**: The type system cannot express the runtime relationship
2. **External Library Integration**: Third-party libraries with incomplete typing
3. **Legacy Compatibility**: Temporary bridges during architectural transitions
4. **Protocol Runtime Behavior**: Using protocols as runtime type tokens

### When Type Ignore Should Be Fixed

1. **Missing Type Information**: Can be fixed by adding proper type annotations
2. **Architectural Issues**: Complex unions, improper inheritance, missing generics
3. **Protocol Violations**: Methods not implementing required signatures
4. **Dictionary/Container Issues**: Can be fixed with proper generic containers

### Documentation Requirements

Every `# type: ignore` must include:

- **Specific error type**: `[type-abstract]`, `[return-value]`, etc.
- **Brief comment**: Why this ignore is necessary
- **Context**: Reference this document for detailed explanation

**Example**:

```python
service = await container.get_service(ConfigurationProtocol)  # type: ignore[type-abstract]
# ^ Protocol used as type token - see TYPES.md section 1
```

## Cleanup Strategy

### Priority Order (High to Low)

1. **P1-Critical**: Dictionary typing, union dispatch - Always fix these
2. **P2-Important**: Protocol implementation issues - Usually fixable
3. **P3-Optional**: Legacy bridges - Acceptable during transitions
4. **P4-Permanent**: Protocol type tokens - Legitimate architectural pattern

### Validation Process

1. **Identify Pattern**: Match against this document
2. **Assess Fixability**: Can the root cause be addressed?
3. **Document Decision**: Add clear comments and references
4. **Track Progress**: Monitor reduction in fixable type ignores

## Current Status

**Total Type Ignores**: ~50 (after P1-P2 cleanup)
**Legitimate**: ~30 (protocol type tokens, legacy bridges)
**Target**: <50 total with all fixable issues resolved

**P1 Result System**: 19→0 ignores eliminated ✅
**P2 Service Container**: 33→0 fixable ignores eliminated ✅

# Data Modeling Guidelines

## Choosing Between Dataclass and Pydantic

### Decision Framework

- **Performance critical** → `@dataclass`
- **Complex validation needed** → Pydantic `BaseModel`
- **API/JSON serialization** → Pydantic `BaseModel`
- **Simple value objects** → `@dataclass`
