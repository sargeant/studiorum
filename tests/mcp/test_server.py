"""Every tool, called through FastMCP's in-memory client.

Each Client runs the server lifespan, so each call is a cold start.
"""

from __future__ import annotations

from typing import Any, get_args

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from studiorum.core.models.content import ContentType
from studiorum.mcp.server import mcp
from studiorum.mcp.tools.lookup import EntryType

pytestmark = pytest.mark.usefixtures("mcp_data")


async def call(tool: str, **args: Any) -> dict[str, Any]:
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.structured_content is not None
    return result.structured_content


def names(result: dict[str, Any]) -> list[str]:
    return [r["name"] for r in result["results"]]


@pytest.mark.asyncio
async def test_the_server_lists_its_tools() -> None:
    async with Client(mcp) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert set(tools) == {
        "search_spells",
        "search_creatures",
        "search_items",
        "get_content",
        "list_publications",
        "calculate_encounter_budget",
        "rate_encounter",
        "suggest_creatures",
        "get_table_of_contents",
        "read_section",
    }
    # Depends parameters stay out of the schema
    assert "services" not in tools["search_spells"].inputSchema["properties"]


@pytest.mark.asyncio
async def test_search_spells_defaults_to_srd() -> None:
    assert names(await call("search_spells")) == ["Alarm", "Fireball"]
    everything = await call("search_spells", srd_only=False)
    assert names(everything) == ["Alarm", "Fireball", "Hellfire Orb"]
    assert [r["srd"] for r in everything["results"]] == [True, True, False]


@pytest.mark.asyncio
async def test_search_spells_filters() -> None:
    assert names(await call("search_spells", query="fire")) == ["Fireball"]
    assert names(await call("search_spells", level=3, school="evocation")) == [
        "Fireball"
    ]
    assert names(await call("search_spells", ritual=True)) == ["Alarm"]
    assert names(await call("search_spells", ritual=False)) == ["Fireball"]
    result = await call("search_spells", srd_only=False, limit=1)
    assert result["total"] == 3
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_search_creatures_filters() -> None:
    assert names(await call("search_creatures", query="goblin")) == ["Goblin"]
    assert names(await call("search_creatures", query="goblin", srd_only=False)) == [
        "Goblin",
        "Goblin Sneak",
    ]
    quarter = await call("search_creatures", cr_min=0.25, cr_max=0.25)
    assert names(quarter) == ["Acolyte", "Goblin"]
    assert quarter["results"][1] == {
        "name": "Goblin",
        "source": "SRD",
        "srd": True,
        "cr": "1/4",
        "type": "humanoid",
    }
    assert names(await call("search_creatures", creature_type="humanoid")) == [
        "Acolyte",
        "Goblin",
    ]
    assert names(await call("search_creatures", creature_type="dragon")) == [
        "Young Red Dragon"
    ]


@pytest.mark.asyncio
async def test_search_items_filters() -> None:
    assert names(await call("search_items")) == ["Ale (mug)", "Amulet of Health"]
    assert names(await call("search_items", rarity="rare", srd_only=False)) == [
        "Amulet of Grit",
        "Amulet of Health",
    ]
    assert names(await call("search_items", magic_only=True)) == ["Amulet of Health"]


@pytest.mark.asyncio
async def test_search_items_names_the_type() -> None:
    ale = (await call("search_items", query="ale"))["results"][0]
    assert ale["type"] == "Food and Drink"


@pytest.mark.asyncio
async def test_get_content_returns_the_entry() -> None:
    result = await call(
        "get_content", content_type="spell", name="fireball", format="json"
    )
    assert result["text"] is None
    assert result["name"] == "Fireball"
    assert result["srd"] is True
    assert result["data"]["level"] == 3
    assert result["data"]["source"] == "SRD"


@pytest.mark.asyncio
async def test_get_content_keeps_to_the_srd() -> None:
    with pytest.raises(ToolError, match="not in the SRD; pass srd_only=false"):
        await call("get_content", content_type="spell", name="Hellfire Orb")
    result = await call(
        "get_content", content_type="spell", name="Hellfire Orb", srd_only=False
    )
    assert result["srd"] is False


@pytest.mark.asyncio
async def test_get_content_suggests_names() -> None:
    with pytest.raises(
        ToolError, match="No creature named 'Goblim'. Did you mean: Goblin"
    ):
        await call("get_content", content_type="creature", name="Goblim")


@pytest.mark.asyncio
async def test_list_publications() -> None:
    result = await call("list_publications")
    assert [(p["id"], p["kind"]) for p in result["publications"]] == [
        ("TA", "adventure"),
        ("TB", "book"),
    ]
    books = await call("list_publications", kind="book")
    assert [p["name"] for p in books["publications"]] == ["Test Book"]


def test_entry_types_are_content_types() -> None:
    for name in get_args(EntryType):
        ContentType(name)


@pytest.mark.asyncio
async def test_all_content_changes_the_srd_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from studiorum.mcp.server import options

    monkeypatch.setattr(options, "all_content", True)
    assert names(await call("search_spells")) == ["Alarm", "Fireball", "Hellfire Orb"]
    assert names(await call("search_spells", srd_only=True)) == ["Alarm", "Fireball"]
    result = await call("get_content", content_type="spell", name="Hellfire Orb")
    assert result["srd"] is False


@pytest.mark.asyncio
async def test_searches_leave_out_reprinted_entries() -> None:
    latest = await call("search_spells", query="alarm")
    assert [(r["name"], r["source"]) for r in latest["results"]] == [("Alarm", "XPHB")]
    both = await call("search_spells", query="alarm", latest_only=False)
    assert [r["source"] for r in both["results"]] == ["SRD", "XPHB"]


@pytest.mark.asyncio
async def test_get_content_as_markdown() -> None:
    goblin = (await call("get_content", content_type="creature", name="Goblin"))["text"]
    assert goblin.startswith("# Goblin\n\n*Small humanoid (goblinoid), neutral evil*")
    assert "**Armor Class** 15 (leather armor, shield)" in goblin
    assert "| 8 (-1) | 14 (+2) | 10 (+0) | 10 (+0) | 8 (-1) | 8 (-1) |" in goblin
    assert "**Challenge** 1/4 (50 XP)" in goblin
    assert "***Scimitar.*** *Melee Weapon Attack:* +4 to hit" in goblin

    fireball = (await call("get_content", content_type="spell", name="Fireball"))[
        "text"
    ]
    assert "*Level 3 Evocation*" in fireball
    assert "**Range** 150 feet" in fireball
    assert "{@" not in fireball


@pytest.mark.asyncio
async def test_get_content_reads_classes_and_features() -> None:
    wizard = (await call("get_content", content_type="class", name="Wizard"))["text"]
    assert "**Hit Die** d6" in wizard
    assert "- Level 1: Arcane Recovery (`Arcane Recovery|Wizard||1`)" in wizard
    assert "- School of Evocation (SRD)" in wizard

    by_uid = await call(
        "get_content",
        content_type="classFeature",
        name="Arcane Recovery|Wizard||1",  # as the class lists it
    )
    assert by_uid["text"].startswith("# Arcane Recovery\n\n*Level 1 Wizard feature*")
