#!/usr/bin/env python3
"""Generate a comprehensive validation report for the dataset.

This script analyzes the current dataset and generates a detailed
report on validation status, file formats, and data quality.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

from src.core.config.settings import get_logger
from src.core.loaders.omnidexer import Omnidexer
from src.core.loaders.source_manager import FileSystemSourceManager
from src.core.loaders.json_loader import (
    create_spell_loader,
    create_creature_loader,
    create_item_loader,
    create_adventure_loader,
    create_book_loader,
)
from src.core.models.content import ContentType


class ValidationReport:
    """Generate comprehensive validation reports."""

    def __init__(self):
        self.results = {
            "summary": {},
            "content_stats": {},
            "file_analysis": {},
            "validation_issues": [],
            "performance_metrics": {},
            "recommendations": [],
        }
        self.log_capture = []

    def setup_logging(self):
        """Set up logging to capture validation issues."""

        class LogCapture(logging.Handler):
            def __init__(self, report):
                super().__init__()
                self.report = report

            def emit(self, record):
                self.report.log_capture.append(
                    {
                        "level": record.levelname,
                        "message": record.getMessage(),
                        "logger": record.name,
                    }
                )

        handler = LogCapture(self)
        loggers = [
            get_logger("src.core.loaders.json_loader"),
            get_logger("src.core.loaders.omnidexer"),
        ]

        for logger in loggers:
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    def analyze_log_messages(self):
        """Analyze captured log messages for issues."""
        warnings = []
        errors = []
        file_skips = defaultdict(int)

        for entry in self.log_capture:
            message = entry["message"]

            if entry["level"] == "WARNING":
                if "Validation failed" in message:
                    warnings.append(message)
                elif "Skipping" in message:
                    if "Foundry VTT" in message:
                        file_skips["foundry"] += 1
                    elif "template" in message:
                        file_skips["template"] += 1
                    elif "copy-template" in message:
                        file_skips["copy_template"] += 1
                    else:
                        file_skips["other"] += 1

            elif entry["level"] == "ERROR":
                errors.append(message)

        return {
            "validation_warnings": warnings,
            "errors": errors,
            "file_skips": dict(file_skips),
        }

    async def run_full_analysis(self):
        """Run comprehensive analysis of the dataset."""
        print("🔍 Starting comprehensive validation analysis...")

        self.setup_logging()
        start_time = time.time()

        # Initialize source manager and omnidexer
        source_manager = FileSystemSourceManager()
        omnidexer = Omnidexer(source_manager)

        # Get data paths
        data_paths = source_manager.get_data_paths()

        # Analyze file structure
        print("📁 Analyzing file structure...")
        file_analysis = await self._analyze_file_structure(data_paths)

        # Load all data through omnidexer
        print("📊 Loading all data through omnidexer...")
        load_start = time.time()
        load_stats = await omnidexer.load_all_data()
        load_time = time.time() - load_start

        # Test individual loaders
        print("🧪 Testing individual loaders...")
        loader_results = await self._test_individual_loaders(data_paths)

        # Analyze log messages
        print("📋 Analyzing validation issues...")
        log_analysis = self.analyze_log_messages()

        # Generate summary
        total_time = time.time() - start_time
        total_items = sum(load_stats.values())

        self.results = {
            "summary": {
                "total_analysis_time": total_time,
                "total_items_loaded": total_items,
                "items_per_second": total_items / load_time if load_time > 0 else 0,
                "total_files_found": sum(len(files) for files in data_paths.values()),
                "total_files_processed": len(
                    [f for files in data_paths.values() for f in files if f.exists()]
                ),
                "validation_warnings": len(log_analysis["validation_warnings"]),
                "errors": len(log_analysis["errors"]),
            },
            "content_stats": load_stats,
            "file_analysis": file_analysis,
            "loader_results": loader_results,
            "validation_issues": log_analysis,
            "performance_metrics": {
                "omnidexer_load_time": load_time,
                "items_per_second": total_items / load_time if load_time > 0 else 0,
                "memory_usage": self._get_memory_usage(),
            },
            "recommendations": self._generate_recommendations(log_analysis, load_stats),
        }

        print("✅ Analysis complete!")
        return self.results

    async def _analyze_file_structure(
        self, data_paths: Dict[ContentType, List[Path]]
    ) -> Dict:
        """Analyze the structure of data files."""
        analysis = {
            "by_content_type": {},
            "file_extensions": defaultdict(int),
            "file_sizes": {"total_mb": 0, "by_type": {}},
            "suspicious_files": [],
        }

        for content_type, files in data_paths.items():
            type_analysis = {
                "count": len(files),
                "existing": len([f for f in files if f.exists()]),
                "total_size_mb": 0,
                "largest_file": None,
                "smallest_file": None,
            }

            existing_files = [f for f in files if f.exists()]
            if existing_files:
                sizes = [(f, f.stat().st_size) for f in existing_files]
                type_analysis["total_size_mb"] = sum(size for _, size in sizes) / (
                    1024 * 1024
                )
                type_analysis["largest_file"] = max(sizes, key=lambda x: x[1])[0].name
                type_analysis["smallest_file"] = min(sizes, key=lambda x: x[1])[0].name

                # Check for suspicious files
                for file_path, size in sizes:
                    if size > 50 * 1024 * 1024:  # Files > 50MB
                        analysis["suspicious_files"].append(
                            {
                                "file": file_path.name,
                                "size_mb": size / (1024 * 1024),
                                "reason": "Very large file",
                            }
                        )
                    elif size < 100:  # Files < 100 bytes
                        analysis["suspicious_files"].append(
                            {
                                "file": file_path.name,
                                "size_mb": size / (1024 * 1024),
                                "reason": "Very small file",
                            }
                        )

            analysis["by_content_type"][content_type.value] = type_analysis

            # Track file extensions
            for file_path in files:
                analysis["file_extensions"][file_path.suffix] += 1

        return analysis

    async def _test_individual_loaders(
        self, data_paths: Dict[ContentType, List[Path]]
    ) -> Dict:
        """Test individual loaders for detailed analysis."""
        loaders = {
            ContentType.SPELL: create_spell_loader(),
            ContentType.CREATURE: create_creature_loader(),
            ContentType.ITEM: create_item_loader(),
            ContentType.ADVENTURE: create_adventure_loader(),
            ContentType.BOOK: create_book_loader(),
        }

        results = {}

        for content_type, loader in loaders.items():
            files = data_paths.get(content_type, [])
            if not files:
                continue

            # Test a sample of files
            sample_files = files[:5]  # Test first 5 files
            loader_result = {
                "files_tested": len(sample_files),
                "total_items": 0,
                "successful_files": 0,
                "failed_files": 0,
                "avg_load_time": 0,
            }

            load_times = []
            for file_path in sample_files:
                if not file_path.exists():
                    continue

                try:
                    start = time.time()
                    items = await loader.load(file_path)
                    load_time = time.time() - start

                    loader_result["total_items"] += len(items)
                    loader_result["successful_files"] += 1
                    load_times.append(load_time)

                except Exception as e:
                    loader_result["failed_files"] += 1

            if load_times:
                loader_result["avg_load_time"] = sum(load_times) / len(load_times)

            results[content_type.value] = loader_result

        return results

    def _get_memory_usage(self) -> Dict:
        """Get current memory usage."""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
                "available": True,
            }
        except ImportError:
            return {"available": False, "reason": "psutil not installed"}

    def _generate_recommendations(
        self, log_analysis: Dict, load_stats: Dict
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        warning_count = len(log_analysis["validation_warnings"])
        total_items = sum(load_stats.values())

        if warning_count > 0:
            warning_ratio = warning_count / total_items if total_items > 0 else 0
            if warning_ratio > 0.02:  # More than 2% warnings
                recommendations.append(
                    f"High validation warning rate ({warning_ratio:.1%}). "
                    "Consider reviewing data models for missing edge cases."
                )
            elif warning_ratio > 0.01:  # More than 1% warnings
                recommendations.append(
                    f"Moderate validation warning rate ({warning_ratio:.1%}). "
                    "Monitor for new data structure patterns."
                )
            else:
                recommendations.append(
                    f"Low validation warning rate ({warning_ratio:.1%}). "
                    "System is handling data well."
                )

        if log_analysis["errors"]:
            recommendations.append(
                f"Found {len(log_analysis['errors'])} errors. "
                "Review error messages for critical issues."
            )

        file_skips = log_analysis["file_skips"]
        if file_skips:
            total_skips = sum(file_skips.values())
            recommendations.append(
                f"Skipped {total_skips} files "
                f"({', '.join(f'{k}: {v}' for k, v in file_skips.items())}). "
                "This is expected for template and Foundry files."
            )

        if total_items < 1000:
            recommendations.append(
                "Low item count suggests incomplete dataset or loading issues."
            )
        elif total_items > 50000:
            recommendations.append(
                "Large dataset detected. Consider performance optimizations."
            )

        return recommendations

    def generate_report_text(self) -> str:
        """Generate human-readable report text."""
        results = self.results

        lines = [
            "=" * 80,
            "🔍 COMPREHENSIVE VALIDATION REPORT",
            "=" * 80,
            "",
            "📊 SUMMARY",
            "-" * 40,
            f"Total analysis time: {results['summary']['total_analysis_time']:.2f}s",
            f"Total items loaded: {results['summary']['total_items_loaded']:,}",
            f"Loading performance: {results['summary']['items_per_second']:.1f} items/second",
            f"Files found: {results['summary']['total_files_found']}",
            f"Files processed: {results['summary']['total_files_processed']}",
            f"Validation warnings: {results['summary']['validation_warnings']}",
            f"Errors: {results['summary']['errors']}",
            "",
            "📋 CONTENT STATISTICS",
            "-" * 40,
        ]

        for content_type, count in sorted(results["content_stats"].items()):
            lines.append(f"{content_type}: {count:,} items")

        lines.extend(
            [
                "",
                "📁 FILE ANALYSIS",
                "-" * 40,
            ]
        )

        file_analysis = results["file_analysis"]
        for content_type, analysis in file_analysis["by_content_type"].items():
            lines.append(f"{content_type}:")
            lines.append(f"  Files: {analysis['existing']}/{analysis['count']} exist")
            lines.append(f"  Total size: {analysis['total_size_mb']:.1f} MB")
            if analysis.get("largest_file"):
                lines.append(f"  Largest: {analysis['largest_file']}")

        if file_analysis["suspicious_files"]:
            lines.extend(
                [
                    "",
                    "⚠️  SUSPICIOUS FILES",
                    "-" * 40,
                ]
            )
            for file_info in file_analysis["suspicious_files"][:5]:
                lines.append(
                    f"{file_info['file']}: {file_info['reason']} "
                    f"({file_info['size_mb']:.1f} MB)"
                )

        if results["validation_issues"]["validation_warnings"]:
            lines.extend(
                [
                    "",
                    "🚨 VALIDATION ISSUES (sample)",
                    "-" * 40,
                ]
            )
            for warning in results["validation_issues"]["validation_warnings"][:3]:
                lines.append(f"  {warning[:100]}...")

        lines.extend(
            [
                "",
                "💡 RECOMMENDATIONS",
                "-" * 40,
            ]
        )

        for i, rec in enumerate(results["recommendations"], 1):
            lines.append(f"{i}. {rec}")

        lines.extend(
            [
                "",
                "⚡ PERFORMANCE METRICS",
                "-" * 40,
                f"Omnidexer load time: {results['performance_metrics']['omnidexer_load_time']:.2f}s",
                f"Items per second: {results['performance_metrics']['items_per_second']:.1f}",
            ]
        )

        if results["performance_metrics"]["memory_usage"]["available"]:
            memory = results["performance_metrics"]["memory_usage"]
            lines.append(f"Memory usage: {memory['rss_mb']:.1f} MB RSS")

        return "\n".join(lines)

    def save_json_report(self, output_path: Path):
        """Save detailed JSON report."""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)


async def main():
    """Run validation report generation."""
    print("🔍 Generating comprehensive validation report...")

    report = ValidationReport()
    results = await report.run_full_analysis()

    # Generate and display text report
    text_report = report.generate_report_text()
    print("\n" + text_report)

    # Save detailed JSON report
    json_path = Path("validation_report.json")
    report.save_json_report(json_path)
    print(f"\n💾 Detailed JSON report saved to: {json_path}")

    # Save text report
    text_path = Path("validation_report.txt")
    with open(text_path, "w") as f:
        f.write(text_report)
    print(f"📄 Text report saved to: {text_path}")


if __name__ == "__main__":
    asyncio.run(main())
