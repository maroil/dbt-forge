"""Integration tests for the `add` subcommand."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig


def _base_config(tmpdir: str) -> ProjectConfig:
    return ProjectConfig(
        project_name="test_project",
        adapter="DuckDB",
        marts=["finance"],
        packages=[],
        add_examples=True,
        add_sqlfluff=False,
        ci_providers=[],
        output_dir=tmpdir,
    )


def _scaffold_project(tmpdir: str) -> Path:
    """Generate a full project and return its root directory."""
    config = _base_config(tmpdir)
    generate_project(config)
    return Path(tmpdir) / "test_project"


# ---------------------------------------------------------------------------
# add mart
# ---------------------------------------------------------------------------

class TestAddMart:
    def test_add_mart_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from dbt_forge.cli.add import add_mart
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["mart", "operations"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / "models" / "marts" / "operations" / "operations_orders.sql").exists()
            assert (project_root / "models" / "marts" / "operations" / "__operations__models.yml").exists()
            assert (
                project_root / "models" / "intermediate" / "operations"
                / "int_operations__orders_enriched.sql"
            ).exists()

    def test_add_mart_models_yml_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from dbt_forge.cli.add import add_app
                from typer.testing import CliRunner
                runner = CliRunner()
                runner.invoke(add_app, ["mart", "product"])
            finally:
                os.chdir(old_cwd)

            yml = project_root / "models" / "marts" / "product" / "__product__models.yml"
            data = yaml.safe_load(yml.read_text())
            assert "models" in data
            assert data["models"][0]["name"] == "product_orders"

    def test_add_mart_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            # finance was scaffolded by _base_config — its files should not be overwritten
            target = project_root / "models" / "marts" / "finance" / "finance_orders.sql"
            original_content = target.read_text()

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from dbt_forge.cli.add import add_app
                from typer.testing import CliRunner
                runner = CliRunner()
                runner.invoke(add_app, ["mart", "finance"])
            finally:
                os.chdir(old_cwd)

            # Content must not change because the file already existed
            assert target.read_text() == original_content


# ---------------------------------------------------------------------------
# add source
# ---------------------------------------------------------------------------

class TestAddSource:
    def test_add_source_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from dbt_forge.cli.add import add_app
                from typer.testing import CliRunner
                runner = CliRunner()
                result = runner.invoke(add_app, ["source", "salesforce"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            staging = project_root / "models" / "staging" / "salesforce"
            assert (staging / "_salesforce__sources.yml").exists()
            assert (staging / "_salesforce__models.yml").exists()
            assert (staging / "stg_salesforce__records.sql").exists()

    def test_add_source_sources_yml_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from dbt_forge.cli.add import add_app
                from typer.testing import CliRunner
                runner = CliRunner()
                runner.invoke(add_app, ["source", "stripe"])
            finally:
                os.chdir(old_cwd)

            staging = project_root / "models" / "staging" / "stripe"
            data = yaml.safe_load((staging / "_stripe__sources.yml").read_text())
            assert "sources" in data
            assert data["sources"][0]["name"] == "stripe"

    def test_add_source_outside_project_exits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                from dbt_forge.cli.add import add_app
                from typer.testing import CliRunner
                runner = CliRunner()
                result = runner.invoke(add_app, ["source", "hubspot"])
            finally:
                os.chdir(old_cwd)

            # Should exit non-zero because no dbt_project.yml found
            assert result.exit_code != 0
