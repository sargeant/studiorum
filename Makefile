# Makefile for studiorum. Every target runs through uv.

# Configuration for fail-fast behavior and error checking
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# Configuration variables
UV := uv run
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs
SCRIPTS_DIR := scripts
CLI_REFERENCE := $(DOCS_DIR)/user-guide/cli-reference.md

# UV configuration for enhanced integration
UV_SYNC_FLAGS := --no-progress
UV_DEV_FLAGS := --group dev
UV_LLM_FLAGS := --group llm
UV_CI_FLAGS := --frozen

# Environment detection
CI_DETECTED := $(if $(CI),1,0)

# Quiet mode configuration
QUIET ?= 0
# Auto-enable quiet mode in CI unless explicitly disabled
ifeq ($(CI_DETECTED),1)
QUIET ?= 1
endif

# Output control based on quiet mode
ifeq ($(QUIET),1)
ECHO_INFO := @:
ECHO_SUCCESS := @:
ECHO_ERROR := @echo "ERROR:"
else
ECHO_INFO := @:
ECHO_SUCCESS := @echo
ECHO_ERROR := @echo "ERROR:"
endif

# Conditional flags based on environment
ifeq ($(CI_DETECTED),1)
UV_SYNC_BASE := uv sync $(UV_SYNC_FLAGS) $(UV_CI_FLAGS)
else
UV_SYNC_BASE := uv sync $(UV_SYNC_FLAGS)
endif

.PHONY: help all check security uv ruff mypy pyright-errors lint-imports pip-audit bandit test test-serial test-full-data test-latex-integration docs docs-serve cli-reference clean ci-install ci-check ci-test uv-llm mcp-ref-tools

# Only the sync targets need to run serially
.NOTPARALLEL: uv ci-install uv-llm

help:
	@echo "Everyday:"
	@echo "  check        - ruff, mypy, pyright errors and import-linter"
	@echo "  test         - Run the test suite (parallel, skips xdist_incompatible)"
	@echo "  security     - pip-audit and bandit"
	@echo "  all          - check, security and test"
	@echo ""
	@echo "Individual checks:"
	@echo "  ruff         - Format, then lint"
	@echo "  mypy         - Type check src/"
	@echo "  pyright-errors - Pyright, errors only"
	@echo "  lint-imports - Import layering and core cycles (import-linter)"
	@echo "  pip-audit    - Dependency vulnerability scan"
	@echo "  bandit       - Static security analysis"
	@echo ""
	@echo "More tests:"
	@echo "  test-serial  - Tests marked xdist_incompatible, run without xdist"
	@echo "  test-full-data - Tests that need a 5etools checkout (STUDIORUM_5ETOOLS_DIR, default ~/Code/5etools-src)"
	@echo "  test-latex-integration - Real LaTeX compilation (needs TeX Live and the DnD template)"
	@echo ""
	@echo "Docs:"
	@echo "  docs         - Generate the CLI reference, build the site and open it"
	@echo "  docs-serve   - Generate the CLI reference and serve with live reload"
	@echo "  cli-reference - Generate $(CLI_REFERENCE) from the Typer app"
	@echo ""
	@echo "CI (called from .github/workflows):"
	@echo "  ci-install, ci-check, ci-test"
	@echo ""
	@echo "Other:"
	@echo "  uv           - Sync the dev environment"
	@echo "  clean        - Remove caches, coverage and build output"
	@echo "  mcp-ref-tools - Run mcp-proxy for ref.tools over stdio"

# Run all pre-push checks
all: check security test
	$(ECHO_SUCCESS) "All pipeline checks completed successfully"

check: ruff mypy pyright-errors lint-imports
	$(ECHO_SUCCESS) "All code quality checks passed"

security: uv pip-audit bandit
	$(ECHO_SUCCESS) "All security checks passed"

# Sync environment (dev dependencies, which include the docs tools)
uv:
	@$(UV_SYNC_BASE) $(UV_DEV_FLAGS)

