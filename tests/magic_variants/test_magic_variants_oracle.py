"""magic_variants matches 5etools' own specific variants over the full data set.

Runs variants.mjs, which loads 5etools' js/ under Node. Needs Node and a
5etools checkout (with js/) at $STUDIORUM_5ETOOLS_DIR or ~/Code/5etools-src;
run with `make test-full-data`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import orjson
import pytest

from studiorum.core.loaders.magic_variants import expand
from studiorum.core.loaders.merge_copy import resolve_copies

FIVETOOLS = Path(
    os.environ.get("STUDIORUM_5ETOOLS_DIR", Path.home() / "Code/5etools-src")
)
ORACLE = Path(__file__).with_name("variants.mjs")

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


def _comparable(item: dict[str, Any]) -> dict[str, Any]:
    """The item without the base-item note, which 5etools wraps and names in full."""
    entries = [
        e
        for e in item.get("entries", [])
        if not (isinstance(e, dict) and e.get("type") == "wrapper")
        and not (isinstance(e, str) and e.startswith("{@note The {@item"))
    ]
    out = {k: v for k, v in item.items() if k != "entries"}
    return out | {"entries": entries} if entries else out


def _key(item: dict[str, Any]) -> tuple[str, str, str]:
    return item["name"], item["source"], item.get("baseItem", "")


def test_every_specific_variant_matches_5etools() -> None:
    result = subprocess.run(
        ["node", str(ORACLE), str(FIVETOOLS)],
        capture_output=True,
        check=True,
        timeout=300,
    )
    oracle = {_key(i): _comparable(i) for i in orjson.loads(result.stdout)}

    raw: dict[str, list[Any]] = defaultdict(list)
    for name in ("items-base.json", "magicvariants.json"):
        for prop, entities in orjson.loads(
            (FIVETOOLS / "data" / name).read_bytes()
        ).items():
            if isinstance(entities, list):
                raw[prop] += entities
    resolve_copies(raw, {})
    generics = [g for g in raw["magicvariant"] if "_copy" not in g]
    ours = {_key(i): _comparable(i) for i in expand(raw["baseitem"], generics)}

    assert ours.keys() == oracle.keys()
    different = [k for k in ours if ours[k] != oracle[k]]
    assert not different, f"{len(different)} differ, e.g. {different[:3]}"
