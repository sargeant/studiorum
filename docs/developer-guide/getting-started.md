---
title: Getting Started
description: Set up a development checkout of Studiorum and run the checks
---

# Getting Started

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- A TeX distribution and the [DND 5e LaTeX template](https://github.com/rpgtex/DND-5e-LaTeX-Template), only if you want to compile PDFs

## Set up

```bash
git clone https://github.com/sargeant/studiorum.git
cd studiorum
uv sync
uv run pre-commit install
uv run studiorum --help
```

## Everyday commands

`make help` lists every target. The ones you will use most:

```bash
make check    # ruff, mypy, pyright errors and import-linter
make test     # the test suite, in parallel
make docs     # generate the CLI reference and build this site
```

`make test` runs against the small data sets in `test-data/` and `srd-data/`, so it needs no 5etools checkout and no TeX installation. Tests that do need them have their own targets: `make test-full-data` and `make test-latex-integration`.

The LaTeX output of four sample documents is pinned by snapshot tests in `tests/e2e/`. If you change rendering on purpose, update the snapshots with `uv run pytest tests/e2e --snapshot-update` and review the diff before committing.

## Conventions

- Branch from `develop` with a `feat/` or `fix/` prefix and open pull requests against `develop`.
- Commit messages follow `<type>(<scope>): <description>`.
- Functions that can fail return `Result` values. Check them with `isinstance(result, Error)` before calling `unwrap()`.
- Read `TYPES.md` before adding or removing a `# type: ignore`.
- Import layering is enforced by import-linter. The contracts are in `pyproject.toml`, and a new import from `studiorum.core` into a higher layer fails `make check`.
