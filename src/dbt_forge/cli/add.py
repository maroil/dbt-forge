"""The `add` subcommand — post-init scaffolding for existing dbt projects."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console

from dbt_forge.generator.renderer import render_template

console = Console()

add_app = typer.Typer(
    name="add",
    help="Add marts, sources, or other components to an existing dbt project.",
    no_args_is_help=True,
)

TEMPLATES_BASE = "add"


def _find_project_root() -> Path:
    """Walk up from cwd to find dbt_project.yml. Returns the directory containing it."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        if (directory / "dbt_project.yml").exists():
            return directory
    console.print(
        "[red]Error:[/red] No [bold]dbt_project.yml[/bold] found in the current directory "
        "or any parent directory.\n"
        "Run [cyan]dbt-forge add[/cyan] from inside a dbt project."
    )
    sys.exit(1)


def _read_project_name(project_root: Path) -> str:
    data = yaml.safe_load((project_root / "dbt_project.yml").read_text())
    return data.get("name", "unknown_project")


def _write(dest: Path, content: str) -> None:
    if dest.exists():
        console.print(f"  [yellow]skip[/yellow]  {dest} already exists")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    console.print(f"  [green]✔[/green]  {dest}")


@add_app.command("mart")
def add_mart(
    name: str = typer.Argument(..., help="Name of the mart to scaffold (e.g. 'finance')."),
) -> None:
    """Scaffold a new mart layer inside an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    ctx = {"mart": name, "project_name": project_name}

    console.print()
    console.print(
        f"  Adding mart [bold cyan]{name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        project_root / f"models/marts/{name}/{name}_orders.sql",
        render_template(f"{TEMPLATES_BASE}/mart_model.sql.j2", ctx),
    )
    _write(
        project_root / f"models/marts/{name}/__{name}__models.yml",
        render_template(f"{TEMPLATES_BASE}/mart_models.yml.j2", ctx),
    )
    _write(
        project_root / f"models/intermediate/{name}/int_{name}__orders_enriched.sql",
        render_template(f"{TEMPLATES_BASE}/int_stub.sql.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Mart [bold]{name}[/bold] scaffolded. "
        "Update the SQL stubs to match your actual source models.[/dim]"
    )
    console.print()


@add_app.command("source")
def add_source(
    name: str = typer.Argument(..., help="Name of the source to scaffold (e.g. 'salesforce')."),
) -> None:
    """Scaffold a new staging source inside an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    ctx = {"source_name": name, "project_name": project_name}

    console.print()
    console.print(
        f"  Adding source [bold cyan]{name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    staging_dir = project_root / f"models/staging/{name}"

    _write(
        staging_dir / f"_{name}__sources.yml",
        render_template(f"{TEMPLATES_BASE}/source_sources.yml.j2", ctx),
    )
    _write(
        staging_dir / f"_{name}__models.yml",
        render_template(f"{TEMPLATES_BASE}/source_models.yml.j2", ctx),
    )
    _write(
        staging_dir / f"stg_{name}__records.sql",
        render_template(f"{TEMPLATES_BASE}/stg_stub.sql.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Source [bold]{name}[/bold] scaffolded. "
        "Update the source YAML to match your actual warehouse tables.[/dim]"
    )
    console.print()
