"""The `init` command implementation."""

from __future__ import annotations

from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig, gather_config
from dbt_forge.ui.theme import forge_style, make_table, print_ok

console = Console()


def _show_review_screen(config: ProjectConfig) -> bool:
    """Display a summary of all config choices and ask for confirmation.

    Returns True if the user wants to proceed, False to abort.
    """
    table = make_table("Project Configuration Review", [
        ("Setting", {"min_width": 25}),
        ("Value", {"min_width": 30}),
    ])

    def _bool_str(v: bool) -> str:
        return "[green]yes[/green]" if v else "[dim]no[/dim]"

    table.add_row("Project name", f"[bold]{config.project_name}[/bold]")
    table.add_row("Adapter", config.adapter)
    table.add_row("Marts", ", ".join(config.marts) if config.marts else "[dim]none[/dim]")
    table.add_row("Packages", ", ".join(config.packages) if config.packages else "[dim]none[/dim]")
    ci = ", ".join(config.ci_providers) if config.ci_providers else "[dim]none[/dim]"
    table.add_row("CI providers", ci)
    table.add_row("Example models", _bool_str(config.add_examples))
    table.add_row("SQLFluff config", _bool_str(config.add_sqlfluff))
    table.add_row("Unit tests", _bool_str(config.add_unit_tests))
    table.add_row("MetricFlow", _bool_str(config.add_metricflow))
    table.add_row("Snapshot", _bool_str(config.add_snapshot))
    table.add_row("Seed", _bool_str(config.add_seed))
    table.add_row("Exposure", _bool_str(config.add_exposure))
    table.add_row("Macro", _bool_str(config.add_macro))
    table.add_row("Pre-commit hooks", _bool_str(config.add_pre_commit))
    table.add_row("Environment config", _bool_str(config.add_env_config))
    table.add_row("Team owner", config.team_owner if config.team_owner else "[dim]none[/dim]")

    console.print()
    console.print(table)
    console.print()

    proceed = questionary.confirm(
        "Proceed with generation?",
        default=True,
        style=forge_style(),
    ).ask()
    return proceed is True


def init_command(
    project_name: str | None,
    use_defaults: bool,
    output_dir: str,
    dry_run: bool = False,
    preset: object | None = None,
) -> None:
    config = gather_config(
        project_name=project_name,
        use_defaults=use_defaults,
        output_dir=output_dir,
        preset=preset,
    )

    console.print()

    if dry_run:
        _run_dry(config, output_dir)
        return

    # Show review screen for interactive mode
    if not use_defaults:
        if not _show_review_screen(config):
            console.print("[dim]Aborted.[/dim]")
            return

    written: list[Path] = []

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Generating project structure...", total=None)

        def on_file(rel_path: str) -> None:
            progress.update(task, description=f"Writing [cyan]{rel_path}[/cyan]")

        written = generate_project(config, progress_cb=on_file)

    project_path = Path(output_dir) / config.project_name

    # Summary
    print_ok(f"Created [bold]{project_path}/[/bold]")
    print_ok(f"{len(written)} files written")
    console.print()

    _print_next_steps(config)


def init_mesh_command(
    project_name: str | None,
    use_defaults: bool,
    output_dir: str,
    dry_run: bool = False,
) -> None:
    """Scaffold a dbt Mesh multi-project setup."""
    import shutil

    from dbt_forge.mesh import MeshProjectConfig, SubProjectConfig, generate_mesh_project
    from dbt_forge.prompts.questions import gather_mesh_config

    if use_defaults:
        name = project_name or "my_dbt_mesh"
        config = MeshProjectConfig(
            name=name,
            adapter="DuckDB",
            adapter_key="duckdb",
            dbt_adapter_package="dbt-duckdb",
            sub_projects=[
                SubProjectConfig(name="staging", purpose="staging"),
                SubProjectConfig(
                    name="transform", purpose="intermediate", upstream_deps=["staging"]
                ),
                SubProjectConfig(name="marts", purpose="marts", upstream_deps=["transform"]),
            ],
            output_dir=output_dir,
        )
    else:
        config = gather_mesh_config(project_name=project_name, output_dir=output_dir)

    console.print()

    if dry_run:
        paths = generate_mesh_project(config)
        base = Path(output_dir) / config.name
        console.print(f"  [yellow]dry-run[/yellow]  {len(paths)} files would be written.")
        # Clean up the generated files in dry-run
        if base.exists():
            shutil.rmtree(base)
        console.print()
        return

    written = generate_mesh_project(config)
    project_path = Path(output_dir) / config.name

    print_ok(f"Created mesh project [bold]{project_path}/[/bold]")
    print_ok(f"{len(config.sub_projects)} sub-projects")
    print_ok(f"{len(written)} files written")
    console.print()


def _run_dry(config: ProjectConfig, output_dir: str) -> None:
    """Show a Rich tree of files that would be written without writing anything."""
    paths = generate_project(config, dry_run=True)

    base = Path(output_dir) / config.project_name
    tree = Tree(
        f"[bold cyan]{base}/[/bold cyan]",
        guide_style="dim",
    )

    # Build a dict of directories → subtrees for nested display
    dir_nodes: dict[Path, Tree] = {}

    def get_node(directory: Path) -> Tree:
        if directory == base:
            return tree
        parent = get_node(directory.parent)
        if directory not in dir_nodes:
            dir_nodes[directory] = parent.add(f"[bold blue]{directory.name}/[/bold blue]")
        return dir_nodes[directory]

    for path in sorted(paths):
        rel = path.relative_to(base)
        parent_node = get_node(base / rel.parent) if rel.parent != Path(".") else tree
        parent_node.add(f"[green]{path.name}[/green]")

    console.print(tree)
    console.print()
    console.print(
        f"  [yellow]dry-run[/yellow]  {len(paths)} files would be written to "
        f"[bold]{base}/[/bold] — nothing was created."
    )
    console.print()


def _print_next_steps(config: ProjectConfig) -> None:
    lines = [
        f"  cd {config.project_name}",
        "  uv sync                              # create venv & install dbt",
    ]
    if config.packages:
        lines.append("  uv run --env-file .env dbt deps      # install dbt packages")
    lines.append("  uv run --env-file .env dbt debug     # verify connection")

    content = "\n".join(lines)

    panel = Panel(
        f"[bold]Next steps[/bold]\n\n{content}\n",
        border_style="cyan",
        padding=(0, 1),
    )
    console.print(panel)
    console.print()
