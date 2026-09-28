"""The reading tools, through FastMCP's in-memory client."""

from __future__ import annotations

import re
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from studiorum.mcp.markdown import references, render, strip_tags
from studiorum.mcp.server import mcp

pytestmark = pytest.mark.usefixtures("mcp_data")


async def call(tool: str, **args: Any) -> dict[str, Any]:
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.structured_content is not None
    return result.structured_content


def ids(result: dict[str, Any]) -> list[tuple[str, str, int]]:
    return [(s["id"], s["name"], s["depth"]) for s in result["sections"]]


@pytest.mark.asyncio
async def test_table_of_contents() -> None:
    top = await call("get_table_of_contents", publication="ta")
    assert (top["id"], top["kind"]) == ("TA", "adventure")
    # A section nested in a chapter is listed under it, as 5etools does
    assert ids(top) == [("000", "Welcome", 1), ("002", "The Cave", 1)]
    deep = await call("get_table_of_contents", publication="Test Adventure", depth=2)
    assert ids(deep) == [
        ("000", "Welcome", 1),
        ("001", "Hooks", 2),
        ("004", "Background", 2),
        ("002", "The Cave", 1),
        ("003", "Big Room", 2),
        ("005", "Guards", 2),
    ]
    assert (deep["total"], deep.get("next_offset")) == (6, None)
    paged = await call("get_table_of_contents", publication="TA", depth=2, limit=4)
    assert (ids(paged)[-1], paged.get("next_offset")) == (("002", "The Cave", 1), 4)
    rest = await call(
        "get_table_of_contents", publication="TA", depth=2, limit=4, offset=4
    )
    assert ids(rest) == ids(deep)[4:]
    inside = await call("get_table_of_contents", publication="TA", section_id="002")
    assert ids(inside) == [("003", "Big Room", 1), ("005", "Guards", 1)]
    assert inside["sections"][0]["chars"] > 30000
    # A section that only holds statblocks says which
    assert [s.get("statblocks") for s in inside["sections"]] == [None, ["Goblin"]]

    book = await call("get_table_of_contents", publication="TB")
    assert (book["kind"], ids(book)) == ("book", [("100", "Rules", 1)])


@pytest.mark.asyncio
async def test_read_section_as_markdown() -> None:
    welcome = await call("read_section", publication="TA", section_id="000")
    assert welcome["text"] == (
        "# Welcome\n\nHello goblins.\n\n## Hooks\n\nA hook.\n\n- one\n- two"
        "\n\n## Background\n\nLong ago. See the side trek."
    )
    assert (welcome["page"], welcome["pages"]) == (1, 1)
    # Empty lists and nulls are left out
    assert "path" not in welcome
    # Its subsections are in the text, so aren't listed
    assert "sections" not in welcome

    rules = await call("read_section", publication="TB", section_id="100")
    assert rules["text"] == "# Rules\n\nRoll a d20."


@pytest.mark.asyncio
async def test_read_section_points_to_long_subsections() -> None:
    cave = await call("read_section", publication="TA", section_id="002")
    assert cave["pages"] == 1
    assert cave["text"].split("\n\n")[:3] == [
        "# The Cave",
        "## Big Room",
        "*[Section 003, 30,016 characters: read it with read_section.]*",
    ]
    assert "| d4 | Item |\n|---|---|\n| 1 | Potion of Healing |" in cave["text"]
    assert "*[Creature statblock: Goblin (MM)]*" in cave["text"]
    assert "> You smell smoke." in cave["text"]
    assert [s["id"] for s in cave["sections"]] == ["003"]


@pytest.mark.asyncio
async def test_read_section_expands_statblocks() -> None:
    guards = await call(
        "read_section", publication="TA", section_id="005", expand_statblocks=True
    )
    # Laid out as get_content lays it out, with headings under the section's
    goblin = await call("get_content", content_type="creature", name="Goblin")
    body = re.sub(r"^(#+) ", r"#\1 ", goblin["text"], flags=re.MULTILINE)
    assert guards["text"] == "# Guards\n\n" + body
    assert "Statblock" not in guards["text"]
    # The text holds what references would, so they're left out unless asked for
    assert "references" not in guards
    guards = await call(
        "read_section",
        publication="TA",
        section_id="005",
        expand_statblocks=True,
        include_references=True,
    )
    # References keep the statblock and add what its text links to
    refs = [(r["type"], r["name"]) for r in guards["references"]]
    assert refs[0] == ("creature", "Goblin")
    assert {(r["type"], r["name"]) for r in goblin["references"]} <= set(refs)

    # A statblock for something not loaded stays a line
    cave = await call(
        "read_section", publication="TA", section_id="002", expand_statblocks=True
    )
    assert "*[Creature statblock: Owlbear (MM)]*" in cave["text"]


