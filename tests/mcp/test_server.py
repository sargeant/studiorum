"""Every tool, called through FastMCP's in-memory client.

Each Client runs the server lifespan, so each call is a cold start.
"""

from __future__ import annotations

from typing import Any, get_args

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from studiorum.data.models.content import ContentType
from studiorum.mcp.errors import suggestions
from studiorum.mcp.server import mcp
from studiorum.mcp.tools.lookup import EntryType
from studiorum.mcp.tools.progression import full_uid

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
        "search_rules",
        "search_content",
        "get_content",
        "get_contents",
        "list_publications",
        "get_class_progression",
        "calculate_encounter_budget",
        "rate_encounter",
        "suggest_creatures",
        "get_table_of_contents",
        "read_section",
        "search_publication",
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
    assert (result["total"], result["next_offset"]) == (3, 1)
    assert len(result["results"]) == 1
    last = await call("search_spells", srd_only=False, limit=1, offset=2)
    assert (names(last), last["next_offset"]) == (["Hellfire Orb"], None)


@pytest.mark.asyncio
async def test_searches_include_text(monkeypatch: pytest.MonkeyPatch) -> None:
    fireball = await call("get_content", content_type="spell", name="Fireball")
    spells = await call("search_spells", query="fire", include_text=True)
    assert spells["results"][0]["text"] == fireball["text"]
    # Without include_text, no text field at all
    assert "text" not in (await call("search_spells", query="fire"))["results"][0]
    for tool in ("search_creatures", "search_items"):
        assert all("text" not in r for r in (await call(tool))["results"])
    plain = await call("search_content", content_type="class", query="wiz")
    assert "text" not in plain["results"][0]
    goblin = await call("get_content", content_type="creature", name="Goblin")
    creatures = await call("search_creatures", query="goblin", include_text=True)
    assert creatures["results"][0]["text"] == goblin["text"]
    items = await call("search_items", query="amulet", include_text=True)
    assert items["results"][0]["text"].startswith("# Amulet of Health")
    wizard = await call("get_content", content_type="class", name="Wizard")
    classes = await call(
        "search_content", content_type="class", query="wiz", include_text=True
    )
    # A class lists its subclasses, as get_content does
    assert classes["results"][0]["text"] == wizard["text"]

    # Text stops a page at the size cap, though a page always has one result
    monkeypatch.setattr("studiorum.mcp.tools.search.PAGE_CHARS", 1)
    capped = await call("search_spells", srd_only=False, include_text=True)
    assert (len(capped["results"]), capped["total"], capped["next_offset"]) == (
        1,
        3,
        1,
    )
    rest = await call("search_spells", srd_only=False, include_text=True, offset=2)
    assert (names(rest), rest["next_offset"]) == (["Hellfire Orb"], None)


