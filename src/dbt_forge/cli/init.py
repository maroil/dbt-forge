"""The `init` command implementation."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from dbt_forge.generator.project import generate_project
from dbt_forge.prompts.questions import ProjectConfig, gather_config

console = Console()


def init_command(
    project_name: str | None,
    use_defaults: bool,
    output_dir: str,
) -> None:
    config = gather_config(
        project_name=project_name,
        use_defaults=use_defaults,
        output_dir=output_dir,
    )

    console.print()

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
