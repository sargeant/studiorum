#!/usr/bin/env python3
"""Analyze fixture patterns in test files to identify standardization opportunities."""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional


class FixtureAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze test fixtures and setup patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fixtures = []
        self.setup_methods = []
        self.factory_patterns = []
        self.test_methods = []

    def visit_FunctionDef(self, node):
        """Visit function definitions to identify patterns."""
        # Check for fixtures
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "fixture":
                self.fixtures.append(node.name)
            elif isinstance(decorator, ast.Attribute) and decorator.attr == "fixture":
                self.fixtures.append(node.name)

        # Check for setup/teardown methods
        if node.name in [
            "setup_method",
            "teardown_method",
            "setup_class",
            "teardown_class",
        ]:
            self.setup_methods.append(node.name)

        # Check for factory patterns
        if node.name.startswith("make_") or node.name.startswith("create_"):
            self.factory_patterns.append(node.name)

        # Check for test methods
        if node.name.startswith("test_"):
            self.test_methods.append(node.name)

        self.generic_visit(node)


def analyze_test_file(filepath: Path) -> dict:
    """Analyze a single test file for patterns."""
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())

        analyzer = FixtureAnalyzer(str(filepath))
        analyzer.visit(tree)

        return {
            "fixtures": analyzer.fixtures,
            "setup_methods": analyzer.setup_methods,
            "factory_patterns": analyzer.factory_patterns,
            "test_methods": analyzer.test_methods,
        }
    except Exception as e:
        return {
            "error": str(e),
            "fixtures": [],
            "setup_methods": [],
            "factory_patterns": [],
            "test_methods": [],
        }


def find_duplicate_fixtures(all_fixtures: dict[str, list[str]]) -> dict[str, list[str]]:
    """Find fixtures that appear in multiple files."""
    fixture_files = defaultdict(list)
    for filepath, fixtures in all_fixtures.items():
        for fixture in fixtures:
            fixture_files[fixture].append(filepath)

    return {name: files for name, files in fixture_files.items() if len(files) > 1}


def analyze_setup_patterns(test_files: list[Path]) -> dict:
    """Analyze setup/teardown patterns across test files."""
    patterns = {
        "setup_method_only": [],
        "teardown_method_only": [],
        "both_setup_teardown": [],
        "setup_class": [],
        "mixed_patterns": [],
        "no_setup": [],
    }

    for filepath in test_files:
        analysis = analyze_test_file(filepath)
        setup_methods = analysis["setup_methods"]

        if not setup_methods:
            patterns["no_setup"].append(str(filepath))
        elif "setup_method" in setup_methods and "teardown_method" in setup_methods:
            patterns["both_setup_teardown"].append(str(filepath))
        elif "setup_method" in setup_methods:
            patterns["setup_method_only"].append(str(filepath))
        elif "teardown_method" in setup_methods:
            patterns["teardown_method_only"].append(str(filepath))
        elif "setup_class" in setup_methods or "teardown_class" in setup_methods:
            patterns["setup_class"].append(str(filepath))
        elif len(set(setup_methods)) > 1:
            patterns["mixed_patterns"].append(str(filepath))

    return patterns


def main():
    """Main analysis function."""
    test_dir = Path("tests")
    test_files = list(test_dir.rglob("test_*.py"))

    print(f"Analyzing {len(test_files)} test files...\n")

    # Analyze all test files
    all_fixtures = {}
    all_factories = []
    setup_patterns = analyze_setup_patterns(test_files)

    for filepath in test_files:
        analysis = analyze_test_file(filepath)
        if analysis["fixtures"]:
            all_fixtures[str(filepath)] = analysis["fixtures"]
        if analysis["factory_patterns"]:
            all_factories.extend(analysis["factory_patterns"])

    # Find duplicate fixtures
    duplicate_fixtures = find_duplicate_fixtures(all_fixtures)

    # Print analysis results
    print("=" * 60)
    print("FIXTURE ANALYSIS REPORT")
    print("=" * 60)

    print("\n📊 Summary Statistics:")
    print(f"  - Total test files: {len(test_files)}")
    print(f"  - Files with fixtures: {len(all_fixtures)}")
    print(
        f"  - Total unique fixtures: {len(set(f for fixtures in all_fixtures.values() for f in fixtures))}"
    )
    print(f"  - Factory patterns found: {len(set(all_factories))}")

    print("\n🔄 Setup/Teardown Patterns:")
    for pattern, files in setup_patterns.items():
        if files:
            print(f"  - {pattern}: {len(files)} files")

    if duplicate_fixtures:
        print("\n⚠️  Duplicate Fixtures (appearing in multiple files):")
        for fixture_name, files in sorted(duplicate_fixtures.items())[:10]:
            print(f"  - {fixture_name}: {len(files)} files")
            for file in files[:3]:
                print(f"      {file}")

    # Find common factory patterns
    factory_counts = defaultdict(int)
    for factory in all_factories:
        factory_counts[factory] += 1

    if factory_counts:
        print("\n🏭 Factory Patterns:")
        for factory, count in sorted(
            factory_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  - {factory}: used {count} times")

    # Recommendations
    print("\n📝 Recommendations:")

    if len(setup_patterns["mixed_patterns"]) > 0:
        print(
            f"  ⚠️  {len(setup_patterns['mixed_patterns'])} files use mixed setup patterns - standardize"
        )

    if len(duplicate_fixtures) > 5:
        print(
            f"  ⚠️  {len(duplicate_fixtures)} duplicate fixtures - consolidate into conftest.py"
        )

    if len(setup_patterns["setup_method_only"]) > len(setup_patterns["no_setup"]) / 2:
        print("  💡 Consider converting setup_method patterns to fixtures")

    if len(all_factories) < 5:
        print("  💡 Consider adding more factory fixtures for test data generation")

    print(
        f"\n✅ Files following best practices (no setup, using fixtures): {len(setup_patterns['no_setup'])}"
    )


if __name__ == "__main__":
    main()
