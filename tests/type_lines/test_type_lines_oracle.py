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
