#!/usr/bin/env python3
"""Extract SRD content from 5e.tools data."""

import json
import os
from pathlib import Path
from typing import Any


def filter_srd_content(data: Any) -> Any:
    """Filter JSON data to only include SRD content."""
    # Handle case where root is a list
    if isinstance(data, list):
        srd_items = [
            item for item in data if isinstance(item, dict) and item.get("srd") is True
        ]
        return srd_items if srd_items else None

    # Handle case where root is not a dict
    if not isinstance(data, dict):
        return None

    filtered = {"_meta": data.get("_meta", {})}

    for key, value in data.items():
        if key.startswith("_"):
            continue

        if isinstance(value, list):
            srd_items = [
                item
                for item in value
                if isinstance(item, dict) and item.get("srd") is True
            ]
            if srd_items:
                filtered[key] = srd_items

    return filtered


def process_json_file(source_path: Path, target_path: Path) -> bool:
    """Process a single JSON file, return True if SRD content found."""
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"✗ Error reading {source_path}: {e}")
        return False

    filtered = filter_srd_content(data)

    # Check if we have any content
    has_content = False
    if isinstance(filtered, list):
        has_content = len(filtered) > 0
    elif isinstance(filtered, dict):
        has_content = any(k for k in filtered.keys() if not k.startswith("_"))

    if has_content:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        return True

    return False


def main():
    source_dir = Path("5etools-src/data")
    target_dir = Path("srd-data")

    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        return

    json_files = list(source_dir.rglob("*.json"))
    processed = 0
    total_files = len(json_files)

    print(f"Found {total_files} JSON files to process...")

    for i, source_path in enumerate(json_files, 1):
        relative_path = source_path.relative_to(source_dir)
        target_path = target_dir / relative_path

        if process_json_file(source_path, target_path):
            print(f"✓ {relative_path}")
            processed += 1
        else:
            print(f"- {relative_path} (no SRD content)")

        # Progress indicator for large datasets
        if i % 50 == 0:
            print(f"Progress: {i}/{total_files} files processed")

    print(
        f"\nCompleted! Processed {processed} files with SRD content out of {total_files} total files"
    )
    print(f"SRD content extracted to: {target_dir}")


if __name__ == "__main__":
    main()
