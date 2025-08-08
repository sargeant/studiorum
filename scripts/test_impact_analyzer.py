#!/usr/bin/env python3
"""Test Impact Analyzer - Determines which tests need to run based on changed files.

This tool analyzes code changes and identifies the minimal set of tests that need
to be run to validate those changes. It uses static analysis to understand
dependencies between source files and test files.
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Optional


class TestImpactAnalyzer:
    """Analyzes which tests are impacted by source code changes."""

    def __init__(self, project_root: Path = None):
        """Initialize the analyzer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.src_root = self.project_root / "src"
        self.test_root = self.project_root / "tests"

        # Cache for import mappings
        self._import_cache: dict[Path, set[str]] = {}
        self._test_coverage_map: dict[str, set[Path]] = {}

        # Build initial mappings
        self._build_test_coverage_map()

    def analyze_changes(self, changed_files: list[str]) -> set[Path]:
        """Determine which tests need to run based on changed files.

        Args:
            changed_files: List of changed file paths (relative to project root)

        Returns:
            Set of test files that should be run
        """
        impacted_tests = set()

        for file_path_str in changed_files:
            file_path = Path(file_path_str)

            # Direct test file changes
            if file_path.parts[0] == "tests":
                impacted_tests.add(file_path)
                continue

            # Source code changes
            if file_path.parts[0] == "src":
                # Find all tests that import this module
                module_name = self._path_to_module(file_path)
                if module_name in self._test_coverage_map:
                    impacted_tests.update(self._test_coverage_map[module_name])

                # Also check for pattern-based test discovery
                impacted_tests.update(self._find_related_tests_by_pattern(file_path))

            # Configuration changes affect many tests
            if file_path.name in [
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "Makefile",
            ]:
                # Add core and configuration tests
                impacted_tests.update(self._find_tests_by_pattern("test_*config*"))
                impacted_tests.update(self._find_tests_by_pattern("test_*setup*"))
                impacted_tests.add(Path("tests/unit/test_cli.py"))

        return impacted_tests

    def _build_test_coverage_map(self) -> None:
        """Build a map of which source modules are tested by which test files."""
        for test_file in self.test_root.rglob("test_*.py"):
            imports = self._extract_imports(test_file)
            for import_name in imports:
                if import_name.startswith("dnd5e"):
                    if import_name not in self._test_coverage_map:
                        self._test_coverage_map[import_name] = set()
                    self._test_coverage_map[import_name].add(test_file)

    def _extract_imports(self, file_path: Path) -> set[str]:
        """Extract all imports from a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            Set of imported module names
        """
        if file_path in self._import_cache:
            return self._import_cache[file_path]

        imports = set()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        # Also add submodule imports
                        for alias in node.names:
                            imports.add(f"{node.module}.{alias.name}")
        except (SyntaxError, FileNotFoundError):
            # Ignore files with syntax errors or missing files
            pass

        self._import_cache[file_path] = imports
        return imports

    def _path_to_module(self, file_path: Path) -> str:
        """Convert a file path to a Python module name.

        Args:
            file_path: Path to the Python file

        Returns:
            Module name (e.g., "dnd5e.core.models.spells")
        """
        # Remove src/ prefix and .py suffix
        if file_path.parts[0] == "src":
            parts = file_path.parts[1:]
        else:
            parts = file_path.parts

        # Remove .py extension
        if parts[-1].endswith(".py"):
            parts = list(parts[:-1]) + [parts[-1][:-3]]

        return ".".join(parts)

    def _find_related_tests_by_pattern(self, source_path: Path) -> set[Path]:
        """Find tests related to a source file based on naming patterns.

        Args:
            source_path: Path to the source file

        Returns:
            Set of related test files
        """
        related_tests = set()

        # Extract the module/class name from the source file
        if source_path.stem == "__init__":
            # For __init__.py, use the parent directory name
            module_name = source_path.parent.name
        else:
            module_name = source_path.stem

        # Look for test files with matching names
        patterns = [
            f"test_{module_name}.py",
            f"test_*{module_name}*.py",
            f"**/test_{module_name}.py",
            f"**/test_*{module_name}*.py",
        ]

        for pattern in patterns:
            for test_file in self.test_root.rglob(pattern):
                related_tests.add(test_file)

        return related_tests

    def _find_tests_by_pattern(self, pattern: str) -> set[Path]:
        """Find test files matching a pattern.

        Args:
            pattern: Glob pattern for test files

        Returns:
            Set of matching test files
        """
        matching_tests = set()
        for test_file in self.test_root.rglob(pattern):
            if test_file.is_file():
                matching_tests.add(test_file)
        return matching_tests

    def get_test_dependencies(self, test_file: Path) -> set[str]:
        """Get the source modules that a test file depends on.

        Args:
            test_file: Path to the test file

        Returns:
            Set of source module names
        """
        imports = self._extract_imports(test_file)
        return {imp for imp in imports if imp.startswith("dnd5e")}

    def generate_impact_report(self, changed_files: list[str]) -> dict:
        """Generate a detailed impact analysis report.

        Args:
            changed_files: List of changed file paths

        Returns:
            Dictionary containing impact analysis details
        """
        impacted_tests = self.analyze_changes(changed_files)

        # Categorize tests by type
        unit_tests = []
        integration_tests = []
        rendering_tests = []
        cli_tests = []
        other_tests = []

        for test in impacted_tests:
            test_str = str(test.relative_to(self.project_root))
            if "integration" in test_str:
                integration_tests.append(test_str)
            elif "renderers" in test_str or "rendering" in test_str:
                rendering_tests.append(test_str)
            elif "cli" in test_str:
                cli_tests.append(test_str)
            elif "unit" in test_str or test.parent.name == "tests":
                unit_tests.append(test_str)
            else:
                other_tests.append(test_str)

        return {
            "changed_files": changed_files,
            "total_impacted_tests": len(impacted_tests),
            "tests_to_run": sorted(
                [str(t.relative_to(self.project_root)) for t in impacted_tests]
            ),
            "by_category": {
                "unit": sorted(unit_tests),
                "integration": sorted(integration_tests),
                "rendering": sorted(rendering_tests),
                "cli": sorted(cli_tests),
                "other": sorted(other_tests),
            },
            "recommended_order": [
                "unit",  # Fast feedback
                "cli",  # User-facing functionality
                "rendering",  # Core functionality
                "integration",  # Full system validation
                "other",  # Everything else
            ],
        }

    def suggest_test_command(self, changed_files: list[str]) -> str:
        """Suggest an optimal pytest command for the changed files.

        Args:
            changed_files: List of changed file paths

        Returns:
            Suggested pytest command
        """
        impacted_tests = self.analyze_changes(changed_files)

        if not impacted_tests:
            return "# No tests impacted by these changes"

        # Convert to relative paths
        test_paths = [str(t.relative_to(self.project_root)) for t in impacted_tests]

        # Group by directory for more efficient execution
        test_dirs = set()
        individual_tests = []

        for test_path in test_paths:
            parts = Path(test_path).parts
            if len(parts) > 2:
                # Group by subdirectory
                test_dirs.add("/".join(parts[:2]))
            else:
                individual_tests.append(test_path)

        # Build command
        if len(test_dirs) > 3:
            # Too many directories, just run all impacted tests
            return f"pytest {' '.join(sorted(test_paths))}"
        else:
            # Run by directory for better organization
            paths = sorted(list(test_dirs) + individual_tests)
            return f"pytest {' '.join(paths)}"


