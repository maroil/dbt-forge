"""dbt ref() / source() dependency graph builder."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from dbt_forge.scanner import find_sql_models


@dataclass
class RefEdge:
    model: str
    ref_type: str  # "ref" or "source"
    source_name: str = ""  # only for source() refs


@dataclass
class ModelNode:
    name: str
    sql_path: Path
    layer: str  # staging / intermediate / marts / other
    refs: list[RefEdge] = field(default_factory=list)
    cte_count: int = 0
    join_count: int = 0
    line_count: int = 0


@dataclass
class RefGraph:
    nodes: dict[str, ModelNode] = field(default_factory=dict)
    upstream: dict[str, set[str]] = field(default_factory=dict)
    downstream: dict[str, set[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Regex patterns for ref() / source()
# ---------------------------------------------------------------------------

_REF_PATTERN = re.compile(
    r"""\{\{\s*ref\(\s*"""
    r"""(?:['"](\w+)['"]\s*,\s*)?"""  # optional project arg
    r"""['"](\w+)['"]\s*\)\s*\}\}""",
    re.VERBOSE,
)

_SOURCE_PATTERN = re.compile(
    r"""\{\{\s*source\(\s*['"](\w+)['"]\s*,\s*['"](\w+)['"]\s*\)\s*\}\}""",
    re.VERBOSE,
)

_CTE_PATTERN = re.compile(r"(?:\bwith|,)\s+\w+\s+as\s*\(", re.IGNORECASE)
_JOIN_PATTERN = re.compile(r"\bjoin\b", re.IGNORECASE)


def parse_refs(sql: str) -> list[RefEdge]:
    """Extract ref() and source() calls from SQL text."""
    edges: list[RefEdge] = []
    seen: set[tuple[str, str, str]] = set()

    for match in _REF_PATTERN.finditer(sql):
        model_name = match.group(2)
        key = ("ref", model_name, "")
        if key not in seen:
            seen.add(key)
            edges.append(RefEdge(model=model_name, ref_type="ref"))

    for match in _SOURCE_PATTERN.finditer(sql):
        source_name = match.group(1)
        table_name = match.group(2)
        key = ("source", table_name, source_name)
        if key not in seen:
            seen.add(key)
            edges.append(RefEdge(model=table_name, ref_type="source", source_name=source_name))

    return edges


def compute_complexity(sql: str) -> dict[str, int]:
    """Compute CTE count, JOIN count, and line count for SQL."""
    lines = sql.splitlines()
    cte_count = len(_CTE_PATTERN.findall(sql))
    join_count = len(_JOIN_PATTERN.findall(sql))
    return {"cte_count": cte_count, "join_count": join_count, "line_count": len(lines)}


def _detect_layer(path: Path, root: Path) -> str:
    """Detect model layer from file path."""
    rel = str(path.relative_to(root)).lower()
    if "staging" in rel:
        return "staging"
    if "intermediate" in rel:
        return "intermediate"
    if "marts" in rel:
        return "marts"
    return "other"


def build_ref_graph(root: Path) -> RefGraph:
    """Walk models/ and build a bidirectional dependency graph."""
    graph = RefGraph()
    sql_files = find_sql_models(root)

    for sql_path in sql_files:
        name = sql_path.stem
        sql = sql_path.read_text()
        refs = parse_refs(sql)
        complexity = compute_complexity(sql)
        layer = _detect_layer(sql_path, root)

        node = ModelNode(
            name=name,
            sql_path=sql_path,
            layer=layer,
            refs=refs,
            cte_count=complexity["cte_count"],
            join_count=complexity["join_count"],
            line_count=complexity["line_count"],
        )
        graph.nodes[name] = node
        graph.upstream.setdefault(name, set())
        graph.downstream.setdefault(name, set())

    # Build edges
    for name, node in graph.nodes.items():
        for ref in node.refs:
            if ref.ref_type == "ref" and ref.model in graph.nodes:
                graph.upstream[name].add(ref.model)
                graph.downstream.setdefault(ref.model, set()).add(name)

    return graph


def get_all_downstream(graph: RefGraph, model: str) -> dict[str, int]:
    """BFS downstream from model. Returns {model_name: depth}."""
    result: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque([(model, 0)])
    visited: set[str] = {model}

    while queue:
        current, depth = queue.popleft()
        for child in graph.downstream.get(current, set()):
            if child not in visited:
                visited.add(child)
                result[child] = depth + 1
                queue.append((child, depth + 1))

    return result


def get_all_upstream(graph: RefGraph, model: str) -> dict[str, int]:
    """BFS upstream from model. Returns {model_name: depth}."""
    result: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque([(model, 0)])
    visited: set[str] = {model}

    while queue:
        current, depth = queue.popleft()
        for parent in graph.upstream.get(current, set()):
            if parent not in visited:
                visited.add(parent)
                result[parent] = depth + 1
                queue.append((parent, depth + 1))

    return result


def detect_cycles(graph: RefGraph) -> list[list[str]]:
    """DFS cycle detection. Returns list of cycles found."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in graph.nodes}
    parent: dict[str, str | None] = {n: None for n in graph.nodes}
    cycles: list[list[str]] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        for v in graph.downstream.get(u, set()):
            if v not in color:
                continue
            if color[v] == GRAY:
                # Found cycle — reconstruct
                cycle = [v]
                node = u
                while node != v:
                    cycle.append(node)
                    node = parent.get(node, v)
                cycle.append(v)
                cycle.reverse()
                cycles.append(cycle)
            elif color[v] == WHITE:
                parent[v] = u
                dfs(v)
        color[u] = BLACK

    for node_name in graph.nodes:
        if color[node_name] == WHITE:
            dfs(node_name)

    return cycles
