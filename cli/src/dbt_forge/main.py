"""dbt-forge entrypoint."""

import importlib.util

import typer
from rich.console import Console

from dbt_forge.cli.add import add_app
from dbt_forge.cli.doctor import run_doctor
from dbt_forge.cli.impact import run_impact
from dbt_forge.cli.init import init_command
from dbt_forge.cli.lint import run_lint
from dbt_forge.cli.migrate import run_migrate
from dbt_forge.cli.status import run_status
from dbt_forge.cli.update import run_update
from dbt_forge.ui.theme import (
    forge_console,
    print_banner,
    print_error,
    set_verbose,
)

HELP_TEXT = """\
Scaffold production-ready dbt projects with opinionated defaults.

Like create-t3-app, but for dbt. Generates a complete project structure
with staging/marts layers, CI pipelines, pre-commit hooks, and more.
"""

EPILOG = """\
[bold cyan]Getting started:[/bold cyan]

  [green]$[/green] dbt-forge init my-project          Interactive
  [green]$[/green] dbt-forge init my-project [bold]-d[/bold]       Defaults
  [green]$[/green] dbt-forge doctor                     Health checks
  [green]$[/green] dbt-forge add source salesforce      Add component

[dim]Docs: https://dbt-forge.marou.one[/dim]
"""

# -- Rich help panels -------------------------------------------------------
_SCAFFOLD = "Scaffold"
_ANALYZE = "Analyze"
_GOVERN = "Govern"
_AI = "AI"
_MIGRATE = "Migrate"
_UTILITY = "Utility"

app = typer.Typer(
    name="dbt-forge",
    help=HELP_TEXT,
    epilog=EPILOG,
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(add_app, name="add", rich_help_panel=_SCAFFOLD)

console = Console()


def _adapter_import_name(package_name: str) -> str:
    """Map pip package names to importable module names."""
    import_name = package_name.replace("-", "_").split("[")[0]
    overrides = {
        "psycopg2-binary": "psycopg2",
        "snowflake-connector-python": "snowflake.connector",
        "google-cloud-bigquery": "google.cloud.bigquery",
        "databricks-sql-connector": "databricks.sql",
    }
    return overrides.get(package_name, import_name)


def _module_available(import_name: str) -> bool:
    """Return whether a module can be imported without raising for missing parents."""
    try:
        return importlib.util.find_spec(import_name) is not None
    except ModuleNotFoundError:
        return False


def version_callback(value: bool) -> None:
    if value:
        from dbt_forge import __version__

        forge_console.print(f"dbt-forge v{__version__}")
        raise typer.Exit()


_verbose = False


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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show full tracebacks on error.",
    ),
) -> None:
    global _verbose
    _verbose = verbose
    set_verbose(verbose)


@app.command(rich_help_panel=_SCAFFOLD)
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
    preset: str = typer.Option(
        None,
        "--preset",
        "-p",
        help="Path or URL to a preset YAML file.",
    ),
    mesh: bool = typer.Option(
        False,
        "--mesh",
        help="Create a multi-project dbt Mesh setup.",
    ),
) -> None:
    """Scaffold a new production-ready dbt project.

    Walks you through an interactive setup to pick your adapter (BigQuery,
    Snowflake, Postgres, etc.), CI provider, packages, and optional features
    like unit tests, MetricFlow, snapshots, seeds, and macros.
    """
    print_banner()

    if mesh:
        from dbt_forge.cli.init import init_mesh_command

        init_mesh_command(
            project_name=project_name,
            use_defaults=defaults,
            output_dir=output_dir,
            dry_run=dry_run,
        )
        return

    preset_config = None
    if preset:
        from dbt_forge.presets import load_preset, validate_preset

        preset_config = load_preset(preset)
        errors = validate_preset(preset_config)
        if errors:
            print_error("Preset validation errors:")
            for err in errors:
                forge_console.print(f"  - {err}")
            raise typer.Exit(1)
        forge_console.print(
            f"  Using preset: [bold cyan]{preset_config.name or preset}[/bold cyan]"
        )
        console.print()

    init_command(
        project_name=project_name,
        use_defaults=defaults,
        output_dir=output_dir,
        dry_run=dry_run,
        preset=preset_config,
    )


