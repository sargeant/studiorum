#!/usr/bin/env python3
"""
Debug script to reproduce the specific duplication issue mentioned in the investigation.
"""

import sys

sys.path.insert(0, "src")

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.document_metadata import DocumentMetadata, DocumentType
from dnd5e.core.references.content_tracker import ContentTracker
from dnd5e.core.resolvers.content_resolver import ContentResolver
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex.document_structure import DocumentStructureBuilder


def reproduce_duplication_issue():
    """Reproduce the exact duplication issue described in the investigation."""
    print("=== Reproducing PHB Duplication Issue ===")

    # Load the omnidexer
    omnidexer = Omnidexer()
    omnidexer.load_all_data()

    # Resolve the PHB book
    resolver = ContentResolver(omnidexer)
    result = resolver.resolve_book("phb")

    if not result.is_success:
        print(f"Failed to resolve PHB: {result.status}")
        return

    book = result.content
    print(f"Book: {book.name}")
    print(f"Chapters: {len(book.contents)}")

    # Create rendering context
    content_tracker = ContentTracker()
    context = RenderingContext(
        output_format="latex",
        omnidexer=omnidexer,
        content_tracker=content_tracker,
        metadata={},
    )

    # Process each chapter using the DocumentStructureBuilder
    document_metadata = DocumentMetadata(
        title=book.name,
        document_type=DocumentType.BOOK,
        include_toc=True,
    )
    builder = DocumentStructureBuilder(document_metadata)

    print("\\n=== Processing Individual Chapters ===")

    # Check the Introduction chapter (index 0)
    intro_chapter = book.contents[0]
    print(f"\\nIntroduction Chapter: {intro_chapter.name}")
    print(f"  Entries: {len(intro_chapter.entries)}")

    # Look for the problematic intro text
    intro_target = "The Dungeons & Dragons roleplaying game is about storytelling"
    intro_content_found = False

    for i, entry in enumerate(intro_chapter.entries):
        if isinstance(entry, str) and intro_target in entry:
            print(f"  Found intro text at entry {i}: {entry[:100]}...")
            intro_content_found = True
            break

    if not intro_content_found:
        print("  No intro text found in Introduction chapter!")

    # Check the Spellcasting chapter (index 10) where duplication was reported
    spellcasting_chapter = book.contents[10]  # Chapter 10: Spellcasting
    print(f"\\nSpellcasting Chapter: {spellcasting_chapter.name}")
    print(f"  Entries: {len(spellcasting_chapter.entries)}")

    # Look for the same intro text in spellcasting
    spellcasting_has_intro = False

    for i, entry in enumerate(spellcasting_chapter.entries):
        if isinstance(entry, str) and intro_target in entry:
            print(f"  DUPLICATE FOUND: Intro text at entry {i}: {entry[:100]}...")
            spellcasting_has_intro = True
        elif isinstance(entry, dict):
            # Check nested entries too
            if "entries" in entry:
                for j, nested in enumerate(entry["entries"]):
                    if isinstance(nested, str) and intro_target in nested:
                        print(
                            f"  DUPLICATE FOUND: Intro text at entry {i}.entries[{j}]: {nested[:100]}..."
                        )
                        spellcasting_has_intro = True

    if not spellcasting_has_intro:
        print("  No intro text found in Spellcasting chapter (as expected)")

    # Now process the chapters through DocumentStructureBuilder
    print("\\n=== Processing Through DocumentStructureBuilder ===")

    intro_section = builder._create_chapter_section(intro_chapter, 1, context)
    spellcasting_section = builder._create_chapter_section(
        spellcasting_chapter, 11, context
    )

    print("\\nIntroduction Section:")
    print(f"  Title: {intro_section.title}")
    print(
        f"  Content items: {len(intro_section.content_items) if intro_section.content_items else 0}"
    )

    # Check if intro content is in the intro section
    intro_in_intro_section = False
    if intro_section.content_items:
        for i, item in enumerate(intro_section.content_items):
            if isinstance(item, str) and intro_target in item:
                print(f"  Intro text found at item {i}")
                intro_in_intro_section = True
                break

    print("\\nSpellcasting Section:")
    print(f"  Title: {spellcasting_section.title}")
    print(
        f"  Content items: {len(spellcasting_section.content_items) if spellcasting_section.content_items else 0}"
    )

    # Check if intro content leaked into spellcasting section
    intro_in_spellcasting_section = False
    if spellcasting_section.content_items:
        for i, item in enumerate(spellcasting_section.content_items):
            if isinstance(item, str) and intro_target in item:
                print(f"  PROBLEM: Intro text found at item {i}: {item[:100]}...")
                intro_in_spellcasting_section = True
            elif isinstance(item, dict) and "entries" in item:
                for j, nested in enumerate(item["entries"]):
                    if isinstance(nested, str) and intro_target in nested:
                        print(
                            f"  PROBLEM: Intro text found at item {i}.entries[{j}]: {nested[:100]}..."
                        )
                        intro_in_spellcasting_section = True

    # Summary
    print("\\n=== Summary ===")
    print(f"Intro text in Introduction chapter: {intro_content_found}")
    print(f"Intro text in Spellcasting chapter raw data: {spellcasting_has_intro}")
    print(
        f"Intro text in Introduction section after processing: {intro_in_intro_section}"
    )
    print(
        f"Intro text in Spellcasting section after processing: {intro_in_spellcasting_section}"
    )

    if intro_in_spellcasting_section:
        print("\\n❌ DUPLICATION ISSUE CONFIRMED")
    else:
        print("\\n✅ No duplication detected - issue may be elsewhere in pipeline")


def check_object_identity_sharing():
    """Check if the same entry objects are being shared between chapters."""
    print("\\n\\n=== Checking Object Identity Sharing ===")

    omnidexer = Omnidexer()
    omnidexer.load_all_data()

    resolver = ContentResolver(omnidexer)
    result = resolver.resolve_book("phb")

    if not result.is_success:
        return

    book = result.content

    # Collect all entry objects by id
    entry_objects = {}

    for chapter_idx, chapter in enumerate(book.contents):
        if hasattr(chapter, "entries") and chapter.entries:
            for entry_idx, entry in enumerate(chapter.entries):
                entry_id = id(entry)
                location = f"Chapter {chapter_idx} ({chapter.name}), Entry {entry_idx}"

                if entry_id in entry_objects:
                    print("SHARED OBJECT DETECTED!")
                    print(f"  Object ID: {entry_id}")
                    print(f"  First location: {entry_objects[entry_id]}")
                    print(f"  Also found at: {location}")
                    if isinstance(entry, str):
                        print(f"  Content preview: {entry[:100]}...")
                    return True
                else:
                    entry_objects[entry_id] = location

    print("No shared objects detected between chapters")
    return False


if __name__ == "__main__":
    print("Starting PHB duplication issue investigation...")

    reproduce_duplication_issue()
    has_shared_objects = check_object_identity_sharing()

    print(f"\\nInvestigation complete. Shared objects detected: {has_shared_objects}")
