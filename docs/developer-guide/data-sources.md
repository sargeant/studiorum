---
title: Data Source Architecture
description: Comprehensive guide to studiorum's three-tier data source architecture and configuration system
---

# Data Source Architecture

Studiorum's modern data source architecture provides a clean separation between **data repositories** (where content comes from) and **content attribution** (which 5e book content belongs to).

<div class="feature-cards" markdown>

-   📚 **Three-Tier Model**

    ---

    SRD, Primary Override, and Extensions for comprehensive content management

    [Configuration Reference](#configuration-models){ .btn-primary }

-   🔄 **Migration Support**

    ---

    Seamless upgrade from legacy configurations with intelligent parsing

    [Migration Guide](#configuration-migration){ .btn-secondary }

-   ⚡ **Modern Architecture**

    ---

    Service container integration with async support and type safety

    [Service Integration](#service-integration){ .btn-accent }

</div>

## Architecture Overview

The data source refactor eliminates the confusing dual "source" concept by creating clear boundaries:

<div class="mermaid">
graph TB
    subgraph "Data Repositories"
        A[SRD Data<br/>Always Available] --> D[DataSourceManager]
        B[Primary Override<br/>Optional 5etools] --> D
        C[Extensions<br/>Homebrew & URLs] --> D
    end

    subgraph "Content Attribution"
        E[Source Metadata<br/>PHB, MM, XGE, etc.] --> F[ContentAttributionManager]
    end

    D --> G[UnifiedSourceManager]
    F --> G
    G --> H[Content Processing]

    style A fill:#e8f5e8
    style B fill:#fff3cd
    style C fill:#f8d7da
    style E fill:#d1ecf1
</div>

### Key Components

**DataSourceManager**: Handles data repositories (GitHub repos, local directories, URLs)
**ContentAttributionManager**: Manages 5e source metadata and priorities
**UnifiedSourceManager**: Coordinates both systems seamlessly
**ConfigurationMigration**: Intelligent upgrade from legacy formats

## Three-Tier Data Model

### 1. SRD Data (Always Available)

```python
from studiorum.core.config.data_sources import SRDDataSourceConfig

# SRD configuration - bundled and copyright-safe
srd_config = SRDDataSourceConfig(
    enabled=True,  # Default
    path="bundled://srd-data",
    description="System Reference Document content"
)
```

- **Content**: System Reference Document only
- **Copyright**: No trademark issues, always safe
- **Structure**: Complex 5etools-compatible format
- **Availability**: Bundled with studiorum installation

### 2. Primary Data Override (Optional)

```python
from studiorum.core.config.data_sources import PrimaryDataOverrideConfig, DataSourceType

# Primary override - replaces SRD with full content
primary_config = PrimaryDataOverrideConfig(
    enabled=True,
    source="/path/to/5etools-src/data",
    type=DataSourceType.FIVE_TOOLS_COMPATIBLE,
    description="Full 5etools content repository"
)
```

- **Purpose**: Replaces SRD with complete WotC content
- **User Choice**: User assumes copyright responsibility
- **Sources**: Local directories, Git repositories
- **Format**: 5etools-compatible structure required

### 3. Extension Data Sources (Additive)

```python
from studiorum.core.config.data_sources import ExtensionDataSourceConfig

# Homebrew directory
homebrew_ext = ExtensionDataSourceConfig(
    name="custom-spells",
    type=DataSourceType.DIRECTORY,
    source="/path/to/homebrew/spells",
    description="Custom spell collection"
)

# URL-based content
url_ext = ExtensionDataSourceConfig(
    name="community-monsters",
    type=DataSourceType.URL,
    source="https://example.com/monsters.json",
    refresh_interval=3600,  # 1 hour
    description="Community monster collection"
)
```

- **Purpose**: Add homebrew and custom content
- **Types**: Directories, files, URLs, Git repositories
- **Pattern**: Simple file inclusion, flexible structure
- **Management**: Can be enabled/disabled individually

## Configuration Models

### Complete Configuration Structure

```python
from studiorum.core.config.data_sources import DataSourcesConfig

# Full configuration with all three tiers
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
        ),
        ExtensionDataSourceConfig(
            name="third-party-content",
            type=DataSourceType.URL,
            source="https://content.example.com/data.json"
        )
    ],

    # Content attribution (separate concern)
    source_attribution=SourceAttributionConfig(
        default_priorities={
            "SRD": 100,
            "PHB": 10,
            "MM": 20,
            "HOMEBREW": 1000
        },
        priority_resolution="highest",
        prefer_official=True
    )
)
```

### Configuration Methods

```python
# Validation and management
issues = config.validate_configuration()
if issues:
    print("Configuration warnings:", issues)

# Active source tracking
active_sources = config.get_active_data_sources()
print("Active:", active_sources)
# Output: ["SRD (bundled)", "5etools Override (primary)", "Homebrew Spells (extension)"]

# Extension management
config.add_extension(ExtensionDataSourceConfig(
    name="new-homebrew",
    type=DataSourceType.DIRECTORY,
    source="/path/to/new/content"
))

removed = config.remove_extension("old-homebrew")
if removed:
    print("Extension removed successfully")
```

## Configuration Migration

The migration system intelligently upgrades legacy configurations to the new three-tier model.

### Migration Process

```python
from studiorum.core.config.migration import ConfigurationMigration

# Legacy configuration format
old_config = {
    "default_sources": [
        "/path/to/5etools-src/data",     # → Primary override
        "PHB",                           # → Source attribution
        "/path/to/homebrew",            # → Extension
        "https://example.com/data.json" # → URL extension
    ],
    "content": {
        "merger": {"cache_ttl": 1800},
        "sources": {
            "CUSTOM": {"name": "Custom", "priority": 300}
        }
    }
}

# Perform migration
migration = ConfigurationMigration()
new_config = migration.migrate_configuration(old_config)

# Generate migration report
report = migration.create_migration_report()
print(report)
```

### Migration Logic

**Path Analysis**:
```python
# Detected as primary override
"/path/to/5etools-src/data"  # → PrimaryDataOverrideConfig
"~/Code/5etools/data"        # → PrimaryDataOverrideConfig

# Detected as extensions
"/home/user/homebrew"        # → ExtensionDataSourceConfig (directory)
"spell_collection.json"      # → ExtensionDataSourceConfig (file)
"https://example.com/data"   # → ExtensionDataSourceConfig (URL)

# Detected as content attribution
"PHB", "MM", "XGE"          # → SourceAttributionConfig custom sources
```

**Preview Mode**:
```python
# Preview migration without changing state
preview = migration.preview_migration(old_config)
print("Migrated config:", preview["migrated_config"])
print("Migration log:", preview["migration_log"])
print("Report:", preview["report"])
```

### Migration Report Example

```
Configuration Migration Report
===============================

Migration Timestamp: 2025-08-25 18:53:34 NZST
Source Configuration: Legacy default_sources format
Target Configuration: Modern three-tier data sources

CHANGES APPLIED:

Data Sources:
✅ Migrated '/path/to/5etools-src/data' as primary data override
✅ Migrated '/path/to/homebrew' as extension (homebrew-content)
✅ Migrated 'https://example.com/data.json' as URL extension (url-example-com)

Content Attribution:
✅ Migrated 'PHB' as custom source attribution
✅ Preserved custom source 'CUSTOM' with priority 300

Performance Settings:
✅ Migrated content.merger.cache_ttl → performance.caching.content_cache.ttl
✅ Set performance.caching.content_cache.enabled = True

Total changes: 6 configurations migrated
Migration completed successfully with no errors
```

## CLI Interface

### New Data Commands

The new `studiorum data` commands provide comprehensive repository management:

```bash
# List configured repositories
studiorum data list

# Set primary data override
studiorum data set-primary ~/Code/5etools-src/data

# Add homebrew extensions
studiorum data add-homebrew ~/homebrew/spells --name "custom-spells"

# Add URL-based extensions
studiorum data add-url https://example.com/content.json

# Repository management
studiorum data remove old-homebrew
studiorum data scan              # Re-index all repositories
studiorum data status           # Detailed status information
studiorum data check            # Validate configurations
```

### Configuration Commands

```bash
# Configuration management
studiorum config show --section data_sources
studiorum config migrate        # Upgrade legacy configuration
studiorum config validate       # Check configuration integrity
studiorum config reset          # Reset to defaults
```

### Backward Compatibility

Legacy commands continue to work with deprecation warnings:

```bash
$ studiorum sources list
⚠️  DEPRECATION WARNING: 'sources' commands are deprecated
Use 'studiorum data list' instead
Migration guide: https://studiorum.dev/data-sources#migration
```

## Service Integration

### Service Container Pattern

The data source architecture integrates with studiorum's service container system:

```python
from studiorum.core.container import get_global_container
from studiorum.core.context import AsyncRequestContext
from studiorum.core.services.protocols import SourceManagerProtocol

# CLI usage (synchronous)
def cli_command():
    container = get_global_container()
    manager = container.get_service_sync(SourceManagerProtocol)
    stats = manager.get_source_statistics()
    print(f"Total repositories: {stats['total_sources']}")

# MCP usage (asynchronous)
async def mcp_tool(ctx: AsyncRequestContext):
    manager = await ctx.get_service(SourceManagerProtocol)
    repositories = manager.list_repositories()
    return {"repositories": repositories}
```

### Protocol Interfaces

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SourceManagerProtocol(Protocol):
    """Protocol for data source management."""

    def get_source_statistics(self) -> dict[str, Any]:
        """Get comprehensive source statistics."""
        ...

    def list_repositories(self) -> list[dict[str, Any]]:
        """List all configured repositories."""
        ...

@runtime_checkable
class ContentAttributionProtocol(Protocol):
    """Protocol for content attribution management."""

    def resolve_source_priority(self, sources: list[str]) -> str:
        """Resolve priority between conflicting sources."""
        ...

    def get_source_metadata(self, source: str) -> dict[str, Any]:
        """Get metadata for a content source."""
        ...
```

## MCP Tool Integration

### Data Repository Tools

```python
from studiorum.mcp.tools.data import manage_data_sources

# List repositories
result = await manage_data_sources("list", context=ctx)
print("Repositories:", result["repositories"])
print("Total:", result["total_count"])

# Add primary override
result = await manage_data_sources(
    "add_primary",
    source="/path/to/5etools-data",
    context=ctx
)

# Add homebrew extension
result = await manage_data_sources(
    "add_homebrew",
    source="/path/to/homebrew",
    name="custom-content",
    context=ctx
)
```

### Content Attribution Tools

```python
from studiorum.mcp.tools.attribution import manage_content_attribution

# List source priorities
result = await manage_content_attribution("list", context=ctx)

# Set source priority
result = await manage_content_attribution(
    "set_priority",
    source="HOMEBREW",
    priority=500,
    context=ctx
)

# Resolve source conflicts
result = await manage_content_attribution(
    "resolve",
    sources=["PHB", "XGE", "HOMEBREW"],
    context=ctx
)
```

## Performance and Caching

### Performance Configuration

```python
config = DataSourcesConfig(
    performance={
        "caching": {
            "content_cache": {
                "enabled": True,
                "ttl": 3600,        # 1 hour
                "max_entries": 10000
            },
            "index_cache": {
                "enabled": True,
                "ttl": 1800         # 30 minutes
            },
            "network_cache": {
                "enabled": True,
                "ttl": 300          # 5 minutes
            }
        },
        "memory": {
            "lazy_loading": True,
            "stream_large_files": True,
            "max_memory_usage": "512MB"
        }
    }
)
```

### Performance Targets

**CLI Operations**: < 3 seconds for all data commands
**MCP Tools**: < 500ms for data operations, < 100ms for attribution
**Memory Usage**: Configurable limits with streaming support
**Network Requests**: Intelligent caching with TTL

## Security Configuration

### Path and URL Restrictions

```python
config = DataSourcesConfig(
    security={
        "allowed_paths": [
            "~/Code/5etools-src/**",     # 5etools repositories
            "~/.studiorum/**",           # User config directory
            "/opt/studiorum-data/**"     # System data directory
        ],
        "allowed_urls": [
            "https://github.com/**",           # GitHub repositories
            "https://raw.githubusercontent.com/**"  # GitHub raw files
        ],
        "ssl_verify": True,
        "timeout": 30,                 # Network timeout (seconds)
        "max_file_size": "100MB",      # Per-file limit
        "max_total_size": "1GB"        # Total content limit
    }
)
```

### Validation and Safety

```python
# Configuration validation
issues = config.validate_configuration()
for issue in issues:
    if "warning" in issue.lower():
        print(f"⚠️  {issue}")
    else:
        print(f"❌ {issue}")

# Path validation example
"""
Extension 'homebrew-spells' source not found: /nonexistent/path (warning)
Extension 'bad-url' has invalid URL: ftp://example.com/data
Primary override enabled but no source specified
"""
```

## Testing and Quality Assurance

### Integration Testing

The data source architecture includes comprehensive test coverage:

```python
# Test configuration migration
def test_configuration_migration():
    old_config = {"default_sources": ["PHB", "/path/to/data"]}
    migration = ConfigurationMigration()
    new_config = migration.migrate_configuration(old_config)

    assert new_config.source_attribution.custom_sources["PHB"]
    assert new_config.primary_override.enabled
    assert new_config.primary_override.source == "/path/to/data"

# Test CLI integration
def test_data_commands():
    result = runner.invoke(app, ["data", "list"])
    assert result.exit_code == 0
    assert "Data Repository Status" in result.stdout

# Test MCP tool integration
async def test_mcp_data_tools():
    result = await manage_data_sources("list", context=mock_context)
    assert "repositories" in result
    assert result["performance"]["target_met"] is True
```

### Quality Metrics

**Test Coverage**: >95% on new data source components
**Type Safety**: Full mypy + pyright compliance
**Performance**: Sub-target performance for all operations
**Compatibility**: Comprehensive backward compatibility testing

## Migration Checklist

### For Users

- [ ] **Backup**: Save current configuration before migration
- [ ] **Review**: Check `studiorum config show` output
- [ ] **Migrate**: Run `studiorum config migrate`
- [ ] **Validate**: Execute `studiorum config validate`
- [ ] **Test**: Try `studiorum data list` and `studiorum data status`

### For Developers

- [ ] **Update Code**: Use new service protocols
- [ ] **Test Integration**: Verify AsyncRequestContext patterns
- [ ] **Check Imports**: Update to new configuration models
- [ ] **Documentation**: Update references to data vs sources
- [ ] **Migration Notes**: Document any custom configuration needs

## Future Extensions

### Planned Features

**Git Integration**: Direct Git repository management with branch tracking
**Content Validation**: Automated 5etools schema validation
**Performance Monitoring**: Real-time metrics and optimization suggestions
**Plugin System**: Extensible content transformation pipeline

### Extension Points

**Custom Sources**: Plugin architecture for new source types
**Validation Rules**: Custom validation for specific content formats
**Caching Strategies**: Pluggable caching backends
**Network Protocols**: Support for additional network protocols

---

## Resources

- 🏗️ **[Architecture Overview](architecture.md)** - Complete system design
- 🚀 **[Getting Started](getting-started.md)** - Development setup
- 🤖 **[AI Agent Development](ai-agents.md)** - MCP integration patterns
- 📚 **[API Reference](api/services.md)** - Service layer documentation
- 💬 **[Migration Support](https://github.com/sargeant/studiorum/discussions)** - Community help

*Successfully delivered modern three-tier data architecture with seamless migration path and comprehensive testing coverage.*
