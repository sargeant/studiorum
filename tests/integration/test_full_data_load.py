"""Loading the full 5etools data set: repeatable, and variants stay themselves.

Needs a 5etools checkout at $STUDIORUM_5ETOOLS_DIR (default ~/Code/5etools-src);
run with `make test-full-data`. Fennor's snapshot depends on the checkout's
version, so refresh it with --snapshot-update after pulling 5etools.
"""

from __future__ import annotations

import os
from pathlib import Path

import orjson
import pytest
from syrupy.assertion import SnapshotAssertion

from studiorum.core.loaders.data_dir import DataDir, DataSet
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType

FIVETOOLS = Path(
    os.environ.get("STUDIORUM_5ETOOLS_DIR", Path.home() / "Code/5etools-src")
)

pytestmark = [
    pytest.mark.requires_data,
    pytest.mark.skipif(
        os.environ.get("STUDIORUM_TEST_FULL_DATA", "").lower()
        not in ("1", "true", "yes"),
        reason="Needs the full data set; run make test-full-data",
    ),
    pytest.mark.skipif(
        not (FIVETOOLS / "data").is_dir(), reason="Needs a 5etools checkout"
    ),
]


def _load() -> Omnidexer:
    omnidexer = Omnidexer(DataSet((DataDir(FIVETOOLS / "data"),)))
    omnidexer.load_all_data()
    return omnidexer


def _dump(omnidexer: Omnidexer) -> list[bytes]:
    return sorted(
        orjson.dumps(
            [ct.value, item.name, item.model_dump(mode="json")],
            option=orjson.OPT_SORT_KEYS,
        )
        for ct in ContentType
        for item in omnidexer.get_all_by_type(ct)
    )


@pytest.fixture(scope="module")
def loaded() -> Omnidexer:
    return _load()


def test_two_fresh_loads_are_equal(loaded: Omnidexer) -> None:
    again = _load()

    assert _dump(again) == _dump(loaded)
    # Differed between processes before _copy was resolved on raw JSON
    exalted = loaded.find(ContentType.ITEM, "Verminshroud (Exalted)")
    assert exalted is not None
    assert (
        exalted.model_dump()
        == again.find(ContentType.ITEM, "Verminshroud (Exalted)").model_dump()
    )  # type: ignore[union-attr]


def test_a_named_npc_keeps_its_own_cr_and_actions(
    loaded: Omnidexer, snapshot: SnapshotAssertion
) -> None:
    # Fennor copies the Berserker (CR 2, Greataxe) with his own CR and actions
    fennor = loaded.find(ContentType.CREATURE, "Fennor", "PotA")

    assert fennor is not None
    assert fennor.cr == "3"  # type: ignore[attr-defined]
    assert [a.name for a in fennor.action or []] == ["Multiattack", "Greatsword"]  # type: ignore[attr-defined]
    assert fennor.model_dump(mode="json") == snapshot
