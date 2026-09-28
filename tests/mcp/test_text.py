from __future__ import annotations

import pytest

from studiorum.mcp.text import fold


@pytest.mark.parametrize(
    ("text", "folded"),
    [
        ("Bigby's Hand", "bigby's hand"),
        ("Bigby’s Hand", "bigby's hand"),
        ("‘Quoted’ “twice”", "'quoted' \"twice\""),
        ("Deep Rothé", "deep rothe"),
        ("Môrgæn", "morgæn"),
        ("Carpet of Flying, 3 ft. × 5 ft.", "carpet of flying, 3 ft. × 5 ft."),
    ],
)
def test_fold(text: str, folded: str) -> None:
    assert fold(text) == folded
