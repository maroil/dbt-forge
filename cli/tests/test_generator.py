"""Tests for the project generator."""

from __future__ import annotations

import tempfile
from pathlib import Path

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig


def _default_config(**kwargs) -> ProjectConfig:
    defaults = dict(
        project_name="test_project",
        adapter="BigQuery",
        marts=["finance", "marketing"],
        packages=["dbt-utils", "dbt-expectations"],
        add_examples=True,
        add_sqlfluff=True,
        ci_providers=["GitHub Actions"],
    )
    defaults.update(kwargs)
    return ProjectConfig(**defaults)


def test_generate_creates_output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        generate_project(config)
        project_dir = Path(tmpdir) / "test_project"
        assert project_dir.is_dir()


def test_core_files_exist():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        generate_project(config)
        base = Path(tmpdir) / "test_project"

        assert (base / "pyproject.toml").exists()
        assert (base / "dbt_project.yml").exists()
        assert (base / "packages.yml").exists()
        assert (base / ".gitignore").exists()
        assert (base / ".env").exists()
        assert (base / "README.md").exists()
        assert (base / "profiles" / "profiles.yml").exists()
        assert (base / "selectors.yml").exists()


def test_pyproject_toml_contains_adapter_package():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, adapter="Snowflake")
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "pyproject.toml").read_text()
        assert "dbt-snowflake" in content


def test_readme_references_uv_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "README.md").read_text()
        assert "uv run --env-file .env dbt" in content


def test_readme_contains_adapter_specific_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, adapter="Snowflake")
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "README.md").read_text()
        assert "DBT_PASSWORD" in content

    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, adapter="BigQuery")
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "README.md").read_text()
        assert "gcloud" in content


def test_readme_contains_dbt_commands_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "README.md").read_text()
        assert "dbt source freshness" in content
        assert "dbt docs generate" in content


def test_sqlfluff_created_when_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_sqlfluff=True)
        generate_project(config)
        assert (Path(tmpdir) / "test_project" / ".sqlfluff").exists()


def test_sqlfluff_skipped_when_not_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_sqlfluff=False)
        generate_project(config)
        assert not (Path(tmpdir) / "test_project" / ".sqlfluff").exists()


def test_github_actions_created_when_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, ci_providers=["GitHub Actions"])
        generate_project(config)
        ci = Path(tmpdir) / "test_project" / ".github" / "workflows" / "dbt_ci.yml"
        assert ci.exists()


def test_github_actions_skipped_when_not_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, ci_providers=[])
        generate_project(config)
        ci = Path(tmpdir) / "test_project" / ".github" / "workflows" / "dbt_ci.yml"
        assert not ci.exists()


def test_gitlab_ci_created_when_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, ci_providers=["GitLab CI"])
        generate_project(config)
        ci = Path(tmpdir) / "test_project" / ".gitlab-ci.yml"
        assert ci.exists()


def test_bitbucket_pipelines_created_when_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, ci_providers=["Bitbucket Pipelines"])
        generate_project(config)
        ci = Path(tmpdir) / "test_project" / "bitbucket-pipelines.yml"
        assert ci.exists()


def test_multiple_ci_providers():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(
            output_dir=tmpdir,
            ci_providers=["GitHub Actions", "GitLab CI", "Bitbucket Pipelines"],
        )
        generate_project(config)
        base = Path(tmpdir) / "test_project"
        assert (base / ".github" / "workflows" / "dbt_ci.yml").exists()
        assert (base / ".gitlab-ci.yml").exists()
        assert (base / "bitbucket-pipelines.yml").exists()


def test_mart_directories_created():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, marts=["finance", "marketing", "operations"])
        generate_project(config)
        base = Path(tmpdir) / "test_project"
        for mart in ["finance", "marketing", "operations"]:
            assert (base / "models" / "marts" / mart).is_dir()
            assert (base / "models" / "intermediate" / mart).is_dir()


