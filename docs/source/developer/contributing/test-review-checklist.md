# Test Review Checklist

This checklist helps ensure consistent test quality during code reviews. Use this when reviewing pull requests that add, modify, or remove tests.

## Quick Reference

### ✅ Good Test Patterns
- Tests behavior, not implementation
- Meaningful assertions with specific error messages
- Factory fixtures for test isolation
- Property-based testing for domain rules
- Strategic mocking of external dependencies only

### ❌ Patterns to Avoid
- Testing private attributes/methods
- False positive assertions (always pass)
- Session-scoped mutable fixtures
- Over-mocking domain objects
- Brittle string matching in assertions

## Detailed Review Checklist

### 1. Test Quality Fundamentals

#### Test Focus and Behavior
- [ ] **Tests focus on behavior, not implementation details**
  - ✅ `assert spell.is_valid()`
  - ❌ `assert spell._internal_state == "ready"`

- [ ] **Tests have meaningful names that describe the scenario**
  - ✅ `test_spell_validation_rejects_invalid_level`
  - ❌ `test_spell_1` or `test_spell_function`

- [ ] **Each test has a single, clear responsibility**
  - Tests should verify one behavior or scenario
  - Long tests (>50 lines) should be broken down
  - Multiple unrelated assertions suggest multiple tests needed

#### Assertions Quality
- [ ] **Assertions are specific and meaningful**
  - ✅ `assert len(results) > 0, "Expected non-empty results"`
  - ❌ `assert len(results) >= 0` (always passes)

- [ ] **Error messages provide debugging context**
  - Include expected vs actual values
  - Reference the specific scenario being tested
  - Provide enough context to understand failure without reading code

- [ ] **No false positive assertions**
  - `len(...) >= 0` - always passes, use `> 0`
  - `result is not None` for operations that never return None
  - Assertions that pass for both valid and invalid inputs

### 2. Test Organization and Structure

#### File and Function Organization
- [ ] **Tests are in appropriate directory**
  - `tests/unit/` - Fast, isolated tests
  - `tests/integration/` - Component interaction tests
  - `tests/performance/` - Memory and timing benchmarks
  - `tests/property_based/` - Hypothesis property tests

- [ ] **Tests use appropriate pytest markers**
  - `@pytest.mark.slow` for tests >5 seconds
  - `@pytest.mark.integration` for component interaction tests
  - `@pytest.mark.property` for property-based tests

- [ ] **Related tests are grouped logically**
  - Use test classes for related scenarios
  - Group by feature or component being tested
  - Clear separation between different test concerns

#### Parametrization and DRY
- [ ] **Parametrized tests instead of duplicate methods**
  - ✅ `@pytest.mark.parametrize("level,expected", [(0, "Cantrip"), (1, "1st-level")])`
  - ❌ Separate `test_level_0`, `test_level_1` methods

- [ ] **Common test patterns are extracted to utilities**
  - Shared assertion helpers for domain concepts
  - Common test data generation functions
  - Reusable validation patterns

### 3. Fixture Design and Test Isolation

#### Modern Fixture Patterns
- [ ] **Factory fixtures instead of session-scoped mutable fixtures**
  - ✅ Factory returns function that creates fresh instances
  - ❌ Session-scoped fixture that mutates shared state

- [ ] **Proper fixture scoping**
  - `function` scope for most fixtures (default)
  - `session` scope only for expensive, immutable setup
  - No `session` scope for mutable state

- [ ] **Test isolation verified**
  - Tests can run in any order
  - No hidden dependencies between tests
  - Proper cleanup of temporary resources

#### Test Data Management
- [ ] **Realistic test data that reflects actual usage**
  - Use SRD-compatible D&D content for domain tests
  - Test data covers common and edge case scenarios
  - Avoid hardcoded test data when possible

- [ ] **Appropriate use of temporary files/directories**
  - Use `tmp_path` fixture for temporary files
  - Clean up resources automatically
  - Don't pollute project directories with test artifacts

### 4. Property-Based Testing

