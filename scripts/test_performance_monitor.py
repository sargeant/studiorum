#!/usr/bin/env python3
"""
Test Performance Monitoring Script

This script monitors test execution performance and tracks metrics over time.
It provides insights into test execution time trends, memory usage, and potential
performance regressions.

Usage:
    python scripts/test_performance_monitor.py [--baseline] [--report] [--threshold=5.0]

    --baseline: Create a new performance baseline
    --report: Generate performance report
    --threshold: Performance regression threshold in seconds (default: 5.0)
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import psutil


class TestPerformanceMonitor:
    """Monitor and track test performance metrics."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.metrics_file = project_root / "tests" / "performance_metrics.json"
        self.baseline_file = project_root / "tests" / "performance_baseline.json"

    def run_tests_with_timing(self, test_type: str = "fast") -> dict[str, Any]:
        """Run tests and collect timing/memory metrics."""
        print(f"Running {test_type} tests with performance monitoring...")

        # Get initial system state
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        start_time = time.time()

        # Run tests with detailed timing
        cmd = ["uv", "run", "pytest"]
        if test_type == "fast":
            cmd.extend(["-m", "not slow"])
        cmd.extend(
            [
                "--tb=short",
                "--durations=20",  # Show 20 slowest tests
                "-v",
                "--json-report",
                "--json-report-file=test_results.json",
            ]
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out after 10 minutes",
                "timestamp": datetime.now().isoformat(),
            }

        end_time = time.time()
        final_memory = process.memory_info().rss

        # Parse test results
        test_results = self._parse_test_results()

        metrics = {
            "test_type": test_type,
            "timestamp": datetime.now().isoformat(),
            "total_duration": end_time - start_time,
            "memory_usage": {
                "initial_mb": initial_memory / (1024 * 1024),
                "final_mb": final_memory / (1024 * 1024),
                "increase_mb": (final_memory - initial_memory) / (1024 * 1024),
            },
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            **test_results,
        }

        # Clean up temporary files
        temp_file = self.project_root / "test_results.json"
        if temp_file.exists():
            temp_file.unlink()

        return metrics

    def _parse_test_results(self) -> dict[str, Any]:
        """Parse pytest JSON output for detailed test metrics."""
        results_file = self.project_root / "test_results.json"

        if not results_file.exists():
            return {
                "test_count": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "slowest_tests": [],
            }

        try:
            with open(results_file) as f:
                data = json.load(f)

            summary = data.get("summary", {})
            tests = data.get("tests", [])

            # Find slowest tests
            test_durations = []
            for test in tests:
                if "duration" in test:
                    test_durations.append(
                        {
                            "name": test.get("nodeid", "unknown"),
                            "duration": test["duration"],
                            "outcome": test.get("outcome", "unknown"),
                        }
                    )

            slowest_tests = sorted(
                test_durations, key=lambda x: x["duration"], reverse=True
            )[:10]  # Top 10 slowest

            return {
                "test_count": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "slowest_tests": slowest_tests,
            }

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not parse test results: {e}")
            return {
                "test_count": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "slowest_tests": [],
            }

    def save_metrics(self, metrics: dict[str, Any]) -> None:
        """Save performance metrics to history file."""
        history = []

        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    history = json.load(f)
            except (json.JSONDecodeError, KeyError):
                history = []

        history.append(metrics)

        # Keep only last 50 runs to avoid file size growth
        history = history[-50:]

        # Ensure directory exists
        self.metrics_file.parent.mkdir(exist_ok=True)

        with open(self.metrics_file, "w") as f:
            json.dump(history, f, indent=2)

        print(f"Metrics saved to {self.metrics_file}")

    def create_baseline(self) -> dict[str, Any]:
        """Create a new performance baseline."""
        print("Creating performance baseline...")

        # Run both fast and slow tests for baseline
        fast_metrics = self.run_tests_with_timing("fast")
        time.sleep(2)  # Brief pause between test runs
        slow_metrics = self.run_tests_with_timing("all")

        baseline = {
            "created": datetime.now().isoformat(),
            "fast_tests": fast_metrics,
            "all_tests": slow_metrics,
        }

        # Ensure directory exists
        self.baseline_file.parent.mkdir(exist_ok=True)

        with open(self.baseline_file, "w") as f:
            json.dump(baseline, f, indent=2)

        print(f"Baseline saved to {self.baseline_file}")
        return baseline

    def check_regression(
        self, current_metrics: dict[str, Any], threshold: float = 5.0
    ) -> list[str]:
        """Check for performance regressions against baseline."""
        if not self.baseline_file.exists():
            return ["No baseline found. Create one with --baseline"]

        try:
            with open(self.baseline_file) as f:
                baseline = json.load(f)
        except (json.JSONDecodeError, KeyError):
            return ["Could not load baseline file"]

        issues = []
        test_type = current_metrics.get("test_type", "fast")
        baseline_key = "fast_tests" if test_type == "fast" else "all_tests"

        if baseline_key not in baseline:
            return [f"No baseline data for {test_type} tests"]

        baseline_metrics = baseline[baseline_key]

        # Check total duration regression
        baseline_duration = baseline_metrics.get("total_duration", 0)
        current_duration = current_metrics.get("total_duration", 0)

        if current_duration > baseline_duration + threshold:
            issues.append(
                f"Performance regression detected: {current_duration:.2f}s vs baseline {baseline_duration:.2f}s "
                f"(+{current_duration - baseline_duration:.2f}s)"
            )

        # Check memory usage regression
        baseline_memory = baseline_metrics.get("memory_usage", {}).get("increase_mb", 0)
        current_memory = current_metrics.get("memory_usage", {}).get("increase_mb", 0)

        if current_memory > baseline_memory + 50:  # 50MB threshold
            issues.append(
                f"Memory usage regression: {current_memory:.1f}MB vs baseline {baseline_memory:.1f}MB "
                f"(+{current_memory - baseline_memory:.1f}MB)"
            )

        # Check for new test failures
        baseline_failed = baseline_metrics.get("failed", 0)
        current_failed = current_metrics.get("failed", 0)

        if current_failed > baseline_failed:
            issues.append(
                f"Test failure regression: {current_failed} failed vs baseline {baseline_failed} failed"
            )

        return issues

    def generate_report(self) -> str:
        """Generate a performance report from historical data."""
        if not self.metrics_file.exists():
            return "No performance metrics found. Run tests with monitoring first."

        try:
            with open(self.metrics_file) as f:
                history = json.load(f)
        except (json.JSONDecodeError, KeyError):
            return "Could not load performance metrics file"

        if not history:
            return "No performance data available"

        latest = history[-1]

        report_lines = [
            "# Test Performance Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Latest Test Run",
            f"- **Timestamp**: {latest.get('timestamp', 'unknown')}",
            f"- **Test Type**: {latest.get('test_type', 'unknown')}",
            f"- **Duration**: {latest.get('total_duration', 0):.2f} seconds",
            f"- **Tests**: {latest.get('test_count', 0)} total, {latest.get('passed', 0)} passed, {latest.get('failed', 0)} failed",
            f"- **Memory Usage**: {latest.get('memory_usage', {}).get('increase_mb', 0):.1f}MB increase",
            "",
        ]

        # Add slowest tests if available
        slowest = latest.get("slowest_tests", [])
        if slowest:
            report_lines.extend(["## Slowest Tests", ""])
            for i, test in enumerate(slowest[:5], 1):
                name = (
                    test["name"].split("::")[-1]
                    if "::" in test["name"]
                    else test["name"]
                )
                report_lines.append(f"{i}. **{name}**: {test['duration']:.3f}s")
            report_lines.append("")

        # Performance trends over last 10 runs
        if len(history) > 1:
            recent_history = history[-10:]
            durations = [run.get("total_duration", 0) for run in recent_history]
            memory_usage = [
                run.get("memory_usage", {}).get("increase_mb", 0)
                for run in recent_history
            ]

            avg_duration = sum(durations) / len(durations)
            avg_memory = sum(memory_usage) / len(memory_usage)

            report_lines.extend(
                [
                    "## Performance Trends (Last 10 Runs)",
                    f"- **Average Duration**: {avg_duration:.2f} seconds",
                    f"- **Average Memory**: {avg_memory:.1f}MB increase",
                    "",
                ]
            )

            # Check for trends
            if len(durations) >= 5:
                recent_avg = sum(durations[-3:]) / 3
                older_avg = sum(durations[-6:-3]) / 3

                if recent_avg > older_avg * 1.2:
                    report_lines.append(
                        "⚠️  **Warning**: Test execution time appears to be increasing"
                    )
                elif recent_avg < older_avg * 0.8:
                    report_lines.append(
                        "✅ **Good**: Test execution time appears to be decreasing"
                    )

                report_lines.append("")

        # Performance budget status
        PERFORMANCE_BUDGETS = {
            "fast_tests_duration": 30.0,  # 30 seconds for fast tests
            "all_tests_duration": 300.0,  # 5 minutes for all tests
            "memory_increase": 100.0,  # 100MB memory increase limit
        }

        report_lines.extend(["## Performance Budget Status", ""])

        test_type = latest.get("test_type", "fast")
        duration = latest.get("total_duration", 0)
        memory = latest.get("memory_usage", {}).get("increase_mb", 0)

        budget_key = f"{test_type}_tests_duration"
        if test_type == "all":
            budget_key = "all_tests_duration"

        duration_budget = PERFORMANCE_BUDGETS.get(budget_key, 60.0)
        memory_budget = PERFORMANCE_BUDGETS["memory_increase"]

        duration_status = "✅" if duration <= duration_budget else "❌"
        memory_status = "✅" if memory <= memory_budget else "❌"

        report_lines.extend(
            [
                f"- **Duration Budget**: {duration_status} {duration:.1f}s / {duration_budget}s",
                f"- **Memory Budget**: {memory_status} {memory:.1f}MB / {memory_budget}MB",
                "",
            ]
        )

        return "\n".join(report_lines)


