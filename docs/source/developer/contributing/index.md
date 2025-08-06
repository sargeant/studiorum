# Contributing Guide

Everything you need to contribute to the 5e2pdf project.

## Getting Started

```{toctree}
:maxdepth: 1

setup-guide
```

## Standards & Guidelines

```{toctree}
:maxdepth: 1

coding-standards
testing-requirements
dependency-management
```

## Development Process

```{toctree}
:maxdepth: 1

contributing
review-process
```

## Quality Assurance

```{toctree}
:maxdepth: 1

test-performance-monitoring
test-review-checklist
```

## Quick Start for Contributors

### First Time Setup
1. {doc}`setup-guide` - Environment setup and project orientation
2. {doc}`coding-standards` - Code style and quality requirements
3. {doc}`testing-requirements` - Testing guidelines and best practices

### Development Workflow
1. **Plan** - Create or assign GitHub issue
2. **Branch** - Create feature/fix branch
3. **Develop** - Follow TDD methodology
4. **Test** - Run full test suite
5. **Review** - Submit PR with {doc}`review-process`

### Quality Standards
- **Type Safety**: Full mypy compliance required
- **Test Coverage**: Maintain or improve existing coverage
- **Performance**: No regressions on critical paths
- **Documentation**: Update relevant docs for changes

## Development Environment

**Required Tools:**
- Python 3.12+ with uv for dependency management
- Git for version control
- LaTeX distribution for PDF generation
- Pre-commit hooks for code quality

**Recommended Tools:**
- VS Code with Python extension
- mypy for type checking
- pytest for testing
- ruff for linting and formatting

## Contribution Types

### Bug Fixes
- Start with {doc}`../development-workflows/troubleshooting-strategies`
- Follow {doc}`../development-workflows/tdd-methodology`
- Include regression tests

### New Features
- Discuss design in GitHub issues first
- Follow {doc}`../system-guide/architecture-overview`
- Add comprehensive tests and documentation

### Documentation
- Follow Sphinx + MyST standards
- Include code examples where helpful
- Update related cross-references

### Performance Improvements
- Benchmark before and after changes
- Follow {doc}`../development-workflows/performance-optimization`
- Document performance impact

## Related Documentation

- {doc}`../getting-started/index` - Choose your contributor path
- {doc}`../system-guide/index` - Understand the system architecture
- {doc}`../development-workflows/index` - Development methodologies
- {doc}`../api-reference/index` - Technical API reference
