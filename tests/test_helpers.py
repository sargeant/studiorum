"""Test helper functions for consistent test setup patterns."""

from __future__ import annotations

import gc
import logging

logger = logging.getLogger(__name__)


def reset_all_containers() -> None:
    """Reset all container systems (legacy and modern) for complete test isolation.

    This function handles the transition period where both old and new container
    systems may be in use. It ensures all container state is properly cleaned up
    for parallel test execution.
    """
    try:
        # Reset legacy container system
        from studiorum.core.container import reset_global_container

        reset_global_container()
        logger.debug("Legacy service container reset")
    except ImportError:
        logger.debug("Legacy container system not available")
    except Exception as e:
        logger.warning(f"Failed to reset legacy container: {e}")

    try:
        # Reset modern async container system
        from studiorum.cli.async_bridge import reset_global_async_container

        reset_global_async_container()
        logger.debug("Modern async service container reset")
    except ImportError:
        logger.debug("Modern async container system not available")
    except Exception as e:
        logger.warning(f"Failed to reset async container: {e}")


def reset_test_environment() -> None:
    """Reset the entire test environment for complete isolation.

    This function provides a standardized way to reset all global state
    between tests, ensuring complete isolation and preventing test failures
    due to contaminated state.

    This should be called in setup_method() for any test class that:
    - Uses Omnidexer instances
    - Uses ConfigurableSourceManager
    - Uses ContentFactory
    - Uses any content type registry functionality
    - Tests that load actual data files
    """
    try:
        # 1. Reset both container systems (legacy and modern)
        # Do this first to create fresh instances
        reset_all_containers()
        logger.debug("All service containers reset")

        # 2. Reset the content type registry instance (preserves decorator registrations)
        from studiorum.core.registry.content_type_registry import (
            reset_content_type_registry,
        )

        reset_content_type_registry()
        logger.debug("Content type registry reset (preserving decorator registrations)")

        # 3. ContentFactory is now managed by the DI container
        # It gets reset when the container is reset, so no manual reset needed

        # 4. Reset disk-based cache
        from studiorum.core.cache import CacheManager

        CacheManager.reset()

        # 5. Reset CLI-specific globals
        from studiorum.cli.main import reset_cli_globals

        reset_cli_globals()

        # 6. Reset content configuration manager to use temporary config
        from studiorum.core.config.sources import reset_config_manager

        reset_config_manager()
        logger.debug("Configuration manager reset to use temporary config")

        # 7. Initialize the content type registry (critical for all systems)
        # This MUST happen LAST to ensure the interface registry is populated after all resets
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()
        logger.debug("Content type registry initialized")

        # 8. Force garbage collection to clean up any lingering objects
        gc.collect()

        logger.debug("Test environment reset completed")

    except ImportError as e:
        logger.warning(f"Could not import reset function: {e}")
    except Exception as e:
        logger.error(f"Error during test environment reset: {e}")
        raise


def setup_test_with_registry() -> None:
    """Simplified setup for tests that need registry initialization.

    Use this in tests that need the content type registry but don't
    need the full environment reset (e.g., unit tests with mocks).
    """
    try:
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()
        logger.debug("Registry-only test setup completed")
    except ImportError as e:
        logger.warning(f"Could not import registry initialization: {e}")
    except Exception as e:
        logger.error(f"Error during registry setup: {e}")
        raise
