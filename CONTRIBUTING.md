# Contributing to Studiorum

Thank you for your interest in contributing to Studiorum! This document provides guidelines and areas where contributions are particularly welcome.

## Quick Start

### Prerequisites

- Python 3.12+
- `uv` for dependency management
- LaTeX distribution (for PDF generation features)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/studiorum.git
cd studiorum

# Install dependencies with uv
uv sync

# Run tests
make test

# Run type checking
make typecheck
```

### Development Workflow

1. Fork the repository
2. Create a feature branch from `develop`: `git checkout -b feat/your-feature develop`
3. Make your changes following our code style (enforced by pre-commit hooks)
4. Write tests for new functionality
5. Ensure all tests pass: `make test`
6. Submit a pull request to the `develop` branch

### Commit Messages

Follow conventional commits format: `<type>(<scope>): <description>`

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `perf`: Performance improvements

## Code Style

- Python code is formatted with `ruff`
- Type hints are required (enforced by `mypy`)
- Follow existing patterns in the codebase
- Consult `/TYPES.md` for type safety patterns

## Testing

- Unit tests: `make test`
- Integration tests: `make test-integration` (requires 5etools data)
- LaTeX tests: `make test-latex-integration` (requires LaTeX)

Tests must pass before PR acceptance. New features require corresponding tests.

## Areas of Special Interest

If you're looking for meaningful ways to contribute, here are some areas where help would be particularly valuable. These are features I'd love to have but haven't had the bandwidth to implement properly:

### 1. 5etools Homebrew Content Creation Resources

**Vision**: Comprehensive documentation and tooling for homebrew content creators

The 5etools ecosystem has powerful homebrew capabilities, but the documentation is scattered and often intimidating for newcomers. We need:

- **Resource Hub**: Curated links to existing 5etools homebrew documentation, schema references, and community resources
- **Tutorial System**: Step-by-step guides for creating common homebrew content (creatures, spells, items, subclasses)
- **Validation Tools**: Enhanced CLI commands to validate homebrew JSON against 5etools schemas with helpful error messages
- **Template Generator**: Interactive tool to scaffold homebrew JSON files with proper structure

This would lower the barrier to entry for DMs wanting to create custom content while maintaining compatibility with the broader 5etools ecosystem.

### 2. Rich Terminal UI for Content Browsing

**Vision**: Interactive terminal interface for exploring 5e content

Leverage the Rich library to create a terminal UI that rivals the LaTeX output in utility:

- **Content Browser**: Navigate creatures, spells, items with keyboard shortcuts, search, and filters
- **Quick Preview**: Inline content rendering with proper formatting, tables, and even ASCII art for stat blocks
- **Interactive Shell**: REPL-style interface for queries like "show me all CR 5 undead" or "what spells deal necrotic damage"
- **Session Management**: Save and restore browsing sessions, bookmarks, and custom views

This would make Studiorum useful even without generating PDFs, turning it into a powerful terminal-based 5e reference tool.

### 3. LaTeX Template Improvements

**Vision**: Upstreamable improvements to the DND-5e-LaTeX-Template project

The LaTeX rendering is core to Studiorum, and improvements here benefit the entire community:

- **Layout System**: Better algorithms for float placement, column balancing, and page breaks to minimize manual tweaking
- **Python Integration**: Clean up the Python->LaTeX bridge to ensure all formatting happens in the appropriate layer
- **New Components**: Creature stat blocks, magic item cards, spell lists, encounter tables - all with the distinctive aesthetic
- **Performance**: Optimize compilation speed for large documents (100+ page books currently take significant time)

The ultimate goal is contributing these improvements back to the upstream DND-5e-LaTeX-Template project, benefiting all users of that excellent resource.

## Getting Help

- Check existing issues and discussions on GitHub
- Ask questions in pull requests or discussions
- For complex features, open an issue for discussion before implementing

## License

By contributing to Studiorum, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Studiorum! Your efforts help make 5e compatible content more accessible and beautiful for everyone.
