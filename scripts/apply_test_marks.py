#!/usr/bin/env python3
"""Apply test marks to test files based on analysis."""

import ast
import json
import sys
from pathlib import Path
from typing import Any


class MarkAdder(ast.NodeTransformer):
    """Add pytest marks to test classes."""

    def __init__(self, marks_to_add: list[str]):
        self.marks_to_add = marks_to_add
        self.imports_needed = set()

    def visit_ClassDef(self, node):
        if node.name.startswith("Test"):
            # Check existing marks
            existing_marks = set()
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute):
                    if (
                        hasattr(decorator.value, "attr")
                        and decorator.value.attr == "mark"
                    ):
                        existing_marks.add(decorator.attr)

            # Add new marks
            for mark in self.marks_to_add:
                if mark not in existing_marks:
                    # Create pytest.mark.{mark} decorator
                    mark_decorator = ast.Attribute(
                        value=ast.Attribute(
                            value=ast.Name(id="pytest", ctx=ast.Load()),
                            attr="mark",
                            ctx=ast.Load(),
                        ),
                        attr=mark,
                        ctx=ast.Load(),
                    )
                    node.decorator_list.insert(0, mark_decorator)
                    self.imports_needed.add("pytest")

        self.generic_visit(node)
        return node


def add_marks_to_file(filepath: Path, marks: list[str]) -> bool:
    """Add marks to a test file."""
    try:
        with open(filepath) as f:
            source = f.read()

        tree = ast.parse(source)

        # Check if file has test classes
        has_test_classes = any(
            isinstance(node, ast.ClassDef) and node.name.startswith("Test")
            for node in ast.walk(tree)
        )

        if not has_test_classes:
            return False

        # Apply marks
        transformer = MarkAdder(marks)
        new_tree = transformer.visit(tree)

        # Ensure pytest is imported
        has_pytest_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pytest":
                        has_pytest_import = True
                        break

        if not has_pytest_import and transformer.imports_needed:
            # Add import at the beginning
            import_node = ast.Import(names=[ast.alias(name="pytest", asname=None)])
            # Find the right position after docstring and other imports
            insert_pos = 0
            for i, node in enumerate(tree.body):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    # Skip docstring
                    insert_pos = i + 1
                elif isinstance(node, ast.Import | ast.ImportFrom):
                    insert_pos = i + 1
                else:
                    break
            tree.body.insert(insert_pos, import_node)

        # Convert back to source
        new_source = ast.unparse(new_tree)

        # Write back
        with open(filepath, "w") as f:
            f.write(new_source)

        return True

    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Apply marks based on analysis results."""
    # Load analysis results
    try:
        with open("test_analysis.json") as f:
            results = json.load(f)
    except FileNotFoundError:
        print("Run analyze_test_marks.py first to generate test_analysis.json")
        sys.exit(1)

    files_updated = 0
    files_skipped = 0

    for result in results:
        filepath = Path(result["file"])
        suggested_marks = result["suggested_marks"]

        if not suggested_marks or not result["tests"]:
            files_skipped += 1
            continue

        # Filter marks to apply (limit to most relevant)
        marks_to_apply = []

        # Speed mark (pick one)
        for speed_mark in ["fast", "medium", "slow"]:
            if speed_mark in suggested_marks:
                marks_to_apply.append(speed_mark)
                break

        # Component mark (pick most specific)
        for component_mark in ["core", "rendering", "cli", "integration"]:
            if component_mark in suggested_marks:
                marks_to_apply.append(component_mark)
                break

        # Dependency marks (add all that apply)
        for dep_mark in ["requires_data", "requires_latex", "network"]:
            if dep_mark in suggested_marks:
                marks_to_apply.append(dep_mark)

        # Quality marks (add if applicable)
        for quality_mark in ["property_based", "performance", "stress"]:
            if quality_mark in suggested_marks:
                marks_to_apply.append(quality_mark)

        if marks_to_apply:
            print(f"Applying marks to {filepath}: {', '.join(marks_to_apply)}")
            if add_marks_to_file(filepath, marks_to_apply):
                files_updated += 1
            else:
                files_skipped += 1
        else:
            files_skipped += 1

    print("\nSummary:")
    print(f"  Files updated: {files_updated}")
    print(f"  Files skipped: {files_skipped}")

    if files_updated > 0:
        print("\nRemember to run 'make format' to fix any formatting issues")


if __name__ == "__main__":
    main()