def main():
    """Main entry point for the test impact analyzer."""
    if len(sys.argv) < 2:
        print("Usage: test_impact_analyzer.py <changed_file1> [<changed_file2> ...]")
        print("\nExample:")
        print("  test_impact_analyzer.py src/dnd5e/core/models/spells.py")
        print("\nOr with git:")
        print("  git diff --name-only main | xargs test_impact_analyzer.py")
        sys.exit(1)

    changed_files = sys.argv[1:]
    analyzer = TestImpactAnalyzer()

    # Generate and print the impact report
    report = analyzer.generate_impact_report(changed_files)

    print(f"\n{'=' * 60}")
    print("TEST IMPACT ANALYSIS REPORT")
    print(f"{'=' * 60}\n")

    print(f"Changed files: {len(report['changed_files'])}")
    for f in report["changed_files"]:
        print(f"  - {f}")

    print(f"\nTotal impacted tests: {report['total_impacted_tests']}")

    print("\nTests by category:")
    for category in report["recommended_order"]:
        tests = report["by_category"][category]
        if tests:
            print(f"\n  {category.upper()} ({len(tests)} tests):")
            for test in tests[:5]:  # Show first 5
                print(f"    - {test}")
            if len(tests) > 5:
                print(f"    ... and {len(tests) - 5} more")

    print(f"\n{'=' * 60}")
    print("SUGGESTED TEST COMMAND:")
    print(f"{'=' * 60}\n")

    command = analyzer.suggest_test_command(changed_files)
    print(command)

    # Also output JSON for CI integration
    json_output = Path(".test-impact.json")
    with open(json_output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to: {json_output}")


if __name__ == "__main__":
    main()
