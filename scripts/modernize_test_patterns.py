#!/usr/bin/env python3
"""Identify and suggest modernization for test patterns."""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional


class TestModernizationAnalyzer(ast.NodeVisitor):
    """AST visitor to identify legacy patterns in tests."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        """Analyze function definitions."""
        old_function = self.current_function
        self.current_function = node.name

        # Check for test methods
        if node.name.startswith("test_"):
            self._check_assertions(node)
            self._check_fixture_patterns(node)
            self._check_setup_patterns(node)

        self.generic_visit(node)
        self.current_function = old_function

    def _check_assertions(self, node):
        """Check for outdated assertion patterns."""
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                # Check for assert x == y without message
                if isinstance(child.test, ast.Compare):
                    if not child.msg:
                        self.issues.append(
                            {
                                "type": "assertion_no_message",
                                "function": node.name,
                                "line": child.lineno,
                                "suggestion": "Add descriptive message to assertion",
                            }
                        )

                    # Check for assert len(x) > 0
                    if (
                        isinstance(child.test.left, ast.Call)
                        and isinstance(child.test.left.func, ast.Name)
                        and child.test.left.func.id == "len"
                    ):
                        self.issues.append(
                            {
                                "type": "assert_len_check",
                                "function": node.name,
                                "line": child.lineno,
                                "suggestion": 'Use "assert x" instead of "assert len(x) > 0"',
                            }
                        )

                # Check for assert x is not None
                if (
                    isinstance(child.test, ast.Compare)
                    and isinstance(child.test.ops[0], ast.IsNot)
                    and isinstance(child.test.comparators[0], ast.Constant)
                    and child.test.comparators[0].value is None
                ):
                    self.issues.append(
                        {
                            "type": "assert_is_not_none",
                            "function": node.name,
                            "line": child.lineno,
                            "suggestion": 'Consider using "assert x" if checking for truthiness',
                        }
                    )

    def _check_fixture_patterns(self, node):
        """Check for outdated fixture patterns."""
        # Check for yield fixtures (now deprecated in favor of context managers)
        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield):
                self.issues.append(
                    {
                        "type": "yield_fixture",
                        "function": node.name,
                        "line": stmt.lineno,
                        "suggestion": "Use context manager pattern instead of yield",
                    }
                )

    def _check_setup_patterns(self, node):
        """Check for setup/teardown patterns that could be fixtures."""
        if node.name in [
            "setup_method",
            "teardown_method",
            "setup_class",
            "teardown_class",
        ]:
            self.issues.append(
                {
                    "type": "setup_teardown_method",
                    "function": node.name,
                    "line": node.lineno,
                    "suggestion": "Consider converting to pytest fixtures for better isolation",
                }
            )


def analyze_test_file(filepath: Path) -> dict:
    """Analyze a single test file for modernization opportunities."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
            tree = ast.parse(content)

        analyzer = TestModernizationAnalyzer(str(filepath))
        analyzer.visit(tree)

        # Also check for string patterns
        lines = content.split("\n")
        string_issues = analyze_string_patterns(lines)

        return {
            "filepath": str(filepath),
            "ast_issues": analyzer.issues,
            "string_issues": string_issues,
            "total_issues": len(analyzer.issues) + len(string_issues),
        }
    except Exception as e:
        return {
            "filepath": str(filepath),
            "error": str(e),
            "ast_issues": [],
            "string_issues": [],
            "total_issues": 0,
        }


def analyze_string_patterns(lines: list[str]) -> list[dict]:
    """Analyze string patterns for modernization opportunities."""
    issues = []

    for i, line in enumerate(lines, 1):
        # Check for unittest style assertions
        if (
            "self.assertEqual" in line
            or "self.assertTrue" in line
            or "self.assertFalse" in line
        ):
            issues.append(
                {
                    "type": "unittest_assertion",
                    "line": i,
                    "content": line.strip(),
                    "suggestion": "Use pytest assertions instead of unittest style",
                }
            )

        # Check for try/except in tests (usually antipattern)
        if line.strip().startswith("try:") or line.strip().startswith("except"):
            issues.append(
                {
                    "type": "try_except_in_test",
                    "line": i,
                    "content": line.strip(),
                    "suggestion": "Use pytest.raises() for exception testing",
                }
            )

        # Check for print statements in tests
        if "print(" in line and not line.strip().startswith("#"):
            issues.append(
                {
                    "type": "print_statement",
                    "line": i,
                    "content": line.strip(),
                    "suggestion": "Remove print statements or use logging",
                }
            )

        # Check for time.sleep in tests
        if "time.sleep" in line:
            issues.append(
                {
                    "type": "sleep_in_test",
                    "line": i,
                    "content": line.strip(),
                    "suggestion": "Avoid time.sleep; use proper synchronization",
                }
            )

    return issues


