# For AI Agents

Systematic approaches, task frameworks, and quality validation patterns for AI coding agents working on 5e2pdf.

## Task Classification Framework

Use this framework to categorize requests and select the appropriate systematic approach:

### New Feature Implementation
**Pattern**: Analysis → Planning → Testing → Implementation → Validation

**Approach:**
1. **Analysis Phase**
   - Use {doc}`../system-guide/architecture-overview` to understand system design
   - Search codebase for similar existing implementations
   - Identify affected components and integration points
   - Assess performance and compatibility impact

2. **Planning Phase**
   - Design API interfaces following existing patterns
   - Plan test coverage strategy (unit, integration, performance)
   - Consider backward compatibility requirements
   - Document implementation approach

3. **Testing Phase**
   - Follow {doc}`../development-workflows/tdd-methodology`
   - Write comprehensive test cases first
   - Include error handling and edge cases
   - Set up performance benchmarks if applicable

4. **Implementation Phase**
   - Implement following established code patterns
   - Use type hints and Pydantic validation
   - Follow synchronous processing patterns for operations
   - Add comprehensive logging and error handling

5. **Validation Phase**
   - Run full test suite (`uv run pytest`)
   - Verify type checking (`uv run mypy src/`)
   - Check code quality (`uv run ruff check src/`)
   - Update relevant documentation

**Key Considerations:**
- Performance impact on loading and rendering pipelines
- Integration with existing omnidexer and content models
- Consistency with LaTeX rendering patterns
- Memory usage and caching implications

### Bug Investigation & Fixing
**Pattern**: Reproduce → Isolate → Test → Fix → Validate → Regression Testing

**Approach:**
1. **Reproduce**
   - Create minimal test case that reproduces the issue
   - Identify exact conditions that trigger the bug
   - Check if issue affects multiple content types or sources

2. **Isolate**
   - Use debugging tools and structured logging
   - Narrow down to specific component or function
   - Identify root cause through systematic elimination

3. **Test**
   - Write failing test that captures the bug
   - Ensure test fails for the right reason
   - Add edge cases related to the bug

4. **Fix**
   - Implement minimal fix that makes test pass
   - Ensure fix doesn't break existing functionality
   - Consider broader implications of the change

5. **Validate**
   - Verify all tests pass including new regression test
   - Check performance impact of fix
   - Update documentation if behavior changes

6. **Regression Testing**
   - Add test to prevent future regressions
   - Consider if similar issues might exist elsewhere
   - Update error handling patterns if applicable

**Debugging Tools:**
- Structured logging: `from dnd5e.core.logging import get_logger`
- Performance profiling: `cProfile` or `py-spy`
- Memory debugging: `tracemalloc`
- Logic debugging: Check for proper function call patterns and data flow

### Code Quality Improvements
**Pattern**: Assessment → Prioritization → Incremental Changes → Validation

**Approach:**
1. **Assessment**
   - Run code quality tools (`mypy`, `ruff`)
   - Identify technical debt and improvement opportunities
   - Assess test coverage gaps
   - Review performance bottlenecks

2. **Prioritization**
   - Focus on user-impacting issues first
   - Address type safety violations
   - Fix performance regressions
   - Improve error handling and logging

3. **Incremental Changes**
   - Make small, focused improvements
   - Maintain backward compatibility
   - Follow existing code patterns
   - Add tests for improved code

4. **Validation**
   - Ensure all tests continue to pass
   - Verify performance improvements
   - Check that changes follow project standards
   - Update documentation as needed

**Quality Standards:**
- Type safety: Full mypy compliance required
- Test coverage: Maintain or improve existing coverage
- Performance: No regressions on critical paths
- Documentation: Update relevant docs for changes

### Architecture Changes
**Pattern**: Impact Analysis → Design Review → Migration Planning → Implementation

**Approach:**
1. **Impact Analysis**
   - Assess scope of changes across codebase
   - Identify breaking changes and compatibility issues
   - Evaluate performance implications
   - Consider migration path for existing code

2. **Design Review**
   - Ensure changes align with system architecture
   - Review against established design patterns
   - Consider extensibility and maintainability
   - Plan for testing complex interactions

3. **Migration Planning**
   - Plan backward compatibility strategy
   - Design incremental migration approach
   - Identify rollback strategies
   - Plan documentation updates

4. **Implementation**
   - Implement changes incrementally
   - Maintain system stability throughout process
   - Add comprehensive tests for new architecture
   - Update all affected documentation

**Considerations:**
- Backward compatibility with existing content
- Performance impact on loading and rendering
- Maintainability and code complexity
- Testing strategy for architectural changes

## System Understanding Priorities

### Essential Knowledge (Master First)
1. **Dual-file Loading Architecture**
   - {doc}`../system-guide/component-deep-dives/loader-architecture`
   - ContentMerger with LRU caching and TTL
   - Runtime merging of metadata and content files

2. **Omnidexer System**
   - {doc}`../system-guide/component-deep-dives/deep-indexing`
   - Multi-index architecture for content discovery
   - DeepIndexable protocol for nested content

3. **Content Models**
   - {doc}`../api-reference/content-models`
   - Pydantic-based validation and type safety
   - BaseContent hierarchy and ContentType system

