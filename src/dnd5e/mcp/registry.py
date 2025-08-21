"""Tool registration system for the dnd5e MCP server.

This module provides utilities for registering and managing MCP tools,
including dynamic tool discovery and registration validation.

Key Features:
- Dynamic tool registration and discovery
- Tool metadata and validation
- Performance monitoring for tool registration
- Integration with FastMCP framework
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP

from dnd5e.core.logging import get_logger

logger = get_logger(__name__)


class ToolMetadata:
    """Metadata container for MCP tools."""

    def __init__(
        self,
        name: str,
        function: Callable,
        description: str | None = None,
        category: str = "general",
        performance_target_ms: float | None = None,
        requires_auth: bool = False,
        tags: set[str] | None = None,
    ):
        self.name = name
        self.function = function
        self.description = description or function.__doc__ or "No description available"
        self.category = category
        self.performance_target_ms = performance_target_ms
        self.requires_auth = requires_auth
        self.tags = tags or set()

        # Extract parameter information
        self.signature = inspect.signature(function)
        self.parameters = list(self.signature.parameters.keys())
        self.return_annotation = self.signature.return_annotation

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "performance_target_ms": self.performance_target_ms,
            "requires_auth": self.requires_auth,
            "tags": list(self.tags),
            "parameters": self.parameters,
            "return_type": str(self.return_annotation)
            if self.return_annotation
            else "Any",
        }


class ToolRegistry:
    """Registry for managing MCP tools and their metadata."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolMetadata] = {}
        self._categories: dict[str, set[str]] = {}
        self._performance_targets: dict[str, float] = {}

    def register_tool(
        self,
        name: str,
        function: Callable,
        description: str | None = None,
        category: str = "general",
        performance_target_ms: float | None = None,
        requires_auth: bool = False,
        tags: set[str] | None = None,
    ) -> ToolMetadata:
        """Register a tool with the registry.

        Args:
            name: Tool name (must be unique)
            function: Tool function to register
            description: Optional tool description
            category: Tool category for organization
            performance_target_ms: Performance target in milliseconds
            requires_auth: Whether tool requires authentication
            tags: Optional set of tags for tool classification

        Returns:
            ToolMetadata instance for the registered tool

        Raises:
            ValueError: If tool name is already registered or invalid
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")

        if not callable(function):
            raise ValueError(f"Tool function for '{name}' is not callable")

        # Validate function signature
        try:
            # Check if it's an async function for MCP compatibility
            if not inspect.iscoroutinefunction(function):
                logger.warning(
                    f"Tool '{name}' is not async - MCP tools should be async"
                )
        except Exception as e:
            raise ValueError(f"Invalid function signature for tool '{name}': {e}")

        # Create metadata
        metadata = ToolMetadata(
            name=name,
            function=function,
            description=description,
            category=category,
            performance_target_ms=performance_target_ms,
            requires_auth=requires_auth,
            tags=tags,
        )

        # Register the tool
        self._tools[name] = metadata

        # Update category index
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(name)

        # Update performance targets
        if performance_target_ms is not None:
            self._performance_targets[name] = performance_target_ms

        logger.info(f"Registered MCP tool '{name}' in category '{category}'")
        return metadata

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool from the registry.

        Args:
            name: Name of tool to unregister

        Returns:
            True if tool was removed, False if it wasn't registered
        """
        if name not in self._tools:
            return False

        metadata = self._tools[name]

        # Remove from main registry
        del self._tools[name]

        # Remove from category index
        if metadata.category in self._categories:
            self._categories[metadata.category].discard(name)
            if not self._categories[metadata.category]:
                del self._categories[metadata.category]

        # Remove from performance targets
        self._performance_targets.pop(name, None)

        logger.info(f"Unregistered MCP tool '{name}'")
        return True

    def get_tool(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name.

        Args:
            name: Tool name to retrieve

        Returns:
            ToolMetadata if found, None otherwise
        """
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolMetadata]:
        """List registered tools, optionally filtered by category.

        Args:
            category: Optional category to filter by

        Returns:
            List of ToolMetadata for matching tools
        """
        if category is None:
            return list(self._tools.values())

        tool_names = self._categories.get(category, set())
        return [self._tools[name] for name in tool_names]

    def list_categories(self) -> list[str]:
        """List all registered categories.

        Returns:
            List of category names
        """
        return sorted(self._categories.keys())

    def get_tools_by_tag(self, tag: str) -> list[ToolMetadata]:
        """Get tools that have a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of ToolMetadata for tools with the tag
        """
        return [metadata for metadata in self._tools.values() if tag in metadata.tags]

    def get_performance_targets(self) -> dict[str, float]:
        """Get performance targets for all tools.

        Returns:
            Dictionary mapping tool names to performance targets in milliseconds
        """
        return self._performance_targets.copy()

    def validate_registry(self) -> dict[str, list[str]]:
        """Validate the tool registry and return any issues found.

        Returns:
            Dictionary with validation issues organized by category
        """
        issues: dict[str, list[str]] = {"errors": [], "warnings": [], "info": []}

        # Check for duplicate functions
        function_map: dict[Callable, list[str]] = {}
        for name, metadata in self._tools.items():
            func = metadata.function
            if func not in function_map:
                function_map[func] = []
            function_map[func].append(name)

        for func, names in function_map.items():
            if len(names) > 1:
                issues["warnings"].append(
                    f"Function {func.__name__} is registered multiple times: {names}"
                )

        # Check for missing performance targets on search tools
        for name, metadata in self._tools.items():
            if "search" in name and metadata.performance_target_ms is None:
                issues["warnings"].append(
                    f"Search tool '{name}' has no performance target"
                )

        # Check for tools without descriptions
        for name, metadata in self._tools.items():
            if (
                not metadata.description
                or metadata.description == "No description available"
            ):
                issues["info"].append(f"Tool '{name}' has no description")

        # Summary
        total_tools = len(self._tools)
        total_categories = len(self._categories)
        issues["info"].append(
            f"Registry contains {total_tools} tools in {total_categories} categories"
        )

        return issues

    def export_metadata(self) -> dict[str, Any]:
        """Export complete registry metadata.

        Returns:
            Dictionary containing all registry metadata
        """
        return {
            "tools": {
                name: metadata.to_dict() for name, metadata in self._tools.items()
            },
            "categories": {cat: list(tools) for cat, tools in self._categories.items()},
            "performance_targets": self._performance_targets.copy(),
            "statistics": {
                "total_tools": len(self._tools),
                "total_categories": len(self._categories),
                "tools_with_performance_targets": len(self._performance_targets),
            },
        }


# Global registry instance
_tool_registry = ToolRegistry()


def register_mcp_tool(
    name: str | None = None,
    category: str = "general",
    performance_target_ms: float | None = None,
    requires_auth: bool = False,
    tags: set[str] | None = None,
) -> Callable:
    """Decorator for registering MCP tools.

    Args:
        name: Tool name (defaults to function name)
        category: Tool category
        performance_target_ms: Performance target in milliseconds
        requires_auth: Whether tool requires authentication
        tags: Set of tags for classification

    Returns:
        Decorator function

    Examples:
        @register_mcp_tool("search_spells", category="content", performance_target_ms=200.0)
        async def search_spells_tool(query: str) -> Dict[str, Any]:
            # Implementation here
            pass
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__

        _tool_registry.register_tool(
            name=tool_name,
            function=func,
            category=category,
            performance_target_ms=performance_target_ms,
            requires_auth=requires_auth,
            tags=tags,
        )

        return func

    return decorator


def sync_registry_with_fastmcp(mcp_server: FastMCP) -> dict[str, Any]:
    """Synchronize registry metadata with FastMCP server tools.

    This function validates that tools registered via @mcp.tool() decorators
    are properly tracked in our metadata registry for monitoring and validation.

    Args:
        mcp_server: FastMCP server instance to sync with

    Returns:
        Dictionary with sync results and any issues found

    Note:
        FastMCP tools are registered via decorators, not dynamic registration.
        This function only syncs metadata for monitoring purposes.
    """
    try:
        # Get tools from FastMCP server (async call requires awaiting)
        import asyncio

        async def _get_server_tools() -> dict[str, Any]:
            return await mcp_server.get_tools()

        # Run async operation to get server tools
        server_tools_dict = {}
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't await here
                logger.warning("Cannot sync with FastMCP server in async context")
                return {
                    "status": "warning",
                    "message": "Sync skipped - cannot await in existing async context",
                    "registry_tools": len(_tool_registry._tools),
                    "server_tools": "unknown",
                }
            else:
                server_tools_dict = loop.run_until_complete(_get_server_tools())
        except RuntimeError:
            # No event loop, create one
            server_tools_dict = asyncio.run(_get_server_tools())

        server_tool_names = set(server_tools_dict.keys())
        registry_tool_names = set(_tool_registry._tools.keys())

        # Find discrepancies
        missing_from_registry = server_tool_names - registry_tool_names
        missing_from_server = registry_tool_names - server_tool_names

        # Log findings
        if missing_from_registry:
            logger.info(f"Server tools not in registry: {missing_from_registry}")
        if missing_from_server:
            logger.warning(f"Registry tools not in server: {missing_from_server}")

        sync_results = {
            "status": "success",
            "registry_tools": len(registry_tool_names),
            "server_tools": len(server_tool_names),
            "missing_from_registry": list(missing_from_registry),
            "missing_from_server": list(missing_from_server),
            "in_sync": len(missing_from_registry) == 0
            and len(missing_from_server) == 0,
        }

        logger.info(
            f"Registry sync complete: {len(registry_tool_names)} registry tools, "
            f"{len(server_tool_names)} server tools"
        )
        return sync_results

    except Exception as e:
        logger.error(f"Failed to sync registry with FastMCP server: {e}")
        return {
            "status": "error",
            "message": str(e),
            "registry_tools": len(_tool_registry._tools),
            "server_tools": "error",
        }


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    return _tool_registry


def list_registered_tools() -> list[str]:
    """Get list of registered tool names.

    Returns:
        List of tool names in alphabetical order
    """
    return sorted(_tool_registry._tools.keys())


def get_tool_metadata(name: str) -> dict[str, Any] | None:
    """Get metadata for a specific tool.

    Args:
        name: Tool name

    Returns:
        Tool metadata dictionary or None if not found
    """
    metadata = _tool_registry.get_tool(name)
    return metadata.to_dict() if metadata else None


def validate_tool_registry() -> dict[str, list[str]]:
    """Validate the tool registry and return validation results.

    Returns:
        Dictionary with validation results
    """
    return _tool_registry.validate_registry()


# Export public API
__all__ = [
    "ToolMetadata",
    "ToolRegistry",
    "register_mcp_tool",
    "sync_registry_with_fastmcp",
    "get_tool_registry",
    "list_registered_tools",
    "get_tool_metadata",
    "validate_tool_registry",
]
