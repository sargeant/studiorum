---
title: Data Source Architecture
description: Developer reference for studiorum's three-tier data source architecture
---

# Data Source Architecture

Developer reference for the three-tier data source architecture that separates **data repositories** (where content comes from) from **content attribution** (which 5e book content belongs to).

## Architecture Overview

<div class="mermaid">
graph TB
    subgraph "Data Repositories"
        A[SRD Data<br/>Always Available] --> D[DataSourceManager]
        B[Primary Override<br/>Optional 5etools] --> D
        C[Extensions<br/>Homebrew & URLs] --> D
    end

    subgraph "Content Attribution"
        E[Source Metadata] --> F[ContentAttributionManager]
    end

    D --> G[UnifiedSourceManager]
    F --> G
    G --> H[Content Processing]

    style A fill:#e8f5e8
    style B fill:#fff3cd
    style C fill:#f8d7da
    style E fill:#d1ecf1
</div>

### Core Components

**DataSourceManager**: Handles data repositories (GitHub repos, local directories, URLs)
**ContentAttributionManager**: Manages 5e source metadata and priorities
**UnifiedSourceManager**: Coordinates both systems

## Configuration Models

### DataSourcesConfig Structure

```python
from studiorum.core.config.data_sources import (
    DataSourcesConfig,
    DataSourceType,
    ExtensionDataSourceConfig,
    PrimaryDataOverrideConfig,
    SRDDataSourceConfig,
    SourceAttributionConfig,
)

# Complete configuration
config = DataSourcesConfig(
    # Tier 1: SRD (always available)
    srd=SRDDataSourceConfig(enabled=True),

    # Tier 2: Primary override (optional)
    primary_override=PrimaryDataOverrideConfig(
        enabled=True,
        source="~/Code/5etools-src/data",
        type=DataSourceType.FIVE_TOOLS_COMPATIBLE
    ),

    # Tier 3: Extensions (additive)
    extensions=[
        ExtensionDataSourceConfig(
            name="homebrew-spells",
            type=DataSourceType.DIRECTORY,
            source="~/homebrew/spells"
        )
    ],

    # Content attribution (separate concern)
    source_attribution=SourceAttributionConfig(
        default_priorities={"SRD": 100, "HOMEBREW": 1000},
        priority_resolution="highest"
    )
)
```

### Extension Management

```python
# Add extension
ext = ExtensionDataSourceConfig(
    name="custom-content",
    type=DataSourceType.URL,
    source="https://example.com/data.json"
)
config.add_extension(ext)

# List active sources
active = config.get_active_data_sources()
# ["SRD (bundled)", "5etools Override (primary)", "Custom Content (extension)"]

# Validate configuration
issues = config.validate_configuration()
if issues:
    print("Issues:", issues)
```

## Service Integration

### Protocol Interfaces

```python
from studiorum.core.services.protocols import (
    SourceManagerProtocol,
    ContentAttributionProtocol
)

# CLI usage (synchronous)
def cli_command():
    from studiorum.core.services.container import ServiceContainer
    container = ServiceContainer.get_global_instance()
    manager = container.get_service_sync(SourceManagerProtocol)
    stats = manager.get_source_statistics()

# MCP usage (asynchronous)
async def mcp_tool(ctx: AsyncRequestContext):
    manager = await ctx.get_service(SourceManagerProtocol)
    repos = manager.list_repositories()
    return {"repositories": repos}
```

### Service Registration

```python
from studiorum.core.services.registration import register_data_source_services

# Services are auto-registered, but manual registration:
container.register_service(
    SourceManagerProtocol,
    create_unified_source_manager,
    lifecycle=ServiceLifecycle.SINGLETON
)
```

## MCP Tool Integration

### Data Repository Tools

```python
from studiorum.mcp.tools.data import manage_data_sources

# List repositories
result = await manage_data_sources("list", context=ctx)

# Add extensions
result = await manage_data_sources(
    "add_homebrew",
    source="/path/to/homebrew",
    name="custom-content",
    context=ctx
)

# Available actions: list, add_primary, add_homebrew, add_url, remove, status
```

### Content Attribution Tools

```python
from studiorum.mcp.tools.attribution import manage_content_attribution

# List source priorities
result = await manage_content_attribution("list", context=ctx)

# Set priority
result = await manage_content_attribution(
    "set_priority",
    source="HOMEBREW",
    priority=500,
    context=ctx
)

# Available actions: list, set_priority, resolve, info
```

