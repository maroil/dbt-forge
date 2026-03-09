"""Tests for dbt Mesh multi-project scaffolding."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from dbt_forge.mesh import (
    MeshProjectConfig,
    SubProjectConfig,
    generate_mesh_project,
    generate_sub_project_standalone,
)


class TestMeshGeneration:
    def _make_config(self, tmpdir: str, **overrides) -> MeshProjectConfig:
        defaults = {
            "name": "my_mesh",
            "adapter": "DuckDB",
            "adapter_key": "duckdb",
            "dbt_adapter_package": "dbt-duckdb",
            "sub_projects": [
                SubProjectConfig(name="staging", purpose="staging"),
                SubProjectConfig(
                    name="transform",
                    purpose="intermediate",
                    upstream_deps=["staging"],
                ),
                SubProjectConfig(name="marts", purpose="marts", upstream_deps=["transform"]),
            ],
            "output_dir": tmpdir,
        }
        defaults.update(overrides)
        return MeshProjectConfig(**defaults)

    def test_generates_root_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            assert (base / "README.md").exists()
            assert (base / "Makefile").exists()

    def test_generates_sub_project_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            for sp_name in ("staging", "transform", "marts"):
                assert (base / sp_name / "dbt_project.yml").exists()

    def test_dependencies_yml_created_for_deps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            # staging has no deps -- no dependencies.yml
            assert not (base / "staging" / "dependencies.yml").exists()
            # transform depends on staging
            assert (base / "transform" / "dependencies.yml").exists()
            dep_content = (base / "transform" / "dependencies.yml").read_text()
            assert "staging" in dep_content

    def test_model_access_levels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"

            # Staging model should have "protected" access
            staging_yml = list((base / "staging" / "models").rglob("*__models.yml"))
            assert staging_yml
            content = staging_yml[0].read_text()
            assert "access: protected" in content

            # Marts model should have "public" access
            marts_yml = list((base / "marts" / "models").rglob("*__models.yml"))
            assert marts_yml
            content = marts_yml[0].read_text()
            assert "access: public" in content

    def test_contract_enforced_on_public(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"

            marts_yml = list((base / "marts" / "models").rglob("*__models.yml"))
            assert marts_yml
            content = marts_yml[0].read_text()
            assert "enforced: true" in content

    def test_group_definitions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            for sp_name in ("staging", "transform", "marts"):
                groups_yml = base / sp_name / "models" / "_groups.yml"
                assert groups_yml.exists()
                content = groups_yml.read_text()
                assert f"name: {sp_name}" in content

    def test_makefile_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            content = (base / "Makefile").read_text()
            assert "staging" in content
            assert "transform" in content
            assert "marts" in content
            assert "dbt run" in content

    def test_profiles_yml_in_sub_projects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            for sp_name in ("staging", "transform", "marts"):
                profiles = base / sp_name / "profiles" / "profiles.yml"
                assert profiles.exists()
                content = profiles.read_text()
                assert "duckdb" in content

    def test_empty_dirs_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            for sp_name in ("staging",):
                for d in ("macros", "tests", "seeds", "snapshots", "analyses"):
                    assert (base / sp_name / d / ".gitkeep").exists()

    def test_custom_purpose_generates_both_layers(self):
        """When purpose doesn't match a known layer, both staging + marts are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(
                tmpdir,
                sub_projects=[SubProjectConfig(name="custom", purpose="general purpose")],
            )
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh" / "custom"
            # Should have both staging and marts models
            assert (base / "models" / "staging").exists()
            assert (base / "models" / "marts").exists()

    def test_readme_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            generate_mesh_project(config)
            base = Path(tmpdir) / "my_mesh"
            content = (base / "README.md").read_text()
            assert "staging" in content
            assert "transform" in content
            assert "marts" in content

    def test_returns_written_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._make_config(tmpdir)
            written = generate_mesh_project(config)
            assert len(written) > 10  # Should generate many files


