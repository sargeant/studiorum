# Code Review Checklist: Data Modeling Updates

**Version**: 1.0
**Date**: 2025-08-25
**Integration**: Extends existing code review processes with data modeling guidance

## Data Modeling Review Items

### Architecture Alignment ⚙️

**Decision Framework Compliance**:
- [ ] **Pattern Choice**: Follows dataclass vs Pydantic decision framework?
  - Performance critical → dataclass with `slots=True`
  - Complex validation → Pydantic with `ConfigDict`
  - JSON serialization → Pydantic `BaseModel`
  - Simple value objects → `@dataclass`

- [ ] **Rationale Documented**: PR description explains choice reasoning?
  - Reference decision criteria used
  - Note performance considerations
  - Explain validation requirements

- [ ] **Future Evolution**: Considers likely changes (validation, serialization)?
  - Document migration path if requirements change
  - Consider API stability needs

**Performance Considerations**:
- [ ] **Hot Path Analysis**: Performance impact assessed for critical paths?
  - Dataclass used for high-frequency instantiation
  - Pydantic overhead justified by validation needs
  - Benchmarks provided for performance-critical changes

- [ ] **Memory Optimization**: Appropriate memory patterns used?
  - `slots=True` for performance-critical dataclasses
  - `frozen=True` for immutable types
  - Proper default factory usage for mutable defaults

### Implementation Quality 🔧

**Type Safety**:
- [ ] **Field Types**: All fields properly annotated with specific types?
  - No `Any` types without justification
  - Use union types (`str | None`) instead of `Optional`
  - Generic types properly parameterized

- [ ] **Validation Logic**: Validation comprehensive but not over-engineered?
  - Simple constraints use `Field()` parameters
  - Complex logic uses validators appropriately
  - Cross-field validation in `@model_validator`

**Error Handling**:
- [ ] **Clear Messages**: Validation errors provide actionable feedback?
  - Specific error descriptions
  - Include expected format/range
  - User-friendly language for external APIs

- [ ] **Exception Types**: Appropriate exception types raised?
  - `ValueError` for data validation issues
  - `TypeError` for type-related problems
  - Custom exceptions for domain-specific errors

**Documentation**:
- [ ] **Field Documentation**: Complex fields include descriptions?
  - `Field(description="...")` for Pydantic models
  - Docstring field descriptions for dataclasses
  - Usage examples for complex types

- [ ] **Class Documentation**: Purpose and usage clearly documented?
  - When to use this type
  - Key constraints and rules
  - Integration patterns

### Consistency Standards 📏

**Naming Conventions**:
- [ ] **Field Names**: Follow `snake_case` convention?
- [ ] **Class Names**: Use `PascalCase` convention?
- [ ] **Boolean Fields**: Use clear positive/negative naming?
  - `is_active` instead of `inactive`
  - `has_permission` instead of `no_permission`

**Pattern Consistency**:
- [ ] **Similar Types**: Consistent with existing patterns in module/package?
  - Same validation approaches for similar data
  - Consistent field ordering and grouping
  - Matching serialization patterns

- [ ] **Integration Points**: Compatible with existing systems?
  - Database models alignment
  - API contract consistency
  - MCP tool compatibility

## Implementation Patterns Review

### Dataclass Implementation ✅

**Structure Review**:
```python
# Check for these patterns
@dataclass(frozen=True, slots=True)  # Performance optimization
class ReviewExample:
    """Clear purpose documentation."""

    # Required fields first
    name: str
    value: int

    # Optional fields with proper defaults
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Minimal validation only."""
        if self.value < 0:
            raise ValueError("Value must be non-negative")
```

**Review Checklist**:
- [ ] **Decorator Parameters**: Appropriate `frozen`, `slots` usage?
- [ ] **Default Values**: Mutable defaults use `field(default_factory=...)`?
- [ ] **Validation Scope**: `__post_init__` validation kept minimal?
- [ ] **Method Placement**: Business logic methods appropriate for value object?

### Pydantic Implementation ✅