@app.command(rich_help_panel=_ANALYZE)
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
    format: str = typer.Option(
        "table",
        "--format",
        help="Output format: table or json.",
    ),
) -> None:
    """Run health checks on an existing dbt project.

    Validates naming conventions, test coverage, schema documentation,
    and other best practices. Use --fix to auto-generate missing schema
    stubs, or --ci for CI pipeline integration.
    """
    run_doctor(check_name=check, fix=fix, ci=ci, output_format=format)


@app.command(rich_help_panel=_ANALYZE)
def status() -> None:
    """Show a dashboard of project stats (models, tests, docs, packages)."""
    run_status()


@app.command(rich_help_panel=_MIGRATE)
def update(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without writing anything.",
    ),
) -> None:
    """Re-apply dbt-forge templates and show diffs for changed files."""
    run_update(dry_run=dry_run)


@app.command(rich_help_panel=_MIGRATE)
def migrate(
    sql_dir: str = typer.Argument(
        ...,
        help="Directory containing SQL files to migrate.",
    ),
    output_dir: str = typer.Option(
        ".",
        "--output",
        "-o",
        help="Output directory for the dbt project.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview migration without writing files.",
    ),
) -> None:
    """Convert legacy SQL scripts into a dbt project with ref() and source()."""
    run_migrate(sql_dir=sql_dir, output_dir=output_dir, dry_run=dry_run)


@app.command(rich_help_panel=_ANALYZE)
def impact(
    model: str = typer.Argument(None, help="Model to analyze downstream impact for."),
    diff: bool = typer.Option(False, "--diff", help="Detect changed models from git diff."),
    base: str = typer.Option("main", "--base", help="Base git ref for diff comparison."),
    pr: bool = typer.Option(False, "--pr", help="Output markdown for PR descriptions."),
    format: str = typer.Option("table", "--format", help="Output format: table or json."),
) -> None:
    """Analyze downstream impact of model changes."""
    run_impact(model=model, diff=diff, base=base, pr=pr, output_format=format)


@app.command(rich_help_panel=_ANALYZE)
def lint(
    rule: str = typer.Option(None, "--rule", "-r", help="Run a specific rule only."),
    ci: bool = typer.Option(False, "--ci", help="Exit 1 on warnings."),
    config: str = typer.Option(None, "--config", help="Path to lint config YAML."),
    format: str = typer.Option("table", "--format", help="Output format: table or json."),
) -> None:
    """Lint dbt project structure for architectural issues."""
    run_lint(rule=rule, ci=ci, config_path=config, output_format=format)


@app.command(rich_help_panel=_UTILITY)
def adapters() -> None:
    """Show which optional warehouse adapter packages are installed."""
    from dbt_forge.introspect.connectors import ADAPTER_DEPS, ADAPTER_MAP
    from dbt_forge.ui.theme import make_table

    table = make_table("dbt-forge adapters", [
        ("Adapter", {"min_width": 14}),
        ("Package", {"min_width": 28}),
        ("Status", {"justify": "center"}),
    ])
    seen: set[str] = set()
    for key in sorted(ADAPTER_MAP):
        dep = ADAPTER_DEPS.get(key, key)
        if dep in seen:
            continue
        seen.add(dep)
        found = _module_available(_adapter_import_name(dep))
        status = "[green]installed[/green]" if found else "[dim]not installed[/dim]"
        table.add_row(key, dep, status)

    console.print()
    console.print(table)
    console.print()


@app.command(rich_help_panel=_ANALYZE)
def cost(
    days: int = typer.Option(30, "--days", help="Number of days to analyze."),
    top: int = typer.Option(10, "--top", help="Number of top models to show."),
    report: bool = typer.Option(False, "--report", help="Output markdown report."),
    target: str = typer.Option("dev", "--target", help="dbt target/profile to use."),
    format: str = typer.Option("table", "--format", help="Output format: table or json."),
) -> None:
    """Estimate query costs from warehouse usage data."""
    from dbt_forge.cli.cost_cmd import run_cost

    run_cost(days=days, top=top, report=report, target=target, output_format=format)


