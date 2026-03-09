"""Integration tests for the `add` subcommand."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

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
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["mart", "operations"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (
                project_root / "models" / "marts" / "operations" / "operations_orders.sql"
            ).exists()
            assert (
                project_root / "models" / "marts" / "operations" / "__operations__models.yml"
            ).exists()
            assert (
                project_root
                / "models"
                / "intermediate"
                / "operations"
                / "int_operations__orders_enriched.sql"
            ).exists()

    def test_add_mart_models_yml_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

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
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

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
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

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
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

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
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["source", "hubspot"])
            finally:
                os.chdir(old_cwd)

            # Should exit non-zero because no dbt_project.yml found
            assert result.exit_code != 0


# ---------------------------------------------------------------------------
# add snapshot
# ---------------------------------------------------------------------------


class TestAddSnapshot:
    def test_add_snapshot_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["snapshot", "orders"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / "snapshots" / "orders.sql").exists()

    def test_add_snapshot_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["snapshot", "customers"])
                target = project_root / "snapshots" / "customers.sql"
                original = target.read_text()
                runner.invoke(add_app, ["snapshot", "customers"])
                assert target.read_text() == original
            finally:
                os.chdir(old_cwd)

    def test_add_snapshot_outside_project_exits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["snapshot", "orders"])
            finally:
                os.chdir(old_cwd)

            assert result.exit_code != 0


# ---------------------------------------------------------------------------
# add seed
# ---------------------------------------------------------------------------


class TestAddSeed:
    def test_add_seed_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["seed", "dim_country"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / "seeds" / "dim_country.csv").exists()
            assert (project_root / "seeds" / "_dim_country__seeds.yml").exists()

    def test_add_seed_yml_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["seed", "dim_region"])
            finally:
                os.chdir(old_cwd)

            yml = project_root / "seeds" / "_dim_region__seeds.yml"
            data = yaml.safe_load(yml.read_text())
            assert "seeds" in data
            assert data["seeds"][0]["name"] == "dim_region"

    def test_add_seed_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["seed", "dim_status"])
                target = project_root / "seeds" / "dim_status.csv"
                original = target.read_text()
                runner.invoke(add_app, ["seed", "dim_status"])
                assert target.read_text() == original
            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# add exposure
# ---------------------------------------------------------------------------


class TestAddExposure:
    def test_add_exposure_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["exposure", "weekly_revenue"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / "models" / "marts" / "__weekly_revenue__exposures.yml").exists()

    def test_add_exposure_yml_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["exposure", "sales_report"])
            finally:
                os.chdir(old_cwd)

            yml = project_root / "models" / "marts" / "__sales_report__exposures.yml"
            data = yaml.safe_load(yml.read_text())
            assert "exposures" in data
            assert data["exposures"][0]["name"] == "sales_report"

    def test_add_exposure_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["exposure", "daily_summary"])
                target = project_root / "models" / "marts" / "__daily_summary__exposures.yml"
                original = target.read_text()
                runner.invoke(add_app, ["exposure", "daily_summary"])
                assert target.read_text() == original
            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# add macro
# ---------------------------------------------------------------------------


class TestAddMacro:
    def test_add_macro_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                result = runner.invoke(add_app, ["macro", "cents_to_dollars"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / "macros" / "cents_to_dollars.sql").exists()

    def test_add_macro_contains_macro_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["macro", "my_util"])
            finally:
                os.chdir(old_cwd)

            content = (project_root / "macros" / "my_util.sql").read_text()
            assert "macro my_util" in content
            assert "endmacro" in content

    def test_add_macro_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner

                from dbt_forge.cli.add import add_app

                runner = CliRunner()
                runner.invoke(add_app, ["macro", "my_helper"])
                target = project_root / "macros" / "my_helper.sql"
                original = target.read_text()
                runner.invoke(add_app, ["macro", "my_helper"])
                assert target.read_text() == original
            finally:
                os.chdir(old_cwd)
