"""Configuration migration from old format to new three-tier structure.

This module handles migration from the old configuration format that mixed
data repositories and content attribution into a clear separation with
the new three-tier data model.

Migration Strategy:
- Intelligently parse old 'default_sources' list
- Separate file paths (data repositories) from abbreviations (content attribution)
- Map old content/merger settings to new performance configuration
- Provide detailed migration logging and reporting
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .data_sources import DataSourcesConfig, DataSourceType, ExtensionDataSourceConfig

logger = logging.getLogger(__name__)


class ConfigurationMigration:
    """Handles migration from old configuration format to new format."""

    def __init__(self) -> None:
        self.migration_log: list[str] = []

    def migrate_configuration(self, old_config: dict[str, Any]) -> DataSourcesConfig:
        """Migrate old configuration to new three-tier structure."""
        logger.info("Starting configuration migration from old format")
        self.migration_log.clear()

        # Start with default new configuration
        new_config = DataSourcesConfig()

        # Migrate default_sources (the problematic mixed concept)
        old_sources = old_config.get("default_sources", [])
        if old_sources:
            self._migrate_default_sources(old_sources, new_config)

        # Migrate old content configuration if present
        old_content = old_config.get("content", {})
        if old_content:
            self._migrate_content_config(old_content, new_config)

        # Migrate paths configuration if present
        old_paths = old_config.get("paths", {})
        if old_paths:
            self._migrate_paths_config(old_paths, new_config)

        # Migrate processing configuration if present
        old_processing = old_config.get("processing", {})
        if old_processing:
            self._migrate_processing_config(old_processing, new_config)

        # Log migration results
        logger.info(
            f"Configuration migration completed with {len(self.migration_log)} changes"
        )
        for log_entry in self.migration_log:
            logger.info(f"  • {log_entry}")

        return new_config

    def _migrate_default_sources(
        self, old_sources: list[str], new_config: DataSourcesConfig
    ) -> None:
        """Migrate old default_sources list to new structure."""
        for source in old_sources:
            if self._is_file_path(source):
                # It's a file path - probably 5etools data
                if self._looks_like_5etools_path(source):
                    # Set as primary override
                    new_config.primary_override.enabled = True
                    new_config.primary_override.source = source
                    new_config.primary_override.type = (
                        DataSourceType.FIVE_TOOLS_COMPATIBLE
                    )
                    new_config.primary_override.description = (
                        f"Migrated 5etools data: {Path(source).name}"
                    )
                    self.migration_log.append(
                        f"Migrated '{source}' as primary data override"
                    )
                else:
                    # Unknown path - add as extension
                    path_obj = Path(source)
                    # For migration purposes, assume directories unless obviously a file
                    is_dir = not path_obj.suffix or path_obj.suffix in [".dir", ".d"]
                    extension = ExtensionDataSourceConfig(
                        name=f"migrated-{path_obj.name}",
                        type=DataSourceType.DIRECTORY
                        if is_dir
                        else DataSourceType.FILE,
                        source=source,
                        description=f"Migrated from default_sources: {source}",
                    )
                    new_config.extensions.append(extension)
                    self.migration_log.append(
                        f"Migrated '{source}' as extension data source"
                    )

            elif self._is_source_abbreviation(source):
                # It's a source abbreviation - add to custom sources
                new_config.source_attribution.custom_sources[source] = {
                    "name": f"Custom Source: {source}",
                    "priority": 500,  # Medium priority for custom sources
                    "official": False,
                }
                self.migration_log.append(
                    f"Migrated '{source}' as custom source attribution"
                )

            elif self._is_url(source):
                # It's a URL - add as extension
                extension = ExtensionDataSourceConfig(
                    name=f"migrated-url-{len(new_config.extensions)}",
                    type=DataSourceType.URL,
                    source=source,
                    description=f"Migrated URL source: {source}",
                )
                new_config.extensions.append(extension)
                self.migration_log.append(f"Migrated '{source}' as URL extension")

            else:
                # Unknown format - log warning
                logger.warning(f"Unable to migrate unknown source format: {source}")
                self.migration_log.append(
                    f"WARNING: Unable to migrate unknown source: {source}"
                )

    def _migrate_content_config(
        self, old_content: dict[str, Any], new_config: DataSourcesConfig
    ) -> None:
        """Migrate old content configuration."""
        # Migrate merger settings to performance config
        merger_config = old_content.get("merger", {})
        if merger_config:
            cache_ttl = merger_config.get("cache_ttl", 3600)
            max_entries = merger_config.get("max_entries", 1000)

            new_config.performance["caching"]["content_cache"]["ttl"] = cache_ttl
            new_config.performance["caching"]["content_cache"]["max_entries"] = (
                max_entries
            )

            self.migration_log.append(
                f"Migrated content merger cache settings (TTL: {cache_ttl}s, max: {max_entries})"
            )

        # Migrate any source-specific settings
        old_sources = old_content.get("sources", {})
        if old_sources:
            for source_abbrev, source_config in old_sources.items():
                if isinstance(source_config, dict):
                    priority = source_config.get("priority", 500)
                    name = source_config.get("name", f"Custom: {source_abbrev}")
                    official = source_config.get("official", False)

                    new_config.source_attribution.custom_sources[source_abbrev] = {
                        "name": name,
                        "priority": priority,
                        "official": official,
                    }
                    self.migration_log.append(
                        f"Migrated source attribution for {source_abbrev}"
                    )

        # Migrate old default_sources from content config
        if "default_sources" in old_content:
            old_default_sources = old_content["default_sources"]
            if isinstance(old_default_sources, list):
                self._migrate_default_sources(old_default_sources, new_config)

    def _migrate_paths_config(
        self, old_paths: dict[str, Any], new_config: DataSourcesConfig
    ) -> None:
        """Migrate old paths configuration."""
        # If there's a data_path in the old config, consider it as primary override
        data_path = old_paths.get("data_path")
        if data_path and not new_config.is_primary_enabled():
            new_config.primary_override.enabled = True
            new_config.primary_override.source = str(data_path)
            new_config.primary_override.type = DataSourceType.DIRECTORY
            new_config.primary_override.description = "Migrated from paths.data_path"
            self.migration_log.append(
                f"Migrated paths.data_path '{data_path}' as primary data override"
            )

    def _migrate_processing_config(
        self, old_processing: dict[str, Any], new_config: DataSourcesConfig
    ) -> None:
        """Migrate old processing configuration."""
        # Migrate caching settings
        if "enable_caching" in old_processing:
            enabled = old_processing["enable_caching"]
            new_config.performance["caching"]["content_cache"]["enabled"] = enabled
            self.migration_log.append(f"Migrated processing.enable_caching: {enabled}")

        if "cache_ttl" in old_processing:
            ttl = old_processing["cache_ttl"]
            # Only set if content merger didn't already set it
            if (
                new_config.performance["caching"]["content_cache"]["ttl"] == 3600
            ):  # default
                new_config.performance["caching"]["content_cache"]["ttl"] = ttl
                self.migration_log.append(f"Migrated processing.cache_ttl: {ttl}")
            else:
                self.migration_log.append(
                    f"Skipped processing.cache_ttl: {ttl} (content merger took precedence)"
                )

        if "max_workers" in old_processing:
            workers = old_processing["max_workers"]
            # Store in performance config for reference
            new_config.performance.setdefault("workers", {})["max_workers"] = workers
            self.migration_log.append(f"Migrated processing.max_workers: {workers}")

    def _is_file_path(self, source: str) -> bool:
        """Check if source looks like a file path."""
        return (
            "/" in source
            or "\\" in source
            or source.startswith("~")
            or source.startswith(".")
        )

    def _looks_like_5etools_path(self, path: str) -> bool:
        """Check if path looks like a 5etools data directory."""
        path_lower = path.lower()
        return (
            "5etools" in path_lower
            or path_lower.endswith("/data")
            or path_lower.endswith("\\data")
        )

    def _is_source_abbreviation(self, source: str) -> bool:
        """Check if source looks like a 5e source abbreviation."""
        # Common pattern: 2-5 uppercase characters
        return (
            len(source) >= 2
            and len(source) <= 5
            and source.isupper()
            and source.isalpha()
        )

    def _is_url(self, source: str) -> bool:
        """Check if source is a URL."""
        return source.startswith(("http://", "https://"))

    def needs_migration(self, config: dict[str, Any]) -> bool:
        """Check if configuration needs migration."""
        # Check for old format indicators
        has_old_default_sources = "default_sources" in config
        has_old_content_format = "content" in config and isinstance(
            config.get("content"), dict
        )
        has_old_paths_format = "paths" in config and "data_path" in config.get(
            "paths", {}
        )
        missing_new_format = "data_sources" not in config

        return (
            has_old_default_sources
            or has_old_content_format
            or has_old_paths_format
            or missing_new_format
        )

    def create_migration_report(self) -> str:
        """Create a human-readable migration report."""
        if not self.migration_log:
            return "No migration changes were needed."

        report = "Configuration Migration Report:\n"
        report += "=" * 40 + "\n"

        for entry in self.migration_log:
            if entry.startswith("WARNING"):
                report += f"⚠️  {entry}\n"
            else:
                report += f"✅ {entry}\n"

        report += f"\nTotal changes: {len(self.migration_log)}"
        return report

    def preview_migration(self, old_config: dict[str, Any]) -> dict[str, Any]:
        """Preview what migration would do without making changes."""
        # Create a temporary migration instance to avoid affecting the main log
        temp_migration = ConfigurationMigration()
        migrated_config = temp_migration.migrate_configuration(old_config)

        return {
            "migrated_config": migrated_config.model_dump(),
            "migration_log": temp_migration.migration_log,
            "report": temp_migration.create_migration_report(),
        }

    def has_deprecated_patterns(self, config: dict[str, Any]) -> list[str]:
        """Identify deprecated configuration patterns."""
        deprecated = []

        if "default_sources" in config:
            deprecated.append(
                "'default_sources' - use three-tier data_sources configuration instead"
            )

        if "content" in config and "merger" in config["content"]:
            deprecated.append(
                "'content.merger' - use data_sources.performance.caching instead"
            )

        if "paths" in config and "data_path" in config["paths"]:
            deprecated.append(
                "'paths.data_path' - use data_sources.primary_override instead"
            )

        return deprecated
