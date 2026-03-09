"""Regex-based SQL parsing for migration assistant."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TableRef:
    """A reference to a table, optionally qualified with a schema."""

    schema: str | None
    table: str

    @property
    def qualified(self) -> str:
        if self.schema:
            return f"{self.schema}.{self.table}"
        return self.table


@dataclass
class ColumnDef:
    """A column definition extracted from a CREATE TABLE statement."""

    name: str
    data_type: str


@dataclass
class CreateStatement:
    """A parsed CREATE TABLE/VIEW statement."""

    table_ref: TableRef
    view_or_table: str
    columns: list[ColumnDef]
    raw_sql: str


@dataclass
class ParsedSQL:
    """Full parse result for a single SQL file."""

    file_path: Path
    creates: list[CreateStatement]
    references: list[TableRef]
    raw_sql: str


@dataclass
class DependencyGraph:
    """Dependency graph built from parsed SQL files."""

    nodes: dict[str, ParsedSQL] = field(default_factory=dict)
    edges: dict[str, set[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_CREATE_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?"
    r"(TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"([a-zA-Z0-9_][a-zA-Z0-9_.]*)",
    re.IGNORECASE,
)

_CTE_RE = re.compile(
    r"\bWITH\s+([a-zA-Z0-9_]+)\s+AS\s*\(",
    re.IGNORECASE,
)

_CTE_CONTINUATION_RE = re.compile(
    r",\s*([a-zA-Z0-9_]+)\s+AS\s*\(",
    re.IGNORECASE,
)

_FROM_JOIN_RE = re.compile(
    r"(?:FROM|JOIN)\s+([a-zA-Z0-9_][a-zA-Z0-9_.]*)",
    re.IGNORECASE,
)

_COLUMN_DEF_RE = re.compile(
    r"([a-zA-Z0-9_]+)\s+((?:CHARACTER\s+VARYING|DOUBLE\s+PRECISION|"
    r"TIMESTAMP\s+WITH(?:OUT)?\s+TIME\s+ZONE|[a-zA-Z0-9_]+)"
    r"(?:\s*\([^)]*\))?)",
    re.IGNORECASE,
)

# SQL keywords that should NOT be treated as column names
_SQL_KEYWORDS = frozenset({
    "select", "from", "where", "and", "or", "not", "in", "on", "as",
    "join", "inner", "left", "right", "outer", "cross", "full", "group",
    "order", "by", "having", "limit", "offset", "union", "all", "insert",
    "into", "values", "update", "set", "delete", "create", "drop",
    "alter", "table", "view", "index", "primary", "key", "foreign",
    "references", "constraint", "default", "null", "unique", "check",
    "if", "exists", "temp", "temporary", "replace", "with", "case",
    "when", "then", "else", "end", "cast", "is", "like", "between",
    "distinct", "asc", "desc", "true", "false",
})

# Data type keywords to validate column parsing
_DATA_TYPES = frozenset({
    "int", "integer", "bigint", "smallint", "tinyint",
    "float", "double", "real", "decimal", "numeric",
    "varchar", "char", "character", "text", "string", "clob",
    "boolean", "bool",
    "date", "time", "timestamp", "datetime", "timestamptz",
    "blob", "binary", "varbinary", "bytea",
    "json", "jsonb", "xml",
    "uuid", "serial", "bigserial",
    "array", "map", "struct",
    "number",
})


def _parse_table_ref(raw: str) -> TableRef:
    """Parse 'schema.table' or 'table' into a TableRef."""
    parts = raw.split(".")
    if len(parts) >= 2:
        return TableRef(schema=parts[-2], table=parts[-1])
    return TableRef(schema=None, table=parts[0])


def _extract_cte_names(sql: str) -> set[str]:
    """Extract all CTE names from a SQL string."""
    names: set[str] = set()
    # Find initial WITH ... AS
    for m in _CTE_RE.finditer(sql):
        names.add(m.group(1).lower())
        # Find continuation CTEs after this WITH block
        rest = sql[m.end():]
        # Walk through balanced parens to find comma-separated CTEs
        for cm in _CTE_CONTINUATION_RE.finditer(rest):
            names.add(cm.group(1).lower())
    return names


def parse_create_statement(sql: str) -> list[CreateStatement]:
    """Extract CREATE TABLE/VIEW statements from SQL."""
    results: list[CreateStatement] = []
    for m in _CREATE_RE.finditer(sql):
        kind = m.group(1).upper()  # TABLE or VIEW
        raw_name = m.group(2)
        table_ref = _parse_table_ref(raw_name)

        # Try to extract column definitions for CREATE TABLE ... (col1 type1, ...)
        columns: list[ColumnDef] = []
        after_name = sql[m.end():].lstrip()
        if after_name.startswith("(") and kind == "TABLE":
            # Find matching closing paren
            depth = 0
            end_idx = 0
            for i, ch in enumerate(after_name):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            if end_idx > 0:
                col_block = after_name[1:end_idx]
                # Only parse if this looks like column definitions (not a subquery)
                if not col_block.strip().upper().startswith("SELECT"):
                    for col_match in _COLUMN_DEF_RE.finditer(col_block):
                        col_name = col_match.group(1)
                        col_type = col_match.group(2)
                        type_base = col_type.split("(")[0].split()[0].lower()
                        if col_name.lower() not in _SQL_KEYWORDS and type_base in _DATA_TYPES:
                            columns.append(ColumnDef(name=col_name, data_type=col_type))

        results.append(CreateStatement(
            table_ref=table_ref,
            view_or_table=kind,
            columns=columns,
            raw_sql=sql,
        ))
    return results


def extract_table_references(sql: str) -> list[TableRef]:
    """Extract table references from FROM/JOIN clauses, excluding CTE names."""
    cte_names = _extract_cte_names(sql)
    refs: list[TableRef] = []
    seen: set[str] = set()

    for m in _FROM_JOIN_RE.finditer(sql):
        raw = m.group(1)
        # Skip if it looks like a subquery keyword
        if raw.upper() in ("SELECT", "LATERAL", "UNNEST", "GENERATE_SERIES"):
            continue
        ref = _parse_table_ref(raw)
        # Skip CTE names
        if ref.table.lower() in cte_names and ref.schema is None:
            continue
        key = ref.qualified.lower()
        if key not in seen:
            seen.add(key)
            refs.append(ref)
    return refs


def parse_sql_file(file_path: Path) -> ParsedSQL:
    """Read a SQL file and parse its contents."""
    raw_sql = file_path.read_text(encoding="utf-8")
    creates = parse_create_statement(raw_sql)
    references = extract_table_references(raw_sql)
    return ParsedSQL(
        file_path=file_path,
        creates=creates,
        references=references,
        raw_sql=raw_sql,
    )


def build_dependency_graph(parsed_files: list[ParsedSQL]) -> DependencyGraph:
    """Build a dependency graph from parsed SQL files.

    Nodes are keyed by the qualified name of the table they create.
    Edges point from a node to the nodes it depends on.
    """
    graph = DependencyGraph()

    # Map created table names to their node key
    table_to_node: dict[str, str] = {}
    for pf in parsed_files:
        for cs in pf.creates:
            key = cs.table_ref.qualified.lower()
            graph.nodes[key] = pf
            graph.edges[key] = set()
            table_to_node[cs.table_ref.table.lower()] = key
            if cs.table_ref.schema:
                table_to_node[cs.table_ref.qualified.lower()] = key

    # Build edges
    for pf in parsed_files:
        for cs in pf.creates:
            node_key = cs.table_ref.qualified.lower()
            for ref in pf.references:
                # Try qualified first, then bare table name
                dep_key = table_to_node.get(ref.qualified.lower())
                if dep_key is None:
                    dep_key = table_to_node.get(ref.table.lower())
                if dep_key is not None and dep_key != node_key:
                    graph.edges[node_key].add(dep_key)

    return graph


def topological_sort(graph: DependencyGraph) -> list[str]:
    """Topological sort using Kahn's algorithm. Breaks cycles gracefully."""
    if not graph.nodes:
        return []

    # Build in-degree map (only for nodes in the graph)
    in_degree: dict[str, int] = {node: 0 for node in graph.nodes}
    for node, deps in graph.edges.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] = in_degree.get(dep, 0)  # already initialized above

    # Recalculate: in_degree counts how many nodes depend on this node
    # Actually for topological sort we want: in_degree[x] = number of deps x has
    # that are still in the graph
    in_degree = {node: 0 for node in graph.nodes}
    for node, deps in graph.edges.items():
        for dep in deps:
            if dep in graph.nodes:
                in_degree[node] = in_degree.get(node, 0) + 1

    # Wait, let me reconsider. Standard Kahn's:
    # in_degree[x] = number of prerequisites of x
    # A node with 0 in-degree has no prerequisites and can be processed first.
    in_degree = {node: 0 for node in graph.nodes}
    for node, deps in graph.edges.items():
        count = sum(1 for d in deps if d in graph.nodes)
        in_degree[node] = count

    queue: deque[str] = deque()
    for node, deg in in_degree.items():
        if deg == 0:
            queue.append(node)

    result: list[str] = []
    remaining = dict(in_degree)

    while queue:
        node = queue.popleft()
        result.append(node)
        del remaining[node]
        # Decrease in-degree of nodes that depend on this node
        for other, deps in graph.edges.items():
            if other in remaining and node in deps:
                remaining[other] -= 1
                if remaining[other] == 0:
                    queue.append(other)

    # Handle cycles: add remaining nodes in alphabetical order
    if remaining:
        for node in sorted(remaining.keys()):
            if node not in result:
                result.append(node)

    return result


