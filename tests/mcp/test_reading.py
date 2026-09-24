"""The reading tools, through FastMCP's in-memory client."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from studiorum.mcp.markdown import strip_tags
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
    # A section nested in a chapter is listed beside it
    assert ids(top) == [
        ("000", "Welcome", 1),
        ("004", "Background", 1),
        ("002", "The Cave", 1),
    ]
    deep = await call("get_table_of_contents", publication="Test Adventure", depth=2)
    assert ids(deep) == [
        ("000", "Welcome", 1),
        ("001", "Hooks", 2),
        ("004", "Background", 1),
        ("002", "The Cave", 1),
        ("003", "Big Room", 2),
        ("005", "Guards", 2),
    ]
    inside = await call("get_table_of_contents", publication="TA", section_id="002")
    assert ids(inside) == [("003", "Big Room", 1), ("005", "Guards", 1)]
    assert inside["sections"][0]["chars"] > 30000
    # A section that only holds statblocks says which
    assert [s["statblocks"] for s in inside["sections"]] == [None, ["Goblin"]]

    book = await call("get_table_of_contents", publication="TB")
    assert (book["kind"], ids(book)) == ("book", [("100", "Rules", 1)])


@pytest.mark.asyncio
async def test_read_section_as_markdown() -> None:
    welcome = await call("read_section", publication="TA", section_id="000")
    assert welcome["text"] == (
        "# Welcome\n\nHello goblins.\n\n## Hooks\n\nA hook.\n\n- one\n- two"
        "\n\n## Background\n\nLong ago."
    )
    assert (welcome["page"], welcome["pages"], welcome["path"]) == (1, 1, [])
    assert [s["id"] for s in welcome["sections"]] == ["001", "004"]

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
    ],
)
def test_strip_tags(text: str, plain: str) -> None:
    assert strip_tags(text) == plain


@pytest.mark.asyncio
async def test_read_section_lists_references() -> None:
    cave = await call("read_section", publication="TA", section_id="002")
    refs = [
        (r["type"], r["name"], r["source"], r["section_id"]) for r in cave["references"]
    ]
    assert refs == [
        ("section", "Big Room", None, "003"),
        ("item", "Potion of Healing", "DMG", None),
        ("creature", "Goblin", "MM", None),
        ("section", "the big room", None, "003"),
    ]


@pytest.mark.asyncio
async def test_search_publication() -> None:
    result = await call("search_publication", publication="TA", query="guards")
    assert [(r["id"], r["name"], r["path"]) for r in result["results"]] == [
        ("005", "Guards", ["The Cave"]),
        ("002", "The Cave", []),
    ]
    assert result["results"][1]["snippet"].endswith(
        "Past the guards, the big room holds a Potion of Healing."
    )
    # A section's own text, not its subsections'
    hooks = await call("search_publication", publication="TA", query="hook")
    assert [r["id"] for r in hooks["results"]] == ["001"]
