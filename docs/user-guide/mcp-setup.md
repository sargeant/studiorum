---
title: MCP Integration
description: Set up studiorum as an MCP server for AI agent integration
---

# MCP Integration

!!! warning "Experimental"
    This is highly unstable and needs testing. The CLI is the primary interface for now.

Studiorum includes a Model Context Protocol (MCP) server that enables AI agents to convert D&D 5e content dynamically. This allows agents to generate PDFs, look up creatures, spells, and more.

## What is MCP?

The Model Context Protocol enables AI applications to integrate with external tools and data sources. Studiorum's MCP server provides AI agents with access to the complete D&D 5e dataset and conversion capabilities.

## Installation

### Claude Desktop

Add studiorum to your Claude Desktop configuration:

=== "macOS"

    Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "studiorum": {
          "command": "uv",
          "args": ["run", "studiorum", "mcp", "run"],
          "cwd": "/path/to/your/project"
        }
      }
    }
    ```

=== "Windows"

    Edit `%APPDATA%/Claude/claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "studiorum": {
          "command": "uv.exe",
          "args": ["run", "studiorum", "mcp", "run"],
          "cwd": "C:\\path\\to\\your\\project"
        }
      }
    }
    ```

### Other MCP Clients

For other MCP-compatible applications, use the server command directly:

```bash
studiorum mcp run --host 0.0.0.0 --port 3000
```

## Available Tools

Once connected, AI agents have access to these tools:

### Content Lookup

```python
# Look up creatures
lookup_creature("Ancient Red Dragon")

# Search spells by level
search_spells(level=3, school="evocation")

# Find magic items
lookup_items(rarity="legendary", type="weapon")
```

### Content Conversion

```python
# Convert single content to LaTeX
convert_content(
    content_type="creature",
    name="Beholder",
    format="latex"
)

# Convert with appendices
convert_adventure(
    name="Lost Mine of Phandelver",
    include_creatures=True,
    include_spells=True,
    format="pdf"
)
```

### Content Discovery

```python
# List available adventures
list_adventures()

# Get content statistics
get_content_stats()

# Search across all content types
search_content("dragon")
```

## Configuration

### Server Settings

Configure the MCP server in `~/.studiorum/mcp-config.yaml`:

```yaml
server:
  host: 127.0.0.1
  port: 3000
  debug: false

  # Request limits
  max_requests_per_minute: 100
  max_concurrent_requests: 10

# Content settings
content:
  # Cache converted content
  enable_cache: true
  cache_ttl: 3600  # 1 hour

  # Default sources to include
  default_sources:
    - SRD

# Output settings
output:
  # Temporary file cleanup
  cleanup_temp_files: true
  max_temp_file_age: 86400  # 24 hours

  # Default formats
  default_format: latex
  supported_formats:
    - latex
    - pdf
    - json
```

### Security

For production deployments, configure authentication:

```yaml
security:
  # API key authentication
  require_api_key: true
  api_keys:
    - key: "your-secure-api-key"
      name: "claude-desktop"
      permissions: ["read", "convert"]

  # Rate limiting
  rate_limits:
    requests_per_minute: 50
    burst_size: 10

  # Content filtering
  allowed_content_types:
    - creature
    - spell
    - item
    - adventure
```

## Usage Examples

### AI Agent Conversations

Here are example prompts that work well with the MCP integration:

#### Content Lookup

```
"Show me the stats for an Ancient Red Dragon and convert it to a PDF stat block"
```

The agent will:

1. Use `lookup_creature("Ancient Red Dragon")` to get the creature data
2. Use `convert_content()` to generate a formatted PDF stat block

#### Adventure Preparation

```
"I'm running Lost Mine of Phandelver. Create a PDF with all the creatures,
spells, and magic items from the adventure"
```

The agent will:

1. Use `convert_adventure()` with appendices enabled
2. Generate a comprehensive PDF reference document

#### Campaign Building

```
"Create a monster manual for CR 10-15 dragons with LaTeX formatting"
```

The agent will:

1. Use `search_creatures()` to find dragons in the CR range
2. Use `convert_content()` to format each creature
3. Combine into a single document

### Custom Integrations

Build custom applications using the MCP protocol:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def convert_creature(name: str) -> str:
    server_params = StdioServerParameters(
        command="studiorum",
        args=["mcp", "run"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "convert_content",
                {
                    "content_type": "creature",
                    "name": name,
                    "format": "latex"
                }
            )

            return result.content

# Usage
latex_output = asyncio.run(convert_creature("Beholder"))
```

## Debugging

### Enable Debug Mode

Start the MCP server with debug logging:

```bash
studiorum mcp run --debug --log-level DEBUG
```

### Monitor Requests

View real-time request logs:

```bash
# Follow MCP logs
tail -f ~/.studiorum/logs/mcp-server.log

# Monitor performance
studiorum mcp stats --watch
```

### Test Tools

Test MCP tools directly:

```bash
# Test creature lookup
studiorum mcp test lookup_creature "Tarrasque"

# Test conversion
studiorum mcp test convert_content \
    --content-type spell \
    --name "Fireball" \
    --format pdf
```

## Performance

### Caching

Enable intelligent caching for better performance:

```yaml
cache:
  # Redis cache (recommended for production)
  redis:
    host: localhost
    port: 6379
    db: 0

  # In-memory cache (development)
  memory:
    max_size: 1000
    ttl: 3600
```

### Optimization

Optimize for your use case:

```yaml
optimization:
  # Preload frequently used content
  preload:
    - creatures: ["Ancient Red Dragon", "Beholder", "Lich"]
    - spells: level_range: [1, 3]

  # Parallel processing
  parallel:
    max_workers: 4
    chunk_size: 10
```

## Deployment

### Docker

Deploy as a containerized service:

```dockerfile
FROM python:3.12-slim
RUN pip install studiorum
EXPOSE 3000
CMD ["studiorum", "mcp", "run", "--host", "0.0.0.0", "--port", "3000"]
```

### Systemd

Create a system service:

```ini
# /etc/systemd/system/studiorum-mcp.service
[Unit]
Description=Studiorum MCP Server
After=network.target

[Service]
Type=simple
User=studiorum
WorkingDirectory=/opt/studiorum
ExecStart=/usr/local/bin/studiorum mcp run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Connection Issues

If Claude Desktop can't connect:

1. **Check the configuration path**: Ensure `cwd` points to a valid directory
2. **Verify installation**: Run `uv run studiorum --version` in the configured directory
3. **Check logs**: Look at `~/.claude/logs/` for connection errors

### Performance Issues

For slow responses:

1. **Enable caching**: Add caching configuration
2. **Optimize sources**: Limit to essential source books
3. **Monitor memory**: Use `--max-memory` flag for large operations

### Content Not Found

If content lookups fail:

1. **Update index**: Run `studiorum index refresh`
2. **Check sources**: Verify source books are enabled
3. **Validate spelling**: Use exact names from `studiorum list` commands

## Next Steps

- **[CLI Reference](cli-reference.md)**: Learn all available commands
- **[Developer Guide](../developer-guide/index.md)**: Build custom MCP tools
- **[API Reference](../developer-guide/api/index.md)**: Integration patterns
