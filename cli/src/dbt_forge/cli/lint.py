"""dbt-forge lint — project structure linter."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from dbt_forge.cli.doctor import CheckResult
from dbt_forge.lint_config import LintConfig, load_lint_config
from dbt_forge.ref_graph import (
    RefGraph,
    build_ref_graph,
    compute_complexity,
    detect_cycles,
)
from dbt_forge.scanner import find_project_root, find_sql_models, find_yml_files

console = Console()


# ---------------------------------------------------------------------------
# Lint rules
# ---------------------------------------------------------------------------

_SELECT_COL_PATTERN = re.compile(
    r"""(?:^|\n)\s*select\b(.*?)(?:\bfrom\b)""",
    re.IGNORECASE | re.DOTALL,
)

_CTE_BODY_PATTERN = re.compile(
    r"""\b(\w+)\s+as\s*\((.*?)\)(?:\s*,|\s*\bselect\b)""",
    re.IGNORECASE | re.DOTALL,
)


def check_dag_fan_out(graph: RefGraph, config: LintConfig) -> CheckResult:
    """Models with downstream count >= threshold."""
    violations = []
    for name in sorted(graph.nodes):
        downstream_count = len(graph.downstream.get(name, set()))
        if downstream_count >= config.fan_out_threshold:
            violations.append(f"  {name} — {downstream_count} downstream dependents")

    if violations:
        return CheckResult(
            name="fan-out",
            passed=False,
            message=f"{len(violations)} model(s) exceed fan-out threshold "
            f"({config.fan_out_threshold}):\n" + "\n".join(violations[:5]),
            fix_hint="Consider breaking high fan-out models into intermediate layers.",
        )
    return CheckResult(name="fan-out", passed=True, message="No excessive fan-out detected.")


def check_source_to_mart(graph: RefGraph) -> CheckResult:
    """Marts directly referencing source() — missing staging layer."""
    violations = []
    for name, node in sorted(graph.nodes.items()):
        if node.layer != "marts":
            continue
        for ref in node.refs:
            if ref.ref_type == "source":
                violations.append(
                    f"  {name} — directly references source('{ref.source_name}', '{ref.model}')"
                )

    if violations:
        return CheckResult(
            name="source-to-mart",
            passed=False,
            message=f"{len(violations)} mart(s) directly reference sources:\n"
            + "\n".join(violations[:5]),
            fix_hint="Add a staging model between sources and marts.",
        )
    return CheckResult(
        name="source-to-mart", passed=True, message="No marts directly reference sources."
    )


def check_model_complexity(root: Path, config: LintConfig) -> CheckResult:
    """Models exceeding CTE/join/line count thresholds."""
    violations = []
    for sql_path in find_sql_models(root):
        sql = sql_path.read_text()
        stats = compute_complexity(sql)
        issues = []
        if stats["cte_count"] > config.max_cte_count:
            issues.append(f"CTEs={stats['cte_count']}")
        if stats["join_count"] > config.max_join_count:
            issues.append(f"JOINs={stats['join_count']}")
        if stats["line_count"] > config.max_line_count:
            issues.append(f"lines={stats['line_count']}")
        if issues:
            rel = sql_path.relative_to(root)
            violations.append(f"  {rel} — {', '.join(issues)}")

    if violations:
        return CheckResult(
            name="model-complexity",
            passed=False,
            message=f"{len(violations)} model(s) exceed complexity thresholds:\n"
            + "\n".join(violations[:5]),
            fix_hint="Break complex models into CTEs or intermediate models.",
        )
    return CheckResult(
        name="model-complexity", passed=True, message="All models within complexity thresholds."
    )


def check_duplicate_logic(root: Path) -> CheckResult:
    """Find models with duplicate CTE bodies (copy-paste indicator)."""
    cte_hashes: dict[str, list[str]] = {}

    for sql_path in find_sql_models(root):
        sql = sql_path.read_text()
        model_name = sql_path.stem
        for match in _CTE_BODY_PATTERN.finditer(sql):
            body = match.group(2).strip()
            # Normalize whitespace for comparison
            normalized = re.sub(r"\s+", " ", body.lower())
            if len(normalized) < 30:  # Skip trivial CTEs
                continue
            h = hashlib.md5(normalized.encode()).hexdigest()
            cte_hashes.setdefault(h, []).append(f"{model_name}.{match.group(1)}")

    duplicates = {h: models for h, models in cte_hashes.items() if len(models) > 1}

    if duplicates:
        violations = []
        for models in list(duplicates.values())[:5]:
            violations.append(f"  {' == '.join(models)}")
        return CheckResult(
            name="duplicate-logic",
            passed=False,
            message=f"{len(duplicates)} duplicate CTE(s) detected:\n" + "\n".join(violations),
            fix_hint="Extract duplicate logic into shared models or macros.",
        )
    return CheckResult(
        name="duplicate-logic", passed=True, message="No duplicate CTE logic detected."
    )


def check_circular_deps(graph: RefGraph) -> CheckResult:
    """Check for circular dependencies in the DAG."""
    cycles = detect_cycles(graph)
    if cycles:
        violations = []
        for cycle in cycles[:3]:
            violations.append(f"  {' -> '.join(cycle)}")
        return CheckResult(
            name="circular-deps",
            passed=False,
            message=f"{len(cycles)} circular dependency(ies) found:\n" + "\n".join(violations),
            fix_hint="Break circular dependencies by restructuring models.",
        )
    return CheckResult(name="circular-deps", passed=True, message="No circular dependencies.")


def check_yaml_sql_drift(root: Path) -> CheckResult:
    """Compare columns in YAML vs SELECT clause in SQL."""
    violations = []
    yml_files = find_yml_files(root)

    for path in yml_files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "models" not in data:
            continue

        for model in data["models"]:
            if not isinstance(model, dict) or "name" not in model:
                continue
            model_name = model["name"]
            yml_columns = {
                col["name"].lower()
                for col in model.get("columns", [])
                if isinstance(col, dict) and "name" in col
            }
            if not yml_columns:
                continue

            # Find corresponding SQL
            sql_path = path.parent / f"{model_name}.sql"
            if not sql_path.exists():
                continue

            sql = sql_path.read_text()
            sql_columns = _extract_select_columns(sql)
            if not sql_columns:
                continue

            yml_only = yml_columns - sql_columns
            sql_only = sql_columns - yml_columns

            if yml_only or sql_only:
                details = []
                if yml_only:
                    details.append(f"YAML-only: {', '.join(sorted(yml_only)[:3])}")
                if sql_only:
                    details.append(f"SQL-only: {', '.join(sorted(sql_only)[:3])}")
                violations.append(f"  {model_name} — {'; '.join(details)}")

    if violations:
        return CheckResult(
            name="yaml-sql-drift",
            passed=False,
            message=f"{len(violations)} model(s) have YAML/SQL column drift:\n"
            + "\n".join(violations[:5]),
            fix_hint="Update YAML schema to match SQL SELECT columns.",
        )
    return CheckResult(
        name="yaml-sql-drift", passed=True, message="YAML and SQL columns are in sync."
    )


def _extract_select_columns(sql: str) -> set[str]:
    """Best-effort extraction of final SELECT column names."""
    # Find the last SELECT ... FROM block
    # Strip comments
    clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)

    matches = list(re.finditer(r"\bselect\b(.*?)\bfrom\b", clean, re.IGNORECASE | re.DOTALL))
    if not matches:
        return set()

    # Use last select block (final select)
    select_body = matches[-1].group(1)
    columns: set[str] = set()

    for part in select_body.split(","):
        part = part.strip()
        if not part:
            continue
        # Handle aliases: "expr as alias" or just "column_name"
        as_match = re.search(r"\bas\s+(\w+)\s*$", part, re.IGNORECASE)
        if as_match:
            columns.add(as_match.group(1).lower())
        else:
            # Last word (could be table.column or just column)
            words = re.findall(r"\w+", part)
            if words:
                columns.add(words[-1].lower())

    return columns


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

ALL_LINT_RULES = {
    "fan-out": "check_dag_fan_out",
    "source-to-mart": "check_source_to_mart",
    "model-complexity": "check_model_complexity",
    "duplicate-logic": "check_duplicate_logic",
    "circular-deps": "check_circular_deps",
    "yaml-sql-drift": "check_yaml_sql_drift",
}


def run_lint(
    rule: str | None = None,
    ci: bool = False,
    config_path: str | None = None,
) -> list[CheckResult]:
    """Run lint rules and display results."""
    root = find_project_root()
    config = load_lint_config(
        config_path=Path(config_path) if config_path else None,
        root=root,
    )
    graph = build_ref_graph(root)

    results: list[CheckResult] = []

    def _run_rule(name: str) -> None:
        if name in config.disabled_rules:
            return
        if name == "fan-out":
            results.append(check_dag_fan_out(graph, config))
        elif name == "source-to-mart":
            results.append(check_source_to_mart(graph))
        elif name == "model-complexity":
            results.append(check_model_complexity(root, config))
        elif name == "duplicate-logic":
            results.append(check_duplicate_logic(root))
        elif name == "circular-deps":
            results.append(check_circular_deps(graph))
        elif name == "yaml-sql-drift":
            results.append(check_yaml_sql_drift(root))

    if rule:
        if rule not in ALL_LINT_RULES:
            console.print(
                f"[red]Error:[/red] Unknown rule '{rule}'. "
                f"Available: {', '.join(ALL_LINT_RULES.keys())}"
            )
            sys.exit(1)
        _run_rule(rule)
    else:
        for name in ALL_LINT_RULES:
            _run_rule(name)

    # Display
    if not ci:
        console.print()
        table = Table(title="dbt-forge lint", show_lines=False, padding=(0, 1))
        table.add_column("Status", width=6, justify="center")
        table.add_column("Rule", min_width=20)
        table.add_column("Details", ratio=1)

        for r in results:
            status = "[green]PASS[/green]" if r.passed else "[yellow]WARN[/yellow]"
            details = r.message
            if not r.passed and r.fix_hint:
                details += f"\n[dim]{r.fix_hint}[/dim]"
            table.add_row(status, r.name, details)

        console.print(table)
        console.print()

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        console.print(f"  [bold]{passed}[/bold] passed, [bold]{failed}[/bold] warnings")
        console.print()

    if ci and any(not r.passed for r in results):
        sys.exit(1)

    return results
