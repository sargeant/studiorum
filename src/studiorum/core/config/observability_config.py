"""
Configuration module for image processing observability.

This module provides configuration options for the observability system,
integrating with the existing unified configuration infrastructure to allow
fine-tuning of monitoring, performance tracking, and reporting features.

Created: 2025-01-23
Status: Phase 4 - Observability Integration
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from studiorum.core.logging.image_observability import ImageProcessingStage


class ObservabilityMetricsConfig(BaseModel):
    """Configuration for metrics collection and aggregation."""

    enable_performance_tracking: bool = Field(
        default=True,
        description="Enable performance metrics collection",
    )
    enable_cache_monitoring: bool = Field(
        default=True,
        description="Enable cache operation monitoring",
    )
    enable_resource_monitoring: bool = Field(
        default=True,
        description="Enable memory and CPU usage monitoring",
    )
    enable_batch_analytics: bool = Field(
        default=True,
        description="Enable batch processing analytics",
    )

    # Performance thresholds
    performance_warning_threshold_ms: float = Field(
        default=5000.0,
        description="Warning threshold for operation duration (milliseconds)",
    )
    memory_warning_threshold_mb: float = Field(
        default=1000.0,
        description="Warning threshold for memory usage (MB)",
    )
    cache_hit_ratio_warning_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Warning threshold for cache hit ratio",
    )
    success_rate_warning_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Warning threshold for operation success rate",
    )

    # Reporting intervals
    statistics_reset_interval_hours: int = Field(
        default=24,
        ge=1,
        description="Hours between automatic statistics resets",
    )
    performance_report_interval_minutes: int = Field(
        default=60,
        ge=1,
        description="Minutes between automatic performance reports",
    )


class LogfireIntegrationConfig(BaseModel):
    """Configuration for Logfire integration and structured logging."""

    enable_logfire_integration: bool = Field(
        default=True,
        description="Enable Logfire structured logging integration",
    )
    log_operation_details: bool = Field(
        default=True,
        description="Log detailed operation information",
    )
    log_cache_operations: bool = Field(
        default=True,
        description="Log cache hit/miss operations",
    )
    log_batch_summaries: bool = Field(
        default=True,
        description="Log batch processing summaries",
    )
    log_performance_reports: bool = Field(
        default=True,
        description="Log performance reports automatically",
    )

    # Logfire-specific settings
    include_metadata_in_logs: bool = Field(
        default=True,
        description="Include operation metadata in log entries",
    )
    include_error_context: bool = Field(
        default=True,
        description="Include full error context in failure logs",
    )

    # Log level filtering
    min_operation_duration_to_log_ms: float = Field(
        default=100.0,
        description="Minimum operation duration to log (milliseconds)",
    )
    log_only_errors_for_stages: list[str] = Field(
        default_factory=list,
        description="Stages to log only when errors occur",
    )


class CLIReportingConfig(BaseModel):
    """Configuration for CLI-friendly progress reporting."""

    enable_progress_reporting: bool = Field(
        default=True,
        description="Enable CLI progress reporting",
    )
    enable_completion_summaries: bool = Field(
        default=True,
        description="Enable operation completion summaries",
    )

    # Progress reporting behavior
    progress_update_interval_seconds: float = Field(
        default=0.5,
        ge=0.1,
        description="Seconds between progress updates",
    )
    show_eta_estimates: bool = Field(
        default=True,
        description="Show estimated time to completion",
    )
    show_throughput_metrics: bool = Field(
        default=True,
        description="Show operations per second metrics",
    )

    # Quiet mode settings
    respect_quiet_flag: bool = Field(
        default=True,
        description="Respect CLI quiet flags for output suppression",
    )
    quiet_mode_exceptions: list[str] = Field(
        default_factory=lambda: ["error", "critical"],
        description="Message types to show even in quiet mode",
    )


class MCPObservabilityConfig(BaseModel):
    """Configuration for MCP-specific observability features."""

    enable_request_isolation: bool = Field(
        default=True,
        description="Enable per-request observability isolation",
    )
    enable_concurrent_monitoring: bool = Field(
        default=True,
        description="Enable monitoring of concurrent operations",
    )

    # Request context settings
    track_request_lifecycle: bool = Field(
        default=True,
        description="Track full request lifecycle from start to finish",
    )
    include_request_id_in_logs: bool = Field(
        default=True,
        description="Include request IDs in all log entries",
    )

    # Resource monitoring for async operations
    monitor_async_resource_usage: bool = Field(
        default=True,
        description="Monitor resource usage for async operations",
    )
    async_monitoring_sampling_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Sampling rate for async resource monitoring (0.0-1.0)",
    )


class DashboardConfig(BaseModel):
    """Configuration for dashboard data generation and visualization."""

    enable_dashboard_data: bool = Field(
        default=True,
        description="Generate data for observability dashboards",
    )
    dashboard_data_retention_hours: int = Field(
        default=168,  # 7 days
        ge=1,
        description="Hours to retain dashboard data",
    )

    # Dashboard metrics
    include_stage_breakdown: bool = Field(
        default=True,
        description="Include processing stage breakdown in dashboard data",
    )
    include_content_type_analysis: bool = Field(
        default=True,
        description="Include content type analysis in dashboard data",
    )
    include_error_categorization: bool = Field(
        default=True,
        description="Include error categorization in dashboard data",
    )
    include_trend_analysis: bool = Field(
        default=True,
        description="Include trend analysis over time",
    )

    # Real-time updates
    enable_real_time_updates: bool = Field(
        default=True,
        description="Enable real-time dashboard updates",
    )
    real_time_update_interval_seconds: int = Field(
        default=5,
        ge=1,
        description="Seconds between real-time dashboard updates",
    )


class ImageObservabilityConfig(BaseModel):
    """Comprehensive configuration for image processing observability."""

    # Sub-configuration sections
    metrics: ObservabilityMetricsConfig = Field(
        default_factory=ObservabilityMetricsConfig,
        description="Metrics collection and aggregation settings",
    )
    logfire: LogfireIntegrationConfig = Field(
        default_factory=LogfireIntegrationConfig,
        description="Logfire integration settings",
    )
    cli_reporting: CLIReportingConfig = Field(
        default_factory=CLIReportingConfig,
        description="CLI progress reporting settings",
    )
    mcp: MCPObservabilityConfig = Field(
        default_factory=MCPObservabilityConfig,
        description="MCP-specific observability settings",
    )
    dashboard: DashboardConfig = Field(
        default_factory=DashboardConfig,
        description="Dashboard data generation settings",
    )

    # Global observability settings
    enable_observability: bool = Field(
        default=True,
        description="Master switch for all observability features",
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode for observability system",
    )

    # Stage-specific configuration
    enabled_stages: list[str] = Field(
        default_factory=lambda: [stage.value for stage in ImageProcessingStage],
        description="List of processing stages to monitor",
    )
    disabled_stages: list[str] = Field(
        default_factory=list,
        description="List of processing stages to exclude from monitoring",
    )

    # Content type filtering
    monitored_content_types: list[str] = Field(
        default_factory=list,  # Empty list = monitor all
        description="Content types to monitor (empty = all)",
    )
    ignored_content_types: list[str] = Field(
        default_factory=list,
        description="Content types to exclude from monitoring",
    )

    def is_stage_enabled(self, stage: ImageProcessingStage) -> bool:
        """Check if a processing stage is enabled for monitoring.

        Args:
            stage: Processing stage to check

        Returns:
            True if stage should be monitored
        """
        if not self.enable_observability:
            return False

        stage_name = stage.value

        # Check disabled stages first
        if stage_name in self.disabled_stages:
            return False

        # Check enabled stages
        if self.enabled_stages and stage_name not in self.enabled_stages:
            return False

        return True

    def is_content_type_monitored(self, content_type: str) -> bool:
        """Check if a content type should be monitored.

        Args:
            content_type: Content type to check

        Returns:
            True if content type should be monitored
        """
        if not self.enable_observability:
            return False

        # Check ignored content types first
        if content_type in self.ignored_content_types:
            return False

        # Check monitored content types (empty = monitor all)
        if (
            self.monitored_content_types
            and content_type not in self.monitored_content_types
        ):
            return False

        return True

    def should_log_operation(
        self,
        stage: ImageProcessingStage,
        duration_ms: float,
        has_error: bool = False,
    ) -> bool:
        """Determine if an operation should be logged based on configuration.

        Args:
            stage: Processing stage
            duration_ms: Operation duration in milliseconds
            has_error: Whether the operation had an error

        Returns:
            True if operation should be logged
        """
        if not self.logfire.enable_logfire_integration:
            return False

        # Always log errors
        if has_error:
            return True

        # Check stage-specific logging rules
        if stage.value in self.logfire.log_only_errors_for_stages:
            return False

        # Check duration threshold
        if duration_ms < self.logfire.min_operation_duration_to_log_ms:
            return False

        return True

    def get_performance_warnings(self, stats: dict[str, Any]) -> list[str]:
        """Get performance warnings based on current statistics.

        Args:
            stats: Current statistics dictionary

        Returns:
            List of warning messages
        """
        warnings = []

        # Check success rate
        success_rate = stats.get("success_rate", 1.0)
        if success_rate < self.metrics.success_rate_warning_threshold:
            warnings.append(
                f"Success rate ({success_rate:.1%}) below threshold "
                f"({self.metrics.success_rate_warning_threshold:.1%})"
            )

        # Check cache hit ratio
        cache_hit_ratio = stats.get("cache_hit_ratio", 1.0)
        if cache_hit_ratio < self.metrics.cache_hit_ratio_warning_threshold:
            warnings.append(
                f"Cache hit ratio ({cache_hit_ratio:.1%}) below threshold "
                f"({self.metrics.cache_hit_ratio_warning_threshold:.1%})"
            )

        # Check average duration
        avg_duration = stats.get("avg_duration_ms", 0.0)
        if avg_duration > self.metrics.performance_warning_threshold_ms:
            warnings.append(
                f"Average duration ({avg_duration:.1f}ms) above threshold "
                f"({self.metrics.performance_warning_threshold_ms:.1f}ms)"
            )

        # Check memory usage
        memory_peak = stats.get("memory_peak_mb", 0.0)
        if memory_peak > self.metrics.memory_warning_threshold_mb:
            warnings.append(
                f"Peak memory usage ({memory_peak:.1f}MB) above threshold "
                f"({self.metrics.memory_warning_threshold_mb:.1f}MB)"
            )

        return warnings

    def model_dump_example(self) -> dict[str, Any]:
        """Generate example configuration for documentation.

        Returns:
            Example configuration dictionary
        """
        return {
            "observability": {
                "enable_observability": True,
                "debug_mode": False,
                "metrics": {
                    "enable_performance_tracking": True,
                    "enable_cache_monitoring": True,
                    "performance_warning_threshold_ms": 5000.0,
                    "cache_hit_ratio_warning_threshold": 0.7,
                },
                "logfire": {
                    "enable_logfire_integration": True,
                    "log_operation_details": True,
                    "min_operation_duration_to_log_ms": 100.0,
                },
                "cli_reporting": {
                    "enable_progress_reporting": True,
                    "progress_update_interval_seconds": 0.5,
                    "show_eta_estimates": True,
                },
                "mcp": {
                    "enable_request_isolation": True,
                    "monitor_async_resource_usage": True,
                },
                "dashboard": {
                    "enable_dashboard_data": True,
                    "dashboard_data_retention_hours": 168,
                    "enable_real_time_updates": True,
                },
                "enabled_stages": [
                    "discovery",
                    "placement",
                    "optimization",
                    "rendering",
                ],
                "monitored_content_types": [],  # Empty = all
            }
        }
