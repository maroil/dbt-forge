"""The `init` command implementation."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig, gather_config

console = Console()


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
    console.print(f"  [green]✔[/green]  Created [bold]{project_path}/[/bold]")
    console.print(f"  [green]✔[/green]  {len(written)} files written")
    console.print()

    _print_next_steps(config)


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
            dir_nodes[directory] = parent.add(
                f"[bold blue]{directory.name}/[/bold blue]"
            )
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
