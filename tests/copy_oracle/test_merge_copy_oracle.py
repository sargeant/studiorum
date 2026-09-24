"""merge_copy matches 5etools' own _copy resolution over the full data set.

Runs merge_copy.mjs, which loads 5etools' js/ under Node, on the same files
and compares every copied entity. Needs Node and a 5etools checkout (with
js/) at $STUDIORUM_5ETOOLS_DIR or ~/Code/5etools-src; run with
`make test-full-data`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import orjson
import pytest

from studiorum.core.loaders.merge_copy import resolve_copies

FIVETOOLS = Path(
    os.environ.get("STUDIORUM_5ETOOLS_DIR", Path.home() / "Code/5etools-src")
)
ORACLE = Path(__file__).with_name("merge_copy.mjs")

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


def _files() -> list[Path]:
    data = FIVETOOLS / "data"
    return sorted(
        p
        for p in data.rglob("*.json")
        if not {"adventure", "book", "generated"} & set(p.relative_to(data).parts[:-1])
        and "foundry" not in p.name
    )


def test_every_copy_matches_5etools() -> None:
    files = _files()
    request = json.dumps({"files": [str(f) for f in files]})
    result = subprocess.run(
        ["node", str(ORACLE), str(FIVETOOLS)],
        input=request,
        capture_output=True,
        text=True,
        check=True,
    )
    expected = json.loads(result.stdout)

    by_prop: dict[str, list[dict]] = {}
    for f in files:
        data = orjson.loads(f.read_bytes())
        if not isinstance(data, dict):
            continue
        for prop, entities in data.items():
            if prop != "_meta" and isinstance(entities, list):
                by_prop.setdefault(prop, []).extend(
                    e for e in entities if isinstance(e, dict)
                )
    template_file = FIVETOOLS / "data/bestiary/template.json"
    templates = {"monster": orjson.loads(template_file.read_bytes())["monsterTemplate"]}
    resolve_copies(by_prop, templates)

    mismatches = []
    for row in expected:
        ent = by_prop[row["prop"]][row["index"]]
        if "error" in row:
            if "_copy" not in ent:
                mismatches.append(
                    (row["prop"], ent.get("name"), "5etools failed: " + row["error"])
                )
        elif orjson.dumps(ent, option=orjson.OPT_SORT_KEYS) != orjson.dumps(
            row["entity"], option=orjson.OPT_SORT_KEYS
        ):
            mismatches.append((row["prop"], ent.get("name"), "differs"))
    assert len(expected) > 1000
    assert mismatches == []
