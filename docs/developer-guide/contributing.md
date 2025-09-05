---
title: Contributing
description: Guide for contributing to studiorum - code, documentation, and community
---

# Contributing to Studiorum

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or helping other users, your contribution makes studiorum better for everyone.

## Getting Started

### Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork**:

   ```bash
   git clone https://github.com/yourusername/studiorum.git
   cd studiorum
   git checkout develop # All features are built on this branch
   ```

3. **Set up development environment**:

   ```bash
   # Install uv (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies
   uv sync

   # Install pre-commit hooks
   uv run pre-commit install
   ```

4. **Verify setup**:

   ```bash
   # Run tests
   uv run pytest tests/unit/ -v

   # Check code quality
   uv run ruff check src/
   uv run mypy src/
   ```

### Project Structure

Understanding the codebase layout helps with contributions:

```
studiorum/
├── src/studiorum/          # Main package code
│   ├── core/               # Core services and models
│   │   ├── container.py    # Dependency injection
│   │   ├── models/         # Pydantic data models
│   │   └── services/       # Service protocols
│   ├── cli/                # Command-line interface
│   ├── mcp/                # MCP server implementation
│   ├── renderers/          # Output rendering system
│   └── latex_engine/       # LaTeX compilation
├── tests/                  # Comprehensive test suite
│   ├── unit/               # Fast, isolated tests
│   ├── integration/        # Real data integration tests
│   └── latex/              # LaTeX compilation tests
└── docs/                   # Documentation (MkDocs)
```

## Types of Contributions

### 🐛 Bug Reports

**Before submitting a bug report:**

- Search existing issues to avoid duplicates
- Test with the latest version
- Gather relevant system information

**Bug report template:**

```markdown
## Bug Description
A clear description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Run command '...'
2. With input '...'
3. See error

## Expected Behavior
What you expected to happen.

## Environment
- OS: [e.g., macOS 14.0, Ubuntu 22.04]
- Python version: [e.g., 3.12.0]
- Studiorum version: [e.g., 0.5.0]
- LaTeX distribution: [e.g., MacTeX 2023]

## Additional Context
- Error messages (full output)
- Relevant configuration files
- Sample content that triggers the issue
```

**Submit bug reports** at: <https://github.com/sargeant/studiorum/issues>

### 💡 Feature Requests

**Before submitting a feature request:**

- Check if it's already requested
- Consider if it fits studiorum's scope
- Think about implementation impact

**Feature request template:**

```markdown
## Feature Description
A clear description of the feature you'd like to see.

## Use Case
Describe the problem this feature would solve and who would benefit.

## Proposed Solution
Your idea for how this could be implemented.

## Alternative Solutions
Other approaches you've considered.

## Implementation Notes
- Would this require breaking changes?
- Are there any performance considerations?
- Does this affect the MCP server interface?
```

### 🔧 Code Contributions

#### Development Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feat/new-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes** following our coding standards

3. **Write tests** for your changes:

   ```bash
   # Unit tests (required)
   tests/unit/test_your_feature.py

   # Integration tests (if applicable)
   tests/integration/test_your_feature.py
   ```

4. **Ensure quality checks pass**:

   ```bash
   # Code formatting and linting
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/

   # Type checking
   uv run mypy src/

   # Run tests
   uv run pytest tests/unit/ -v

   # Full quality check
   make lint && make test
   ```

5. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: add new awesome feature

   - Implement core functionality
   - Add comprehensive tests
   - Update documentation"
   ```

6. **Push and create pull request**:

   ```bash
   git push origin feat/new-feature-name
   ```

#### Pull Request Guidelines

**Pull Request Template:**

```markdown
## Description
Brief description of the changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that causes existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Changes Made
- List the key changes
- Include any new dependencies
- Mention configuration changes

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All existing tests pass
- [ ] Manual testing completed

