#!/usr/bin/env python3
"""
Deep Indexing Examples for Omnidexer

This module provides comprehensive examples of using the Omnidexer deep indexing system
to discover and work with nested D&D content.

Run this file to see the deep indexing system in action:
    python docs/examples/deep-indexing.py
"""

import asyncio
import time
from collections import defaultdict

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType


async def basic_deep_indexing_example():
    """Basic example of loading and querying deep indexed content."""
    print("=== Basic Deep Indexing Example ===")

    # Initialize omnidexer with deep indexing enabled (default)
    omnidexer = Omnidexer(enable_deep_indexing=True)

    # Load all content
    print("Loading all D&D content...")
    start_time = time.time()
    await omnidexer.load_all_data()
    load_time = time.time() - start_time

    print(f"Loaded {omnidexer.total_items} items in {load_time:.2f} seconds")

    # Find primary content (works with or without deep indexing)
    print("\n--- Primary Content ---")
    fighter = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")
    if fighter:
        print(f"Found class: {fighter.name} from {fighter.source}")

    fireball = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
    if fireball:
        print(f"Found spell: {fireball.name} from {fireball.source}")

    # Find nested content (requires deep indexing)
    print("\n--- Nested Content (Deep Indexing) ---")

    # Class features
    action_surge = omnidexer.find(ContentType.CLASS_FEATURE, "Action Surge", "PHB")
    if action_surge:
        print(f"Found class feature: {action_surge.name}")

    # Adventure content
    adventure_sections = omnidexer.find_all(ContentType.ADVENTURE_SECTION)
    if adventure_sections:
        print(f"Found {len(adventure_sections)} adventure sections")
        # Show first few
        for section in adventure_sections[:3]:
            print(f"  - {section.name} from {section.source}")

    # Book content
    variant_rules = omnidexer.find_all(ContentType.VARIANT_RULE)
    if variant_rules:
        print(f"Found {len(variant_rules)} variant rules")
        for rule in variant_rules[:3]:
            print(f"  - {rule.name} from {rule.source}")


async def content_type_exploration():
    """Explore all available content types in the deep indexed system."""
    print("\n=== Content Type Exploration ===")

    omnidexer = Omnidexer(enable_deep_indexing=True)
    await omnidexer.load_all_data()

    # Get all indexed content types
    content_types = omnidexer.get_content_types()
    print(f"\nFound {len(content_types)} different content types:")

    # Count items by type
    type_counts = defaultdict(int)
    for entry in omnidexer._index.values():
        type_counts[entry.content_type] += 1

    # Sort by count (descending)
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

    for content_type, count in sorted_types:
        print(f"  {content_type.value:20} : {count:4} items")

    # Show examples from each nested content type
    print("\n--- Nested Content Examples ---")

    nested_types = [
        ContentType.ADVENTURE_SECTION,
        ContentType.ADVENTURE_TABLE,
        ContentType.BOOK_SECTION,
        ContentType.VARIANT_RULE,
        ContentType.CLASS_FEATURE,
    ]

    for content_type in nested_types:
        items = omnidexer.find_all(content_type)
        if items:
            print(f"\n{content_type.value.replace('_', ' ').title()}:")
            for item in items[:3]:  # Show first 3
                print(f"  - {item.name} ({item.source})")
            if len(items) > 3:
                print(f"  ... and {len(items) - 3} more")


async def search_and_discovery_examples():
    """Examples of different search and discovery patterns."""
    print("\n=== Search and Discovery Examples ===")

    omnidexer = Omnidexer(enable_deep_indexing=True)
    await omnidexer.load_all_data()

    # 1. Find all content from a specific source
    print("\n--- Content by Source ---")
    phb_content = omnidexer.find_by_source("PHB")
    print(f"Player's Handbook contains {len(phb_content)} indexed items")

    # Group by type
    phb_by_type = defaultdict(list)
    for content in phb_content:
        content_type = omnidexer._index[content.hash].content_type
        phb_by_type[content_type].append(content)

    for content_type, items in sorted(
        phb_by_type.items(), key=lambda x: len(x[1]), reverse=True
    ):
        if len(items) > 0:
            print(f"  {content_type.value}: {len(items)} items")

    # 2. Find content by name pattern
    print("\n--- Content by Name ---")

    # Find all content with "Fire" in the name
    fire_content = []
    for entry in omnidexer._index.values():
        if "fire" in entry.content.name.lower():
            fire_content.append(entry.content)

    print(f"Found {len(fire_content)} items with 'fire' in the name:")
    for content in fire_content[:5]:
        content_type = omnidexer._index[content.hash].content_type
        print(f"  - {content.name} ({content_type.value}, {content.source})")

    # 3. Hierarchical content discovery
    print("\n--- Hierarchical Content ---")

    # Find adventure sections with hierarchical names
    adventure_sections = omnidexer.find_all(ContentType.ADVENTURE_SECTION)
    if adventure_sections:
        print("Adventure sections with hierarchical names:")
        for section in adventure_sections[:5]:
            # Get the full hierarchical name from index
            entry = omnidexer._index[section.hash]
            print(f"  - {entry.hierarchical_name}")