# Sync environment (LLM / MCP dependencies)
uv-llm:
	@$(UV_SYNC_BASE) $(UV_LLM_FLAGS)

## Format, then lint
ruff: uv
	@$(UV) ruff format $(SRC_DIR) $(TEST_DIR)
	@$(UV) ruff check $(SRC_DIR) $(TEST_DIR) || (echo "ERROR: ruff: code style violations found"; exit 1)

## Static type checking
mypy: uv
	@$(UV) mypy $(SRC_DIR)/ || (echo "ERROR: mypy: type checking failed"; exit 1)

pyright-errors: uv
	@$(UV) pyright $(SRC_DIR)/ --pythonpath .venv/bin/python --level error

## Check import layering and cycles (contracts in pyproject.toml)
lint-imports: uv
	@$(UV) lint-imports --no-logo || (echo "ERROR: lint-imports: import contract broken"; exit 1)

## Security vulnerability scan
# PYSEC-2026-2447 (CVE-2025-69872): diskcache pickles by default, so anyone who
# can write to the local cache directory could run code. No fixed release; the
# pickled content cache is due to be removed.
pip-audit: uv
	@$(UV) pip-audit --desc=off --ignore-vuln GHSA-4xh5-x5gv-qwph --ignore-vuln PYSEC-2026-2447 || (echo "ERROR: pip-audit: security vulnerabilities found"; exit 1)

## Static security analysis
bandit: uv
	@$(UV) bandit -c pyproject.toml --quiet -r $(SRC_DIR)/ || (echo "ERROR: bandit: security issues found"; exit 1)

# MCP: ref.tools via mcp-proxy (stdio)
mcp-ref-tools: uv-llm
	@chmod +x $(SCRIPTS_DIR)/mcp-proxy-ref-tools.sh
	@$(SCRIPTS_DIR)/mcp-proxy-ref-tools.sh

# Tests
## Parallel-safe tests (pyproject addopts deselect xdist_incompatible)
test: uv
	@$(UV) pytest

## Tests that hang under xdist, run sequentially
test-serial: uv
	@$(UV) pytest -m "xdist_incompatible" -n 0

## Tests that need the full 5etools data set
test-full-data: uv
	STUDIORUM_TEST_FULL_DATA=1 uv run --env-file .env.dev pytest -m "requires_data"

## Real LaTeX compilation (requires TeX Live and DND-5e-LaTeX-Template)
test-latex-integration: uv
	@$(UV) pytest -m "latex_compilation" tests/integration/latex/ -v || (echo "LaTeX integration tests failed"; exit 1)

# Documentation
## Generate the CLI reference from the Typer app (not tracked in git)
cli-reference: uv
	@$(UV) typer studiorum.cli.main utils docs --name studiorum --title "CLI Reference" --output $(CLI_REFERENCE)

## Build HTML docs and open in browser
docs: cli-reference
	@$(UV) mkdocs build || (echo "Documentation build failed"; exit 1)
	@echo "Documentation built at ./site"
	@open site/index.html 2>/dev/null || true

## Serve docs with live reload
docs-serve: cli-reference
	@$(UV) mkdocs serve -a 127.0.0.1:8000

## Remove caches, coverage and build output
clean:
	rm -rf site/ .pytest_cache/ .mypy_cache/ .ruff_cache/ .coverage htmlcov/ dist/ build/ *.egg-info/ coverage.xml test-results.xml $(CLI_REFERENCE)
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +

# CI targets, called from .github/workflows
ci-install:
	@$(UV_SYNC_BASE) $(UV_DEV_FLAGS)

## Outputs coverage.xml, htmlcov/ and test-results.xml
ci-test: ci-install
	@$(UV) pytest --cov=studiorum --cov-report=xml --cov-report=html --junitxml=test-results.xml -m "not ci_broken and not requires_latex and not xdist_incompatible" || (echo "ERROR: CI test suite failed"; exit 1)

ci-check: ci-install check security
