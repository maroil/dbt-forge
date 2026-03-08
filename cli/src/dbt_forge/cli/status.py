"""dbt-forge status — project stats dashboard."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from dbt_forge.scanner import (
    count_models_by_layer,
    find_project_root,
    find_sql_models,
    parse_packages,
    parse_sources,
    parse_yml_models,
    parse_yml_tests,
)

console = Console()


def run_status() -> None:
    """Display a project stats dashboard."""
    root = find_project_root()
    project_name = root.name

    layer_counts = count_models_by_layer(root)
    total_models = sum(layer_counts.values())

    sql_models = find_sql_models(root)
    documented = parse_yml_models(root)
    tested = parse_yml_tests(root)

    # Count non-internal models for coverage
    countable = [m for m in sql_models if not m.stem.startswith("_")]
    doc_count = sum(1 for m in countable if m.stem in documented)
    test_count = sum(1 for m in countable if m.stem in tested)
    doc_pct = int(doc_count / len(countable) * 100) if countable else 0
    test_pct = int(test_count / len(countable) * 100) if countable else 0

    sources = parse_sources(root)
    freshness_count = sum(1 for s in sources if s["has_freshness"])

    packages = parse_packages(root)

    # Build dashboard
    console.print()

    table = Table(
        title=f"Project: {project_name}",
        show_lines=False,
        padding=(0, 2),
        expand=False,
    )
    table.add_column("Models", min_width=20)
    table.add_column("Quality", min_width=20)
    table.add_column("Dependencies", min_width=20)

    # Models column
    models_lines = []
    for layer in ("staging", "intermediate", "marts", "other"):
        count = layer_counts[layer]
        if count > 0:
            models_lines.append(f"{layer}: {count}")
    models_lines.append(f"[bold]total: {total_models}[/bold]")
    models_text = "\n".join(models_lines)

    # Quality column
    quality_lines = [
        f"test coverage: {test_pct}%",
        f"doc coverage: {doc_pct}%",
    ]
    if sources:
        quality_lines.append(f"sources: {len(sources)} (freshness: {freshness_count})")
    quality_text = "\n".join(quality_lines)

    # Dependencies column
    if packages:
        deps_lines = [p["name"] for p in packages]
    else:
        deps_lines = ["(none)"]
    deps_text = "\n".join(deps_lines)

    table.add_row(models_text, quality_text, deps_text)
    console.print(table)
    console.print()