async def performance_comparison():
    """Compare performance with and without deep indexing."""
    print("\n=== Performance Comparison ===")

    # Test without deep indexing
    print("Testing without deep indexing...")
    start_time = time.time()
    omnidexer_shallow = Omnidexer(enable_deep_indexing=False)
    await omnidexer_shallow.load_all_data()
    shallow_time = time.time() - start_time
    shallow_count = omnidexer_shallow.total_items

    print(f"  Loaded {shallow_count} items in {shallow_time:.2f} seconds")

    # Test with deep indexing
    print("Testing with deep indexing...")
    start_time = time.time()
    omnidexer_deep = Omnidexer(enable_deep_indexing=True)
    await omnidexer_deep.load_all_data()
    deep_time = time.time() - start_time
    deep_count = omnidexer_deep.total_items

    print(f"  Loaded {deep_count} items in {deep_time:.2f} seconds")

    # Calculate overhead
    overhead = ((deep_time - shallow_time) / shallow_time) * 100
    additional_items = deep_count - shallow_count

    print("\nPerformance Impact:")
    print(f"  Additional items indexed: {additional_items}")
    print(f"  Time overhead: {overhead:.1f}%")
    print(f"  Items per second (shallow): {shallow_count / shallow_time:.0f}")
    print(f"  Items per second (deep): {deep_count / deep_time:.0f}")

    # Get detailed performance stats
    stats = omnidexer_deep.get_performance_stats()
    print("\nDetailed Stats:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for subkey, subvalue in value.items():
                print(f"    {subkey}: {subvalue}")
        else:
            print(f"  {key}: {value}")


async def advanced_usage_examples():
    """Advanced usage patterns and techniques."""
    print("\n=== Advanced Usage Examples ===")

    omnidexer = Omnidexer(enable_deep_indexing=True)
    await omnidexer.load_all_data()

    # 1. Content relationship discovery
    print("\n--- Content Relationships ---")

    # Find a class and its features
    fighter = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")
    if fighter:
        print(f"Found class: {fighter.name}")

        # Find all fighter features
        all_features = omnidexer.find_all(ContentType.CLASS_FEATURE)
        fighter_features = [
            f
            for f in all_features
            if "fighter" in f.name.lower()
            or any(
                "fighter" in str(getattr(f, attr, "")).lower()
                for attr in ["description", "class_name", "source_class"]
            )
        ]

        print(f"  Related features: {len(fighter_features)}")
        for feature in fighter_features[:5]:
            print(f"    - {feature.name}")

    # 2. Cross-content discovery
    print("\n--- Cross-Content Discovery ---")

    # Find creatures that might reference spells
    creatures = omnidexer.find_all(ContentType.CREATURE)
    spellcasting_creatures = []

    for creature in creatures[:10]:  # Check first 10 for demo
        # This is a simplified check - real implementation would use
        # the creature's spell reference resolution
        if hasattr(creature, "spellcasting") or hasattr(creature, "trait"):
            spellcasting_creatures.append(creature)

    print(f"Found {len(spellcasting_creatures)} spellcasting creatures (sample):")
    for creature in spellcasting_creatures[:3]:
        print(f"  - {creature.name} ({creature.source})")

    # 3. Memory and index analysis
    print("\n--- Index Analysis ---")

    print(f"Total indexed hashes: {len(omnidexer.indexed_hashes)}")
    print(f"Hash index size: {len(omnidexer._index)}")
    print(
        f"Type index entries: {sum(len(entries) for entries in omnidexer._by_type.values())}"
    )
    print(
        f"Source index entries: {sum(len(entries) for entries in omnidexer._by_source.values())}"
    )
    print(
        f"Name index entries: {sum(len(entries) for entries in omnidexer._by_name.values())}"
    )

    # Check for any potential inconsistencies
    hash_count = len(omnidexer._index)
    indexed_hash_count = len(omnidexer.indexed_hashes)

    if hash_count == indexed_hash_count:
        print("✓ Index consistency check passed")
    else:
        print(
            f"⚠ Index inconsistency: {hash_count} indexed vs {indexed_hash_count} tracked"
        )


async def custom_content_example():
    """Example of implementing DeepIndexable for custom content."""
    print("\n=== Custom Content Implementation Example ===")

    from dnd5e.core.interfaces import DeepIndexable
    from dnd5e.core.models.content import BaseContent

    class CustomAdventure(BaseContent, DeepIndexable):
        """Example custom adventure with nested encounters."""

        def __init__(self, name: str, source: str, encounters: list[dict]):
            super().__init__(name=name, source=source)
            self.encounters = encounters

        def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
            """Extract encounters as indexable content."""
            nested_content = []

            for encounter_data in self.encounters:
                try:
                    encounter = CustomEncounter(
                        name=encounter_data.get("name", "Unknown Encounter"),
                        source=self.source,
                        description=encounter_data.get("description", ""),
                        challenge_rating=encounter_data.get("cr", "Unknown"),
                    )
                    nested_content.append(encounter)
                except Exception as e:
                    print(f"Warning: Failed to parse encounter {encounter_data}: {e}")
                    continue

            return nested_content

    class CustomEncounter(BaseContent):
        """Example custom encounter content."""

        def __init__(
            self, name: str, source: str, description: str, challenge_rating: str
        ):
            super().__init__(name=name, source=source)
            self.description = description
            self.challenge_rating = challenge_rating

    # Create and test custom content
    print("Creating custom adventure with nested encounters...")

    custom_adventure = CustomAdventure(
        name="Example Adventure",
        source="CUSTOM",
        encounters=[
            {
                "name": "Goblin Patrol",
                "description": "3 goblins patrol the area",
                "cr": "1/4",
            },
            {
                "name": "Orc Chieftain",
                "description": "The orc leader challenges the party",
                "cr": "2",
            },
            {
                "name": "Dragon's Lair",
                "description": "Ancient red dragon in its lair",
                "cr": "17",
            },
        ],
    )

    # Test deep indexing
    omnidexer = Omnidexer(enable_deep_indexing=True)

    # Manually test the deep indexing method
    encounters = custom_adventure.get_deep_index_entries(omnidexer)
    print(f"Extracted {len(encounters)} encounters from custom adventure:")

    for encounter in encounters:
        print(f"  - {encounter.name} (CR {encounter.challenge_rating})")

    print(
        "\nThis demonstrates how to implement DeepIndexable for custom content types."
    )


async def troubleshooting_examples():
    """Examples of troubleshooting and debugging deep indexing."""
    print("\n=== Troubleshooting Examples ===")

    omnidexer = Omnidexer(enable_deep_indexing=True)
    await omnidexer.load_all_data()

    # 1. Check for missing expected content
    print("\n--- Missing Content Checks ---")

    expected_class_features = ["Action Surge", "Fighting Style", "Second Wind"]
    missing_features = []

    for feature_name in expected_class_features:
        feature = omnidexer.find(ContentType.CLASS_FEATURE, feature_name, "PHB")
        if not feature:
            missing_features.append(feature_name)

    if missing_features:
        print(f"Missing expected class features: {missing_features}")
        print("This might indicate issues with class feature parsing.")
    else:
        print("✓ All expected class features found")

    # 2. Performance troubleshooting
    print("\n--- Performance Diagnostics ---")

    stats = omnidexer.get_performance_stats()

    # Check for performance issues
    load_time = stats.get("load_time", 0)
    if load_time > 5.0:
        print(f"⚠ Slow loading detected: {load_time:.2f}s (target: <5s)")
        print("Consider disabling deep indexing for performance-critical applications")
    else:
        print(f"✓ Loading time acceptable: {load_time:.2f}s")

    # Check memory usage (simplified)
    total_items = stats.get("total_items", 0)
    if total_items > 10000:
        print(f"⚠ High item count: {total_items} items")
        print("Monitor memory usage in production")
    else:
        print(f"✓ Item count reasonable: {total_items} items")

    # 3. Index consistency checks
    print("\n--- Index Consistency ---")

    # Check that all indexed items are findable
    consistency_errors = 0
    sample_size = min(100, len(omnidexer._index))  # Check first 100 items

    for i, (hash_id, entry) in enumerate(omnidexer._index.items()):
        if i >= sample_size:
            break

        # Try to find the content
        found = omnidexer.find(
            entry.content_type, entry.content.name, entry.content.source
        )
        if not found:
            consistency_errors += 1
            print(
                f"⚠ Content not findable: {entry.content.name} ({entry.content_type.value})"
            )

    if consistency_errors == 0:
        print(f"✓ Index consistency check passed ({sample_size} items tested)")
    else:
        print(
            f"⚠ Found {consistency_errors} consistency issues in {sample_size} items tested"
        )


async def main():
    """Run all examples."""
    print("Omnidexer Deep Indexing Examples")
    print("=" * 50)

    try:
        await basic_deep_indexing_example()
        await content_type_exploration()
        await search_and_discovery_examples()
        await performance_comparison()
        await advanced_usage_examples()
        await custom_content_example()
        await troubleshooting_examples()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("\nFor more information, see:")
        print("  - docs/omnidexer-deep-indexing.md")
        print("  - docs/api/omnidexer.md")

    except Exception as e:
        print(f"\nExample failed with error: {e}")
        print("This might indicate missing data files or configuration issues.")
        print("Make sure you have run the setup and data loading commands.")


if __name__ == "__main__":
    asyncio.run(main())
