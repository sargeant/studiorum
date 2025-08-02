#!/usr/bin/env python3
"""Debug script to analyze the content enrichment process."""

import asyncio
import json
from pathlib import Path

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.resolvers.content_resolver import ContentResolver


async def debug_content_enrichment():
    """Debug the content enrichment process step by step."""
    print("=== Content Enrichment Debug Analysis ===\n")

    # 1. Set up the source manager and omnidexer
    print("1. Setting up source manager...")
    source_manager = ConfigurableSourceManager()
    await source_manager.ensure_sources_ready()

    omnidexer = Omnidexer(source_manager)
    await omnidexer.load_all_data()

    # 2. Check what adventures are loaded
    print("2. Checking loaded adventures...")
    adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
    print(f"Found {len(adventures)} adventures:")
    for adventure in adventures:
        print(
            f"  - {adventure.name} (ID: {adventure.id}, Source: {adventure.source.abbreviation})"
        )
        print(f"    has_content(): {adventure.has_content()}")
        print(f"    is_metadata_only(): {adventure.is_metadata_only()}")
        print(f"    Contents: {len(adventure.contents)} chapters")
        for i, chapter in enumerate(adventure.contents):
            print(
                f"      Chapter {i + 1}: '{chapter.name}' - {len(chapter.entries)} entries"
            )
        print()

    # 3. Test content resolution
    print("3. Testing content resolution...")
    resolver = ContentResolver(omnidexer)

    print("Resolving adventure 'TEST'...")
    result = resolver.resolve_adventure("TEST")

    print(f"Resolution status: {result.status}")
    print(f"Resolution successful: {result.is_success}")

    if result.content:
        adventure = result.content
        print(f"Resolved adventure: {adventure.name}")
        print(f"Adventure ID: {adventure.id}")
        print(f"Source: {adventure.source.abbreviation}")
        print(f"has_content(): {adventure.has_content()}")
        print(f"is_metadata_only(): {adventure.is_metadata_only()}")
        print(f"Contents: {len(adventure.contents)} chapters")

        # Check content details
        print("\n4. Content details:")
        for i, chapter in enumerate(adventure.contents):
            print(f"  Chapter {i + 1}: '{chapter.name}'")
            print(f"    Entries: {len(chapter.entries)} items")
            if chapter.entries:
                print(f"    First entry preview: {str(chapter.entries[0])[:100]}...")
            else:
                print("    No entries (empty)")

        # Get content summary
        print("\n5. Content summary:")
        summary = adventure.get_content_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
    else:
        print("No content resolved!")
        print(f"Suggestions: {result.suggestions}")

    # 4. Check content files directly
    print("\n6. Checking content files...")
    content_files = source_manager.get_content_files()
    adventure_files = content_files.get(ContentType.ADVENTURE, [])
    print(f"Found {len(adventure_files)} adventure content files:")
    for file_path in adventure_files:
        print(f"  - {file_path.name}")

        # Check what's in the test adventure file
        if "test-adventure" in file_path.name.lower():
            print(f"    Reading {file_path.name}...")
            try:
                with open(file_path, "r") as f:
                    content_data = json.load(f)
                    print(f"    Keys: {list(content_data.keys())}")
                    if "data" in content_data:
                        data_sections = content_data["data"]
                        print(f"    Data sections: {len(data_sections)}")
                        for i, section in enumerate(
                            data_sections[:3]
                        ):  # First 3 sections
                            print(
                                f"      Section {i + 1}: {section.get('name', 'No name')} - type: {section.get('type', 'No type')}"
                            )
                            entries = section.get("entries", [])
                            print(f"        Entries: {len(entries)} items")
            except Exception as e:
                print(f"    Error reading file: {e}")

    # 5. Test ContentMerger directly
    print("\n7. Testing ContentMerger directly...")
    content_merger = resolver.content_merger

    print("Loading content file for 'test-adventure'...")
    content_data = content_merger.load_content_file(
        ContentType.ADVENTURE, "test-adventure"
    )

    if content_data:
        print("Content file loaded successfully!")
        print(f"Keys: {list(content_data.keys())}")
        if "data" in content_data:
            print(f"Data sections: {len(content_data['data'])}")
    else:
        print("Failed to load content file!")

        # Try different ID patterns
        print("Trying different ID patterns...")
        for test_id in ["test-adventure", "TEST", "test"]:
            print(f"  Trying ID: '{test_id}'")
            test_data = content_merger.load_content_file(ContentType.ADVENTURE, test_id)
            if test_data:
                print(f"    SUCCESS with ID '{test_id}'!")
                break
            else:
                print(f"    Failed with ID '{test_id}'")

    # 6. Test book content enrichment
    print("\n8. Testing book content enrichment...")
    books = omnidexer.get_all_by_type(ContentType.BOOK)
    print(f"Found {len(books)} books:")
    for book in books:
        print(f"  - {book.name} (ID: {book.id}, Source: {book.source.abbreviation})")
        print(f"    has_content(): {book.has_content()}")
        print(f"    is_metadata_only(): {book.is_metadata_only()}")
        print(f"    Contents: {len(book.contents)} chapters")
        print()

    print("Resolving book 'TEST'...")
    book_result = resolver.resolve_book("TEST")

    print(f"Book resolution status: {book_result.status}")
    print(f"Book resolution successful: {book_result.is_success}")

    if book_result.content:
        book = book_result.content
        print(f"Resolved book: {book.name}")
        print(f"Book ID: {book.id}")
        print(f"Source: {book.source.abbreviation}")
        print(f"has_content(): {book.has_content()}")
        print(f"is_metadata_only(): {book.is_metadata_only()}")
        print(f"Contents: {len(book.contents)} chapters")

        # Check content details
        print("\n9. Book content details:")
        for i, chapter in enumerate(book.contents):
            print(f"  Chapter {i + 1}: '{chapter.name}'")
            print(f"    Entries: {len(chapter.entries)} items")
            if chapter.entries:
                print(f"    First entry preview: {str(chapter.entries[0])[:100]}...")
            else:
                print("    No entries (empty)")
    else:
        print("No book content resolved!")
        print(f"Suggestions: {book_result.suggestions}")

    print("\nLoading book content file for 'test-book'...")
    book_content_data = content_merger.load_content_file(ContentType.BOOK, "test-book")

    if book_content_data:
        print("Book content file loaded successfully!")
        print(f"Keys: {list(book_content_data.keys())}")
        if "data" in book_content_data:
            print(f"Data sections: {len(book_content_data['data'])}")
    else:
        print("Failed to load book content file!")


if __name__ == "__main__":
    asyncio.run(debug_content_enrichment())