**Structure Review**:
```python
# Check for these patterns
class ReviewExample(BaseModel):
    """Clear business purpose."""

    model_config = ConfigDict(
        extra="forbid",          # Strict validation
        use_enum_values=True,    # For enum fields
        validate_assignment=True # Runtime validation
    )

    # Fields with proper constraints
    name: str = Field(..., min_length=1, max_length=100, description="Entity name")
    category: CategoryEnum = Field(..., description="Entity category")

    @field_validator('name')
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize field value."""
        return v.strip().title()

    @model_validator(mode='after')
    def validate_business_rules(self) -> Self:
        """Cross-field business validation."""
        # Business logic here
        return self
```

**Review Checklist**:
- [ ] **ConfigDict**: Includes `extra="forbid"` for strict validation?
- [ ] **Field Constraints**: Uses `Field()` parameters effectively?
- [ ] **Validators**: Appropriate validator types and placement?
- [ ] **Return Types**: Validators return correct types?

## Common Anti-Patterns 🚫

### Dataclass Anti-Patterns

❌ **Mutable Default Values**:
```python
@dataclass
class Bad:
    items: list = []  # Shared across instances!

# Should be:
@dataclass
class Good:
    items: list = field(default_factory=list)
```

❌ **Complex Validation Logic**:
```python
@dataclass
class Bad:
    def __post_init__(self):
        # 20 lines of validation - use Pydantic instead
        pass
```

❌ **Missing Performance Optimization**:
```python
@dataclass  # Missing slots=True for performance-critical type
class PerformanceCritical:
    pass
```

### Pydantic Anti-Patterns

❌ **Missing Strict Validation**:
```python
class Bad(BaseModel):  # Missing ConfigDict
    name: str

# Should be:
class Good(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
```

❌ **Overly Permissive Types**:
```python
class Bad(BaseModel):
    data: Any  # Loses type safety

# Should be:
class Good(BaseModel):
    data: dict[str, str] | list[int]  # Specific union type
```

❌ **Validator Misuse**:
```python
class Bad(BaseModel):
    @field_validator('simple_field')
    @classmethod
    def complex_validation(cls, v):
        # Should use Field() constraints instead
        return v
```

## Integration Review Points

### API Boundaries 🌐

**Request/Response Models**:
- [ ] **Strict Validation**: API models use `extra="forbid"`?
- [ ] **Clear Contracts**: Request/response shapes well-defined?
- [ ] **Error Handling**: Validation errors properly handled and returned?
- [ ] **Documentation**: API model fields documented for external users?

### Configuration Classes ⚙️

**Environment Integration**:
- [ ] **Environment Variables**: Proper `env_prefix` configuration?
- [ ] **Default Values**: Sensible defaults for all environments?
- [ ] **Validation**: Environment values validated appropriately?
- [ ] **Security**: Sensitive values handled securely?

### Database Integration 💾

**ORM Compatibility**:
- [ ] **Field Mapping**: Pydantic models map correctly to database schemas?
- [ ] **Serialization**: Database types serialize/deserialize correctly?
- [ ] **Migration Safety**: Changes backward compatible with existing data?

## Performance Review Guidelines

### Benchmarking Requirements 📊

**When to Benchmark**:
- Changes to performance-critical dataclasses
- New Pydantic models in hot paths
- Migration from one pattern to another
- Complex validation logic addition

**Benchmark Criteria**:
```python
# Example benchmark requirements
def test_performance_regression():
    # Dataclass instantiation should be < 1µs
    # Pydantic validation should be < 10µs
    # JSON serialization should be < 100µs
    pass
```

### Memory Usage Review 📈

**Memory Optimization Check**:
- [ ] **Slots Usage**: `slots=True` used for high-volume types?
- [ ] **Frozen Objects**: Immutable types use `frozen=True`?
- [ ] **Default Factories**: Mutable defaults properly handled?
- [ ] **Memory Profiling**: Large objects profiled for memory usage?

## Testing Requirements 🧪

### Validation Testing

