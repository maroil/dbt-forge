"""CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys

from dbt_forge import __version__


def test_module_version_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert f"dbt-forge v{__version__}" in result.stdout


def test_module_help_lists_init_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Scaffold production-ready dbt projects with opinionated defaults." in result.stdout
    assert "init" in result.stdout
