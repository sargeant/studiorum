"""Global pytest configuration."""

import os
from pathlib import Path


def pytest_configure(config):
    """Configure pytest environment."""
    # Load test environment variables
    env_file = Path(__file__).parent / ".env.test"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)