class TestAddSubProject:
    def test_add_sub_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # First generate a mesh
            config = MeshProjectConfig(
                name="my_mesh",
                adapter="DuckDB",
                adapter_key="duckdb",
                dbt_adapter_package="dbt-duckdb",
                sub_projects=[
                    SubProjectConfig(name="staging", purpose="staging"),
                ],
                output_dir=tmpdir,
            )
            generate_mesh_project(config)
            mesh_root = Path(tmpdir) / "my_mesh"

            # Now add a new sub-project
            sp = SubProjectConfig(name="analytics", purpose="marts", upstream_deps=["staging"])
            written = generate_sub_project_standalone(
                mesh_root=mesh_root,
                sp=sp,
                adapter="DuckDB",
                adapter_key="duckdb",
                dbt_adapter_package="dbt-duckdb",
            )

            assert (mesh_root / "analytics" / "dbt_project.yml").exists()
            assert (mesh_root / "analytics" / "dependencies.yml").exists()
            dep_content = (mesh_root / "analytics" / "dependencies.yml").read_text()
            assert "staging" in dep_content
            assert len(written) > 5

    def test_add_sub_project_no_deps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MeshProjectConfig(
                name="my_mesh",
                adapter="DuckDB",
                adapter_key="duckdb",
                dbt_adapter_package="dbt-duckdb",
                sub_projects=[
                    SubProjectConfig(name="staging", purpose="staging"),
                ],
                output_dir=tmpdir,
            )
            generate_mesh_project(config)
            mesh_root = Path(tmpdir) / "my_mesh"

            sp = SubProjectConfig(name="standalone", purpose="", upstream_deps=[])
            generate_sub_project_standalone(
                mesh_root=mesh_root,
                sp=sp,
                adapter="DuckDB",
                adapter_key="duckdb",
                dbt_adapter_package="dbt-duckdb",
            )

            assert (mesh_root / "standalone" / "dbt_project.yml").exists()
            assert not (mesh_root / "standalone" / "dependencies.yml").exists()


class TestMeshInitCommand:
    """Tests for init --mesh via init_mesh_command."""

    def test_init_mesh_defaults(self):
        """init --mesh --defaults creates the preset staging/transform/marts layout."""
        from dbt_forge.cli.init import init_mesh_command

        with tempfile.TemporaryDirectory() as tmpdir:
            init_mesh_command(
                project_name="test_mesh",
                use_defaults=True,
                output_dir=tmpdir,
                dry_run=False,
            )

            base = Path(tmpdir) / "test_mesh"
            assert base.exists()

            # Three sub-projects
            for sp in ("staging", "transform", "marts"):
                assert (base / sp / "dbt_project.yml").exists()

            # Root files
            assert (base / "README.md").exists()
            assert (base / "Makefile").exists()

            # Staging has no dependencies.yml, transform and marts do
            assert not (base / "staging" / "dependencies.yml").exists()
            assert (base / "transform" / "dependencies.yml").exists()
            assert (base / "marts" / "dependencies.yml").exists()

    def test_init_mesh_dry_run(self):
        """init --mesh --dry-run does not leave files on disk."""
        from dbt_forge.cli.init import init_mesh_command

        with tempfile.TemporaryDirectory() as tmpdir:
            init_mesh_command(
                project_name="dry_mesh",
                use_defaults=True,
                output_dir=tmpdir,
                dry_run=True,
            )

            base = Path(tmpdir) / "dry_mesh"
            assert not base.exists()

    def test_dbt_project_yml_valid(self):
        """Each sub-project dbt_project.yml is valid YAML with the correct name."""
        from dbt_forge.cli.init import init_mesh_command

        with tempfile.TemporaryDirectory() as tmpdir:
            init_mesh_command(
                project_name="valid_mesh",
                use_defaults=True,
                output_dir=tmpdir,
            )

            base = Path(tmpdir) / "valid_mesh"
            for sp in ("staging", "transform", "marts"):
                data = yaml.safe_load((base / sp / "dbt_project.yml").read_text())
                assert data["name"] == sp


class TestMeshHelpers:
    """Tests for mesh root detection and sub-project listing."""

    def test_find_existing_sub_projects(self):
        from dbt_forge.cli.add import _find_existing_sub_projects

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            for sp in ("staging", "marts"):
                sp_dir = base / sp
                sp_dir.mkdir()
                (sp_dir / "dbt_project.yml").write_text(f"name: {sp}\n")

            result = _find_existing_sub_projects(base)
            assert result == ["marts", "staging"]

    def test_is_mesh_root_true(self):
        from dbt_forge.cli.add import _is_mesh_root

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "Makefile").write_text("build:\n\techo build")
            sp = base / "staging"
            sp.mkdir()
            (sp / "dbt_project.yml").write_text("name: staging\n")

            assert _is_mesh_root(base)

    def test_is_mesh_root_false_no_makefile(self):
        from dbt_forge.cli.add import _is_mesh_root

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            sp = base / "staging"
            sp.mkdir()
            (sp / "dbt_project.yml").write_text("name: staging\n")

            assert not _is_mesh_root(base)

    def test_is_mesh_root_false_no_sub_projects(self):
        from dbt_forge.cli.add import _is_mesh_root

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "Makefile").write_text("build:\n\techo build")

            assert not _is_mesh_root(base)
