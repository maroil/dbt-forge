"""dbt-forge entrypoint."""

import typer
from rich.console import Console
from rich.text import Text

from dbt_forge.cli.add import add_app
from dbt_forge.cli.init import init_command

app = typer.Typer(
    name="dbt-forge",
    help="Scaffold production-ready dbt projects with opinionated defaults.",
    add_completion=False,
    no_args_is_help=True,
)

app.add_typer(add_app, name="add")

console = Console()


def version_callback(value: bool) -> None:
    if value:
        from dbt_forge import __version__

        console.print(f"dbt-forge v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


@app.command()
def init(
    project_name: str = typer.Argument(
        None,
        help="Name of the dbt project to scaffold.",
    ),
    defaults: bool = typer.Option(
        False,
        "--defaults",
        "-d",
        help="Use default options without interactive prompts.",
    ),
    output_dir: str = typer.Option(
        ".",
        "--output",
        "-o",
        help="Directory where the project will be created.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview files that would be generated without writing anything.",
    ),
) -> None:
    """Scaffold a new production-ready dbt project."""
    _print_banner()
    init_command(
        project_name=project_name,
        use_defaults=defaults,
        output_dir=output_dir,
        dry_run=dry_run,
    )


def _print_banner() -> None:
    text = Text()
    text.append("✦  dbt-forge", style="bold cyan")
    text.append(" — scaffold production-ready dbt projects", style="dim")
    console.print()
    console.print(text)
    console.print()


if __name__ == "__main__":
    app()
