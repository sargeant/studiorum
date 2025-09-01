#!/usr/bin/env python3
"""Analyze tests and suggest appropriate marks based on characteristics."""

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class TestAnalyzer(ast.NodeVisitor):
    """Analyze test files to determine appropriate marks."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.test_functions = []
        self.imports = []
        self.fixtures_used = []
        self.current_class = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        if node.name.startswith("Test"):
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = None
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name.startswith("test_"):
            # Check for marks
            marks = []
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute):
                    if decorator.attr in ["mark", "fixture"]:
                        marks.append(ast.unparse(decorator))
                elif isinstance(decorator, ast.Call):
                    marks.append(ast.unparse(decorator))

            # Check fixtures used
            fixtures = [arg.arg for arg in node.args.args if arg.arg != "self"]

            self.test_functions.append(
                {
                    "name": node.name,
                    "class": self.current_class,
                    "marks": marks,
                    "fixtures": fixtures,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)


def analyze_file(filepath: Path) -> dict[str, Any]:
    """Analyze a single test file."""
    with open(filepath) as f:
        tree = ast.parse(f.read())

    analyzer = TestAnalyzer(filepath)
    analyzer.visit(tree)

    # Determine suggested marks based on analysis
    suggested_marks = []

    # Component-based marks
    rel_path = filepath.relative_to(Path("tests"))
    if "unit" in str(rel_path):
        suggested_marks.append("fast")
    if "integration" in str(rel_path):
        suggested_marks.append("integration")
        suggested_marks.append("medium")
    if "performance" in str(rel_path) or "benchmark" in str(rel_path):
        suggested_marks.append("performance")
        suggested_marks.append("slow")
    if "renderers/latex" in str(rel_path):
        suggested_marks.append("rendering")
    if "cli" in str(rel_path):
        suggested_marks.append("cli")
    if "core" in str(rel_path):
        suggested_marks.append("core")

    # Check imports for dependencies
    imports_str = " ".join(analyzer.imports)
    if "omnidexer" in imports_str.lower():
        suggested_marks.append("requires_data")
    if "latex" in imports_str.lower() or "xelatex" in imports_str.lower():
        suggested_marks.append("requires_latex")
    if "hypothesis" in imports_str.lower():
        suggested_marks.append("property_based")
    if "requests" in imports_str.lower() or "urllib" in imports_str.lower():
        suggested_marks.append("network")

    # Check for slow/stress patterns
    for test in analyzer.test_functions:
        if "stress" in test["name"] or "large" in test["name"]:
            suggested_marks.append("stress")
        if "slow" in test["name"] or "performance" in test["name"]:
            suggested_marks.append("slow")

    # Remove duplicates
    suggested_marks = list(set(suggested_marks))

    return {
        "file": str(filepath),
        "tests": analyzer.test_functions,
        "suggested_marks": suggested_marks,
        "imports": list(set(analyzer.imports)),
    }


def main():
    """Analyze all test files and generate marking recommendations."""
    test_dir = Path("tests")
    results = []

    for filepath in test_dir.rglob("test_*.py"):
        if "__pycache__" in str(filepath):
            continue

        try:
            analysis = analyze_file(filepath)
            results.append(analysis)

            # Print recommendations for files needing marks
            if analysis["suggested_marks"] and analysis["tests"]:
                existing_marks = set()
                for test in analysis["tests"]:
                    for mark in test["marks"]:
                        if "pytest.mark" in mark:
                            existing_marks.add(mark)

                if not existing_marks or len(analysis["suggested_marks"]) > len(
                    existing_marks
                ):
                    print(f"\n{filepath}:")
                    print(
                        f"  Suggested marks: {', '.join(analysis['suggested_marks'])}"
                    )
                    if existing_marks:
                        print(f"  Existing marks: {', '.join(existing_marks)}")
                    print(f"  Tests in file: {len(analysis['tests'])}")

        except Exception as e:
            print(f"Error analyzing {filepath}: {e}", file=sys.stderr)

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_tests = sum(len(r["tests"]) for r in results)
    files_needing_marks = sum(1 for r in results if r["suggested_marks"] and r["tests"])

    print(f"Total test files analyzed: {len(results)}")
    print(f"Total test functions: {total_tests}")
    print(f"Files needing marks: {files_needing_marks}")

    # Mark distribution
    mark_counts = {}
    for result in results:
        for mark in result["suggested_marks"]:
            mark_counts[mark] = mark_counts.get(mark, 0) + len(result["tests"])

    print("\nSuggested mark distribution:")
    for mark, count in sorted(mark_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mark}: {count} tests")

    # Save results to JSON for further processing
    with open("test_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed analysis saved to test_analysis.json")


if __name__ == "__main__":
    main()
