"""Tests for Phase 1 features: pre-commit, add ci, env config, CODEOWNERS."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig


def _config(**kwargs) -> ProjectConfig:
    defaults = dict(
        project_name="test_project",
        adapter="BigQuery",
        marts=["finance", "marketing"],
        packages=["dbt-utils"],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=["GitHub Actions"],
    )
    defaults.update(kwargs)
    return ProjectConfig(**defaults)


# ---------------------------------------------------------------------------
# 1.1 Pre-commit + Linting
# ---------------------------------------------------------------------------

class TestPreCommit:
    def test_pre_commit_config_created_when_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_pre_commit=True)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert (base / ".pre-commit-config.yaml").exists()

    def test_pre_commit_config_skipped_when_not_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_pre_commit=False)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert not (base / ".pre-commit-config.yaml").exists()

    def test_pre_commit_config_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_pre_commit=True)
            generate_project(config)
            yml = Path(tmpdir) / "test_project" / ".pre-commit-config.yaml"
            data = yaml.safe_load(yml.read_text())
            assert "repos" in data

    def test_pre_commit_includes_sqlfluff_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_pre_commit=True, add_sqlfluff=True)
            generate_project(config)
            content = (Path(tmpdir) / "test_project" / ".pre-commit-config.yaml").read_text()
            assert "sqlfluff" in content

    def test_pre_commit_excludes_sqlfluff_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_pre_commit=True, add_sqlfluff=False)
            generate_project(config)
            content = (Path(tmpdir) / "test_project" / ".pre-commit-config.yaml").read_text()
            assert "sqlfluff" not in content

    def test_editorconfig_created_with_pre_commit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_pre_commit=True)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert (base / ".editorconfig").exists()
            content = (base / ".editorconfig").read_text()
            assert "utf-8" in content
            assert "indent_size" in content

    def test_sqlfluffignore_created_with_sqlfluff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_sqlfluff=True)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert (base / ".sqlfluffignore").exists()
            content = (base / ".sqlfluffignore").read_text()
            assert "target/" in content
            assert "dbt_packages/" in content

    def test_sqlfluffignore_not_created_without_sqlfluff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_sqlfluff=False)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert not (base / ".sqlfluffignore").exists()


class TestAddPreCommitCommand:
    def test_add_pre_commit_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_sqlfluff=True)
            generate_project(config)
            project_root = Path(tmpdir) / "test_project"

            # Remove pre-commit config if it exists
            pc = project_root / ".pre-commit-config.yaml"
            if pc.exists():
                pc.unlink()

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["pre-commit"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / ".pre-commit-config.yaml").exists()
            assert (project_root / ".editorconfig").exists()
            assert (project_root / ".sqlfluffignore").exists()


# ---------------------------------------------------------------------------
# 1.2 add ci
# ---------------------------------------------------------------------------

class TestAddCi:
    def test_add_ci_github(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, ci_providers=[])
            generate_project(config)
            project_root = Path(tmpdir) / "test_project"

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["ci", "github"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            ci = project_root / ".github" / "workflows" / "dbt_ci.yml"
            assert ci.exists()
            data = yaml.safe_load(ci.read_text())
            assert "jobs" in data

    def test_add_ci_gitlab(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, ci_providers=[])
            generate_project(config)
            project_root = Path(tmpdir) / "test_project"

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["ci", "gitlab"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / ".gitlab-ci.yml").exists()

    def test_add_ci_bitbucket(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, ci_providers=[])
            generate_project(config)
            project_root = Path(tmpdir) / "test_project"

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["ci", "bitbucket"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            assert (project_root / "bitbucket-pipelines.yml").exists()

    def test_add_ci_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, ci_providers=["GitHub Actions"])
            generate_project(config)
            project_root = Path(tmpdir) / "test_project"
            ci = project_root / ".github" / "workflows" / "dbt_ci.yml"
            original = ci.read_text()

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["ci", "github"])
                assert result.exit_code == 0
            finally:
                os.chdir(old_cwd)

            assert ci.read_text() == original

    def test_add_ci_unknown_provider_exits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, ci_providers=[])
            generate_project(config)
            project_root = Path(tmpdir) / "test_project"

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["ci", "jenkins"])
                assert result.exit_code != 0
            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# 1.3 Environment Config
# ---------------------------------------------------------------------------

class TestEnvConfig:
    def test_env_example_created_when_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_env_config=True)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert (base / ".env.example").exists()

    def test_env_example_skipped_when_not_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_env_config=False)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert not (base / ".env.example").exists()

    def test_env_example_contains_adapter_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_env_config=True, adapter="Snowflake")
            generate_project(config)
            content = (Path(tmpdir) / "test_project" / ".env.example").read_text()
            assert "DBT_PROFILES_DIR" in content
            assert "Snowflake" in content

    def test_generate_schema_name_created_when_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_env_config=True)
            generate_project(config)
            macro = Path(tmpdir) / "test_project" / "macros" / "generate_schema_name.sql"
            assert macro.exists()
            content = macro.read_text()
            assert "generate_schema_name" in content
            assert "target.name" in content

    def test_generate_schema_name_skipped_when_not_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, add_env_config=False)
            generate_project(config)
            macro = Path(tmpdir) / "test_project" / "macros" / "generate_schema_name.sql"
            assert not macro.exists()


# ---------------------------------------------------------------------------
# 1.4 CODEOWNERS
# ---------------------------------------------------------------------------

class TestCodeowners:
    def test_codeowners_created_when_team_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, team_owner="@my-org/data-team")
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert (base / "CODEOWNERS").exists()

    def test_codeowners_skipped_when_team_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, team_owner="")
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            assert not (base / "CODEOWNERS").exists()

    def test_codeowners_contains_team_and_marts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(
                output_dir=tmpdir,
                team_owner="@acme/analytics",
                marts=["finance", "marketing"],
            )
            generate_project(config)
            content = (Path(tmpdir) / "test_project" / "CODEOWNERS").read_text()
            assert "@acme/analytics" in content
            assert "models/marts/finance/" in content
            assert "models/marts/marketing/" in content


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

class TestNewConfigFields:
    def test_new_fields_default_false(self):
        c = _config()
        assert c.add_pre_commit is False
        assert c.add_env_config is False
        assert c.team_owner == ""

    def test_new_fields_can_be_set(self):
        c = ProjectConfig(
            project_name="p", adapter="BigQuery", marts=[], packages=[],
            add_examples=True, add_sqlfluff=True, ci_providers=[],
            add_pre_commit=True, add_env_config=True, team_owner="@team",
        )
        assert c.add_pre_commit is True
        assert c.add_env_config is True
        assert c.team_owner == "@team"