@pytest.mark.asyncio
async def test_read_section_pages() -> None:
    first = await call("read_section", publication="TA", section_id="003")
    assert (first["pages"], first["path"]) == (2, ["The Cave"])
    second = await call("read_section", publication="TA", section_id="003", page=2)
    assert len(first["text"]) <= 24000
    assert first["text"].count("word") + second["text"].count("word") == 6000
    with pytest.raises(ToolError, match="Section 003 has 2 page"):
        await call("read_section", publication="TA", section_id="003", page=3)


@pytest.mark.asyncio
async def test_reading_errors() -> None:
    with pytest.raises(ToolError, match="No section '999' in TA"):
        await call("read_section", publication="TA", section_id="999")
    with pytest.raises(ToolError, match="Did you mean: Test Adventure"):
        await call("get_table_of_contents", publication="Test Adventurer")


@pytest.mark.parametrize(
    ("text", "plain"),
    [
        ("{@creature goblin|MM|the {@i sneaky} goblin}", "the *sneaky* goblin"),
        (
            "{@atk mw} {@hit 4} to hit. {@h}5 ({@damage 1d6 + 2})",
            "*Melee Weapon Attack:* +4 to hit. *Hit:* 5 (1d6 + 2)",
        ),
        (
            "{@recharge 5} {@recharge} {@dc 13} {@chance 50}",
            "(Recharge 5–6) (Recharge 6) DC 13 50 percent",
        ),
        (
            "{@classFeature Rage|Barbarian||1} {@deity Mask|Forgotten Realms|PHB|the god}",
            "Rage the god",
        ),
        (
            "{@area 3|012|x} {@area Hall|013} {@b bold} and {@unknownTag x|y}",
            "3 area Hall **bold** and x",
        ),
        ("{@actSave wis} {@atkr m}", "*Wisdom Saving Throw:* *Melee Attack Roll:*"),
        ("a {b} c", "a {b} c"),
        (
            "{@damage 1d8 + 3 + summonSpellLevel} {@damage (summonSpellLevel - 4)d4|1d4}",
            "1d8 + 3 + the spell's level 1d4",
        ),
        ("{@dice 2d8 + summonClassLevel}", "2d8 + your class level"),
    ],
)
def test_strip_tags(text: str, plain: str) -> None:
    assert strip_tags(text) == plain


def test_a_statblock_without_a_source_takes_the_default() -> None:
    goblin = {"type": "statblock", "name": "Goblin", "tag": "creature"}
    assert render(goblin) == "*[Creature statblock: Goblin (MM)]*"
    assert references([goblin]) == [
        {"type": "creature", "name": "Goblin", "source": "MM"}
    ]


@pytest.mark.parametrize(
    ("entry", "markdown"),
    [
        ({"type": "bonus", "value": 2}, "+2"),
        ({"type": "bonusSpeed", "value": 10}, "+10 ft."),
        ({"type": "bonusSpeed", "value": 0}, "\u2014"),
        (
            {"type": "dice", "toRoll": [{"number": 2, "faces": 6, "modifier": 3}]},
            "2d6+3",
        ),
        ({"type": "refOptionalfeature", "optionalfeature": "Dueling|XPHB"}, "Dueling"),
        (
            {
                "type": "ingredient",
                "entry": "{=amount1/v} cup {@item flour}",
                "amount1": 1.5,
            },
            "1 1/2 cup flour",
        ),
        (
            {
                "type": "flowchart",
                "blocks": [{"type": "flowBlock", "name": "Start", "entries": ["Go."]}],
            },
            "# Start\n\nGo.",
        ),
        (
            {
                "type": "spellcasting",
                "name": "Shared Spellcasting",
                "headerEntries": ["The coven casts:"],
                "spells": {"1": {"slots": 4, "spells": ["{@spell sleep}"]}},
            },
            "# Shared Spellcasting\n\nThe coven casts:\n\nLevel 1 (4 slots): sleep",
        ),
    ],
)
def test_entry_types_render_as_5etools_shows_them(
    entry: dict[str, Any], markdown: str
) -> None:
    assert render(entry) == markdown


