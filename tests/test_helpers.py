"""Test helper functions for consistent test setup patterns."""

from __future__ import annotations

import gc
import logging

logger = logging.getLogger(__name__)


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
        # 1. Reset the service container (handles most singletons)
        # Do this first to create fresh instances
        from dnd5e.core.container import reset_global_container

        reset_global_container()
        logger.debug("Service container reset")

        # 2. Reset the content type resolver (holds onto old registry instance)
        from dnd5e.core.content_type_resolver import reset_content_type_resolver

        reset_content_type_resolver()
        logger.debug("Content type resolver reset")

        # 3. Reset the content type registry instance (preserves decorator registrations)
        from dnd5e.core.registry.content_type_registry import (
            reset_content_type_registry,
        )

        reset_content_type_registry()
        logger.debug("Content type registry reset (preserving decorator registrations)")

        # 4. Reset ContentFactory (clears both global instance and class state)
        # Do this before initialize_content_types() to ensure clean state
        from dnd5e.core.loaders.content_factory import reset_content_factory

        reset_content_factory()

        # 5. Initialize the content type registry (critical for all systems)
        # This must happen after service container reset to populate the fresh registry
        from dnd5e.core.registry import initialize_content_types

        initialize_content_types()
        logger.debug("Content type registry initialized")

        # 6. Reset disk-based cache
        from dnd5e.core.cache import CacheManager

        CacheManager.reset()

        # 7. Reset CLI-specific globals
        from dnd5e.cli.main import reset_cli_globals

        reset_cli_globals()

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
        from dnd5e.core.registry import initialize_content_types

        initialize_content_types()
        logger.debug("Registry-only test setup completed")
    except ImportError as e:
        logger.warning(f"Could not import registry initialization: {e}")
    except Exception as e:
        logger.error(f"Error during registry setup: {e}")
        raise
