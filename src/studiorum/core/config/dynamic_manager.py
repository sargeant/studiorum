"""
Dynamic configuration manager for runtime configuration updates.

This module provides the ConfigurationManager class that enables runtime
configuration updates with validation, persistence, and notification support
for the D&D 5e project. It integrates with the existing ApplicationConfig
system and supports request-scoped overrides for MCP operations.

Key Features:
- Runtime configuration updates without application restart
- Full validation through existing ApplicationConfig
- YAML persistence with atomic file operations
- Configuration change notifications and watchers
- Request-scoped configuration overrides
- Thread-safe operations for concurrent MCP requests
- Integration with existing AsyncRequestContext pattern

Examples:
    Basic usage:
    ```python
    manager = ConfigurationManager()

    # Update configuration
    result = await manager.update_config({
        "logging": {"level": "DEBUG"},
        "rendering": {"debug": True}
    })

    if result.is_success():
        config = result.unwrap()
        print(f"Updated config: {config.logging.level}")
    ```

    With configuration watcher:
    ```python
    def on_config_changed(old_config, new_config):
        print(f"Log level changed: {old_config.logging.level} -> {new_config.logging.level}")

    manager.register_config_watcher(on_config_changed)
    ```

    Request-scoped override:
    ```python
    # In MCP request handler
    request_config = manager.create_request_scoped_config(
        base_config,
        {"validation": {"strictness": "strict"}}
    )

    async with AsyncRequestContext(user_config=request_config) as ctx:
        # Operations use the overridden config
        pass
    ```
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import uuid4

import yaml
from pydantic import ValidationError
from watchdog.events import FileSystemEventHandler

from studiorum.core.logging import get_logger

if TYPE_CHECKING:
    from watchdog.observers import Observer

from ..error_types import ConfigurationError, ErrorCategory, ErrorSeverity, MCPErrorCode
from ..result import Error, Result, Success
from .loader import ConfigLoader
from .unified_config import ApplicationConfig, get_app_config, set_app_config

T = TypeVar("T")
ConfigChangeCallback = Callable[[ApplicationConfig, ApplicationConfig], None]

logger = get_logger(__name__)


class ConfigFileWatcher(FileSystemEventHandler):
    """File system watcher for configuration file changes."""

    def __init__(self, manager: ConfigurationManager, config_path: Path) -> None:
        """Initialize the file watcher.

        Args:
            manager: The configuration manager to notify
            config_path: Path to watch for changes
        """
        super().__init__()
        self.manager = manager
        self.config_path = config_path
        self.last_modified = 0.0

    def on_modified(self, event: Any) -> None:
        """Handle file modification events."""
        if not event.is_directory and Path(event.src_path) == self.config_path:
            # Debounce file changes (some editors write multiple times)
            import time

            current_time = time.time()
            if current_time - self.last_modified > 0.5:  # 500ms debounce
                self.last_modified = current_time
                asyncio.create_task(self.manager._reload_from_file())


class ConfigurationManager:
    """
    Dynamic configuration manager with runtime updates and validation.

    This manager provides thread-safe runtime configuration updates,
    YAML persistence, change notifications, and request-scoped overrides
    while integrating with the existing ApplicationConfig system.
    """

    def __init__(
        self, config_path: Path | None = None, enable_file_watcher: bool = False
    ) -> None:
        """Initialize the configuration manager.

        Args:
            config_path: Optional path to configuration file.
                        Defaults to ~/.config/studiorum/config.yaml
            enable_file_watcher: Whether to watch config file for changes
        """
        self._lock = asyncio.Lock()  # Async lock for config updates
        self._loader = ConfigLoader()

        # Configuration file path
        if config_path is None:
            home = Path.home()
            config_dir = home / ".config" / "studiorum"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_path = config_dir / "config.yaml"
        else:
            self._config_path = config_path

        # Change notification system
        self._watchers: list[ConfigChangeCallback] = []

        # File watching
        self._file_observer: Any | None = None
        self._enable_file_watcher = enable_file_watcher

        # Initialize file watcher if enabled
        if enable_file_watcher:
            self._setup_file_watcher()

    def get_current_config(self) -> ApplicationConfig:
        """Get the current application configuration.

        Returns:
            Current ApplicationConfig instance

        Thread-safe: Yes
        """
        return get_app_config()

    async def update_config(
        self, updates: dict[str, Any]
    ) -> Result[ApplicationConfig, ConfigurationError]:
        """Update configuration with partial changes.

        Args:
            updates: Dictionary of configuration updates using nested keys
                    (e.g., {"logging": {"level": "DEBUG"}})

        Returns:
            Success with updated ApplicationConfig, or Error with validation details

        Thread-safe: Yes

        Examples:
            ```python
            result = await manager.update_config({
                "logging": {"level": "DEBUG"},
                "rendering": {"debug": True},
                "mcp": {"enabled": True, "port": 8080}
            })
            ```
        """
        # Get old config first
        old_config = self.get_current_config()

        try:
            async with self._lock:
                # Create updated configuration data
                current_data = old_config.model_dump()
                updated_data = self._deep_merge_dicts(current_data, updates)

                # Validate new configuration
                new_config = ApplicationConfig(**updated_data)

                # Update global configuration
                set_app_config(new_config)

            # Notify watchers outside the lock to avoid deadlock
            await self._notify_watchers(old_config, new_config)

            logger.info(
                "Configuration updated successfully",
                extra={"updates": updates, "config_sections": list(updates.keys())},
            )

            return Success(new_config)

        except ValidationError as e:
            error_messages = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            logger.warning(
                "Configuration update validation failed",
                extra={"updates": updates, "validation_errors": error_messages},
            )

            return Error(
                ConfigurationError(
                    message="Configuration update validation failed",
                    error_code=MCPErrorCode.VALIDATION_FAILED,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                    suggestions=[
                        "Check field types and value constraints",
                        "Review required vs optional fields",
                        "Verify nested configuration structure",
                        "Use configuration schema for validation",
                    ],
                    data={
                        "updates": updates,
                        "validation_errors": error_messages,
                        "error_count": len(error_messages),
                    },
                )
            )
        except Exception as e:
            logger.error(
                "Unexpected error during configuration update",
                extra={
                    "updates": updates,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                },
            )

            return Error(
                ConfigurationError(
                    message=f"Unexpected error during configuration update: {e}",
                    error_code=MCPErrorCode.INTERNAL_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.CRITICAL,
                    suggestions=[
                        "Review configuration update data format",
                        "Check for conflicting configuration values",
                        "Report this error if problem persists",
                    ],
                    data={"updates": updates, "exception_type": type(e).__name__},
                )
            )

    async def save_config_to_file(
        self, config: ApplicationConfig | None = None, path: Path | None = None
    ) -> Result[Path, ConfigurationError]:
        """Save configuration to YAML file with atomic operations.

        Args:
            config: Configuration to save. If None, uses current config
            path: File path to save to. If None, uses default config path

        Returns:
            Success with saved file path, or Error with save details

        Thread-safe: Yes
        """
        if config is None:
            config = self.get_current_config()
        if path is None:
            path = self._config_path

        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare configuration data for YAML (serialize Path objects to strings)
            config_data = config.model_dump(
                exclude_defaults=False,
                exclude_none=True,
                mode="json",  # Use JSON mode to serialize Path objects as strings
            )

            # Atomic write using temporary file
            temp_path = path.with_suffix(f".{uuid4().hex}.tmp")

            try:
                with temp_path.open("w", encoding="utf-8") as f:
                    yaml.dump(
                        config_data,
                        f,
                        default_flow_style=False,
                        indent=2,
                        sort_keys=True,
                        allow_unicode=True,
                    )

                # Atomic move to final location
                temp_path.replace(path)

                logger.info(
                    f"Configuration saved to {path}",
                    extra={
                        "config_path": str(path),
                        "config_size": path.stat().st_size,
                    },
                )

                return Success(path)

            finally:
                # Clean up temp file if it still exists
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(
                f"Failed to save configuration to {path}",
                extra={
                    "config_path": str(path),
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                },
            )

            return Error(
                ConfigurationError(
                    message=f"Failed to save configuration to {path}: {e}",
                    error_code=MCPErrorCode.CONFIGURATION_ERROR,
                    category=ErrorCategory.SYSTEM_ERROR,
                    severity=ErrorSeverity.ERROR,
                    suggestions=[
                        "Check file and directory permissions",
                        "Ensure sufficient disk space",
                        "Verify parent directory exists",
                        "Check for file system errors",
                    ],
                    data={"config_path": str(path), "exception_type": type(e).__name__},
                )
            )

    async def load_config_from_file(
        self, path: Path | None = None
    ) -> Result[ApplicationConfig, ConfigurationError]:
        """Load configuration from YAML file.

        Args:
            path: File path to load from. If None, uses default config path

        Returns:
            Success with loaded ApplicationConfig, or Error with load details

        Thread-safe: Yes
        """
        if path is None:
            path = self._config_path

        return self._loader.load_from_file(path)

    async def register_config_watcher(self, callback: ConfigChangeCallback) -> None:
        """Register a callback for configuration changes.

        Args:
            callback: Function to call when configuration changes.
                     Receives (old_config, new_config) arguments

        Thread-safe: Yes

        Examples:
            ```python
            def on_log_level_changed(old_config, new_config):
                if old_config.logging.level != new_config.logging.level:
                    get_logger().setLevel(new_config.logging.level)

            await manager.register_config_watcher(on_log_level_changed)
            ```
        """
        async with self._lock:
            self._watchers.append(callback)

    async def unregister_config_watcher(self, callback: ConfigChangeCallback) -> bool:
        """Unregister a configuration change callback.

        Args:
            callback: Callback function to remove

        Returns:
            True if callback was found and removed, False otherwise

        Thread-safe: Yes
        """
        async with self._lock:
            try:
                self._watchers.remove(callback)
                return True
            except ValueError:
                return False

    def create_request_scoped_config(
        self,
        base_config: ApplicationConfig | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> ApplicationConfig:
        """Create configuration for request-scoped operations.

        This creates a new ApplicationConfig instance with temporary
        overrides for use in MCP operations without affecting global state.

        Args:
            base_config: Base configuration to use. If None, uses current config
            overrides: Configuration overrides to apply

        Returns:
            New ApplicationConfig instance with overrides applied

        Thread-safe: Yes

        Examples:
            ```python
            # Create stricter validation for specific MCP request
            request_config = manager.create_request_scoped_config(
                overrides={
                    "validation": {"strictness": "strict"},
                    "rendering": {"debug": True}
                }
            )

            async with AsyncRequestContext(user_config=request_config) as ctx:
                # Operations in this context use the overridden config
                pass
            ```
        """
        if base_config is None:
            base_config = self.get_current_config()

        if not overrides:
            return base_config

        # Merge overrides into base configuration
        base_data = base_config.model_dump()
        merged_data = self._deep_merge_dicts(base_data, overrides)

        return ApplicationConfig(**merged_data)

    async def reload_from_file(self) -> Result[ApplicationConfig, ConfigurationError]:
        """Reload configuration from file and update global config.

        Returns:
            Success with reloaded ApplicationConfig, or Error with load details

        Thread-safe: Yes
        """
        async with self._lock:
            old_config = self.get_current_config()

            load_result = await self.load_config_from_file()
            if load_result.is_error():
                return load_result

            new_config = load_result.unwrap()
            set_app_config(new_config)

            # Notify watchers
            await self._notify_watchers(old_config, new_config)

            logger.info(
                f"Configuration reloaded from {self._config_path}",
                extra={"config_path": str(self._config_path)},
            )

            return Success(new_config)

    def get_config_path(self) -> Path:
        """Get the current configuration file path.

        Returns:
            Path to configuration file
        """
        return self._config_path

    def is_file_watcher_enabled(self) -> bool:
        """Check if file watcher is enabled.

        Returns:
            True if file watcher is active, False otherwise
        """
        return self._file_observer is not None and self._file_observer.is_alive()

    async def enable_file_watcher(self) -> None:
        """Enable file system watching for configuration changes.

        Thread-safe: Yes
        """
        async with self._lock:
            if not self._enable_file_watcher:
                self._enable_file_watcher = True
                self._setup_file_watcher()

    async def disable_file_watcher(self) -> None:
        """Disable file system watching for configuration changes.

        Thread-safe: Yes
        """
        async with self._lock:
            self._disable_file_watcher_sync()

    def _disable_file_watcher_sync(self) -> None:
        """Synchronous version of disable_file_watcher for internal use."""
        self._enable_file_watcher = False
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join(timeout=1.0)
            self._file_observer = None

    async def close(self) -> None:
        """Clean up resources and stop file watching.

        Thread-safe: Yes
        """
        await self.disable_file_watcher()

        async with self._lock:
            self._watchers.clear()

    # Private methods

    def _setup_file_watcher(self) -> None:
        """Set up file system watcher for configuration changes."""
        if not self._enable_file_watcher:
            return

        try:
            if self._file_observer:
                self._disable_file_watcher_sync()

            from watchdog.observers import Observer

            self._file_observer = Observer()
            handler = ConfigFileWatcher(self, self._config_path)

            # Watch the parent directory for the specific file
            self._file_observer.schedule(
                handler, str(self._config_path.parent), recursive=False
            )
            self._file_observer.start()

            logger.debug(
                f"File watcher enabled for {self._config_path}",
                extra={"config_path": str(self._config_path)},
            )

        except Exception as e:
            logger.warning(
                f"Failed to setup file watcher: {e}",
                extra={"config_path": str(self._config_path), "exception": str(e)},
            )

    async def _reload_from_file(self) -> None:
        """Internal method to reload configuration from file."""
        try:
            result = await self.reload_from_file()
            if result.is_error():
                logger.error(
                    "Failed to reload configuration from file",
                    extra={
                        "config_path": str(self._config_path),
                        "error": result.error.message,  # type: ignore[attr-defined]
                    },
                )
        except Exception as e:
            logger.error(
                "Exception during configuration file reload",
                extra={"config_path": str(self._config_path), "exception": str(e)},
            )

    async def _notify_watchers(
        self, old_config: ApplicationConfig, new_config: ApplicationConfig
    ) -> None:
        """Notify registered watchers of configuration changes."""
        if not self._watchers:
            return

        async with self._lock:
            watchers = self._watchers.copy()  # Avoid modification during iteration

        # Notify watchers synchronously (they should be fast)
        for watcher in watchers:
            try:
                watcher(old_config, new_config)
            except Exception as e:
                logger.warning(
                    "Configuration watcher failed",
                    extra={
                        "watcher": watcher.__name__
                        if hasattr(watcher, "__name__")
                        else str(watcher),
                        "exception": str(e),
                    },
                )

    def _deep_merge_dicts(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries with override precedence."""
        return self._loader._deep_merge_dicts(base, override)


# Global configuration manager instance
_config_manager: ConfigurationManager | None = None


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance.

    Returns:
        Global ConfigurationManager instance

    Thread-safe: Yes
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def reset_config_manager() -> None:
    """Reset the global configuration manager (for testing).

    Thread-safe: Yes
    """
    global _config_manager
    if _config_manager is not None:
        asyncio.create_task(_config_manager.close())
        _config_manager = None


def set_config_manager(manager: ConfigurationManager) -> None:
    """Set the global configuration manager instance.

    Args:
        manager: ConfigurationManager instance to use globally

    Thread-safe: Yes
    """
    global _config_manager
    if _config_manager is not None:
        asyncio.create_task(_config_manager.close())
    _config_manager = manager
