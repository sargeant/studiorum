#!/usr/bin/env python3
"""
Comprehensive validation error analysis script.

Searches all JSON content for patterns that cause validation errors,
helping identify complex data structures that need preprocessing.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any, Dict, List, Set

def find_choice_objects(obj: Any, path: str = "") -> List[str]:
    """Find all choice objects in the data structure."""
    results = []
    
    if isinstance(obj, dict):
        # Check for choice objects
        if "choose" in obj:
            results.append(f"{path}: choice object {obj}")
        elif "from" in obj and "amount" in obj:
            results.append(f"{path}: from/amount choice object {obj}")
        
        # Recurse into dict values
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(find_choice_objects(value, new_path))
    
    elif isinstance(obj, list):
        # Recurse into list items
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(find_choice_objects(item, new_path))
    
    return results

def find_complex_objects(obj: Any, path: str = "") -> List[str]:
    """Find objects that might need conversion to strings."""
    results = []
    
    if isinstance(obj, dict):
        # Check for header-like objects
        if "header" in obj and "index" in obj:
            results.append(f"{path}: header object {obj}")
        
        # Check for objects in string-expected fields
        for key in ["author", "authors", "headers"]:
            if key in obj and isinstance(obj[key], (dict, list)):
                if isinstance(obj[key], list):
                    for i, item in enumerate(obj[key]):
                        if isinstance(item, dict):
                            results.append(f"{path}.{key}[{i}]: dict in list field {item}")
                else:
                    results.append(f"{path}.{key}: dict in string field {obj[key]}")
        
        # Recurse into dict values
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(find_complex_objects(value, new_path))
    
    elif isinstance(obj, list):
        # Recurse into list items
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(find_complex_objects(item, new_path))
    
    return results

def find_validation_patterns(obj: Any, path: str = "") -> Dict[str, List[str]]:
    """Find all patterns that might cause validation errors."""
    patterns = {
        "choice_objects": [],
        "complex_objects": [],
        "type_mismatches": [],
        "nested_structures": []
    }
    
    patterns["choice_objects"].extend(find_choice_objects(obj, path))
    patterns["complex_objects"].extend(find_complex_objects(obj, path))
    
    if isinstance(obj, dict):
        # Check for common type mismatches
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            
            # String fields that might contain objects
            if key in ["name", "source", "author", "storyline"] and isinstance(value, (dict, list)):
                patterns["type_mismatches"].append(f"{new_path}: expected string, got {type(value).__name__} {value}")
            
            # List fields that might contain single values
            elif key in ["entries", "headers", "authors"] and not isinstance(value, list):
                patterns["type_mismatches"].append(f"{new_path}: expected list, got {type(value).__name__} {value}")
            
            # Recurse
            sub_patterns = find_validation_patterns(value, new_path)
            for pattern_type, items in sub_patterns.items():
                patterns[pattern_type].extend(items)
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            sub_patterns = find_validation_patterns(item, new_path)
            for pattern_type, items in sub_patterns.items():
                patterns[pattern_type].extend(items)
    
    return patterns

def analyze_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a single JSON file for validation error patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        patterns = find_validation_patterns(data, file_path.name)
        
        return {
            "file": str(file_path),
            "patterns": patterns,
            "size": file_path.stat().st_size,
            "success": True
        }
    
    except Exception as e:
        return {
            "file": str(file_path),
            "error": str(e),
            "success": False
        }

def main():
    """Main analysis function."""
    # Find all JSON files in 5etools-src/data directory
    data_dir = Path("5etools-src/data")
    if not data_dir.exists():
        print("Error: 5etools-src/data directory not found")
        sys.exit(1)
    
    json_files = list(data_dir.rglob("*.json"))
    print(f"Found {len(json_files)} JSON files to analyze...")
    
    # Analyze all files
    all_patterns = defaultdict(list)
    file_results = []
    error_count = 0
    
    for i, file_path in enumerate(json_files, 1):
        if i % 100 == 0:
            print(f"Processed {i}/{len(json_files)} files...")
        
        result = analyze_file(file_path)
        file_results.append(result)
        
        if not result["success"]:
            error_count += 1
            continue
        
        # Aggregate patterns
        for pattern_type, items in result["patterns"].items():
            all_patterns[pattern_type].extend(items)
    
    print(f"\nAnalysis complete!")
    print(f"Files processed: {len(json_files)}")
    print(f"Errors: {error_count}")
    print(f"Success: {len(json_files) - error_count}")
    
    # Summary of patterns found
    print(f"\n{'='*60}")
    print("VALIDATION ERROR PATTERNS SUMMARY")
    print(f"{'='*60}")
    
    for pattern_type, items in all_patterns.items():
        print(f"\n{pattern_type.upper().replace('_', ' ')}: {len(items)} instances")
        if items:
            # Show unique patterns
            unique_patterns = Counter()
            for item in items:
                # Extract just the pattern part, not the file-specific path
                if ": " in item:
                    pattern_part = item.split(": ", 1)[1]
                    unique_patterns[pattern_part] += 1
            
            print("  Most common patterns:")
            for pattern, count in unique_patterns.most_common(10):
                print(f"    ({count}x) {pattern}")
    
    # Detailed output for choice objects
    if all_patterns["choice_objects"]:
        print(f"\n{'='*60}")
        print("DETAILED CHOICE OBJECT ANALYSIS")
        print(f"{'='*60}")
        
        choice_types = defaultdict(list)
        for item in all_patterns["choice_objects"]:
            if "choice object" in item:
                # Extract the actual choice object
                try:
                    obj_str = item.split("choice object ", 1)[1]
                    obj = eval(obj_str)  # Dangerous but for analysis only
                    if isinstance(obj, dict) and "choose" in obj:
                        choose_value = obj["choose"]
                        if isinstance(choose_value, list):
                            choice_types[f"choose list of {len(choose_value)} items"].append(obj)
                        else:
                            choice_types[f"choose {type(choose_value).__name__}"].append(obj)
                except:
                    choice_types["unparseable"].append(item)
            elif "from/amount choice object" in item:
                choice_types["from/amount pattern"].append(item)
        
        for choice_type, examples in choice_types.items():
            print(f"\n{choice_type}: {len(examples)} instances")
            # Show a few examples
            for i, example in enumerate(examples[:3]):
                print(f"  Example {i+1}: {example}")
    
    # Files with most issues
    files_with_issues = []
    for result in file_results:
        if result["success"]:
            total_issues = sum(len(items) for items in result["patterns"].values())
            if total_issues > 0:
                files_with_issues.append((result["file"], total_issues, result["patterns"]))
    
    files_with_issues.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n{'='*60}")
    print("FILES WITH MOST VALIDATION ISSUES")
    print(f"{'='*60}")
    
    for file_path, issue_count, patterns in files_with_issues[:10]:
        print(f"\n{file_path}: {issue_count} issues")
        for pattern_type, items in patterns.items():
            if items:
                print(f"  {pattern_type}: {len(items)}")

if __name__ == "__main__":
    main()