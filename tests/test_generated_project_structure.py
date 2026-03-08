"""
Structural validation tests for generated projects.

These are "guardrail" tests that catch issues that would cause `dbt compile`
to fail — without needing dbt installed. They validate the generated file
tree and YAML contents.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig

ALL_ADAPTERS = ["BigQuery", "Snowflake", "PostgreSQL", "DuckDB", "Databricks"]
ALL_MARTS = ["finance", "marketing", "operations", "product", "engineering"]


def _config(**kwargs) -> ProjectConfig:
    defaults = dict(
        project_name="test_project",
        adapter="BigQuery",
        marts=["finance", "marketing"],
        packages=["dbt-utils", "dbt-expectations"],
        add_examples=True,
        add_sqlfluff=True,
        add_github_actions=True,
    )
    defaults.update(kwargs)
    return ProjectConfig(**defaults)


def _generate(config: ProjectConfig) -> Path:
    """Generate project and return the base path."""
    tmpdir = tempfile.mkdtemp()
    generate_project(config, output_dir=tmpdir if hasattr(config, '_tmpdir') else config.output_dir)
    return Path(config.output_dir) / config.project_name


# ---------------------------------------------------------------------------
# Model name uniqueness — the most critical check
# ---------------------------------------------------------------------------

class TestModelNameUniqueness:
    def test_no_duplicate_model_names_two_marts(self):
        """Two marts must not produce models with identical names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, marts=["finance", "marketing"])
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            _assert_no_duplicate_model_names(base)

    def test_no_duplicate_model_names_all_marts(self):
        """All possible marts selected must still produce unique model names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, marts=ALL_MARTS)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            _assert_no_duplicate_model_names(base)

    def test_no_duplicate_model_names_single_mart(self):
        """Single mart should trivially have no duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, marts=["finance"])
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            _assert_no_duplicate_model_names(base)

    def test_mart_models_are_prefixed_with_mart_name(self):
        """Mart SQL files must be prefixed with the mart name, not generic names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, marts=["finance", "marketing"])
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            for mart in ["finance", "marketing"]:
                mart_dir = base / "models" / "marts" / mart
                sql_files = list(mart_dir.glob("*.sql"))
                assert sql_files, f"No SQL files in marts/{mart}/"
                for f in sql_files:
                    assert f.stem.startswith(mart), (
                        f"{f.name} in marts/{mart}/ must be prefixed with '{mart}_' "
                        f"to avoid dbt name collisions across marts"
                    )


def _assert_no_duplicate_model_names(base: Path) -> None:
    sql_files = list(base.rglob("models/**/*.sql"))
    names = [f.stem for f in sql_files]
    seen, duplicates = set(), set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    assert not duplicates, (
        f"Duplicate dbt model names found — dbt compile will fail: {duplicates}\n"
        f"Files: {[str(f.relative_to(base)) for f in sql_files]}"
    )


# ---------------------------------------------------------------------------
# YAML validity — generated YAML must parse without errors
# ---------------------------------------------------------------------------

class TestYamlValidity:
    def test_all_yaml_files_are_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, marts=ALL_MARTS)
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            yaml_files = list(base.rglob("*.yml")) + list(base.rglob("*.yaml"))
            assert yaml_files, "No YAML files generated"
            for path in yaml_files:
                try:
                    yaml.safe_load(path.read_text())
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {path.relative_to(base)}: {e}")

    def test_sources_yaml_uses_config_for_freshness(self):
        """Freshness must be inside config: block (dbt 1.9+ requirement)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            sources_yml = (
                Path(tmpdir) / "test_project"
                / "models/staging/example_source/_example_source__sources.yml"
            )
            data = yaml.safe_load(sources_yml.read_text())
            source = data["sources"][0]
            assert "freshness" not in source, (
                "Top-level `freshness` on source is deprecated in dbt 1.9+. "
                "Move it inside `config:`."
            )
            assert "freshness" in source.get("config", {}), (
                "`freshness` must be defined inside `config:` on the source."
            )

    def test_dbt_project_yml_has_required_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            data = yaml.safe_load(
                (Path(tmpdir) / "test_project" / "dbt_project.yml").read_text()
            )
            for key in ("name", "version", "profile", "model-paths"):
                assert key in data, f"dbt_project.yml missing required key: {key}"

    def test_models_yaml_names_match_sql_files(self):
        """Model names declared in YAML must match their SQL filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, marts=["finance", "marketing"])
            generate_project(config)
            base = Path(tmpdir) / "test_project"
            _assert_yaml_model_names_match_sql(base)


def _assert_yaml_model_names_match_sql(base: Path) -> None:
    """For every _models.yml, check that declared model names have matching .sql files."""
    model_dirs = [
        base / "models" / "staging",
        base / "models" / "intermediate",
        base / "models" / "marts",
    ]
    for model_dir in model_dirs:
        for yml_path in model_dir.rglob("*models.yml"):
            data = yaml.safe_load(yml_path.read_text())
            if not data or "models" not in data:
                continue
            for model in data["models"]:
                name = model["name"]
                sql_path = yml_path.parent / f"{name}.sql"
                assert sql_path.exists(), (
                    f"Model '{name}' declared in {yml_path.relative_to(base)} "
                    f"but {sql_path.name} does not exist"
                )


# ---------------------------------------------------------------------------
# .env and profiles-dir
# ---------------------------------------------------------------------------

class TestEnvAndProfiles:
    def test_env_file_generated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            env_file = Path(tmpdir) / "test_project" / ".env"
            assert env_file.exists(), ".env file must be generated"

    def test_env_file_sets_profiles_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            content = (Path(tmpdir) / "test_project" / ".env").read_text()
            assert "DBT_PROFILES_DIR" in content
            assert "profiles" in content

    def test_env_file_is_gitignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            gitignore = (Path(tmpdir) / "test_project" / ".gitignore").read_text()
            assert ".env" in gitignore, ".env must be listed in .gitignore"

    def test_profiles_dir_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            assert (Path(tmpdir) / "test_project" / "profiles" / "profiles.yml").exists()


# ---------------------------------------------------------------------------
# All adapters generate valid profiles
# ---------------------------------------------------------------------------

class TestAdapterProfiles:
    @pytest.mark.parametrize("adapter", ALL_ADAPTERS)
    def test_profile_is_valid_yaml(self, adapter: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, adapter=adapter)
            generate_project(config)
            profiles_yml = Path(tmpdir) / "test_project" / "profiles" / "profiles.yml"
            try:
                data = yaml.safe_load(profiles_yml.read_text())
            except yaml.YAMLError as e:
                pytest.fail(f"profiles.yml for {adapter} is not valid YAML: {e}")
            assert data is not None
            assert "test_project" in data, "Profile must contain the project name key"

    @pytest.mark.parametrize("adapter", ALL_ADAPTERS)
    def test_profile_has_dev_and_prod_targets(self, adapter: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, adapter=adapter)
            generate_project(config)
            data = yaml.safe_load(
                (Path(tmpdir) / "test_project" / "profiles" / "profiles.yml").read_text()
            )
            outputs = data["test_project"]["outputs"]
            assert "dev" in outputs, f"{adapter} profile missing 'dev' target"
            assert "prod" in outputs, f"{adapter} profile missing 'prod' target"


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------

class TestPackages:
    def test_packages_yml_is_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir)
            generate_project(config)
            data = yaml.safe_load(
                (Path(tmpdir) / "test_project" / "packages.yml").read_text()
            )
            assert "packages" in data

    def test_no_deprecated_calogica_package(self):
        """calogica/dbt_expectations is deprecated; must use metaplane/dbt_expectations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(output_dir=tmpdir, packages=["dbt-expectations"])
            generate_project(config)
            content = (Path(tmpdir) / "test_project" / "packages.yml").read_text()
            assert "calogica" not in content, (
                "calogica/dbt_expectations is deprecated — use metaplane/dbt_expectations"
            )
            assert "metaplane" in content
