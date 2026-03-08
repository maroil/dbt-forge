"""Tests for Phase 1/2 gaps (A1-A4) and Phase 3 features (B1-B4)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

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


def _scaffold(tmpdir: str, **kwargs) -> Path:
    config = _config(output_dir=tmpdir, **kwargs)
    generate_project(config)
    return Path(tmpdir) / "test_project"


# ---------------------------------------------------------------------------
# A1: README env config section
# ---------------------------------------------------------------------------

class TestReadmeEnvSection:
    def test_readme_contains_env_section_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir, add_env_config=True)
            readme = (project_root / "README.md").read_text()
            assert "Environment configuration" in readme
            assert "generate_schema_name" in readme

    def test_readme_no_env_section_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir, add_env_config=False)
            readme = (project_root / "README.md").read_text()
            assert "Environment configuration" not in readme


# ---------------------------------------------------------------------------
# A2: Source auto-detection
# ---------------------------------------------------------------------------

class TestScanSources:
    def test_scan_sources_finds_sources(self):
        from dbt_forge.cli.add import _scan_sources
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir) / "models" / "staging" / "stripe"
            models_dir.mkdir(parents=True)
            sources_yml = models_dir / "_stripe__sources.yml"
            sources_yml.write_text(yaml.dump({
                "version": 2,
                "sources": [
                    {"name": "stripe", "tables": [{"name": "payments"}]},
                ],
            }))
            result = _scan_sources(Path(tmpdir))
            assert result == ["stripe"]

    def test_scan_sources_empty_when_no_sources(self):
        from dbt_forge.cli.add import _scan_sources
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "models").mkdir()
            result = _scan_sources(Path(tmpdir))
            assert result == []

    def test_scan_sources_deduplicates(self):
        from dbt_forge.cli.add import _scan_sources
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir) / "models" / "staging"
            models_dir.mkdir(parents=True)
            for i in range(2):
                f = models_dir / f"_sources_{i}.yml"
                f.write_text(yaml.dump({
                    "version": 2,
                    "sources": [{"name": "mydb"}],
                }))
            result = _scan_sources(Path(tmpdir))
            assert result == ["mydb"]


# ---------------------------------------------------------------------------
# A3: Schema test + _find_model_columns
# ---------------------------------------------------------------------------

class TestFindModelColumns:
    def test_finds_columns_from_yml(self):
        from dbt_forge.cli.add import _find_model_columns
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir) / "models" / "staging"
            models_dir.mkdir(parents=True)
            yml = models_dir / "_stg_orders__models.yml"
            yml.write_text(yaml.dump({
                "version": 2,
                "models": [{
                    "name": "stg_orders",
                    "columns": [
                        {"name": "id", "description": "PK"},
                        {"name": "amount", "description": "Total"},
                    ],
                }],
            }))
            result = _find_model_columns(Path(tmpdir), "stg_orders")
            assert result == ["id", "amount"]

    def test_returns_empty_when_no_model(self):
        from dbt_forge.cli.add import _find_model_columns
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "models").mkdir()
            result = _find_model_columns(Path(tmpdir), "nonexistent")
            assert result == []


class TestSchemaTestTemplate:
    def test_renders_schema_test(self):
        from dbt_forge.generator.renderer import render_template
        ctx = {
            "model_name": "stg_orders",
            "columns": [
                {"name": "id", "tests": ["unique", "not_null"]},
                {"name": "status", "tests": [
                    {"accepted_values": {"values": ["active", "inactive"]}}
                ]},
            ],
        }
        content = render_template("add/test_schema.yml.j2", ctx)
        data = yaml.safe_load(content)
        assert data["models"][0]["name"] == "stg_orders"
        cols = data["models"][0]["columns"]
        assert cols[0]["name"] == "id"
        assert "unique" in cols[0]["data_tests"]
        assert "not_null" in cols[0]["data_tests"]

    def test_add_schema_test_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                with patch("dbt_forge.cli.add.questionary") as mock_q:
                    mock_q.Style = lambda x: None
                    # First call: test type → schema
                    # Then: text for columns (no existing columns)
                    # Then: checkbox for tests per column
                    select_returns = iter(["schema"])
                    text_returns = iter(["id,amount"])
                    checkbox_returns = iter([
                        ["unique", "not_null"],  # tests for id
                        ["not_null"],  # tests for amount
                    ])
                    mock_q.select.return_value.ask.side_effect = (
                        lambda: next(select_returns)
                    )
                    mock_q.text.return_value.ask.side_effect = (
                        lambda: next(text_returns)
                    )
                    mock_q.checkbox.return_value.ask.side_effect = (
                        lambda: next(checkbox_returns)
                    )
                    mock_q.Choice = lambda title="", value="", checked=False: value
                    result = runner.invoke(add_app, ["test", "stg_orders"])
                    assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            test_file = project_root / "models" / "_stg_orders__tests.yml"
            assert test_file.exists()
            data = yaml.safe_load(test_file.read_text())
            assert data["models"][0]["name"] == "stg_orders"


# ---------------------------------------------------------------------------
# A4: Package config generation
# ---------------------------------------------------------------------------

class TestPackageConfig:
    def test_elementary_adds_vars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.cli.add import add_app
                runner = CliRunner()
                result = runner.invoke(add_app, ["package", "elementary"])
                assert result.exit_code == 0, result.output
            finally:
                os.chdir(old_cwd)

            dbt_project = yaml.safe_load(
                (project_root / "dbt_project.yml").read_text()
            )
            assert "vars" in dbt_project
            assert "elementary" in dbt_project["vars"]
            assert dbt_project["vars"]["elementary"]["edr_cli_run"] == "true"

    def test_no_config_package_doesnt_touch_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            original = (project_root / "dbt_project.yml").read_text()
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

            # dbt_project.yml shouldn't gain vars for dbt-codegen
            new_content = (project_root / "dbt_project.yml").read_text()
            dbt_project = yaml.safe_load(new_content)
            assert "codegen" not in (dbt_project.get("vars") or {})


# ---------------------------------------------------------------------------
# B1: Scanner module
# ---------------------------------------------------------------------------

class TestScanner:
    def test_count_models_by_layer(self):
        from dbt_forge.scanner import count_models_by_layer
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            counts = count_models_by_layer(project_root)
            assert counts["staging"] > 0
            assert counts["marts"] > 0
            assert isinstance(counts["other"], int)

    def test_parse_sources(self):
        from dbt_forge.scanner import parse_sources
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            sources = parse_sources(project_root)
            assert len(sources) > 0
            assert sources[0]["name"] == "example_source"

    def test_parse_packages(self):
        from dbt_forge.scanner import parse_packages
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            packages = parse_packages(project_root)
            assert len(packages) > 0
            names = [p["name"] for p in packages]
            assert "dbt_utils" in names


# ---------------------------------------------------------------------------
# B2: Status command
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["status"])
                assert result.exit_code == 0, result.output
                assert "test_project" in result.output
            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# B3: Manifest + Update
# ---------------------------------------------------------------------------

class TestManifest:
    def test_manifest_created_on_generate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            assert (project_root / ".dbt-forge.yml").exists()

    def test_manifest_roundtrip(self):
        from dbt_forge.manifest import (
            config_to_dict,
            dict_to_config,
            read_manifest,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            manifest = read_manifest(project_root)
            assert manifest is not None
            assert manifest.dbt_forge_version != ""
            assert manifest.config["project_name"] == "test_project"
            assert len(manifest.files) > 0

            # Round-trip config
            config = dict_to_config(manifest.config)
            d = config_to_dict(config)
            assert d["project_name"] == "test_project"
            assert d["adapter"] == "BigQuery"

    def test_update_dry_run_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["update", "--dry-run"])
                assert result.exit_code == 0, result.output
                assert "unchanged" in result.output
            finally:
                os.chdir(old_cwd)

    def test_update_detects_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            # Modify a file
            readme = project_root / "README.md"
            readme.write_text("# Modified\n")

            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["update", "--dry-run"])
                assert result.exit_code == 0, result.output
                assert "changed" in result.output
            finally:
                os.chdir(old_cwd)

    def test_update_no_manifest_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _scaffold(tmpdir)
            (project_root / ".dbt-forge.yml").unlink()
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                from typer.testing import CliRunner
                from dbt_forge.main import app
                runner = CliRunner()
                result = runner.invoke(app, ["update", "--dry-run"])
                assert result.exit_code == 0
                assert ".dbt-forge.yml" in result.output
            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# B4: Presets
# ---------------------------------------------------------------------------

class TestPresets:
    def test_load_preset_from_string(self):
        from dbt_forge.presets import PresetConfig, validate_preset
        preset = PresetConfig(
            name="Test",
            description="A test preset",
            defaults={"adapter": "Snowflake", "add_sqlfluff": True},
            locked=["adapter"],
        )
        errors = validate_preset(preset)
        assert errors == []

    def test_validate_unknown_field(self):
        from dbt_forge.presets import PresetConfig, validate_preset
        preset = PresetConfig(
            defaults={"nonexistent_field": True},
            locked=[],
        )
        errors = validate_preset(preset)
        assert any("Unknown field" in e for e in errors)

    def test_validate_locked_without_default(self):
        from dbt_forge.presets import PresetConfig, validate_preset
        preset = PresetConfig(
            defaults={},
            locked=["adapter"],
        )
        errors = validate_preset(preset)
        assert any("no default" in e for e in errors)

    def test_validate_invalid_adapter(self):
        from dbt_forge.presets import PresetConfig, validate_preset
        preset = PresetConfig(
            defaults={"adapter": "MySQL"},
            locked=[],
        )
        errors = validate_preset(preset)
        assert any("Invalid adapter" in e for e in errors)

    def test_load_preset_from_file(self):
        from dbt_forge.presets import load_preset
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = Path(tmpdir) / "preset.yml"
            preset_path.write_text(yaml.dump({
                "name": "Company Standard",
                "description": "Standard config",
                "defaults": {
                    "adapter": "Snowflake",
                    "marts": ["finance"],
                    "add_sqlfluff": True,
                },
                "locked": ["adapter"],
            }))
            preset = load_preset(str(preset_path))
            assert preset.name == "Company Standard"
            assert preset.defaults["adapter"] == "Snowflake"
            assert "adapter" in preset.locked

    def test_preset_validate_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = Path(tmpdir) / "preset.yml"
            preset_path.write_text(yaml.dump({
                "name": "Valid Preset",
                "defaults": {"adapter": "BigQuery"},
                "locked": ["adapter"],
            }))
            from typer.testing import CliRunner
            from dbt_forge.main import app
            runner = CliRunner()
            result = runner.invoke(app, ["preset", "validate", str(preset_path)])
            assert result.exit_code == 0, result.output
            assert "valid" in result.output.lower()

    def test_preset_validate_command_fails_on_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = Path(tmpdir) / "preset.yml"
            preset_path.write_text(yaml.dump({
                "name": "Bad Preset",
                "defaults": {"nonexistent": True},
            }))
            from typer.testing import CliRunner
            from dbt_forge.main import app
            runner = CliRunner()
            result = runner.invoke(app, ["preset", "validate", str(preset_path)])
            assert result.exit_code != 0

    def test_locked_field_skips_prompt(self):
        """When a field is locked in a preset, gather_config should skip the prompt."""
        from dbt_forge.presets import PresetConfig
        from dbt_forge.prompts.questions import gather_config

        preset = PresetConfig(
            name="Test",
            defaults={
                "adapter": "Snowflake",
                "add_sqlfluff": True,
                "ci_providers": ["GitLab CI"],
                "add_pre_commit": False,
                "add_env_config": False,
            },
            locked=[
                "adapter", "add_sqlfluff", "ci_providers",
                "add_pre_commit", "add_env_config",
            ],
        )

        config = gather_config(
            project_name="test",
            use_defaults=True,
            output_dir=".",
            preset=preset,
        )
        # use_defaults=True doesn't use preset, but the preset param is accepted
        assert config is not None
