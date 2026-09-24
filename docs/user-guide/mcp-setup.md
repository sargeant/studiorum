---
title: MCP Integration
description: Run studiorum as an MCP server so an AI client can search 5e content
---

# MCP Integration

!!! warning "Experimental"
    The MCP server is new and has had little use with real clients. The CLI is the main interface.

Studiorum includes a Model Context Protocol (MCP) server. An MCP client such as Claude Desktop can use it to search the 5etools data studiorum loads, read single entries in full, read books and adventures a section at a time, and work out encounter difficulty. The server is read-only: it doesn't change configuration or write files.

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

### SRD only, or everything

Content tools return only entries that 5etools marks as part of the 2014 SRD or the 5.2 SRD unless a call passes `srd_only=false`. For a personal install with your own data, start the server with `--all-content` to make everything the default instead: `"args": ["run", "--directory", "/path/to/studiorum", "studiorum", "mcp", "run", "--all-content"]`. A call can still pass `srd_only=true`.

## Tools

| Tool | What it returns |
|---|---|
| `search_spells` | Spells by name, level, school, class list, ritual or concentration |
| `search_creatures` | Creatures by name, challenge rating range and creature type |
| `search_items` | Items by name, rarity, attunement, or magic items only |
| `search_content` | Entries of any type `get_content` reads, by name: deities, feats, races, backgrounds and the rest |
| `search_rules` | Actions, conditions, statuses, variant rules and senses whose name or text has the words asked for |
| `get_content` | One entry in full, such as a statblock, a spell, a class or a class feature, as Markdown |
| `list_publications` | The books and adventures loaded, oldest first |
| `get_table_of_contents` | A book or adventure's chapters and sections, with their ids and sizes |
| `read_section` | One chapter or section of a book or adventure as Markdown |
| `search_publication` | The sections of a book or adventure that mention something |
| `calculate_encounter_budget` | The XP for each encounter difficulty for a party |
| `rate_encounter` | How hard a group of creatures is for a party |
| `suggest_creatures` | Creatures that make an encounter of a given difficulty |

The search tools return short summaries (name, source, level or challenge rating, and so on) with the number of matches, up to a `limit` of 100. If a name isn't found, the error suggests the closest names. Each result says whether the call kept to the SRD (`srd_only`) and, when the SRD filter left matches out, how many (`hidden_by_srd`). Pass `offset` with `limit` to page through a long list. An unknown class or creature type, or `cr_min` above `cr_max`, is an error that lists what's valid. Searches leave out an entry when a later book reprints it and the reprint is also a match, so you see the XPHB Fireball and not the PHB one. Pass `latest_only=false` to see both.

`search_rules` matches every word of the query against a rule's name and text, name matches first, with a short snippet of the text around the match. It finds rules that aren't where you'd expect: in the 2024 rules, grappling is part of the Unarmed Strike variant rule.

`get_content` returns an entry as Markdown: a creature as a statblock, and spells, items, classes and subclasses in their own layouts, with tags reduced to their text. Pass `format="json"` for the 5etools data instead. `references` lists what the entry's text links to, such as the items a creature carries, for further `get_content` calls. A class lists its features with their 5etools uids, such as `Spell Mastery|Wizard|XPHB|18`; pass one as the name with `content_type="classFeature"` (or `subclassFeature`) to read it. Without a `source`, `get_content` returns the latest edition. Specific magic items such as +3 Plate Armor are built from 5etools' generic variants, as the 5etools site builds them.

`list_publications` and the reading tools have no SRD filter, because 5etools doesn't mark books and adventures that way.

### Reading books and adventures

`get_content` doesn't return books or adventures, which run to hundreds of thousands of characters. Read them a section at a time:

1. `get_table_of_contents` takes an id from `list_publications` (such as `LMoP`), or the full name, and lists its chapters with their sections' ids and their size in characters. A section that the adventure's text nests inside a chapter is listed beside it, as the 5etools site shows it. A section that holds nothing but statblocks lists them in `statblocks`, so you can go straight to `get_content`. `depth` lists more levels of sections, and `section_id` lists the sections inside one section.
2. `read_section` returns one chapter or section as Markdown, with the ids of its subsections. Tags such as `{@creature goblin|MM}` become their text ("goblin"), and a statblock becomes a line naming the creature, which `get_content` returns in full. A page holds up to 24,000 characters. A longer section comes in pages (`page`, `pages`), and a subsection too long for a page is left as a pointer to read on its own. `references` lists what the page links to: content for `get_content`, and other sections by id.
3. `search_publication` finds the sections that mention something, with a breadcrumb path and a snippet. Every word must appear in a section's name or its own text; sections named for the words come first, then the rest in book order.

### Encounters

The encounter tools take the party as a list of character levels, such as `[5, 5, 5, 4]`, and `rules`:

- `2024` (the default): the 2024 Dungeon Master's Guide. Each difficulty (low, moderate, high) has a budget, the most XP the creatures can be worth.
- `2014`: the 2014 Dungeon Master's Guide. Each difficulty (easy, medium, hard, deadly) has a threshold, the least adjusted XP. The creatures' total XP is multiplied by a factor for how many there are, shifted for parties smaller than three or larger than five.

`calculate_encounter_budget` returns those numbers. `rate_encounter` takes creatures by name, with a count and optionally a source, and returns their XP, the adjusted XP and the difficulty it reaches. If it can't find some of the names, the error lists each with its closest matches. `notes` flags a creature that 5etools reprinted under another name, such as the 2014 Goblin, which the 2025 Monster Manual calls Goblin Warrior. `suggest_creatures` returns creatures that, a given `count` at a time, make an encounter of the difficulty asked for, strongest first. It can filter by creature type and by the environments 5etools tags creatures with (forest, underdark, urban and so on). For a mixed group, pick creatures and check them with `rate_encounter`. It leaves out creatures whose XP isn't their challenge rating's, such as Flee, Mortals! minions and retainers; pass `include_minions=true` to see them.

## Troubleshooting

- **The client can't start the server.** Run the command from your client configuration in a terminal. `studiorum mcp run` should wait silently for input; press Ctrl-C to stop it. If it exits, the error names the problem, usually a missing configuration file or data directory.
- **Nothing comes back.** Check `srd_only`: much of the data is outside the SRD. `studiorum data show` lists the data directories the server loads.
- **Logs.** The server writes logs to stderr, never to stdout, which carries the protocol. Claude Desktop keeps each server's stderr in its own log directory (on macOS, `~/Library/Logs/Claude/`).
