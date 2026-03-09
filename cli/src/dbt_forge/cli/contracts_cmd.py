"""dbt-forge contracts — CLI command for data contract generation."""

from __future__ import annotations

from rich.console import Console

from dbt_forge.contracts import (
    find_public_models,
    generate_contract,
    get_model_schema,
    introspect_model_columns,
)
from dbt_forge.introspect.connectors import get_introspector
from dbt_forge.introspect.profile_reader import read_profile
from dbt_forge.scanner import find_project_root, parse_yml_models

console = Console()


def run_contracts_generate(
    model: str | None = None,
    all_public: bool = False,
    dry_run: bool = False,
    auto_accept: bool = False,
    target: str = "dev",
) -> None:
    """Generate data contracts for models."""
    root = find_project_root()

    # Determine which models to process
    models_to_process: list[str] = []
    if model:
        models_to_process = [model]
    elif all_public:
        models_to_process = find_public_models(root)
        if not models_to_process:
            console.print("[yellow]No public models found.[/yellow]")
            return
        console.print(f"[bold]Found {len(models_to_process)} public model(s)[/bold]")
    else:
        console.print("[red]Error:[/red] Provide a model name or use --all-public.")
        return

    # Connect to warehouse
    try:
        profile = read_profile(root, target=target)
    except Exception as e:
        console.print(f"[red]Error reading profile:[/red] {e}")
        return

    adapter = profile.get("type", "")
    if not adapter:
        console.print("[red]Error:[/red] Could not determine adapter from profile.")
        return

    try:
        introspector = get_introspector(adapter, **profile)
        introspector.connect()
    except Exception as e:
        console.print(f"[red]Error connecting to warehouse:[/red] {e}")
        return

    yml_models = parse_yml_models(root)

    try:
        for model_name in models_to_process:
            console.print(f"\n[bold]Processing: {model_name}[/bold]")

            schema = get_model_schema(root, model_name)
            if not schema:
                console.print("  [yellow]Could not determine schema, skipping.[/yellow]")
                continue

            try:
                columns = introspect_model_columns(introspector, schema, model_name)
            except Exception as e:
                console.print(f"  [yellow]Could not introspect columns: {e}[/yellow]")
                continue

            if not columns:
                console.print("  [yellow]No columns found, skipping.[/yellow]")
                continue

            # Display columns
            console.print(f"  Found {len(columns)} column(s):")
            for col in columns:
                nullable = "NULL" if col.is_nullable else "NOT NULL"
                console.print(f"    {col.name}: {col.data_type} ({nullable})")

            # Find or create YAML path
            yml_path = yml_models.get(model_name)
            if not yml_path:
                yml_path = root / "models" / f"_{model_name}__models.yml"

            content = generate_contract(yml_path, model_name, columns)

            if dry_run:
                console.print(f"\n  [dim]Would write to {yml_path}:[/dim]")
                console.print(content)
                continue

            if not auto_accept:
                try:
                    import questionary

                    choice = questionary.select(
                        f"Apply contract for {model_name}?",
                        choices=["Accept", "Skip"],
                    ).ask()
                    if choice != "Accept":
                        console.print(f"  [dim]Skipped {model_name}[/dim]")
                        continue
                except (ImportError, EOFError, KeyboardInterrupt):
                    pass

            yml_path.parent.mkdir(parents=True, exist_ok=True)
            yml_path.write_text(content)
            console.print(f"  [green]Contract written to {yml_path.relative_to(root)}[/green]")

    finally:
        introspector.close()
