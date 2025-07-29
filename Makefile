# Makefile for 5e2pdf project
# All commands run via uv (https://github.com/astral-sh/uv)

.PHONY: uv uv-docs test mypy pip-audit bandit pre-push docs

# Default target: run all pre-push checks
all: check security test

check: ruff mypy imports boundaries
security: pip-audit bandit-medium
test: pytest

# Sync environment (dev dependencies)
uv:
	uv sync --group dev

# Sync environment (docs dependencies)
uv-docs:
	uv sync --extra docs

# Checks and tools

## Linting and formatting
ruff: uv
	uv run ruff format src tests
	uv run ruff check src tests

## Static type checking
mypy: uv
	uv run mypy src/

## Check for circular imports
imports: uv
	uv run python scripts/check_circular_imports.py src/dnd5e/ --fail-on-cycles

## Check architectural boundaries
boundaries: uv
	uv run python scripts/check_architectural_boundaries.py src/dnd5e/ --fail-on-violations

# Security checks
## Security vulnerability scan
pip-audit: uv
	uv run pip-audit --desc=off

## Static security analysis (medium severity)
bandit-medium: uv
	uv run bandit --severity-level medium -r src/

## Static security analysis (medium severity)
bandit: uv
	uv run bandit -r src/

# Run unit tests
pytest: uv
	uv run pytest

# Documentation
## Build HTML docs and open in browser
docs: uv-docs
	cd docs && uv run sphinx-build -b html source _build/html
	open docs/_build/html/index.html

## Start documentation auto-rebuild server
docs-serve: uv-docs
	cd docs && uv run sphinx-autobuild source _build/html --host 0.0.0.0 --port 8000 --open-browser

## Clean documentation build artifacts
docs-clean:
	rm -rf docs/_build docs/build

## Build docs with clean rebuild
docs-rebuild: docs-clean docs

## Check documentation for issues (broken links, syntax)
docs-check: uv-docs
	cd docs && uv run sphinx-build -b linkcheck source _build/linkcheck
	cd docs && uv run sphinx-build -W -b html source _build/html

## Validate documentation quality and structure
docs-validate: uv-docs
	uv run python scripts/validate_docs.py --docs-dir docs

## Full documentation validation (strict mode)
docs-validate-strict: uv-docs
	uv run python scripts/validate_docs.py --docs-dir docs --strict