#### Hypothesis Usage
- [ ] **Property-based tests for domain rules**
  - D&D rule validation (spell levels 0-9, ability scores 1-30)
  - Serialization roundtrip testing
  - Input validation robustness

- [ ] **Efficient test data generation**
  - Use `st.sampled_from()` for better performance
  - Constrain ranges appropriately (`st.integers(0, 9)` for spell levels)
  - Custom `@composite` strategies for complex domain objects

- [ ] **Reasonable Hypothesis settings**
  - `max_examples=50` for most tests (not 100+ unless needed)
  - `deadline=5000` for performance-sensitive tests
  - Use `assume()` to filter invalid inputs rather than broad generation

#### Property Test Quality
- [ ] **Properties test meaningful invariants**
  - ✅ Spell level always 0-9 after validation
  - ✅ Serialization roundtrip preserves data
  - ❌ Trivial properties that don't add value

- [ ] **Copyright-safe test data generation**
  - Use SRD/OGL content for names and references
  - Avoid generating copyrighted D&D content
  - Use generic placeholders for non-SRD content

### 5. Mocking and Dependencies

#### Strategic Mocking
- [ ] **Mocks only external dependencies**
  - ✅ Mock network requests, file system operations, external processes
  - ❌ Mock domain objects, business logic, or internal components

- [ ] **Mock interfaces, not implementations**
  - Mock at the boundary between your code and external systems
  - Use dependency injection to enable easy mocking
  - Avoid mocking deep into your own code structure

- [ ] **Realistic mock behavior**
  - Mock return values match real service behavior
  - Include error conditions that could occur in production
  - Don't oversimplify mock responses

#### Integration vs Unit Testing Balance
- [ ] **Appropriate test type for scenario**
  - Unit tests for isolated component logic
  - Integration tests for component interactions
  - End-to-end tests for critical user workflows

- [ ] **Integration tests use real objects with test data**
  - Prefer real implementations with smaller test datasets
  - Use test databases, test files, etc. instead of mocks
  - Validate actual integration behavior

### 6. Performance and Resource Usage

#### Test Performance
- [ ] **Tests complete within reasonable time**
  - Unit tests: <1 second each
  - Integration tests: <10 seconds each
  - Full test suite: <5 minutes

- [ ] **Performance-sensitive tests are marked appropriately**
  - `@pytest.mark.slow` for tests >5 seconds
  - Performance tests in `tests/performance/` directory
  - Consider test execution time impact on development workflow

#### Resource Management
- [ ] **Proper resource cleanup**
  - Files and connections are closed
  - Temporary resources are cleaned up
  - No resource leaks between tests

- [ ] **Memory usage is reasonable**
  - Tests don't consume excessive memory
  - Large objects are cleaned up when no longer needed
  - Memory profiling done for memory-intensive tests

### 7. Domain-Specific Validation

#### D&D 5e Content Testing
- [ ] **D&D rule compliance testing**
  - Spell levels, ability scores, challenge ratings within valid ranges
  - Content type validation (spells, creatures, items, etc.)
  - Cross-reference validation for content relationships

- [ ] **LaTeX output validation**
  - ✅ Semantic validation: `assert_has_section("Spell Name")`
  - ❌ Brittle string matching: `assert "\\section{Fireball}" in output`
  - Test LaTeX structure and validity, not exact formatting

- [ ] **Content parsing robustness**
  - Handle malformed input gracefully
  - Test edge cases in 5etools JSON format
  - Validate error handling for invalid content

#### Security Considerations
- [ ] **No hardcoded secrets or sensitive data in tests**
  - Use environment variables or test fixtures for sensitive data
  - Don't commit API keys, passwords, or personal information
  - Use placeholder values for security-sensitive testing

- [ ] **Input validation testing**
  - Test with malicious or malformed inputs
  - Validate proper sanitization of user input
  - Test boundary conditions and edge cases

### 8. Documentation and Maintainability

#### Test Documentation
- [ ] **Test docstrings explain the "why" not the "what"**
  - Explain the business rule or scenario being tested
  - Document assumptions or special conditions
  - Reference related requirements or issues when relevant