## Documentation
- [ ] Code is self-documenting
- [ ] Docstrings added/updated
- [ ] User documentation updated (if applicable)
- [ ] API documentation updated (if applicable)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] No console.log or debug print statements
- [ ] Performance impact considered
- [ ] Breaking changes documented
```

**Pull Request Review Process:**

1. **Automated checks** must pass (CI, code quality, tests)
2. **Code review** by maintainers
3. **Testing** of new functionality
4. **Documentation review** (if applicable)
5. **Merge** after approval

#### Coding Standards

**Code Style:**

- Follow [PEP 8](https://pep8.org/) Python style guide
- Use Ruff for linting and formatting
- Maximum line length: 88 characters (Black default)
- Use type hints for all functions and methods

**Architecture Patterns:**

- Use dependency injection through the service container
- Implement Result types for operations that can fail
- Follow protocol-based interfaces for loose coupling
- Use Pydantic models for data validation

**Error Handling:**

```python
# ✅ Good - Use Result types
def risky_operation(data: str) -> Result[ProcessedData, str]:
    if not data:
        return Error("Input cannot be empty")

    try:
        result = process_data(data)
        return Success(result)
    except ValueError as e:
        return Error(f"Processing failed: {e}")

# ✅ Good - Handle Result types with isinstance (current pattern)
result = risky_operation(input_data)
if isinstance(result, Error):
    logger.error(f"Operation failed: {result.error}")
    return

processed = result.unwrap()  # Type checker knows this is Success
```

**Testing Standards:**

```python
# ✅ Good - Clear test structure
class TestFeature:
    def setup_method(self):
        """Reset global state for test isolation."""
        reset_global_container()

    def test_feature_with_valid_input(self):
        """Test successful operation with valid data."""
        # Arrange
        input_data = create_test_data()

        # Act
        result = feature_function(input_data)

        # Assert
        assert isinstance(result, Success)
        assert result.unwrap().property == "expected_value"

    def test_feature_with_invalid_input(self):
        """Test error handling with invalid data."""
        with pytest.raises(ValidationError):
            feature_function(invalid_data)
```

**Documentation Standards:**

```python
def convert_adventure(
    adventure_name: str,
    include_appendices: bool = False,
    output_format: str = "latex"
) -> Result[ConversionResult, str]:
    """
    Convert a 5e adventure to the specified format.

    Args:
        adventure_name: Name or abbreviation of the adventure
        include_appendices: Whether to include creature/spell appendices
        output_format: Output format ("latex" or "pdf")

    Returns:
        Success with ConversionResult containing the output, or Error with description

    Example:
        >>> result = convert_adventure("Lost Mine of Phandelver", include_appendices=True)
        >>> if isinstance(result, Success):
        ...     print(f"Converted to {len(result.unwrap().content)} characters")
    """
```

### 📚 Documentation Contributions

Documentation improvements are always welcome!

**Types of documentation:**

- **User guides**: Help users accomplish tasks
- **Developer guides**: Help contributors understand the codebase
- **API documentation**: Document functions and classes
- **Examples**: Show real-world usage patterns

**Documentation workflow:**

1. **Fork and clone** the repository
2. **Make changes** to files in `docs/`
3. **Test locally**:

   ```bash
   uv run mkdocs serve
   # Visit http://127.0.0.1:8000 to preview
   ```

4. **Submit pull request** with documentation changes

**Documentation standards:**

- Use clear, concise language
- Include code examples for technical content
- Test all code examples
- Follow existing style and structure
- Use proper Markdown formatting

### 🎨 Design and UX

Help improve the visual design and user experience:

- **MkDocs theme**: CSS/JS improvements for documentation
- **CLI interface**: Better error messages and help text
- **LaTeX templates**: Improved PDF layouts and styling
- **MCP tool interfaces**: Better AI agent integration

### 🧪 Testing

Contribute to our test suite:

**Test types needed:**

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows
- **Performance tests**: Ensure scalability
- **LaTeX tests**: Verify PDF generation

**Testing guidelines:**

```python
# Test file structure
tests/
├── unit/
│   ├── core/
│   │   ├── test_omnidexer.py
│   │   └── test_container.py
│   └── renderers/
│       └── test_latex_renderer.py
├── integration/
│   ├── test_adventure_conversion.py
│   └── test_mcp_server.py
└── latex/
    ├── test_pdf_generation.py
    └── test_template_rendering.py
```

**Test naming:**

```python
# ✅ Good - Descriptive test names
def test_omnidexer_loads_creature_data_successfully():
def test_adventure_conversion_includes_appendices_when_requested():
def test_mcp_tool_returns_error_for_invalid_creature_name():

