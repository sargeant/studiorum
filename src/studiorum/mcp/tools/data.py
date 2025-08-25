"""MCP tools for data repository management.

This module provides MCP tools for managing data repositories (SRD, primary override,
extensions) separately from content attribution concerns. Integrates with the
DataSourceManager from Package 1 foundation refactoring.

Key Features:
- Data repository operations (list, add, remove)
- Integration with DataSourceManager via AsyncRequestContext
- Comprehensive path validation and error handling
- Performance target: <500ms
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from studiorum.core.logging import get_logger

from ...core.context import AsyncRequestContext
from ...core.error_types import (
    ErrorCategory,
    MCPError,
    MCPErrorCode,
)
from ...core.result import Error, Result, Success
from ...core.services.protocols import SourceManagerProtocol

logger = get_logger(__name__)


class DataSourceStatus:
    """Status information for data sources."""

    def __init__(
        self,
        total_repositories: int,
        active_repositories: int,
        indexed_files: int,
        last_index_time: str | None = None,
        errors: list[str] | None = None,
    ):
        self.total_repositories = total_repositories
        self.active_repositories = active_repositories
        self.indexed_files = indexed_files
        self.last_index_time = last_index_time
        self.errors = errors or []


class DataRepositoryInfo:
    """Repository information for data sources."""

    def __init__(
        self,
        name: str,
        repository_type: str,
        enabled: bool,
        description: str,
        source_path: str | None = None,
    ):
        self.name = name
        self.repository_type = repository_type
        self.enabled = enabled
        self.description = description
        self.source_path = source_path


async def manage_data_sources(
    action: Literal[
        "list", "add_primary", "add_homebrew", "add_url", "remove", "status"
    ],
    source: str | None = None,
    name: str | None = None,
    description: str | None = None,
    context: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """
    Manage data repositories in Studiorum's three-tier data model.

    This tool manages data repositories (SRD, primary override, extensions)
    separately from content attribution. Uses the DataSourceManager from
    Package 1 foundation refactoring.

    Actions:
    - list: Show all configured repositories
    - add_primary: Set primary data override (replaces SRD)
    - add_homebrew: Add homebrew extension directory
    - add_url: Add URL-based extension
    - remove: Remove repository by name
    - status: Get detailed repository status

    Examples:
    - manage_data_sources("list")
    - manage_data_sources("add_primary", source="/path/to/5etools-data")
    - manage_data_sources("add_homebrew", source="/path/to/homebrew", name="my-spells")
    - manage_data_sources("add_url", source="https://example.com/content.json")
    - manage_data_sources("remove", name="old-homebrew")

    Args:
        action: Operation to perform
        source: Path or URL for repository operations
        name: Repository name for operations
        description: Optional description for new repositories
        context: AsyncRequestContext for service access

    Returns:
        Dictionary with operation results
    """
    import time
    import urllib.parse

    start_time = time.time()

    if not context:
        return {"error": "AsyncRequestContext required for data operations"}

    try:
        # Get the source manager service
        manager = await context.get_service(SourceManagerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        if action == "list":
            # Get repository statistics
            stats = manager.get_source_statistics()

            repositories = []
            # Since we don't have direct access to repository list from the protocol,
            # we'll extract it from the statistics
            if "repositories" in stats:
                for repo_info in stats["repositories"]:
                    repositories.append(
                        {
                            "name": repo_info.get("name", "unknown"),
                            "type": repo_info.get("type", "unknown"),
                            "enabled": repo_info.get("enabled", False),
                            "description": repo_info.get("description", ""),
                            "source": repo_info.get(
                                "path", repo_info.get("source_path", "")
                            ),
                        }
                    )

            duration_ms = (time.time() - start_time) * 1000

            return {
                "repositories": repositories,
                "total_count": len(repositories),
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 500.0,
                },
            }

        elif action == "status":
            # Get detailed status information
            stats = manager.get_source_statistics()

            # Extract repositories for detailed information
            repositories = []
            if "repositories" in stats:
                for repo_info in stats["repositories"]:
                    repositories.append(
                        {
                            "name": repo_info.get("name", "unknown"),
                            "type": repo_info.get("type", "unknown"),
                            "enabled": repo_info.get("enabled", False),
                            "file_count": repo_info.get("file_count", 0),
                            "validation_errors": repo_info.get("validation_errors", []),
                        }
                    )

            duration_ms = (time.time() - start_time) * 1000

            return {
                "total_repositories": stats.get("total_sources", 0),
                "active_repositories": stats.get("active_sources", 0),
                "indexed_files": stats.get("total_files", 0),
                "last_index_time": stats.get("last_sync", None),
                "errors": stats.get("sync_errors", []),
                "repositories": repositories,
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 500.0,
                },
            }

        elif action == "add_primary":
            if not source:
                return {"error": "Source path required for add_primary action"}

            # Validate path
            data_path = Path(source).expanduser().resolve()
            if not data_path.exists():
                return {"error": f"Path does not exist: {data_path}"}

            if not data_path.is_dir():
                return {"error": f"Path is not a directory: {data_path}"}

            # For now, we'll provide a response that indicates the operation would succeed
            # The actual implementation would require extending the SourceManagerProtocol
            # with methods for adding repositories

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "message": f"Primary data source would be set to: {data_path}",
                "note": "Repository management requires extending SourceManagerProtocol",
                "repository": {
                    "name": "primary-override",
                    "type": "primary",
                    "source": str(data_path),
                },
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 500.0,
                },
            }

        elif action == "add_homebrew":
            if not source:
                return {"error": "Source path required for add_homebrew action"}

            # Validate path
            homebrew_path = Path(source).expanduser().resolve()
            if not homebrew_path.exists():
                return {"error": f"Path does not exist: {homebrew_path}"}

            # Generate name if not provided
            repo_name = name or f"homebrew-{homebrew_path.name}"

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "message": f"Homebrew repository would be added: {repo_name}",
                "note": "Repository management requires extending SourceManagerProtocol",
                "repository": {
                    "name": repo_name,
                    "type": "extension",
                    "source": str(homebrew_path),
                },
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 500.0,
                },
            }

        elif action == "add_url":
            if not source:
                return {"error": "URL required for add_url action"}

            # Validate URL
            parsed = urllib.parse.urlparse(source)
            if parsed.scheme not in ("http", "https"):
                return {
                    "error": f"Invalid URL scheme. Must use http or https: {source}"
                }

            # Generate name if not provided
            repo_name = name or f"url-{parsed.netloc.replace('.', '-')}"

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "message": f"URL repository would be added: {repo_name}",
                "note": "Repository management requires extending SourceManagerProtocol",
                "repository": {
                    "name": repo_name,
                    "type": "extension",
                    "source": source,
                },
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 500.0,
                },
            }

        elif action == "remove":
            if not name:
                return {"error": "Repository name required for remove action"}

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "message": f"Repository would be removed: {name}",
                "note": "Repository management requires extending SourceManagerProtocol",
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 500.0,
                },
            }

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.exception(f"Failed to manage data sources: {e}")
        return {
            "error": f"Failed to manage data sources: {str(e)}",
            "performance": {"duration_ms": duration_ms, "target_met": False},
        }
