#!/usr/bin/env python3
"""
Debug the specific book loader to see why it returns 0 items.
"""


def debug_book_loader_detailed():
    """Debug the book loader in detail"""
    print("=== Debugging Book Loader ===")

    import logging
    import os
    from pathlib import Path

    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("dnd5e.core.loaders")
    logger.setLevel(logging.DEBUG)

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.models.content import ContentType

    omnidexer = Omnidexer()

    # Check if book loader is registered
    book_type = ContentType("book")
    print(f"Book loader registered: {book_type in omnidexer._loaders}")

    if book_type in omnidexer._loaders:
        loader = omnidexer._loaders[book_type]
        print(f"Book loader type: {type(loader)}")

        # Test the loader directly on our test file
        test_book_path = Path("test-data/books.json")
        print(f"Test file exists: {test_book_path.exists()}")

        if test_book_path.exists():
            print("\n--- Testing loader directly ---")
            try:
                result = loader.load(test_book_path)
                print(f"Loader returned: {len(result)} items")

                if result:
                    for item in result:
                        print(f"  - {item.name} (type: {type(item)})")
                else:
                    print("No items returned by loader - investigating why...")

                    # Let's manually inspect what the loader sees
                    print("\n--- Manual loader investigation ---")

                    # Check if it's a JsonDataLoader
                    if hasattr(loader, "load_from_data"):
                        import json

                        with open(test_book_path, "r") as f:
                            raw_data = json.load(f)

                        print(f"Raw JSON keys: {list(raw_data.keys())}")
                        print(f"Book array length: {len(raw_data.get('book', []))}")

                        if raw_data.get("book"):
                            print(f"First book: {raw_data['book'][0]}")

                        # Test the loader's internal methods
                        try:
                            result2 = loader.load_from_data(raw_data, test_book_path)
                            print(f"load_from_data returned: {len(result2)} items")
                        except Exception as e:
                            print(f"load_from_data failed: {e}")
                            import traceback

                            traceback.print_exc()

            except Exception as e:
                print(f"Loader failed: {e}")
                import traceback

                traceback.print_exc()
    else:
        print("No book loader registered!")
        print(f"Available loaders: {list(omnidexer._loaders.keys())}")


if __name__ == "__main__":
    debug_book_loader_detailed()
