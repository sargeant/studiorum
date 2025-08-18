#!/usr/bin/env python3
"""
Detailed investigation of book loading in test environment.
"""


def debug_test_environment_loading():
    """Debug what happens during test environment loading"""
    print("=== Debugging Test Environment Loading ===")

    import logging
    import os

    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("dnd5e.core.loaders.omnidexer")
    logger.setLevel(logging.DEBUG)

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.loaders.omnidexer import Omnidexer

    omnidexer = Omnidexer()

    print("\n--- Loading all data ---")
    omnidexer.load_all_data()

    books = omnidexer.get_all_by_type("book")
    adventures = omnidexer.get_all_by_type("adventure")

    print(f"\nFinal result: Books={len(books)}, Adventures={len(adventures)}")

    # Check the raw data loading
    print("\n--- Testing direct JSON loader ---")
    from dnd5e.core.loaders.json_data_loader import JsonDataLoader
    from dnd5e.core.models.content_types import ContentType

    loader = JsonDataLoader()
    book_data = loader.load("test-data/books.json")
    print(f"Direct JSON loader result: {len(book_data)} books")

    if book_data:
        print(f"First book: {book_data[0].name}")

    # Check the content factory
    print("\n--- Testing content factory ---")
    from dnd5e.core.factories.content_factory import ContentFactory

    factory = ContentFactory()

    # Load raw JSON data
    import json

    with open("test-data/books.json", "r") as f:
        raw_data = json.load(f)

    book_items = raw_data.get("book", [])
    print(f"Raw JSON has {len(book_items)} book items")

    if book_items:
        created_book = factory.create_content(book_items[0], ContentType.BOOK)
        print(f"Factory created book: {created_book.name}")

    return len(books), len(adventures)


if __name__ == "__main__":
    try:
        books, adventures = debug_test_environment_loading()
        print(f"\nFinal: Books={books}, Adventures={adventures}")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback

        traceback.print_exc()
