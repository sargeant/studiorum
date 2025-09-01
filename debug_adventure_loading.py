#!/usr/bin/env python3
"""Debug script to trace adventure content loading issue."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from studiorum.core.loaders.content_merger import ContentMerger
from studiorum.core.loaders.json_loader import JsonDataLoader
from studiorum.core.loaders.unified_source_manager import UnifiedSourceManager
from studiorum.core.models.content import ContentType
from studiorum.core.services.access import get_app_config


def main():
    print("=== DEBUG: Adventure Loading Analysis ===\n")

    # Initialize source manager
    source_manager = UnifiedSourceManager()
    source_manager.ensure_sources_ready()

    print("=== STEP 1: Check what files are available ===")

    # Check metadata files (get_data_paths)
    metadata_files = source_manager.get_data_paths()
    adventure_metadata = metadata_files.get(ContentType.ADVENTURE, [])
    print(f"Adventure METADATA files: {len(adventure_metadata)}")
    for path in adventure_metadata:
        print(f"  - {path}")

    print()

    # Check content files (get_content_files)
    content_files = source_manager.get_content_files()
    adventure_content = content_files.get(ContentType.ADVENTURE, [])
    print(f"Adventure CONTENT files: {len(adventure_content)}")
    for path in adventure_content:
        print(f"  - {path}")

    print("\n=== STEP 2: Test ContentMerger ===")

    # Create merger and test loading SKT
    merger = ContentMerger(source_manager)

    # Try to load adventure content for SKT
    skt_content = merger.load_content_file(ContentType.ADVENTURE, "skt")
    if skt_content:
        print("✅ ContentMerger found content for SKT")
        print(f"   Content keys: {list(skt_content.keys())}")
        if "data" in skt_content:
            data_sections = skt_content["data"]
            print(f"   Data sections: {len(data_sections)}")
            if data_sections:
                first_section = data_sections[0]
                print(f"   First section type: {first_section.get('type')}")
                print(f"   First section name: {first_section.get('name')}")
                entries = first_section.get("entries", [])
                print(f"   First section entries: {len(entries)}")
    else:
        print("❌ ContentMerger could not find content for SKT")

    print("\n=== STEP 3: Test JsonDataLoader directly ===")

    # Create loader and try to load metadata file
    loader = JsonDataLoader(ContentType.ADVENTURE)

    if adventure_metadata:
        metadata_path = adventure_metadata[0]  # Usually adventures.json
        print(f"Loading metadata from: {metadata_path}")
        metadata_adventures = loader.load(metadata_path)
        print(f"Loaded {len(metadata_adventures)} adventures from metadata")

        # Find SKT in metadata
        skt_metadata = None
        for adv in metadata_adventures:
            if hasattr(adv, "id") and adv.id == "skt":
                skt_metadata = adv
                break

        if skt_metadata:
            print(f"✅ Found SKT in metadata: {skt_metadata.name}")
            print(
                f"   Contents: {len(skt_metadata.contents) if hasattr(skt_metadata, 'contents') else 0}"
            )
            if hasattr(skt_metadata, "contents") and skt_metadata.contents:
                first_content = skt_metadata.contents[0]
                print(f"   First content: {getattr(first_content, 'name', 'no name')}")
                entries = getattr(first_content, "entries", [])
                print(f"   First content entries: {len(entries)}")
        else:
            print("❌ Could not find SKT in metadata")

    if adventure_content:
        # Find SKT content file
        skt_content_file = None
        for path in adventure_content:
            if "skt" in path.stem.lower():
                skt_content_file = path
                break

        if skt_content_file:
            print(f"\nLoading content from: {skt_content_file}")
            content_adventures = loader.load(skt_content_file)
            print(f"Loaded {len(content_adventures)} adventures from content file")

            if content_adventures:
                adv = content_adventures[0]
                print(f"   Adventure name: {getattr(adv, 'name', 'no name')}")
                print(f"   Contents: {len(getattr(adv, 'contents', []))}")
                if hasattr(adv, "contents") and adv.contents:
                    first_content = adv.contents[0]
                    print(
                        f"   First content: {getattr(first_content, 'name', 'no name')}"
                    )
                    entries = getattr(first_content, "entries", [])
                    print(f"   First content entries: {len(entries)}")
        else:
            print("❌ Could not find SKT content file")

    print("\n=== STEP 4: Test merging ===")

    if skt_metadata and skt_content:
        print("Testing ContentMerger.merge_metadata_content()")

        # Convert Pydantic model back to dict for merging
        metadata_dict = (
            skt_metadata.model_dump()
            if hasattr(skt_metadata, "model_dump")
            else skt_metadata.__dict__
        )

        merged = merger.merge_metadata_content(metadata_dict, skt_content)
        print(f"Merged result keys: {list(merged.keys())}")
        merged_contents = merged.get("contents", [])
        print(f"Merged contents: {len(merged_contents)}")

        if merged_contents:
            first_merged = merged_contents[0]
            print(f"   First merged content: {first_merged.get('name', 'no name')}")
            entries = first_merged.get("entries", [])
            print(f"   First merged entries: {len(entries)}")
            if entries:
                print(f"   Sample entry: {str(entries[0])[:100]}...")


if __name__ == "__main__":
    main()
