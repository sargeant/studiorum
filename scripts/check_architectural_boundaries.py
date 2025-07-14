#!/usr/bin/env python3
"""
Architectural boundary checker for 5e2pdf project.

This script enforces architectural layering rules to prevent violations of
dependency boundaries and maintain clean architecture.
"""

import argparse
import ast
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Layer:
    """Represents an architectural layer."""

    name: str
    path_patterns: List[str]
    allowed_dependencies: List[str]
    description: str


@dataclass
class Violation:
    """Represents an architectural boundary violation."""

    from_module: str
    to_module: str
    from_layer: str
    to_layer: str
    line_number: int
    description: str

    def __str__(self) -> str:
        return f"{self.from_module}:{self.line_number} -> {self.to_module} ({self.from_layer} -> {self.to_layer}): {self.description}"


class ArchitecturalBoundaryChecker:
    """Checks architectural boundary violations in Python projects."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.layers = self._define_layers()
        self.module_layer_map: Dict[str, str] = {}
        self.violations: List[Violation] = []

    def _define_layers(self) -> List[Layer]:
        """Define the architectural layers for 5e2pdf."""
        return [
            Layer(
                name="cli",
                path_patterns=["src.cli"],
                allowed_dependencies=["core", "renderers", "processors"],
                description="Command-line interface layer",
            ),
            Layer(
                name="renderers",
                path_patterns=["src.renderers"],
                allowed_dependencies=["core"],
                description="Output rendering layer",
            ),
            Layer(
                name="processors",
                path_patterns=["src.processors"],
                allowed_dependencies=["core"],
                description="Data processing layer",
            ),
            Layer(
                name="core",
                path_patterns=["src.core"],
                allowed_dependencies=[],
                description="Core business logic layer",
            ),
        ]

    def _get_module_layer(self, module_name: str) -> Optional[str]:
        """Get the layer for a module."""
        for layer in self.layers:
            for pattern in layer.path_patterns:
                if module_name.startswith(pattern):
                    return layer.name
        return None

    def _is_dependency_allowed(self, from_layer: str, to_layer: str) -> bool:
        """Check if a dependency between layers is allowed."""
        if from_layer == to_layer:
            return True  # Same layer is always allowed

        for layer in self.layers:
            if layer.name == from_layer:
                return to_layer in layer.allowed_dependencies

        return False

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for boundary violations."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Get module name
            relative_path = file_path.relative_to(self.source_path)
            module_parts = list(relative_path.parts)
            if module_parts[-1].endswith(".py"):
                module_parts[-1] = module_parts[-1][:-3]
            if module_parts[-1] == "__init__":
                module_parts = module_parts[:-1]
            module_name = ".".join(module_parts)

            # Get module layer
            from_layer = self._get_module_layer(module_name)
            if not from_layer:
                return  # Not in a defined layer

            # Check imports
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._check_import(node, module_name, from_layer)

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    def _check_import(self, node: ast.AST, from_module: str, from_layer: str) -> None:
        """Check an import statement for boundary violations."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src."):
                    to_layer = self._get_module_layer(alias.name)
                    if to_layer and not self._is_dependency_allowed(
                        from_layer, to_layer
                    ):
                        self.violations.append(
                            Violation(
                                from_module=from_module,
                                to_module=alias.name,
                                from_layer=from_layer,
                                to_layer=to_layer,
                                line_number=node.lineno,
                                description=f"Layer '{from_layer}' cannot import from layer '{to_layer}'",
                            )
                        )

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("src."):
                to_layer = self._get_module_layer(node.module)
                if to_layer and not self._is_dependency_allowed(from_layer, to_layer):
                    for alias in node.names:
                        self.violations.append(
                            Violation(
                                from_module=from_module,
                                to_module=node.module,
                                from_layer=from_layer,
                                to_layer=to_layer,
                                line_number=node.lineno,
                                description=f"Layer '{from_layer}' cannot import '{alias.name}' from layer '{to_layer}'",
                            )
                        )

    def analyze_project(self) -> None:
        """Analyze the entire project for boundary violations."""
        python_files = list(self.source_path.rglob("*.py"))

        for file_path in python_files:
            if file_path.name.startswith("."):
                continue  # Skip hidden files
            self.analyze_file(file_path)

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the analysis."""
        layer_counts = defaultdict(int)
        violation_counts = defaultdict(int)

        for violation in self.violations:
            layer_counts[violation.from_layer] += 1
            violation_counts[f"{violation.from_layer} -> {violation.to_layer}"] += 1

        return {
            "total_violations": len(self.violations),
            "layers_with_violations": len(layer_counts),
            "layer_counts": dict(layer_counts),
            "violation_types": dict(violation_counts),
        }

    def generate_report(self) -> str:
        """Generate a comprehensive architectural boundary report."""
        stats = self.get_statistics()

        report = ["Architectural Boundary Analysis Report"]
        report.append("=" * 45)
        report.append("")

        # Layer definitions
        report.append("Defined Layers:")
        for layer in self.layers:
            deps = (
                ", ".join(layer.allowed_dependencies)
                if layer.allowed_dependencies
                else "None"
            )
            report.append(f"  {layer.name}: {layer.description}")
            report.append(f"    Patterns: {', '.join(layer.path_patterns)}")
            report.append(f"    Allowed dependencies: {deps}")
            report.append("")

        # Statistics
        report.append("Analysis Results:")
        report.append(f"  Total violations: {stats['total_violations']}")
        report.append(f"  Layers with violations: {stats['layers_with_violations']}")
        report.append("")

        if stats["total_violations"] > 0:
            report.append("Violation Types:")
            for vtype, count in stats["violation_types"].items():
                report.append(f"  {vtype}: {count} violations")
            report.append("")

            report.append("Detailed Violations:")
            for violation in self.violations:
                report.append(f"  {violation}")
            report.append("")
        else:
            report.append("✓ No architectural boundary violations found!")

        return "\n".join(report)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Check architectural boundaries in Python projects"
    )
    parser.add_argument(
        "source_path", type=Path, help="Path to the source directory to analyze"
    )
    parser.add_argument(
        "--output", type=Path, help="Output file for the report (default: stdout)"
    )
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit with error code if boundary violations are found",
    )

    args = parser.parse_args()

    if not args.source_path.exists():
        print(f"Error: Source path {args.source_path} does not exist")
        sys.exit(1)

    # Analyze the project
    checker = ArchitecturalBoundaryChecker(args.source_path)
    checker.analyze_project()

    # Generate report
    report = checker.generate_report()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    # Exit with error if violations found and --fail-on-violations is set
    if args.fail_on_violations and checker.violations:
        print(
            f"\nError: {len(checker.violations)} architectural boundary violations found!"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