changelog_app = typer.Typer(
    name="changelog",
    help="Track and communicate model changes.",
    no_args_is_help=True,
)
app.add_typer(changelog_app, name="changelog", rich_help_panel=_GOVERN)

contracts_app = typer.Typer(
    name="contracts",
    help="Generate and manage dbt data contracts.",
    no_args_is_help=True,
)
app.add_typer(contracts_app, name="contracts", rich_help_panel=_GOVERN)

preset_app = typer.Typer(
    name="preset",
    help="Manage dbt-forge presets.",
    no_args_is_help=True,
)
app.add_typer(preset_app, name="preset", rich_help_panel=_UTILITY)

docs_app = typer.Typer(
    name="docs",
    help="AI-assisted documentation generation.",
    no_args_is_help=True,
)
app.add_typer(docs_app, name="docs", rich_help_panel=_AI)


@docs_app.command("generate")
def docs_generate(
    model: str = typer.Option(
        None, "--model", "-m", help="Generate docs for a specific model only."
    ),
    provider: str = typer.Option(None, "--provider", help="LLM provider: claude, openai, ollama."),
    auto_accept: bool = typer.Option(
        False, "--yes", "-y", help="Auto-accept all generated descriptions."
    ),
    delay: float = typer.Option(1.0, "--delay", help="Delay (seconds) between API calls."),
) -> None:
    """Generate model and column descriptions using an LLM."""
    from dbt_forge.cli.docs_cmd import run_docs_generate

    run_docs_generate(
        model=model,
        provider_key=provider,
        auto_accept=auto_accept,
        delay=delay,
    )


@changelog_app.command("generate")
def changelog_generate(
    from_ref: str = typer.Option(None, "--from", help="Starting git ref (default: latest tag)."),
    to_ref: str = typer.Option("HEAD", "--to", help="Ending git ref."),
    format: str = typer.Option("markdown", "--format", help="Output format: markdown or json."),
    breaking_only: bool = typer.Option(
        False, "--breaking-only", help="Show only breaking changes."
    ),
    output: str = typer.Option(None, "-o", "--output", help="Write to file instead of stdout."),
) -> None:
    """Generate a changelog of model changes between git refs."""
    from dbt_forge.cli.changelog_cmd import run_changelog_generate

    run_changelog_generate(
        from_ref=from_ref,
        to_ref=to_ref,
        format=format,
        breaking_only=breaking_only,
        output=output,
    )


@contracts_app.command("generate")
def contracts_generate(
    model: str = typer.Argument(None, help="Model to generate contract for."),
    all_public: bool = typer.Option(
        False, "--all-public", help="Generate contracts for all public models."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-accept all contracts."),
    target: str = typer.Option("dev", "--target", help="dbt target/profile to use."),
) -> None:
    """Generate data contracts with enforced column types."""
    from dbt_forge.cli.contracts_cmd import run_contracts_generate

    run_contracts_generate(
        model=model,
        all_public=all_public,
        dry_run=dry_run,
        auto_accept=yes,
        target=target,
    )


@preset_app.command("validate")
def preset_validate(
    path: str = typer.Argument(..., help="Path or URL to a preset YAML file."),
) -> None:
    """Validate a preset file."""
    from dbt_forge.presets import load_preset, validate_preset

    try:
        preset_config = load_preset(path)
    except Exception as e:
        console.print(f"[red]Error loading preset:[/red] {e}")
        raise typer.Exit(1)

    errors = validate_preset(preset_config)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)
    else:
        label = preset_config.name or path
        console.print(f"[green]\u2714[/green]  Preset [bold]{label}[/bold] is valid.")
        if preset_config.description:
            console.print(f"  {preset_config.description}")
        console.print(f"  Defaults: {', '.join(preset_config.defaults.keys())}")
        console.print(f"  Locked: {', '.join(preset_config.locked) or '(none)'}")


if __name__ == "__main__":
    app()
