# Makefile for 5e2pdf project
# All commands run via uv (https://github.com/astral-sh/uv)

# Configuration for fail-fast behavior and error checking
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# Configuration variables
PYTHON_VERSION := 3.12
UV := uv run
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs
SCRIPTS_DIR := scripts

.PHONY: help uv uv-docs test mypy pip-audit bandit pre-push docs all check security format clean clean-all ci-install ci-test ci-check ci-full test-perf-baseline test-perf-compare test-perf-compare-legacy test-quality-gate test-quality-strict doctor upgrade

# Parallel execution control - only sync targets should be serial
# This allows make to run independent targets in parallel while ensuring
# dependency synchronization targets (uv sync commands) run sequentially
.NOTPARALLEL: uv uv-docs ci-install

# Default target: show help
help:
	@echo "Available targets:"
	@echo "  help         - Show this help message"
	@echo "  all          - Run all checks, security, and tests"
	@echo "  check        - Run code quality checks (ruff, mypy, imports, boundaries)"
	@echo "  security     - Run security scans (pip-audit, bandit)"
	@echo "  test         - Run tests"
	@echo "  format       - Format code with ruff"
	@echo "  docs         - Build and open documentation"
	@echo "  clean        - Clean build artifacts"
	@echo "  clean-all    - Deep clean including virtual environment"
	@echo ""
	@echo "Development targets:"
	@echo "  ruff         - Run ruff formatting and checks"
	@echo "  mypy         - Run type checking"
	@echo "  imports      - Check for circular imports"
	@echo "  boundaries   - Check architectural boundaries"
	@echo "  pip-audit    - Security vulnerability scan"
	@echo "  bandit       - Static security analysis"
	@echo ""
	@echo "Smart test selection:"
	@echo "  test-quick        - Quick feedback (changed files + fast tests)"
	@echo "  test-impacted     - Run only tests impacted by changes"
	@echo "  test-focused      - Run tests for current feature branch"
	@echo "  test-impact-analyze - Analyze which tests are impacted"
	@echo ""
	@echo "Test performance and quality:"
	@echo "  test-profile      - Run tests with performance profiling"
	@echo "  test-perf-baseline - Create performance baseline"
	@echo "  test-perf-compare - Compare against baseline"
	@echo "  test-perf-track   - Track performance history"
	@echo "  test-perf-trends  - Show performance trends"
	@echo "  test-perf         - Run fast performance tests (legacy)"
	@echo "  test-perf-all     - Run all performance tests (legacy)"
	@echo "  test-quality      - Analyze test quality metrics"
	@echo "  test-quality-gate - Check quality gates"
	@echo "  test-quality-strict - Strict quality validation"
	@echo ""
	@echo "Documentation:"
	@echo "  docs-serve   - Start documentation auto-rebuild server"
	@echo "  docs-check   - Check documentation for issues"
	@echo ""
	@echo "CI/CD targets:"
	@echo "  ci-check     - Run all quality and security checks"
	@echo "  ci-test      - Run full test suite with coverage"
	@echo "  ci-full      - Complete CI pipeline"
	@echo ""
	@echo "Diagnostics and maintenance:"
	@echo "  doctor       - Diagnose environment and dependencies"
	@echo "  upgrade      - Upgrade project dependencies"

# Run all pre-push checks
all: check security test
	@echo "All pipeline checks completed successfully"

check: ruff mypy imports boundaries
	@echo "All code quality checks passed"

security: uv pip-audit bandit-medium
	@echo "All security checks passed"

# Sync environment (dev dependencies)
uv:
	@echo "Syncing development environment..."
	uv sync --group dev

# Sync environment (docs dependencies)
uv-docs:
	@echo "Syncing documentation environment..."
	uv sync --extra docs

# Checks and tools

## Linting and formatting
ruff: uv
	@echo "Running ruff formatting and checks..."
	$(UV) ruff format $(SRC_DIR) $(TEST_DIR)
	$(UV) ruff check $(SRC_DIR) $(TEST_DIR) || (echo "Ruff checks failed"; exit 1)

## Code formatting target
format: uv
	@echo "Formatting code..."
	$(UV) ruff format $(SRC_DIR) $(TEST_DIR)
	@echo "Code formatted"

