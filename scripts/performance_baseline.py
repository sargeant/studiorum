#!/usr/bin/env python3
"""Performance Baseline Management - Create and compare test performance baselines."""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class PerformanceBaseline:
    """Manage test performance baselines."""

    def __init__(self):
        """Initialize baseline manager."""
        self.baseline_path = Path(".test-performance-baseline.json")
        self.report_path = Path(".test-performance-report.json")
        self.history_path = Path(".test-performance-history.json")

    def create_baseline(self, test_args: list[str] = None) -> bool:
        """Create a new performance baseline.

        Args:
            test_args: Additional pytest arguments

        Returns:
            True if baseline was created successfully
        """
        print("Creating performance baseline...")

        # Run tests with profiling enabled
        cmd = ["uv", "run", "pytest", "--profile"]
        if test_args:
            cmd.extend(test_args)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Tests failed with return code {result.returncode}")
            print(result.stderr)
            return False

        # Load the generated report
        if not self.report_path.exists():
            print("Performance report not generated")
            return False

        with open(self.report_path, "r") as f:
            report = json.load(f)

        # Save as baseline
        baseline = {
            "created": datetime.now().isoformat(),
            "test_count": report["total_tests"],
            "total_duration": report["total_duration"],
            "metrics": report["metrics"],
        }

        # Backup existing baseline if it exists
        if self.baseline_path.exists():
            backup_path = Path(
                f".test-performance-baseline-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            )
            self.baseline_path.rename(backup_path)
            print(f"Previous baseline backed up to: {backup_path}")

        with open(self.baseline_path, "w") as f:
            json.dump(baseline, f, indent=2)

        print(f"✓ Baseline created with {baseline['test_count']} tests")
        print(f"  Total duration: {baseline['total_duration']:.2f}s")

        return True

    def compare_with_baseline(self, tolerance: float = 0.2) -> tuple[bool, list[dict]]:
        """Compare current performance with baseline.

        Args:
            tolerance: Acceptable regression threshold (0.2 = 20% slower)

        Returns:
            Tuple of (passed, regressions)
        """
        if not self.baseline_path.exists():
            print("No baseline found. Create one with --create-baseline")
            return False, []

        if not self.report_path.exists():
            print("No current report found. Run tests with --profile first")
            return False, []

        with open(self.baseline_path, "r") as f:
            baseline = json.load(f)

        with open(self.report_path, "r") as f:
            current = json.load(f)

        regressions = []
        improvements = []
        baseline_metrics = baseline["metrics"]
        current_metrics = current["metrics"]

        for test_id, current_data in current_metrics.items():
            if test_id in baseline_metrics:
                baseline_time = baseline_metrics[test_id]["duration"]
                current_time = current_data["duration"]

                diff_pct = ((current_time / baseline_time) - 1) * 100

                if current_time > baseline_time * (1 + tolerance):
                    regressions.append(
                        {
                            "test": test_id,
                            "baseline": baseline_time,
                            "current": current_time,
                            "regression_percent": diff_pct,
                        }
                    )
                elif current_time < baseline_time * 0.8:  # 20% faster
                    improvements.append(
                        {
                            "test": test_id,
                            "baseline": baseline_time,
                            "current": current_time,
                            "improvement_percent": -diff_pct,
                        }
                    )

        # Print summary
        print(f"\n{'=' * 60}")
        print("PERFORMANCE COMPARISON")
        print(f"{'=' * 60}\n")

        print(f"Baseline created: {baseline['created']}")
        print(f"Tests compared: {len(current_metrics)}")

        if regressions:
            print(
                f"\n⚠️  {len(regressions)} Performance Regressions (>{tolerance * 100:.0f}% slower):"
            )
            for reg in sorted(
                regressions, key=lambda x: x["regression_percent"], reverse=True
            )[:5]:
                test_name = reg["test"].split("::")[-1]
                print(f"  - {test_name}: {reg['regression_percent']:.1f}% slower")
                print(f"    ({reg['baseline']:.3f}s → {reg['current']:.3f}s)")

        if improvements:
            print(f"\n✓ {len(improvements)} Performance Improvements (>20% faster):")
            for imp in sorted(
                improvements, key=lambda x: x["improvement_percent"], reverse=True
            )[:5]:
                test_name = imp["test"].split("::")[-1]
                print(f"  + {test_name}: {imp['improvement_percent']:.1f}% faster")
                print(f"    ({imp['baseline']:.3f}s → {imp['current']:.3f}s)")

        # Overall comparison
        baseline_total = baseline["total_duration"]
        current_total = current["total_duration"]
        total_diff_pct = ((current_total / baseline_total) - 1) * 100

        print("\nOverall Performance:")
        print(f"  Baseline: {baseline_total:.2f}s")
        print(f"  Current:  {current_total:.2f}s")
        print(f"  Change:   {total_diff_pct:+.1f}%")

        if total_diff_pct > tolerance * 100:
            print("\n❌ Overall performance regression detected!")
        elif total_diff_pct < -20:
            print("\n✅ Significant overall performance improvement!")
        else:
            print("\n✓ Performance within acceptable range")

        return len(regressions) == 0, regressions

    def track_history(self) -> None:
        """Track performance over time."""
        if not self.report_path.exists():
            print("No current report found")
            return

        with open(self.report_path, "r") as f:
            current = json.load(f)

        # Load or create history
        if self.history_path.exists():
            with open(self.history_path, "r") as f:
                history = json.load(f)
        else:
            history = {"entries": []}

        # Add current entry
        entry = {
            "timestamp": current["timestamp"],
            "total_tests": current["total_tests"],
            "total_duration": current["total_duration"],
            "total_memory_mb": current["total_memory_mb"],
            "slow_test_count": len(current.get("slow_tests", [])),
            "memory_intensive_count": len(current.get("memory_intensive_tests", [])),
        }

        history["entries"].append(entry)

        # Keep only last 100 entries
        if len(history["entries"]) > 100:
            history["entries"] = history["entries"][-100:]

        with open(self.history_path, "w") as f:
            json.dump(history, f, indent=2)

        print(f"Performance history updated ({len(history['entries'])} entries)")

    def show_trends(self, last_n: int = 10) -> None:
        """Show performance trends over time.

        Args:
            last_n: Number of recent entries to show
        """
        if not self.history_path.exists():
            print("No performance history found")
            return

        with open(self.history_path, "r") as f:
            history = json.load(f)

        entries = history["entries"][-last_n:]

        if not entries:
            print("No history entries found")
            return

        print(f"\n{'=' * 60}")
        print(f"PERFORMANCE TRENDS (Last {len(entries)} runs)")
        print(f"{'=' * 60}\n")

        # Calculate trends
        durations = [e["total_duration"] for e in entries]
        memory_usage = [e["total_memory_mb"] for e in entries]
        slow_counts = [e["slow_test_count"] for e in entries]

        avg_duration = sum(durations) / len(durations)
        avg_memory = sum(memory_usage) / len(memory_usage)
        avg_slow = sum(slow_counts) / len(slow_counts)

        # Show recent performance
        print("Recent Performance:")
        for entry in entries[-5:]:
            timestamp = entry["timestamp"].split("T")[0]
            duration = entry["total_duration"]
            trend = "↑" if duration > avg_duration else "↓"
            print(f"  {timestamp}: {duration:.2f}s {trend}")

        print(f"\nAverages (last {len(entries)} runs):")
        print(f"  Duration: {avg_duration:.2f}s")
        print(f"  Memory:   {avg_memory:.2f} MB")
        print(f"  Slow tests: {avg_slow:.1f}")

        # Trend analysis
        if len(entries) >= 3:
            recent_avg = sum(durations[-3:]) / 3
            older_avg = sum(durations[:-3]) / (len(durations) - 3)
            trend_pct = ((recent_avg / older_avg) - 1) * 100

            if abs(trend_pct) > 5:
                trend_str = "getting slower ⚠️" if trend_pct > 0 else "improving ✓"
                print(f"\nTrend: Tests are {trend_str} ({trend_pct:+.1f}%)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage test performance baselines")

    parser.add_argument(
        "--create-baseline",
        action="store_true",
        help="Create a new performance baseline",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare current performance with baseline",
    )
    parser.add_argument(
        "--track", action="store_true", help="Track performance history"
    )
    parser.add_argument("--trends", action="store_true", help="Show performance trends")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.2,
        help="Regression tolerance (default: 0.2 = 20%%)",
    )
    parser.add_argument("test_args", nargs="*", help="Additional pytest arguments")

    args = parser.parse_args()

    baseline = PerformanceBaseline()

    if args.create_baseline:
        success = baseline.create_baseline(args.test_args)
        sys.exit(0 if success else 1)

    if args.compare:
        passed, regressions = baseline.compare_with_baseline(args.tolerance)
        sys.exit(0 if passed else 1)

    if args.track:
        baseline.track_history()

    if args.trends:
        baseline.show_trends()

    if not any([args.create_baseline, args.compare, args.track, args.trends]):
        parser.print_help()


if __name__ == "__main__":
    main()
