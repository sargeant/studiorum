"""The encounter tools, through FastMCP's in-memory client."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from studiorum.mcp.server import mcp

pytestmark = [pytest.mark.usefixtures("mcp_data"), pytest.mark.asyncio]


async def call(tool: str, **args: Any) -> dict[str, Any]:
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.structured_content is not None
    return result.structured_content


def names(result: dict[str, Any]) -> list[str]:
    return [r["name"] for r in result["results"]]


async def test_calculate_encounter_budget() -> None:
    party = [5, 5, 5, 5]
    result = await call("calculate_encounter_budget", party_levels=party)
    assert result["xp"] == {"low": 2000, "moderate": 3000, "high": 4400}
    classic = await call("calculate_encounter_budget", party_levels=party, rules="2014")
    assert classic["xp"] == {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4400}


async def test_rate_encounter() -> None:
    goblins = [{"name": "goblin", "count": 4}]
    result = await call("rate_encounter", party_levels=[1, 1, 1, 1], creatures=goblins)
    assert result["creatures"] == [
        {
            "name": "Goblin",
            "source": "SRD",
            "srd": True,
            "cr": "1/4",
            "xp": 50,
            "count": 4,
        }
    ]
    assert (result["total_xp"], result["adjusted_xp"]) == (200, 200)
    assert result["difficulty"] == "low"

    classic = await call(
        "rate_encounter", party_levels=[1, 1, 1, 1], creatures=goblins, rules="2014"
    )
    assert (classic["multiplier"], classic["adjusted_xp"]) == (2.0, 400)
    assert classic["difficulty"] == "deadly"


async def test_rate_encounter_keeps_to_the_srd() -> None:
    sneak = [{"name": "Goblin Sneak"}]
    with pytest.raises(ToolError, match="not in the SRD; pass srd_only=false"):
        await call("rate_encounter", party_levels=[3], creatures=sneak)
    result = await call(
        "rate_encounter", party_levels=[3], creatures=sneak, srd_only=False
    )
    assert result["creatures"][0]["source"] == "HB"
    with pytest.raises(ToolError, match="Did you mean: Goblin"):
        await call("rate_encounter", party_levels=[3], creatures=[{"name": "Goblim"}])


async def test_suggest_creatures() -> None:
    party = [1, 1, 1, 1]
    five = await call(
        "suggest_creatures", party_levels=party, difficulty="moderate", count=5
    )
    assert five["xp_each"] == [41, 60]
    assert names(five) == ["Acolyte", "Goblin"]
    forest = await call(
        "suggest_creatures",
        party_levels=party,
        difficulty="moderate",
        count=5,
        environment="forest",
        srd_only=False,
    )
    assert names(forest) == ["Goblin", "Goblin Sneak"]
    assert forest["results"][0]["environment"] == [
        "underdark",
        "grassland",
        "forest",
        "hill",
    ]

    dragons = await call(
        "suggest_creatures",
        party_levels=[8, 8, 8, 8],
        difficulty="moderate",
        creature_type="dragon",
    )
    assert names(dragons) == ["Young Red Dragon"]
    assert dragons["results"][0]["xp"] == 5900


async def test_suggest_creatures_checks_the_rules() -> None:
    with pytest.raises(ToolError, match="2024 difficulties are low, moderate, high"):
        await call("suggest_creatures", party_levels=[3], difficulty="deadly")