## Static type checking
mypy: uv
	@echo "Running mypy type checking..."
	$(UV) mypy $(SRC_DIR)/ || (echo "Type checking failed"; exit 1)

## Check for circular imports
imports: uv
	@echo "Checking for circular imports..."
	$(UV) python $(SCRIPTS_DIR)/check_circular_imports.py $(SRC_DIR)/dnd5e/ --fail-on-cycles || (echo "Circular import check failed"; exit 1)

## Check architectural boundaries
boundaries: uv
	@echo "Checking architectural boundaries..."
	$(UV) python $(SCRIPTS_DIR)/check_architectural_boundaries.py $(SRC_DIR)/dnd5e/ --fail-on-violations || (echo "Architectural boundary check failed"; exit 1)

# Security checks
## Security vulnerability scan
pip-audit: uv
	@echo "Running security vulnerability scan..."
	$(UV) pip-audit --desc=off || (echo "Security vulnerability scan failed"; exit 1)

## Static security analysis (medium severity)
bandit-medium: uv
	@echo "Running static security analysis (medium severity)..."
	$(UV) bandit --severity-level medium -r $(SRC_DIR)/ || (echo "Security analysis failed"; exit 1)

## Static security analysis (all severity)
bandit: uv
	@echo "Running static security analysis..."
	$(UV) bandit -ll -r $(SRC_DIR)/ || (echo "Security analysis failed"; exit 1)

# Run all tests
test: uv
	@echo "Running all tests..."
	$(UV) pytest

# Speed-based test targets for development workflow
## Run fast tests only (<1s per test)
test-fast: uv
	@echo "Running fast tests only..."
	$(UV) pytest -m "fast"

## Run unit tests (excludes integration and slow tests)
test-unit: uv
	@echo "Running unit tests..."
	$(UV) pytest -m "not integration and not slow"

## Run core functionality tests
test-core: uv
	@echo "Running core functionality tests..."
	$(UV) pytest -m "core"

## Run rendering system tests
test-rendering: uv
	@echo "Running rendering system tests..."
	$(UV) pytest -m "rendering"

## Run CLI interface tests
test-cli: uv
	@echo "Running CLI interface tests..."
	$(UV) pytest -m "cli"

## Run integration tests only
test-integration: uv
	@echo "Running integration tests..."
	$(UV) pytest -m "integration"

## Run slow tests only (>10s per test)
test-slow: uv
	@echo "Running slow tests..."
	$(UV) pytest -m "slow"

## Run tests requiring external data
test-data: uv
	@echo "Running tests requiring external data..."
	$(UV) pytest -m "requires_data"

# Smart Test Selection (Phase 4.1)
## Run only tests impacted by current changes
test-impacted: uv
	@echo "Analyzing test impact for current changes..."
	@$(SCRIPTS_DIR)/run_impacted_tests.sh

## Analyze which tests are impacted by changes
test-impact-analyze: uv
	@echo "Analyzing test impact..."
	@git diff --name-only main...HEAD | xargs $(UV) python $(SCRIPTS_DIR)/test_impact_analyzer.py

## Run tests for current feature branch
test-focused: uv
	@echo "Running tests for current feature branch..."
	@$(SCRIPTS_DIR)/run_impacted_tests.sh origin/main

## Quick feedback loop - changed files + fast tests
test-quick: uv
	@echo "Running quick test suite (changed files + fast tests)..."
	@if [ -n "$$(git diff --name-only HEAD 2>/dev/null)" ]; then \
		$(SCRIPTS_DIR)/run_impacted_tests.sh HEAD; \
	else \
		$(UV) pytest -m "fast" --tb=short; \
	fi

# Test Performance and Quality Monitoring (Phase 4.2)
## Run tests with performance profiling
test-profile: uv
	@echo "Running tests with performance profiling..."
	$(UV) pytest --profile -m "not slow" || true
	@echo "Performance report saved to .test-performance-report.json"

## Create performance baseline
test-perf-baseline: uv
	@echo "Creating performance baseline..."
	$(UV) python $(SCRIPTS_DIR)/performance_baseline.py --create-baseline
	@echo "Performance baseline created"