def main():
    """Main entry point for the performance monitoring script."""
    parser = argparse.ArgumentParser(
        description="Monitor and track test performance metrics"
    )
    parser.add_argument(
        "--baseline", action="store_true", help="Create a new performance baseline"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate performance report"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Performance regression threshold in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--test-type",
        choices=["fast", "all"],
        default="fast",
        help="Type of tests to run (default: fast)",
    )

    args = parser.parse_args()

    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    monitor = TestPerformanceMonitor(project_root)

    if args.baseline:
        monitor.create_baseline()
        print("✅ Performance baseline created successfully")
        return 0

    if args.report:
        report = monitor.generate_report()
        print(report)
        return 0

    # Run performance monitoring
    print(f"Running {args.test_type} tests with performance monitoring...")
    metrics = monitor.run_tests_with_timing(args.test_type)

    if not metrics.get("success", False):
        print(f"❌ Tests failed with exit code {metrics.get('exit_code', 'unknown')}")
        if "error" in metrics:
            print(f"Error: {metrics['error']}")
        return 1

    # Save metrics
    monitor.save_metrics(metrics)

    # Check for regressions
    regressions = monitor.check_regression(metrics, args.threshold)
    if regressions:
        print("\n⚠️  Performance Issues Detected:")
        for issue in regressions:
            print(f"  - {issue}")
        return 1

    print(
        f"\n✅ Tests completed successfully in {metrics.get('total_duration', 0):.2f}s"
    )
    print(
        f"📊 Memory usage: {metrics.get('memory_usage', {}).get('increase_mb', 0):.1f}MB increase"
    )
    print(
        f"📈 Tests: {metrics.get('passed', 0)} passed, {metrics.get('failed', 0)} failed, {metrics.get('skipped', 0)} skipped"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
