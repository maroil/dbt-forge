"""CLI smoke tests."""

from __future__ import annotations

import re
import subprocess
import sys
from unittest.mock import patch

from typer.testing import CliRunner

from dbt_forge import __version__
from dbt_forge.main import _module_available, app


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_module_version_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert f"dbt-forge v{__version__}" in _strip_ansi(result.stdout)


def test_module_help_lists_init_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = _strip_ansi(result.stdout)
    assert "Scaffold production-ready dbt projects with opinionated defaults." in out
    assert "init" in out
    assert "add" in out
    assert "Docs: https://dbt-forge.marou.one" in out


def test_init_dry_run_flag_in_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "init", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--dry-run" in _strip_ansi(result.stdout)


def test_add_help_lists_mart_and_source() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "add", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = _strip_ansi(result.stdout)
    assert "mart" in out
    assert "source" in out


def test_module_available_handles_missing_parent_package(monkeypatch) -> None:
    def fake_find_spec(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("importlib.util.find_spec", fake_find_spec)

    assert _module_available("google.cloud.bigquery") is False


def test_help_shows_grouped_panels() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbt_forge.main", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = _strip_ansi(result.stdout)
    assert "Scaffold" in out
    assert "Analyze" in out
    assert "Govern" in out
    assert "Migrate" in out


def test_adapters_command_reports_missing_optional_deps(monkeypatch) -> None:
    from dbt_forge.introspect import connectors

    runner = CliRunner()
    monkeypatch.setattr(connectors, "ADAPTER_MAP", {"bigquery": object, "duckdb": object})
    monkeypatch.setattr(
        connectors,
        "ADAPTER_DEPS",
        {"bigquery": "google-cloud-bigquery", "duckdb": "duckdb"},
    )
    monkeypatch.setattr(
        "dbt_forge.main._module_available",
        lambda name: name == "duckdb",
    )

    result = runner.invoke(app, ["adapters"])
    out = _strip_ansi(result.stdout)

    assert result.exit_code == 0
    assert "dbt-forge adapters" in out
    assert "bigquery" in out
    assert "not installed" in out
    assert "duckdb" in out
    assert "installed" in out


class TestInitReviewScreen:
    def test_review_screen_renders(self):
        from dbt_forge.cli.init import _show_review_screen
        from dbt_forge.prompts.questions import ProjectConfig

        config = ProjectConfig(
            project_name="test_proj",
            adapter="BigQuery",
            marts=["finance"],
            packages=["dbt-utils"],
            add_examples=True,
            add_sqlfluff=True,
        )
        with patch("dbt_forge.cli.init.questionary") as mock_q:
            mock_q.confirm.return_value.ask.return_value = True
            result = _show_review_screen(config)
            assert result is True

    def test_review_screen_abort(self):
        from dbt_forge.cli.init import _show_review_screen
        from dbt_forge.prompts.questions import ProjectConfig

        config = ProjectConfig(
            project_name="test_proj",
            adapter="BigQuery",
            marts=["finance"],
            packages=[],
            add_examples=False,
            add_sqlfluff=False,
        )
        with patch("dbt_forge.cli.init.questionary") as mock_q:
            mock_q.confirm.return_value.ask.return_value = False
            result = _show_review_screen(config)
            assert result is False

    def test_review_screen_skipped_in_defaults_mode(self):
        """When use_defaults=True, review screen is not shown."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("dbt_forge.cli.init._show_review_screen") as mock_review:
                from dbt_forge.cli.init import init_command

                init_command(
                    project_name="test_proj",
                    use_defaults=True,
                    output_dir=tmpdir,
                )
                mock_review.assert_not_called()
