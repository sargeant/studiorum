"""Importing the render layer first must not break the CLI's command imports."""

import subprocess
import sys


def test_latex_engine_before_cli() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import studiorum.latex_engine.core.template_engine\n"
            "import studiorum.cli.main\n"
            "from studiorum.cli.main import app\n"
            "print(sorted(g.name for g in app.registered_groups))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Failed to import CLI commands" not in result.stdout + result.stderr
    assert "convert" in result.stdout