def generate_modernization_examples() -> str:
    """Generate examples of modernized patterns."""
    return """
MODERNIZATION EXAMPLES
======================

1. Assertions with Messages
----------------------------
OLD:
    assert result == expected

NEW:
    assert result == expected, f"Expected {expected}, got {result}"

2. Length Checks
----------------
OLD:
    assert len(items) > 0

NEW:
    assert items, "Expected non-empty items"

3. None Checks
--------------
OLD:
    assert obj is not None

NEW:
    assert obj, "Object should not be None"

4. Setup/Teardown → Fixtures
-----------------------------
OLD:
    def setup_method(self):
        self.data = load_data()

    def teardown_method(self):
        cleanup_data()

NEW:
    @pytest.fixture
    def data(self):
        data = load_data()
        yield data
        cleanup_data()

5. Exception Testing
--------------------
OLD:
    try:
        dangerous_function()
        assert False, "Should have raised"
    except ValueError:
        pass

NEW:
    with pytest.raises(ValueError):
        dangerous_function()

6. Parametrized Tests
---------------------
OLD:
    def test_case_1(self): ...
    def test_case_2(self): ...
    def test_case_3(self): ...

NEW:
    @pytest.mark.parametrize("case", [1, 2, 3])
    def test_cases(self, case): ...
"""


def main():
    """Main modernization analysis."""
    test_dir = Path("tests")
    test_files = list(test_dir.rglob("test_*.py"))

    print(
        f"Analyzing {len(test_files)} test files for modernization opportunities...\n"
    )

    # Analyze all test files
    all_results = []
    issue_counts = defaultdict(int)

    for filepath in test_files:
        result = analyze_test_file(filepath)
        all_results.append(result)

        # Count issue types
        for issue in result["ast_issues"] + result["string_issues"]:
            issue_counts[issue["type"]] += 1

    # Sort files by number of issues
    files_with_issues = [r for r in all_results if r["total_issues"] > 0]
    files_with_issues.sort(key=lambda x: x["total_issues"], reverse=True)

    # Print report
    print("=" * 70)
    print("TEST MODERNIZATION REPORT")
    print("=" * 70)

    print("\n📊 Summary:")
    print(f"  Files analyzed: {len(test_files)}")
    print(f"  Files with issues: {len(files_with_issues)}")
    print(f"  Total issues found: {sum(r['total_issues'] for r in all_results)}")

    if issue_counts:
        print("\n📈 Issue Types:")
        for issue_type, count in sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {issue_type}: {count}")

    if files_with_issues:
        print("\n🔥 Top Files Needing Modernization:")
        print("-" * 70)

        for result in files_with_issues[:10]:
            filepath = Path(result["filepath"])
            print(f"\n{filepath.name} ({result['total_issues']} issues)")

            # Show first few issues
            all_issues = result["ast_issues"] + result["string_issues"]
            for issue in all_issues[:3]:
                print(f"  Line {issue.get('line', '?')}: {issue['type']}")
                if "suggestion" in issue:
                    print(f"    → {issue['suggestion']}")

    # Recommendations
    print("\n💡 Recommendations:")
    print("-" * 70)

    if issue_counts.get("assertion_no_message", 0) > 50:
        print(
            "⚠️  Many assertions lack descriptive messages - add context for better debugging"
        )

    if issue_counts.get("setup_teardown_method", 0) > 20:
        print("🔧 Convert setup/teardown methods to fixtures for better test isolation")

    if issue_counts.get("unittest_assertion", 0) > 0:
        print("🔄 Migrate from unittest assertions to pytest assertions")

    if issue_counts.get("try_except_in_test", 0) > 0:
        print("⚡ Use pytest.raises() for exception testing instead of try/except")

    # Print examples
    print(generate_modernization_examples())

    # Generate migration script snippet
    print("\n📝 Quick Migration Script:")
    print("-" * 70)
    print("""
# Run these commands to apply common fixes:

# Add assertion messages
find tests -name "*.py" -exec sed -i '' 's/assert \\(.*\\) == \\(.*\\)$/assert \\1 == \\2, f"Expected {\\2}, got {\\1}"/' {} \\;

# Replace len checks
find tests -name "*.py" -exec sed -i '' 's/assert len(\\(.*\\)) > 0/assert \\1, "Expected non-empty"/' {} \\;

# Remove print statements
find tests -name "*.py" -exec sed -i '' '/print(/d' {} \\;
""")


if __name__ == "__main__":
    main()
