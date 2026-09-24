"""studiorum doctor: check the configuration, data sources and cache."""

import os
from pathlib import Path

import typer
from rich.table import Table

from studiorum.cli.context import get_services
from studiorum.cli.display_manager import display_manager
from studiorum.core.cache import CacheManager
from studiorum.core.config.unified_config import get_default_config_path

OK, WARN, FAIL = "✅", "⚠️", "❌"
Check = tuple[str, str, str]


def doctor(ctx: typer.Context) -> None:
    """Check the configuration, data sources and cache, and exit 1 on a failure.

    The data check lists the configured data directories and homebrew
    without loading them.
    """
    console = display_manager.console
    checks = [*_config_checks(ctx), *_data_checks(), *_cache_checks()]

    table = Table(title="studiorum doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    for check in checks:
        table.add_row(*check)
    console.print(table)

    failures = sum(status == FAIL for _, status, _ in checks)
    warnings = sum(status == WARN for _, status, _ in checks)
    if failures:
        console.print(f"\n[red]{failures} check(s) failed.[/red]")
        raise typer.Exit(1)
    if warnings:
        console.print(f"\n[yellow]{warnings} warning(s).[/yellow]")
    else:
        console.print("\n[green]All checks passed.[/green]")


def _config_checks(ctx: typer.Context) -> list[Check]:
    config_file = ctx.find_root().params.get("config_file") or get_default_config_path()
    source = str(config_file) if Path(config_file).exists() else "defaults (no file)"
    return [("Configuration", OK, f"Loaded from {source}")]


def _data_checks() -> list[Check]:
    data = get_services().data
    problems = data.problems()
    if problems:
        return [("Data", FAIL, problem) for problem in problems]
    files = len(data.files())
    return [
        (
            "Data",
            OK,
            f"{files} files from {len(data.dirs)} data directories "
            f"and {len(data.homebrew)} homebrew",
        )
    ]


def _cache_checks() -> list[Check]:
    try:
        cache_dir = Path(CacheManager.get_instance().directory)
        stats = CacheManager.get_stats()
    except Exception as e:
        return [("Cache", FAIL, f"Cache error: {e}")]

    if not cache_dir.is_dir():
        return [("Cache", FAIL, f"Cache directory does not exist: {cache_dir}")]
    if not os.access(cache_dir, os.W_OK):
        return [("Cache", FAIL, f"Cache directory is not writable: {cache_dir}")]

    usage = stats["total_size_mb"] / stats["max_size_mb"] * 100
    details = f"{cache_dir}: {stats['total_entries']:,} entries, {usage:.1f}% full"
    if usage > 90:
        return [("Cache", WARN, f"{details}; run studiorum cache clear")]
    return [("Cache", OK, details)]
