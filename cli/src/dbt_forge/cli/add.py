"""The `add` subcommand — post-init scaffolding for existing dbt projects."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
import questionary
import typer
import typer.core
import yaml
from rich.console import Console

from dbt_forge.generator.renderer import render_template

console = Console()

class AddHelpGroup(typer.core.TyperGroup):
    """Custom group that appends usage examples after the default help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_help(ctx, formatter)
        _console = Console()
        _console.print()
        _console.print("[bold cyan]Examples:[/bold cyan]")
        _console.print()
        _console.print("  [green]$[/green] dbt-forge add source salesforce       Staging layer with source YAML")
        _console.print("  [green]$[/green] dbt-forge add mart finance             Mart + intermediate models")
        _console.print("  [green]$[/green] dbt-forge add snapshot orders          SCD type-2 snapshot")
        _console.print("  [green]$[/green] dbt-forge add seed country_codes       CSV + schema YAML")
        _console.print("  [green]$[/green] dbt-forge add macro cents_to_dollars   Reusable SQL macro")
        _console.print("  [green]$[/green] dbt-forge add exposure weekly_report   Exposure definition")
        _console.print("  [green]$[/green] dbt-forge add pre-commit               Pre-commit + editorconfig")
        _console.print("  [green]$[/green] dbt-forge add ci                       CI pipeline config")
        _console.print("  [green]$[/green] dbt-forge add model users              Interactive model generator")
        _console.print("  [green]$[/green] dbt-forge add test orders              Test generator")
        _console.print("  [green]$[/green] dbt-forge add package dbt-utils        Smart package installer")
        _console.print()
        _console.print("[dim]Run from inside a dbt project (must contain dbt_project.yml).[/dim]")
        _console.print()