- [ ] **Clear test setup and expectations**
  - Test arrangement is easy to understand
  - Expected outcomes are clearly defined
  - Test flow is logical and readable

#### Code Quality
- [ ] **Tests follow same quality standards as production code**
  - Proper typing and type hints
  - Clear variable and function names
  - Appropriate code organization and structure

- [ ] **Tests are easy to maintain and modify**
  - Minimal duplication between related tests
  - Easy to add new test cases for similar scenarios
  - Clear separation of test concerns

## Performance and Quality Gates

### Automated Checks
- [ ] **Performance monitoring shows acceptable results**
  - Test execution time within budgets
  - Memory usage reasonable
  - No significant performance regressions

- [ ] **Quality metrics pass gates**
  - No false positive assertions detected
  - Private attribute access eliminated
  - Mock usage within reasonable limits

### Manual Review Points
- [ ] **Test coverage is appropriate**
  - Critical business logic is tested
  - Edge cases are covered
  - Error conditions are validated

- [ ] **Tests add value**
  - Tests catch real bugs, not just exercise code
  - Property-based tests discover edge cases
  - Integration tests validate real system behavior

## Common Anti-Patterns to Flag

### Implementation Detail Testing
```python
# ❌ BAD - Testing implementation details
def test_omnidexer_internal_state():
    omnidexer = Omnidexer()
    assert omnidexer._depth == 0
    assert len(omnidexer._loaders) > 0

# ✅ GOOD - Testing behavior
def test_omnidexer_initialization():
    omnidexer = Omnidexer()
    assert omnidexer.is_ready_for_indexing()
    assert omnidexer.get_loader_count() > 0
```

### False Positive Assertions
```python
# ❌ BAD - Always passes
assert len(results) >= 0
assert result is not None  # for str(), len(), etc.

# ✅ GOOD - Meaningful checks
assert len(results) > 0, "Expected non-empty results"
assert isinstance(result, str), f"Expected string, got {type(result)}"
```

### Over-Mocking
```python
# ❌ BAD - Mocking domain objects
@mock.patch('dnd5e.models.Spell')
def test_spell_processing(mock_spell):
    # Testing mock interactions, not real behavior

# ✅ GOOD - Using real objects with test data
def test_spell_processing(sample_spell):
    result = SpellProcessor().process(sample_spell)
    assert result.is_valid()
```

### Session-Scoped Mutable State
```python
# ❌ BAD - Shared mutable state
@pytest.fixture(scope="session")
def shared_omnidexer():
    omnidexer = Omnidexer()
    omnidexer.load_data()  # Shared between tests
    return omnidexer

# ✅ GOOD - Factory pattern
@pytest.fixture
def make_omnidexer():
    def _make(config=None):
        return Omnidexer(config or {})
    return _make
```

## Review Process Integration

### Pre-Review Preparation
Before requesting review:
- [ ] Run test quality analysis: `make test-quality`
- [ ] Run performance monitoring: `make test-perf`
- [ ] Verify test isolation and independence
- [ ] Check that new tests follow established patterns

### During Code Review
- [ ] Focus on test design and quality, not just coverage
- [ ] Suggest improvements using examples from this checklist
- [ ] Verify that tests actually test the intended behavior
- [ ] Check for opportunities to use property-based testing

### Post-Review Actions
- [ ] Update test baselines if performance characteristics change
- [ ] Document any new test patterns or conventions
- [ ] Share learnings with team if novel testing approaches used

## Continuous Improvement

### Regular Test Health Checks
- Monitor test quality metrics trends
- Review slowest tests and optimization opportunities
- Update this checklist based on common review feedback
- Share effective testing patterns with the team

### Training and Knowledge Sharing
- Reference this checklist in PR templates
- Use examples from reviews to improve guidelines
- Conduct periodic test quality reviews
- Update onboarding materials with testing standards

This checklist ensures that tests not only provide comprehensive coverage but also maintain high quality, performance, and maintainability standards that support confident, rapid development of the D&D 5e PDF generation system.
