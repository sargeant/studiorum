#!/usr/bin/env python3
"""
Circular import detection tool for 5e2pdf project.

This script analyzes Python import dependencies to detect potential circular
import chains that could cause runtime errors or make the code harder to maintain.

Output behavior:
- Silent when no circular imports are found
- Detailed error information when circular imports are detected
- Warning messages for analysis issues (to stderr)
"""

import argparse
import ast
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module: str
    imported_name: str | None = None
    line_number: int = 0
    is_from_import: bool = False


@dataclass
class CircularDependency:
    """Represents a circular dependency chain."""

    modules: list[str]
    description: str

    def __str__(self) -> str:
        cycle_str = " -> ".join(self.modules + [self.modules[0]])
        return f"Circular dependency: {cycle_str}\n  {self.description}"


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to extract import information from Python files."""

    def __init__(self, file_path: Path, base_path: Path):
        self.file_path = file_path
        self.base_path = base_path
        self.imports: list[ImportInfo] = []
        self.module_name = self._get_module_name()

    def _get_module_name(self) -> str:
        """Get the module name from file path."""
        relative_path = self.file_path.relative_to(self.base_path)
        module_parts = list(relative_path.parts)

        # Remove .py extension and __init__ files
        if module_parts[-1].endswith(".py"):
            module_parts[-1] = module_parts[-1][:-3]
        if module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]

        # Prepend base package name (dnd5e)
        base_package = self.base_path.name
        if module_parts:
            return f"{base_package}." + ".".join(module_parts)
        else:
            return base_package

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            # Only track imports within the project (starting with 'dnd5e.')
            if alias.name.startswith("dnd5e."):
                self.imports.append(
                    ImportInfo(
                        module=alias.name, line_number=node.lineno, is_from_import=False
                    )
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statements."""
        if node.module and node.module.startswith("dnd5e."):
            # Handle relative imports
            if node.module.startswith(".."):
                # Convert relative import to absolute
                module_parts = self.module_name.split(".")
                level = node.level
                if level > len(module_parts):
                    return  # Invalid relative import

                base_module = ".".join(module_parts[:-level])
                if node.module.startswith(".."):
                    module_name = base_module + "." + node.module[2:]
                else:
                    module_name = base_module + "." + node.module
            else:
                module_name = node.module

            for alias in node.names:
                self.imports.append(
                    ImportInfo(
                        module=module_name,
                        imported_name=alias.name,
                        line_number=node.lineno,
                        is_from_import=True,
                    )
                )
        elif node.module is None:
            # Handle relative imports like "from . import something"
            # These are imports from the same package
            base_module = ".".join(self.module_name.split(".")[:-1])
            if base_module:
                for alias in node.names:
                    self.imports.append(
                        ImportInfo(
                            module=f"{base_module}.{alias.name}",
                            imported_name=alias.name,
                            line_number=node.lineno,
                            is_from_import=True,
                        )
                    )