add_app = typer.Typer(
    name="add",
    help="Add components to an existing dbt project.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    cls=AddHelpGroup,
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


@add_app.command("snapshot")
def add_snapshot(
    name: str = typer.Argument(..., help="Name of the snapshot to scaffold (e.g. 'orders')."),
) -> None:
    """Scaffold a new snapshot inside an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    ctx = {"name": name, "project_name": project_name}

    console.print()
    console.print(
        f"  Adding snapshot [bold cyan]{name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        project_root / f"snapshots/{name}.sql",
        render_template(f"{TEMPLATES_BASE}/snapshot.sql.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Snapshot [bold]{name}[/bold] scaffolded. "
        "Update the source reference and unique key to match your data.[/dim]"
    )
    console.print()


@add_app.command("seed")
def add_seed(
    name: str = typer.Argument(..., help="Name of the seed to scaffold (e.g. 'dim_country')."),
) -> None:
    """Scaffold a new seed (CSV + YAML) inside an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    ctx = {"name": name, "project_name": project_name}

    console.print()
    console.print(
        f"  Adding seed [bold cyan]{name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        project_root / f"seeds/{name}.csv",
        render_template(f"{TEMPLATES_BASE}/seed.csv.j2", ctx),
    )
    _write(
        project_root / f"seeds/_{name}__seeds.yml",
        render_template(f"{TEMPLATES_BASE}/seed.yml.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Seed [bold]{name}[/bold] scaffolded. "
        "Replace the CSV stub with your actual reference data.[/dim]"
    )
    console.print()


@add_app.command("exposure")
def add_exposure(
    name: str = typer.Argument(
        ..., help="Name of the exposure to scaffold (e.g. 'weekly_revenue')."
    ),
) -> None:
    """Scaffold a new exposure YAML inside an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    ctx = {"name": name, "project_name": project_name}

    console.print()
    console.print(
        f"  Adding exposure [bold cyan]{name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        project_root / f"models/marts/__{name}__exposures.yml",
        render_template(f"{TEMPLATES_BASE}/exposure.yml.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Exposure [bold]{name}[/bold] scaffolded. "
        "Update the depends_on references and owner details.[/dim]"
    )
    console.print()


@add_app.command("macro")
def add_macro(
    name: str = typer.Argument(
        ..., help="Name of the macro to scaffold (e.g. 'cents_to_dollars')."
    ),
) -> None:
    """Scaffold a new macro inside an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    ctx = {"name": name, "project_name": project_name}

    console.print()
    console.print(
        f"  Adding macro [bold cyan]{name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        project_root / f"macros/{name}.sql",
        render_template(f"{TEMPLATES_BASE}/macro.sql.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Macro [bold]{name}[/bold] scaffolded. "
        "Add your macro logic inside the block.[/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# Helpers for new commands
# ---------------------------------------------------------------------------

def _read_adapter_from_profiles(project_root: Path) -> str:
    """Read the adapter type from profiles.yml. Returns adapter key like 'bigquery'."""
    profiles_path = project_root / "profiles" / "profiles.yml"
    if not profiles_path.exists():
        return "bigquery"  # fallback
    data = yaml.safe_load(profiles_path.read_text())
    if not data:
        return "bigquery"
    # Profile is keyed by project name — get the first profile's dev target type
    for _profile_name, profile in data.items():
        if isinstance(profile, dict) and "outputs" in profile:
            for _target_name, target in profile["outputs"].items():
                if isinstance(target, dict) and "type" in target:
                    return target["type"]
    return "bigquery"


def _adapter_key_to_package(adapter_key: str) -> str:
    """Map adapter key to dbt adapter package name."""
    mapping = {
        "bigquery": "dbt-bigquery",
        "snowflake": "dbt-snowflake",
        "postgres": "dbt-postgres",
        "postgresql": "dbt-postgres",
        "duckdb": "dbt-duckdb",
        "databricks": "dbt-databricks",
        "redshift": "dbt-redshift",
        "trino": "dbt-trino",
        "spark": "dbt-spark",
    }
    return mapping.get(adapter_key, "dbt-core")


def _style() -> questionary.Style:
    return questionary.Style(
        [
            ("qmark", "fg:#00d7ff bold"),
            ("question", "bold"),
            ("answer", "fg:#00d7ff bold"),
            ("pointer", "fg:#00d7ff bold"),
            ("highlighted", "fg:#00d7ff bold"),
            ("selected", "fg:#00d7ff"),
        ]
    )


# ---------------------------------------------------------------------------
# add pre-commit
# ---------------------------------------------------------------------------

@add_app.command("pre-commit")
def add_pre_commit() -> None:
    """Scaffold pre-commit config, .editorconfig, and .sqlfluffignore."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)
    adapter_key = _read_adapter_from_profiles(project_root)
    add_sqlfluff = (project_root / ".sqlfluff").exists()

    ctx = {
        "project_name": project_name,
        "adapter_key": adapter_key,
        "dbt_adapter_package": _adapter_key_to_package(adapter_key),
        "add_sqlfluff": add_sqlfluff,
    }

    console.print()
    console.print(
        f"  Adding pre-commit config to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        project_root / ".pre-commit-config.yaml",
        render_template(".pre-commit-config.yaml.j2", ctx),
    )
    _write(
        project_root / ".editorconfig",
        render_template(".editorconfig.j2", ctx),
    )
    if add_sqlfluff:
        _write(
            project_root / ".sqlfluffignore",
            render_template(".sqlfluffignore.j2", ctx),
        )

    console.print()
    console.print(
        "  [dim]Pre-commit configured. Run [bold]pre-commit install[/bold] "
        "to activate hooks.[/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# add ci
# ---------------------------------------------------------------------------

CI_PROVIDERS = ["GitHub Actions", "GitLab CI", "Bitbucket Pipelines"]

CI_TEMPLATE_MAP = {
    "GitHub Actions": (
        ".github/workflows/dbt_ci.yml",
        ".github/workflows/dbt_ci.yml.j2",
    ),
    "GitLab CI": (
        ".gitlab-ci.yml",
        ".gitlab-ci.yml.j2",
    ),
    "Bitbucket Pipelines": (
        "bitbucket-pipelines.yml",
        "bitbucket-pipelines.yml.j2",
    ),
}


@add_app.command("ci")
def add_ci(
    provider: Optional[str] = typer.Argument(
        None,
        help="CI provider: 'github', 'gitlab', or 'bitbucket'. Omit for interactive prompt.",
    ),
) -> None:
    """Scaffold CI/CD pipeline config for an existing dbt project."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)
    adapter_key = _read_adapter_from_profiles(project_root)

    # Resolve provider
    provider_map = {
        "github": "GitHub Actions",
        "gitlab": "GitLab CI",
        "bitbucket": "Bitbucket Pipelines",
    }

    if provider and provider.lower() in provider_map:
        selected = [provider_map[provider.lower()]]
    elif provider:
        console.print(f"[red]Error:[/red] Unknown provider '{provider}'. Use: github, gitlab, bitbucket")
        sys.exit(1)
    else:
        # Interactive prompt
        choices = [
            questionary.Choice(title=p, value=p) for p in CI_PROVIDERS
        ]
        selected = questionary.checkbox(
            "Select CI provider(s):",
            choices=choices,
            style=_style(),
            validate=lambda v: True if v else "Select at least one provider.",
        ).ask()
        if selected is None:
            console.print("\n[dim]Aborted.[/dim]")
            sys.exit(0)

    # Adapter name mapping (profile type → display name for templates)
    adapter_display = {
        "bigquery": "BigQuery", "snowflake": "Snowflake",
        "postgres": "PostgreSQL", "duckdb": "DuckDB",
        "databricks": "Databricks", "redshift": "Redshift",
        "trino": "Trino", "spark": "Spark",
    }

    ctx = {
        "project_name": project_name,
        "adapter": adapter_display.get(adapter_key, adapter_key),
        "adapter_key": adapter_key,
        "dbt_adapter_package": _adapter_key_to_package(adapter_key),
        "packages": [],  # CI templates may reference packages
    }

    console.print()
    console.print(
        f"  Adding CI config to [bold]{project_root.name}[/bold]"
    )
    console.print()

    for prov in selected:
        dest_path, template = CI_TEMPLATE_MAP[prov]
        dest = project_root / dest_path
        if dest.exists():
            console.print(f"  [yellow]skip[/yellow]  {dest} already exists")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(render_template(template, ctx))
            console.print(f"  [green]\u2714[/green]  {dest}")

    console.print()
    console.print("  [dim]CI config added. Update credentials and secrets before merging.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# add model
# ---------------------------------------------------------------------------

LAYER_CHOICES = ["staging", "intermediate", "marts"]
MATERIALIZATION_CHOICES = ["view", "table", "incremental", "ephemeral"]
LAYER_DEFAULT_MAT = {
    "staging": "view",
    "intermediate": "ephemeral",
    "marts": "table",
}
TEST_CHOICES = ["unique", "not_null", "accepted_values", "relationships"]


@add_app.command("model")
def add_model(
    name: str = typer.Argument(..., help="Name of the model to create (e.g. 'users')."),
) -> None:
    """Interactively scaffold a new dbt model with SQL + YAML."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    # Layer selection
    layer = questionary.select(
        "Model layer:",
        choices=LAYER_CHOICES,
        style=_style(),
    ).ask()
    if layer is None:
        console.print("\n[dim]Aborted.[/dim]")
        return

    # Materialization
    default_mat = LAYER_DEFAULT_MAT[layer]
    materialization = questionary.select(
        "Materialization:",
        choices=MATERIALIZATION_CHOICES,
        default=default_mat,
        style=_style(),
    ).ask()
    if materialization is None:
        console.print("\n[dim]Aborted.[/dim]")
        return

    # Source (for staging only)
    source_name = ""
    entity = name
    if layer == "staging":
        source_name = questionary.text(
            "Source name (e.g. 'stripe'):",
            default="",
            style=_style(),
        ).ask()
        if source_name is None:
            console.print("\n[dim]Aborted.[/dim]")
            return

    # Description
    description = questionary.text(
        "Model description:",
        default="",
        style=_style(),
    ).ask()
    if description is None:
        console.print("\n[dim]Aborted.[/dim]")
        return

    # Columns
    columns: list[dict] = []
    add_cols = questionary.confirm(
        "Add columns interactively?",
        default=False,
        style=_style(),
    ).ask()
    if add_cols is None:
        console.print("\n[dim]Aborted.[/dim]")
        return

    if add_cols:
        while True:
            col_name = questionary.text(
                "Column name (blank to finish):",
                style=_style(),
            ).ask()
            if col_name is None:
                console.print("\n[dim]Aborted.[/dim]")
                return
            if not col_name.strip():
                break

            col_desc = questionary.text(
                f"Description for '{col_name}':",
                default="",
                style=_style(),
            ).ask()
            if col_desc is None:
                console.print("\n[dim]Aborted.[/dim]")
                return

            col_tests = questionary.checkbox(
                f"Tests for '{col_name}':",
                choices=[questionary.Choice(t, value=t) for t in TEST_CHOICES],
                style=_style(),
            ).ask()
            if col_tests is None:
                console.print("\n[dim]Aborted.[/dim]")
                return

            columns.append({
                "name": col_name.strip(),
                "description": col_desc,
                "tests": col_tests,
            })

    # Determine model name and directory
    if layer == "staging":
        prefix = f"stg_{source_name}__" if source_name else "stg_"
        model_name = f"{prefix}{name}"
        if source_name:
            model_dir = project_root / f"models/staging/{source_name}"
        else:
            model_dir = project_root / "models/staging"
    elif layer == "intermediate":
        model_name = f"int_{name}"
        model_dir = project_root / "models/intermediate"
    else:
        model_name = name
        model_dir = project_root / "models/marts"

    ctx = {
        "model_name": model_name,
        "name": name,
        "layer": layer,
        "materialization": materialization,
        "source_name": source_name,
        "entity": entity,
        "description": description,
        "columns": columns,
        "project_name": project_name,
    }

    console.print()
    console.print(
        f"  Adding model [bold cyan]{model_name}[/bold cyan] to [bold]{project_root.name}[/bold]"
    )
    console.print()

    _write(
        model_dir / f"{model_name}.sql",
        render_template(f"{TEMPLATES_BASE}/model.sql.j2", ctx),
    )
    _write(
        model_dir / f"_{model_name}__models.yml",
        render_template(f"{TEMPLATES_BASE}/model.yml.j2", ctx),
    )

    console.print()
    console.print(
        f"  [dim]Model [bold]{model_name}[/bold] scaffolded. "
        "Update the SQL and YAML to match your data.[/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# add test
# ---------------------------------------------------------------------------

@add_app.command("test")
def add_test(
    model_name: str = typer.Argument(..., help="Name of the model to test (e.g. 'stg_orders')."),
) -> None:
    """Scaffold a test for an existing dbt model."""
    project_root = _find_project_root()
    project_name = _read_project_name(project_root)

    test_type = questionary.select(
        "Test type:",
        choices=[
            questionary.Choice("Data test (custom SQL assertion)", value="data"),
            questionary.Choice("Unit test (dbt 1.8+ mock-based)", value="unit"),
        ],
        style=_style(),
    ).ask()
    if test_type is None:
        console.print("\n[dim]Aborted.[/dim]")
        return

    console.print()
    console.print(
        f"  Adding {test_type} test for [bold cyan]{model_name}[/bold cyan]"
    )
    console.print()

    if test_type == "data":
        test_name = f"assert_{model_name}_valid"
        ctx = {"test_name": test_name, "model_name": model_name}
        _write(
            project_root / f"tests/{test_name}.sql",
            render_template(f"{TEMPLATES_BASE}/test_data.sql.j2", ctx),
        )
    else:
        test_name = f"test_{model_name}"
        ctx = {"test_name": test_name, "model_name": model_name}
        _write(
            project_root / f"tests/unit/{test_name}.yml",
            render_template(f"{TEMPLATES_BASE}/test_unit.yml.j2", ctx),
        )

    console.print()
    console.print(
        f"  [dim]Test [bold]{test_name}[/bold] scaffolded. "
        "Update the test logic to match your assertions.[/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# add package
# ---------------------------------------------------------------------------

# Curated registry of popular dbt packages
PACKAGE_REGISTRY: dict[str, dict] = {
    "dbt-utils": {
        "hub": "dbt-labs/dbt_utils",
        "version": '[">=1.3.0", "<2.0.0"]',
    },
    "dbt-expectations": {
        "hub": "metaplane/dbt_expectations",
        "version": '[">=0.10.0", "<0.11.0"]',
    },
    "dbt-codegen": {
        "hub": "dbt-labs/codegen",
        "version": '[">=0.12.0", "<0.13.0"]',
    },
    "elementary": {
        "hub": "elementary-data/elementary",
        "version": '[">=0.16.0", "<0.17.0"]',
    },
    "dbt-audit-helper": {
        "hub": "dbt-labs/audit_helper",
        "version": '[">=0.12.0", "<0.13.0"]',
    },
    "dbt-project-evaluator": {
        "hub": "dbt-labs/dbt_project_evaluator",
        "version": '[">=0.11.0", "<0.12.0"]',
    },
    "dbt-meta-testing": {
        "hub": "tnightengale/dbt_meta_testing",
        "version": '[">=0.3.0", "<0.4.0"]',
    },
    "dbt-date": {
        "hub": "calogica/dbt_date",
        "version": '[">=0.10.0", "<0.11.0"]',
    },
    "dbt-profiler": {
        "hub": "data-mie/dbt_profiler",
        "version": '[">=0.8.0", "<0.9.0"]',
    },
    "re-data": {
        "hub": "re-data/dbt_re_data",
        "version": '[">=0.11.0", "<0.12.0"]',
    },
    "dbt-artifacts": {
        "hub": "brooklyn-data/dbt_artifacts",
        "version": '[">=2.6.0", "<3.0.0"]',
    },
    "dbt-external-tables": {
        "hub": "dbt-labs/dbt_external_tables",
        "version": '[">=0.9.0", "<0.10.0"]',
    },
    "metrics": {
        "hub": "dbt-labs/metrics",
        "version": '[">=0.5.0", "<0.6.0"]',
    },
    "dbt-activity-schema": {
        "hub": "bcodell/dbt_activity_schema",
        "version": '[">=2.0.0", "<3.0.0"]',
    },
    "dbt-constraints": {
        "hub": "Snowflake-Labs/dbt_constraints",
        "version": '[">=1.0.0", "<2.0.0"]',
    },
    "dbt-privacy": {
        "hub": "pvcy/dbt_privacy",
        "version": '[">=0.3.0", "<0.4.0"]',
    },
    "dbt-unit-testing": {
        "hub": "EqualExperts/dbt-unit-testing",
        "version": '[">=0.5.0", "<0.6.0"]',
    },
    "dbt-fivetran-utils": {
        "hub": "fivetran/fivetran_utils",
        "version": '[">=0.4.0", "<0.5.0"]',
    },
    "dbt-snowplow-web": {
        "hub": "snowplow/dbt_snowplow_web",
        "version": '[">=1.0.0", "<2.0.0"]',
    },
    "dbt-segment": {
        "hub": "dbt-labs/segment",
        "version": '[">=0.12.0", "<0.13.0"]',
    },
}


@add_app.command("package")
def add_package(
    name: Optional[str] = typer.Argument(
        None, help="Package name (e.g. 'dbt-utils'). Omit to browse."
    ),
    list_packages: bool = typer.Option(
        False, "--list", "-l", help="List all available packages."
    ),
) -> None:
    """Add a dbt package to packages.yml with known-good version ranges."""
    project_root = _find_project_root()

    if list_packages:
        console.print()
        console.print("[bold cyan]Available packages:[/bold cyan]")
        console.print()
        for pkg_name, info in sorted(PACKAGE_REGISTRY.items()):
            console.print(f"  [green]{pkg_name:<30}[/green] {info['hub']}")
        console.print()
        return

    if not name:
        # Interactive selection
        choices = [
            questionary.Choice(f"{n}  ({info['hub']})", value=n)
            for n, info in sorted(PACKAGE_REGISTRY.items())
        ]
        name = questionary.select(
            "Select package:",
            choices=choices,
            style=_style(),
        ).ask()
        if name is None:
            console.print("\n[dim]Aborted.[/dim]")
            return

    if name not in PACKAGE_REGISTRY:
        console.print(f"[red]Error:[/red] Unknown package '{name}'. Use --list to see available packages.")
        console.print("[dim]For custom packages, add them manually to packages.yml.[/dim]")
        sys.exit(1)

    pkg_info = PACKAGE_REGISTRY[name]
    packages_path = project_root / "packages.yml"

    if not packages_path.exists():
        console.print("[red]Error:[/red] No packages.yml found.")
        sys.exit(1)

    data = yaml.safe_load(packages_path.read_text()) or {}
    packages_list = data.get("packages", [])

    # Check if already installed
    for pkg in packages_list:
        if isinstance(pkg, dict) and "package" in pkg:
            if pkg["package"] == pkg_info["hub"]:
                console.print(f"  [yellow]skip[/yellow]  {name} is already in packages.yml")
                return

    # Add the package
    new_entry = {
        "package": pkg_info["hub"],
        "version": pkg_info["version"],
    }
    packages_list.append(new_entry)
    data["packages"] = packages_list

    packages_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    console.print()
    console.print(f"  [green]\u2714[/green]  Added [bold]{name}[/bold] ({pkg_info['hub']}) to packages.yml")
    console.print()
    console.print("  [dim]Run [bold]dbt deps[/bold] to install.[/dim]")
    console.print()
