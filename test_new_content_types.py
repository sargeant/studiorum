#!/usr/bin/env python3
"""
Test script to verify new content types (backgrounds, classes, feats, races) are working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.loaders.omnidexer import Omnidexer
from core.models.content import ContentType


async def test_new_content_types():
    """Test that new content types are working correctly."""
    
    print("=" * 60)
    print("Testing New Content Types Integration")
    print("=" * 60)
    
    # Test 1: Basic Setup
    print("\n1. Creating Omnidexer instance...")
    try:
        omnidexer = Omnidexer()
        print("✓ Omnidexer created successfully")
    except Exception as e:
        print(f"✗ Failed to create omnidexer: {e}")
        return False
    
    # Test 2: Check loader registration
    print("\n2. Checking loader registration...")
    try:
        registered_types = list(omnidexer._loaders.keys())
        new_types = [ContentType.BACKGROUND, ContentType.CLASS, ContentType.FEAT, ContentType.RACE]
        
        for content_type in new_types:
            if content_type in registered_types:
                print(f"✓ {content_type.value} loader registered")
            else:
                print(f"✗ {content_type.value} loader NOT registered")
        
        print(f"Total registered loaders: {len(registered_types)}")
        print(f"Registered types: {[t.value for t in registered_types]}")
        
    except Exception as e:
        print(f"✗ Error checking loader registration: {e}")
    
    # Test 3: Load data
    print("\n3. Loading data...")
    try:
        # Try to load from 5etools-src first, then test-data
        data_paths = [
            Path("5etools-src/data"),
            Path("test-data")
        ]
        
        loaded_path = None
        for data_path in data_paths:
            if data_path.exists():
                print(f"Found data directory: {data_path}")
                await omnidexer.load_all_data(data_path)
                loaded_path = data_path
                break
        
        if loaded_path:
            print(f"✓ Data loaded from {loaded_path}")
        else:
            print("✗ No data directory found, creating minimal test data...")
            # Create minimal test data
            test_data_dir = Path("test-data")
            test_data_dir.mkdir(exist_ok=True)
            
            # Create a simple backgrounds.json for testing
            backgrounds_file = test_data_dir / "backgrounds.json"
            if not backgrounds_file.exists():
                minimal_data = {
                    "background": [
                        {
                            "name": "Test Background",
                            "source": "TEST",
                            "skillProficiencies": [
                                {"athletics": True, "perception": True}
                            ],
                            "entries": [
                                "A simple test background."
                            ]
                        }
                    ]
                }
                import json
                with open(backgrounds_file, 'w') as f:
                    json.dump(minimal_data, f, indent=2)
                print(f"Created test file: {backgrounds_file}")
            
            # Load the test data
            await omnidexer.load_all_data(test_data_dir)
            print("✓ Test data loaded")
    
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check content statistics
    print("\n4. Content statistics...")
    try:
        stats = omnidexer.get_statistics()
        print(f"Total indexed content: {stats.get('total_entries', 0)}")
        print(f"Content by type:")
        
        for content_type in [ContentType.BACKGROUND, ContentType.CLASS, ContentType.FEAT, ContentType.RACE]:
            count = stats.get('by_type', {}).get(content_type.value, 0)
            print(f"  {content_type.value}: {count}")
            
    except Exception as e:
        print(f"✗ Error getting statistics: {e}")
    
    # Test 5: Search functionality
    print("\n5. Testing search functionality...")
    try:
        # Test finding content by type
        new_types = [ContentType.BACKGROUND, ContentType.CLASS, ContentType.FEAT, ContentType.RACE]
        
        for content_type in new_types:
            try:
                all_content = omnidexer.get_all_by_type(content_type)
                print(f"✓ Found {len(all_content)} {content_type.value}(s)")
                
                # Show first few items
                if all_content:
                    sample_items = all_content[:3]
                    print(f"  Sample items: {[item.name for item in sample_items]}")
                
            except Exception as e:
                print(f"✗ Error searching {content_type.value}: {e}")
    
    except Exception as e:
        print(f"✗ Error in search tests: {e}")
    
    # Test 6: Specific item lookup
    print("\n6. Testing specific item lookup...")
    try:
        # Common items that should exist in 5etools data
        test_cases = [
            (ContentType.BACKGROUND, "Acolyte"),
            (ContentType.FEAT, "Alert"),
            (ContentType.RACE, "Human"),
            (ContentType.CLASS, "Fighter"),
        ]
        
        for content_type, name in test_cases:
            try:
                found_items = omnidexer.find_by_name(name)
                type_specific = [item for item in found_items if item.content_type == content_type]
                
                if type_specific:
                    print(f"✓ Found {name} ({content_type.value})")
                else:
                    print(f"- {name} ({content_type.value}) not found (may not be in test data)")
                    
            except Exception as e:
                print(f"✗ Error looking up {name}: {e}")
    
    except Exception as e:
        print(f"✗ Error in specific lookup tests: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    asyncio.run(test_new_content_types())