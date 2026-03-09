"""dbt Mesh multi-project scaffolding."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dbt_forge.generator.renderer import render_template


@dataclass
class SubProjectConfig:
    """Configuration for a single sub-project in a mesh."""

    name: str
    purpose: str = ""  # e.g. "staging", "transform", "marts"
    upstream_deps: list[str] = field(default_factory=list)


@dataclass
class MeshProjectConfig:
    """Configuration for a dbt mesh (multi-project) setup."""

    name: str
    adapter: str
    adapter_key: str
    dbt_adapter_package: str
    sub_projects: list[SubProjectConfig] = field(default_factory=list)
    output_dir: str = "."


# Default access levels by layer directory
ACCESS_MAP = {
    "staging": "protected",
    "intermediate": "private",
    "marts": "public",
}


def generate_mesh_project(config: MeshProjectConfig) -> list[Path]:
    """Generate a complete mesh project with multiple sub-projects."""
    base = Path(config.output_dir) / config.name
    base.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def write(rel_path: str, content: str) -> None:
        dest = base / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        written.append(dest)

    ctx = {
        "mesh_name": config.name,
        "adapter": config.adapter,
        "adapter_key": config.adapter_key,
        "dbt_adapter_package": config.dbt_adapter_package,
        "sub_projects": config.sub_projects,
    }

    # Root README
    write("README.md", render_template("mesh/root_README.md.j2", ctx))

    # Root Makefile
    write("Makefile", render_template("mesh/Makefile.j2", ctx))

    # Generate each sub-project
    for sp in config.sub_projects:
        sp_ctx = {
            **ctx,
            "project_name": sp.name,
            "purpose": sp.purpose,
            "upstream_deps": sp.upstream_deps,
        }
        _generate_sub_project(base, sp, sp_ctx, written)

    return written


def _generate_sub_project(
    base: Path, sp: SubProjectConfig, ctx: dict, written: list[Path]
) -> None:
    """Generate a single sub-project within a mesh."""
    sp_dir = base / sp.name

    def write(rel_path: str, content: str) -> None:
        dest = sp_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        written.append(dest)

    # dbt_project.yml
    write("dbt_project.yml", render_template("mesh/dbt_project.yml.j2", ctx))

    # dependencies.yml (if has upstream deps)
    if sp.upstream_deps:
        write("dependencies.yml", render_template("mesh/dependencies.yml.j2", ctx))

    # Group definition
    write(
        "models/_groups.yml",
        render_template("mesh/group_definition.yml.j2", ctx),
    )

    # Default model directories based on purpose
    layer = _purpose_to_layer(sp.purpose)
    if layer:
        # Create example model with access config
        model_name = f"example_{sp.name}"
        access = ACCESS_MAP.get(layer, "protected")
        model_ctx = {
            **ctx,
            "model_name": model_name,
            "layer": layer,
            "access": access,
            "contract_enforced": access == "public",
            "group_name": sp.name,
        }
        write(
            f"models/{layer}/{model_name}.sql",
            render_template("mesh/model_with_access.sql.j2", model_ctx),
        )
        write(
            f"models/{layer}/_{model_name}__models.yml",
            render_template("mesh/model_with_access.yml.j2", model_ctx),
        )
    else:
        # Generic: create staging + marts layers
        for lyr in ("staging", "marts"):
            model_name = f"example_{sp.name}_{lyr}"
            access = ACCESS_MAP.get(lyr, "protected")
            model_ctx = {
                **ctx,
                "model_name": model_name,
                "layer": lyr,
                "access": access,
                "contract_enforced": access == "public",
                "group_name": sp.name,
            }
            write(
                f"models/{lyr}/{model_name}.sql",
                render_template("mesh/model_with_access.sql.j2", model_ctx),
            )
            write(
                f"models/{lyr}/_{model_name}__models.yml",
                render_template("mesh/model_with_access.yml.j2", model_ctx),
            )

    # Profiles
    write("profiles/profiles.yml", _profiles_stub(ctx))

    # Empty dirs
    for d in ("macros", "tests", "seeds", "snapshots", "analyses"):
        (sp_dir / d).mkdir(parents=True, exist_ok=True)
        write(f"{d}/.gitkeep", "")


def _purpose_to_layer(purpose: str) -> str | None:
    """Map sub-project purpose to a single layer, or None for generic."""
    purpose_lower = purpose.lower()
    if "staging" in purpose_lower or "extract" in purpose_lower:
        return "staging"
    if "transform" in purpose_lower or "intermediate" in purpose_lower:
        return "intermediate"
    if (
        "marts" in purpose_lower
        or "analytics" in purpose_lower
        or "reporting" in purpose_lower
    ):
        return "marts"
    return None


def _profiles_stub(ctx: dict) -> str:
    """Generate a minimal profiles.yml stub."""
    adapter_key = ctx.get("adapter_key", "duckdb")
    project_name = ctx.get("project_name", "my_project")
    return (
        f"{project_name}:\n"
        f"  target: dev\n"
        f"  outputs:\n"
        f"    dev:\n"
        f"      type: {adapter_key}\n"
        f"      # TODO: Configure connection settings\n"
    )


def generate_sub_project_standalone(
    mesh_root: Path,
    sp: SubProjectConfig,
    adapter: str,
    adapter_key: str,
    dbt_adapter_package: str,
) -> list[Path]:
    """Add a new sub-project to an existing mesh. Used by `add project`."""
    written: list[Path] = []
    ctx = {
        "mesh_name": mesh_root.name,
        "adapter": adapter,
        "adapter_key": adapter_key,
        "dbt_adapter_package": dbt_adapter_package,
        "project_name": sp.name,
        "purpose": sp.purpose,
        "upstream_deps": sp.upstream_deps,
        "sub_projects": [],
    }
    _generate_sub_project(mesh_root, sp, ctx, written)
    return written
