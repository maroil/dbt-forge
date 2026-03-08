"""Tests for Phase 2 add commands: model, test, package."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig


def _scaffold(tmpdir: str) -> Path:
    config = ProjectConfig(
        project_name="test_project",
        adapter="DuckDB",
        marts=["finance"],
        packages=["dbt-utils"],
        add_examples=True,
        add_sqlfluff=False,
        ci_providers=[],
        output_dir=tmpdir,
    )
    generate_project(config)
    return Path(tmpdir) / "test_project"


# ---------------------------------------------------------------------------
# add model (non-interactive — we test the template rendering directly)
# ---------------------------------------------------------------------------

class TestAddModelTemplates:
    def test_model_sql_renders_staging(self):
        from dbt_forge.generator.renderer import render_template
        ctx = {
            "model_name": "stg_stripe__payments",
            "name": "payments",
            "layer": "staging",
            "materialization": "view",
            "source_name": "stripe",
            "entity": "payments",
            "description": "Stripe payments",
            "columns": [
                {"name": "id", "description": "Primary key", "tests": ["unique", "not_null"]},
                {"name": "amount", "description": "Payment amount", "tests": []},
            ],
            "project_name": "test_project",
        }
        content = render_template("add/model.sql.j2", ctx)
        assert "source('stripe', 'payments')" in content
        assert "id" in content
        assert "amount" in content

    def test_model_sql_renders_incremental(self):
        from dbt_forge.generator.renderer import render_template
        ctx = {
            "model_name": "fct_orders",
            "name": "orders",
            "layer": "marts",
            "materialization": "incremental",
            "source_name": "",
            "entity": "orders",
            "description": "",
            "columns": [],
            "project_name": "test_project",
        }
        content = render_template("add/model.sql.j2", ctx)
        assert "is_incremental()" in content
        assert "materialized='incremental'" in content

    def test_model_yml_renders(self):
        from dbt_forge.generator.renderer import render_template
        ctx = {
            "model_name": "stg_stripe__payments",
            "materialization": "view",
            "description": "Stripe payments",
            "columns": [
                {"name": "id", "description": "PK", "tests": ["unique", "not_null"]},
            ],
        }
        content = render_template("add/model.yml.j2", ctx)
        data = yaml.safe_load(content)
        assert data["models"][0]["name"] == "stg_stripe__payments"
        assert data["models"][0]["columns"][0]["name"] == "id"
        assert "unique" in data["models"][0]["columns"][0]["data_tests"]


# ---------------------------------------------------------------------------
# add test
# ---------------------------------------------------------------------------

class TestAddTest:
    def test_add_data_test(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                # Mock questionary to return "data"
                with patch("dbt_forge.cli.add.questionary") as mock_q:
                    mock_q.select.return_value.ask.return_value = "data"
                    mock_q.Style = lambda x: None
                    result = runner.invoke(add_app, ["test", "stg_orders"])
                    assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            test_file = project_root / "tests" / "assert_stg_orders_valid.sql"
            assert test_file.exists()
            content = test_file.read_text()
            assert "stg_orders" in content

    def test_add_unit_test(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                # Mock questionary to return "unit"
                with patch("dbt_forge.cli.add.questionary") as mock_q:
                    mock_q.select.return_value.ask.return_value = "unit"
                    mock_q.Style = lambda x: None
                    result = runner.invoke(add_app, ["test", "stg_orders"])
                    assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            test_file = project_root / "tests" / "unit" / "test_stg_orders.yml"
            assert test_file.exists()
            data = yaml.safe_load(test_file.read_text())
            assert "unit_tests" in data
            assert data["unit_tests"][0]["model"] == "stg_orders"


# ---------------------------------------------------------------------------
# add package
# ---------------------------------------------------------------------------

class TestAddPackage:
    def test_add_known_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["package", "dbt-codegen"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            data = yaml.safe_load((project_root / "packages.yml").read_text())
            hub_names = [p.get("package", "") for p in data["packages"]]
            assert "dbt-labs/codegen" in hub_names

    def test_add_duplicate_package_skips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                runner.invoke(add_app, ["package", "dbt-codegen"])
                result = runner.invoke(add_app, ["package", "dbt-codegen"])
                assert result.exit_code == 0
                assert "skip" in result.output
            finally:
                os.chdir(old_cwd)

    def test_add_unknown_package_exits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["package", "nonexistent-package"])
                assert result.exit_code != 0
            finally:
                os.chdir(old_cwd)

    def test_list_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["package", "--list"])
                assert result.exit_code == 0
                assert "dbt-utils" in result.output
                assert "elementary" in result.output
            finally:
                os.chdir(old_cwd)
