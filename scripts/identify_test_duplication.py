#!/usr/bin/env python3
"""Identify test duplication patterns that can be reduced through parametrization."""

import ast
import difflib
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional


class TestPatternAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze test patterns for duplication."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.test_methods = {}
        self.current_class = None

    def visit_ClassDef(self, node):
        """Track current test class."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Analyze test methods for patterns."""
        if node.name.startswith("test_"):
            # Extract key characteristics
            method_info = {
                "name": node.name,
                "class": self.current_class,
                "filepath": self.filepath,
                "body_length": len(node.body),
                "has_parametrize": any(
                    isinstance(d, ast.Attribute) and d.attr == "parametrize"
                    for d in node.decorator_list
                ),
                "assertions": self._count_assertions(node),
                "calls": self._extract_calls(node),
                "structure": self._get_structure_signature(node),
            }
            self.test_methods[node.name] = method_info
        self.generic_visit(node)

    def _count_assertions(self, node) -> int:
        """Count assertion statements in a test."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                count += 1
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == "assert":
                    count += 1
                elif isinstance(child.func, ast.Attribute):
                    if child.func.attr in [
                        "assertEqual",
                        "assertTrue",
                        "assertFalse",
                        "assertRaises",
                        "assertIn",
                        "assertIsNone",
                    ]:
                        count += 1
        return count

    def _extract_calls(self, node) -> list[str]:
        """Extract function calls made in the test."""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return calls

    def _get_structure_signature(self, node) -> str:
        """Get a simplified structure signature of the test."""
        structure = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                structure.append("assign")
            elif isinstance(stmt, ast.Assert):
                structure.append("assert")
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                structure.append("call")
            elif isinstance(stmt, ast.If):
                structure.append("if")
            elif isinstance(stmt, ast.For):
                structure.append("for")
            elif isinstance(stmt, ast.With):
                structure.append("with")
        return "-".join(structure)


def find_similar_tests(test_methods: dict) -> list[list[dict]]:
    """Find groups of similar test methods."""
    # Group by similar names (differing only by suffix)
    name_groups = defaultdict(list)
    for name, info in test_methods.items():
        # Extract base name (e.g., test_spell_level_0 -> test_spell_level)
        base_name = name
        for suffix in [
            "_0",
            "_1",
            "_2",
            "_3",
            "_4",
            "_5",
            "_6",
            "_7",
            "_8",
            "_9",
            "_empty",
            "_none",
            "_valid",
            "_invalid",
            "_success",
            "_failure",
            "_true",
            "_false",
            "_positive",
            "_negative",
        ]:
            if name.endswith(suffix):
                base_name = name[: -len(suffix)]
                break
        name_groups[base_name].append(info)

    # Find groups with multiple similar tests
    similar_groups = []
    for base_name, tests in name_groups.items():
        if len(tests) >= 3:  # At least 3 similar tests
            similar_groups.append(tests)

    return similar_groups


def find_structural_duplicates(test_methods: dict) -> list[list[dict]]:
    """Find tests with identical structure signatures."""
    structure_groups = defaultdict(list)
    for name, info in test_methods.items():
        if info["structure"] and len(info["structure"]) > 5:  # Non-trivial structure
            structure_groups[info["structure"]].append(info)

    # Return groups with duplicates
    return [tests for tests in structure_groups.values() if len(tests) >= 3]


def suggest_parametrization(similar_tests: list[dict]) -> dict:
    """Suggest parametrization for similar tests."""
    if not similar_tests:
        return {}

    # Analyze differences
    names = [t["name"] for t in similar_tests]
    base_name = os.path.commonprefix(names)

    # Extract varying parts
    varying_parts = []
    for name in names:
        suffix = name[len(base_name) :]
        if suffix.startswith("_"):
            suffix = suffix[1:]
        varying_parts.append(suffix)

    return {
        "base_name": base_name or similar_tests[0]["name"].split("_")[0],
        "count": len(similar_tests),
        "varying_parts": varying_parts,
        "files": list(set(t["filepath"] for t in similar_tests)),
        "suggested_parameters": analyze_parameter_pattern(varying_parts),
    }


def analyze_parameter_pattern(parts: list[str]) -> str:
    """Analyze pattern in varying parts to suggest parameters."""
    # Check if they're numeric
    if all(p.isdigit() for p in parts if p):
        return f"@pytest.mark.parametrize('value', [{', '.join(parts)}])"

    # Check if they're boolean indicators
    if all(
        p in ["true", "false", "valid", "invalid", "success", "failure"]
        for p in parts
        if p
    ):
        return f"@pytest.mark.parametrize('condition', [{', '.join(repr(p) for p in parts)}])"

    # Check if they're descriptive
    if parts:
        return (
            f"@pytest.mark.parametrize('case', [{', '.join(repr(p) for p in parts)}])"
        )

    return "@pytest.mark.parametrize('param', [...])"


def main():
    """Main analysis function."""
    test_dir = Path("tests")
    test_files = list(test_dir.rglob("test_*.py"))

    print(f"Analyzing {len(test_files)} test files for duplication patterns...\n")

    # Analyze all test files
    all_test_methods = {}
    for filepath in test_files:
        try:
            with open(filepath, "r") as f:
                tree = ast.parse(f.read())

            analyzer = TestPatternAnalyzer(str(filepath))
            analyzer.visit(tree)
            all_test_methods.update(analyzer.test_methods)
        except Exception:
            continue

    # Find duplication patterns
    similar_groups = find_similar_tests(all_test_methods)
    structural_duplicates = find_structural_duplicates(all_test_methods)

    # Print analysis results
    print("=" * 70)
    print("TEST DUPLICATION ANALYSIS REPORT")
    print("=" * 70)

    print("\n📊 Summary:")
    print(f"  Total test methods analyzed: {len(all_test_methods)}")
    print(f"  Similar test groups found: {len(similar_groups)}")
    print(f"  Structural duplicate groups: {len(structural_duplicates)}")

    # Calculate potential reduction
    total_reducible = sum(len(g) - 1 for g in similar_groups)
    print(f"  Potential test reduction: {total_reducible} tests")

    if similar_groups:
        print("\n🔄 Top Parametrization Opportunities:")
        print("-" * 70)

        # Sort by potential reduction
        sorted_groups = sorted(similar_groups, key=len, reverse=True)

        for i, group in enumerate(sorted_groups[:10], 1):
            suggestion = suggest_parametrization(group)
            print(f"\n{i}. {suggestion['base_name']}* ({suggestion['count']} tests)")
            print(
                f"   Files: {', '.join(Path(f).name for f in suggestion['files'][:3])}"
            )
            print(f"   Suggestion: {suggestion['suggested_parameters']}")
            print(
                f"   Reduction: {suggestion['count'] - 1} tests → 1 parametrized test"
            )

    if structural_duplicates:
        print("\n📋 Structural Duplicates (same test structure):")
        print("-" * 70)

        for i, group in enumerate(structural_duplicates[:5], 1):
            print(f"\n{i}. Pattern: {group[0]['structure']}")
            print(f"   Found in {len(group)} tests:")
            for test in group[:3]:
                print(f"     - {test['name']} ({Path(test['filepath']).name})")
            if len(group) > 3:
                print(f"     ... and {len(group) - 3} more")

    # Generate recommendations
    print("\n💡 Recommendations:")
    print("-" * 70)

    if total_reducible > 50:
        print(
            f"⚡ High Impact: Parametrizing similar tests could reduce test count by {total_reducible}"
        )

    if len(similar_groups) > 10:
        print(
            f"📝 {len(similar_groups)} groups of similar tests identified for parametrization"
        )

    # Find test classes with many similar methods
    class_methods = defaultdict(list)
    for name, info in all_test_methods.items():
        if info["class"]:
            class_methods[f"{info['filepath']}::{info['class']}"].append(name)

    classes_with_duplication = [
        (cls, methods) for cls, methods in class_methods.items() if len(methods) > 10
    ]

    if classes_with_duplication:
        print("\n🎯 Test classes with many methods (consider parametrization):")
        for cls, methods in sorted(
            classes_with_duplication, key=lambda x: len(x[1]), reverse=True
        )[:5]:
            filepath, classname = cls.split("::")
            print(f"   - {classname} ({Path(filepath).name}): {len(methods)} methods")

    # Example parametrization
    if similar_groups:
        print("\n📖 Example Parametrization:")
        print("-" * 70)
        group = similar_groups[0]
        suggestion = suggest_parametrization(group)

        print("Before (multiple test methods):")
        for test in group[:3]:
            print(f"  def {test['name']}(self): ...")

        print("\nAfter (single parametrized test):")
        print(f"  {suggestion['suggested_parameters']}")
        param_name = (
            suggestion["suggested_parameters"].split("(")[1].split(",")[0].strip("'")
        )
        print(f"  def {suggestion['base_name']}(self, {param_name}): ...")
        print("      # Test logic using parameter")

    print(f"\n✅ Total potential test reduction: {total_reducible} tests")
    percentage = (
        (total_reducible / len(all_test_methods)) * 100 if all_test_methods else 0
    )
    print(f"   This represents {percentage:.1f}% of all test methods")


if __name__ == "__main__":
    main()
