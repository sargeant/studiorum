# Developer Onboarding Guide

Welcome to the 5e2pdf project! This guide will get you up and running with the development environment using our comprehensive Makefile workflow system.

## Quick Setup

### 1. Prerequisites Check

Before starting, ensure you have the required tools:

```bash
# Check if you have the required tools
python --version     # Should be 3.12+
git --version        # Any recent version
```

If you don't have `uv` installed:

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Check environment health
make doctor          # Diagnose any setup issues

# Install dependencies
make uv             # Install development dependencies
```

### 3. Verify Installation

```bash
# Run comprehensive verification
make ci-fast        # Quick validation (formatting, types, fast tests)

# If everything passes, you're ready to develop!
```

## Development Workflow

### Daily Development Commands

Our Makefile provides a comprehensive workflow for daily development:

```bash
# See all available commands
make help           # Comprehensive help with organized sections

# Development cycle
make format         # Format your code
make check          # Run all quality checks (ruff, mypy, imports, boundaries)
make test           # Run fast tests while developing
make security       # Run security scans

# All-in-one validation
make all            # Run everything: checks + security + tests
```

### Pre-Commit Workflow

Before committing any changes:

```bash
# Quick validation
make ci-fast        # Fast CI checks (recommended for rapid iteration)

# Complete validation
make ci-check       # All quality and security checks
make ci-test        # Full test suite with coverage

# If you want to run everything
make ci-full        # Complete CI pipeline
```

### Working with Tests

Our test system provides multiple levels of validation:

```bash
# Development testing
make test           # Fast tests (excludes slow tests) - use during development
make test-all       # All tests including slow ones - use before commits

# Performance monitoring
make test-perf      # Fast tests with performance monitoring
make test-perf-all  # All tests with performance monitoring

# Quality validation
make test-quality-gate    # Check test quality gates
make test-quality-strict  # Strict test quality validation
```

### Performance Monitoring

Track performance regressions during development:

```bash
# Create baseline (do this once per feature)
make test-perf-baseline

# Check for regressions
make test-perf-compare   # Compare current performance against baseline
```

## Environment Management

### Diagnostics

When things go wrong, use our diagnostic tools:

```bash
# Comprehensive environment diagnosis
make doctor         # Check Python, UV, dependencies, git status, disk space

# Common fixes
make clean          # Clean build artifacts
make clean-all      # Deep clean including virtual environment
make upgrade        # Upgrade all dependencies
```

### Maintenance

Keep your environment healthy:

```bash
# Clean up build artifacts
make clean          # Remove Python cache, coverage files, build artifacts

# Deep cleaning (when needed)
make clean-all      # Remove virtual environment and UV cache

# Dependency updates
make upgrade        # Upgrade to latest compatible dependency versions
```

## CI/CD Integration

Understanding our CI pipeline:

```bash
# Local CI simulation
make ci-fast        # Quick feedback (use during development)
make ci-check       # Quality and security checks (use before commits)
make ci-test        # Full test suite with coverage (use before PRs)
make ci-full        # Complete CI pipeline (use for final validation)
```

**CI Target Breakdown:**
- `ci-fast`: Formatting, type checking, fast tests (~2-3 minutes)
- `ci-check`: All quality and security checks (~3-5 minutes)
- `ci-test`: Full test suite with coverage (~5-10 minutes)
- `ci-full`: Everything combined (~8-15 minutes)

## Documentation Workflow

Working with documentation:

```bash
# Build and view docs
make docs           # Build docs and open in browser

# Development server
make docs-serve     # Auto-rebuilding docs server

# Validation
make docs-check     # Check for broken links and syntax errors

# Cleanup
make docs-clean     # Clean documentation build artifacts
```

## Common Workflows

### New Feature Development

```bash
# 1. Start development
make doctor         # Verify environment
git checkout -b feat/my-new-feature

# 2. During development
make format         # Keep code formatted
make check          # Validate quality
make test           # Run tests frequently

# 3. Before committing
make ci-fast        # Quick validation
git add .
git commit -m "feat: my new feature"

# 4. Before creating PR
make ci-full        # Complete validation
git push origin feat/my-new-feature
```

### Bug Fix Workflow

```bash
# 1. Reproduce issue
make test           # Run tests to identify failing cases

# 2. Fix and validate
make check          # Ensure code quality
make test           # Verify fix works
make test-all       # Ensure no regressions

# 3. Submit fix
make ci-check       # Final validation
git commit -m "fix: resolve issue description"
```

### Performance Investigation

```bash
# 1. Create baseline
make test-perf-baseline

# 2. Make changes
# ... your code changes ...

# 3. Check for regressions
make test-perf-compare

# 4. Generate reports
make test-perf-report   # Detailed performance analysis
```

## Troubleshooting

### Common Issues and Solutions

**Environment Issues:**
```bash
make doctor         # Diagnose environment problems
make clean-all      # Reset environment completely
make upgrade        # Update dependencies
```

**Test Failures:**
```bash
make test           # Run with default settings
make test-all       # Include slow tests
# Check output for specific failure details
```

**Quality Check Failures:**
```bash
make format         # Fix formatting issues
make mypy           # Check type issues specifically
make ruff           # Check linting issues specifically
```

**Performance Regressions:**
```bash
make test-perf-baseline    # Create new baseline
make test-perf-compare     # Compare against baseline
make test-perf-report      # Get detailed analysis
```

### Getting Help

1. **Environment Diagnosis**: Always start with `make doctor`
2. **Check Documentation**: Our help system is comprehensive: `make help`
3. **Ask for Help**: Include `make doctor` output in issue reports
4. **Check CI Logs**: Use the same commands locally that CI uses

## Advanced Usage

### Parallel Execution

Our Makefile is optimized for parallel execution:

```bash
# These can run in parallel (make -j)
make -j4 check      # Run quality checks in parallel where safe
```

**Note**: Dependency sync targets (`uv`, `uv-docs`, `ci-install`) run sequentially for consistency.

### Custom Workflows

You can combine targets for custom workflows:

```bash
# Quick development cycle
make format check test

# Pre-commit validation
make ci-fast

# Release preparation
make ci-full docs-check
```

## Summary

The 5e2pdf Makefile provides a comprehensive development experience:

- **30+ targets** for all development needs
- **Organized help system** with logical groupings
- **CI/CD integration** with multiple validation levels
- **Performance monitoring** with regression detection
- **Environment diagnostics** for troubleshooting
- **Parallel execution** optimized for speed

**Essential Commands to Remember:**
- `make help` - See all available commands
- `make doctor` - Diagnose environment issues
- `make ci-fast` - Quick validation during development
- `make all` - Complete local validation

Welcome to the team! The Makefile is designed to make your development experience smooth and productive. When in doubt, run `make help` or `make doctor`.