### Important Knowledge (Learn Second)
1. **LaTeX Rendering Pipeline**
   - {doc}`../system-guide/component-deep-dives/latex-rendering`
   - Template-based document generation
   - Multi-engine compilation support

2. **Configuration System**
   - {doc}`../api-reference/configuration`
   - Environment variable integration
   - Hierarchical configuration loading

### Detailed Knowledge (Learn as Needed)
1. **Tag System and Content Organization**
2. **Rendering and Output Optimization**
3. **Caching Mechanisms and Performance Tuning**
4. **Error Handling and Logging Patterns**

## Quality Validation Checklist

Run this validation sequence before considering any task complete:

### Code Quality
- [ ] Type checking passes: `uv run mypy src/`
- [ ] Linting passes: `uv run ruff check src/`
- [ ] Formatting is correct: `uv run ruff format src/`
- [ ] No security issues: Review for secret exposure

### Testing
- [ ] All tests pass: `uv run pytest`
- [ ] New code has appropriate test coverage
- [ ] Integration tests cover component interactions
- [ ] Performance tests show no regressions

### Documentation
- [ ] Docstrings added for new public methods
- [ ] API documentation updated if interfaces change
- [ ] Implementation guides updated for architectural changes
- [ ] Examples updated if user-facing behavior changes

### Performance
- [ ] No performance regressions on critical paths
- [ ] Memory usage remains within acceptable bounds
- [ ] Operations use proper synchronous patterns
- [ ] Caching strategies are appropriate

### Integration
- [ ] Changes integrate properly with existing systems
- [ ] No breaking changes to public APIs
- [ ] Configuration changes are backward compatible
- [ ] Error handling follows established patterns

## Context Building Strategy

### Initial Orientation (Do Once)
1. Read {doc}`../system-guide/architecture-overview` for high-level understanding
2. Review {doc}`../system-guide/component-deep-dives/index` for component relationships
3. Examine {doc}`../api-reference/index` for key interfaces
4. Understand {doc}`../contributing/index` for development workflow

### Task-Specific Context (Do Per Task)
1. **Search for Related Code**
   ```bash
   # Find similar implementations
   rg "class.*Similar" src/
   # Look for existing tests
   rg "test.*feature" tests/
   # Check for documentation
   rg "feature" docs/
   ```

2. **Examine Affected Components**
   - Read relevant source files completely
   - Understand data flow and dependencies
   - Check existing error handling patterns
   - Review test coverage for the area

3. **Check Configuration and Settings**
   - Review relevant config options
   - Understand environment variable usage
   - Check for feature flags or toggles

### Performance Context (For Performance Tasks)
1. **Profile Current Performance**
   ```bash
   # Profile specific operations
   uv run python -m cProfile script.py
   # Monitor memory usage
   uv run python -m tracemalloc script.py
   ```

2. **Understand Bottlenecks**
   - Identify I/O vs CPU bound operations
   - Check caching effectiveness
   - Review synchronous processing patterns
   - Examine memory allocation patterns

## Common Task Patterns

### Adding New Content Type Support
1. **Model Definition**: Create Pydantic model in `src/dnd5e/core/models/`
2. **Parser Implementation**: Add parsing logic in `src/dnd5e/core/parsers/`
3. **Indexing Support**: Implement DeepIndexable if needed
4. **Rendering Support**: Add LaTeX templates and processors
5. **Testing**: Comprehensive test coverage for all components

### Performance Optimization
1. **Measurement**: Profile before making changes
2. **Identification**: Find specific bottlenecks
3. **Optimization**: Apply targeted improvements
4. **Validation**: Measure improvement and check for regressions
5. **Monitoring**: Add performance tests to prevent future regressions

### API Enhancement
1. **Design**: Plan interface changes carefully
2. **Backward Compatibility**: Ensure existing code continues working
3. **Implementation**: Follow established patterns
4. **Documentation**: Update API reference and examples
5. **Migration**: Provide migration guide if needed

## Error Patterns and Solutions

### Common Issues
1. **Type Errors**: Usually indicate missing type hints or incorrect assumptions
2. **Logic Errors**: Check for incorrect function calls or data flow patterns
3. **Validation Errors**: Review Pydantic model definitions and input data
4. **Performance Issues**: Profile to identify actual bottlenecks
5. **Import Errors**: Check for circular imports or missing dependencies

### Debugging Strategies
1. **Use Structured Logging**: Add detailed logging to understand execution flow
2. **Write Tests**: Create minimal reproduction cases
3. **Isolate Problems**: Narrow down to specific components
4. **Check Assumptions**: Verify data types and formats
5. **Review Documentation**: Ensure following established patterns

## Integration with Human Developer

### Status Reporting
- Provide clear progress updates using TodoWrite tool
- Explain reasoning behind implementation decisions
- Highlight any deviations from standard patterns
- Report performance impacts and trade-offs

### Collaboration Patterns
- Ask clarifying questions about requirements
- Propose alternative approaches when appropriate
- Identify potential issues or concerns early
- Provide comprehensive documentation of changes

### Handoff Preparation
- Ensure all tests pass and quality checks complete
- Document any technical debt or future improvement opportunities
- Explain complex implementation decisions
- Provide clear commit messages and PR descriptions

This systematic approach ensures consistent, high-quality contributions to the 5e2pdf project while maintaining system stability and performance.
