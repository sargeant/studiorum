"""Test helper functions for consistent test setup patterns."""

from __future__ import annotations

import gc
import logging

logger = logging.getLogger(__name__)


def reset_test_environment(*, collect_garbage: bool = True) -> None:
    """Reset the entire test environment for complete isolation.

    This function provides a standardized way to reset all global state
    between tests, ensuring complete isolation and preventing test failures
    due to contaminated state.

    This should be called in setup_method() for any test class that:
    - Uses Omnidexer instances
    - Tests that load actual data files
    """
    try:
        # 0. Use the test configuration, never a developer's own
        import os

        from studiorum.core.config.unified_config import reset_app_config

        if "STUDIORUM_CONFIG_FILE" not in os.environ:
            os.environ["STUDIORUM_CONFIG_FILE"] = "tests/test-config.yaml"

        # Reset app config to pick up environment changes
        reset_app_config()

        from studiorum.core.loaders import item_types

        item_types.reset()

        # 1. Forget Services built outside a CLI invocation
        from studiorum.cli.context import reset_services
        from studiorum.mcp.context import reset_mcp_services

        reset_services()
        reset_mcp_services()

        # 2.1. Reset the entry type registry global instance
        from studiorum.core.entry_registry import reset_global_registry

        reset_global_registry()
        logger.debug("Entry type registry global instance reset")

        # 4. Reset disk-based cache
        from studiorum.core.cache import CacheManager

        CacheManager.reset()

        # 8. Force garbage collection to clean up any lingering objects. The
        # per-test autouse fixture skips this: it costs ~30 ms a call.
        if collect_garbage:
            gc.collect()

        logger.debug("Test environment reset completed")

    except ImportError as e:
        logger.warning(f"Could not import reset function: {e}")
    except Exception as e:
        logger.error(f"Error during test environment reset: {e}")
        raise
