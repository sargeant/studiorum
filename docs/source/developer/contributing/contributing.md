# Contributing

Welcome to the 5e2pdf project! This guide provides comprehensive information for
contributing to the codebase, from setting up your development environment to
submitting pull requests.

## Getting Started

### Prerequisites

- **Python**: 3.12+ required
- **uv**: Modern Python package manager
- **Git**: For version control
- **LaTeX**: XeLaTeX or PDFLaTeX for PDF generation

### Development Setup

```bash
# Clone the repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Install all dependencies with uv (required package manager)
uv sync --extra dev --extra docs --extra test

# Install pre-commit hooks (enforces code quality)
pre-commit install

# Verify installation
uv run 5e2pdf --version
```

### Directory Structure

```
5e2pdf/
├── src/dnd5e/           # Main package source
│   ├── core/            # Core functionality
│   ├── models/          # Data models
│   ├── cli/             # Command-line interface
│   └── utils/           # Utility functions
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── performance/    # Performance tests
├── docs/               # Documentation source
└── scripts/            # Development scripts
```

### Code Quality Standards

#### **Type Safety (Required)**

- **Python 3.12+ type hints** for all functions and methods
- **mypy strict mode** enforced in CI
- **Protocol-based design** for interfaces and dependency injection

#### **Code Style (Enforced)**

- **ruff** for linting and formatting (line length: 88 characters)
- **Import sorting** with first-party package `dnd5e`
- **Pre-commit hooks** ensure consistent formatting

#### **Testing (Comprehensive)**

- **pytest** with asyncio, coverage, and parallel execution support
- **Minimum 90% code coverage** required
- **Test categories**: unit, integration, performance
- **Test markers**: `@pytest.mark.slow`, `@pytest.mark.integration`

#### **Security & Quality**

- **bandit** security scanning
- **pip-audit** vulnerability checking
- **Architectural validation** prevents circular imports

## Development Workflow

### Issue-Driven Development (Required)

**Every contribution must start with a GitHub issue:**

1. **Create or find an issue** describing the work
2. **Get approval** for significant changes
3. **Create branch** using format: `feat/123-short-description` or `fix/123-short-description`
4. **Implement** using TDD workflow
5. **Submit PR** referencing the issue

### Test-Driven Development (TDD)

**Required workflow for all feature development:**

1. **Explore**: Read relevant code and understand requirements
2. **Plan**: Design implementation approach and identify dependencies
3. **Write Tests**: Define expected behavior with comprehensive test cases
4. **Implement**: Write code to make tests pass
5. **Validate**: Ensure all tests pass and quality checks succeed

### Git Workflow

#### **Branch Strategy**

- **`main`**: Production releases (protected, auto-deployed)
- **`develop`**: Main development branch
- **`feat/<issue>-<description>`**: Feature branches from `develop`
- **`fix/<issue>-<description>`**: Bug fix branches from `develop`

#### **Commit Standards**

