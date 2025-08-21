# Contributing Guide

Everything you need to contribute to the 5e2pdf project.

## Getting Started

```{toctree}
:maxdepth: 1

developer/contributing/index
developer/contributing/setup-guide
```

## Standards & Guidelines

```{toctree}
:maxdepth: 1

developer/contributing/coding-standards
developer/contributing/testing-requirements
developer/contributing/dependency-management
```

## Development Process

```{toctree}
:maxdepth: 1

developer/contributing/contributing
developer/contributing/test-review-checklist
```

## Quality Assurance

```{toctree}
:maxdepth: 1

developer/contributing/test-performance-monitoring
developer/contributing/test-review-checklist
```

## Quick Start for Contributors

### First Time Setup
1. {doc}`developer/contributing/setup-guide` - Environment setup and project orientation
2. {doc}`developer/contributing/coding-standards` - Code style and quality requirements
3. {doc}`developer/contributing/testing-requirements` - Testing guidelines and best practices

### Development Workflow
1. **Plan** - Create or assign GitHub issue
2. **Branch** - Create feature/fix branch
3. **Develop** - Follow TDD methodology
4. **Test** - Run full test suite
5. **Review** - Submit PR with {doc}`developer/contributing/test-review-checklist`

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
- Start with {doc}`developer/development-workflows/troubleshooting-strategies`
- Follow {doc}`developer/development-workflows/tdd-methodology`
- Include regression tests

### New Features
- Discuss design in GitHub issues first
- Follow {doc}`architecture-overview`
- Add comprehensive tests and documentation

### Documentation
- Follow Sphinx + MyST standards
- Include code examples where helpful
- Update related cross-references

### Performance Improvements
- Benchmark before and after changes
- Follow {doc}`developer/development-workflows/quality-standards`
- Document performance impact

## Related Documentation

- {doc}`getting-started` - Choose your contributor path
- {doc}`architecture-overview` - Understand the system architecture
- {doc}`development-workflows` - Development methodologies
- {doc}`library-reference/index` - Technical API reference