**Required Test Coverage**:
- [ ] **Valid Inputs**: All valid input combinations tested?
- [ ] **Invalid Inputs**: All validation rules tested with invalid data?
- [ ] **Edge Cases**: Boundary conditions (min/max lengths, values) tested?
- [ ] **Error Messages**: Validation error messages verified?

**Test Pattern Examples**:
```python
def test_pydantic_validation():
    """Test Pydantic model validation."""
    # Valid case
    model = MyModel(field="valid_value")
    assert model.field == "valid_value"

    # Invalid case
    with pytest.raises(ValidationError) as exc:
        MyModel(field="")

    errors = exc.value.errors()
    assert "min_length" in errors[0]['type']

def test_dataclass_validation():
    """Test dataclass post_init validation."""
    # Valid case
    obj = MyDataclass(value=5)
    assert obj.value == 5

    # Invalid case
    with pytest.raises(ValueError, match="must be positive"):
        MyDataclass(value=-1)
```

### Serialization Testing

**JSON Serialization** (Pydantic only):
- [ ] **Round-trip**: Serialize → deserialize produces same object?
- [ ] **Field Names**: JSON keys match expected API contract?
- [ ] **Type Coercion**: String numbers converted appropriately?
- [ ] **Optional Fields**: Missing fields handled correctly?

## Security Review Items 🔒

### Input Validation Security

**Injection Prevention**:
- [ ] **SQL Injection**: No raw SQL in validation logic?
- [ ] **Command Injection**: No shell command execution in validators?
- [ ] **Path Traversal**: File paths validated and sanitized?
- [ ] **XSS Prevention**: User input properly escaped/validated?

**Data Exposure**:
- [ ] **Sensitive Data**: No passwords/keys in `__repr__` or logs?
- [ ] **PII Handling**: Personal information properly protected?
- [ ] **Error Messages**: No sensitive data in validation error messages?

## Review Process Integration

### PR Review Workflow 🔄

**Before Review**:
1. Author runs `make test` and `uv run mypy src/`
2. Author confirms pattern choice aligns with decision framework
3. Author documents rationale in PR description

**During Review**:
1. Reviewer uses this checklist systematically
2. Focus on architectural alignment first, then implementation details
3. Request benchmarks for performance-critical changes
4. Verify test coverage adequacy

**Review Comments Format**:
```markdown
**Data Modeling**: Consider using Pydantic BaseModel here since this class needs JSON serialization for the MCP API. See [decision framework](docs/adr/ADR-001-dataclass-pydantic-strategy.md#decision-framework).

**Performance**: This dataclass is used in the hot path - consider adding `slots=True` for memory optimization.

**Validation**: The validation logic in `__post_init__` is complex. Consider migrating to Pydantic with field validators for better error messages.
```

### Architecture Review Escalation 🔺

**When to Escalate**:
- Deviation from established patterns without clear rationale
- Performance implications for critical paths
- New validation patterns that might affect other systems
- Complex business rules requiring domain expertise

**Escalation Process**:
1. Tag `@architecture-team` in PR
2. Include specific questions and concerns
3. Reference relevant documentation and decision records
4. Provide performance benchmarks if applicable

## Tools Integration 🛠️

### IDE Integration

**VSCode Settings**:
```json
{
    "python.linting.mypyEnabled": true,
    "python.analysis.typeCheckingMode": "strict",
    "pydantic.enableCodeLens": true
}
```

**PyCharm Configuration**:
- Enable Pydantic plugin
- Configure type checking profile
- Set up validation error highlighting

### Pre-commit Hooks

**Required Checks**:
```yaml
- repo: local
  hooks:
    - id: mypy
      name: mypy
      entry: uv run mypy
      language: system
      types: [python]
      require_serial: true

    - id: data-model-lint
      name: Data Model Linting
      entry: ./scripts/check-data-models.py
      language: python
      types: [python]
```

---

**Next Review**: This checklist should be reviewed quarterly and updated based on team feedback and new patterns discovered during code reviews.

**Integration**: This checklist complements existing code review processes and should be used alongside general Python code review guidelines.
