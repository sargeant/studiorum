---
title: MCP Integration
description: Run studiorum as an MCP server so an AI client can search 5e content
---

# MCP Integration

!!! warning "Experimental"
    The MCP server is new and has had little use with real clients. The CLI is the main interface.

Studiorum includes a Model Context Protocol (MCP) server. An MCP client such as Claude Desktop can use it to search the 5etools data studiorum loads and read single entries in full. The server is read-only: it doesn't change configuration or write files.

## Setting it up

The server loads the same data as the CLI, from the `data` section of your configuration file (see [Configuration](configuration.md)). It loads everything once at start-up, which takes a few seconds on the full 5etools data set, and answers each call from memory after that.

### Claude Desktop

Add studiorum to `claude_desktop_config.json` (on macOS, `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "studiorum": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/studiorum", "studiorum", "mcp", "run"]
    }
  }
}
```

To use a configuration file other than `~/.studiorum/config.yaml`, pass it before the subcommand: `"args": ["run", "--directory", "/path/to/studiorum", "studiorum", "-c", "/path/to/config.yaml", "mcp", "run"]`.

### Other clients

`studiorum mcp run` speaks MCP over stdio, which is what local clients expect. For a client that connects over HTTP, run:

```bash
studiorum mcp run --transport http --host 127.0.0.1 --port 8000
```

`studiorum mcp tools` lists the tools the server registers.

## Tools

| Tool | What it returns |
|---|---|
| `search_spells` | Spells by name, level, school, class list, ritual or concentration |
| `search_creatures` | Creatures by name, challenge rating range and creature type |
| `search_items` | Items by name, rarity, attunement, or magic items only |
| `get_content` | One entry in full, such as a statblock or a spell's text, by type and name |
| `list_publications` | The books and adventures loaded, oldest first |

The search tools return short summaries (name, source, level or challenge rating, and so on) with the number of matches, up to a `limit` of 100. Use `get_content` to read an entry in full. If a name isn't found, the error suggests the closest names.

Every content tool takes `srd_only`, which defaults to true. With it on, the tools return only entries that 5etools marks as part of the 2014 SRD or the 5.2 SRD. Pass `srd_only=false` to include everything in your data. `list_publications` has no SRD filter, because 5etools doesn't mark books and adventures that way.

## Troubleshooting

- **The client can't start the server.** Run the command from your client configuration in a terminal. `studiorum mcp run` should wait silently for input; press Ctrl-C to stop it. If it exits, the error names the problem, usually a missing configuration file or data directory.
- **Nothing comes back.** Check `srd_only`: much of the data is outside the SRD. `studiorum data show` lists the data directories the server loads.
- **Logs.** The server writes logs to stderr, never to stdout, which carries the protocol. Claude Desktop keeps each server's stderr in its own log directory (on macOS, `~/Library/Logs/Claude/`).
