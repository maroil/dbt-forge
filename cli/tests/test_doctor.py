"""Tests for the dbt-forge doctor command."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from dbt_forge.cli.doctor import (
    check_disabled_models,
    check_gitignore,
    check_hardcoded_refs,
    check_naming_conventions,
    check_orphaned_yml,
    check_packages_pinned,
    check_schema_coverage,
    check_source_freshness,
    check_sqlfluff_config,
    check_test_coverage,
    fix_schema_coverage,
)
from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig


def _generate_project(tmpdir: str, **kwargs) -> Path:
    defaults = dict(
        project_name="test_project",
        adapter="DuckDB",
        marts=["finance"],
        packages=["dbt-utils"],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=[],
        output_dir=tmpdir,
    )
    defaults.update(kwargs)
    config = ProjectConfig(**defaults)
    generate_project(config)
    return Path(tmpdir) / "test_project"


class TestNamingConventions:
    def test_passes_for_correct_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_naming_conventions(root)
            assert result.passed

    def test_fails_for_bad_staging_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            bad = root / "models" / "staging" / "bad_model.sql"
            bad.write_text("SELECT 1")
            result = check_naming_conventions(root)
            assert not result.passed
            assert "stg_" in result.message


class TestSchemaCoverage:
    def test_passes_for_documented_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_schema_coverage(root)
            assert result.passed

    def test_fails_for_undocumented_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            undoc = root / "models" / "marts" / "finance" / "lonely_model.sql"
            undoc.write_text("SELECT 1")
            result = check_schema_coverage(root)
            assert not result.passed


class TestTestCoverage:
    def test_fails_for_untested_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            untested = root / "models" / "marts" / "finance" / "no_tests_model.sql"
            untested.write_text("SELECT 1")
            # Add YAML but no tests
            yml = root / "models" / "marts" / "finance" / "_no_tests_model__models.yml"
            yml.write_text(yaml.dump({
                "version": 2,
                "models": [{"name": "no_tests_model", "columns": []}],
            }))
            result = check_test_coverage(root)
            assert not result.passed


class TestHardcodedRefs:
    def test_passes_for_clean_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_hardcoded_refs(root)
            assert result.passed

    def test_fails_for_hardcoded_ref(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            bad = root / "models" / "marts" / "finance" / "hardcoded.sql"
            bad.write_text("SELECT * FROM my_database.my_schema.my_table")
            result = check_hardcoded_refs(root)
            assert not result.passed


class TestPackagesPinned:
    def test_passes_for_pinned_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_packages_pinned(root)
            assert result.passed

    def test_fails_for_unpinned_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            pkg = root / "packages.yml"
            pkg.write_text(yaml.dump({
                "packages": [{"package": "dbt-labs/dbt_utils"}]
            }))
            result = check_packages_pinned(root)
            assert not result.passed


class TestSourceFreshness:
    def test_passes_when_freshness_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_source_freshness(root)
            assert result.passed

    def test_fails_when_freshness_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            src = root / "models" / "staging" / "no_fresh" / "_no_fresh__sources.yml"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(yaml.dump({
                "sources": [{"name": "no_fresh", "tables": [{"name": "t1"}]}]
            }))
            result = check_source_freshness(root)
            assert not result.passed


class TestOrphanedYml:
    def test_passes_for_valid_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_orphaned_yml(root)
            assert result.passed

    def test_fails_for_orphaned_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            yml = root / "models" / "marts" / "finance" / "_orphan__models.yml"
            yml.write_text(yaml.dump({
                "models": [{"name": "ghost_model"}]
            }))
            result = check_orphaned_yml(root)
            assert not result.passed


class TestSqlfluffConfig:
    def test_passes_when_config_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir, add_sqlfluff=True)
            result = check_sqlfluff_config(root)
            assert result.passed

    def test_fails_when_config_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir, add_sqlfluff=False)
            result = check_sqlfluff_config(root)
            assert not result.passed


class TestGitignore:
    def test_passes_for_good_gitignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_gitignore(root)
            assert result.passed

    def test_fails_when_gitignore_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            (root / ".gitignore").unlink()
            result = check_gitignore(root)
            assert not result.passed


class TestDisabledModels:
    def test_passes_for_no_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            result = check_disabled_models(root)
            assert result.passed

    def test_fails_for_disabled_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            yml = root / "models" / "marts" / "finance" / "_disabled__models.yml"
            yml.write_text(yaml.dump({
                "models": [{"name": "old_model", "config": {"enabled": False}}]
            }))
            result = check_disabled_models(root)
            assert not result.passed


class TestFixSchemaCoverage:
    def test_generates_stubs_for_undocumented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            undoc = root / "models" / "marts" / "finance" / "lonely_model.sql"
            undoc.write_text("SELECT 1")
            fixed = fix_schema_coverage(root)
            assert fixed == 1
            stub = root / "models" / "marts" / "finance" / "_lonely_model__models.yml"
            assert stub.exists()
            data = yaml.safe_load(stub.read_text())
            assert data["models"][0]["name"] == "lonely_model"


class TestDoctorCli:
    def test_doctor_runs_from_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["doctor"])
                assert result.exit_code == 0, result.output
                assert "passed" in result.output
            finally:
                os.chdir(old_cwd)

    def test_doctor_check_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["doctor", "--check", "gitignore"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

    def test_doctor_fix_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _generate_project(tmpdir)
            # Add undocumented model
            undoc = root / "models" / "marts" / "finance" / "fix_me.sql"
            undoc.write_text("SELECT 1")

            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["doctor", "--fix"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            stub = root / "models" / "marts" / "finance" / "_fix_me__models.yml"
            assert stub.exists()