## Compare performance against baseline
test-perf-compare: uv
	@echo "Comparing performance against baseline..."
	$(UV) pytest --profile -m "not slow" || true
	$(UV) python $(SCRIPTS_DIR)/performance_baseline.py --compare

## Track performance history
test-perf-track: uv
	@echo "Tracking performance history..."
	$(UV) pytest --profile -m "not slow" || true
	$(UV) python $(SCRIPTS_DIR)/performance_baseline.py --track

## Show performance trends
test-perf-trends: uv
	@echo "Showing performance trends..."
	$(UV) python $(SCRIPTS_DIR)/performance_baseline.py --trends

## Run legacy performance monitoring (fast)
test-perf: uv
	@echo "Running fast performance tests..."
	$(UV) python $(SCRIPTS_DIR)/test_performance_monitor.py --test-type=fast || (echo "Performance tests failed"; exit 1)
	@echo "Fast performance tests completed"

## Run all tests with legacy performance monitoring
test-perf-all: uv
	@echo "Running all performance tests..."
	$(UV) python $(SCRIPTS_DIR)/test_performance_monitor.py --test-type=all || (echo "Performance tests failed"; exit 1)
	@echo "All performance tests completed"

## Generate performance report
test-perf-report: uv
	@echo "Generating performance report..."
	$(UV) python $(SCRIPTS_DIR)/test_performance_monitor.py --report || (echo "Performance report failed"; exit 1)
	@echo "Performance report generated"

## Compare performance against legacy baseline
test-perf-compare-legacy: uv
	@echo "Comparing performance against legacy baseline..."
	$(UV) python $(SCRIPTS_DIR)/test_performance_monitor.py --compare --fail-on-regression || (echo "Performance regression detected"; exit 1)
	@echo "Performance comparison completed"

## Analyze test quality metrics
test-quality: uv
	@echo "Analyzing test quality metrics..."
	$(UV) python $(SCRIPTS_DIR)/test_quality_metrics.py --report || (echo "Test quality analysis failed"; exit 1)
	@echo "Test quality analysis completed"

## Check test quality gates
test-quality-gate: uv
	@echo "Checking test quality gates..."
	$(UV) python $(SCRIPTS_DIR)/test_quality_metrics.py --check --fail-on-issues || (echo "Test quality gates failed"; exit 1)
	@echo "Test quality gates passed"

## Comprehensive test quality validation
test-quality-strict: uv
	@echo "Running strict test quality validation..."
	$(UV) python $(SCRIPTS_DIR)/test_quality_metrics.py --check --strict --fail-on-issues || (echo "Strict test quality validation failed"; exit 1)
	@echo "Strict test quality validation passed"

# Documentation
## Build HTML docs and open in browser
docs: uv-docs
	@echo "Building documentation..."
	cd $(DOCS_DIR) && $(UV) sphinx-build -b html source _build/html || (echo "Documentation build failed"; exit 1)
	@echo "Documentation built and opened"

## Start documentation auto-rebuild server
docs-serve: uv-docs
	@echo "Starting documentation auto-rebuild server..."
	@echo "Server will be available at http://localhost:8000"
	cd $(DOCS_DIR) && $(UV) sphinx-autobuild source _build/html --host 0.0.0.0 --port 8000 --open-browser || (echo "Documentation server failed to start"; exit 1)

## Clean documentation build artifacts
docs-clean:
	@echo "Cleaning documentation build artifacts..."
	rm -rf $(DOCS_DIR)/_build $(DOCS_DIR)/build
	@echo "Documentation artifacts cleaned"

## Build docs with clean rebuild
docs-rebuild: docs-clean docs
	@echo "Documentation rebuilt successfully"

## Check documentation for issues (broken links, syntax)
docs-check: uv-docs
	@echo "Checking documentation for issues..."
	cd $(DOCS_DIR) && $(UV) sphinx-build -b linkcheck source _build/linkcheck || (echo "Link check failed"; exit 1)
	cd $(DOCS_DIR) && $(UV) sphinx-build -W -b html source _build/html || (echo "Documentation syntax check failed"; exit 1)
	@echo "Documentation checks passed"