def test_example_models_created():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_examples=True)
        generate_project(config)
        base = Path(tmpdir) / "test_project"
        assert (
            base / "models" / "staging" / "example_source" / "stg_example_source__orders.sql"
        ).exists()
        assert (base / "tests" / "assert_positive_total_amount.sql").exists()


def test_dbt_project_yml_contains_project_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, project_name="my_analytics")
        generate_project(config)
        content = (Path(tmpdir) / "my_analytics" / "dbt_project.yml").read_text()
        assert "my_analytics" in content


def test_packages_yml_contains_selected_packages():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, packages=["dbt-utils"])
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "packages.yml").read_text()
        assert "dbt_utils" in content
        assert "dbt_expectations" not in content


def test_generated_readme_references_public_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        generate_project(config)
        content = (Path(tmpdir) / "test_project" / "README.md").read_text()
        assert "https://github.com/maroil/dbt-forge" in content


def test_all_adapters_have_profile_template():
    from dbt_forge.generator.renderer import TEMPLATES_DIR
    adapters = ["bigquery", "snowflake", "postgresql", "duckdb", "databricks",
                "redshift", "trino", "spark"]
    for adapter in adapters:
        profile = TEMPLATES_DIR / "profiles" / f"{adapter}.yml.j2"
        assert profile.exists(), f"Missing profile template for {adapter}"


def test_progress_callback_called():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        calls = []
        generate_project(config, progress_cb=lambda p: calls.append(p))
        assert len(calls) > 0


def test_no_examples_creates_gitkeep():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_examples=False, marts=["finance"])
        generate_project(config)
        base = Path(tmpdir) / "test_project"
        assert (base / "models" / "marts" / "finance" / ".gitkeep").exists()


def test_selectors_yml_always_generated():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, marts=["finance", "marketing"])
        generate_project(config)
        sel = Path(tmpdir) / "test_project" / "selectors.yml"
        assert sel.exists()
        content = sel.read_text()
        assert "finance_mart" in content
        assert "marketing_mart" in content
        assert "staging_only" in content


def test_dry_run_returns_paths_without_writing():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir)
        paths = generate_project(config, dry_run=True)
        project_dir = Path(tmpdir) / "test_project"
        assert len(paths) > 0
        assert not project_dir.exists(), "dry_run must not create any directories"


def test_unit_tests_created_when_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_examples=True, add_unit_tests=True)
        generate_project(config)
        unit_test = Path(tmpdir) / "test_project" / "tests" / "unit" / "test_stg_example.yml"
        assert unit_test.exists()


def test_unit_tests_skipped_when_not_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_examples=True, add_unit_tests=False)
        generate_project(config)
        unit_test = Path(tmpdir) / "test_project" / "tests" / "unit" / "test_stg_example.yml"
        assert not unit_test.exists()


def test_metricflow_created_when_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_metricflow=True)
        generate_project(config)
        sem = (
            Path(tmpdir) / "test_project"
            / "models" / "marts" / "semantic_models" / "sem_orders.yml"
        )
        assert sem.exists()


def test_metricflow_skipped_when_not_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _default_config(output_dir=tmpdir, add_metricflow=False)
        generate_project(config)
        sem = (
            Path(tmpdir) / "test_project"
            / "models" / "marts" / "semantic_models" / "sem_orders.yml"
        )
        assert not sem.exists()


def test_new_adapters_have_correct_package():
    assert ProjectConfig(
        project_name="p", adapter="Redshift", marts=["finance"], packages=[],
        add_examples=False, add_sqlfluff=False,
    ).dbt_adapter_package == "dbt-redshift"

    assert ProjectConfig(
        project_name="p", adapter="Trino", marts=["finance"], packages=[],
        add_examples=False, add_sqlfluff=False,
    ).dbt_adapter_package == "dbt-trino"

    assert ProjectConfig(
        project_name="p", adapter="Spark", marts=["finance"], packages=[],
        add_examples=False, add_sqlfluff=False,
    ).dbt_adapter_package == "dbt-spark"
