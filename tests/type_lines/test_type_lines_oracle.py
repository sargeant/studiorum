"""Prerequisites and type lines match what 5etools shows, over the full data set.

Runs lines.mjs, which loads 5etools' js/ under Node. Needs Node and a 5etools
checkout (with js/) at $STUDIORUM_5ETOOLS_DIR or ~/Code/5etools-src; run with
`make test-full-data`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import orjson
import pytest

from studiorum.core.compact import compact_entries
from studiorum.core.loaders.data_dir import DataDir, DataSet
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content_models import PROP_TYPES
from studiorum.core.text.prerequisites import prerequisite_entry

FIVETOOLS = Path(
    os.environ.get("STUDIORUM_5ETOOLS_DIR", Path.home() / "Code/5etools-src")
)
ORACLE = Path(__file__).with_name("lines.mjs")

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
def oracle() -> dict[str, Any]:
    result = subprocess.run(
        ["node", str(ORACLE), str(FIVETOOLS)],
        capture_output=True,
        check=True,
        timeout=300,
    )
    return orjson.loads(result.stdout)


def test_every_prerequisite_matches_5etools(oracle: dict[str, Any]) -> None:
    cases = oracle["prerequisites"]
    different = [
        (case["text"], ours)
        for case in cases
        if (ours := prerequisite_entry(case["prerequisite"], style=case["style"]))
        != case["text"]
    ]
    assert cases
    assert not different, (
        f"{len(different)} of {len(cases)} differ, e.g. {different[:3]}"
    )


@pytest.fixture(scope="module")
def omnidexer() -> Omnidexer:
    loaded = Omnidexer(DataSet((DataDir(FIVETOOLS / "data"),)))
    loaded.load_all_data()
    return loaded


def _differences(
    oracle: dict[str, Any], omnidexer: Omnidexer, prop: str
) -> tuple[int, list[tuple[str, Any, Any]]]:
    content_type = PROP_TYPES[prop]
    cases = oracle["compact"][prop]
    different = []
    for case in cases:
        found = [
            f
            for f in omnidexer.find_all(content_type, case["name"])
            if f.source.abbreviation == case["source"]
        ]
        ours = [compact_entries(f, omnidexer) for f in found]
        if case["entries"] not in ours:
            different.append((case["name"], case["entries"], ours))
    return len(cases), different


@pytest.mark.parametrize("prop", ["trap", "hazard"])
def test_type_lines_match_5etools(
    oracle: dict[str, Any], omnidexer: Omnidexer, prop: str
) -> None:
    count, different = _differences(oracle, omnidexer, prop)
    assert count
    assert not different, f"{len(different)} of {count} differ, e.g. {different[:2]}"
