"""dbt-forge doctor — project health check."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import typer
import yaml
from rich.console import Console

from dbt_forge.scanner import find_project_root as _scanner_find_project_root
from dbt_forge.scanner import find_sql_models as _find_sql_models
from dbt_forge.scanner import find_yml_files as _find_yml_files
from dbt_forge.scanner import parse_yml_models as _parse_yml_models
from dbt_forge.scanner import parse_yml_tests as _parse_yml_tests
from dbt_forge.ui.theme import (
    ICON_FAIL,
    ICON_OK,
    forge_console,
    make_table,
    print_error,
    print_ok,
    print_summary,
    timed,
)

console = Console()


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    fix_hint: str = ""


@dataclass
class DoctorReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)


def find_project_root() -> Path:
    """Walk up from cwd to find dbt_project.yml."""
    return _scanner_find_project_root()


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_naming_conventions(root: Path) -> CheckResult:
    """Check that models follow naming conventions."""
    models = _find_sql_models(root)
    violations = []
    for model in models:
        name = model.stem
        rel = model.relative_to(root)
        parts = str(rel).split("/")

        if "staging" in parts and not name.startswith("stg_") and not name.startswith("_"):
            violations.append(f"  {rel} — staging models should be prefixed 'stg_'")
        elif "intermediate" in parts and not name.startswith("int_") and not name.startswith("_"):
            violations.append(f"  {rel} — intermediate models should be prefixed 'int_'")

    if violations:
        return CheckResult(
            name="naming-conventions",
            passed=False,
            message=(
                f"{len(violations)} model(s) violate naming conventions:\n"
                + "\n".join(violations[:5])
            ),
            fix_hint="Rename models to follow stg_/int_ prefix conventions.",
        )
    return CheckResult(
        name="naming-conventions",
        passed=True,
        message="All models follow naming conventions.",
    )


def check_schema_coverage(root: Path) -> CheckResult:
    """Check that every SQL model has a YAML entry."""
    sql_models = _find_sql_models(root)
    documented = _parse_yml_models(root)

    undocumented = []
    for model in sql_models:
        name = model.stem
        if name.startswith("_"):
            continue  # Skip YAML-only files
        if name.startswith("int_"):
            continue  # Intermediate models are typically ephemeral and don't need separate docs
        if name not in documented:
            undocumented.append(str(model.relative_to(root)))

    if undocumented:
        return CheckResult(
            name="schema-coverage",
            passed=False,
            message=f"{len(undocumented)} model(s) missing YAML documentation:\n"
            + "\n".join(f"  {u}" for u in undocumented[:5]),
            fix_hint="Run dbt-forge doctor --fix to auto-generate schema stubs.",
        )
    return CheckResult(
        name="schema-coverage",
        passed=True,
        message="All models have YAML documentation.",
    )


def check_test_coverage(root: Path) -> CheckResult:
    """Check that every model has at least one test."""
    sql_models = _find_sql_models(root)
    tested = _parse_yml_tests(root)

    untested = []
    for model in sql_models:
        name = model.stem
        if name.startswith("_"):
            continue
        if name not in tested:
            untested.append(str(model.relative_to(root)))

    if untested:
        return CheckResult(
            name="test-coverage",
            passed=False,
            message=f"{len(untested)} model(s) have no tests:\n"
            + "\n".join(f"  {u}" for u in untested[:5]),
            fix_hint="Use dbt-forge add test <model> to generate test stubs.",
        )
    return CheckResult(
        name="test-coverage",
        passed=True,
        message="All models have at least one test.",
    )


def check_hardcoded_refs(root: Path) -> CheckResult:
    """Check for hardcoded database/schema references in SQL models."""
    models = _find_sql_models(root)
    # Pattern: database.schema.table (3-part reference)
    pattern = re.compile(r"\b\w+\.\w+\.\w+\b")
    # Exclusions: common false positives
    exclusions = {"config.materialized", "target.schema", "target.name", "target.database"}

    violations = []
    for model in models:
        content = model.read_text()
        # Skip lines that are comments or Jinja
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("--") or stripped.startswith("{"):
                continue
            matches = pattern.findall(stripped)
            for match in matches:
                if match.lower() not in exclusions and not match.startswith("{{"):
                    violations.append(f"  {model.relative_to(root)}:{i} — {match}")
                    break

    if violations:
        return CheckResult(
            name="hardcoded-refs",
            passed=False,
            message=f"{len(violations)} file(s) may have hardcoded references:\n"
            + "\n".join(violations[:5]),
            fix_hint="Replace hardcoded references with ref() or source().",
        )
    return CheckResult(
        name="hardcoded-refs",
        passed=True,
        message="No hardcoded database/schema references found.",
    )


def check_packages_pinned(root: Path) -> CheckResult:
    """Check that packages.yml uses pinned version ranges."""
    packages_path = root / "packages.yml"
    if not packages_path.exists():
        return CheckResult(
            name="packages-pinned",
            passed=True,
            message="No packages.yml (skipped).",
        )

    try:
        data = yaml.safe_load(packages_path.read_text())
    except yaml.YAMLError:
        return CheckResult(
            name="packages-pinned",
            passed=False,
            message="packages.yml is not valid YAML.",
        )

    if not data or "packages" not in data:
        return CheckResult(name="packages-pinned", passed=True, message="No packages defined.")

    unpinned = []
    for pkg in data["packages"]:
        if not isinstance(pkg, dict):
            continue
        if "package" in pkg and "version" not in pkg:
            unpinned.append(pkg["package"])

    if unpinned:
        return CheckResult(
            name="packages-pinned",
            passed=False,
            message=f"{len(unpinned)} package(s) missing version pin:\n"
            + "\n".join(f"  {u}" for u in unpinned),
            fix_hint="Add version ranges to all packages in packages.yml.",
        )
    return CheckResult(
        name="packages-pinned",
        passed=True,
        message="All packages have version ranges.",
    )


def check_source_freshness(root: Path) -> CheckResult:
    """Check that sources have freshness config."""
    yml_files = _find_yml_files(root)
    sources_without_freshness = []

    for path in yml_files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "sources" not in data:
            continue
        for source in data["sources"]:
            if not isinstance(source, dict):
                continue
            name = source.get("name", "unknown")
            config = source.get("config", {})
            has_freshness = "freshness" in source or "freshness" in (config or {})
            if not has_freshness:
                sources_without_freshness.append(name)

    if sources_without_freshness:
        return CheckResult(
            name="source-freshness",
            passed=False,
            message=f"{len(sources_without_freshness)} source(s) missing freshness config:\n"
            + "\n".join(f"  {s}" for s in sources_without_freshness),
            fix_hint="Add freshness config inside the source's config: block.",
        )
    return CheckResult(
        name="source-freshness",
        passed=True,
        message="All sources have freshness config.",
    )


def check_orphaned_yml(root: Path) -> CheckResult:
    """Check for YAML model entries referencing non-existent SQL files."""
    yml_files = _find_yml_files(root)
    orphaned = []

    for path in yml_files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "models" not in data:
            continue
        for model in data["models"]:
            if not isinstance(model, dict):
                continue
            name = model.get("name", "")
            sql_path = path.parent / f"{name}.sql"
            if not sql_path.exists():
                orphaned.append(f"  {path.relative_to(root)}: {name}")

    if orphaned:
        return CheckResult(
            name="orphaned-yml",
            passed=False,
            message=f"{len(orphaned)} YAML model(s) reference missing SQL files:\n"
            + "\n".join(orphaned[:5]),
            fix_hint="Remove orphaned entries or create the missing SQL files.",
        )
    return CheckResult(
        name="orphaned-yml",
        passed=True,
        message="No orphaned YAML entries.",
    )


def check_sqlfluff_config(root: Path) -> CheckResult:
    """Check that .sqlfluff config exists."""
    if (root / ".sqlfluff").exists():
        return CheckResult(
            name="sqlfluff-config",
            passed=True,
            message=".sqlfluff config found.",
        )
    return CheckResult(
        name="sqlfluff-config",
        passed=False,
        message="No .sqlfluff config found.",
        fix_hint="Run dbt-forge add pre-commit or create .sqlfluff manually.",
    )


def check_gitignore(root: Path) -> CheckResult:
    """Check that .gitignore includes critical dbt paths."""
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return CheckResult(
            name="gitignore",
            passed=False,
            message="No .gitignore found.",
            fix_hint="Create a .gitignore with target/, dbt_packages/, logs/.",
        )
    content = gitignore_path.read_text()
    missing = []
    for entry in ("target/", "dbt_packages/", "logs/"):
        if entry not in content:
            missing.append(entry)

    if missing:
        return CheckResult(
            name="gitignore",
            passed=False,
            message=f".gitignore missing: {', '.join(missing)}",
            fix_hint=f"Add {', '.join(missing)} to .gitignore.",
        )
    return CheckResult(name="gitignore", passed=True, message=".gitignore looks good.")


def check_disabled_models(root: Path) -> CheckResult:
    """Check for disabled models (tech debt indicator)."""
    yml_files = _find_yml_files(root)
    disabled = []

    for path in yml_files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not data or "models" not in data:
            continue
        for model in data["models"]:
            if not isinstance(model, dict):
                continue
            config = model.get("config", {})
            if isinstance(config, dict) and config.get("enabled") is False:
                disabled.append(model.get("name", "unknown"))

    if disabled:
        return CheckResult(
            name="disabled-models",
            passed=False,
            message=f"{len(disabled)} disabled model(s) found (tech debt):\n"
            + "\n".join(f"  {d}" for d in disabled),
            fix_hint="Remove disabled models or re-enable them.",
        )
    return CheckResult(
        name="disabled-models",
        passed=True,
        message="No disabled models.",
    )


# ---------------------------------------------------------------------------
# All checks registry
# ---------------------------------------------------------------------------

ALL_CHECKS = {
    "naming-conventions": check_naming_conventions,
    "schema-coverage": check_schema_coverage,
    "test-coverage": check_test_coverage,
    "hardcoded-refs": check_hardcoded_refs,
    "packages-pinned": check_packages_pinned,
    "source-freshness": check_source_freshness,
    "orphaned-yml": check_orphaned_yml,
    "sqlfluff-config": check_sqlfluff_config,
    "gitignore": check_gitignore,
    "disabled-models": check_disabled_models,
}


# ---------------------------------------------------------------------------
# --fix: auto-generate missing schema stubs
# ---------------------------------------------------------------------------


def fix_schema_coverage(root: Path) -> int:
    """Generate missing _models.yml stubs for undocumented models. Returns count."""
    sql_models = _find_sql_models(root)
    documented = _parse_yml_models(root)

    fixed = 0
    for model in sql_models:
        name = model.stem
        if name.startswith("_") or name.startswith("int_") or name in documented:
            continue

        yml_path = model.parent / f"_{name}__models.yml"
        if yml_path.exists():
            continue

        stub = {
            "version": 2,
            "models": [
                {
                    "name": name,
                    "description": "",
                    "columns": [],
                }
            ],
        }
        yml_path.write_text(yaml.dump(stub, default_flow_style=False, sort_keys=False))
        console.print(f"  [green]\u2714[/green]  {yml_path.relative_to(root)}")
        fixed += 1

    return fixed


# ---------------------------------------------------------------------------
# Main doctor runner
# ---------------------------------------------------------------------------


def run_doctor(
    check_name: str | None = None,
    fix: bool = False,
    ci: bool = False,
) -> DoctorReport:
    """Run doctor checks and return report."""
    root = find_project_root()
    report = DoctorReport()

    if check_name:
        if check_name not in ALL_CHECKS:
            print_error(
                f"Unknown check '{check_name}'. "
                f"Available: {', '.join(ALL_CHECKS.keys())}"
            )
            raise typer.Exit(1)
        result = ALL_CHECKS[check_name](root)
        report.results.append(result)
    else:
        with timed("Running health checks..."):
            for _name, check_fn in ALL_CHECKS.items():
                result = check_fn(root)
                report.results.append(result)

    # Display results
    if not ci:
        forge_console.print()
        table = make_table("dbt-forge doctor", [
            ("Status", {"width": 6, "justify": "center"}),
            ("Check", {"min_width": 20}),
            ("Details", {"ratio": 1}),
        ])

        for r in report.results:
            status = f"{ICON_OK} PASS" if r.passed else f"{ICON_FAIL} FAIL"
            details = r.message
            if not r.passed and r.fix_hint:
                details += f"\n[dim]{r.fix_hint}[/dim]"
            table.add_row(status, r.name, details)

        forge_console.print(table)
        print_summary("Doctor results", [
            f"{report.pass_count} passed",
            f"{report.fail_count} failed",
        ])

    # Auto-fix
    if fix:
        forge_console.print("[bold cyan]Auto-fixing schema coverage...[/bold cyan]")
        fixed = fix_schema_coverage(root)
        if fixed:
            print_ok(f"Generated {fixed} schema stub(s).")
        else:
            forge_console.print("  Nothing to fix.")
        forge_console.print()

    # CI exit code
    if ci and not report.passed:
        raise typer.Exit(1)

    return report
