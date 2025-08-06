#!/usr/bin/env python3
"""
Test Quality Metrics Tracker

This script analyzes test code quality and tracks metrics that indicate test health
and effectiveness. It identifies anti-patterns, measures test isolation, and provides
actionable feedback for improving test quality.

Usage:
    python scripts/test_quality_metrics.py [--report] [--check] [--fail-on-issues]

    --report: Generate comprehensive quality report
    --check: Check for specific quality issues
    --fail-on-issues: Exit with error code if quality issues found
"""

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


class TestQualityAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze test code quality."""

    def __init__(self):
        self.issues = []
        self.current_file = ""
        self.current_function = ""
        self.mock_usage = set()
        self.assertions = []
        self.private_access = []
        self.fixture_usage = defaultdict(list)

    def analyze_file(self, file_path: Path) -> dict[str, Any]:
        """Analyze a single test file for quality issues."""
        self.current_file = str(file_path)
        self.issues = []
        self.mock_usage = set()
        self.assertions = []
        self.private_access = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            self.visit(tree)

            # Additional text-based analysis
            self._analyze_text_patterns(content)

            return {
                "file": str(file_path),
                "issues": self.issues,
                "mock_usage": list(self.mock_usage),
                "assertion_count": len(self.assertions),
                "private_access_count": len(self.private_access),
                "fixture_usage": dict(self.fixture_usage),
            }

        except Exception as e:
            return {
                "file": str(file_path),
                "error": f"Failed to analyze: {e}",
                "issues": [],
                "mock_usage": [],
                "assertion_count": 0,
                "private_access_count": 0,
                "fixture_usage": {},
            }

    def visit_FunctionDef(self, node):
        """Analyze function definitions for test patterns."""
        if node.name.startswith("test_"):
            self.current_function = node.name
            self._check_function_quality(node)
        self.generic_visit(node)
        self.current_function = ""

    def visit_Assert(self, node):
        """Analyze assert statements for quality issues."""
        assertion_text = ast.unparse(node) if hasattr(ast, "unparse") else str(node)
        self.assertions.append(assertion_text)

        # Check for false positive assertions
        self._check_false_positive_assertion(node, assertion_text)

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Check for private attribute access."""
        if isinstance(node.attr, str) and node.attr.startswith("_"):
            # Get the full attribute access chain
            attr_chain = self._get_attribute_chain(node)
            if any(part.startswith("_") for part in attr_chain.split(".")):
                self.private_access.append(
                    {
                        "function": self.current_function,
                        "attribute": attr_chain,
                        "line": getattr(node, "lineno", 0),
                    }
                )
                self.issues.append(
                    {
                        "type": "private_attribute_access",
                        "function": self.current_function,
                        "message": f"Accessing private attribute: {attr_chain}",
                        "line": getattr(node, "lineno", 0),
                    }
                )

        self.generic_visit(node)

    def visit_Call(self, node):
        """Analyze function calls for patterns."""
        # Check for mock usage
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ["patch", "Mock", "MagicMock"]:
                self.mock_usage.add(f"{node.func.attr}")
        elif isinstance(node.func, ast.Name):
            if node.func.id in ["mock", "patch", "Mock", "MagicMock"]:
                self.mock_usage.add(f"{node.func.id}")

        self.generic_visit(node)

    def _check_function_quality(self, node):
        """Check test function for quality issues."""
        # Check function length
        line_count = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
        if line_count > 50:
            self.issues.append(
                {
                    "type": "long_test_function",
                    "function": node.name,
                    "message": f"Test function is very long ({line_count} lines). Consider breaking it down.",
                    "line": node.lineno,
                }
            )

        # Check for multiple unrelated assertions (smells like multiple tests in one)
        assertion_count = sum(
            1 for child in ast.walk(node) if isinstance(child, ast.Assert)
        )
        if assertion_count > 10:
            self.issues.append(
                {
                    "type": "too_many_assertions",
                    "function": node.name,
                    "message": f"Test has many assertions ({assertion_count}). Consider splitting into multiple tests.",
                    "line": node.lineno,
                }
            )

    def _check_false_positive_assertion(self, node, assertion_text):
        """Check for assertions that can never fail."""
        # Check for len() >= 0 pattern
        if (
            isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.GtE)
        ):
            if (
                isinstance(node.test.left, ast.Call)
                and isinstance(node.test.left.func, ast.Name)
                and node.test.left.func.id == "len"
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == 0
            ):
                self.issues.append(
                    {
                        "type": "false_positive_assertion",
                        "function": self.current_function,
                        "message": "Assertion 'len(...) >= 0' always passes. Use 'len(...) > 0' instead.",
                        "line": getattr(node, "lineno", 0),
                    }
                )

        # Check for 'is not None' with objects that are never None
        if (
            isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.IsNot)
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value is None
        ):
            # This is a weak check - could be improved with type analysis
            if "len(" in assertion_text or "str(" in assertion_text:
                self.issues.append(
                    {
                        "type": "weak_assertion",
                        "function": self.current_function,
                        "message": f"Weak assertion: {assertion_text}. Consider more specific checks.",
                        "line": getattr(node, "lineno", 0),
                    }
                )

    def _get_attribute_chain(self, node):
        """Get the full attribute access chain (e.g., 'obj.attr.subattr')."""
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    def _analyze_text_patterns(self, content: str):
        """Analyze text patterns that AST parsing might miss."""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for string-based assertions that might be brittle
            if "assert" in line and any(
                pattern in line
                for pattern in [r"\\section{", r"\\begin{", r"\\end{", '"\\', "'\\"]
            ):
                self.issues.append(
                    {
                        "type": "brittle_string_assertion",
                        "function": self._get_current_function_at_line(lines, i),
                        "message": "Brittle LaTeX string assertion. Consider semantic validation.",
                        "line": i,
                    }
                )

            # Check for hardcoded numbers in assertions
            if "assert" in line and re.search(r"== \d{2,}|!= \d{2,}", line):
                self.issues.append(
                    {
                        "type": "magic_number_assertion",
                        "function": self._get_current_function_at_line(lines, i),
                        "message": "Hardcoded number in assertion. Consider making it configurable.",
                        "line": i,
                    }
                )

    def _get_current_function_at_line(self, lines: list[str], line_num: int) -> str:
        """Get the current test function name for a given line number."""
        for i in range(line_num - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("def test_"):
                return line.split("(")[0].replace("def ", "")
        return "unknown"


class TestQualityMetrics:
    """Track and analyze test quality metrics."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dirs = [
            project_root / "tests",
        ]
        self.analyzer = TestQualityAnalyzer()

    def find_test_files(self) -> list[Path]:
        """Find all test files in the project."""
        test_files = []

        for test_dir in self.test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.rglob("test_*.py"))
                test_files.extend(test_dir.rglob("*_test.py"))

        return sorted(test_files)

    def analyze_all_tests(self) -> dict[str, Any]:
        """Analyze all test files and aggregate metrics."""
        test_files = self.find_test_files()

        if not test_files:
            return {"error": "No test files found", "metrics": {}}

        print(f"Analyzing {len(test_files)} test files...")

        all_results = []
        total_issues = []
        mock_usage_files = set()
        private_access_files = set()

        for test_file in test_files:
            print(f"  Analyzing {test_file.relative_to(self.project_root)}")
            result = self.analyzer.analyze_file(test_file)
            all_results.append(result)

            if result.get("issues"):
                total_issues.extend(result["issues"])

            if result.get("mock_usage"):
                mock_usage_files.add(str(test_file))

            if result.get("private_access_count", 0) > 0:
                private_access_files.add(str(test_file))

        # Aggregate metrics
        issue_types = Counter(issue["type"] for issue in total_issues)
        total_assertions = sum(r.get("assertion_count", 0) for r in all_results)

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_test_files": len(test_files),
            "total_issues": len(total_issues),
            "issue_breakdown": dict(issue_types),
            "total_assertions": total_assertions,
            "files_with_mocks": len(mock_usage_files),
            "files_with_private_access": len(private_access_files),
            "quality_score": self._calculate_quality_score(
                len(test_files), len(total_issues)
            ),
            "file_results": all_results,
        }

        return {"metrics": metrics}

    def _calculate_quality_score(self, total_files: int, total_issues: int) -> float:
        """Calculate a quality score (0-100) based on issues found."""
        if total_files == 0:
            return 0.0

        # Start with 100, subtract points for issues
        issues_per_file = total_issues / total_files
        score = max(0.0, 100.0 - (issues_per_file * 10))

        return round(score, 1)

    def generate_report(self, metrics: dict[str, Any]) -> str:
        """Generate a comprehensive quality report."""
        if "error" in metrics:
            return f"Error: {metrics['error']}"

        m = metrics["metrics"]

        report_lines = [
            "# Test Quality Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total Test Files**: {m['total_test_files']}",
            f"- **Quality Score**: {m['quality_score']}/100",
            f"- **Total Issues**: {m['total_issues']}",
            f"- **Total Assertions**: {m['total_assertions']}",
            "",
        ]

        # Issue breakdown
        if m["issue_breakdown"]:
            report_lines.extend(["## Issue Breakdown", ""])

            for issue_type, count in sorted(m["issue_breakdown"].items()):
                issue_name = issue_type.replace("_", " ").title()
                report_lines.append(f"- **{issue_name}**: {count}")

            report_lines.append("")

        # Mock usage analysis
        mock_percentage = (m["files_with_mocks"] / m["total_test_files"]) * 100
        status = "✅" if mock_percentage < 50 else "⚠️" if mock_percentage < 70 else "❌"

        report_lines.extend(
            [
                "## Test Patterns Analysis",
                f"- **Mock Usage**: {status} {m['files_with_mocks']} files ({mock_percentage:.1f}%)",
                f"- **Private Access**: {'⚠️' if m['files_with_private_access'] > 0 else '✅'} {m['files_with_private_access']} files",
                "",
            ]
        )

        # Quality recommendations
        report_lines.extend(["## Recommendations", ""])

        if m["files_with_private_access"] > 0:
            report_lines.append(
                "- 🔧 **Remove private attribute testing** - Focus on public behavior instead"
            )

        if mock_percentage > 50:
            report_lines.append(
                "- 🔧 **Reduce mock usage** - Use real objects with test data when possible"
            )

        false_positives = m["issue_breakdown"].get("false_positive_assertion", 0)
        if false_positives > 0:
            report_lines.append(
                "- 🔧 **Fix false positive assertions** - Replace assertions that always pass"
            )

        brittle_strings = m["issue_breakdown"].get("brittle_string_assertion", 0)
        if brittle_strings > 0:
            report_lines.append(
                "- 🔧 **Replace brittle string assertions** - Use semantic validation for LaTeX"
            )

        if m["quality_score"] < 80:
            report_lines.append(
                "- 📈 **Overall quality improvement needed** - Focus on top issue types"
            )

        report_lines.append("")

        # Top problematic files
        problematic_files = []
        for result in m["file_results"]:
            if result.get("issues"):
                issue_count = len(result["issues"])
                problematic_files.append((result["file"], issue_count))

        if problematic_files:
            problematic_files.sort(key=lambda x: x[1], reverse=True)

            report_lines.extend(["## Files Needing Attention", ""])

            for file_path, issue_count in problematic_files[:10]:  # Top 10
                relative_path = Path(file_path).relative_to(self.project_root)
                report_lines.append(f"- **{relative_path}**: {issue_count} issues")

            report_lines.append("")

        return "\n".join(report_lines)

    def check_quality_gates(self, metrics: dict[str, Any]) -> tuple[bool, list[str]]:
        """Check if quality gates are met."""
        if "error" in metrics:
            return False, [metrics["error"]]

        m = metrics["metrics"]
        failures = []

        # Quality gates
        if m["quality_score"] < 70:
            failures.append(
                f"Quality score too low: {m['quality_score']}/100 (minimum: 70)"
            )

        if m["files_with_private_access"] > 0:
            failures.append(
                f"Private attribute access found in {m['files_with_private_access']} files"
            )

        false_positives = m["issue_breakdown"].get("false_positive_assertion", 0)
        if false_positives > 0:
            failures.append(f"False positive assertions found: {false_positives}")

        mock_percentage = (m["files_with_mocks"] / m["total_test_files"]) * 100
        if mock_percentage > 60:
            failures.append(
                f"Too much mock usage: {mock_percentage:.1f}% of files (limit: 60%)"
            )

        return len(failures) == 0, failures


def main():
    """Main entry point for test quality metrics."""
    parser = argparse.ArgumentParser(
        description="Analyze test code quality and track metrics"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate comprehensive quality report"
    )
    parser.add_argument("--check", action="store_true", help="Check quality gates")
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with error code if quality issues found",
    )

    args = parser.parse_args()

    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    quality_tracker = TestQualityMetrics(project_root)

    print("Analyzing test quality...")
    metrics = quality_tracker.analyze_all_tests()

    if args.report or not (args.check or args.fail_on_issues):
        report = quality_tracker.generate_report(metrics)
        print(report)

        # Also save to file for CI
        with open("test-quality-report.txt", "w") as f:
            f.write(report)

    if args.check or args.fail_on_issues:
        passed, failures = quality_tracker.check_quality_gates(metrics)

        if passed:
            print("✅ All quality gates passed")
            return 0
        else:
            print("❌ Quality gate failures:")
            for failure in failures:
                print(f"  - {failure}")

            if args.fail_on_issues:
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