## Validate documentation quality and structure
docs-validate: uv-docs
	@echo "Validating documentation quality..."
	$(UV) python $(SCRIPTS_DIR)/validate_docs.py --docs-dir $(DOCS_DIR) || (echo "Documentation validation failed"; exit 1)
	@echo "Documentation validation passed"

## Full documentation validation (strict mode)
docs-validate-strict: uv-docs
	@echo "Running strict documentation validation..."
	$(UV) python $(SCRIPTS_DIR)/validate_docs.py --docs-dir $(DOCS_DIR) --strict || (echo "Strict documentation validation failed"; exit 1)
	@echo "Strict documentation validation passed"

# Cleanup and maintenance
## Clean build artifacts
clean: docs-clean
	@echo "Cleaning build artifacts..."
	@echo "  - Removing Python cache files..."
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "  - Removing coverage files..."
	rm -rf .coverage
	rm -rf htmlcov/
	@echo "  - Removing build artifacts..."
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf build/
	@echo "  - Removing temporary files..."
	find . -name "*.tmp" -delete
	find . -name "*.temp" -delete
	find . -name ".DS_Store" -delete
	@echo "Cleanup completed successfully"

## Deep clean including virtual environment
clean-all: clean
	@echo "Performing deep cleanup..."
	@echo "  - Removing virtual environment..."
	rm -rf .venv/
	@echo "  - Removing UV cache..."
	uv cache clean || true
	@echo "Deep cleanup completed"

# CI/CD Integration
# These targets are designed for continuous integration environments
# and provide different levels of validation based on CI pipeline needs

## Install CI dependencies
# Ensures consistent environment setup across CI runs
ci-install:
	@echo "Installing CI dependencies..."
	uv sync --group dev
	@echo "CI dependencies installed"

## Run CI test suite with coverage
# Full test suite with coverage reporting and JUnit XML for CI integration
# Outputs: coverage.xml, htmlcov/, test-results.xml
# Skips tests marked as ci_broken to avoid CI-specific environment issues
ci-test: ci-install
	@echo "Running CI test suite..."
	$(UV) pytest --cov=dnd5e --cov-report=xml --cov-report=html --junitxml=test-results.xml -m "not ci_broken" || (echo "CI test suite failed"; exit 1)
	@echo "CI test suite completed"

## Run CI checks (quality and security)
# Comprehensive quality and security validation for CI pipelines
ci-check: ci-install check security
	@echo "CI checks completed"

## Full CI pipeline
# Complete validation: install → checks → tests
# Use this for comprehensive CI validation
ci-full: ci-install ci-check ci-test
	@echo "Full CI pipeline completed successfully"

## Lightweight CI for fast feedback
# Quick validation for rapid feedback in development
# Includes: formatting, type checking, fast tests only

# Diagnostics and maintenance
# These targets help diagnose environment issues and maintain the project

## Diagnose environment and dependencies
# Comprehensive environment health check for troubleshooting
# Checks: Python, UV, virtual environment, dependencies, git status, disk space
doctor:
	@echo "Diagnosing development environment..."
	@echo "Python version:"
	@python --version || echo "Python not found"
	@echo ""
	@echo "UV version:"
	@uv --version || echo "UV not found"
	@echo ""
	@echo "Virtual environment status:"
	@if [ -d ".venv" ]; then echo "Virtual environment exists"; else echo "Virtual environment missing"; fi
	@echo ""
	@echo "Dependency sync status:"
	@uv sync --dry-run --group dev 2>/dev/null && echo "Dependencies are up to date" || echo "Dependencies need synchronization"
	@echo ""
	@echo "Git repository status:"
	@git status --porcelain | wc -l | sed 's/^/Modified files: /'
	@echo ""
	@echo "Disk space in project directory:"
	@du -sh . 2>/dev/null || echo "Cannot check disk usage"
	@echo "Environment diagnosis completed"

## Upgrade project dependencies
# Updates all dependencies to latest compatible versions
# Includes clean to ensure fresh state after upgrade
upgrade: clean
	@echo "Upgrading project dependencies..."
	uv sync --upgrade --group dev
	@echo "Dependencies upgraded successfully"
