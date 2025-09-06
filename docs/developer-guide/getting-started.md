---
title: Getting Started
description: Set up your development environment and start building with studiorum
---

# Getting Started

This guide will help you set up a development environment for contributing to studiorum or building applications that integrate with it.

## Development Setup

### Prerequisites

- **Python 3.12+**: Required for modern typing features
- **uv**: Recommended package manager (faster than pip)
- **Git**: For version control and contributing
- **LaTeX**: For PDF generation (optional for development)

### Clone and Setup

1. **Fork and clone the repository**:

   ```bash
   git clone https://github.com/yourusername/studiorum.git
   cd studiorum
   ```

2. **Install dependencies with uv**:

   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install project dependencies
   uv sync

   # Install pre-commit hooks
   uv run pre-commit install
   ```

3. **Verify installation**:

   ```bash
   # Test the CLI
   uv run studiorum --version

   # Run basic tests
   uv run pytest tests/unit/ -v
   ```

### Development Dependencies

The project uses several development tools:

```toml
# pyproject.toml - dev dependencies
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-xdist>=3.5.0",
    "mypy>=1.8.0",
    "ruff>=0.3.0",
    "pre-commit>=3.6.0",
    "mkdocs>=1.6.1",
    "mkdocs-cinder>=1.2.0",
]
```

### Project Structure

Understanding the codebase layout:

```
studiorum/
├── src/studiorum/           # Main package (src layout)
│   ├── core/               # Core business logic
│   │   ├── container.py    # Service container
│   │   ├── models/         # Pydantic data models
│   │   └── services/       # Service protocols
│   ├── cli/                # Command-line interface
│   ├── mcp/                # MCP server implementation
│   ├── renderers/          # Output renderers (LaTeX, etc.)
│   └── latex_engine/       # LaTeX compilation
├── tests/                  # Test suite
│   ├── unit/              # Fast unit tests
│   ├── integration/       # Integration tests
│   └── latex/             # LaTeX compilation tests
├── docs/                  # Documentation
├── private/               # Private development docs
└── pyproject.toml         # Project configuration
```

## Core Concepts

### Service Container

Studiorum uses dependency injection through a service container:

```python
from studiorum.core.services.container import ServiceContainer, create_mcp_request_container
from studiorum.core.services.protocols import OmnidexerProtocol

# Get the global container
container = ServiceContainer.get_global_instance()

# Resolve services by protocol (sync)
omnidexer = container.get_service_sync(OmnidexerProtocol)

# For async contexts (MCP server)
async def my_async_function(base_config):
    async with await create_mcp_request_container(base_config) as ctx:
        omnidexer = await ctx.get_service(OmnidexerProtocol)
        # Use omnidexer...
```

### Content Models

All 5e content uses Pydantic models for validation:

```python
from studiorum.core.models.creatures import Creature
from studiorum.core.models.spells import Spell
from studiorum.core.models.adventures import Adventure

# Models have full type safety
creature = Creature(
    name="Ancient Red Dragon",
    size=CreatureSize.GARGANTUAN,
    creature_type=CreatureType.DRAGON,
    challenge_rating=ChallengeRating(24),
    # ... other required fields
)