class CircularImportDetector:
    """Detects circular import dependencies in Python projects."""

    def __init__(self, source_path: Path, verbose: bool = False):
        self.source_path = source_path
        self.verbose = verbose
        self.dependencies: dict[str, set[str]] = defaultdict(set)
        self.module_files: dict[str, Path] = {}
        self.import_details: dict[str, list[ImportInfo]] = {}
        self.analysis_warnings: list[str] = []

    def analyze_project(self) -> None:
        """Analyze all Python files in the project."""
        python_files = list(self.source_path.rglob("*.py"))

        for file_path in python_files:
            if file_path.name.startswith("."):
                continue  # Skip hidden files

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                analyzer = ImportAnalyzer(file_path, self.source_path)
                analyzer.visit(tree)

                # Store module information
                self.module_files[analyzer.module_name] = file_path
                self.import_details[analyzer.module_name] = analyzer.imports

                # Build dependency graph
                for import_info in analyzer.imports:
                    self.dependencies[analyzer.module_name].add(import_info.module)

            except Exception as e:
                warning = f"Could not analyze {file_path}: {e}"
                self.analysis_warnings.append(warning)
                if self.verbose:
                    print(f"Warning: {warning}", file=sys.stderr)

    def find_circular_dependencies(self) -> list[CircularDependency]:
        """Find circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(module: str, path: list[str]) -> None:
            if module in rec_stack:
                # Found a cycle
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]

                # Create description
                description = self._describe_cycle(cycle)
                cycles.append(CircularDependency(cycle, description))
                return

            if module in visited:
                return

            visited.add(module)
            rec_stack.add(module)

            for dependency in self.dependencies.get(module, set()):
                dfs(dependency, path + [module])

            rec_stack.remove(module)

        # Start DFS from each module
        for module in self.dependencies:
            if module not in visited:
                dfs(module, [])

        return cycles

    def _describe_cycle(self, cycle: list[str]) -> str:
        """Create a description of the circular dependency."""
        descriptions = []

        for i in range(len(cycle) - 1):
            from_module = cycle[i]
            to_module = cycle[i + 1]

            # Find specific imports causing the dependency
            imports = self.import_details.get(from_module, [])
            relevant_imports = [imp for imp in imports if imp.module == to_module]

            if relevant_imports:
                # Get file path for context
                file_path = self.module_files.get(from_module, "unknown")
                relative_path = (
                    file_path.relative_to(self.source_path)
                    if isinstance(file_path, Path)
                    else file_path
                )

                import_names = [
                    imp.imported_name or imp.module for imp in relevant_imports
                ]
                line_nums = [str(imp.line_number) for imp in relevant_imports]
                descriptions.append(
                    f"{relative_path}:{','.join(line_nums)} imports {', '.join(import_names)} from {to_module}"
                )

        return "; ".join(descriptions)

    def get_summary_stats(self) -> dict[str, int]:
        """Get basic statistics for reporting."""
        return {
            "modules_analyzed": len(self.module_files),
            "total_imports": sum(
                len(imports) for imports in self.import_details.values()
            ),
            "analysis_warnings": len(self.analysis_warnings),
        }

    def check(self) -> int:
        """
        Perform the circular import check.

        Returns:
            0 if no circular imports found
            1 if circular imports found
            2 if analysis errors occurred
        """
        self.analyze_project()
        cycles = self.find_circular_dependencies()

        # Report analysis warnings to stderr
        if self.analysis_warnings:
            for warning in self.analysis_warnings:
                print(f"Warning: {warning}", file=sys.stderr)

        if cycles:
            # Print detailed error information
            print(f"ERROR: {len(cycles)} circular import(s) detected:", file=sys.stderr)
            print("", file=sys.stderr)

            for i, cycle in enumerate(cycles, 1):
                print(f"{i}. {cycle}", file=sys.stderr)
                print("", file=sys.stderr)

            stats = self.get_summary_stats()
            print(
                f"Analysis summary: {stats['modules_analyzed']} modules, {stats['total_imports']} imports",
                file=sys.stderr,
            )

            return 1

        # Silent success - no output when everything is good
        return 0

    def generate_verbose_report(self) -> str:
        """Generate a comprehensive report (for --verbose mode)."""
        cycles = self.find_circular_dependencies()
        stats = self.get_summary_stats()

        report = ["Circular Import Analysis Report"]
        report.append("=" * 40)
        report.append("")

        # Statistics
        report.append("Project Statistics:")
        report.append(f"  Modules analyzed: {stats['modules_analyzed']}")
        report.append(f"  Total imports: {stats['total_imports']}")
        report.append(f"  Analysis warnings: {stats['analysis_warnings']}")
        report.append("")

        # Analysis warnings
        if self.analysis_warnings:
            report.append("Analysis Warnings:")
            for warning in self.analysis_warnings:
                report.append(f"  - {warning}")
            report.append("")

        # Circular dependencies
        if cycles:
            report.append(f"Found {len(cycles)} circular dependencies:")
            report.append("")
            for i, cycle in enumerate(cycles, 1):
                report.append(f"{i}. {cycle}")
                report.append("")
        else:
            report.append("✓ No circular dependencies found!")

        return "\n".join(report)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Detect circular imports in Python projects",
        epilog="Exit codes: 0=no issues, 1=circular imports found, 2=analysis errors",
    )
    parser.add_argument(
        "source_path", type=Path, help="Path to the source directory to analyze"
    )
    parser.add_argument(
        "--output", type=Path, help="Output file for the report (default: stdout)"
    )
    parser.add_argument(
        "--fail-on-cycles",
        action="store_true",
        help="Exit with error code if circular dependencies are found (default behavior)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output including statistics and warnings",
    )

    args = parser.parse_args()

    if not args.source_path.exists():
        print(f"ERROR: Source path {args.source_path} does not exist", file=sys.stderr)
        sys.exit(2)

    # Analyze the project
    detector = CircularImportDetector(args.source_path, verbose=args.verbose)

    if args.verbose or args.output:
        # Analyze first for verbose report
        detector.analyze_project()
        report = detector.generate_verbose_report()

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Report written to {args.output}")
        else:
            print(report)

        # Check for cycles to set exit code
        cycles = detector.find_circular_dependencies()
        exit_code = 1 if cycles else 0
    else:
        # Use the new streamlined check method
        exit_code = detector.check()

    # Handle serious analysis errors
    if detector.analysis_warnings and exit_code == 0:
        # If we have warnings but no cycles, still indicate potential issues
        if (
            len(detector.analysis_warnings) > len(detector.module_files) * 0.1
        ):  # > 10% failure rate
            exit_code = 2

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
