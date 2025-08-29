#!/usr/bin/env python3
"""Debug script to trace adventure content loading issue in detail."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from typing import cast

from studiorum.core.models.content import ContentType
from studiorum.core.resolvers.content_resolver import ContentResolver
from studiorum.core.services.container import ServiceContainer
from studiorum.core.services.protocols import OmnidexerProtocol


def main():
    print("=== DEBUG: CLI Adventure Resolution Chain ===\n")

    # Step 1: Get omnidexer via service container (same as CLI)
    print("=== STEP 1: Loading omnidexer via service container ===")
    container = ServiceContainer.get_global_instance()
    omnidexer_service = container.get_service_sync(OmnidexerProtocol)
    print("Omnidexer service loaded successfully")

    # Step 2: Check what adventures are in the omnidexer
    print("\n=== STEP 2: Check adventures in omnidexer ===")
    adventure_type = ContentType.ADVENTURE
    all_adventures = omnidexer_service.get_all_by_type(adventure_type)
    print(f"Total adventures in omnidexer: {len(all_adventures)}")

    # Find SKT specifically
    skt_adventures = [
        adv
        for adv in all_adventures
        if hasattr(adv.source, "abbreviation")
        and adv.source.abbreviation.upper() == "SKT"
    ]

    if skt_adventures:
        skt = skt_adventures[0]
        print("✅ Found SKT in omnidexer:")
        print(f"   Name: {skt.name}")
        print(f"   ID: {getattr(skt, 'id', 'no-id')}")
        print(f"   Contents: {len(getattr(skt, 'contents', []))}")

        # Check if contents have entries
        if hasattr(skt, "contents") and skt.contents:
            first_content = skt.contents[0]
            print(f"   First content: {getattr(first_content, 'name', 'no-name')}")
            entries = getattr(first_content, "entries", [])
            print(f"   First content entries: {len(entries)}")
            if entries:
                print(f"   Sample entry: {str(entries[0])[:100]}...")
            else:
                print("   ❌ First content has NO entries!")
        else:
            print("   ❌ Adventure has NO contents!")
    else:
        print("❌ SKT not found in omnidexer")
        # Show what we have
        for adv in all_adventures[:5]:
            source_abbrev = getattr(adv.source, "abbreviation", "no-abbrev")
            print(f"   - {adv.name} ({source_abbrev})")

    # Step 3: Use ContentResolver like CLI does
    print("\n=== STEP 3: Using ContentResolver (same as CLI) ===")
    resolver = ContentResolver(cast(OmnidexerProtocol, omnidexer_service))
    result = resolver.resolve_adventure("skt")

    print(f"Resolution status: {result.status}")
    if result.is_success and result.content:
        adventure = result.content
        print(f"✅ Resolved adventure: {adventure.name}")
        print(f"   ID: {getattr(adventure, 'id', 'no-id')}")
        print(f"   Contents: {len(getattr(adventure, 'contents', []))}")

        if hasattr(adventure, "contents") and adventure.contents:
            first_content = adventure.contents[0]
            print(f"   First content: {getattr(first_content, 'name', 'no-name')}")
            entries = getattr(first_content, "entries", [])
            print(f"   First content entries: {len(entries)}")
            if entries:
                print(f"   Sample entry: {str(entries[0])[:100]}...")
                print(f"   Entry type: {type(entries[0])}")
            else:
                print("   ❌ First content has NO entries after resolution!")
        else:
            print("   ❌ Resolved adventure has NO contents after resolution!")
    else:
        print("❌ Failed to resolve adventure")
        if result.suggestions:
            print(f"   Suggestions: {result.suggestions}")


if __name__ == "__main__":
    main()
