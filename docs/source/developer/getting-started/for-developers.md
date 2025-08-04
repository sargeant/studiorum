# For Developers

Strategic guidance for feature development, architectural decisions, and long-term planning.

## Strategic Decision Frameworks

### Feature Development Strategy

When planning new features, use this decision framework:

#### 1. Feature Evaluation Matrix

| Criteria | Weight | Score (1-5) | Notes |
|----------|--------|-------------|-------|
| User Impact | 40% | | How many users benefit? |
| Implementation Complexity | 25% | | Development effort required |
| Maintenance Burden | 20% | | Long-term support needs |
| Performance Impact | 15% | | Effect on system performance |

**Decision Rules:**
- **High Priority**: Weighted score > 4.0
- **Medium Priority**: Weighted score 3.0-4.0
- **Low Priority**: Weighted score < 3.0

#### 2. Architecture Alignment Check

Before implementing features, ensure alignment with:

- **Type Safety**: Will this maintain full mypy compliance?
- **Performance**: Does this follow sync patterns (async migration complete)?
- **Extensibility**: Can this be extended without breaking changes?
- **Testing**: Can this be comprehensively tested?
- **Service Container**: Does this use dependency injection instead of global singletons?

#### Service Container Architecture

**Current State**: The codebase has migrated to a service container pattern for dependency management.

**Key Principles**:
- Use `get_global_container()` for accessing core services
- Avoid direct global singleton access (deprecated patterns)
- Use `reset_global_container()` for test isolation
- Prefer scoped containers for batch operations

**Migration Status**:
- ✅ `EntryRegistry` - Migrated to service container
- ✅ `ReferenceManager` - Migrated to service container
- ✅ `Omnidexer` - Managed by service container
- ✅ `TagResolver` - Managed by service container
- ❌ `CacheManager` - Still uses individual reset
- ❌ CLI globals - Still require individual reset

**Implementation Guidelines**:
```python
# ✅ Preferred approach
from dnd5e.core.container import get_global_container
container = get_global_container()
registry = container.get_entry_registry()

# ❌ Deprecated approach (backward compatible)
from dnd5e.core.entry_registry import get_registry
registry = get_registry()  # Uses container internally
```

#### 3. Resource Planning

**Development Phases:**
1. **Research** (20% of effort): Understanding requirements and existing systems
2. **Design** (25% of effort): API design and integration planning
3. **Implementation** (35% of effort): Core development work
4. **Testing & Documentation** (20% of effort): Quality assurance and docs

### Refactoring vs. Extension Decision Framework

When faced with adding functionality to existing systems:

#### Extend When:
- Current architecture supports the new requirement cleanly
- Performance impact is minimal
- No breaking changes to existing APIs
- Implementation can be isolated to new components

**Example**: Adding a new content type that follows existing BaseContent patterns.

#### Refactor When:
- Current design creates significant technical debt
- Performance requirements can't be met with current architecture
- Code becomes difficult to maintain or understand
- Security or reliability issues exist

**Example**: Replacing synchronous file loading with async operations.

#### Hybrid Approach When:
- New requirements partially fit existing patterns
- Migration path can be incremental
- Backward compatibility must be maintained
- Risk of breaking existing functionality is high

**Strategy**: Implement new patterns alongside old ones, then gradually migrate.

### Performance vs. Maintainability Trade-offs

#### Performance Optimization Guidelines

**Optimize When:**
- Profiling shows actual bottlenecks (not perceived ones)
- User experience is significantly impacted
- Scalability requirements aren't being met
- Resource usage is unsustainable

**Don't Optimize When:**
- Performance is already acceptable
- Optimization would significantly complicate code
- Maintenance burden would increase substantially
- Alternative approaches haven't been explored

#### Maintainability Priorities

1. **Code Clarity**: Prioritize readable, self-documenting code
2. **Type Safety**: Maintain comprehensive type annotations
3. **Test Coverage**: Ensure changes don't reduce test quality
4. **Documentation**: Keep implementation guides current