- **Format**: [Conventional Commits](https://www.conventionalcommits.org/)
- **Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`
- **Examples**:

  ```
  feat(loaders): implement dual-file content merging
  fix(cli): resolve LaTeX compiler configuration bug
  docs(api): add ContentMerger usage examples
  ```

#### **Merge Strategy**

- **Feature/fix → develop**: Squash and merge
- **Release → main**: Merge commit with tag

### Running Tests

We provide comprehensive Makefile targets for all testing workflows:

```bash
# Quick testing workflow
make test              # Run fast tests (excludes slow tests)
make test-all          # Run all tests including slow ones

# Test with performance monitoring
make test-perf         # Run fast tests with performance monitoring
make test-perf-all     # Run all tests with performance monitoring

# Test quality validation
make test-quality-gate # Check test quality gates
make test-quality-strict # Strict test quality validation

# Direct pytest usage (if needed)
uv run pytest                      # All tests
uv run pytest tests/unit/          # Unit tests only
uv run pytest -m "not slow"        # Skip slow tests
uv run pytest --cov=dnd5e --cov-report=html  # With coverage
```

### Code Quality Checks

Use our comprehensive Makefile targets for consistent quality checks:

```bash
# Development workflow
make check             # Run all code quality checks (ruff, mypy, imports, boundaries)
make security          # Run security scans (pip-audit, bandit)
make format            # Format code with ruff

# All-in-one commands
make all               # Run all checks, security, and tests
make ci-check          # Run all quality and security checks (CI-ready)

# Individual quality checks (if needed)
make ruff              # Run ruff formatting and checks
make mypy              # Run type checking
make imports           # Check for circular imports
make boundaries        # Check architectural boundaries
make pip-audit         # Security vulnerability scan
make bandit            # Static security analysis

# Direct tool usage (if needed)
uv run ruff check .                 # Linting
uv run ruff format .                # Format code
uv run mypy src/                    # Type checking
uv run bandit -r src/               # Security scanning
```

## Pull Request Process

### Before Submitting

**Automated Checks (must pass):**

```bash
# Quick validation before submitting
make ci-fast           # Fast CI checks (ruff, mypy, fast tests)
make all               # Complete local validation

# Or run individual checks
make check             # All code quality checks
make security          # Security scans
make test              # Fast tests

# Legacy direct commands (if needed)
uv run pytest                       # All tests pass
uv run ruff check .                 # No linting errors
uv run mypy src/                    # Type checking passes
uv run bandit -r src/               # Security scan clean
```

### Pull Request Requirements

**Required for all PRs:**

- [ ] **Links to GitHub issue** (format: "Fixes #123" or "Addresses #123")
- [ ] **All CI checks pass** (tests, linting, security, docs)
- [ ] **Code coverage maintained** (minimum 90%)
- [ ] **Type annotations complete** (mypy strict mode)
- [ ] **Tests added** for new functionality
- [ ] **Documentation updated** for API changes
- [ ] **Conventional commit format** used
- [ ] **No breaking changes** without major version bump

### PR Template

Use this template for your pull request description:

```markdown
## Summary
Brief description of changes and motivation.

## Changes
- List of specific changes made
- Highlight any breaking changes

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Issue referenced in PR title/description
- [ ] Tests pass locally
- [ ] Code follows project patterns
- [ ] Documentation updated
```

### Code Review Checklist

**Reviewers should verify:**

#### **Functionality**

- [ ] Code solves the stated problem
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] Performance impact is acceptable

#### **Code Quality**

- [ ] Follows established patterns and conventions
- [ ] Type hints are comprehensive and accurate
- [ ] No code duplication or unnecessary complexity
- [ ] Protocol-based design used for interfaces

#### **Testing**

- [ ] Test coverage is comprehensive
- [ ] Tests are well-organized and readable
- [ ] Integration tests cover realistic scenarios
- [ ] Performance tests added for critical paths

#### **Documentation**

- [ ] API documentation updated for public interfaces
- [ ] Code comments explain "why" not "what"
- [ ] Examples provided for complex functionality

## Advanced Contributions

### Adding New Content Types

**Extending the model system:**

1. **Create model class** inheriting from base model
2. **Implement protocols**: `DeepIndexable` for searchability
3. **Add validation** using Pydantic validators
4. **Update loaders** to handle new format
5. **Add comprehensive tests** including edge cases

### Performance Optimization

**Key areas for optimization:**

- **Caching strategies**: Extend LRU cache implementations
- **Async processing**: Add async/await support to I/O operations
- **Memory usage**: Optimize large dataset handling
- **Parsing performance**: Improve JSON processing speed

### Architecture Extensions

**Extension points:**

- **Custom loaders**: Implement `ContentLoader` protocol
- **Merger strategies**: Extend `ContentMerger` for new formats
- **Template engines**: Alternative rendering backends
- **Output formats**: Beyond LaTeX/PDF generation

## Release Process

### Version Management

```bash
# Bump version (automated)
python scripts/bump_version.py minor  # or major, patch

# Validate version
python scripts/get_version.py
```

### Release Workflow

1. **Feature freeze**: Merge all features to `develop`
2. **Version bump**: Update version in `pyproject.toml`
3. **Release notes**: Generated automatically from conventional commits
4. **Create release**: GitHub Actions handles building and publishing
5. **Deploy docs**: Automatic deployment to GitHub Pages

## Community Guidelines

### Communication

- **GitHub Issues**: Primary communication for bugs and features
- **Pull Requests**: Code-focused discussions
- **Documentation**: Comprehensive examples and guides

### Recognition

- **Contributors**: Listed in project documentation
- **Major contributions**: Highlighted in release notes
- **Continuous contributors**: May be invited as maintainers

## Getting Help

### Resources

- **[Architecture Guide](architecture.md)**: System design and components
- **[API Documentation](api/index.md)**: Detailed API reference
- **[Implementation Guides](implementation/index.md)**: Step-by-step tutorials

### Troubleshooting

**Environment Diagnostics:**

```bash
# Quick environment check
make doctor            # Comprehensive environment diagnosis

# Dependency issues
make upgrade           # Upgrade all dependencies
make clean-all         # Deep clean including virtual environment
```

**Common issues:**

- **uv not found**: Install uv using official installer
- **Type errors**: Run `make mypy` or `uv run mypy src/` for detailed error messages
- **Test failures**: Use `make test` or `uv run pytest -v` for verbose output
- **Pre-commit issues**: Run `pre-commit run --all-files` to fix
- **Environment issues**: Run `make doctor` for comprehensive diagnosis

**Getting support:**

1. Run `make doctor` and include output in issue reports
2. Check existing GitHub issues
3. Search documentation for similar problems
4. Create detailed issue with reproduction steps
5. Include environment information (`uv run 5e2pdf --version`)

Thank you for contributing to 5e2pdf! Your contributions help make D&D content more accessible through high-quality PDF generation.
