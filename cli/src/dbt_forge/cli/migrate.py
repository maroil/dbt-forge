"""The `migrate` command — convert legacy SQL scripts into a dbt project."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from dbt_forge.generator.renderer import render_template
from dbt_forge.sql_parser import (
    DependencyGraph,
    ParsedSQL,
    build_dependency_graph,
    detect_layer,
    parse_sql_file,
    replace_refs_in_sql,
    topological_sort,
)

console = Console()

_CREATE_PREFIX_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?"
    r"(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"[a-zA-Z0-9_.]+\s+AS\s+",
    re.IGNORECASE,
)


def _to_snake(name: str) -> str:
    """Convert a name to snake_case."""
    s = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower().strip("_")


def _strip_create_prefix(sql: str) -> str:
    """Strip CREATE TABLE/VIEW ... AS prefix, leaving just the SELECT."""
    m = _CREATE_PREFIX_RE.search(sql)
    if m:
        return sql[m.end() :].strip().rstrip(";").strip()
    return sql.strip().rstrip(";").strip()


def _detect_sources(
    parsed_files: list[ParsedSQL],
    graph: DependencyGraph,
) -> dict[str, set[str]]:
    """Find tables that are referenced but never created (external sources).

    Returns: {schema_or_default: {table_name, ...}}
    """
    # Collect all qualified names of created tables
    created_qualified: set[str] = set()
    created_bare: set[str] = set()
    for pf in parsed_files:
        for cs in pf.creates:
            created_qualified.add(cs.table_ref.qualified.lower())
            created_bare.add(cs.table_ref.table.lower())

    sources: dict[str, set[str]] = {}
    for pf in parsed_files:
        for ref in pf.references:
            q = ref.qualified.lower()
            # If the ref is schema-qualified, only match against qualified names
            if ref.schema:
                if q not in created_qualified:
                    sources.setdefault(ref.schema, set()).add(ref.table)
            else:
                # Bare ref: only a source if no created table has this name
                if ref.table.lower() not in created_bare:
                    sources.setdefault("raw", set()).add(ref.table)

    return sources


def _derive_model_name(node_key: str, layer: str, sources: dict[str, set[str]]) -> str:
    """Derive a dbt model name from a node key and layer."""
    ref = node_key
    # Strip schema prefix for the model name
    if "." in ref:
        ref = ref.split(".")[-1]
    name = _to_snake(ref)

    if layer == "staging":
        # Try to figure out the source for the prefix
        # For staging, we prefix with stg_<source>__
        if not name.startswith("stg_"):
            return f"stg_{name}"
    elif layer == "intermediate":
        if not name.startswith("int_"):
            return f"int_{name}"

    return name


def run_migrate(
    sql_dir: str,
    output_dir: str = ".",
    dry_run: bool = False,
) -> None:
    """Convert legacy SQL scripts into a dbt project with ref() and source()."""
    sql_path = Path(sql_dir)
    out_path = Path(output_dir)

    if not sql_path.is_dir():
        console.print(f"[red]Error:[/red] {sql_dir} is not a directory.")
        return

    # 1. Scan for SQL files
    sql_files = sorted(sql_path.rglob("*.sql"))
    if not sql_files:
        console.print(f"[yellow]No .sql files found in {sql_dir}[/yellow]")
        return

    console.print(f"  Scanning [bold]{len(sql_files)}[/bold] SQL file(s) in {sql_dir}")

    # 2. Parse each file
    parsed_files: list[ParsedSQL] = []
    for f in sql_files:
        try:
            parsed = parse_sql_file(f)
            if parsed.creates or parsed.references:
                parsed_files.append(parsed)
        except Exception as e:
            console.print(f"  [yellow]Warning:[/yellow] Could not parse {f}: {e}")

    if not parsed_files:
        console.print("[yellow]No CREATE statements or table references found.[/yellow]")
        return

    # 3. Build dependency graph
    graph = build_dependency_graph(parsed_files)

    # 4. Topological sort
    dep_order = topological_sort(graph)

    # 5. Detect sources
    sources = _detect_sources(parsed_files, graph)

    # 6. Detect layers and build model info
    models_info: list[dict] = []
    ref_map: dict[str, str] = {}  # qualified_name -> model_name

    for node_key in dep_order:
        layer = detect_layer(node_key, graph)
        model_name = _derive_model_name(node_key, layer, sources)
        ref_map[node_key] = model_name
        # Also map bare table name
        if "." in node_key:
            ref_map[node_key.split(".")[-1]] = model_name

        pf = graph.nodes[node_key]
        columns = []
        for cs in pf.creates:
            if cs.table_ref.qualified.lower() == node_key:
                columns = cs.columns
                break

        models_info.append(
            {
                "name": model_name,
                "layer": layer,
                "node_key": node_key,
                "original_file": str(pf.file_path),
                "columns": columns,
                "raw_sql": pf.raw_sql,
            }
        )

    # Build source_map for ref replacement
    source_map: dict[str, tuple[str, str]] = {}
    for schema, tables in sources.items():
        for table in tables:
            qualified = f"{schema}.{table}"
            source_map[qualified] = (schema, table)
            source_map[table] = (schema, table)

    # Print summary
    console.print(
        f"  Found [bold]{len(models_info)}[/bold] model(s), [bold]{len(sources)}[/bold] source(s)"
    )
    console.print()

    # Show table
    tbl = Table(title="Migration Plan", show_lines=False)
    tbl.add_column("Model", style="cyan")
    tbl.add_column("Layer", style="green")
    tbl.add_column("Original File", style="dim")
    for m in models_info:
        tbl.add_row(m["name"], m["layer"], m["original_file"])
    console.print(tbl)
    console.print()

    if dry_run:
        console.print("[yellow]Dry run — no files written.[/yellow]")
        return

    # 7. Generate output files
    files_written: list[str] = []

    # Generate source YAML files
    for schema, tables in sources.items():
        source_path = out_path / "models" / "staging" / schema / f"_{schema}__sources.yml"
        content = render_template(
            "migrate/source.yml.j2",
            {
                "source_name": schema,
                "schema": schema,
                "tables": sorted(tables),
            },
        )
        _write_file(source_path, content)
        files_written.append(str(source_path))

    # Generate model SQL and YAML files
    for model in models_info:
        layer = model["layer"]
        model_name = model["name"]

        # Determine output subdirectory
        if layer == "staging":
            # Find which source this staging model reads from
            sub_dir = out_path / "models" / "staging"
        elif layer == "intermediate":
            sub_dir = out_path / "models" / "intermediate"
        else:
            sub_dir = out_path / "models" / "marts"

        # Generate SQL with ref/source substitution
        sql_body = _strip_create_prefix(model["raw_sql"])
        sql_body = replace_refs_in_sql(sql_body, ref_map, source_map)

        sql_content = render_template(
            "migrate/model.sql.j2",
            {
                "sql_body": sql_body,
            },
        )
        sql_dest = sub_dir / f"{model_name}.sql"
        _write_file(sql_dest, sql_content)
        files_written.append(str(sql_dest))

        # Generate YAML
        yml_content = render_template(
            "migrate/model.yml.j2",
            {
                "model_name": model_name,
                "original_file": model["original_file"],
                "columns": [{"name": c.name, "data_type": c.data_type} for c in model["columns"]],
            },
        )
        yml_dest = sub_dir / f"_{model_name}__models.yml"
        _write_file(yml_dest, yml_content)
        files_written.append(str(yml_dest))

    # Generate migration report
    report_content = render_template(
        "migrate/migration_report.md.j2",
        {
            "files_scanned": len(sql_files),
            "models_generated": len(models_info),
            "sources_detected": len(sources),
            "models": models_info,
            "sources": {s: sorted(t) for s, t in sources.items()},
            "dependency_order": dep_order,
        },
    )
    report_dest = out_path / "migration_report.md"
    _write_file(report_dest, report_content)
    files_written.append(str(report_dest))

    console.print(f"  [green]Wrote {len(files_written)} file(s)[/green]")
    console.print(f"  Migration report: [bold]{report_dest}[/bold]")


def _write_file(dest: Path, content: str) -> None:
    """Write a file, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    console.print(f"  [green]created[/green]  {dest}")