def test_an_items_attached_spells_are_references_without_level_or_ability() -> None:
    signet = {
        "attachedSpells": {
            "daily": {"1e": ["augury", "fireball#5", "summon dragon|xphb#9"]},
            "ability": "int",
        }
    }

    assert [(r["name"], r["source"]) for r in references(signet)] == [
        ("augury", "PHB"),
        ("fireball", "PHB"),
        ("summon dragon", "xphb"),
    ]


def test_a_quote_names_who_and_where() -> None:
    quote = {
        "type": "quote",
        "entries": ["Hi"],
        "by": "{@creature Strahd von Zarovich|CoS}",
        "from": "I, Strahd",
    }
    assert render(quote) == "> Hi\n>\n> — Strahd von Zarovich, *I, Strahd*"
    assert render({"type": "quote", "entries": ["Hi"], "from": "Vows"}) == (
        "> Hi\n>\n> — *Vows*"
    )


@pytest.mark.asyncio
async def test_read_section_lists_references() -> None:
    cave = await call("read_section", publication="TA", section_id="002")
    refs = [
        (r["type"], r["name"], r.get("source"), r.get("section_id"))
        for r in cave["references"]
    ]
    assert refs == [
        ("section", "Big Room", None, "003"),
        ("item", "Potion of Healing", "DMG", None),
        ("creature", "Goblin", "MM", None),
        ("creature", "Owlbear", "MM", None),
        ("creature", "Goblin", "SRD", None),
        ("section", "the big room", None, "003"),
    ]
    bare = await call(
        "read_section", publication="TA", section_id="002", include_references=False
    )
    assert "references" not in bare


@pytest.mark.asyncio
async def test_search_publication() -> None:
    result = await call("search_publication", publication="TA", query="guards")
    assert [(r["id"], r["name"], r.get("path", [])) for r in result["results"]] == [
        ("005", "Guards", ["The Cave"]),
        ("002", "The Cave", []),
    ]
    assert result["results"][1]["snippet"].endswith(
        "Past the guards, the big room holds a Potion of Healing."
    )
    # A section's own text, not its subsections'
    hooks = await call("search_publication", publication="TA", query="hook")
    assert [r["id"] for r in hooks["results"]] == ["001"]


@pytest.mark.asyncio
async def test_search_every_publication() -> None:
    def found(result: dict[str, Any]) -> list[tuple[str, str]]:
        return [(r["publication"], r["id"]) for r in result["results"]]

    trek = await call("search_publication", query="trek")
    assert "publication" not in trek
    # Named sections first, then the text, oldest publication first
    assert found(trek) == [("TB-ST", "200"), ("TA", "004")]
    names = await call("search_publication", query="trek", names_only=True)
    assert found(names) == [("TB-ST", "200")]
    # Names only: no snippet or size
    assert names["results"][0] == {
        "publication": "TB-ST",
        "id": "200",
        "name": "Trek",
    }
    assert found(await call("search_publication", query="roll d20")) == [("TB", "100")]
    one = await call("search_publication", query="trek", publication="TA")
    assert (one["publication"], found(one)) == ("TA", [("TA", "004")])


@pytest.mark.asyncio
async def test_search_publication_ranks_matches() -> None:
    def found(result: dict[str, Any]) -> list[str]:
        return [r["id"] for r in result["results"]]

    # The exact name, then the word whole in a name, then inside a word
    traps = await call("search_publication", query="traps", names_only=True)
    assert found(traps) == ["203", "201", "202"]
    # A statblock named for it, then a table cell, then the word whole in the
    # text, then inside a word
    assert found(await call("search_publication", query="detonate")) == [
        "203",
        "204",
        "202",
        "201",
    ]
    # Parts of words still match, and ties go in book order
    assert found(await call("search_publication", query="detonat")) == [
        "201",
        "202",
        "204",
        "203",
    ]
    assert found(await call("search_publication", query="mousetrap")) == ["202"]


@pytest.mark.asyncio
async def test_an_adventure_sharing_a_books_source_is_found_by_its_id() -> None:
    book = await call("get_table_of_contents", publication="TB")
    trek = await call("get_table_of_contents", publication="TB-ST")
    assert (book["kind"], trek["kind"], trek["id"]) == ("book", "adventure", "TB-ST")
    assert ids(trek) == [("200", "Trek", 1)]


@pytest.mark.asyncio
async def test_links_to_other_publications_are_references() -> None:
    welcome = await call("read_section", publication="TA", section_id="004")
    assert {
        (r["type"], r["name"], r["publication"]) for r in welcome["references"]
    } == {("publication", "the side trek", "TB-ST")}
