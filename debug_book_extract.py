#!/usr/bin/env python3
"""
Debug the book content extraction process step by step.
"""


def debug_book_content_extraction():
    """Debug book content extraction in detail"""
    print("=== Debugging Book Content Extraction ===")

    import json
    import os
    from pathlib import Path

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.loaders.json_loader import JsonDataLoader
    from dnd5e.core.models.content import ContentType

    # Create the exact same loader the omnidexer uses
    book_type = ContentType("book")
    loader = JsonDataLoader(book_type)

    # Test with our specific file
    test_path = Path("test-data/books.json")

    print(f"Testing file: {test_path}")
    print(f"File exists: {test_path.exists()}")

    # Load and inspect the raw data
    with open(test_path, "r") as f:
        raw_data = json.load(f)

    print(f"Raw data keys: {list(raw_data.keys())}")
    print(f"Book array length: {len(raw_data.get('book', []))}")

    # Test the metadata file detection
    is_metadata = loader._is_book_metadata_file(raw_data)
    print(f"Is book metadata file: {is_metadata}")

    # Test content extraction
    print("\n--- Testing _extract_content ---")
    extracted_content = loader._extract_content(raw_data, test_path)
    print(f"Extracted content length: {len(extracted_content)}")

    if extracted_content:
        for i, item in enumerate(extracted_content):
            print(f"  Item {i}: {item.get('name', 'no name')} (type: {type(item)})")

    # Test the full loader pipeline
    print("\n--- Testing full loader.load() ---")
    loaded_content = loader.load(test_path)
    print(f"Loaded content length: {len(loaded_content)}")

    if loaded_content:
        for i, item in enumerate(loaded_content):
            print(f"  Item {i}: {item.name} (type: {type(item)})")


if __name__ == "__main__":
    debug_book_content_extraction()
