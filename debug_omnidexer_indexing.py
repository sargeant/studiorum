#!/usr/bin/env python3
"""
Debug the omnidexer indexing process to see where books are lost.
"""


def debug_indexing_process():
    """Debug the omnidexer indexing process"""
    print("=== Debugging Omnidexer Indexing Process ===")

    import logging
    import os
    from pathlib import Path

    # Enable debug logging for the omnidexer specifically
    logging.basicConfig(level=logging.INFO)
    omnidexer_logger = logging.getLogger("dnd5e.core.loaders.omnidexer")
    omnidexer_logger.setLevel(logging.DEBUG)

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.models.content import ContentType

    omnidexer = Omnidexer()

    # Get the exact same parameters the omnidexer would use
    book_type = ContentType("book")
    test_path = Path("test-data/books.json")

    print(f"Testing with book_type: {book_type}")
    print(f"Testing with path: {test_path}")

    # Call the exact same method the omnidexer calls
    print("\n--- Calling _load_content_type directly ---")

    # Monkey patch the _add_to_index method to debug what happens
    original_add_to_index = omnidexer._add_to_index

    def debug_add_to_index(content, content_type):
        print(f"  _add_to_index called with: {content.name} (type: {type(content)})")
        try:
            original_add_to_index(content, content_type)
            print(f"  Successfully indexed: {content.name}")
        except Exception as e:
            print(f"  Failed to index {content.name}: {e}")
            import traceback

            traceback.print_exc()

    omnidexer._add_to_index = debug_add_to_index

    # Now call the method
    try:
        result = omnidexer._load_content_type(book_type, test_path)
        print(f"_load_content_type result: {result}")
    except Exception as e:
        print(f"_load_content_type failed: {e}")
        import traceback

        traceback.print_exc()

    # Check what's actually in the omnidexer
    print("\n--- Final omnidexer state ---")
    books = omnidexer.get_all_by_type("book")
    print(f"Books in omnidexer: {len(books)}")
    for book in books:
        print(f"  - {book.name}")


if __name__ == "__main__":
    debug_indexing_process()