**Trade-off Example:**
```python
# More maintainable (prefer this)
async def load_content_simple(content_type: ContentType) -> list[BaseContent]:
    """Clear, straightforward implementation."""
    data = await fetch_data(content_type)
    return [parse_content(item) for item in data]

# More performant but complex (use only if proven necessary)
async def load_content_optimized(content_type: ContentType) -> list[BaseContent]:
    """Optimized version with caching and batching."""
    # Complex caching logic, batching, and optimization
    # Harder to understand and maintain
```

### Testing Investment Strategy

#### Testing ROI Framework

**High Testing Investment** (>90% coverage):
- Core content models and validation
- Data loading and parsing pipelines
- Public API interfaces
- Security-sensitive operations

**Medium Testing Investment** (70-90% coverage):
- Rendering and output generation
- Configuration and settings management
- Error handling and recovery
- Performance-critical paths

**Lower Testing Investment** (50-70% coverage):
- User interface and CLI interactions
- Documentation generation
- Development tools and utilities
- Experimental features

#### Test Strategy by Component

**Unit Tests**: Fast, isolated, comprehensive coverage
- Content model validation
- Parser logic and transformations
- Utility functions and helpers

**Integration Tests**: Component interactions, realistic scenarios
- Omnidexer with content loading
- End-to-end rendering workflows
- Configuration and environment setup

**Performance Tests**: Regression prevention, scalability validation
- Large dataset processing
- Memory usage monitoring
- Rendering performance benchmarks

### Technical Debt Management

#### Debt Classification

**Type 1: Deliberate and Strategic**
- Temporary workarounds with documented timelines
- Performance shortcuts with known alternatives
- Quick fixes for urgent production issues

**Type 2: Deliberate but Tactical**
- Implementation shortcuts to meet deadlines
- Simplified solutions pending better understanding
- Deferred optimization for non-critical paths

**Type 3: Inadvertent**
- Outdated patterns that no longer align with architecture
- Code that worked around old limitations
- Dependencies that are no longer optimal

**Type 4: Reckless**
- Code without tests or documentation
- Security vulnerabilities
- Performance issues affecting users

#### Debt Repayment Strategy

**Priority Order:**
1. **Type 4**: Address immediately, high risk
2. **Type 3**: Regular maintenance, planned refactoring
3. **Type 1**: Follow documented timeline
4. **Type 2**: Address when touching related code

**Allocation Guidelines:**
- 20% of development time for debt reduction
- Address Type 4 debt immediately regardless of other priorities
- Combine debt reduction with feature development when possible
- Track debt reduction in documentation and commits

## Long-term Planning Guidance

### Architecture Evolution Patterns

#### Incremental Enhancement Pattern
**Use For**: Adding new content types, extending existing features
**Approach**: Build on existing foundations, maintain backward compatibility
**Example**: Adding new spell properties while maintaining existing parsing

#### Migration Pattern
**Use For**: Replacing core systems, updating dependencies
**Approach**: Parallel implementation with gradual migration
**Example**: Moving from synchronous to asynchronous loading

#### Modular Expansion Pattern
**Use For**: Adding major new capabilities
**Approach**: Create new modules with clean interfaces
**Example**: Adding support for entirely new output formats

### Dependency Management Strategy

#### Dependency Categories

**Core Dependencies**: Essential for basic functionality
- Python runtime and standard library
- Pydantic for data validation
- Click for CLI interface

**Feature Dependencies**: Enable specific capabilities
- Jinja2 for templating
- LaTeX distribution for PDF generation
- aiofiles for async file operations

**Development Dependencies**: Support development workflow
- pytest for testing
- mypy for type checking
- ruff for linting and formatting

#### Update Strategy

**Core Dependencies**:
- Conservative updates with thorough testing
- Major version updates require migration planning
- Security updates applied immediately

**Feature Dependencies**:
- Regular updates with compatibility testing
- Monitor for deprecations and plan migrations
- Evaluate alternatives periodically

**Development Dependencies**:
- Keep current with latest stable versions
- Update frequently to benefit from improvements
- Accept breaking changes in development tools

### Performance Scaling Considerations

#### Current Architecture Limits

**Memory Usage**:
- Current: ~100MB for full content dataset
- Scaling limit: ~1GB before architectural changes needed
- Mitigation: Lazy loading, content streaming

**Processing Speed**:
- Current: ~30 seconds for full book generation
- Scaling target: <10 seconds for typical use cases
- Optimization areas: Template compilation, content caching

