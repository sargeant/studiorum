---
title: Developer Guide
description: Where to start when working on the Studiorum code
---

# Developer Guide

Studiorum is a Python 3.12 package managed with `uv`. [Getting Started](getting-started.md) covers setting up a checkout, running the checks and tests, and building these docs. The [contributing guide](https://github.com/sargeant/studiorum/blob/develop/CONTRIBUTING.md) covers branches, commit messages and pull requests.

The code is being restructured, so this guide does not describe its internals. Those change too often to keep a public copy accurate. The maintainers keep design notes outside the repository, under these topic names:

- Service Container and Async Architecture: how the CLI and the MCP server get their services
- Content Loading, Content Type System and 5etools Data Format: reading 5etools JSON into models
- Data Modelling Patterns and Pydantic Strategy: how the content models are built and validated
- Tag System, LaTeX Rendering and Rendering Pipeline: turning entries and `{@tag}` markup into LaTeX
- CLI Architecture and MCP Strategy: the two front ends
- Result Pattern and Type Safety Patterns: error handling and typing conventions
- Testing Strategy and Git Workflow: how changes are tested and merged

If you need detail on one of these, open an issue or a discussion on GitHub and ask.
