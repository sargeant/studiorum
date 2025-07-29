# Contributing

```{note}
This page is under construction. Please check back later for detailed contribution guidelines.
```

## Getting Started

### Development Setup

```bash
# Clone the repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Install development dependencies
uv sync --extra dev --extra docs --extra test

# Install pre-commit hooks
pre-commit install
```

### Code Standards

- **Python Version**: 3.12+
- **Type Checking**: mypy for all source code
- **Linting**: ruff with project configuration
- **Testing**: pytest with comprehensive coverage
- **Documentation**: Sphinx with MyST markdown

## Development Workflow

### Test-Driven Development

1. **Explore**: Understand the codebase and requirements
2. **Plan**: Design the implementation approach
3. **Test**: Write tests that define expected behavior
4. **Code**: Implement features to pass tests
5. **Validate**: Ensure all tests pass and code quality checks succeed

### Git Workflow

- **Branches**: `feat/` or `fix/` branches from `main`
- **Commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/)
- **Merging**: Pull requests with squash and merge

## Code Review Process

### Pull Request Requirements

- [ ] All tests pass
- [ ] Code coverage maintained
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Documentation updated
- [ ] Conventional commit format

### Review Checklist

- Code follows project patterns
- Tests cover edge cases
- Documentation is clear and complete
- Performance considerations addressed

## Release Process

1. Version bump in `pyproject.toml`
2. Update CHANGELOG.md
3. Tag release
4. GitHub Actions handles publishing

For architectural details, see [Architecture](architecture.md).