# ❌ Bad - Generic test names
def test_omnidexer():
def test_conversion():
def test_mcp():
```

## Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/) for clear history:

**Format:**

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
# Simple feature
git commit -m "feat: add spell search filters for school and level"

# Bug fix with scope
git commit -m "fix(mcp): resolve creature lookup timeout issues"

# Breaking change
git commit -m "feat!: redesign content resolution API

BREAKING CHANGE: ContentResolver.resolve() now returns Result type instead of throwing exceptions"

# Documentation update
git commit -m "docs: add MCP integration examples for campaign management"
```

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, backwards compatible

### Release Workflow

**For maintainers:**

1. **Create release branch**:

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/1.2.0
   ```

2. **Update version and changelog**:

   ```bash
   # Update pyproject.toml version
   # Update CHANGELOG.md
   # Update version in docs
   ```

3. **Final testing**:

   ```bash
   make test-all
   make docs-build
   make integration-test
   ```

4. **Create pull request** to `main` branch

5. **After merge, tag release**:

   ```bash
   git checkout main
   git pull origin main
   git tag v1.2.0
   git push origin v1.2.0
   ```

6. **GitHub Actions** will automatically:
   - Build and test the release
   - Publish to PyPI
   - Create GitHub release
   - Deploy documentation

## Community

### Getting Help

- **GitHub Discussions**: [Ask questions and share ideas](https://github.com/sargeant/studiorum/discussions)
- **GitHub Issues**: [Report bugs and request features](https://github.com/sargeant/studiorum/issues)
- **Discord**: Join our development community (link in README)

### Code Review Process

**For contributors:**

- Be open to feedback
- Respond promptly to review comments
- Make requested changes in additional commits
- Don't force-push after review starts

**For reviewers:**

- Be constructive and specific
- Focus on code quality and maintainability
- Consider performance and security implications
- Approve when ready, request changes if needed

### Recognition

We recognize contributors in several ways:

- **CONTRIBUTORS.md**: All contributors are listed
- **Release notes**: Major contributions are highlighted
- **GitHub**: Contributor profiles show activity
- **Documentation**: Examples may feature contributor code

## Development Tips

### IDE Setup

**VS Code recommended extensions:**

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml"
  ]
}
```

**VS Code settings:**

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### Performance Debugging

**Profile code performance:**

```python
import cProfile
import pstats

def profile_function():
    """Profile a specific function."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Your code here
    result = expensive_operation()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return result
```

**Memory profiling:**

```bash
# Install memory profiler
uv add --dev memory-profiler

# Profile memory usage
uv run python -m memory_profiler your_script.py
```

### Debugging Tips

**Use the debugger effectively:**

```python
# Add breakpoints in code
import pdb; pdb.set_trace()

# Or use the more modern version
breakpoint()

# Debug specific test
uv run pytest tests/unit/test_feature.py::test_specific_case -v -s --pdb
```

**Enable debug logging:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable specific logger
logging.getLogger('studiorum.core.omnidexer').setLevel(logging.DEBUG)
```

## Troubleshooting

### Common Issues

**Import errors after adding new dependencies:**

```bash
# Regenerate lock file
uv sync --upgrade

# Clean and reinstall
rm -rf .venv
uv sync
```

**Test failures in CI but not locally:**

```bash
# Reset test environment
uv run python -c "from studiorum.core.container import reset_global_container; reset_global_container()"

# Run tests in same environment as CI
uv run pytest --maxfail=1 -v
```

**Type checker errors:**

```bash
# Run mypy on specific files
uv run mypy src/studiorum/core/models/

# Check type ignore usage
grep -r "type: ignore" src/
```

**Pre-commit hook failures:**

```bash
# Run hooks manually
uv run pre-commit run --all-files

# Update hook versions
uv run pre-commit autoupdate
```

## Thank You

Thank you for contributing to studiorum! Your efforts help make 5e content more accessible and easier to work with for DMs and players around the world.

Every contribution, no matter how small, makes a difference:

- 🐛 Bug reports help us identify and fix issues
- 💡 Feature requests guide our development priorities
- 🔧 Code contributions add new capabilities
- 📚 Documentation helps users succeed
- 🧪 Tests ensure reliability and quality
- 💬 Community participation makes everyone feel welcome

Questions? Ideas? Want to get involved? Join our community!

- **GitHub**: [https://github.com/sargeant/studiorum](https://github.com/sargeant/studiorum)
- **Discussions**: [https://github.com/sargeant/studiorum/discussions](https://github.com/sargeant/studiorum/discussions)
- **Issues**: [https://github.com/sargeant/studiorum/issues](https://github.com/sargeant/studiorum/issues)
