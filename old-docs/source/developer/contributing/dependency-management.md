# Dependency Management

This document outlines the dependency management strategy for 5e2pdf, covering best practices for maintaining reliable and secure dependencies.

## Overview

This project uses a three-layer approach to dependency management for reliability and flexibility:

1. **pyproject.toml** - Liberal constraints for compatibility
2. **uv.lock** - Exact versions for reproducibility
3. **Regular updates** - Controlled upgrade process

## Constraint Strategy

### Version Bounds

- **Lower bounds**: Set to minimum required version for needed features
- **Upper bounds**: Cap at next major version to prevent breaking changes
- **Format**: `package>=min_version,<next_major_version>`

### Examples

```toml
# Runtime dependencies - conservative bounds
"pydantic>=2.0.0,<3.0.0"     # Cap at major version
"typer>=0.9.0,<1.0.0"        # Pre-1.0 projects are volatile
"requests>=2.31.0,<3.0.0"    # Stable APIs, major version cap
"aiofiles>=23.0.0,<25.0.0"   # Allow multiple major versions for stable APIs

# Documentation - mixed strategy
"sphinx==8.2.3"              # Pinned for reproducible builds
"furo>=2024.1.29"            # Date-versioned theme, use >=
"myst-parser==4.0.1"         # Pinned for stability

# Development tools - broader ranges
"pytest>=8.0.0,<9.0.0"      # Standard major version cap
"ruff>=0.12.2,<1.0.0"       # Pre-1.0, cap at 1.0
"types-pyyaml>=6.0.12.20250516"  # Type stubs, >= only
```

### Exceptions

- **Type stubs**: Often don't follow semver, use `>=` only (e.g., `types-pyyaml>=6.0.12.20250516`)
- **Security packages**: Like `certifi>=2025.7.14`, allow patch updates freely
- **Date-versioned packages**: Use `>=` for latest security fixes (e.g., `furo>=2024.1.29`)
- **Documentation pinning**: Some docs tools pinned for reproducible builds (`sphinx==8.2.3`)
- **Stable multi-major**: Some packages allow multiple major versions (`aiofiles>=23.0.0,<25.0.0`)

## Dependency Categories

### Runtime Dependencies (`dependencies`)

- Core packages needed for application to run
- Conservative version bounds
- Avoid dev/test packages here

### Development Dependencies (`project.optional-dependencies.dev`)

- Testing, linting, type checking tools
- Broader version ranges acceptable
- Include dev-specific packages (coverage, pytest-*, etc.)

### Documentation Dependencies (`project.optional-dependencies.docs`)

- Sphinx and documentation tools
- **Pinned versions**: Documentation builds need to be reproducible, so some packages are pinned to exact versions (e.g., `sphinx==8.2.3`, `myst-parser==4.0.1`)
- Mixed strategy: Core tools pinned, supporting packages use ranges

### Optional Feature Dependencies (`project.optional-dependencies`)

- Feature-specific dependencies like `images` and `xml`
- Use standard version range approach

### Dependency Groups (`dependency-groups.dev`)

- Development tools including testing, linting, and type checking
- Uses broader version ranges than runtime dependencies
- **Type stubs**: Use `>=` only as they don't follow semver (e.g., `types-pyyaml>=6.0.12.20250516`)

## Update Process

### Low-Risk Updates (Patch/Minor)

1. Check package changelogs for breaking changes
2. Update version constraints in pyproject.toml
3. Run `uv lock` to update lock file
4. Run full test suite
5. Check linting and type checking
6. Commit if all passes

### Medium/High-Risk Updates (Major versions)

1. Create dedicated branch
2. Update one package at a time
3. Read migration guides
4. Update code if needed
5. Extensive testing
6. Update documentation if APIs changed

### Regular Maintenance

- Monthly review of outdated packages using `uv show --outdated`
- Quarterly security audit with `pip-audit`
- Annual major version review

## Tools

- `uv show --outdated` - Check for available updates
- `uv tree` - Examine dependency tree
- `uv run pip-audit` - Security vulnerability scanning (included in dev dependencies)
- `uv run bandit -r src/` - Security linting (included in dev dependencies)
- `uv lock --upgrade` - Update all packages within constraints
- `uv sync --extra dev` - Install development dependencies

## Benefits

- **Predictable builds** via lock file
- **Security updates** through regular maintenance
- **Breaking change protection** via upper bounds
- **Flexibility** for compatible updates
- **Clear separation** of runtime vs dev dependencies