## CLI Commands

### Data Commands

```bash
studiorum data list              # List repositories
studiorum data set-primary PATH  # Set primary override
studiorum data add-homebrew PATH # Add homebrew directory
studiorum data add-url URL       # Add URL source
studiorum data remove NAME      # Remove repository
studiorum data status           # Repository status
```

**CLI Implementation**: All data repository management commands are fully implemented with proper YAML serialization and configuration handling.

### Config Commands

```bash
studiorum config show                    # Show configuration
studiorum config show --section data_sources
studiorum config validate               # Validate config
studiorum config reset                  # Reset to defaults
```

## Implementation Details

### Data Source Types

```python
class DataSourceType(str, Enum):
    SRD = "srd"
    FIVE_TOOLS_COMPATIBLE = "5etools-compatible"
    DIRECTORY = "directory"
    FILE = "file"
    URL = "url"
    GIT = "git"
```

### Homebrew Content Support

**Multi-Type File Support**: Single JSON files can contain multiple content types:

```python
# Example homebrew file with mixed content
{
    "adventure": [
        {"name": "My Adventure", "id": "my-adventure", ...}
    ],
    "spell": [
        {"name": "Custom Spell", "level": 3, ...}
    ],
    "monster": [
        {"name": "Custom Monster", "cr": "5", ...}
    ]
}
```

**Single-File Detection**: The system automatically detects and indexes single-file homebrew content with proper content type separation and validation.

**Adventure Metadata Merging**: Homebrew adventures support metadata/data merging patterns for enhanced content organization.

### Validation Rules

- Primary override requires `source` when `enabled=True`
- Extension names must be unique
- File paths are validated for existence (warnings only)
- URLs must use http/https schemes
- Security restrictions on allowed paths/URLs

### Performance Configuration

```python
config = DataSourcesConfig(
    performance={
        "caching": {
            "content_cache": {"enabled": True, "ttl": 3600, "max_entries": 10000},
            "index_cache": {"enabled": True, "ttl": 1800},
            "network_cache": {"enabled": True, "ttl": 300}
        },
        "memory": {
            "lazy_loading": True,
            "stream_large_files": True,
            "max_memory_usage": "512MB"
        }
    }
)
```

### Security Settings

```python
config = DataSourcesConfig(
    security={
        "allowed_paths": [
            "~/Code/5etools-src/**",
            "~/.studiorum/**"
        ],
        "allowed_urls": [
            "https://github.com/**",
            "https://raw.githubusercontent.com/**"
        ],
        "ssl_verify": True,
        "timeout": 30,
        "max_file_size": "100MB"
    }
)
```

## Testing

### Test Setup

```python
from studiorum.core.services.container import ServiceContainer
from studiorum.core.config.data_sources import DataSourcesConfig

def setup_method():
    ServiceContainer.reset_global_instance()

# Mock data configuration for tests
test_config = DataSourcesConfig(
    extensions=[
        ExtensionDataSourceConfig(
            name="test-ext",
            type=DataSourceType.DIRECTORY,
            source="/test/path"
        )
    ]
)
```

### Integration Testing

```python
# Test MCP tools with AsyncRequestContext
async def test_mcp_integration():
    mock_context = Mock(spec=AsyncRequestContext)
    mock_manager = Mock()
    mock_context.get_service = AsyncMock(return_value=mock_manager)

    result = await manage_data_sources("list", context=mock_context)
    assert "repositories" in result
```

## Development Notes

- All configuration changes go through Pydantic validation
- Service protocols enable loose coupling and testing
- Performance targets: <500ms data operations, <100ms attribution
- Use `isinstance() + unwrap()` for Result[T,E] error handling
- Reset container in tests for proper isolation

---

## Key Files

- `src/studiorum/core/config/data_sources.py` - Configuration models
- `src/studiorum/core/loaders/data_source_manager.py` - Data repository management
- `src/studiorum/core/loaders/content_attribution_manager.py` - Source attribution
- `src/studiorum/core/loaders/unified_source_manager.py` - Coordination layer
- `src/studiorum/mcp/tools/data.py` - MCP data repository tools
- `src/studiorum/mcp/tools/attribution.py` - MCP attribution tools