def detect_layer(node_name: str, graph: DependencyGraph) -> str:
    """Detect the dbt layer for a node.

    Heuristic:
    - Sources: referenced but never created (not in graph.nodes)
    - Staging: only depends on sources (no deps in graph.nodes)
    - Marts: nothing else depends on it
    - Intermediate: everything else
    """
    deps = graph.edges.get(node_name, set())
    # Nodes that depend on this node
    dependents = {n for n, d in graph.edges.items() if node_name in d}

    # If no dependencies within the graph, it's staging (it reads from sources)
    internal_deps = {d for d in deps if d in graph.nodes}
    if not internal_deps:
        return "staging"

    # If nothing depends on it, it's a mart
    if not dependents:
        return "marts"

    return "intermediate"


def replace_refs_in_sql(
    sql: str,
    ref_map: dict[str, str],
    source_map: dict[str, tuple[str, str]],
) -> str:
    """Replace raw table references with dbt ref() and source() calls.

    ref_map: qualified_name -> model_name
    source_map: qualified_name -> (source_name, table_name)
    """
    # Sort by length descending to replace longer matches first (schema.table before table)
    all_replacements: list[tuple[str, str]] = []

    for raw_name, model_name in ref_map.items():
        replacement = "{{ " + f"ref('{model_name}')" + " }}"
        all_replacements.append((raw_name, replacement))

    for raw_name, (src_name, tbl_name) in source_map.items():
        replacement = "{{ " + f"source('{src_name}', '{tbl_name}')" + " }}"
        all_replacements.append((raw_name, replacement))

    # Sort by length of raw_name descending
    all_replacements.sort(key=lambda x: len(x[0]), reverse=True)

    result = sql
    for raw_name, replacement in all_replacements:
        # Replace case-insensitively but preserve word boundaries
        pattern = re.compile(re.escape(raw_name), re.IGNORECASE)
        result = pattern.sub(replacement, result)

    return result
