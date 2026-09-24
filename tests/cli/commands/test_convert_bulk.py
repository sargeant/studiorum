"""convert bulk --type mixed tells books from adventures by the loaded books' ids."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.models.content import ContentType
from studiorum.core.resolvers.content_resolver import ContentResolver

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_mixed_resolves_book_ids_as_books(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    requested: list[tuple[str, ContentType]] = []

    def resolve_multiple(self, queries):
        requested.extend(queries)
        return []

    monkeypatch.setattr(ContentResolver, "resolve_multiple", resolve_multiple)

    result = CliRunner().invoke(
        app,
        [
            "convert", "bulk", "TEST-BOOK", "test-adventure",
            "--type", "mixed", "--output-dir", str(tmp_path),
        ],
    )  # fmt: skip

    assert requested == [
        ("TEST-BOOK", ContentType.BOOK),
        ("test-adventure", ContentType.ADVENTURE),
    ], result.output
