"""The ``docs generate`` command -- AI-assisted documentation generation."""

from __future__ import annotations

import time

import questionary
import typer
from rich.console import Console
from rich.table import Table

from dbt_forge.docs import (
    find_models_needing_docs,
    read_model_sql,
    update_model_descriptions,
)
from dbt_forge.ui.theme import abort, forge_style, print_error, print_ok

console = Console()


def run_docs_generate(
    model: str | None = None,
    provider_key: str | None = None,
    auto_accept: bool = False,
    delay: float = 1.0,
) -> None:
    """Generate AI-assisted documentation for models with missing descriptions."""
    from dbt_forge.cli.add import _find_project_root

    project_root = _find_project_root()

    # Find models needing docs
    models = find_models_needing_docs(project_root)
    if model:
        models = [m for m in models if m["model_name"] == model]

    if not models:
        if not model:
            print_ok("All models are fully documented!")
        else:
            console.print(f"  [yellow]No undocumented model found matching '{model}'.[/yellow]")
        return

    console.print(f"  Found [bold]{len(models)}[/bold] model(s) needing documentation.")
    console.print()

    # Select provider
    provider = _select_provider(provider_key)
    if provider is None:
        return

    console.print(f"  Using [bold cyan]{provider.name()}[/bold cyan] for generation.")
    console.print()

    accepted = 0
    skipped = 0

    for i, model_info in enumerate(models):
        model_name = model_info["model_name"]
        sql = read_model_sql(model_info["sql_path"])
        columns = model_info["columns"]
        existing = model_info["existing_descriptions"]

        console.print(
            f"  [{i + 1}/{len(models)}] Generating docs for [bold cyan]{model_name}[/bold cyan]..."
        )

        try:
            result = provider.generate_descriptions(
                model_name=model_name,
                sql=sql,
                columns=columns,
                existing_descriptions=existing if existing else None,
            )
        except Exception as e:
            print_error(f"Error generating docs: {e}")
            skipped += 1
            continue

        # Display results
        if result.model_description:
            console.print(f"    Model: [italic]{result.model_description}[/italic]")

        if result.column_descriptions:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Column")
            table.add_column("Description")
            for col_name, col_desc in result.column_descriptions.items():
                if col_name in existing:
                    continue  # Skip already described columns
                table.add_row(col_name, col_desc)
            if table.row_count > 0:
                console.print(table)

        # Accept/skip
        if auto_accept:
            action = "accept"
        else:
            action = questionary.select(
                "Action:",
                choices=[
                    questionary.Choice("Accept", value="accept"),
                    questionary.Choice("Skip", value="skip"),
                ],
                style=forge_style(),
            ).ask()
            if action is None:
                abort()

        if action == "accept":
            update_model_descriptions(
                yml_path=model_info["yml_path"],
                model_name=model_name,
                model_description=result.model_description,
                column_descriptions=result.column_descriptions,
            )
            print_ok(f"Updated {model_info['yml_path'].name}")
            accepted += 1
        else:
            skipped += 1

        # Rate limiting
        if i < len(models) - 1 and delay > 0:
            time.sleep(delay)

        console.print()

    console.print(f"  [bold]Done.[/bold] {accepted} updated, {skipped} skipped.")
    console.print()


def _select_provider(provider_key: str | None):
    """Select or detect an LLM provider."""
    from dbt_forge.llm.providers import create_provider, get_available_providers

    if provider_key:
        try:
            return create_provider(provider_key)
        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(1)

    available = get_available_providers()
    if not available:
        console.print(
            "[red]Error:[/red] No LLM providers available.\n"
            "Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, or start Ollama."
        )
        raise typer.Exit(1)

    if len(available) == 1:
        key, display = available[0]
        try:
            return create_provider(key)
        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(1)

    # Multiple providers -- let user choose
    choices = [questionary.Choice(display, value=key) for key, display in available]
    selected = questionary.select(
        "Select LLM provider:",
        choices=choices,
        style=forge_style(),
    ).ask()
    if selected is None:
        abort()

    try:
        return create_provider(selected)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