# Validation happens automatically
try:
    invalid_creature = Creature(
        name="Test",
        challenge_rating="invalid"  # This will raise ValidationError
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Result Pattern

All operations that can fail use Result types:

```python
from studiorum.core.result import Result, Success, Error

def convert_creature(creature_name: str) -> Result[str, str]:
    """Convert a creature to LaTeX, returning Result type."""

    # Check if creature exists
    if not creature_exists(creature_name):
        return Error(f"Creature not found: {creature_name}")

    # Perform conversion
    latex_output = do_conversion(creature_name)
    return Success(latex_output)

# Usage with isinstance pattern (recommended)
result = convert_creature("Ancient Red Dragon")
if isinstance(result, Error):
    print(f"Conversion failed: {result.error}")
    return

# Type checker knows this is Success
latex_content = result.unwrap()
print(f"Generated {len(latex_content)} characters of LaTeX")
```

## Development Workflows

### Running Tests

Studiorum has a comprehensive test suite:

```bash
# Fast unit tests (no external dependencies)
uv run pytest tests/unit/ -v

# Integration tests (requires 5etools data)
uv run pytest tests/integration/ -v -m requires_data

# Full test suite (includes LaTeX compilation)
make test

# Run tests in parallel
uv run pytest -n auto

# Test specific functionality
uv run pytest tests/unit/core/test_omnidexer.py -v

# Test with coverage
uv run pytest --cov=studiorum tests/
```

### Code Quality

The project uses several code quality tools:

```bash
# Linting with ruff
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking with mypy
uv run mypy src/

# Pre-commit hooks (run automatically)
uv run pre-commit run --all-files

# Full quality check
make lint
```

### Documentation

Build and serve documentation locally:

```bash
# Serve docs with hot reload
uv run mkdocs serve

# Build static docs
uv run mkdocs build

# Deploy to GitHub Pages (maintainers only)
make docs-deploy
```

### Testing with Real Data

Some tests require 5etools data:

```bash
# Check data repositories (first time only)
uv run studiorum data status

# Run integration tests
uv run pytest tests/integration/ -v -m requires_data

# Test MCP server functionality
uv run studiorum mcp test lookup_creature "Ancient Red Dragon"
```

## Building Features

### Adding a New Content Type

1. **Define the data model**:

   ```python
   # src/studiorum/core/models/new_content.py
   from pydantic import BaseModel
   from typing import Literal

   class NewContent(BaseModel):
       """Model for new 5e content type."""

       name: str
       content_type: Literal["new_content"] = "new_content"
       source: str
       # ... other fields

       class Config:
           validate_assignment = True
           extra = "forbid"
   ```

2. **Add to Omnidexer**:

   ```python
   # src/studiorum/core/omnidexer.py
   def get_new_content_by_name(self, name: str) -> NewContent | None:
       """Get new content by name."""
       return self._search_content("new_content", {"name": name})
   ```

3. **Create renderer**:

   ```python
   # src/studiorum/renderers/latex/new_content.py
   from studiorum.renderers.core.interfaces import RenderingContext

   def render_new_content(content: NewContent, context: RenderingContext) -> str:
       """Render new content type to LaTeX."""
       return f"\\section{{{content.name}}}\n% New content rendering"
   ```

4. **Add CLI command**:

   ```python
   # src/studiorum/cli/commands/convert.py
   @app.command()
   def new_content(
       name: str,
       output: str | None = None
   ):
       """Convert new content type."""
       # Implementation here
   ```

5. **Write tests**:

   ```python
   # tests/unit/models/test_new_content.py
   def test_new_content_validation():
       content = NewContent(name="Test", source="MY-HOMEBREW")
       assert content.name == "Test"
       assert content.content_type == "new_content"
   ```

### Adding MCP Tools

Create new MCP tools for AI integration:

```python
# src/studiorum/mcp/tools/new_tool.py
from studiorum.mcp.core.decorators import mcp_tool
from studiorum.core.async_request_context import AsyncRequestContext

@mcp_tool("new_content_lookup")
async def lookup_new_content(
    ctx: AsyncRequestContext,
    name: str,
    source: str | None = None
) -> dict[str, Any]:
    """Look up new content by name."""

    # Get omnidexer from context
    omnidexer = await ctx.get_service(OmnidexerProtocol)

    # Perform lookup
    content = omnidexer.get_new_content_by_name(name)

    if not content:
        return {"error": f"New content not found: {name}"}

    return {
        "name": content.name,
        "source": content.source,
        # ... other fields
    }
```

### Custom Renderers

Implement custom output formats:

```python
# src/studiorum/renderers/custom/my_renderer.py
from studiorum.renderers.core.interfaces import (
    DocumentRenderer,
    RenderingContext
)

class MyCustomRenderer(DocumentRenderer):
    """Custom renderer for specific output format."""

    def get_supported_formats(self) -> list[str]:
        return ["my_format"]

    def render_document(
        self,
        content: list[Any],
        context: RenderingContext
    ) -> str:
        """Render content to custom format."""

        output_parts = []
        for item in content:
            rendered = self._render_item(item, context)
            output_parts.append(rendered)

        return "\n\n".join(output_parts)

    def _render_item(self, item: Any, context: RenderingContext) -> str:
        """Render individual content item."""
        # Custom rendering logic
        return f"CUSTOM: {item}"

# Register the renderer
from studiorum.renderers.registry import get_renderer_registry

registry = get_renderer_registry()
registry.register_renderer("my_format", MyCustomRenderer())
```

## Advanced Development

### Service Container Patterns

Create custom services:

```python
# Define protocol
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyServiceProtocol(Protocol):
    def do_something(self, data: str) -> str: ...

# Implement service
class MyService:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency

    def do_something(self, data: str) -> str:
        return f"Processed: {data}"

# Register service
def create_my_service() -> MyService:
    dependency = get_some_dependency()
    return MyService(dependency)

# In service registration
container.register_service(
    MyServiceProtocol,
    create_my_service,
    lifecycle=ServiceLifecycle.SINGLETON
)
```

### Async Context Management

For MCP tools and async operations:

```python
from studiorum.core.async_request_context import AsyncRequestContext

class MyAsyncService:
    def __init__(self, ctx: AsyncRequestContext):
        self.ctx = ctx

    async def process_data(self, data: str) -> str:
        # Get other services as needed
        omnidexer = await self.ctx.get_service(OmnidexerProtocol)

        # Process with type safety
        result = await self._do_async_work(data, omnidexer)
        return result
```

### Error Handling Patterns

Use Result types consistently:

```python
from studiorum.core.result import Result, Success, Error

def risky_operation(input_data: str) -> Result[str, str]:
    """Operation that might fail."""

    if not input_data:
        return Error("Input data cannot be empty")

    try:
        result = process_data(input_data)
        return Success(result)
    except Exception as e:
        return Error(f"Processing failed: {e}")

# Chain operations
def chain_operations(data: str) -> Result[str, str]:
    result1 = risky_operation(data)
    if isinstance(result1, Error):
        return result1.with_context(
            "First operation failed",
            operation="risky_operation",
            input=data
        )

    result2 = another_operation(result1.unwrap())
    if isinstance(result2, Error):
        return result2.with_context("Second operation failed")

    return result2
```

## Debugging Tips

### Logging Configuration

Enable detailed logging for development:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger('studiorum.core.omnidexer').setLevel(logging.DEBUG)
logging.getLogger('studiorum.mcp').setLevel(logging.DEBUG)
```

### MCP Server Debugging

Debug MCP server issues:

```bash
# Run MCP server with debug logging
uv run studiorum mcp run --debug --log-level DEBUG

# Test MCP tools directly
uv run studiorum mcp test lookup_creature "Ancient Red Dragon"

# Monitor MCP logs
tail -f ~/.studiorum/logs/mcp-debug-*.log
```

### Service Container Debugging

Debug service resolution issues:

```python
from studiorum.core.services.container import ServiceContainer

container = ServiceContainer.get_global_instance()

# Check registered services
print("Registered services:")
for protocol in container.get_registered_protocols():
    print(f"  - {protocol}")

# Check service instances
print("Singleton instances:")
for protocol, instance in container.get_singleton_instances().items():
    print(f"  - {protocol}: {instance}")
```

## Contributing Guidelines

### Code Standards

- **Type hints**: All functions must have type annotations
- **Docstrings**: Use numpy-style docstrings for public APIs
- **Error handling**: Use Result types for operations that can fail
- **Testing**: Write tests for all new functionality

### Pull Request Process

1. **Create feature branch**:

   ```bash
   git checkout -b feat/my-new-feature
   ```

2. **Make changes with tests**:

   ```bash
   # Write code
   # Write tests
   uv run pytest tests/unit/test_my_feature.py -v
   ```

3. **Quality checks**:

   ```bash
   make lint
   make test
   ```

4. **Commit and push**:

   ```bash
   git add .
   git commit -m "feat: add new feature with comprehensive tests"
   git push origin feat/my-new-feature
   ```

5. **Create pull request** targeting `develop` branch

### Release Process

For maintainers:

1. **Create release branch**:

   ```bash
   git checkout -b release/1.2.0 develop
   ```

2. **Update version and changelog**:

   ```bash
   # Update pyproject.toml version
   # Update CHANGELOG.md
   ```

3. **Final testing**:

   ```bash
   make test-all
   make docs-build
   ```

4. **Merge to main and tag**:

   ```bash
   git checkout main
   git merge release/1.2.0
   git tag v1.2.0
   git push origin main --tags
   ```

## Getting Help

- **Documentation**: Read the full [developer guide](index.md)
- **GitHub Issues**: [Report bugs or request features](https://github.com/sargeant/studiorum/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/sargeant/studiorum/discussions)
- **Discord**: Join our development community

## Next Steps

- **[Architecture Guide](architecture.md)**: Deep dive into system design
- **[API Reference](api/index.md)**: Complete API documentation
- **[AI Agent Development](ai-agents.md)**: Build MCP integrations
- **[Contributing Guidelines](contributing.md)**: Detailed contribution process
