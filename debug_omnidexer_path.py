#!/usr/bin/env python3
"""
Debug what path the omnidexer is actually using for book loading.
"""


def debug_omnidexer_paths():
    """Debug the paths omnidexer uses for loading"""
    print("=== Debugging Omnidexer Paths ===")

    import os

    os.environ["DND5E_CONFIG_FILE"] = "test-config.yaml"

    from tests.test_helpers import reset_test_environment

    reset_test_environment()

    from dnd5e.core.loaders.omnidexer import Omnidexer
    from dnd5e.core.models.content import ContentType

    omnidexer = Omnidexer()

    # Get the source manager to see what paths it's discovering
    print("=== Checking source manager paths ===")

    # Access the source manager
    source_manager = omnidexer._source_manager
    source_manager.ensure_sources_ready()

    data_paths = source_manager.get_data_paths()

    print(f"Available content types: {list(data_paths.keys())}")

    book_type = ContentType("book")
    if book_type in data_paths:
        book_paths = data_paths[book_type]
        print(f"Book paths discovered: {book_paths}")

        for path in book_paths:
            print(f"  - {path} (exists: {path.exists()})")
    else:
        print("No book paths found!")
        print(f"ContentType.BOOK = {ContentType.BOOK}")
        print(f"Available types: {[ct.value for ct in data_paths.keys()]}")

    # Also check metadata vs content files
    print("\n=== Metadata files ===")
    metadata_paths = source_manager.get_metadata_files()
    for content_type, paths in metadata_paths.items():
        print(f"{content_type.value}: {paths}")

    print("\n=== Content files ===")
    content_paths = source_manager.get_content_files()
    for content_type, paths in content_paths.items():
        print(f"{content_type.value}: {paths}")


if __name__ == "__main__":
    debug_omnidexer_paths()
