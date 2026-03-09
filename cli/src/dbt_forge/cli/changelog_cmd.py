"""dbt-forge changelog — CLI command for model change tracking."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from dbt_forge.changelog import (
    _get_latest_tag,
    detect_changes_between_refs,
    render_changelog_json,
    render_changelog_markdown,
)
from dbt_forge.scanner import find_project_root

console = Console()


def run_changelog_generate(
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    format: str = "markdown",
    breaking_only: bool = False,
    output: str | None = None,
) -> None:
    """Generate a changelog between git refs."""
    root = find_project_root()

    if not from_ref:
        from_ref = _get_latest_tag(root)
        if not from_ref:
            console.print("[yellow]No git tag found. Use --from to specify a ref.[/yellow]")
            return
        console.print(f"[dim]Using latest tag: {from_ref}[/dim]")

    changes = detect_changes_between_refs(root, from_ref, to_ref)

    if breaking_only:
        changes = [c for c in changes if c.is_breaking]

    if not changes:
        console.print("[green]No model changes detected.[/green]")
        return

    if format == "json":
        rendered = render_changelog_json(changes)
    else:
        rendered = render_changelog_markdown(changes)

    if output:
        Path(output).write_text(rendered)
        console.print(f"[green]Changelog written to {output}[/green]")
    else:
        console.print(rendered)
