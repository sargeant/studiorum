#!/usr/bin/env python
"""Debug script to understand test data loading issues."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def debug_test_data_loading():
    """Debug why test data isn't loading in integration tests."""

    print("=== Debug Test Data Loading ===\n")

    # Step 1: Reset environment
    print("1. Resetting test environment...")
    from tests.test_helpers import reset_test_environment

    reset_test_environment()
    print("   ✓ Environment reset complete\n")

    # Step 2: Check content type registry
    print("2. Checking content type registry...")
    from dnd5e.core.registry import get_content_type_registry

    registry = get_content_type_registry()
    registrations = registry.get_all()
    print(f"   - Registered content types: {len(registrations)}")
    for ct in list(registrations.keys())[:5]:
        print(f"     - {ct}")
    print()

    # Step 3: Check ContentFactory
    print("3. Checking ContentFactory...")
    from dnd5e.core.loaders.content_factory import ContentFactory

    if hasattr(ContentFactory, "_class_map"):
        print(
            f"   - ContentFactory has class map: {list(ContentFactory._class_map.keys())[:5]}"
        )
    else:
        print("   - ContentFactory has NO class map")

    # Create a factory instance
    from dnd5e.core.loaders.content_factory import get_content_factory

    factory = get_content_factory()
    print(f"   - Factory instance created: {factory is not None}")
    print()

    # Step 4: Try to load test-data
    print("4. Setting up test-data source...")
    from dnd5e.core.config.sources import (
        ContentConfiguration,
        ContentSource,
        SourceType,
    )
    from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager

    config = ContentConfiguration()
    test_data_path = Path("test-data")
    print(f"   - Test data path exists: {test_data_path.exists()}")
    print(f"   - Test data path: {test_data_path.absolute()}")

    config.add_source(
        ContentSource(
            name="test-data",
            type=SourceType.DIRECTORY,
            path=test_data_path,
            enabled=True,
            priority=0,  # Highest priority
        )
    )

    source_manager = ConfigurableSourceManager()
    source_manager._config = config
    source_manager._manager = None  # Force rebuild
    source_manager.ensure_sources_ready()
    print("   - Source manager configured with test-data\n")

    # Step 5: Create omnidexer and load data
    print("5. Creating Omnidexer and loading data...")
    from dnd5e.core.loaders.omnidexer import Omnidexer

    omnidexer = Omnidexer(source_manager)

    # Check if omnidexer has data before loading
    print("   - Omnidexer created")

    # Load all data
    omnidexer.load_all_data()
    print("   - Data loading complete\n")

    # Step 6: Check what was loaded
    print("6. Checking loaded content...")
    books = omnidexer.get_all_by_type("book")
    adventures = omnidexer.get_all_by_type("adventure")
    creatures = omnidexer.get_all_by_type("monster")
    spells = omnidexer.get_all_by_type("spell")

    print(f"   - Books loaded: {len(books)}")
    if books:
        for book in books[:3]:
            print(f"     - {book.name} ({book.source.abbreviation})")

    print(f"   - Adventures loaded: {len(adventures)}")
    if adventures:
        for adv in adventures[:3]:
            print(f"     - {adv.name} ({adv.source.abbreviation})")

    print(f"   - Creatures loaded: {len(creatures)}")
    print(f"   - Spells loaded: {len(spells)}")
    print()

    # Step 7: Check test-data files directly
    print("7. Checking test-data files directly...")
    test_data_files = list(test_data_path.glob("*.json"))
    print(f"   - JSON files in test-data: {len(test_data_files)}")
    for f in test_data_files[:5]:
        print(f"     - {f.name}")

    # Check books.json specifically
    books_file = test_data_path / "books.json"
    if books_file.exists():
        import json

        with open(books_file) as f:
            data = json.load(f)
            if "book" in data:
                print(f"   - books.json has {len(data['book'])} books")
                for book in data["book"][:2]:
                    print(
                        f"     - {book.get('name', 'unnamed')} ({book.get('id', 'no-id')})"
                    )

    # Check adventures.json specifically
    adventures_file = test_data_path / "adventures.json"
    if adventures_file.exists():
        import json

        with open(adventures_file) as f:
            data = json.load(f)
            if "adventure" in data:
                print(f"   - adventures.json has {len(data['adventure'])} adventures")
                for adv in data["adventure"][:2]:
                    print(
                        f"     - {adv.get('name', 'unnamed')} ({adv.get('id', 'no-id')})"
                    )
    print()

    # Step 8: Try simulating parallel test execution
    print("8. Simulating parallel test execution...")
    print("   - Resetting environment again...")
    reset_test_environment()

    print("   - Checking if registry is still populated...")
    registry = get_content_type_registry()
    registrations = registry.get_all()
    print(f"   - Registered content types after reset: {len(registrations)}")

    print("   - Checking ContentFactory after reset...")
    if hasattr(ContentFactory, "_class_map"):
        print(
            f"   - ContentFactory still has class map: {bool(ContentFactory._class_map)}"
        )
    else:
        print("   - ContentFactory has NO class map after reset")

    print("\n=== Diagnosis Complete ===")

    # Return diagnostic info
    return {
        "books_loaded": len(books),
        "adventures_loaded": len(adventures),
        "registry_populated": len(registrations) > 0,
        "factory_has_map": hasattr(ContentFactory, "_class_map"),
        "test_data_exists": test_data_path.exists(),
    }


if __name__ == "__main__":
    try:
        results = debug_test_data_loading()
        print("\nDiagnostic Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
