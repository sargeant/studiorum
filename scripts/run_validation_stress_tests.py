#!/usr/bin/env python3
"""Script to run comprehensive validation stress tests.

This script runs the full suite of data validation stress tests,
including loading all available data and checking for warnings.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"🔬 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")

    start_time = time.time()
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        duration = time.time() - start_time

        print(f"✅ Completed in {duration:.2f}s")
        if result.stdout:
            print("\nOutput:")
            print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"❌ Failed after {duration:.2f}s")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print("\nStdout:")
            print(e.stdout)
        if e.stderr:
            print("\nStderr:")
            print(e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Run validation stress tests")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip slow integration tests)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage reporting"
    )
    args = parser.parse_args()

    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "pyproject.toml").exists():
        print("❌ Must be run from project root directory")
        sys.exit(1)

    print("🧪 VALIDATION STRESS TEST SUITE")
    print(f"Project root: {project_root}")

    # Test configurations
    base_cmd = ["python", "-m", "pytest"]

    if args.coverage:
        base_cmd.extend(["--cov=src", "--cov-report=term-missing"])

    if args.verbose:
        base_cmd.append("-v")

    # Test suites to run
    test_suites = [
        {
            "name": "Model Validation Edge Cases",
            "path": "tests/unit/test_model_validation_edge_cases.py",
            "description": "Test edge cases in model validation",
            "quick": True,
        },
        {
            "name": "Liberal Parsing Tests",
            "path": "tests/unit/test_liberal_parsing.py",
            "description": "Test liberal parsing capabilities",
            "quick": True,
        },
        {
            "name": "Data Validation Stress Tests",
            "path": "tests/unit/test_data_validation_stress.py",
            "description": "Stress test data validation with real data",
            "quick": False,
        },
        {
            "name": "Full Dataset Integration Tests",
            "path": "tests/integration/test_full_dataset_validation.py",
            "description": "Full dataset validation with all available data",
            "quick": False,
        },
    ]

    # Filter test suites based on --quick flag
    if args.quick:
        test_suites = [suite for suite in test_suites if suite["quick"]]
        print("🏃 Running quick tests only")
    else:
        print("🐌 Running all tests including slow integration tests")

    results = []
    total_start = time.time()

    for suite in test_suites:
        cmd = base_cmd + [suite["path"]]
        success = run_command(cmd, suite["description"])
        results.append((suite["name"], success))

        if not success:
            print(f"\n⚠️  {suite['name']} failed!")

    # Summary
    total_duration = time.time() - total_start
    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total time: {total_duration:.2f}s")
    print(f"Passed: {passed}/{total}")

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {name}")

    if passed == total:
        print(f"\n🎉 All {total} test suites passed!")

        # Run additional specific validation tests
        print("\n🔍 Running specific validation checks...")

        # Check for any validation warnings in recent CLI run
        cli_check_cmd = [
            "python",
            "-m",
            "src.cli.main",
            "list",
            "content",
            "--limit",
            "10",
        ]
        print(f"Running CLI validation check: {' '.join(cli_check_cmd)}")

        try:
            result = subprocess.run(
                cli_check_cmd, capture_output=True, text=True, timeout=60
            )
            stderr_lines = result.stderr.split("\n") if result.stderr else []
            warning_lines = [
                line
                for line in stderr_lines
                if "WARNING" in line and "Validation failed" in line
            ]

            if warning_lines:
                print(
                    f"⚠️  Found {len(warning_lines)} validation warnings in CLI output"
                )
                for line in warning_lines[:3]:  # Show first 3
                    print(f"  {line}")
                if len(warning_lines) > 3:
                    print(f"  ... and {len(warning_lines) - 3} more")
            else:
                print("✅ No validation warnings found in CLI output")

        except subprocess.TimeoutExpired:
            print("⚠️  CLI validation check timed out")
        except Exception as e:
            print(f"⚠️  CLI validation check failed: {e}")

        sys.exit(0)
    else:
        print(f"\n💥 {total - passed} test suite(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
