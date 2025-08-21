#!/usr/bin/env python3
"""
Script to migrate all logging imports to use dnd5e.core.logging.get_logger
"""

from __future__ import annotations

import re
from pathlib import Path


def migrate_file(file_path: Path) -> bool:
    """Migrate a single file's logging imports."""
    try:
        content = file_path.read_text()
        original_content = content

        # Pattern 1: Replace `import logging`
        content = re.sub(
            r"^import logging$",
            "from dnd5e.core.logging import get_logger",
            content,
            flags=re.MULTILINE,
        )

        # Pattern 2: Replace `logger = logging.getLogger(__name__)`
        content = re.sub(
            r"^logger = logging\.getLogger\(__name__\)$",
            "logger = get_logger(__name__)",
            content,
            flags=re.MULTILINE,
        )

        # Pattern 3: Replace inline logging.getLogger() calls
        content = re.sub(r"logging\.getLogger\(", "get_logger(", content)

        # Pattern 4: Handle specific cases with local imports
        content = re.sub(
            r"(\s+)import logging\n(\s+)logger = logging\.getLogger\(__name__\)",
            r"\1from dnd5e.core.logging import get_logger\n\2logger = get_logger(__name__)",
            content,
            flags=re.MULTILINE,
        )

        # Pattern 5: Handle multi-line import blocks like:
        # import logging
        # import something_else
        # logger = logging.getLogger(__name__)
        content = re.sub(
            r"^(import logging)$",
            "from dnd5e.core.logging import get_logger",
            content,
            flags=re.MULTILINE,
        )

        if content != original_content:
            file_path.write_text(content)
            return True
        return False

    except Exception as e:
        print(f"Error migrating {file_path}: {e}")
        return False


def migrate_all_files() -> None:
    """Migrate all Python files in src/dnd5e/"""
    src_dir = Path("src/dnd5e")
    if not src_dir.exists():
        print("Error: src/dnd5e directory not found")
        return

    migrated_files: list[Path] = []
    for py_file in src_dir.rglob("*.py"):
        # Skip the logging module itself
        if "core/logging" in str(py_file):
            continue

        if migrate_file(py_file):
            migrated_files.append(py_file)

    print(f"Migrated {len(migrated_files)} files:")
    for file_path in migrated_files:
        print(f"  - {file_path}")


if __name__ == "__main__":
    migrate_all_files()
