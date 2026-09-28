"""Class tables match what 5etools' class page shows, over the full data.

Runs progression.mjs, which loads 5etools' js/ under Node. Needs Node and a
5etools checkout (with js/) at $STUDIORUM_5ETOOLS_DIR or ~/Code/5etools-src;
run with `make test-full-data`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import orjson
import pytest

from studiorum.data.catalogue import Catalogue
from studiorum.data.class_entries import class_progression
from studiorum.data.loaders.data_dir import DataDir, DataSet
from studiorum.data.models.content import ContentType
from studiorum.mcp.markdown import strip_tags
from studiorum.mcp.tools.progression import cell_text

FIVETOOLS = Path(
    os.environ.get("STUDIORUM_5ETOOLS_DIR", Path.home() / "Code/5etools-src")
)
ORACLE = Path(__file__).with_name("progression.mjs")

pytestmark = [
    pytest.mark.requires_data,
    pytest.mark.skipif(
        os.environ.get("STUDIORUM_TEST_FULL_DATA", "").lower()
        not in ("1", "true", "yes"),
        reason="Needs the full data set; run make test-full-data",
    ),
    pytest.mark.skipif(shutil.which("node") is None, reason="Needs Node"),
    pytest.mark.skipif(
        not (FIVETOOLS / "js/utils.js").exists(),
        reason="Needs a 5etools checkout with js/",
    ),
]


@pytest.fixture(scope="module")
def oracle() -> list[dict[str, Any]]:
    result = subprocess.run(
        ["node", str(ORACLE), str(FIVETOOLS)],
        capture_output=True,
        check=True,
        timeout=300,
    )
    return orjson.loads(result.stdout)


@pytest.fixture(scope="module")
def catalogue() -> Catalogue:
    loaded = Catalogue(DataSet((DataDir(FIVETOOLS / "data"),)))
    loaded.load_all_data()
    return loaded


def _raw(content: Any) -> dict[str, Any]:
    raw: dict[str, Any] = content.model_dump(by_alias=True, exclude_none=True)
    return raw


def test_every_class_table_matches_5etools(
    oracle: list[dict[str, Any]], catalogue: Catalogue
) -> None:
    different = []
    for case in oracle:
        cls = catalogue.find(ContentType.CLASS, case["name"], case["source"])
        assert cls is not None, case["name"]
        sub = None
        if case["subclass"]:
            wanted = case["subclass"]
            sub = catalogue.find_uid(
                ContentType.SUBCLASS,
                f"{wanted['shortName']}|{case['name']}|{case['source']}|{wanted['source']}",
            )
            assert sub is not None, wanted
        progression = class_progression(_raw(cls), _raw(sub) if sub else None)
        ours = {
            "labels": [strip_tags(c.label) for c in progression.columns],
            "levels": [
                {
                    "level": row.level,
                    "pb": row.proficiency_bonus,
                    "cells": [cell_text(cell) for cell in row.cells],
                }
                for row in progression.levels
            ],
        }
        theirs = {"labels": case["labels"], "levels": case["levels"]}
        if ours != theirs:
            different.append((case["name"], case["source"], case["subclass"]))
    assert len(oracle) > 30
    assert not different, f"{len(different)} of {len(oracle)} differ: {different}"
