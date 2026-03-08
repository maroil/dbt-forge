"""dbt-forge entrypoint."""

import click
import typer
import typer.core
from rich.console import Console
from rich.text import Text

from dbt_forge.cli.add import add_app
from dbt_forge.cli.doctor import run_doctor
from dbt_forge.cli.init import init_command

HELP_TEXT = """\
Scaffold production-ready dbt projects with opinionated defaults.

Like create-t3-app, but for dbt. Generates a complete project structure
with staging/marts layers, CI pipelines, pre-commit hooks, and more.
"""


class HelpGroup(typer.core.TyperGroup):
    """Custom group that appends usage examples after the default help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_help(ctx, formatter)
        console = Console()
        console.print()
        console.print("[bold cyan]Getting started:[/bold cyan]")
        console.print()
        console.print("  [green]$[/green] dbt-forge init my-project          Interactive")
        console.print("  [green]$[/green] dbt-forge init my-project [bold]-d[/bold]       Defaults")
        console.print("  [green]$[/green] dbt-forge init my-project [bold]--dry-run[/bold] Preview")
        console.print()
        console.print("[bold cyan]Add components:[/bold cyan]")
        console.print()
        console.print("  [green]$[/green] dbt-forge add source salesforce     Source")
        console.print("  [green]$[/green] dbt-forge add mart finance           Mart")
        console.print("  [green]$[/green] dbt-forge add snapshot orders        Snapshot")
        console.print("  [green]$[/green] dbt-forge add seed country_codes     Seed")
        console.print("  [green]$[/green] dbt-forge add macro cents_to_dollars Macro")
        console.print("  [green]$[/green] dbt-forge add exposure weekly_report Exposure")
        console.print("  [green]$[/green] dbt-forge add pre-commit             Pre-commit")
        console.print("  [green]$[/green] dbt-forge add ci                     CI pipeline")
        console.print("  [green]$[/green] dbt-forge add model users            Model")
        console.print("  [green]$[/green] dbt-forge add test orders            Test")
        console.print("  [green]$[/green] dbt-forge add package dbt-utils      Package")
        console.print()
        console.print("[bold cyan]Project health:[/bold cyan]")
        console.print()
        console.print("  [green]$[/green] dbt-forge doctor                     Health checks")
        console.print("  [green]$[/green] dbt-forge doctor [bold]--fix[/bold]             Auto-fix")
        console.print("  [green]$[/green] dbt-forge doctor [bold]--ci[/bold]               CI mode")
        console.print()
        console.print("[dim]Docs: https://dbt-forge.com[/dim]")
        console.print()


app = typer.Typer(
    name="dbt-forge",
    help=HELP_TEXT,
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    cls=HelpGroup,
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
    """Scaffold a new production-ready dbt project.

    Walks you through an interactive setup to pick your adapter (BigQuery,
    Snowflake, Postgres, etc.), CI provider, packages, and optional features
    like unit tests, MetricFlow, snapshots, seeds, and macros.
    """
    _print_banner()
    init_command(
        project_name=project_name,
        use_defaults=defaults,
        output_dir=output_dir,
        dry_run=dry_run,
    )


@app.command()
def doctor(
    check: str = typer.Option(
        None,
        "--check",
        "-c",
        help="Run a specific check only (e.g. 'naming-conventions').",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Auto-fix issues where possible (e.g. generate missing schema stubs).",
    ),
    ci: bool = typer.Option(
        False,
        "--ci",
        help="Non-interactive mode. Exit code 1 on failures.",
    ),
) -> None:
    """Run health checks on an existing dbt project.

    Validates naming conventions, test coverage, schema documentation,
    and other best practices. Use --fix to auto-generate missing schema
    stubs, or --ci for CI pipeline integration.
    """
    run_doctor(check_name=check, fix=fix, ci=ci)


def _print_banner() -> None:
    text = Text()
    text.append("✦  dbt-forge", style="bold cyan")
    text.append(" — scaffold production-ready dbt projects", style="dim")
    console.print()
    console.print(text)
    console.print()


if __name__ == "__main__":
    app()
