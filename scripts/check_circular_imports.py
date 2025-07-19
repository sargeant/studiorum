#!/usr/bin/env python3
"""
Circular import detection tool for 5e2pdf project.

This script analyzes Python import dependencies to detect potential circular
import chains that could cause runtime errors or make the code harder to maintain.
"""

import argparse
import ast
import sys
from collections import defaultdict, deque
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

        return ".".join(module_parts)

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

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.dependencies: dict[str, set[str]] = defaultdict(set)
        self.module_files: dict[str, Path] = {}
        self.import_details: dict[str, list[ImportInfo]] = {}

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
                print(f"Warning: Could not analyze {file_path}: {e}")

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
                import_names = [
                    imp.imported_name or imp.module for imp in relevant_imports
                ]
                line_nums = [str(imp.line_number) for imp in relevant_imports]
                descriptions.append(
                    f"{from_module} imports {', '.join(import_names)} from {to_module} (lines {', '.join(line_nums)})"
                )

        return "; ".join(descriptions)

    def get_import_statistics(self) -> dict[str, int]:
        """Get statistics about imports in the project."""
        stats = {
            "total_modules": len(self.module_files),
            "total_imports": sum(
                len(imports) for imports in self.import_details.values()
            ),
            "modules_with_imports": len(
                [m for m in self.import_details if self.import_details[m]]
            ),
            "max_imports_per_module": max(
                len(imports) for imports in self.import_details.values()
            )
            if self.import_details
            else 0,
        }

        # Find most imported modules
        import_counts = defaultdict(int)
        for imports in self.import_details.values():
            for imp in imports:
                import_counts[imp.module] += 1

        if import_counts:
            most_imported = max(import_counts, key=import_counts.get)
            stats["most_imported_module"] = most_imported
            stats["most_imported_count"] = import_counts[most_imported]

        return stats

    def generate_report(self) -> str:
        """Generate a comprehensive report."""
        cycles = self.find_circular_dependencies()
        stats = self.get_import_statistics()

        report = ["Circular Import Analysis Report"]
        report.append("=" * 40)
        report.append("")

        # Statistics
        report.append("Project Statistics:")
        report.append(f"  Total modules: {stats['total_modules']}")
        report.append(f"  Total imports: {stats['total_imports']}")
        report.append(f"  Modules with imports: {stats['modules_with_imports']}")
        report.append(f"  Max imports per module: {stats['max_imports_per_module']}")

        if "most_imported_module" in stats:
            report.append(
                f"  Most imported module: {stats['most_imported_module']} ({stats['most_imported_count']} times)"
            )

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
        description="Detect circular imports in Python projects"
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
        help="Exit with error code if circular dependencies are found",
    )

    args = parser.parse_args()

    if not args.source_path.exists():
        print(f"Error: Source path {args.source_path} does not exist")
        sys.exit(1)

    # Analyze the project
    detector = CircularImportDetector(args.source_path)
    detector.analyze_project()

    # Generate report
    report = detector.generate_report()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    # Exit with error if cycles found and --fail-on-cycles is set
    if args.fail_on_cycles:
        cycles = detector.find_circular_dependencies()
        if cycles:
            print(f"\nError: {len(cycles)} circular dependencies found!")
            sys.exit(1)


if __name__ == "__main__":
    main()
