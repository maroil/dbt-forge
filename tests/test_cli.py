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
    assert "add" in result.stdout


def test_init_dry_run_flag_in_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "init", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--dry-run" in result.stdout


def test_add_help_lists_mart_and_source() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "add", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mart" in result.stdout
    assert "source" in result.stdout