@pytest.mark.asyncio
async def test_search_creatures_filters() -> None:
    assert names(await call("search_creatures", query="goblin")) == ["Goblin"]
    assert names(await call("search_creatures", query="goblin", srd_only=False)) == [
        "Goblin",
        "Goblin Minion",
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
async def test_search_creatures_with_a_type_to_choose_and_no_cr() -> None:
    familiar = await call(
        "search_creatures", query="familiar", creature_type="fey", srd_only=False
    )
    assert [(r["name"], r["type"], r["cr"]) for r in familiar["results"]] == [
        ("Battle Familiar", "celestial | fey | fiend", None)
    ]
    fiends = await call("search_creatures", creature_type="fiend", srd_only=False)
    assert names(fiends) == ["Battle Familiar"]
    assert (
        names(await call("search_creatures", creature_type="undead", srd_only=False))
        == []
    )


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
    # Keys with nothing to say are left out rather than sent as null
    assert "text" not in result
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
    # A part of the name suggests the names that contain it
    with pytest.raises(ToolError, match="Did you mean: Young Red Dragon"):
        await call("get_content", content_type="creature", name="red drag")


@pytest.mark.asyncio
async def test_get_content_suggests_names_from_the_source() -> None:
    with pytest.raises(
        ToolError,
        match=r"No creature named 'Goblin' in HB\. Did you mean: Goblin Sneak, Goblin Minion\?$",
    ):
        await call("get_content", content_type="creature", name="Goblin", source="HB")
    # Every source when nothing in the source is close
    with pytest.raises(ToolError, match="in HB. Did you mean: Young Red Dragon"):
        await call("get_content", content_type="creature", name="Dragon", source="HB")


def test_suggestions_put_whole_words_first() -> None:
    names = ["Searing Smite", "Festering Blast", "Lightning Ring", "Ring of Frost"]
    assert suggestions("Ring", names) == [
        "Ring of Frost",
        "Lightning Ring",
        "Searing Smite",
        "Festering Blast",
    ]


@pytest.mark.asyncio
async def test_get_contents_returns_several(monkeypatch: pytest.MonkeyPatch) -> None:
    items = [
        {"content_type": "creature", "name": "Goblin"},
        {"content_type": "spell", "name": "Fireball"},
        {"content_type": "spell", "name": "Hellfire Orb"},
        {"content_type": "spell", "name": "Nothing"},
        {"content_type": "item", "name": "Amulet of Health"},
        {"content_type": "spell", "name": "fireball"},
    ]
    result = await call("get_contents", items=items)
    assert [e["name"] for e in result["entries"]] == [
        "Goblin",
        "Fireball",
        "Amulet of Health",
    ]
    fireball = await call(
        "get_content", content_type="spell", name="Fireball", include_references=False
    )
    assert result["entries"][1] == fireball
    assert [(m["index"], m["name"], m["error"][:20]) for m in result["not_found"]] == [
        (2, "Hellfire Orb", "Hellfire Orb (HB) is"),
        (3, "Nothing", "No spell named 'Noth"),
    ]
    linked = await call("get_contents", items=items[:1], include_references=True)
    assert "references" in linked["entries"][0]
    assert result["next_offset"] is None

    # A size cap stops the batch; next_offset resumes it
    monkeypatch.setattr("studiorum.mcp.tools.lookup.PAGE_CHARS", 1)
    first = await call("get_contents", items=items)
    assert ([e["name"] for e in first["entries"]], first["next_offset"]) == (
        ["Goblin"],
        1,
    )
    rest = await call("get_contents", items=items, offset=4, format="json")
    assert rest["entries"][0]["data"]["name"] == "Amulet of Health"
    with pytest.raises(ToolError):
        await call("get_contents", items=[items[0]] * 21)


@pytest.mark.asyncio
async def test_list_publications() -> None:
    # Newest first
    result = await call("list_publications")
    assert result["publications"][0]["source"] == "TB"
    assert [(p["id"], p["kind"]) for p in result["publications"]] == [
        ("TB-ST", "adventure"),
        ("TB", "book"),
        ("TA", "adventure"),
    ]
    books = await call("list_publications", kind="book")
    assert [p["name"] for p in books["publications"]] == ["Test Book"]


@pytest.mark.asyncio
async def test_list_publications_filters_sorts_and_pages() -> None:
    def ids(result: dict[str, Any]) -> list[str]:
        return [p["id"] for p in result["publications"]]

    assert ids(await call("list_publications", query="book")) == ["TB-ST", "TB"]
    assert ids(await call("list_publications", query="ta")) == ["TA"]
    assert ids(await call("list_publications", published_after="2020")) == [
        "TB-ST",
        "TB",
    ]
    assert ids(await call("list_publications", published_after="2020-06-01")) == [
        "TB-ST"
    ]
    newest = await call("list_publications", limit=2, offset=0)
    assert (newest["total"], ids(newest), newest["next_offset"]) == (
        3,
        ["TB-ST", "TB"],
        2,
    )
    assert ids(await call("list_publications", offset=2)) == ["TA"]
    oldest = await call("list_publications", newest_first=False, limit=2)
    assert (ids(oldest), oldest["next_offset"]) == (["TA", "TB"], 2)
    with pytest.raises(ToolError):
        await call("list_publications", published_after="last year")


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


@pytest.mark.asyncio
async def test_search_rules_matches_names_then_text() -> None:
    # A rule with a part named the query comes before other name matches
    result = await call("search_rules", query="grapple")
    assert [(r["name"], r["type"]) for r in result["results"]] == [
        ("Unarmed Strike", "variantrule"),
        ("Grappled", "condition"),
    ]
    assert result["results"][0]["snippet"].startswith(
        "A blow to damage, grapple, or shove a target."
    )
    shove = await call("search_rules", query="shove")
    assert [r["name"] for r in shove["results"]] == ["Unarmed Strike"]
    speed = await call("search_rules", query="speed", rule_type="condition")
    assert speed["results"][0]["snippet"] == "Your Speed is 0."


@pytest.mark.asyncio
async def test_searches_say_what_the_srd_filter_hid() -> None:
    result = await call("search_spells", query="orb")
    assert (result["total"], result["hidden_by_srd"]) == (0, 1)
    assert (await call("search_spells", query="orb", srd_only=False))[
        "hidden_by_srd"
    ] == 0


@pytest.mark.asyncio
async def test_get_content_lists_references() -> None:
    goblin = await call("get_content", content_type="creature", name="Goblin")
    assert {(r["type"], r["name"]) for r in goblin["references"]} >= {
        ("item", "leather armor"),
        ("item", "shield"),
    }


@pytest.mark.asyncio
async def test_feats_keep_their_prerequisites() -> None:
    grappler = await call("get_content", content_type="feat", name="Grappler")
    assert "**Prerequisite** Strength 13" in grappler["text"]
    raw = await call("get_content", content_type="feat", name="Grappler", format="json")
    assert raw["data"]["prerequisite"] == [{"ability": [{"str": 13}]}]


@pytest.mark.asyncio
async def test_languages_can_be_found_and_read() -> None:
    found = await call("search_content", content_type="language", query="elv")
    assert [r["name"] for r in found["results"]] == ["Elvish"]
    elvish = await call("get_content", content_type="language", name="Elvish")
    assert "Elvish" in elvish["text"]


@pytest.mark.asyncio
async def test_bad_filters_say_what_is_wrong() -> None:
    with pytest.raises(ToolError, match=r"cr_min \(5\) is more than cr_max \(1\)"):
        await call("search_creatures", cr_min=5, cr_max=1)
    with pytest.raises(ToolError, match="No creature type 'robot'. Types: aberration"):
        await call("search_creatures", creature_type="robot")
    with pytest.raises(ToolError, match="No class named 'pilot'. Classes: Wizard"):
        await call("search_spells", spell_class="pilot")


@pytest.mark.asyncio
async def test_searches_page_and_report_the_srd_mode() -> None:
    first = await call("search_creatures", srd_only=False, limit=2)
    second = await call("search_creatures", srd_only=False, limit=2, offset=2)
    assert first["total"] == second["total"] == 6
    assert names(first) + names(second) == [
        "Acolyte",
        "Battle Familiar",
        "Goblin",
        "Goblin Minion",
    ]
    assert (first["srd_only"], (await call("search_spells"))["srd_only"]) == (
        False,
        True,
    )


@pytest.mark.asyncio
async def test_search_content_finds_any_type_by_name() -> None:
    feats = await call("search_content", content_type="feat", query="grap")
    assert names(feats) == ["Grappler"]
    features = await call("search_content", content_type="classFeature", query="arcane")
    assert "Arcane Recovery" in names(features)
    nothing = await call("search_content", content_type="deity", query="annam")
    assert (nothing["total"], nothing["hidden_by_srd"]) == (0, 0)


@pytest.mark.asyncio
async def test_search_content_gives_uids_where_names_repeat() -> None:
    result = await call(
        "search_content", content_type="classFeature", query="arcane recovery"
    )
    first = result["results"][0]
    assert (first["detail"], first["uid"]) == (
        "Level 1 Wizard",
        "Arcane Recovery|Wizard|PHB|1|SRD",
    )
    feature = await call("get_content", content_type="classFeature", name=first["uid"])
    assert feature["name"] == "Arcane Recovery"


@pytest.mark.asyncio
async def test_get_class_progression() -> None:
    wizard = await call("get_class_progression", class_name="wizard")
    assert (wizard["name"], len(wizard["levels"])) == ("Wizard", 20)
    assert wizard["columns"][-9:] == [
        "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"
    ]  # fmt: skip
    first = wizard["levels"][0]
    assert (first["level"], first["proficiency_bonus"]) == (1, 2)
    assert first["cells"][-9:-7] == ["2", "\u2014"]
    assert "subclass_features" not in first
    assert "Arcane Recovery" in [f["name"] for f in first["features"]]

    one = await call("get_class_progression", class_name="Wizard", level=17)
    assert [r["level"] for r in one["levels"]] == [17]
    assert one["levels"][0]["proficiency_bonus"] == 6
    assert one["levels"][0]["cells"][-9:] == [
        "4",
        "3",
        "3",
        "3",
        "2",
        "1",
        "1",
        "1",
        "1",
    ]
    # A feature's uid reads it in full
    uid = first["features"][0]["uid"]
    feature = await call("get_content", content_type="classFeature", name=uid)
    assert feature["name"] == first["features"][0]["name"]


@pytest.mark.asyncio
async def test_get_class_progression_with_a_subclass() -> None:
    evoker = await call(
        "get_class_progression", class_name="Wizard", subclass="evocation", level=2
    )
    assert (evoker["subclass"], evoker["subclass_source"]) == (
        "School of Evocation",
        "SRD",
    )
    assert [f["name"] for f in evoker["levels"][0]["subclass_features"]] == [
        "School of Evocation"
    ]
    with pytest.raises(ToolError, match="No Wizard subclass named 'Nope'"):
        await call("get_class_progression", class_name="Wizard", subclass="Nope")

    only = await call(
        "get_class_progression",
        class_name="Wizard",
        subclass="evocation",
        subclass_only=True,
    )
    assert only["columns"] == []
    assert [r["level"] for r in only["levels"]] == [2, 6, 10, 14]
    assert only["levels"][0]["cells"] == []
    assert "features" not in only["levels"][0]
    with pytest.raises(ToolError, match="subclass_only needs a subclass"):
        await call("get_class_progression", class_name="Wizard", subclass_only=True)


@pytest.mark.parametrize(
    ("kind", "uid", "full"),
    [
        ("classFeature", "Rage|Barbarian||1", "Rage|Barbarian|PHB|1|PHB"),
        (
            "classFeature",
            "Spell Mastery|Wizard|XPHB|18",
            "Spell Mastery|Wizard|XPHB|18|XPHB",
        ),
        (
            "subclassFeature",
            "Evoker|Wizard|XPHB|Evoker|XPHB|3",
            "Evoker|Wizard|XPHB|Evoker|XPHB|3|XPHB",
        ),
        (
            "subclassFeature",
            "Evoker|Wizard||Evoker||2",
            "Evoker|Wizard|PHB|Evoker|PHB|2|PHB",
        ),
    ],
)
def test_full_uid(kind: str, uid: str, full: str) -> None:
    assert full_uid(kind, uid) == full


@pytest.mark.asyncio
async def test_unknown_parameters_list_the_ones_a_tool_takes() -> None:
    with pytest.raises(
        ToolError,
        match=r"^list_publications has no parameter 'name_contains'\. "
        r"Its parameters: kind, query, published_after, newest_first, limit, offset\.$",
    ):
        await call("list_publications", name_contains="tomb")
    with pytest.raises(ToolError, match="has no parameter 'lvl' or 'name'"):
        await call("search_spells", lvl=1, name="x")


@pytest.mark.asyncio
async def test_bad_arguments_say_what_is_wrong_in_a_line_each() -> None:
    with pytest.raises(ToolError) as caught:
        await call("search_spells", limit=101, offset=-1)
    assert str(caught.value) == (
        "Bad arguments to search_spells. "
        "limit: Input should be less than or equal to 100. "
        "offset: Input should be greater than or equal to 0."
    )
    with pytest.raises(
        ToolError, match=r"^Bad arguments to search_content\. query: Required\.$"
    ):
        await call("search_content", content_type="feat")


@pytest.mark.asyncio
async def test_results_leave_out_empty_keys() -> None:
    grappler = (await call("search_content", content_type="feat", query="grap"))[
        "results"
    ][0]
    assert set(grappler) == {"name", "source", "srd"}
    goblin = await call("get_content", content_type="creature", name="Goblin")
    assert "data" not in goblin
    assert all(set(r) == {"type", "name", "source"} for r in goblin["references"])


@pytest.mark.asyncio
async def test_queries_match_without_accents() -> None:
    assert names(await call("search_creatures", query="GÖB")) == ["Goblin"]
    goblin = await call("get_content", content_type="creature", name="Göblin")
    assert goblin["name"] == "Goblin"


@pytest.mark.asyncio
async def test_include_text_tools_describe_the_size_cap() -> None:
    async with Client(mcp) as client:
        tools = {t.name: t.description or "" for t in await client.list_tools()}
    for name in ("search_spells", "search_creatures", "search_items", "search_content"):
        assert "fewer results than limit; next_offset" in tools[name], name
