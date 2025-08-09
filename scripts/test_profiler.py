#!/usr/bin/env python3
"""Test Performance Profiler - Advanced performance monitoring for pytest.

This plugin provides detailed performance profiling for test execution,
including execution time, memory usage, and performance regression detection.
"""

import json
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter


@dataclass
class TestMetrics:
    """Metrics for a single test execution."""

    test_id: str
    duration: float
    memory_delta: int  # bytes
    setup_time: float = 0.0
    teardown_time: float = 0.0
    call_time: float = 0.0
    cpu_percent: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_time(self) -> float:
        """Total execution time including setup and teardown."""
        return self.setup_time + self.call_time + self.teardown_time

    @property
    def memory_mb(self) -> float:
        """Memory delta in megabytes."""
        return self.memory_delta / (1024 * 1024)


class TestProfilerPlugin:
    """Pytest plugin for test performance profiling."""

    # Performance thresholds
    SLOW_TEST_THRESHOLD = 1.0  # seconds
    HIGH_MEMORY_THRESHOLD = 50 * 1024 * 1024  # 50 MB
    REGRESSION_THRESHOLD = 1.2  # 20% slower is considered regression

    def __init__(self, config: Config):
        """Initialize the profiler plugin.

        Args:
            config: Pytest configuration
        """
        self.config = config
        self.metrics: dict[str, TestMetrics] = {}
        self.baseline_path = Path(".test-performance-baseline.json")
        self.report_path = Path(".test-performance-report.json")

        # Timing tracking
        self._start_times: dict[str, float] = {}
        self._phase_times: dict[str, dict[str, float]] = {}

        # Memory tracking
        self._start_memory: dict[str, int] = {}
        self._process = psutil.Process()

        # Enable memory tracing
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: Item) -> None:
        """Called before test setup."""
        test_id = item.nodeid
        self._phase_times[test_id] = {}
        self._start_times[test_id] = time.perf_counter()
        self._start_memory[test_id] = self._process.memory_info().rss

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_call(self, item: Item) -> None:
        """Called before test execution."""
        test_id = item.nodeid
        # Record setup time
        if test_id in self._start_times:
            self._phase_times[test_id]["setup"] = (
                time.perf_counter() - self._start_times[test_id]
            )
        self._start_times[test_id] = time.perf_counter()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_teardown(self, item: Item) -> None:
        """Called before test teardown."""
        test_id = item.nodeid
        # Record call time
        if test_id in self._start_times:
            self._phase_times[test_id]["call"] = (
                time.perf_counter() - self._start_times[test_id]
            )
        self._start_times[test_id] = time.perf_counter()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: Item, call) -> None:
        """Process test results and collect metrics."""
        outcome = yield
        report: TestReport = outcome.get_result()

        if report.when == "teardown":
            test_id = item.nodeid

            # Calculate teardown time
            if test_id in self._start_times:
                self._phase_times[test_id]["teardown"] = (
                    time.perf_counter() - self._start_times[test_id]
                )

            # Calculate total metrics
            if test_id in self._phase_times:
                phases = self._phase_times[test_id]
                memory_end = self._process.memory_info().rss
                memory_start = self._start_memory.get(test_id, memory_end)

                metrics = TestMetrics(
                    test_id=test_id,
                    duration=sum(phases.values()),
                    memory_delta=memory_end - memory_start,
                    setup_time=phases.get("setup", 0.0),
                    call_time=phases.get("call", 0.0),
                    teardown_time=phases.get("teardown", 0.0),
                    cpu_percent=self._process.cpu_percent(),
                )

                self.metrics[test_id] = metrics

                # Clean up tracking data
                self._cleanup_test_data(test_id)

    def _cleanup_test_data(self, test_id: str) -> None:
        """Clean up tracking data for a test."""
        self._start_times.pop(test_id, None)
        self._phase_times.pop(test_id, None)
        self._start_memory.pop(test_id, None)

    def pytest_sessionfinish(self, session) -> None:
        """Called after all tests have run."""
        self._generate_performance_report()
        self._check_performance_regressions()
        self._print_summary()

    def _generate_performance_report(self) -> None:
        """Generate detailed performance report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.metrics),
            "total_duration": sum(m.duration for m in self.metrics.values()),
            "total_memory_mb": sum(m.memory_mb for m in self.metrics.values()),
            "metrics": {
                test_id: {
                    "duration": metrics.duration,
                    "memory_mb": metrics.memory_mb,
                    "setup_time": metrics.setup_time,
                    "call_time": metrics.call_time,
                    "teardown_time": metrics.teardown_time,
                    "cpu_percent": metrics.cpu_percent,
                    "timestamp": metrics.timestamp,
                }
                for test_id, metrics in self.metrics.items()
            },
            "slow_tests": self._identify_slow_tests(),
            "memory_intensive_tests": self._identify_memory_intensive_tests(),
            "performance_hotspots": self._identify_hotspots(),
        }

        with open(self.report_path, "w") as f:
            json.dump(report, f, indent=2)

    def _identify_slow_tests(self) -> list[dict]:
        """Identify tests that exceed the slow threshold."""
        slow_tests = []
        for test_id, metrics in self.metrics.items():
            if metrics.duration > self.SLOW_TEST_THRESHOLD:
                slow_tests.append(
                    {
                        "test": test_id,
                        "duration": metrics.duration,
                        "phases": {
                            "setup": metrics.setup_time,
                            "call": metrics.call_time,
                            "teardown": metrics.teardown_time,
                        },
                    }
                )
        return sorted(slow_tests, key=lambda x: x["duration"], reverse=True)

    def _identify_memory_intensive_tests(self) -> list[dict]:
        """Identify tests with high memory usage."""
        memory_tests = []
        for test_id, metrics in self.metrics.items():
            if metrics.memory_delta > self.HIGH_MEMORY_THRESHOLD:
                memory_tests.append(
                    {
                        "test": test_id,
                        "memory_mb": metrics.memory_mb,
                        "duration": metrics.duration,
                    }
                )
        return sorted(memory_tests, key=lambda x: x["memory_mb"], reverse=True)

    def _identify_hotspots(self) -> dict:
        """Identify performance hotspots by test category."""
        categories = {}

        for test_id, metrics in self.metrics.items():
            # Extract category from test path
            parts = test_id.split("/")
            if len(parts) > 1:
                category = parts[1] if parts[0] == "tests" else parts[0]
            else:
                category = "other"

            if category not in categories:
                categories[category] = {
                    "count": 0,
                    "total_duration": 0.0,
                    "total_memory_mb": 0.0,
                    "slowest_test": None,
                }

            cat_stats = categories[category]
            cat_stats["count"] += 1
            cat_stats["total_duration"] += metrics.duration
            cat_stats["total_memory_mb"] += metrics.memory_mb

            if (
                not cat_stats["slowest_test"]
                or metrics.duration > cat_stats["slowest_test"]["duration"]
            ):
                cat_stats["slowest_test"] = {
                    "test": test_id,
                    "duration": metrics.duration,
                }

        # Calculate averages
        for category in categories.values():
            if category["count"] > 0:
                category["avg_duration"] = (
                    category["total_duration"] / category["count"]
                )
                category["avg_memory_mb"] = (
                    category["total_memory_mb"] / category["count"]
                )

        return categories

    def _check_performance_regressions(self) -> list[dict] | None:
        """Check for performance regressions against baseline."""
        if not self.baseline_path.exists():
            return None

        with open(self.baseline_path, "r") as f:
            baseline = json.load(f)

        regressions = []
        baseline_metrics = baseline.get("metrics", {})

        for test_id, current_metrics in self.metrics.items():
            if test_id in baseline_metrics:
                baseline_time = baseline_metrics[test_id]["duration"]
                current_time = current_metrics.duration

                if current_time > baseline_time * self.REGRESSION_THRESHOLD:
                    regression_pct = ((current_time / baseline_time) - 1) * 100
                    regressions.append(
                        {
                            "test": test_id,
                            "baseline": baseline_time,
                            "current": current_time,
                            "regression_percent": regression_pct,
                        }
                    )

        if regressions:
            regressions.sort(key=lambda x: x["regression_percent"], reverse=True)
            self._save_regressions(regressions)

        return regressions

    def _save_regressions(self, regressions: list[dict]) -> None:
        """Save regression data to file."""
        regression_path = Path(".test-performance-regressions.json")
        with open(regression_path, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "count": len(regressions),
                    "regressions": regressions,
                },
                f,
                indent=2,
            )

    def _print_summary(self) -> None:
        """Print performance summary to console."""
        reporter: TerminalReporter = self.config.pluginmanager.get_plugin(
            "terminalreporter"
        )
        if not reporter:
            return

        # Check if we have any metrics to avoid division by zero
        if not self.metrics:
            reporter.write_sep("=", "Performance Summary")
            reporter.write_line("No tests were profiled.")
            return

        reporter.write_sep("=", "Performance Summary")

        # Overall statistics
        total_duration = sum(m.duration for m in self.metrics.values())
        total_memory = sum(m.memory_mb for m in self.metrics.values())

        reporter.write_line(f"Total execution time: {total_duration:.2f}s")
        reporter.write_line(f"Total memory usage: {total_memory:.2f} MB")
        reporter.write_line(
            f"Average test duration: {total_duration / len(self.metrics):.3f}s"
        )

        # Slow tests
        slow_tests = self._identify_slow_tests()
        if slow_tests:
            reporter.write_sep("-", f"Slowest Tests (>{self.SLOW_TEST_THRESHOLD}s)")
            for test_info in slow_tests[:5]:
                test_name = test_info["test"].split("::")[-1]
                reporter.write_line(f"  {test_name}: {test_info['duration']:.2f}s")

        # Memory intensive tests
        memory_tests = self._identify_memory_intensive_tests()
        if memory_tests:
            reporter.write_sep(
                "-",
                f"Memory Intensive Tests (>{self.HIGH_MEMORY_THRESHOLD / 1024 / 1024:.0f} MB)",
            )
            for test_info in memory_tests[:5]:
                test_name = test_info["test"].split("::")[-1]
                reporter.write_line(f"  {test_name}: {test_info['memory_mb']:.2f} MB")

        # Performance regressions
        regressions = self._check_performance_regressions()
        if regressions:
            reporter.write_sep("-", "⚠️  Performance Regressions Detected", red=True)
            for regression in regressions[:5]:
                test_name = regression["test"].split("::")[-1]
                reporter.write_line(
                    f"  {test_name}: {regression['regression_percent']:.1f}% slower "
                    f"({regression['baseline']:.2f}s → {regression['current']:.2f}s)",
                    red=True,
                )

        reporter.write_line(f"\nDetailed report saved to: {self.report_path}")
        if regressions:
            reporter.write_line(
                "Regressions saved to: .test-performance-regressions.json", red=True
            )


def pytest_configure(config: Config) -> None:
    """Register the plugin with pytest."""
    if config.getoption("--profile", default=False):
        config.pluginmanager.register(TestProfilerPlugin(config), "test_profiler")


def pytest_addoption(parser) -> None:
    """Add command-line options for the profiler."""
    group = parser.getgroup("profiler", "Test performance profiling")
    group.addoption(
        "--profile",
        action="store_true",
        default=False,
        help="Enable test performance profiling",
    )
    group.addoption(
        "--profile-baseline",
        action="store_true",
        default=False,
        help="Create performance baseline",
    )
    group.addoption(
        "--profile-threshold",
        type=float,
        default=1.0,
        help="Threshold for slow test detection (seconds)",
    )