**Concurrent Operations**:
- Current: Single-threaded with async I/O
- Scaling option: Multi-process for CPU-intensive tasks
- Consideration: Balance complexity vs. performance gains

#### Scaling Strategies

**Horizontal Scaling**: Distribute work across multiple processes
- Content loading can be parallelized by content type
- Rendering can be distributed across chapters/sections
- Requires careful coordination and result aggregation

**Vertical Scaling**: Optimize single-process performance
- Better algorithms and data structures
- Compiled extensions for critical paths
- Memory usage optimization

**Hybrid Approach**: Combine strategies based on workload
- Parallel loading with optimized single-threaded rendering
- Dynamic scaling based on content size and complexity

### API Stability Planning

#### Stability Guarantees

**Public APIs**: Full backward compatibility within major versions
- Content model interfaces
- CLI command structure
- Configuration format

**Internal APIs**: Best effort compatibility, documented changes
- Component interfaces between modules
- Extension points for plugins
- Development utilities

#### Versioning Strategy

**Semantic Versioning**: MAJOR.MINOR.PATCH
- **MAJOR**: Breaking changes to public APIs
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, performance improvements

**Deprecation Process**:
1. **Announcement**: Document planned changes
2. **Warning**: Add deprecation warnings
3. **Migration**: Provide migration tools/guides
4. **Removal**: Remove deprecated features in next major version

#### Change Management

**API Evolution Planning**:
- Design APIs for extensibility from the start
- Use protocols and abstract base classes for flexibility
- Provide migration tools for breaking changes
- Maintain detailed changelog for all versions

**Compatibility Testing**:
- Automated tests for API stability
- Integration tests with real content
- Performance regression testing
- Documentation validation

## Implementation Decision Points

### When to Add New Dependencies

**Add Dependency When**:
- Significant functionality needed that's well-implemented elsewhere
- Implementation cost > maintenance cost of dependency
- Dependency is stable, well-maintained, and widely used
- Adds capabilities beyond reasonable internal development

**Avoid Dependencies When**:
- Functionality is simple to implement internally
- Dependency adds significant bloat or security concerns
- License incompatibility or legal issues
- Unstable or poorly maintained external project

### Code Organization Principles

#### Module Structure Guidelines

**Single Responsibility**: Each module has one clear purpose
```
src/dnd5e/core/
├── models/          # Data structures only
├── parsers/         # Transformation logic only
├── loaders/         # Data fetching only
└── config/          # Configuration only
```

**Clear Dependencies**: Avoid circular imports
- Models don't import parsers
- Parsers can import models
- Loaders can import both models and parsers
- Config is imported by others, doesn't import business logic

**Interface Segregation**: Multiple small interfaces vs. large ones
```python
# Good: Specific protocols
class Loadable(Protocol):
    async def load(self) -> Any: ...

class Parseable(Protocol):
    def parse(self, data: Any) -> BaseContent: ...

# Avoid: Kitchen sink interfaces
class ContentProcessor(Protocol):
    async def load(self) -> Any: ...
    def parse(self, data: Any) -> BaseContent: ...
    def validate(self, content: BaseContent) -> bool: ...
    def render(self, content: BaseContent) -> str: ...
```

### Error Handling Strategy

#### Error Categories and Responses

**User Errors**: Invalid input, missing files, configuration issues
- **Response**: Clear error messages, suggested fixes
- **Recovery**: Graceful degradation where possible
- **Example**: Missing source file → skip with warning, continue processing

**System Errors**: Network issues, permission problems, resource exhaustion
- **Response**: Retry with backoff, fallback options
- **Recovery**: Temporary failure handling, resource cleanup
- **Example**: Network timeout → retry 3 times, then offline mode

**Programming Errors**: Bugs, logic errors, assertion failures
- **Response**: Fail fast with detailed diagnostics
- **Recovery**: No recovery, fix the bug
- **Example**: Invalid data structure → raise detailed exception

**Performance Degradation**: Slow operations, memory pressure
- **Response**: Monitoring, warnings, automatic optimization
- **Recovery**: Reduce quality or functionality temporarily
- **Example**: Large content → switch to streaming mode

This strategic guidance helps navigate complex decisions while maintaining code quality and system reliability over the long term.
