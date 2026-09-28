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

### Running it as a service

Over HTTP the server listens at `/mcp`. It opens its port only once the data has loaded, so a TCP check on the port, or `GET /healthz` (200, `ok`), is a readiness check; a plain `GET /mcp` returns 406. Sessions live in the process, so run one replica. Every tool is annotated read-only and idempotent.

A container image or other deployment can rely on these, and a change to any of them is called out in the pull request that makes it:

- The command: `studiorum mcp run --transport http --host 0.0.0.0 --port 8000`, with `--all-content` for everything by default, and `--client-ip-header NAME` (or `STUDIORUM_TRUSTED_CLIENT_IP_HEADER=NAME`) to log the client address from a header the proxy in front sets, such as Cloudflare's `CF-Connecting-IP`. Without it the log has the TCP peer. Only set it when nothing but that proxy can reach the server, since a client can send any header.
- The configuration file, named by `STUDIORUM_CONFIG_FILE`: `data.dirs` (5etools `data/` directories; spell class lists come from each one's `generated/`), `data.homebrew`, `logging.level` and `logging.format`. An unknown top-level key is an error.
- Environment variables: `STUDIORUM_<SECTION>__<KEY>` overrides a configuration key, such as `STUDIORUM_LOGGING__LEVEL=INFO`; `STUDIORUM_PROGRESS=false` turns off progress bars; `STUDIORUM_CACHE_DIR` sets the cache directory (else the platform's user cache directory, under `XDG_CACHE_HOME` on Linux); `STUDIORUM_TELEMETRY=true` with `LOGFIRE_TOKEN` also sends logs to Logfire.
- Logs: one JSON object per line on stderr (see [Configuration](configuration.md#logging-configuration)). At INFO each MCP request is one line with `method`, `tool`, `status` (`ok`, `error` for a bad call, `failed` for a crash), `duration_ms`, `session` and `client_ip`.

`make mcp-smoke` starts the server over HTTP with your configuration, checks `/healthz` and calls three tools; `uv run python scripts/mcp_smoke.py --url URL` checks one already running.

## Tools

| Tool | What it returns |
|---|---|
| `search_spells` | Spells by name, level, school, class list, ritual or concentration |
| `search_creatures` | Creatures by name, challenge rating range, and creature type or a tag on it such as demon or goblinoid |
| `search_items` | Items by name, kind (ring, wand, wondrous, weapon), rarity, attunement, or magic items only |
| `search_content` | Entries of any type `get_content` reads, by name or source (every one of a type without a query): deities, feats, races, backgrounds, random tables and the rest |
| `search_rules` | Actions, conditions, statuses, variant rules, senses, hazards, and weapon properties and masteries whose name or text has the words asked for |
| `get_content` | One entry in full, such as a statblock (with its lair actions and regional effects), a spell, a class feature, a generic magic item such as Flame Tongue, or a random table, as Markdown |
| `get_contents` | Up to 20 entries in full in one call |
| `get_class_progression` | A class's table by level: proficiency bonus, features, spell slots and its other columns |
| `list_publications` | The books and adventures loaded, by name, date or kind |
| `get_table_of_contents` | A book or adventure's chapters and sections, with their ids and sizes |
| `read_section` | One chapter or section of a book or adventure as Markdown |
| `search_publication` | The sections of a book or adventure, or of all of them, that mention something |
| `calculate_encounter_budget` | The XP for each encounter difficulty for a party |
| `rate_encounter` | How hard a group of creatures is for a party |
| `suggest_creatures` | Creatures that make an encounter of a given difficulty |

The search tools return short summaries (name, source, level or challenge rating, and so on) with the number of matches, up to a `limit` of 100. Pass `include_text=true` to `search_spells`, `search_creatures`, `search_items` or `search_content` to get each result's text too, as `get_content` gives it; a page then stops at 24,000 characters, so it can hold fewer results than `limit`, and `next_offset` picks up the rest. Without `include_text`, results have no `text` field. If a name isn't found, the error suggests names that contain it (as a whole word or at the start of one first, then inside a word), then the closest spellings. With a `source`, suggestions come from that source, or from every source when nothing there is close. A creature that can be one of several types, such as the Battle Familiar, gives them as `celestial | fey | fiend` and matches a `creature_type` filter for any of them. A statblock that scales with the spell or class level that summons it has no `cr`. A parameter a tool doesn't take is an error that lists the ones it does. Each result says whether the call kept to the SRD (`srd_only`) and, when the SRD filter left matches out, how many (`hidden_by_srd`). Every tool that returns a list takes `limit` and `offset` and returns `total` and `next_offset`, the offset of the next page (left out on the last). Replies leave out a field that would be null or an empty list, and each field's description says what its absence means. `read_section` is the exception: its pages are pages of text (`page` and `pages`). An unknown class or creature type, or `cr_min` above `cr_max`, is an error that lists what's valid. Searches leave out an entry when a later book reprints it and the reprint is also a match, so you see the XPHB Fireball and not the PHB one. Pass `latest_only=false` to see both. 5etools marks a reprinted class or subclass but not its features, so `search_content` leaves out a feature of the PHB Wizard when the XPHB Wizard has one of the same name.

`search_rules` matches every word of the query against a rule's name and text, with a short snippet of the text around the match. A rule named the query comes first, then a rule with a part named it, then other name matches. That finds rules that aren't where you'd expect: in the 2024 rules, Grapple and Shove are parts of the Unarmed Strike variant rule, so a search for either puts Unarmed Strike near the top. Some DMG and XGE options are kept both as an action and as a part of a variant rule (Climb onto a Bigger Creature in Action Options); when the variant rule matches only in such a part, the action is listed and the variant rule isn't.

`get_content` returns an entry as Markdown: a creature as a statblock, and spells, items, classes and subclasses in their own layouts, with tags reduced to their text. Pass `format="json"` for the 5etools data instead, less what only the 5etools site uses (its filter tags, token and sound clip fields). `references` lists what the entry's text links to, such as the items a creature carries, for further `get_content` calls; `include_references=false` leaves it out. A class lists its features with their 5etools uids, such as `Spell Mastery|Wizard|XPHB|18|XPHB`; pass one as the name with `content_type="classFeature"` (or `subclassFeature`) to read it. A condition comes with the text of the conditions it names, and those they name in turn, so Unconscious brings Incapacitated and Prone in one call. Without a `source`, `get_content` returns the latest edition: a 2024 entry, then the 2024 core rules, then the 2014 core rules, then an entry with text over one that only names itself. With a `source` that doesn't have the name, the error lists the sources that do. `rate_encounter` picks creatures the same way. Specific magic items such as +3 Plate Armor are built from 5etools' generic variants, as the 5etools site builds them.

`get_contents` takes a list of up to 20 requests, each a `content_type`, `name` and optional `source`, and returns them as `get_content` would, up to 24,000 characters in all. When the entries would run past that it stops short and `next_offset` says where to resume. Names it can't find are listed in `not_found` with their place in the list and the reason, and an entry asked for twice comes once. Entries leave out `references` unless you pass `include_references=true`.

`get_class_progression` takes a class (and optionally its `source`, a `subclass` and a `level`) and returns its table by level: proficiency bonus, the features gained with their uids, and the class's own columns, such as cantrips and spell slots by spell level, rendered as the 5etools class page shows them. The column labels come once, in `columns`, and each level's `cells` line up with them; a level leaves out `features` or `subclass_features` when it gains none. A subclass adds its features and any columns it has, such as an Eldritch Knight's spell slots. With `subclass_only=true` the reply keeps only the levels the subclass gains features at and only its own columns, without the class's table. Feature uids are given in full, with every source filled in, as `search_content` gives them.

`search_content` gives a `uid` and a `detail` where a name and source repeat, such as the Celtic and Forgotten Realms Silvanus in the PHB; pass the uid as `get_content`'s name to pick one.

`list_publications` gives each book or adventure's `id` and the `source` its content carries, newest first. `query` keeps those whose name or id contains the text, `published_after` those published on or after a date (`2024` or `2024-11-12`), and `newest_first=false` lists them oldest first; it returns 20 at a time unless you pass `limit` (up to 200). They differ for some, such as `PS-X` and `PSX`, and `sources` filters take either. `list_publications` and the reading tools have no SRD filter, because 5etools doesn't mark books and adventures that way.

### Reading books and adventures

`get_content` doesn't return books or adventures, which run to hundreds of thousands of characters. Read them a section at a time:

1. `get_table_of_contents` takes an id from `list_publications` (such as `LMoP`), or the full name, and lists its chapters with their sections' ids and their size in characters. A section that holds nothing but statblocks lists them in `statblocks`, so you can go straight to `get_content`. `depth` lists more levels of sections, and `section_id` lists the sections inside one section. A long listing comes in pages of `limit` sections (100 unless you say otherwise), with `total` and `next_offset`.
2. `read_section` returns one chapter or section as Markdown. Subsections short enough are part of the text; `sections` lists the ones too long for a page, with their ids. Tags such as `{@creature goblin|MM}` become their text ("goblin"), and a statblock becomes a line naming the creature, which `get_content` returns in full. Pass `expand_statblocks=true` to have each statblock laid out in full in its place instead, as `get_content` gives it; a section full of spells or creatures then takes more pages. A page holds up to 24,000 characters. A longer section comes in pages (`page`, `pages`), and a subsection too long for a page is left as a pointer to read on its own. `references` lists what the page links to: content for `get_content`, other sections by id, and other books and adventures by publication id. With `expand_statblocks=true` the text already holds what the statblocks link to, so `references` is left out unless you pass `include_references=true`; `include_references=false` leaves it out at any time.
3. `search_publication` finds the sections that mention something, with a breadcrumb path and a snippet. Every word must appear in a section's name or its own text, even inside a longer word, so "detonat" finds "detonated". Results are ranked by how well they match: a section named exactly the query, then one whose name holds the words whole, then other name matches, then a section with a statblock named the query, then one with a heading or table cell named it, then whole words in the text, then parts of words. Ties go in book order, oldest publication first. Leave out `publication` to search every book and adventure to find which one has something. `names_only=true` matches section names alone and leaves out each result's snippet and size. The first search over all of them takes a couple of seconds while the text is prepared, and later ones take a fraction of a second.

### Encounters

The encounter tools take the party as a list of character levels, such as `[5, 5, 5, 4]`, and `rules`:

- `2024` (the default): the 2024 Dungeon Master's Guide. Each difficulty (low, moderate, high) has a budget, the most XP the creatures can be worth.
- `2014`: the 2014 Dungeon Master's Guide. Each difficulty (easy, medium, hard, deadly) has a threshold, the least adjusted XP. The creatures' total XP is multiplied by a factor for how many there are, shifted for parties smaller than three or larger than five.

`calculate_encounter_budget` returns those numbers. `rate_encounter` takes creatures by name, with a count and optionally a source, and returns their XP, the adjusted XP and the difficulty it reaches. If it can't find some of the names, the error lists each with its closest matches. `notes` flags a creature that 5etools reprinted under another name, such as the 2014 Goblin, which the 2025 Monster Manual calls Goblin Warrior. `suggest_creatures` returns creatures that, a given `count` at a time, make an encounter of the difficulty asked for, strongest first. It can filter by creature type and by the environments 5etools tags creatures with (forest, underdark, urban and so on). For a mixed group, pick creatures and check them with `rate_encounter`. It leaves out creatures whose XP isn't their challenge rating's, such as Flee, Mortals! minions and retainers; pass `include_minions=true` to see them.

## Troubleshooting

- **The client can't start the server.** Run the command from your client configuration in a terminal. `studiorum mcp run` should wait silently for input; press Ctrl-C to stop it. If it exits, the error names the problem, usually a missing configuration file or data directory.
- **Nothing comes back.** Check `srd_only`: much of the data is outside the SRD. `studiorum data show` lists the data directories the server loads.
- **Logs.** The server writes logs to stderr, never to stdout, which carries the protocol. Claude Desktop keeps each server's stderr in its own log directory (on macOS, `~/Library/Logs/Claude/`). Run with `--verbose` (before `mcp`) to log each request.
